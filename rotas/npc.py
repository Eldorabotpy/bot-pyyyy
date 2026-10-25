# rotas/npc.py
from flask import Blueprint, request, jsonify
from bson import ObjectId
from modules.player.core import users_collection
from modules.missoes import obter_status_npc, aceitar_missao, entregar_missao, registrar_decisao_jornada

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
        
    resultado = aceitar_missao(
        user_id,
        quest_id,
        data.get('escolha_id'),
    )
    return jsonify(resultado)


@npc_bp.route('/api/npc/missao/decidir', methods=['POST'])
def npc_decidir_jornada():
    data = request.get_json() or {}
    user_id = data.get('user_id')
    etapa = data.get('etapa')
    escolha_id = data.get('escolha_id')
    if not user_id or not etapa or not escolha_id:
        return jsonify({"success": False, "error": "Faltam dados para registrar sua decisão."}), 400
    resultado = registrar_decisao_jornada(user_id, etapa, escolha_id)
    return jsonify(resultado), (200 if resultado.get("success") else 400)

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
        from modules.skill_progression import Q6_INITIAL_SKILLS_BY_CLASS
        skills_iniciais = Q6_INITIAL_SKILLS_BY_CLASS
        
        skill_id = skills_iniciais.get(classe_do_player)
        
        if skill_id:
            skill_instancia = {"unlocked": True, "rarity": "comum", "level": 1}
            skills_jogador = player.get("skills", {})
            skills_jogador = dict(skills_jogador) if isinstance(skills_jogador, dict) else {}
            skills_jogador[skill_id] = skill_instancia
            skills_desbloqueadas = player.get("skills_desbloqueadas", {})
            skills_desbloqueadas = dict(skills_desbloqueadas) if isinstance(skills_desbloqueadas, dict) else {}
            skills_desbloqueadas[skill_id] = skill_instancia
            database_skills = player.get("database_skills", {})
            database_skills = dict(database_skills) if isinstance(database_skills, dict) else {}
            database_skills[skill_id] = skill_instancia
            # Injeta a skill desbloqueada no banco de dados
            users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "skills_desbloqueadas": skills_desbloqueadas,
                        "database_skills": database_skills,
                        "skills": skills_jogador,
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

    from modules.game_data.classes import CLASSES_DATA
    nova_classe = str(nova_classe or "").strip().lower()
    if quest_id != "q4_selene_classe" or nova_classe not in CLASSES_DATA or int(player.get("level", 1) or 1) < 5:
        return jsonify({"success": False, "error": "O despertar exige uma classe válida, o Nível 5 e a etapa de Selene."}), 403
    quests = player.get("quests", {}) or {}
    if (quests.get("q3_varek_provacao", {}) or {}).get("status") != "resgatada":
        return jsonify({"success": False, "error": "Conclua a provação da caravana antes do despertar."}), 403
    classe_atual = str(player.get("class_key") or player.get("class") or player.get("classe") or "aventureiro").strip().lower()
    if classe_atual not in ("", "aventureiro", "aprendiz"):
        return jsonify({"success": False, "error": "Seu despertar de classe já foi concluído."}), 409

    if nova_classe == "necromante":
        caravana = quests.get("q3_varek_provacao", {}) or {}
        caminho_revelado = (
            caravana.get("status") == "resgatada"
            and caravana.get("decisao_alma") == "escutar"
            and caravana.get("decisao_foco") == "acolher"
        )
        if not caminho_revelado:
            return jsonify({
                "success": False,
                "error": "Selene ainda não reconhece a Centelha do Necromante na sua jornada."
            }), 403
        
    # 1. Muda a classe do jogador no banco
    # 2. Marca a q4_selene_classe como resgatada
    users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$set": {
                "class": nova_classe,
                "class_key": nova_classe,
                f"quests.{quest_id}.status": "resgatada"
            }
        }
    )
    
    return jsonify({"success": True, "message": f"Você despertou como {nova_classe.capitalize()}!"})
