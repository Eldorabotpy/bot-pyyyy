import os
import requests
import asyncio
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from bson.objectid import ObjectId
from datetime import datetime, timezone, timedelta
from modules import player_manager
# Importa as conexões oficiais do seu bot
from modules.player.core import users_collection
from modules.database import clans_col
from modules.game_data.skills import SKILL_DATA, get_skill_data_with_rarity
app = Flask(__name__)
CORS(app) 
from modules.webapp_api import webapp_bp
app.register_blueprint(webapp_bp)

def _run_async(coro):
    """Ferramenta que força funções do Telegram a rodarem com segurança no Flask"""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(coro)
        loop.close()
        return res
    
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
@app.route('/ping')
def ping_server():
    return "Eldora Resiste!", 200

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def pagina_login():
    return render_template('login.html')

# --- ROTA CORRIGIDA PARA O PORTAL DE ACESSO FUNCIONAR ---
@app.route('/api/meus_personagens/<telegram_id>')
def listar_personagens(telegram_id):
    try:
        # Se o JS mandar lixo (undefined/null), a gente devolve vazio sem dar Erro 404
        if telegram_id in ["undefined", "null", ""]:
            return jsonify([])
            
        busca_id = int(telegram_id)
        
        cursor = users_collection.find({"$or": [{"telegram_id": busca_id}, {"telegram_owner_id": busca_id}, {"last_chat_id": busca_id}]})
        personagens = [{"id": str(p["_id"]), "nome": p.get("character_name", "Desconhecido"), "classe": str(p.get("class", "aventureiro")).capitalize(), "level": p.get("level", 1)} for p in cursor]
        return jsonify(personagens)
    except Exception as e: 
        print(f"Erro ao buscar personagens: {e}")
        return jsonify([])

# ==========================================
# ROTAS DE RANKING E WIKI (Resumidas)
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

@app.route('/api/viajar', methods=['POST'])
def api_viajar():
    dados = request.json
    user_id = dados.get("user_id")
    destino = dados.get("destino")

    try:
        busca_id = ObjectId(user_id)
        pdata = users_collection.find_one({"_id": busca_id})
        
        if not pdata:
            return jsonify({"erro": "Personagem não encontrado"}), 404

        # Se for VIP, viaja instantâneo
        tier = str(pdata.get("premium_tier", "free")).lower()
        eh_vip = tier in ["lenda", "vip", "premium", "admin"]

        if eh_vip:
            users_collection.update_one(
                {"_id": busca_id}, 
                {"$set": {"current_location": destino, "player_state": {"action": "idle"}}}
            )
            return jsonify({"sucesso": True, "is_vip": True})
        
        # Se for Free, inicia cronômetro de 6 minutos
        tempo_viagem = 6 # minutos
        finish_time = datetime.now(timezone.utc) + timedelta(minutes=tempo_viagem)
        
        users_collection.update_one(
            {"_id": busca_id}, 
            {"$set": {
                "player_state": {
                    "action": "travel",
                    "finish_time": finish_time.isoformat(),
                    "details": {"destination": destino}
                }
            }}
        )
        return jsonify({"sucesso": True, "is_vip": False})

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/api/finalizar_viagem', methods=['POST'])
def api_finalizar_viagem():
    dados = request.json
    user_id = dados.get("user_id")
    try:
        busca_id = ObjectId(user_id)
        pdata = users_collection.find_one({"_id": busca_id})
        
        estado = pdata.get("player_state", {})
        if estado.get("action") == "travel":
            destino = estado["details"]["destination"]
            users_collection.update_one(
                {"_id": busca_id},
                {"$set": {"current_location": destino, "player_state": {"action": "idle"}}}
            )
        return jsonify({"sucesso": True})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    
@app.route('/api/recent_premium')
def obter_recent_premium():
    try:
        # Busca os últimos 5 jogadores VIP/Premium no MongoDB
        cursor = users_collection.find(
            {"premium_tier": {"$ne": "free"}}, 
            {"character_name": 1, "premium_tier": 1, "_id": 0}
        ).sort("_id", -1).limit(5)
        
        colaboradores = []
        for c in cursor:
            colaboradores.append({
                "nome": c.get("character_name", "Aventureiro"),
                "tier": str(c.get("premium_tier", "VIP")).upper()
            })
        return jsonify(colaboradores)
    except Exception as e:
        return jsonify([])
        
