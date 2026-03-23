import os
import requests
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from bson.objectid import ObjectId
from datetime import datetime, timezone, timedelta

# Importa as conexões oficiais do seu bot
from modules.player.core import users_collection
from modules.database import clans_col

app = Flask(__name__)
CORS(app) 

# ==========================================
# FUNÇÃO PARA SINCRONIZAR COM O CHAT DO TELEGRAM
# ==========================================
def enviar_mensagem_telegram(chat_id, texto, destino=None):
    token = os.getenv("BOT_TOKEN")
    if not token or not chat_id: 
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto, "parse_mode": "HTML"}
    
    if destino:
        payload["reply_markup"] = {
            "inline_keyboard": [[
                {"text": "🗺️ Abrir Menu da Região", "callback_data": f"open_region:{destino}"}
            ]]
        }
        
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Erro ao enviar msg pro telegram:", e)

# ==========================================
# ROTA PRINCIPAL E LOGIN
# ==========================================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def pagina_login():
    return render_template('login.html')

# ==========================================
# ROTAS DE RANKING
# ==========================================
@app.route('/ranking/level')
def ranking_level():
    try:
        top = users_collection.find({}, {"character_name": 1, "level": 1, "_id": 0}).sort("level", -1).limit(10)
        return jsonify([{"nome": j.get("character_name", "Desconhecido"), "valor": f"Lvl {j.get('level', 1)}"} for j in top])
    except Exception as e: return jsonify([])

@app.route('/ranking/ouro')
def ranking_ouro():
    try:
        top = users_collection.find({}, {"character_name": 1, "gold": 1, "_id": 0}).sort("gold", -1).limit(10)
        return jsonify([{"nome": j.get("character_name", "Desconhecido"), "valor": f"💰 {j.get('gold', 0)}"} for j in top])
    except Exception as e: return jsonify([])

@app.route('/ranking/pvp')
def ranking_pvp():
    return jsonify([{"nome": "Murdock", "valor": "⚔️ 2500 Pontos"}, {"nome": "Skuks", "valor": "⚔️ 2340 Pontos"}])

@app.route('/ranking/guildas')
def ranking_guildas():
    try:
        if clans_col is None: return jsonify([])
        top_clans = clans_col.find({}, {"name": 1, "prestige_level": 1, "prestige_points": 1, "_id": 0}).sort([("prestige_level", -1), ("prestige_points", -1)]).limit(10)
        lista = [{"nome": clan.get("name", "Sem Nome"), "valor": f"🌟 Lvl {clan.get('prestige_level', 0)} ({clan.get('prestige_points', 0)} pts)"} for clan in top_clans]
        return jsonify(lista) if len(lista) > 0 else jsonify([{"nome": "Nenhuma guilda", "valor": "-"}])
    except Exception as e: return jsonify([])

# ==========================================
# ROTA DE PERFIL (COM PROTEÇÃO CONTRA NULLS)
# ==========================================
@app.route('/perfil/<user_id>')
def obter_perfil(user_id):
    try:
        busca_id = ObjectId(user_id) if len(str(user_id)) == 24 else int(user_id) if str(user_id).isdigit() else user_id
        usuario = users_collection.find_one({"$or": [{"_id": busca_id}, {"last_chat_id": busca_id}, {"telegram_id_owner": busca_id}, {"telegram_id": busca_id}]})
        
        if usuario:
            lvl = int(usuario.get("level", 1))
            xp_visual_max = int(200 + (100 * (lvl - 1)) + (40 * (lvl - 1) * (lvl - 1))) 
            
            # Trava de segurança para garantir que a classe nunca seja nula
            classe_bd = usuario.get("class")
            classe_str = str(classe_bd) if classe_bd else "aprendiz"
            
            return jsonify({
                "nome": usuario.get("character_name", "Aventureiro"), 
                "level": lvl, 
                "gold": usuario.get("gold", 0), 
                "gems": usuario.get("gems", 0),
                "classe": classe_str.capitalize(), 
                "xp": int(usuario.get("xp", 0)), 
                "xp_max": xp_visual_max,
                "hp_atual": usuario.get("current_hp", 0), 
                "hp_max": usuario.get("max_hp", 0), 
                "energy": usuario.get("energy", 0),
                "pontos_livres": usuario.get("stat_points", 0), 
                "avatar": f"{request.host_url}static/classes/{classe_str.lower()}.png"
            })
            
        return jsonify({"erro": "Personagem não encontrado no banco."}), 404
    except Exception as e: 
        return jsonify({"erro": str(e)}), 400

