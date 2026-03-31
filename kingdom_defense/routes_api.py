# Arquivo: kingdom_defense/routes_api.py
import asyncio
from flask import Blueprint, jsonify, request
from bson.objectid import ObjectId

# Importações do seu sistema
from modules import player_manager
from modules.player.core import users_collection
from kingdom_defense.engine import event_manager

# Criando o Blueprint (O nosso "mini api.py" isolado)
kd_api_bp = Blueprint('kd_api', __name__)

# Ferramenta para rodar funções assíncronas do Telegram no Flask
def _run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(coro)
        loop.close()
        return res

# ==========================================
# ROTA SECRETA DE DEBUG: FORÇAR EVENTO ON
# ==========================================
@kd_api_bp.route('/api/debug/ligar_defesa', methods=['GET'])
def ligar_defesa_debug():
    _run_async(event_manager.start_event())
    users_collection.database["server_state"].update_one(
        {"_id": "eventos_ativos"},
        {"$set": {"defesa_reino": True}},
        upsert=True
    )
    return jsonify({"msg": "🔥 EVENTO DE DEFESA ATIVADO COM SUCESSO! Pode ir pro site testar!"})

# ==========================================
# ROTA: INICIAR DEFESA DO REINO (WEB APP)
# ==========================================
@kd_api_bp.route('/api/defesa_reino/iniciar', methods=['POST'])
def api_defesa_reino_iniciar():
    dados = request.json
    user_id = dados.get("user_id")

    try:
        busca_id = ObjectId(user_id)
        pdata = users_collection.find_one({"_id": busca_id})
        if not pdata: return jsonify({"erro": "Personagem não encontrado"})

        inventario = pdata.get("inventory", {})
        ticket_item = inventario.get("ticket_defesa_reino", 0)
        tickets = ticket_item.get("quantity", 0) if isinstance(ticket_item, dict) else ticket_item

        if tickets <= 0:
            return jsonify({"erro": "Você não tem Tickets de Defesa do Reino! Colete no menu inicial."})

        if not event_manager.is_active:
            return jsonify({"erro": "Os portões estão seguros. O evento não está ativo no momento."})

        if isinstance(inventario.get("ticket_defesa_reino"), dict):
            pdata["inventory"]["ticket_defesa_reino"]["quantity"] -= 1
        else:
            pdata["inventory"]["ticket_defesa_reino"] -= 1

        _run_async(player_manager.save_player_data(busca_id, pdata))
        status = _run_async(event_manager.add_player_to_event(str(busca_id), pdata))

        if status == "active":
            bdata = event_manager.get_battle_data(str(busca_id))
            is_boss = bdata["current_mob"].get("is_boss", False)
            mob_hp = event_manager.boss_global_hp if is_boss else bdata["current_mob"]["hp"]
            mob_max_hp = event_manager.boss_max_hp if is_boss else bdata["current_mob"]["max_hp"]

            return jsonify({
                "sucesso": True,
                "status": "active",
                "player_hp": bdata.get("player_hp"),
                "player_mp": bdata.get("player_mp"),
                "player_max_hp": bdata.get("player_max_hp"),
                "player_max_mp": bdata.get("player_max_mp"),
                "mob_nome": bdata["current_mob"]["name"],
                "mob_hp": mob_hp,
                "mob_max_hp": mob_max_hp,
                "wave": bdata.get("current_wave", 1),
                "is_boss": is_boss
            })
            
        elif status == "waiting":
            return jsonify({"sucesso": True, "status": "waiting", "fila": event_manager.get_queue_status_text()})
            
        else:
            return jsonify({"erro": "Você já está na batalha ou houve um erro de conexão."})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": f"Falha crítica: {str(e)}"}), 500

# ==========================================
# ROTA: AÇÃO NA DEFESA DO REINO (WEB APP)
# ==========================================
@kd_api_bp.route('/api/defesa_reino/acao', methods=['POST'])
def api_defesa_reino_acao():
    dados = request.json
    user_id = dados.get("user_id")
    acao = dados.get("acao", "atacar")
    
    try:
        busca_id = ObjectId(user_id)
        pdata = users_collection.find_one({"_id": busca_id})
        if not pdata: return jsonify({"erro": "Personagem não encontrado"})

        if str(busca_id) not in event_manager.active_fighters:
            return jsonify({"erro": "Você não está em uma batalha ativa no momento!"})

        total_stats = _run_async(player_manager.get_player_total_stats(pdata))

        if acao == "atacar":
            result = _run_async(event_manager.process_player_attack(str(busca_id), pdata, total_stats))
        else:
            return jsonify({"erro": "Ação de magia será implementada em breve!"})

        if "error" in result:
            return jsonify({"erro": result["error"]})

        bdata = event_manager.get_battle_data(str(busca_id))
        mob_hp = 0
        if bdata:
            is_boss = bdata["current_mob"].get("is_boss", False)
            mob_hp = event_manager.boss_global_hp if is_boss else bdata["current_mob"]["hp"]

        return jsonify({
            "sucesso": True,
            "log": result.get("action_log", "Ataque realizado!"),
            "game_over": result.get("game_over", False),
            "monster_defeated": result.get("monster_defeated", False),
            "event_over": result.get("event_over", False),
            "loot": result.get("loot_message", ""),
            "player_hp": bdata.get("player_hp", 0) if bdata else 0,
            "player_mp": bdata.get("player_mp", 0) if bdata else 0,
            "mob_hp": mob_hp
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": f"Erro no combate: {str(e)}"}), 500