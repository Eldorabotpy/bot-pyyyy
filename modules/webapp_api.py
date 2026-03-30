# modules/webapp_api.py
import asyncio
import traceback
from flask import Blueprint, jsonify, request
from bson import ObjectId

# Cria o Blueprint (Mini-Aplicativo)
webapp_bp = Blueprint('webapp_bp', __name__)

def _run_async(coro):
    """Ferramenta interna para rodar funções Async do Telegram no Flask"""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(coro)
        loop.close()
        return res

# ==========================================
# ROTA DE PERFIL COMPLETO (TRANSFERIDA DO API.PY)
# ==========================================

@webapp_bp.route('/perfil/<user_id>')
def obter_perfil(user_id):
    try:
        from modules.player.core import users_collection 
        from modules import player_manager
        from modules.game_data import items as items_data
        from modules.game_data.equipment import SLOT_EMOJI, SLOT_ORDER
        from modules.game_data.classes import get_class_avatar
        from modules.game_data.skins import get_skin_avatar
        
        # 1. Busca Segura do Personagem
        busca_id = ObjectId(user_id) if len(str(user_id)) == 24 else int(user_id) if str(user_id).isdigit() else user_id
        pdata = users_collection.find_one({"$or": [{"_id": busca_id}, {"last_chat_id": busca_id}, {"telegram_id_owner": busca_id}, {"telegram_id": busca_id}]})
        
        if not pdata:
            return jsonify({"erro": "Personagem não encontrado."}), 404
        
        lvl = int(pdata.get("level", 1))
        
        # 👇 CORREÇÃO: Usa a função oficial de XP do jogo em vez da fórmula antiga
        from modules import game_data
        try:
            xp_visual_max = int(game_data.get_xp_for_next_combat_level(lvl))
        except:
            xp_visual_max = int(200 + (100 * (lvl - 1))) # Fallback básico de segurança
            
        classe_str = str(pdata.get("class", "aprendiz"))
        genero_str = str(pdata.get("gender", "masculino"))
        
        # 2. CALCULA STATUS TOTAIS (Considerando Equipamentos e Passivas)
        totals = _run_async(player_manager.get_player_total_stats(pdata))
        esquiva = int(_run_async(player_manager.get_player_dodge_chance(pdata)) * 100)
        atk_duplo = int(_run_async(player_manager.get_player_double_attack_chance(pdata)) * 100)
        
        # Definição correta de Máximos baseados nos itens equipados
        hp_max = int(totals.get("max_hp", 100))
        mp_max = int(totals.get("max_mana", 50))
        
        # Correção: Garante que o HP/MP atual não seja maior que o novo máximo e nem nulo
        hp_atual = int(pdata.get("current_hp", hp_max))
        mp_atual = int(pdata.get("current_mp", mp_max))
        
        if hp_atual > hp_max: hp_atual = hp_max
        if mp_atual > mp_max: mp_atual = mp_max

        # 3. Formatação de Status para exibição na UI
        status_formatados = {}
        for stat in ["attack", "defense", "initiative", "luck"]:
            val = int(totals.get(stat, 0))
            nome_pt = {"attack": "Ataque", "defense": "Defesa", "initiative": "Agilidade", "luck": "Sorte"}[stat]
            emoji = {"attack": "⚔️", "defense": "🛡️", "initiative": "🏃", "luck": "🍀"}[stat]
            status_formatados[stat] = {"nome": nome_pt, "emoji": emoji, "valor": val}

        # 4. Processamento de Profissão
        prof_nome, prof_lvl = "Nenhuma", 0
        prof_raw = pdata.get("profession")
        if prof_raw:
            if isinstance(prof_raw, dict):
                if "type" in prof_raw:
                    prof_nome, prof_lvl = str(prof_raw.get("type")).capitalize(), int(prof_raw.get("level", 1))
                else:
                    p_key = list(prof_raw.keys())[0]
                    prof_nome = str(p_key).capitalize()
                    prof_lvl = int(prof_raw[p_key].get("level", 1)) if isinstance(prof_raw[p_key], dict) else 1
            else:
                prof_nome, prof_lvl = str(prof_raw).capitalize(), 1

        # 5. Inventário formatado com Base_ID para imagens WebP
        inventario_cru = pdata.get("inventory") or {}
        inventario_formatado = []
        for item_id, qtd_ou_dict in inventario_cru.items():
            obj_item = qtd_ou_dict if isinstance(qtd_ou_dict, dict) else {}
            qtd = obj_item.get("quantity", 1) if obj_item else qtd_ou_dict
            
            if qtd > 0:
                base_id = obj_item.get("base_id", item_id) if obj_item else item_id
                info_item = items_data.ITEMS_DATA.get(base_id, {})
                nome_item = info_item.get("display_name", base_id.replace("_", " ").title())
                
                refino = obj_item.get("upgrade_level", obj_item.get("refine_level", 0))
                status_item = obj_item.get("enchantments") or obj_item.get("attributes") or info_item.get("stats", {})

                inventario_formatado.append({
                    "id": item_id, 
                    "base_id": base_id, 
                    "nome": nome_item, 
                    "emoji": info_item.get("emoji", "📦"), 
                    "qtd": qtd,
                    "tipo": info_item.get("type", "material"),
                    "desc": info_item.get("description", "Um item do mundo de Eldora."),
                    "raridade": obj_item.get("rarity", info_item.get("rarity", "comum")),
                    "refino": refino,
                    "stats": status_item
                })
        inventario_formatado.sort(key=lambda x: x["qtd"], reverse=True)

        # 6. Equipamentos formatados para o Boneco de Neve/UI
        equip_cru = pdata.get("equipment") or {}
        equip_formatado = []
        for slot in SLOT_ORDER:
            item_uid = equip_cru.get(slot)
            emoji_slot = SLOT_EMOJI.get(slot, "🔲")
            if item_uid and item_uid in inventario_cru:
                obj_item = inventario_cru[item_uid]
                base_id = obj_item.get("base_id", item_uid) if isinstance(obj_item, dict) else item_uid
                info_item = items_data.ITEMS_DATA.get(base_id, {})
                nome_equip = info_item.get("display_name", base_id.replace("_", " ").title())
                icon_equip = info_item.get("icon_url", info_item.get("emoji", "📦")) 
                
                refino = obj_item.get("upgrade_level", obj_item.get("refine_level", 0)) if isinstance(obj_item, dict) else 0
                status_item = obj_item.get("enchantments") or obj_item.get("attributes") or info_item.get("stats", {})

                equip_formatado.append({
                    "slot": slot, "uid": item_uid, "emoji": emoji_slot, "nome": nome_equip, 
                    "icon": icon_equip, "vazio": False,
                    "base_id": base_id, 
                    "tipo": info_item.get("type", "equipamento"), 
                    "desc": info_item.get("description", "Equipamento em uso."), 
                    "raridade": obj_item.get("rarity", info_item.get("rarity", "comum")),
                    "refino": refino,
                    "stats": status_item
                })
            else:
                equip_formatado.append({
                    "slot": slot, "emoji": emoji_slot, "nome": "Vazio", "icon": "🔲", 
                    "vazio": True, "desc": "Espaço vazio.", "tipo": "vazio", "raridade": "", "refino": 0, "stats": {}
                })

        # ==========================================
        # LÓGICA DO AVATAR (PRIORIZA A SKIN)
        # ==========================================
        avatar_final = ""
        skin_equipada = pdata.get("equipped_skin")
        
        # 1. Se tem skin equipada, tenta puxar o link da skin
        if skin_equipada:
            avatar_final = get_skin_avatar(skin_equipada, genero_str)
            
        # 2. Se não tem skin (ou se o link não foi encontrado), puxa a classe padrão
        if not avatar_final:
            avatar_final = get_class_avatar(classe_str, genero_str)

        # Retorno unificado para o Frontend (Perfil e Combate)
        return jsonify({
            "nome": pdata.get("character_name", "Aventureiro"), 
            "level": lvl, "gold": pdata.get("gold", 0), "gems": pdata.get("gems", 0),
            "classe": classe_str.capitalize(), "xp": int(pdata.get("xp", 0)), "xp_max": xp_visual_max,
            "hp_atual": hp_atual, "hp_max": hp_max, 
            "mp_atual": mp_atual, "mp_max": mp_max,
            "energy": pdata.get("energy", 0), "pontos_livres": pdata.get("stat_points", 0), 
            "avatar": avatar_final, # <--- AQUI ELE MANDA A SKIN OU A CLASSE!
            "status": status_formatados,
            "inventario": inventario_formatado, "equipamentos": equip_formatado,
            "esquiva": esquiva, "atk_duplo": atk_duplo, "prof_nome": prof_nome, "prof_lvl": prof_lvl
        })

    except Exception as e: 
        import traceback
        traceback.print_exc()
        return jsonify({"erro": f"Erro interno Python: {str(e)}"}), 400