# ==========================================
# ROTAS DA WIKI
# ==========================================
@app.route('/wiki/classes')
def obter_classes():
    lista = []
    try:
        from modules.game_data.classes import CLASSES_DATA
        from modules.game_data.class_evolution import EVOLUTIONS
        for chave, classe_info in CLASSES_DATA.items():
            if classe_info.get("tier") == 1:
                evos = [{"nome": evo.get("display_name", ""), "tier": evo.get("tier_num", 0), "descricao": evo.get("desc", "")} for evo in EVOLUTIONS.get(chave, [])]
                status = classe_info.get("stat_modifiers", {})
                lista.append({
                    "id": chave, "nome": classe_info.get("display_name", "Desconhecida"), "emoji": classe_info.get("emoji", "❓"),
                    "descricao": classe_info.get("description", "Sem descrição."), "hp": status.get("hp", 0), "ataque": status.get("attack", 0), "defesa": status.get("defense", 0),
                    "imagem": classe_info.get("image_url", f"{request.host_url}static/classes/{chave}.png"), "video": classe_info.get("video_url", ""), "total_evolucoes": len(evos), "evolucoes": evos
                })
    except: pass
    return jsonify(sorted(lista, key=lambda x: x["nome"]))

@app.route('/wiki/regioes')
def obter_regioes():
    lista = []
    try:
        from modules.game_data.worldmap import REGIONS_DATA, REGION_TARGET_POWER
        for chave, info in REGIONS_DATA.items():
            lista.append({
                "id": chave, "nome": info.get("display_name", "Região"), "emoji": info.get("emoji", "🗺️"),
                "descricao": info.get("description", ""), "level_min": REGION_TARGET_POWER.get(chave, 1), "imagem": info.get("image_url", f"{request.host_url}static/regions/{chave}.jpg")
            })
    except: pass
    return jsonify(sorted(lista, key=lambda x: x["level_min"]))

@app.route('/wiki/monstros')
def obter_monstros():
    lista = []
    try:
        from modules.game_data.monsters import MONSTERS_DATA
        nomes_itens = {}
        try:
            from modules.game_data.items import ITEMS_DATA
            for k, v in ITEMS_DATA.items(): nomes_itens[k] = f"{v.get('emoji', '📦')} {v.get('display_name', k.replace('_', ' ').title())}"
        except: pass
        mobs_vistos = set() 
        for regiao_id, lista_mobs in MONSTERS_DATA.items():
            for mob in lista_mobs:
                mob_id = mob.get("id")
                if mob_id in mobs_vistos: continue
                mobs_vistos.add(mob_id)
                loot_formatado = [{"nome": nomes_itens.get(l.get("item_id"), l.get("item_id")), "chance": l.get("drop_chance", 0)} for l in mob.get("loot_table", [])]
                lista.append({
                    "id": mob_id, "nome": mob.get("name", "Monstro"), "level": mob.get("min_level", mob.get("level", 1)),
                    "hp": mob.get("hp", mob.get("max_hp", 0)), "ataque": mob.get("attack", mob.get("atk", 0)), "defesa": mob.get("defense", mob.get("def", 0)),
                    "xp": mob.get("xp_reward", 0), "gold": mob.get("gold_drop", 0), "loot": loot_formatado, 
                    "imagem": mob.get("image_url", f"{request.host_url}static/monsters/{mob_id}.jpg"),
                    "regiao_id": regiao_id, "regiao_nome": regiao_id.replace("_", " ").title(), "nivel_regiao": 1, "is_evento": False
                })
    except: pass
    return jsonify(lista)

@app.route('/wiki/itens')
def obter_itens():
    lista = []
    try:
        from modules.game_data.items import ITEMS_DATA
        for chave, info in ITEMS_DATA.items():
            lista.append({
                "id": chave, "nome": info.get("display_name", "Item"), "raridade": str(info.get("rarity", "Comum")).capitalize(),
                "descricao": info.get("description", ""), "preco": info.get("value", info.get("price", 0)), "imagem": info.get("image_url", f"{request.host_url}static/items/{chave}.png")
            })
    except: pass
    return jsonify(sorted(lista, key=lambda x: x["nome"]))

@app.route('/api/meus_personagens/<int:telegram_id>')
def listar_personagens(telegram_id):
    try:
        cursor = users_collection.find({"$or": [{"telegram_id": telegram_id}, {"telegram_owner_id": telegram_id}, {"last_chat_id": telegram_id}]})
        personagens = [{"id": str(p["_id"]), "nome": p.get("character_name", "Desconhecido"), "classe": str(p.get("class", "aventureiro")).capitalize(), "level": p.get("level", 1)} for p in cursor]
        return jsonify(personagens)
    except: return jsonify([])