@app.route('/ranking/guildas')
def ranking_guildas():
    try:
        if clans_col is None: return jsonify([])
        top_clans = clans_col.find({}, {"name": 1, "prestige_level": 1, "prestige_points": 1, "_id": 0}).sort([("prestige_level", -1), ("prestige_points", -1)]).limit(10)
        lista = [{"nome": clan.get("name", "Sem Nome"), "valor": f"🌟 Lvl {clan.get('prestige_level', 0)} ({clan.get('prestige_points', 0)} pts)"} for clan in top_clans]
        return jsonify(lista) if len(lista) > 0 else jsonify([{"nome": "Nenhuma guilda", "valor": "-"}])
    except Exception as e: return jsonify([])
       
@app.route('/api/personagem/<personagem_id>')
def obter_personagem_info(personagem_id):
    try:
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
# ROTA: BUSCAR MAGIAS EQUIPADAS DO JOGADOR
# ==========================================
@app.route('/api/personagem/<user_id>/magias_equipadas')
def obter_magias_equipadas(user_id):
    try:
        from bson.objectid import ObjectId
        
        # 1. Busca o jogador de forma blindada
        try:
            jogador = users_collection.find_one({"_id": ObjectId(user_id)})
        except:
            jogador = users_collection.find_one({"telegram_id": int(user_id)})
            if not jogador:
                jogador = users_collection.find_one({"_id": int(user_id)})

        if not jogador:
            return jsonify([{"id": "erro", "nome": "Erro: Jogador não achado no BD", "icone": "❌", "custo_mp": 0, "tipo": "active", "cooldown_atual": 0}])

        # 2. Pega as magias do BD
        skills_equipadas = jogador.get("equipped_skills", [])
        if not skills_equipadas:
            return jsonify([]) # Aqui o grimório está vazio de verdade

        cooldowns_atuais = jogador.get("cooldowns") or {}
        magias_formatadas = []

        # 3. IMPORTANTE: Importando direto aqui dentro para não dar erro de caminho
        from modules.game_data.skills import get_skill_data_with_rarity

        for skill_id in skills_equipadas:
            # Puxa os dados
            dados_skill = get_skill_data_with_rarity(jogador, skill_id)
            if not dados_skill:
                continue
                
            # Só mostra magias ativas ou suportes
            tipo_skill = dados_skill.get("type", "passive")
            if tipo_skill not in ["active", "support"]:
                continue

            nome_display = dados_skill.get("display_name", skill_id)
            
            # Escolhendo o ícone combinando com o nome
            icone = "✨"
            if any(x in nome_display for x in ["Cura", "Luz", "Sagrada", "Restauradora"]): icone = "💖"
            elif any(x in nome_display for x in ["Fogo", "Chama", "Magma", "Meteoro"]): icone = "🔥"
            elif any(x in nome_display for x in ["Corte", "Golpe", "Lâmina", "Guilhotina"]): icone = "⚔️"
            elif any(x in nome_display for x in ["Defesa", "Escudo", "Couraça"]): icone = "🛡️"
            elif any(x in nome_display for x in ["Sombra", "Furtivo", "Veneno", "Sorrateiro"]): icone = "🌑"
            elif any(x in nome_display for x in ["Flecha", "Tiro", "Mira"]): icone = "🏹"

            turnos_espera = int(cooldowns_atuais.get(skill_id, 0))

            magia = {
                "id": skill_id,
                "nome": nome_display,
                "icone": icone,
                "custo_mp": dados_skill.get("mana_cost", 0),
                "tipo": tipo_skill,
                "cooldown_atual": turnos_espera
            }
            magias_formatadas.append(magia)

        # Se filtrou tudo e não sobrou nada
        if len(magias_formatadas) == 0:
            return jsonify([{"id": "erro", "nome": "Aviso: Suas skills são apenas PASSIVAS", "icone": "⚠️", "custo_mp": 0, "tipo": "active", "cooldown_atual": 0}])

        return jsonify(magias_formatadas)

    except Exception as e:
        # SE O PYTHON TRAVAR, VAI MOSTRAR O ERRO NUM BOTÃO NA TELA!
        print(f"Erro Fatal nas Magias: {e}")
        return jsonify([{
            "id": "erro_fatal", 
            "nome": f"Erro Python: {str(e)}", 
            "icone": "🐛", 
            "custo_mp": 0, 
            "tipo": "active", 
            "cooldown_atual": 0
        }])
    
