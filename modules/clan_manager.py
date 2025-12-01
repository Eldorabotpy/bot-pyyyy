# modules/clan_manager.py
# (VERSÃO FINAL CORRIGIDA: SINTAXE DO MONGODB AJUSTADA)

import os
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict, Any
from pymongo import MongoClient, ReturnDocument
import certifi

from modules.game_data.clans import CLAN_PRESTIGE_LEVELS, CLAN_CONFIG

logger = logging.getLogger(__name__)

# ==============================================================================
# CONFIGURAÇÃO BLINDADA DO MONGODB
# ==============================================================================
MONGO_STR = os.getenv("MONGO_CONNECTION_STRING") or "mongodb+srv://eldora-cluster:pb060987@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
clans_col = None

try:
    client = MongoClient(MONGO_STR, tlsCAFile=certifi.where())
    db = client["eldora_db"]
    clans_col = db["clans"]
    
    # Cria índice para garantir que nomes de clãs sejam únicos
    clans_col.create_index("name_lower", unique=True)
    logger.info("✅ [CLAN MANAGER] Conectado ao MongoDB Atlas.")
except Exception as e:
    logger.critical(f"❌ [CLAN MANAGER] Falha crítica na conexão: {e}")
    clans_col = None

# ==============================================================================
# HELPERS
# ==============================================================================

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def _generate_clan_id() -> str:
    return f"clan_{uuid.uuid4().hex[:8]}"

# ==============================================================================
# FUNÇÕES DE LEITURA (GETTERS)
# ==============================================================================

async def get_clan(clan_id: str) -> Optional[dict]:
    """Busca os dados de um clã pelo ID."""
    if clans_col is None or not clan_id: return None
    return clans_col.find_one({"_id": clan_id})

async def find_clan_by_display_name(name: str) -> Optional[dict]:
    """Busca clã pelo nome (case-insensitive)."""
    if clans_col is None: return None
    return clans_col.find_one({"name_lower": name.strip().lower()})

# ==============================================================================
# FUNÇÕES DE GERENCIAMENTO (CRIAR, ENTRAR, SAIR)
# ==============================================================================

async def create_clan(leader_id: int, clan_name: str, payment_method: str = 'gold') -> str:
    """
    Cria um novo clã no banco de dados.
    Retorna o clan_id gerado ou levanta ValueError.
    """
    if clans_col is None: raise ValueError("Banco de dados offline.")
    
    # Verifica nome duplicado
    name_clean = clan_name.strip()
    if clans_col.find_one({"name_lower": name_clean.lower()}):
        raise ValueError(f"O nome '{name_clean}' já está em uso.")

    clan_id = _generate_clan_id()
    
    new_clan = {
        "_id": clan_id,
        "name": name_clean,
        "name_lower": name_clean.lower(),
        "display_name": name_clean,
        "leader_id": int(leader_id),
        "created_at": _now_iso(),
        "level": 1,
        "xp": 0,
        "prestige_level": 1,
        "prestige_points": 0,
        "bank": 0, # Saldo de Ouro
        "members": [int(leader_id)],
        "max_members": 10, # Valor inicial
        "pending_applications": [],
        "bank_log": [],
        "buffs": {},
        "active_mission": None,
        "logo_media_key": None
    }
    
    # Pagamento já foi descontado pelo handler antes de chamar aqui (idealmente)
    # Mas se quiser reforçar, pode adicionar lógica de player_manager aqui.
    
    clans_col.insert_one(new_clan)
    logger.info(f"[CLAN] Novo clã criado: {name_clean} ({clan_id}) por {leader_id}")
    return clan_id

async def add_application(clan_id: str, user_id: int):
    """Adiciona um jogador à lista de espera."""
    clan = await get_clan(clan_id)
    if not clan: raise ValueError("Clã não encontrado.")
    
    if user_id in clan.get("members", []):
        raise ValueError("Você já é membro deste clã.")
        
    if user_id in clan.get("pending_applications", []):
        raise ValueError("Você já enviou um pedido para este clã.")
        
    clans_col.update_one(
        {"_id": clan_id},
        {"$push": {"pending_applications": int(user_id)}}
    )

