# modules/missoes.py
from bson import ObjectId
from modules.player.core import users_collection

# ==========================================
# 📜 CATÁLOGO DE MISSÕES DO REINO DE ELDORA
# ==========================================
# modules/missoes.py

QUESTS_DATA = {
    # 1. O Despertar (Nível 5)
    "q4_selene_classe": {
        "titulo": "O Despertar da Centelha",
        "npc": "selene_arquimaga",
        "level_req": 5,
        "pre_req": None,
        "objetivo": "Sua alma despertou. Fale com a Selene para abraçar seu destino.",
        "req_itens": {},
        "recompensas": {}
    },
    
    ## 2. A Forja do Destino (Nível 7)
    "q5_thorek_profissao": {
        "titulo": "A Voz do Aço e da Terra",
        "npc": "thorek_mestre",
        "level_req": 7,
        "pre_req": "q4_selene_classe",
        "objetivo": "Escolha um ofício com Thorek e receba o seu Kit de Ferramentas Iniciante.",
        "req_itens": {},
        "recompensas": {"xp": 300, "gold": 200}
    },

    # 3. O SELO DO GRIMÓRIO (Nível 17 - A LONGA JORNADA)
    "q6_selene_grimorio": {
        "titulo": "A Provação do Conhecimento Proibido",
        "npc": "selene_arquimaga",
        "level_req": 17,
        "pre_req": "q5_thorek_profissao",
        "objetivo": "Sobreviva à Floresta Sombria. Traga 15 Ectoplasmas e 30 Couro de lobo Alfa para Selene.",
        "req_itens": {"ectoplasma": 15, "couro_de_lobo_alfa": 30},
        "recompensas": {"xp": 1000, "gold": 500} # A Skill será injetada via npc.py
    },
    
    # 4. A Proxima Etapa (Nível 15)
    "q7_selene_guildas": {
        "titulo": "O Reconhecimento da Capital",
        "npc": "selene_arquimaga",
        "level_req": 20,
        "pre_req": "q6_selene_grimorio",
        "objetivo": "Prove que dominou suas novas artes. Selene emitirá sua Carta de Recomendação.",
        "req_itens": {},
        "recompensas": {
            "xp": 2000, 
            "gold": 1500, 
            "itens": {"carta_recomendacao": 1}
        }
    }
}

# ==========================================
# ⚙️ MOTOR DE PROCESSAMENTO DE MISSÕES
# ==========================================

def obter_status_npc(player_data: dict, npc_id: str) -> dict:
    """
    Verifica o banco de dados do jogador e descobre quais missões 
    aquele NPC específico tem para oferecer ou concluir.
    """
    my_level = player_data.get("level", 1)
    my_quests = player_data.get("quests") or {}
    my_inv = player_data.get("inventory") or {}
    
    missoes_disponiveis = []
    missoes_concluidas = []
    
    for q_id, q_data in QUESTS_DATA.items():
        if q_data["npc"] != npc_id:
            continue
            
        status_atual = my_quests.get(q_id, {}).get("status")
        
        # Se já resgatou, ignora
        if status_atual == "resgatada":
            continue
            
        # Verifica Pré-requisito (se a missão anterior já foi feita)
        pre_req = q_data.get("pre_req")
        if pre_req and my_quests.get(pre_req, {}).get("status") != "resgatada":
            continue
            
        # Verifica se tem nível mínimo
        if my_level < q_data["level_req"]:
            continue
            
        # Se a missão já está ativa, verifica se o jogador tem os itens no inventário para entregar
        if status_atual == "ativa":
            pode_entregar = True
            for item_req, qtd_req in q_data.get("req_itens", {}).items():
                if int(my_inv.get(item_req, 0)) < qtd_req:
                    pode_entregar = False
                    break
            
            if pode_entregar:
                missoes_concluidas.append({"id": q_id, "data": q_data})
        else:
            # Se não está ativa e passou nos requisitos, pode aceitar!
            missoes_disponiveis.append({"id": q_id, "data": q_data})
            
    return {
        "disponiveis": missoes_disponiveis,
        "prontas_para_entrega": missoes_concluidas
    }

def aceitar_missao(user_id: str, quest_id: str) -> dict:
    """Registra a missão como 'ativa' no banco de dados do jogador."""
    q_data = QUESTS_DATA.get(quest_id)
    if not q_data:
        return {"success": False, "error": "Missão não encontrada nas lendas."}
        
    users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$set": {
                f"quests.{quest_id}": {
                    "titulo": q_data["titulo"],
                    "objetivo": q_data["objetivo"],
                    "status": "ativa"
                }
            }
        }
    )
    return {"success": True, "message": f"Missão Aceita: {q_data['titulo']}"}

def entregar_missao(user_id: str, player_data: dict, quest_id: str) -> dict:
    """Consome os itens do inventário, entrega recompensas e marca como resgatada."""
    q_data = QUESTS_DATA.get(quest_id)
    if not q_data:
        return {"success": False, "error": "Missão não encontrada."}
        
    my_inv = player_data.get("inventory") or {}
    
    # 1. Validação de Segurança Dupla (Garante que não vai entregar sem ter os itens)
    for item_req, qtd_req in q_data.get("req_itens", {}).items():
        if int(my_inv.get(item_req, 0)) < qtd_req:
            return {"success": False, "error": f"Falta material: {item_req}"}
            
    # 2. Consome os itens do inventário
    update_query = {"$set": {}, "$inc": {}}
    
    for item_req, qtd_req in q_data.get("req_itens", {}).items():
        update_query["$inc"][f"inventory.{item_req}"] = -qtd_req
        
    # 3. Adiciona as Recompensas
    recompensas = q_data.get("recompensas", {})
    if "xp" in recompensas:
        update_query["$inc"]["xp"] = recompensas["xp"]
    if "gold" in recompensas:
        update_query["$inc"]["gold"] = recompensas["gold"]
        
    # Se a missão der itens (como a Carta de Recomendação)
    if "itens" in recompensas:
        for item_ganho, qtd_ganha in recompensas["itens"].items():
            update_query["$inc"][f"inventory.{item_ganho}"] = qtd_ganha
            
    # 4. Muda o Status da Missão para Finalizada
    update_query["$set"][f"quests.{quest_id}.status"] = "resgatada"
    
    # Limpeza caso o $inc ou $set fiquem vazios (Evita erro no MongoDB)
    if not update_query["$inc"]:
        del update_query["$inc"]
    if not update_query["$set"]:
        del update_query["$set"]

    users_collection.update_one({"_id": ObjectId(user_id)}, update_query)
    
    return {
        "success": True, 
        "message": f"Missão Concluída! Você recebeu suas recompensas.",
        "recompensas_entregues": recompensas
    }

    