# ==========================================
# ROTAS DE AÇÕES DOS BOTÕES (TRANSFERIDAS)
# ==========================================
@webapp_bp.route('/api/personagem/distribuir_ponto', methods=['POST'])
def api_distribuir_ponto():
    try:
        data = request.json
        user_id = data.get("user_id")
        stat = data.get("stat") # ex: "attack", "defense", "hp"

        from modules.player.core import users_collection
        from modules import player_manager
        from bson import ObjectId

        busca_id = ObjectId(user_id) if len(str(user_id)) == 24 else int(user_id) if str(user_id).isdigit() else user_id
        pdata = users_collection.find_one({"_id": busca_id})
        
        if not pdata: 
            return jsonify({"erro": "Personagem não encontrado."}), 404

        pontos_livres = int(pdata.get("stat_points", 0))
        if pontos_livres <= 0: 
            return jsonify({"erro": "Não tens pontos disponíveis!"}), 400

        # 👇 CORREÇÃO: Salva os pontos manuais na chave 'invested', e não 'base_stats'
        invested = pdata.get("invested", {})
        invested[stat] = int(invested.get(stat, 0)) + 1
        
        pdata["invested"] = invested
        pdata["stat_points"] = pontos_livres - 1

        _run_async(player_manager.save_player_data(user_id, pdata))
        return jsonify({"sucesso": True, "msg": "Ponto adicionado com sucesso!"})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": str(e)}), 500

