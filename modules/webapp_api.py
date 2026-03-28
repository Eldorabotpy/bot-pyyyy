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

        # 1. Busca Segura do Personagem
        busca_id = ObjectId(user_id) if len(str(user_id)) == 24 else int(user_id) if str(user_id).isdigit() else user_id
        pdata = users_collection.find_one({"$or": [{"_id": busca_id}, {"last_chat_id": busca_id}, {"telegram_id_owner": busca_id}, {"telegram_id": busca_id}]})
        
        if not pdata:
            return jsonify({"erro": "Personagem não encontrado."}), 404
        
        lvl = int(pdata.get("level", 1))
        xp_visual_max = int(200 + (100 * (lvl - 1)) + (40 * (lvl - 1) * (lvl - 1))) 
        classe_str = str(pdata.get("class", "aprendiz"))
        
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

        # Retorno unificado para o Frontend (Perfil e Combate)
        return jsonify({
            "nome": pdata.get("character_name", "Aventureiro"), 
            "level": lvl, "gold": pdata.get("gold", 0), "gems": pdata.get("gems", 0),
            "classe": classe_str.capitalize(), "xp": int(pdata.get("xp", 0)), "xp_max": xp_visual_max,
            "hp_atual": hp_atual, "hp_max": hp_max, 
            "mp_atual": mp_atual, "mp_max": mp_max,
            "energy": pdata.get("energy", 0), "pontos_livres": pdata.get("stat_points", 0), 
            "avatar": get_class_avatar(classe_str), "status": status_formatados,
            "inventario": inventario_formatado, "equipamentos": equip_formatado,
            "esquiva": esquiva, "atk_duplo": atk_duplo, "prof_nome": prof_nome, "prof_lvl": prof_lvl
        })

    except Exception as e: 
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
        stat = data.get("stat")

        from modules.player.core import users_collection
        from modules import player_manager

        busca_id = ObjectId(user_id) if len(str(user_id)) == 24 else int(user_id) if str(user_id).isdigit() else user_id
        pdata = users_collection.find_one({"$or": [{"_id": busca_id}, {"last_chat_id": busca_id}, {"telegram_id_owner": busca_id}, {"telegram_id": busca_id}]})
        
        if not pdata: return jsonify({"erro": "Personagem não encontrado."}), 404

        pontos_livres = int(pdata.get("stat_points", 0))
        if pontos_livres <= 0: return jsonify({"erro": "Não tens pontos disponíveis!"}), 400

        base_stats = pdata.get("base_stats", {})
        base_stats[stat] = int(base_stats.get(stat, 0)) + 1
        pdata["base_stats"] = base_stats
        pdata["stat_points"] = pontos_livres - 1

        _run_async(player_manager.save_player_data(user_id, pdata))
        return jsonify({"sucesso": True, "msg": "Ponto adicionado!"})
    except Exception as e:
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


@webapp_bp.route('/api/personagem/desequipar', methods=['POST'])
def api_desequipar_item():
    try:
        data = request.json
        from modules.player.inventory import unequip_item_for_user
        sucesso, msg = _run_async(unequip_item_for_user(data.get("user_id"), data.get("slot")))
        if sucesso: return jsonify({"sucesso": True, "msg": msg})
        return jsonify({"erro": msg}), 400
    except Exception as e: return jsonify({"erro": str(e)}), 500