@app.route('/api/personagem/<personagem_id>')
def obter_personagem_info(personagem_id):
    try:
        if users_collection is None: return jsonify({"erro": "Servidor conectando..."}), 500
        busca_id = ObjectId(personagem_id) if len(str(personagem_id)) == 24 else None
        if not busca_id: return jsonify({"erro": "ID inválido"}), 400

        pdata = users_collection.find_one({"_id": busca_id})
        if not pdata: return jsonify({"erro": "Personagem não encontrado."}), 404
            
        return jsonify({
            "nome": pdata.get("character_name", "Aventureiro"), "classe": str(pdata.get("class", "aventureiro")).capitalize(),
            "level": pdata.get("level", 1), "ouro": pdata.get("gold", 0), "diamantes": pdata.get("gems", 0),
            "hp": pdata.get("current_hp", 0), "max_hp": pdata.get("max_hp", 0),
            "mp": pdata.get("current_mp", pdata.get("mana", 0)), "max_mp": pdata.get("max_mana", 0),
            "local_atual": pdata.get("current_location", "reino_eldora"),
            "tier": str(pdata.get("premium_tier", "free")).lower(),
            "estado": pdata.get("player_state", {"action": "idle"}), "energia": pdata.get("energy", 0)
        })
    except Exception as e: return jsonify({"erro": str(e)}), 500    

# ==========================================
# ROTA: INICIAR VIAGEM + AVISO TELEGRAM
# ==========================================
@app.route('/api/viajar', methods=['POST'])
def api_viajar():
    dados = request.json
    user_id = dados.get("user_id")
    destino = dados.get("destino")

    try:
        busca_id = ObjectId(user_id)
        pdata = users_collection.find_one({"_id": busca_id})
        if not pdata: return jsonify({"erro": "Personagem não encontrado"})

        estado = pdata.get("player_state", {})
        if estado.get("action") == "travel": return jsonify({"erro": "Você já está viajando!"})

        tier = str(pdata.get("premium_tier", "free")).lower()
        is_vip = tier in ["lenda", "vip", "premium", "admin"]
        secs = 0 if is_vip else 360 
        
        try:
            from modules.game_data.worldmap import REGIONS_DATA
            nome_destino = REGIONS_DATA.get(destino, {}).get("display_name", destino)
        except:
            nome_destino = destino
            
        chat_id = pdata.get("last_chat_id")
        
        if secs <= 0:
            pdata["current_location"] = destino
            pdata["player_state"] = {"action": "idle"}
            users_collection.replace_one({"_id": busca_id}, pdata)
            enviar_mensagem_telegram(chat_id, f"🚀 <b>[Eldora App]</b> Viagem instantânea concluída! Você chegou em <b>{nome_destino}</b>.", destino)
        else:
            finish = datetime.now(timezone.utc) + timedelta(seconds=secs)
            pdata["player_state"] = {"action": "travel", "finish_time": finish.isoformat(), "details": {"destination": destino}}
            users_collection.replace_one({"_id": busca_id}, pdata)
            enviar_mensagem_telegram(chat_id, f"🧭 <b>[Eldora App]</b> Viagem iniciada para <b>{nome_destino}</b>.\n⏳ Tempo estimado: {secs//60} minutos.")
        
        return jsonify({"sucesso": True, "secs": secs, "destino": destino, "is_vip": is_vip})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# ==========================================
# ROTA: FINALIZAR VIAGEM PELO APP + AVISO TELEGRAM
# ==========================================
@app.route('/api/finalizar_viagem', methods=['POST'])
def api_finalizar_viagem():
    dados = request.json
    user_id = dados.get("user_id")
    
    try:
        busca_id = ObjectId(user_id)
        pdata = users_collection.find_one({"_id": busca_id})
        if not pdata: return jsonify({"erro": "Personagem não encontrado"})

        estado = pdata.get("player_state", {})
        if estado.get("action") == "travel":
            destino = estado.get("details", {}).get("destination", "reino_eldora")
            
            try:
                from modules.game_data.worldmap import REGIONS_DATA
                nome_destino = REGIONS_DATA.get(destino, {}).get("display_name", destino)
            except:
                nome_destino = destino
            
            pdata["current_location"] = destino
            pdata["player_state"] = {"action": "idle"}
            users_collection.replace_one({"_id": busca_id}, pdata)

            chat_id = pdata.get("last_chat_id")
            enviar_mensagem_telegram(chat_id, f"✅ <b>[Eldora App]</b> Sua viagem terminou! Você chegou em <b>{nome_destino}</b>.", destino)
            
        return jsonify({"sucesso": True})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/api/recent_premium')