async def accept_application(clan_id: str, applicant_id: int):
    """Aceita um membro (Move de pending para members)."""
    clan = await get_clan(clan_id)
    if not clan: raise ValueError("Clã inválido.")
    
    if len(clan.get("members", [])) >= clan.get("max_members", 10):
        raise ValueError("O clã está lotado! Aumente o nível para recrutar mais.")
        
    clans_col.update_one(
        {"_id": clan_id},
        {
            "$pull": {"pending_applications": int(applicant_id)},
            "$addToSet": {"members": int(applicant_id)}
        }
    )

async def decline_application(clan_id: str, applicant_id: int):
    """Recusa um membro."""
    clans_col.update_one(
        {"_id": clan_id},
        {"$pull": {"pending_applications": int(applicant_id)}}
    )

async def remove_member(clan_id: str, user_id: int, kicked_by_leader: bool = True):
    """Remove um membro do clã."""
    clan = await get_clan(clan_id)
    if not clan: raise ValueError("Clã não encontrado.")
    
    if int(user_id) == int(clan.get("leader_id")):
        raise ValueError("O líder não pode sair/ser expulso. Transfira a liderança ou desfaça o clã.")
        
    clans_col.update_one(
        {"_id": clan_id},
        {"$pull": {"members": int(user_id)}}
    )

async def transfer_leadership(clan_id: str, old_leader_id: int, new_leader_id: int):
    """Passa a coroa para outro membro."""
    clan = await get_clan(clan_id)
    if int(new_leader_id) not in clan.get("members", []):
        raise ValueError("O novo líder deve ser um membro do clã.")
        
    clans_col.update_one(
        {"_id": clan_id},
        {"$set": {"leader_id": int(new_leader_id)}}
    )

async def set_clan_media(clan_id: str, user_id: int, media_data: dict):
    """Salva o file_id da logo do clã."""
    clans_col.update_one(
        {"_id": clan_id},
        {"$set": {
            "logo_media_key": f"clan_logo_{clan_id}", 
            "custom_logo_data": media_data 
        }}
    )

# ==============================================================================
# BANCO E ECONOMIA
# ==============================================================================

async def bank_deposit(clan_id: str, user_id: int, amount: int) -> Tuple[bool, str]:
    """Adiciona ouro ao banco do clã e registra log."""
    if amount <= 0: return False, "Valor inválido."
    
    try:
        clans_col.update_one(
            {"_id": clan_id},
            {
                "$inc": {"bank": amount, "prestige_points": int(amount * 0.01)}, 
                "$push": {
                    "bank_log": {
                        "$each": [{
                            "action": "depositou",
                            "player_id": user_id,
                            "player_name": f"ID {user_id}", # O handler pode melhorar isso
                            "amount": amount,
                            "timestamp": _now_iso()
                        }],
                        "$slice": -20 
                    }
                }
            }
        )
        return True, f"Depositado {amount} com sucesso!"
    except Exception as e:
        logger.error(f"Erro no depósito: {e}")
        return False, "Erro no banco de dados."

async def bank_withdraw(clan_id: str, user_id: int, amount: int) -> Tuple[bool, str]:
    """Retira ouro do banco do clã (apenas líder)."""
    clan = await get_clan(clan_id)
    if not clan: return False, "Clã não encontrado."
    
    if clan.get("leader_id") != user_id:
        return False, "Apenas o líder pode sacar."
        
    current_balance = clan.get("bank", 0)
    if current_balance < amount:
        return False, f"Saldo insuficiente (Atual: {current_balance})."
        
    clans_col.update_one(
        {"_id": clan_id},
        {
            "$inc": {"bank": -amount},
            "$push": {
                "bank_log": {
                    "$each": [{
                        "action": "sacou",
                        "player_id": user_id,
                        "player_name": "Líder",
                        "amount": amount,
                        "timestamp": _now_iso()
                    }],
                    "$slice": -20
                }
            }
        }
    )
    return True, f"Saque de {amount} realizado."