@webapp_bp.route('/api/personagem/equipar', methods=['POST'])
def api_equipar_item():
    try:
        data = request.json
        from modules.player.inventory import equip_unique_item_for_user
        sucesso, msg = _run_async(equip_unique_item_for_user(data.get("user_id"), data.get("item_id")))
        if sucesso: return jsonify({"sucesso": True, "msg": msg})
        return jsonify({"erro": msg}), 400
    except Exception as e: return jsonify({"erro": str(e)}), 500

# ==========================================
# ROTAS DA WIKI (Adicione no webapp_api.py)
# ==========================================

@webapp_bp.route('/wiki/classes')
def wiki_classes():
    try:
        from modules.game_data.classes import CLASSES_DATA, get_class_avatar
        from modules.game_data.class_evolution import EVOLUTIONS
        from modules.game_data import items as items_data # Importa os itens para puxar emojis
        
        classes_base = {k: v for k, v in CLASSES_DATA.items() if v.get('tier', 1) == 1}
        lista_final = []

        for class_id, dados in classes_base.items():
            evolucoes_brutas = EVOLUTIONS.get(class_id, [])
            evolucoes_formatadas = []
            
            for evo in evolucoes_brutas:
                target_id = evo.get("to")
                target_data = CLASSES_DATA.get(target_id, {})
                
                # 1. Soma todos os custos de todos os nodes de ascensão
                custo_total = {}
                for node in evo.get("ascension_path", []):
                    for item_req, qtd_req in node.get("cost", {}).items():
                        custo_total[item_req] = custo_total.get(item_req, 0) + qtd_req
                
                # 2. Formata os custos com nomes bonitos e emojis
                custos_formatados = []
                for item_req, qtd_req in custo_total.items():
                    if item_req == "gold":
                        custos_formatados.append({"nome": "Ouro", "emoji": "💰", "qtd": qtd_req})
                    elif item_req == "gems":
                        custos_formatados.append({"nome": "Diamantes", "emoji": "💎", "qtd": qtd_req})
                    else:
                        info_item = items_data.ITEMS_DATA.get(item_req, {})
                        nome_item = info_item.get("display_name", item_req.replace("_", " ").title())
                        emoji_item = info_item.get("emoji", "📦")
                        custos_formatados.append({"nome": nome_item, "emoji": emoji_item, "qtd": qtd_req})

                # 3. Adiciona a evolução com a própria imagem e status dela!
                evolucoes_formatadas.append({
                    "id": target_id,
                    "tier": evo.get("tier_num"),
                    "nome": evo.get("display_name"),
                    "descricao": evo.get("desc"),
                    "emoji": target_data.get("emoji", "❓"),
                    "imagem": get_class_avatar(target_id, plataforma="web"), # Imagem da evolução!
                    "hp": target_data.get("stat_modifiers", {}).get("hp", 0),
                    "ataque": target_data.get("stat_modifiers", {}).get("attack", 0),
                    "defesa": target_data.get("stat_modifiers", {}).get("defense", 0),
                    "custos": custos_formatados # <--- OS REQUISITOS VÃO AQUI
                })
            
            evolucoes_formatadas.sort(key=lambda x: x['tier'])

            mod = dados.get('stat_modifiers', {})
            lista_final.append({
                "id": class_id,
                "nome": dados.get('display_name'),
                "emoji": dados.get('emoji', '❓'),
                "descricao": dados.get('description'),
                "hp": mod.get('hp', 0),
                "ataque": mod.get('attack', 0),
                "defesa": mod.get('defense', 0),
                "imagem": get_class_avatar(class_id, plataforma="web"),
                "total_evolucoes": len(evolucoes_formatadas),
                "evolucoes": evolucoes_formatadas
            })

        return jsonify(lista_final)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": str(e)}), 500
    