# ==========================================
# ROTA: CAÇAR (ROTA CLÁSSICA RESTAURADA)
# ==========================================
@app.route('/api/cacar', methods=['POST'])
def api_cacar():
    import asyncio
    from handlers.hunt_handler import _pick_monster_template, _build_combat_details_from_template
    from modules.combat import combat_engine, rewards

    dados = request.json
    user_id = dados.get("user_id")

    try:
        busca_id = ObjectId(user_id)
        pdata = users_collection.find_one({"_id": busca_id})
        if not pdata: return jsonify({"erro": "Personagem não encontrado"})

        hp_atual = int(pdata.get("current_hp", pdata.get("max_hp", 100)))
        if hp_atual <= 0: return jsonify({"erro": "Você está desmaiado! Recupere-se antes de caçar."})
        if pdata.get("energy", 0) < 1: return jsonify({"erro": "Sem energia suficiente (⚡)."})

        # Desconta Energia
        users_collection.update_one({"_id": busca_id}, {"$inc": {"energy": -1}})
        pdata["energy"] -= 1

        player_lvl = int(pdata.get("level", 1))
        regiao = pdata.get("current_location", "pradaria_inicial")
        
        tpl = _pick_monster_template(regiao, player_lvl)
        monster_stats = _build_combat_details_from_template(tpl, player_lvl)
        mob_img = tpl.get("image_url", f"/static/monsters/{tpl.get('id')}.jpg")

        player_stats = pdata.get("total_stats", pdata.copy())
        player_stats.pop("_id", None)
        if "max_hp" not in player_stats: player_stats["max_hp"] = pdata.get("max_hp", 100)

        # Helper para Async
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

        log_batalha = []
        mob_hp = monster_stats.get("max_hp", 50)
        p_hp = hp_atual
        
        turno = 1
        while p_hp > 0 and mob_hp > 0 and turno <= 20:
            # Player ataca
            res_p = rodar_engine(combat_engine.processar_acao_combate(
                attacker_pdata=pdata, attacker_stats=player_stats,
                target_stats=monster_stats, skill_id=None, attacker_current_hp=p_hp
            ))
            dano_p = res_p.get("total_damage", 0)
            mob_hp -= dano_p
            log_batalha.append({"atacante": "player", "dano": dano_p, "texto": res_p.get("log_messages", ["Atacou"])[0]})
            
            if mob_hp <= 0: break
            
            # Mob ataca
            res_m = rodar_engine(combat_engine.processar_acao_combate(
                attacker_pdata={}, attacker_stats=monster_stats,
                target_stats=player_stats, skill_id=None, attacker_current_hp=mob_hp
            ))
            dano_m = res_m.get("total_damage", 0)
            p_hp -= dano_m
            log_batalha.append({"atacante": "mob", "dano": dano_m, "texto": res_m.get("log_messages", ["Atacou"])[0]})
            
            turno += 1

        vitoria = mob_hp <= 0
        recompensas = {"xp": 0, "gold": 0, "items": []}
        
        if vitoria:
            xp, gold, items_ids = rewards.calculate_victory_rewards(pdata, monster_stats)
            pdata["xp"] = pdata.get("xp", 0) + xp
            pdata["gold"] = pdata.get("gold", 0) + gold
            
            # Formata os nomes dos itens para o JS
            items_names = []
            try:
                from modules.game_data import items as items_data
                for item_id in items_ids:
                    n_item = items_data.ITEMS_DATA.get(item_id, {}).get("display_name", item_id)
                    items_names.append(n_item)
            except:
                items_names = items_ids
                
            recompensas = {"xp": xp, "gold": gold, "items": items_names}
        else:
            rewards.process_defeat(pdata, monster_stats)

        pdata["current_hp"] = max(0, p_hp)
        _run_async(player_manager.save_player_data(busca_id, pdata)) # <--- USE ISSO

        return jsonify({
            "sucesso": True,
            "vitoria": vitoria,
            "regiao": regiao,
            "classe_player": str(pdata.get("class", "aventureiro")).lower(),
            "mob": {
                "nome": monster_stats.get("name", "Monstro"), 
                "hp_max": monster_stats.get("max_hp", 50), 
                "mp_max": monster_stats.get("max_mana", 0),
                "imagem": mob_img
            },
            "player": {
                "hp_max": player_stats.get("max_hp", 100),
                "mp_max": pdata.get("max_mana", 50) 
            },
            "log": log_batalha,
            "recompensas": recompensas
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": str(e)}), 500


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

        # =======================================================
        # 1. A MÁGICA: RECALCULA TUDO USANDO O MOTOR DO BOT
        # =======================================================
        total_stats = _run_async(player_manager.get_player_total_stats(pdata))
        
        hp_max_real = int(total_stats.get("max_hp", 100))
        mp_max_real = int(total_stats.get("max_mana", 50))
        
        # Garante que o HP/MP atual não ultrapasse o máximo real
        hp_atual = min(int(pdata.get("current_hp", hp_max_real)), hp_max_real)
        mp_atual = min(int(pdata.get("current_mp", mp_max_real)), mp_max_real)

        if hp_atual <= 0: return jsonify({"erro": "Você está morto! Descanse ou use uma poção."})
        if pdata.get("energy", 0) < 1: return jsonify({"erro": "Sem energia suficiente (⚡)."})

        # Desconta Energia
        users_collection.update_one({"_id": busca_id}, {"$inc": {"energy": -1}})
        pdata["energy"] -= 1

        player_lvl = int(pdata.get("level", 1))
        regiao = pdata.get("current_location", "pradaria_inicial")
        
        tpl = _pick_monster_template(regiao, player_lvl)
        monster_stats = _build_combat_details_from_template(tpl, player_lvl)
        mob_img = tpl.get("image_url", f"/static/monsters/{tpl.get('id')}.jpg")

        # =======================================================
        # 2. CRIA O CACHE COM OS DADOS PERFEITOS
        # =======================================================
        battle_cache = {
            "player_stats": total_stats, # Usa os status calculados!
            "monster_stats": monster_stats,
            "player_hp": hp_atual,
            "player_mp": mp_atual,
            "monster_hp": monster_stats.get("max_hp"),
            "regiao": regiao,
            "mob_img": mob_img,
            "mob_nome": monster_stats.get("name"),
            "turno": 1
        }
        
        pdata["battle_cache"] = battle_cache
        pdata["player_state"] = {"action": "in_combat"}
        pdata["current_hp"] = hp_atual
        pdata["current_mp"] = mp_atual
        
        _run_async(player_manager.save_player_data(busca_id, pdata)) 

        # =======================================================
        # 3. ENVIA PARA O JAVASCRIPT (COM LÓGICA DE SKIN)
        # =======================================================
        from modules.game_data.skins import get_skin_avatar
        
        classe_str = str(pdata.get("class", "aventureiro")).lower()
        genero_str = str(pdata.get("gender", "masculino")).lower()
        skin_equipada = pdata.get("equipped_skin")
        
        avatar_skin_combate = ""
        # Tenta puxar a imagem da skin se ela estiver equipada
        if skin_equipada:
            avatar_skin_combate = get_skin_avatar(skin_equipada, genero_str)

        estado_frontend = {
            "player_hp": hp_atual,
            "player_mp": mp_atual,
            "monster_hp": battle_cache["monster_hp"],
            "regiao": battle_cache["regiao"],
            "mob_img": battle_cache["mob_img"],
            "mob_nome": battle_cache["mob_nome"],
            "player_level": player_lvl,
            "monster_level": monster_stats.get("level", player_lvl), 
            "player_stats": total_stats, # JavaScript recebe tudo certinho
            "monster_stats": {
                "max_hp": monster_stats.get("max_hp", 100)
            }
        }

        return jsonify({
            "sucesso": True,
            "estado": estado_frontend,
            "classe_player": classe_str,
            "genero_player": genero_str,
            "avatar_combate": avatar_skin_combate # <--- MANDA A SKIN AQUI
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": str(e)})

# ==========================================
# ROTA: AÇÃO DO TURNO (NOVO SISTEMA)
# ==========================================

@app.route('/api/combate/acao', methods=['POST'])
def api_combate_acao():
    import asyncio
    from modules.combat import combat_engine, rewards

    dados = request.json
    user_id = dados.get("user_id")
    acao = dados.get("acao") 
    target_id = dados.get("target_id", None) 
    skill_id = dados.get("skill_id")
    
    try:
        busca_id = ObjectId(user_id)
        pdata = users_collection.find_one({"_id": busca_id})
        cache = pdata.get("battle_cache")

        if not cache: return jsonify({"erro": "Nenhuma batalha ativa."})

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
        
        if acao == "fugir":
            pdata.pop("battle_cache", None)
            pdata.pop("cooldowns", None) # Limpa cooldowns se fugir
            pdata["player_state"] = {"action": "idle"}
            pdata["current_hp"] = max(0, cache.get("player_hp", 0))
            pdata["current_mp"] = max(0, cache.get("player_mp", 0))
            _run_async(player_manager.save_player_data(busca_id, pdata))
            return jsonify({"fugiu": True, "log": [{"autor": "system", "texto": "🏃 Você fugiu da batalha!"}]})

        elif acao == "atacar" or acao == "magia":
            
            mana_atual = cache.get("player_mp", pdata.get("current_mp", 0))

            # ==========================================================
            # 1. GASTO DE MANA E COOLDOWN OFICIAL
            # ==========================================================
            if acao == "magia" and skill_id:
                from modules.game_data.skills import get_skill_data_with_rarity
                from modules.cooldowns import aplicar_cooldown
                
                skill_info = get_skill_data_with_rarity(pdata, skill_id)
                custo_mp = int(skill_info.get("mana_cost", 0))
                
                if mana_atual < custo_mp:
                    return jsonify({"erro": "Mana insuficiente para esta magia!"})
                
                mana_atual -= custo_mp
                cache["player_mp"] = mana_atual
                
                raridade_skill = skill_info.get("rarity", "comum")
                if "cooldowns" not in pdata: pdata["cooldowns"] = {}
                aplicar_cooldown(pdata, skill_id, raridade_skill)

            res_p = rodar_engine(combat_engine.processar_acao_combate(
                attacker_pdata=pdata,
                attacker_stats=cache["player_stats"],
                target_stats=cache["monster_stats"],
                skill_id=skill_id if acao == "magia" else None, 
                attacker_current_hp=cache.get("player_hp", 0),
                attacker_current_mp=mana_atual 
            ))
            
            dano_p = res_p.get("total_damage", 0)
            cache["monster_hp"] -= dano_p
            
            if "attacker_mp_left" in res_p:
                cache["player_mp"] = res_p["attacker_mp_left"]
            
            for msg in res_p.get("log_messages", []):
                log_turno.append({"autor": "player", "dano": dano_p, "texto": f"🧑‍🚀 {msg}"})

        # ==========================================================
        # 2. VERIFICAÇÃO DE VITÓRIA (ÚNICO BLOCO IF)
        # ==========================================================
        vitoria = cache["monster_hp"] <= 0
        derrota = False
        recompensas_finais = {}

        if vitoria:
            from modules.game_data import items as items_data
            from modules import game_data # Motor de XP
            
            xp, gold, items_ids = rewards.calculate_victory_rewards(pdata, cache["monster_stats"])
            pdata["xp"] = pdata.get("xp", 0) + xp
            pdata["gold"] = pdata.get("gold", 0) + gold
            
            # --- SISTEMA DE LEVEL UP AUTOMÁTICO ---
            subiu_nivel = False
            while True:
                lvl_atual = pdata.get("level", 1)
                try:
                    xp_necessaria = game_data.get_xp_for_next_combat_level(lvl_atual)
                except:
                    xp_necessaria = int(200 + (100 * (lvl_atual - 1)))
                    
                if pdata["xp"] >= xp_necessaria:
                    pdata["xp"] -= xp_necessaria
                    pdata["level"] = lvl_atual + 1
                    pdata["stat_points"] = pdata.get("stat_points", 0) + 3 # Dando 3 pontos (ajuste se precisar)
                    subiu_nivel = True
                else:
                    break
            
            # --- GESTÃO DE INVENTÁRIO ---
            items_names = []
            if "inventory" not in pdata: pdata["inventory"] = {}
        
            for item_id in items_ids:
                if item_id not in pdata["inventory"]: pdata["inventory"][item_id] = 0
            
                if isinstance(pdata["inventory"][item_id], dict):
                    pdata["inventory"][item_id]["quantity"] = pdata["inventory"][item_id].get("quantity", 0) + 1
                else:
                    pdata["inventory"][item_id] += 1
                
                n_item = items_data.ITEMS_DATA.get(item_id, {}).get("display_name", item_id) if hasattr(items_data, 'ITEMS_DATA') else item_id
                items_names.append(n_item)

            recompensas_finais = {"xp": xp, "gold": gold, "items": items_names}
            
            # Limpa cache e cooldowns
            pdata.pop("battle_cache", None)
            pdata.pop("cooldowns", None)
            pdata["player_state"] = {"action": "idle"}
            
            log_turno.append({"autor": "system", "texto": f"🏆 {cache['mob_nome']} foi derrotado!"})
            
            if subiu_nivel:
                log_turno.append({"autor": "system", "texto": f"🌟 PARABÉNS! Você alcançou o Nível {pdata['level']}!"})
                recompensas_finais["subiu_nivel"] = True 
                recompensas_finais["novo_nivel"] = pdata['level']
                
        else:
            # ==========================================================
            # 3. TURNO DO MONSTRO E DERROTA
            # ==========================================================
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

            if cache["player_hp"] <= 0:
                derrota = True
                log_turno.append({"autor": "system", "texto": "☠️ Você foi derrotado..."})
                msg_derrota, perdeu_xp = rewards.process_defeat(pdata, cache["monster_stats"])
                
                chat_id = pdata.get("last_chat_id")
                enviar_mensagem_telegram(chat_id, f"💀 <b>[App de Eldora]</b> {msg_derrota}")
                
                pdata.pop("battle_cache", None)
                pdata.pop("cooldowns", None)
                pdata["player_state"] = {"action": "idle"}

        # ==========================================================
        # 4. TRANSIÇÃO DE TURNO (SE NINGUÉM MORREU)
        # ==========================================================
        if not vitoria and not derrota:
            cache["turno"] += 1
            pdata["battle_cache"] = cache
            pdata["current_hp"] = max(0, cache.get("player_hp", 0))
            pdata["current_mp"] = max(0, cache.get("player_mp", 0))
            
            # Avança o relógio dos cooldowns
            if "cooldowns" in pdata:
                novos_cds = {}
                for sk, cd in pdata["cooldowns"].items():
                    if cd > 1: novos_cds[sk] = cd - 1
                pdata["cooldowns"] = novos_cds
        else:
            # Luta acabou, restaura a vida/mana para o máximo
            max_hp = cache.get("player_stats", {}).get("max_hp", 100)
            max_mp = cache.get("player_stats", {}).get("max_mana", 50)
            pdata["current_hp"] = max_hp
            pdata["current_mp"] = max_mp

        _run_async(player_manager.save_player_data(busca_id, pdata))

        return jsonify({
            "sucesso": True,
            "log": log_turno,
            "player_hp": cache.get("player_hp", 0),
            "player_mp": cache.get("player_mp", pdata.get("current_mp", 0)), 
            "monster_hp": cache.get("monster_hp", 0),
            "vitoria": vitoria,
            "derrota": derrota,
            "recompensas": recompensas_finais
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": str(e)})
    
# ==========================================
# ROTAS: AUTO-HUNT (WEB APP)
# ==========================================
@app.route('/api/autohunt/iniciar', methods=['POST'])
def api_autohunt_iniciar():
    dados = request.json
    user_id = dados.get("user_id")
    quantidade = int(dados.get("quantidade", 10))

    try:
        busca_id = ObjectId(user_id)
        pdata = users_collection.find_one({"_id": busca_id})
        if not pdata: return jsonify({"erro": "Personagem não encontrado"})

        tier = str(pdata.get("premium_tier", "free")).lower()
        limites = {"free": 0, "premium": 10, "vip": 25, "lenda": 35, "admin": 100}
        limite_permitido = limites.get(tier, 0)

        if limite_permitido <= 0:
            return jsonify({"erro": "🔒 O Auto-Hunt é exclusivo para jogadores Premium, VIP ou Lenda!"})

        if quantidade > limite_permitido:
            return jsonify({"erro": f"Seu plano permite no máximo {limite_permitido}x por vez."})

        energia_atual = int(pdata.get("energy", 0))
        if energia_atual < quantidade:
            return jsonify({"erro": f"Você precisa de {quantidade}⚡, mas tem {energia_atual}⚡."})

        # Desconta energia e calcula o tempo (30 seg por monstro)
        tempo_segundos = quantidade * 30
        finish_time = datetime.now(timezone.utc) + timedelta(seconds=tempo_segundos)
        regiao = pdata.get("current_location", "pradaria_inicial")

        users_collection.update_one(
            {"_id": busca_id},
            {"$inc": {"energy": -quantidade},
             "$set": {
                 "player_state": {
                     "action": "auto_hunting",
                     "finish_time": finish_time.isoformat(),
                     "details": {"hunt_count": quantidade, "region": regiao}
                 }
             }}
        )

        return jsonify({"sucesso": True, "finish_time": finish_time.isoformat()})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": str(e)}), 500

@app.route('/api/autohunt/finalizar', methods=['POST'])
def api_autohunt_finalizar():
    import random
    from handlers.hunt_handler import _pick_monster_template, _build_combat_details_from_template
    from modules.combat import rewards
    from modules.game_data import items as items_data
    from datetime import datetime, timezone

    dados = request.json
    user_id = dados.get("user_id")

    try:
        busca_id = ObjectId(user_id)
        pdata = users_collection.find_one({"_id": busca_id})
        
        estado = pdata.get("player_state", {})
        if estado.get("action") != "auto_hunting":
            return jsonify({"erro": "Você não está em uma caçada automática."})

        finish_time_str = estado.get("finish_time")
        if finish_time_str:
            finish_time = datetime.fromisoformat(finish_time_str.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) < finish_time:
                return jsonify({"erro": "A caçada ainda não terminou! Os monstros estão lutando."})

        quantidade = int(estado.get("details", {}).get("hunt_count", 1))
        regiao = estado.get("details", {}).get("region", "pradaria_inicial")
        player_lvl = int(pdata.get("level", 1))
        total_xp = 0
        total_gold = 0
        todos_itens = []
        nomes_itens_formatados = []

        for _ in range(quantidade):
            tpl = _pick_monster_template(regiao, player_lvl)
            monster_stats = _build_combat_details_from_template(tpl, player_lvl)
            xp, gold, items_ids = rewards.calculate_victory_rewards(pdata, monster_stats)
            total_xp += xp
            total_gold += gold
            todos_itens.extend(items_ids)

        pdata["xp"] = pdata.get("xp", 0) + total_xp
        pdata["gold"] = pdata.get("gold", 0) + total_gold
        
        # ==========================================================
        # 👇 SISTEMA DE LEVEL UP NO AUTO-HUNT 👇
        # ==========================================================
        from modules import game_data
        subiu_nivel = False
        
        while True:
            lvl_atual = pdata.get("level", 1)
            try:
                xp_necessaria = game_data.get_xp_for_next_combat_level(lvl_atual)
            except:
                xp_necessaria = int(200 + (100 * (lvl_atual - 1)))
                
            if pdata["xp"] >= xp_necessaria:
                pdata["xp"] -= xp_necessaria
                pdata["level"] = lvl_atual + 1
                pdata["stat_points"] = pdata.get("stat_points", 0) + 3 
                subiu_nivel = True
            else:
                break
        # ==========================================================
        
        if "inventory" not in pdata: pdata["inventory"] = {}
        for item_id in todos_itens:
            if item_id not in pdata["inventory"]: pdata["inventory"][item_id] = 0
            if isinstance(pdata["inventory"][item_id], dict):
                pdata["inventory"][item_id]["quantity"] = pdata["inventory"][item_id].get("quantity", 0) + 1
            else:
                pdata["inventory"][item_id] += 1
                
            n_item = items_data.ITEMS_DATA.get(item_id, {}).get("display_name", item_id) if hasattr(items_data, 'ITEMS_DATA') else item_id
            nomes_itens_formatados.append(n_item)

        pdata["player_state"] = {"action": "idle"}
        _run_async(player_manager.save_player_data(busca_id, pdata)) 

        return jsonify({
            "sucesso": True,
            "xp": total_xp,
            "gold": total_gold,
            "items": nomes_itens_formatados,
            "subiu_nivel": subiu_nivel,
            "novo_nivel": pdata.get("level")
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": str(e)}), 500

@app.route('/api/personagem/equipar', methods=['POST'])
def api_equipar_item():
    try:
        data = request.json
        from modules.player.inventory import equip_unique_item_for_user
        sucesso, msg = _run_async(equip_unique_item_for_user(data.get("user_id"), data.get("item_id")))
        if sucesso: return jsonify({"sucesso": True, "msg": msg})
        return jsonify({"erro": msg}), 400
    except Exception as e: return jsonify({"erro": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)