# ==============================================================================
# PROGRESSÃO E MISSÕES
# ==============================================================================

async def level_up_clan(clan_id: str, user_id: int, payment_method: str):
    """Tenta subir o nível de prestígio do clã e consome recursos."""
    clan = await get_clan(clan_id)
    if not clan: raise ValueError("Clã não encontrado.")
    
    current_lvl = clan.get("prestige_level", 1)
    current_pts = clan.get("prestige_points", 0)
    
    # Busca dados do próximo nível
    next_lvl_info = CLAN_PRESTIGE_LEVELS.get(current_lvl + 1)
    if not next_lvl_info:
        raise ValueError("Nível máximo atingido!")
        
    req_pts = next_lvl_info.get("points_to_next_level", 999999)
    cost = next_lvl_info.get("upgrade_cost", {})
    
    # 1. Verifica XP
    if current_pts < req_pts:
        raise ValueError(f"Faltam pontos de prestígio ({current_pts}/{req_pts}).")
        
    cost_val = cost.get(payment_method, 0)
    
    # 2. Verifica e Cobra o Custo Monetário (Gold/Dimas)
    update_query = {}
    
    if payment_method == 'gold':
        if clan.get("bank", 0) < cost_val:
            raise ValueError(f"Ouro insuficiente no cofre ({cost_val} necessários).")
        
        # Prepara a query para Ouro
        update_query = {
            "$inc": {
                "bank": -cost_val, 
                "prestige_level": 1,
                "prestige_points": -req_pts  # <--- CORREÇÃO CRÍTICA: Subtrai o XP usado!
            },
            "$set": {"max_members": next_lvl_info.get("max_members", 10)}
        }
        
    elif payment_method == 'dimas':
        # Nota: A cobrança de Dimas geralmente é feita no handler (do bolso do jogador),
        # então aqui só atualizamos o nível e o XP do clã.
        update_query = {
            "$inc": {
                "prestige_level": 1,
                "prestige_points": -req_pts # <--- CORREÇÃO CRÍTICA: Subtrai o XP usado!
            },
            "$set": {"max_members": next_lvl_info.get("max_members", 10)}
        }
    
    # 3. Executa a atualização
    clans_col.update_one({"_id": clan_id}, update_query)
    
    logger.info(f"[CLAN] Clã {clan_id} subiu para nível {current_lvl + 1} por {user_id}.")

async def get_active_guild_mission(clan_id: str) -> Optional[dict]:
    """Retorna a missão ativa do clã."""
    clan = await get_clan(clan_id)
    return clan.get("active_mission") if clan else None

async def purchase_mission_board(clan_id: str, user_id: int):
    """Compra o quadro de missões."""
    clan = await get_clan(clan_id)
    if clan.get("has_mission_board"):
        raise ValueError("O clã já possui o quadro.")
        
    cost = CLAN_CONFIG.get("mission_board_cost", {}).get("gold", 5000)
    
    if clan.get("bank", 0) < cost:
        raise ValueError(f"Ouro insuficiente no cofre ({cost}).")
        
    clans_col.update_one(
        {"_id": clan_id},
        {
            "$set": {"has_mission_board": True},
            "$inc": {"bank": -cost}
        }
    )