@webapp_bp.route('/wiki/monstros')
def wiki_monstros():
    try:
        from modules.game_data.monsters import MONSTERS_DATA
        from modules.game_data import items as items_data
        
        lista_final = []
        
        # Mapeamento de nomes bonitos para as regiões (IDs do dicionário)
        NOMES_REGIOES = {
            "pradaria_inicial": "Pradaria Inicial",
            "floresta_sombria": "Floresta Sombria",
            "pedreira_granito": "Pedreira de Granito",
            "_evolution_trials": "Provações de Evolução",
            # Adicione as outras regiões aqui...
        }

        for regiao_id, monstros in MONSTERS_DATA.items():
            regiao_nome = NOMES_REGIOES.get(regiao_id, regiao_id.replace("_", " ").title())
            
            # Define se é evento (Trials ou regiões especiais)
            is_evento = regiao_id.startswith("_") or "evento" in regiao_id.lower()
            
            for mob in monstros:
                # 1. Formata a tabela de loot (Drops)
                loot_formatado = []
                for drop in mob.get("loot_table", []):
                    item_id = drop.get("item_id")
                    # Busca o nome real do item no seu motor de itens
                    info_item = items_data.ITEMS_DATA.get(item_id, {})
                    nome_exibicao = info_item.get("display_name", item_id.replace("_", " ").title())
                    
                    loot_formatado.append({
                        "nome": nome_exibicao,
                        "chance": drop.get("drop_chance", 0)
                    })

                # 2. Monta o objeto que o wiki.js espera
                lista_final.append({
                    "id": mob.get("id"),
                    "nome": mob.get("name"),
                    "level": mob.get("level", 1), # Se não tiver level fixo, pegamos o base
                    "hp": mob.get("hp", 0),
                    "ataque": mob.get("attack", 0),
                    "defesa": mob.get("defense", 0),
                    "xp": mob.get("xp_reward", 0),
                    "gold": mob.get("gold_drop", 0),
                    "loot": loot_formatado,
                    "imagem": mob.get("image_url") or mob.get("media_key") or "/static/mobs/placeholder.png",
                    "regiao_id": regiao_id,
                    "regiao_nome": regiao_nome,
                    "is_evento": is_evento,
                    "nivel_regiao": mob.get("level", 0) # Usado para ordenar as regiões por dificuldade
                })
                
        return jsonify(lista_final)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": str(e)}), 500    