def recent_premium():
    try:
        ativos = users_collection.find({"premium_tier": {"$in": ["premium", "vip", "lenda"]}}, {"character_name": 1, "premium_tier": 1, "_id": 1}).sort("premium_expires_at", -1).limit(10)
        return jsonify([{"id": str(p["_id"]), "nome": p.get("character_name", "Um Herói"), "tier": str(p.get("premium_tier", "premium")).capitalize()} for p in ativos])
    except: return jsonify([])    
    

# ==========================================
# ROTA: INICIAR COMBATE WEB APP (NOVO SISTEMA)
# ==========================================
@app.route('/api/combate/iniciar', methods=['POST'])
def api_combate_iniciar():
    import random
    from handlers.hunt_handler import _pick_monster_template, _build_combat_details_from_template

    dados = request.json
    user_id = dados.get("user_id")

    try:
        busca_id = ObjectId(user_id)
        pdata = users_collection.find_one({"_id": busca_id})
        if not pdata: return jsonify({"erro": "Personagem não encontrado"})

        hp_atual = int(pdata.get("current_hp", pdata.get("max_hp", 100)))
        if hp_atual <= 0: return jsonify({"erro": "Você está morto! Descanse ou use uma poção."})
        if pdata.get("energy", 0) < 1: return jsonify({"erro": "Sem energia suficiente (⚡)."})

        # Desconta Energia
        users_collection.update_one({"_id": busca_id}, {"$inc": {"energy": -1}})
        pdata["energy"] -= 1

        # Sorteia Monstro usando a MESMA lógica do Telegram (hunt_handler)
        player_lvl = int(pdata.get("level", 1))
        regiao = pdata.get("current_location", "pradaria_inicial")
        
        tpl = _pick_monster_template(regiao, player_lvl)
        monster_stats = _build_combat_details_from_template(tpl, player_lvl)
        mob_img = tpl.get("image_url", f"/static/monsters/{tpl.get('id')}.jpg")

        player_stats = pdata.get("total_stats", pdata.copy())
        player_stats.pop("_id", None)
        if "max_hp" not in player_stats: player_stats["max_hp"] = pdata.get("max_hp", 100)

        # CRIA O CACHE DE BATALHA NO MONGODB
        battle_cache = {
            "player_stats": player_stats,
            "monster_stats": monster_stats,
            "player_hp": hp_atual,
            "player_mp": pdata.get("current_mp", player_stats.get("max_mana", 50)),
            "monster_hp": monster_stats.get("max_hp"),
            "regiao": regiao,
            "mob_img": mob_img,
            "mob_nome": monster_stats.get("name"),
            "turno": 1
        }
        
        pdata["battle_cache"] = battle_cache
        pdata["player_state"] = {"action": "in_combat"}
        users_collection.replace_one({"_id": busca_id}, pdata)

        # 👇 ADICIONE ISTO: O filtro que salva a vida do Flask 👇
        estado_frontend = {
            "player_hp": battle_cache["player_hp"],
            "player_mp": battle_cache["player_mp"],
            "monster_hp": battle_cache["monster_hp"],
            "regiao": battle_cache["regiao"],
            "mob_img": battle_cache["mob_img"],
            "mob_nome": battle_cache["mob_nome"],
            "player_stats": {
                "max_hp": player_stats.get("max_hp", 100),
                "max_mana": player_stats.get("max_mana", 50)
            },
            "monster_stats": {
                "max_hp": monster_stats.get("max_hp", 100)
            }
        }

        # E enviamos apenas o estado limpo!
        return jsonify({
            "sucesso": True,
            "estado": estado_frontend,
            "classe_player": str(pdata.get("class", "aventureiro")).lower()
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": str(e)})

# ==========================================
# ROTA: AÇÃO DO TURNO (O jogador clicou em algo)
# ==========================================
@app.route('/api/combate/acao', methods=['POST'])
def api_combate_acao():
    import asyncio
    from modules.combat import combat_engine, rewards

    dados = request.json
    user_id = dados.get("user_id")
    acao = dados.get("acao") # Pode ser 'atacar', 'skill', 'pocao', 'fugir'
    target_id = dados.get("target_id", None) # ID da skill ou poção se houver

    try:
        busca_id = ObjectId(user_id)
        pdata = users_collection.find_one({"_id": busca_id})
        cache = pdata.get("battle_cache")

        if not cache: return jsonify({"erro": "Nenhuma batalha ativa."})

        # Helper para rodar a Engine Async dentro do Flask Sync
        def rodar_engine(coro):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import nest_asyncio
                    nest_asyncio.apply()
                    return loop.run_until_complete(coro)
            except RuntimeError:
                return asyncio.run(coro)
            return loop.run_until_complete(coro)

        log_turno = []
        
        # 1. AÇÃO DO JOGADOR
        if acao == "fugir":
            pdata.pop("battle_cache", None)
            pdata["player_state"] = {"action": "idle"}
            users_collection.replace_one({"_id": busca_id}, pdata)
            return jsonify({"fugiu": True, "log": [{"autor": "system", "texto": "🏃 Você fugiu da batalha!"}]})

        elif acao == "atacar":
            res_p = rodar_engine(combat_engine.processar_acao_combate(
                attacker_pdata=pdata,
                attacker_stats=cache["player_stats"],
                target_stats=cache["monster_stats"],
                skill_id=None,
                attacker_current_hp=cache["player_hp"]
            ))
            dano_p = res_p.get("total_damage", 0)
            cache["monster_hp"] -= dano_p
            
            for msg in res_p.get("log_messages", []):
                log_turno.append({"autor": "player", "dano": dano_p, "texto": f"🧑‍🚀 {msg}"})

        # 2. CHECA SE MONSTRO MORREU
        vitoria = cache["monster_hp"] <= 0
        derrota = False
        recompensas_finais = {}

        if vitoria:
            from modules.game_data import items as items_data
            xp, gold, items_ids = rewards.calculate_victory_rewards(pdata, cache["monster_stats"])
            pdata["xp"] = pdata.get("xp", 0) + xp
            pdata["gold"] = pdata.get("gold", 0) + gold
            
            items_names = []
            if "inventory" not in pdata: pdata["inventory"] = {}
            for item_id in items_ids:
                if item_id not in pdata["inventory"]:
                    pdata["inventory"][item_id] = {"base_id": item_id, "quantity": 0}
                pdata["inventory"][item_id]["quantity"] += 1
                n_item = items_data.ITEMS_DATA.get(item_id, {}).get("display_name", item_id) if hasattr(items_data, 'ITEMS_DATA') else item_id
                items_names.append(n_item)

            recompensas_finais = {"xp": xp, "gold": gold, "items": items_names}
            pdata.pop("battle_cache", None)
            pdata["player_state"] = {"action": "idle"}
            log_turno.append({"autor": "system", "texto": f"🏆 {cache['mob_nome']} foi derrotado!"})
        else:
            # 3. TURNO DO MONSTRO (Se sobreviveu)
            res_m = rodar_engine(combat_engine.processar_acao_combate(
                attacker_pdata={}, 
                attacker_stats=cache["monster_stats"],
                target_stats=cache["player_stats"],
                skill_id=None,
                attacker_current_hp=cache["monster_hp"]
            ))
            dano_m = res_m.get("total_damage", 0)
            cache["player_hp"] -= dano_m
            
            msg_padrao = res_m.get("log_messages", [f"causou {dano_m}"])[0]
            log_turno.append({"autor": "mob", "dano": dano_m, "texto": f"🩸 {cache['mob_nome']} {msg_padrao}"})

            # Checa se jogador morreu
            if cache["player_hp"] <= 0:
                derrota = True
                log_turno.append({"autor": "system", "texto": "☠️ Você foi derrotado..."})
                msg_derrota, perdeu_xp = rewards.process_defeat(pdata, cache["monster_stats"])
                
                chat_id = pdata.get("last_chat_id")
                enviar_mensagem_telegram(chat_id, f"💀 <b>[App de Eldora]</b> {msg_derrota}")
                
                pdata.pop("battle_cache", None)
                pdata["player_state"] = {"action": "idle"}

        # Atualiza banco de dados
        if not vitoria and not derrota:
            cache["turno"] += 1
            pdata["battle_cache"] = cache
            
        pdata["current_hp"] = max(0, cache.get("player_hp", 0))
        users_collection.replace_one({"_id": busca_id}, pdata)

        return jsonify({
            "sucesso": True,
            "log": log_turno,
            "player_hp": cache.get("player_hp", 0),
            "monster_hp": cache.get("monster_hp", 0),
            "vitoria": vitoria,
            "derrota": derrota,
            "recompensas": recompensas_finais
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": str(e)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)