async def assign_mission_to_clan(clan_id: str, mission_id: str, user_id: int):
    """Define uma missão ativa para o clã."""
    from modules.game_data.guild_missions import GUILD_MISSIONS_CATALOG
    
    mission_template = GUILD_MISSIONS_CATALOG.get(mission_id)
    if not mission_template: raise ValueError("Missão inválida.")
    
    # [CORREÇÃO] Agora copiamos TODOS os campos essenciais para o Mission Manager funcionar
    active_mission = {
        "id": mission_id,
        "title": mission_template["title"],
        "type": mission_template["type"], # <--- ESSENCIAL!
        "target_monster_id": mission_template.get("target_monster_id"), # <--- ESSENCIAL!
        "target_item_id": mission_template.get("target_item_id"),       # <--- Para missões de coleta
        "target_count": mission_template["target_count"],
        "current_progress": 0,
        "start_date": _now_iso(),
        "rewards": mission_template["rewards"],
        "description": mission_template.get("description", ""),
        "completed": False # <--- Marcador para evitar contar depois de pronta
    }
    
    clans_col.update_one(
        {"_id": clan_id},
        {"$set": {"active_mission": active_mission}}
    )

async def set_active_mission(clan_id: str, mission_data: dict):
    """
    Salva uma estrutura de missão completa diretamente no clã.
    Usado pelo sistema de sorteio de missões (missions.py).
    """
    if clans_col is None: return
    
    clans_col.update_one(
        {"_id": clan_id},
        {"$set": {"active_mission": mission_data}}
    )

# Add this function to modules/clan_manager.py

async def update_guild_mission_progress(user_id: int, action_type: str, target_id: str, quantity: int = 1):
    """
    Atualiza o progresso da missão do clã se a ação corresponder.
    Chamado pelo sistema de combate/coleta.
    """
    # 1. Busca o clã do jogador
    # Precisamos importar player_manager aqui dentro para evitar ciclo, ou assumir que quem chama já sabe o clan_id.
    # Como a assinatura pede user_id, vamos buscar o clã.
    from modules import player_manager
    pdata = await player_manager.get_player_data(user_id)
    if not pdata or not pdata.get("clan_id"):
        return

    clan_id = pdata.get("clan_id")
    clan = await get_clan(clan_id)
    if not clan: return

    mission = clan.get("active_mission")
    if not mission or mission.get("completed"):
        return

    # 2. Verifica se a ação bate com a missão
    # Normaliza tipos para comparação (ex: 'HUNT' vs 'hunt')
    mission_type = str(mission.get("type", "")).upper()
    action_type = str(action_type).upper()

    match = False
    
    # Caso Caçada (HUNT)
    if mission_type == 'HUNT' and action_type == 'HUNT':
        # Verifica se o monstro é o alvo
        target_monster = mission.get("target_monster_id")
        if target_monster == target_id:
            match = True
            
    # Caso Coleta (COLLECT) - Se houver no futuro
    elif mission_type == 'COLLECT' and action_type == 'COLLECT':
        target_item = mission.get("target_item_id")
        if target_item == target_id:
            match = True

    # 3. Se deu match, atualiza o banco
    if match:
        # Incrementa progresso
        new_progress = mission.get("current_progress", 0) + quantity
        
        # Verifica se completou (mas não finaliza, deixa pro líder)
        # target_count = mission.get("target_count", 1)
        # is_complete = new_progress >= target_count
        
        clans_col.update_one(
            {"_id": clan_id},
            {"$inc": {"active_mission.current_progress": quantity}}
        )
        
        # Opcional: Logar ou avisar
        # logger.info(f"Progresso de clã atualizado: {clan_id} (+{quantity})")
        #     
async def delete_clan(clan_id: str, leader_id: int):
    """
    Apaga permanentemente um clã e remove os membros.
    """
    clan = await get_clan(clan_id)
    if not clan: 
        raise ValueError("Clã não encontrado.")
    
    if int(clan.get("leader_id")) != int(leader_id):
        raise ValueError("Apenas o líder pode dissolver o clã.")

    # 1. Remove o documento do Clã
    clans_col.delete_one({"_id": clan_id})

    # 2. Remove o clan_id de TODOS os jogadores que estavam nele
    # (Usa a collection de players do mesmo database)
    db["players"].update_many(
        {"clan_id": clan_id},
        {"$set": {"clan_id": None}}
    )
    
    logger.info(f"[CLAN] Clã {clan_id} foi deletado pelo líder {leader_id}.")