# ==========================================
# ROTA DA WIKI: ITENS (COM ABAS INTELIGENTES)
# ==========================================
@webapp_bp.route('/wiki/itens')
def wiki_itens():
    try:
        from modules.game_data import items as items_data
        
        lista_itens = []
        for item_id, dados in items_data.ITEMS_DATA.items():
            if dados.get("hidden", False): continue
                
            tipo = str(dados.get("type", "")).lower()
            categoria = str(dados.get("category", "")).lower()
            
            # --- LÓGICA DE ETIQUETAS (TABS) ---
            wiki_tab = "materiais" # Padrão (Cai na aba Caçada/Drops)
            wiki_sub = "geral"
            
            if tipo == "equipamento":
                wiki_tab = "equipamentos"
                # Pega a classe que pode usar o item
                classes_req = dados.get("class_req", [])
                wiki_sub = classes_req[0] if classes_req else "geral"
                
            elif tipo == "tool":
                wiki_tab = "coleta"
                wiki_sub = "ferramenta"
                
            elif tipo == "material_bruto" or categoria == "coletavel":
                wiki_tab = "coleta"
                wiki_sub = "bruto"
                
            elif tipo in ["material_refinado", "material_runico", "runa"]:
                wiki_tab = "refino"
                wiki_sub = tipo
                
            elif tipo in ["potion", "consumable", "reagent"]:
                wiki_tab = "consumiveis"
                wiki_sub = "geral"

            preco_venda = dados.get("value") or dados.get("price") or 10
            
            lista_itens.append({
                "id": item_id,
                "nome": dados.get("display_name", item_id.replace("_", " ").title()),
                "descricao": dados.get("description", "Um misterioso item de Eldora."),
                "raridade": str(dados.get("rarity", "comum")).capitalize(),
                "preco": preco_venda,
                "emoji": dados.get("emoji", "📦"),
                "imagem": f"/static/items/{item_id}.webp",
                "wiki_tab": wiki_tab, # A aba principal
                "wiki_sub": wiki_sub  # A sub-aba (ex: guerreiro, mago)
            })
            
        lista_itens.sort(key=lambda x: x["nome"])
        return jsonify(lista_itens)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": str(e)}), 500

# ==========================================
# ROTA DA WIKI: REGIÕES E MAPAS
# ==========================================
@webapp_bp.route('/wiki/regioes')
def wiki_regioes():
    try:
        from modules.game_data.regions import REGIONS_DATA
        
        lista_regioes = []
        for regiao_id, dados in REGIONS_DATA.items():
            
            # Pega o nível mínimo da tupla level_range (ex: (15, 35) -> pega o 15)
            # Se a região não tiver level_range (como o Reino de Eldora), assume level 1
            level_range = dados.get("level_range", (1, 99))
            level_min = level_range[0] if isinstance(level_range, tuple) else 1
            
            lista_regioes.append({
                "id": regiao_id,
                "nome": dados.get("display_name", regiao_id.replace("_", " ").title()),
                "emoji": dados.get("emoji", "🗺️"),
                "descricao": dados.get("description", "Uma região inexplorada de Eldora."),
                "level_min": level_min,
                # O wiki.js vai tentar carregar essa imagem jpg. Se falhar, mostra o emoji!
                "imagem": f"/static/regions/{regiao_id}.jpg" 
            })
            
        # Ordena a lista do mapa por nível de dificuldade (do mais fácil pro mais difícil)
        lista_regioes.sort(key=lambda x: x["level_min"])
        
        return jsonify(lista_regioes)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": str(e)}), 500
    
@webapp_bp.route('/api/personagem/desequipar', methods=['POST'])
def api_desequipar_item():
    try:
        data = request.json
        from modules.player.inventory import unequip_item_for_user
        sucesso, msg = _run_async(unequip_item_for_user(data.get("user_id"), data.get("slot")))
        if sucesso: return jsonify({"sucesso": True, "msg": msg})
        return jsonify({"erro": msg}), 400
    except Exception as e: return jsonify({"erro": str(e)}), 500