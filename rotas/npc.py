# rotas/npc.py
from flask import Blueprint, request, jsonify
from bson import ObjectId
from modules.player.core import users_collection
from modules.missoes import obter_status_npc, aceitar_missao, entregar_missao

npc_bp = Blueprint('npc_bp', __name__)

# ==========================================
# 🗣️ ROTA 1: VERIFICAR STATUS DO NPC
# ==========================================
# O jogo chama essa rota quando você clica na Selene para saber se tem missão com ela.
@npc_bp.route('/api/npc/<npc_id>/status', methods=['GET'])
def npc_status(npc_id):
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "O pergaminho de identidade (User ID) está em branco."}), 400
        
    player = users_collection.find_one({"_id": ObjectId(user_id)})
    if not player:
        return jsonify({"success": False, "error": "Herói não encontrado nas lendas de Eldora."}), 404
        
    # Pergunta pro nosso motor de missões o que esse NPC tem pro jogador
    status = obter_status_npc(player, npc_id)
    
    return jsonify({
        "success": True, 
        "npc_id": npc_id, 
        "status": status
    })

# ==========================================
# 📜 ROTA 2: ACEITAR UMA MISSÃO
# ==========================================
@npc_bp.route('/api/npc/missao/aceitar', methods=['POST'])
def npc_aceitar_missao():
    data = request.get_json()
    user_id = data.get('user_id')
    quest_id = data.get('quest_id')
    
    if not user_id or not quest_id:
        return jsonify({"success": False, "error": "Magia falhou. Faltam dados da missão."}), 400
        
    resultado = aceitar_missao(user_id, quest_id)
    return jsonify(resultado)

# ==========================================
# 💰 ROTA 3: ENTREGAR MISSÃO E PEGAR RECOMPENSA
# ==========================================
@npc_bp.route('/api/npc/missao/entregar', methods=['POST'])
def npc_entregar_missao():
    data = request.get_json()
    user_id = data.get('user_id')
    quest_id = data.get('quest_id')
    
    if not user_id or not quest_id:
        return jsonify({"success": False, "error": "Magia falhou. Faltam dados da missão."}), 400
        
    player = users_collection.find_one({"_id": ObjectId(user_id)})
    if not player:
        return jsonify({"success": False, "error": "Herói não encontrado."}), 404
        
    # Executa a entrega consumindo os itens e dando o ouro/xp/carta de recomendação
    resultado = entregar_missao(user_id, player, quest_id)
    # 🌟 LÓGICA ESPECIAL DA PRIMEIRA SKILL 🌟
    if resultado.get("success") and quest_id == "q6_selene_grimorio":
        classe_do_player = player.get("class", "aventureiro").lower()
        
        # Mapa de skills baseado no seu skills.py
        skills_iniciais = {
            "guerreiro": "guerreiro_corte_perfurante",
            "mago": "mago_bola_de_fogo",
            "cacador": "cacador_flecha_precisa",
            "assassino": "assassino_ataque_furtivo",
            "monge": "monge_rajada_de_punhos",
            "samurai": "samurai_corte_iaijutsu",
            "berserker": "berserker_golpe_selvagem",
            "curandeiro": "curandeiro_chama_sagrada",
            "bardo": "bardo_nota_cortante"
        }
        
        skill_id = skills_iniciais.get(classe_do_player)
        
        if skill_id:
            # Injeta a skill desbloqueada no banco de dados
            users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        f"skills_desbloqueadas.{skill_id}": {"rarity": "comum", "level": 1},
                        f"database_skills.{skill_id}": {"rarity": "comum", "level": 1}
                    }
                }
            )
            resultado["message"] += " A Arquimaga quebrou os selos... Você aprendeu sua primeira habilidade!"

    return jsonify(resultado)

# ==========================================
# ✨ ROTA 4: DESPERTAR DE CLASSE (ESPECIAL Q4)
# ==========================================
@npc_bp.route('/api/npc/missao/despertar', methods=['POST'])
def npc_despertar_classe():
    data = request.get_json()
    user_id = data.get('user_id')
    quest_id = data.get('quest_id')
    nova_classe = data.get('nova_classe')
    
    if not user_id or not quest_id or not nova_classe:
        return jsonify({"success": False, "error": "Faltam componentes do feitiço."}), 400
        
    player = users_collection.find_one({"_id": ObjectId(user_id)})
    if not player:
        return jsonify({"success": False, "error": "Herói não encontrado."}), 404
        
    # 1. Muda a classe do jogador no banco
    # 2. Marca a q4_selene_classe como resgatada
    users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$set": {
                "class": nova_classe,
                f"quests.{quest_id}.status": "resgatada"
            }
        }
    )
    
    return jsonify({"success": True, "message": f"Você despertou como {nova_classe.capitalize()}!"})
