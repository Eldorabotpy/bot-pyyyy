# modules/clan_manager.py
# (VERSÃO FINAL: COMPATÍVEL COM OBJECTID STRING E COLEÇÃO USERS)

import os
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict, Any, Union
from pymongo import MongoClient, ReturnDocument
import certifi

from modules.game_data.clans import CLAN_PRESTIGE_LEVELS, CLAN_CONFIG

logger = logging.getLogger(__name__)

# ==============================================================================
# CONFIGURAÇÃO BLINDADA DO MONGODB
# ==============================================================================
MONGO_STR = "mongodb+srv://eldora-cluster:pb060987@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
clans_col = None
users_col = None # Referência para limpar vínculo ao deletar clã

try:
    client = MongoClient(MONGO_STR, tlsCAFile=certifi.where())
    db = client["eldora_db"]
    clans_col = db["clans"]
    users_col = db["users"] # Coleção nova de jogadores
    
    # Cria índice para garantir que nomes de clãs sejam únicos
    clans_col.create_index("name_lower", unique=True)
    logger.info("✅ [CLAN MANAGER] Conectado ao MongoDB Atlas (Clans + Users).")
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

def _ensure_str(value: Any) -> str:
    """Garante que IDs sejam strings para compatibilidade com ObjectId."""
    return str(value)

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

async def create_clan(leader_id: Union[str, int], clan_name: str, payment_method: str = 'gold') -> str:
    """
    Cria um novo clã no banco de dados.
    Retorna o clan_id gerado.
    """
    if clans_col is None: raise ValueError("Banco de dados offline.")
    
    leader_id_str = _ensure_str(leader_id)
    
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
        "leader_id": leader_id_str, # String
        "created_at": _now_iso(),
        "level": 1,
        "xp": 0,
        "prestige_level": 1,
        "prestige_points": 0,
        "bank": 0, 
        "members": [leader_id_str], # Lista de Strings
        "max_members": 10,
        "pending_applications": [],
        "bank_log": [],
        "buffs": {},
        "active_mission": None,
        "logo_media_key": None
    }
    
    clans_col.insert_one(new_clan)
    logger.info(f"[CLAN] Novo clã criado: {name_clean} ({clan_id}) por {leader_id_str}")
    return clan_id

async def add_application(clan_id: str, user_id: Union[str, int]):
    """Adiciona um jogador à lista de espera."""
    user_id_str = _ensure_str(user_id)
    clan = await get_clan(clan_id)
    if not clan: raise ValueError("Clã não encontrado.")
    
    # Verifica em strings
    members = [_ensure_str(m) for m in clan.get("members", [])]
    if user_id_str in members:
        raise ValueError("Você já é membro deste clã.")
        
    pending = [_ensure_str(p) for p in clan.get("pending_applications", [])]
    if user_id_str in pending:
        raise ValueError("Você já enviou um pedido para este clã.")
        
    clans_col.update_one(
        {"_id": clan_id},
        {"$push": {"pending_applications": user_id_str}}
    )

async def accept_application(clan_id: str, applicant_id: Union[str, int]):
    """Aceita um membro (Move de pending para members)."""
    app_id_str = _ensure_str(applicant_id)
    
    clan = await get_clan(clan_id)
    if not clan: raise ValueError("Clã inválido.")
    
    if len(clan.get("members", [])) >= clan.get("max_members", 10):
        raise ValueError("O clã está lotado! Aumente o nível para recrutar mais.")
        
    clans_col.update_one(
        {"_id": clan_id},
        {
            "$pull": {"pending_applications": app_id_str},
            "$addToSet": {"members": app_id_str}
        }
    )

async def decline_application(clan_id: str, applicant_id: Union[str, int]):
    """Recusa um membro."""
    app_id_str = _ensure_str(applicant_id)
    clans_col.update_one(
        {"_id": clan_id},
        {"$pull": {"pending_applications": app_id_str}}
    )

async def remove_member(clan_id: str, user_id: Union[str, int], kicked_by_leader: bool = True):
    """Remove um membro do clã."""
    user_id_str = _ensure_str(user_id)
    
    clan = await get_clan(clan_id)
    if not clan: raise ValueError("Clã não encontrado.")
    
    if user_id_str == _ensure_str(clan.get("leader_id")):
        raise ValueError("O líder não pode sair/ser expulso. Transfira a liderança ou desfaça o clã.")
        
    clans_col.update_one(
        {"_id": clan_id},
        {"$pull": {"members": user_id_str}}
    )

async def transfer_leadership(clan_id: str, old_leader_id: Union[str, int], new_leader_id: Union[str, int]):
    """Passa a coroa para outro membro."""
    new_leader_str = _ensure_str(new_leader_id)
    
    clan = await get_clan(clan_id)
    
    # Normaliza lista de membros para verificação
    members_str = [_ensure_str(m) for m in clan.get("members", [])]
    
    if new_leader_str not in members_str:
        raise ValueError("O novo líder deve ser um membro do clã.")
        
    clans_col.update_one(
        {"_id": clan_id},
        {"$set": {"leader_id": new_leader_str}}
    )

async def set_clan_media(clan_id: str, user_id: str, media_data: dict):
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

async def bank_deposit(clan_id: str, user_id: Union[str, int], amount: int) -> Tuple[bool, str]:
    """Adiciona ouro ao banco do clã e registra log."""
    if amount <= 0: return False, "Valor inválido."
    user_id_str = _ensure_str(user_id)
    
    try:
        # Pega info do jogador para o log (opcional, pode ser só ID se falhar)
        player_name = f"ID {user_id_str}"
        try:
            from modules import player_manager
            pdata = await player_manager.get_player_data(user_id_str)
            if pdata: player_name = pdata.get("character_name", player_name)
        except: pass

        clans_col.update_one(
            {"_id": clan_id},
            {
                "$inc": {"bank": amount, "prestige_points": int(amount * 0.01)}, 
                "$push": {
                    "bank_log": {
                        "$each": [{
                            "action": "depositou",
                            "player_id": user_id_str,
                            "player_name": player_name,
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

async def bank_withdraw(clan_id: str, user_id: str, amount: int) -> Tuple[bool, str]:
    """Retira ouro do banco do clã (apenas líder)."""
    user_id_str = _ensure_str(user_id)
    clan = await get_clan(clan_id)
    if not clan: return False, "Clã não encontrado."
    
    if _ensure_str(clan.get("leader_id")) != user_id_str:
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
                        "player_id": user_id_str,
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

async def level_up_clan(clan_id: str, user_id: str, payment_method: str):
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
    
    # OBS: O custo em Ouro do player ou Dimas do player deve ser descontado no Handler.
    # Aqui descontamos do BANCO DO CLÃ se for ouro, ou apenas o XP se for Dimas (pago pelo player).
    
    if payment_method == 'gold':
        if clan.get("bank", 0) < cost_val:
            raise ValueError(f"Ouro insuficiente no cofre ({cost_val} necessários).")
        
        update_query = {
            "$inc": {
                "bank": -cost_val, 
                "prestige_level": 1,
                "prestige_points": -req_pts 
            },
            "$set": {"max_members": next_lvl_info.get("max_members", 10)}
        }
        
    elif payment_method == 'dimas':
        # O handler já cobrou os diamantes do usuário. Aqui só evoluímos.
        update_query = {
            "$inc": {
                "prestige_level": 1,
                "prestige_points": -req_pts 
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

async def assign_mission_to_clan(clan_id: str, mission_id: str, user_id: str):
    """Define uma missão ativa para o clã."""
    from modules.game_data.guild_missions import GUILD_MISSIONS_CATALOG
    
    mission_template = GUILD_MISSIONS_CATALOG.get(mission_id)
    if not mission_template: raise ValueError("Missão inválida.")
    
    active_mission = {
        "id": mission_id,
        "title": mission_template["title"],
        "type": mission_template["type"],
        "target_monster_id": mission_template.get("target_monster_id"),
        "target_item_id": mission_template.get("target_item_id"),
        "target_count": mission_template["target_count"],
        "current_progress": 0,
        "start_date": _now_iso(),
        "rewards": mission_template["rewards"],
        "description": mission_template.get("description", ""),
        "completed": False
    }
    
    clans_col.update_one(
        {"_id": clan_id},
        {"$set": {"active_mission": active_mission}}
    )

async def update_guild_mission_progress(user_id: Union[str, int], action_type: str, target_id: str, quantity: int = 1):
    """
    Atualiza o progresso da missão do clã se a ação corresponder.
    """
    user_id_str = _ensure_str(user_id)
    
    # Importação local para evitar ciclo
    from modules import player_manager
    pdata = await player_manager.get_player_data(user_id_str)
    
    if not pdata or not pdata.get("clan_id"):
        return

    clan_id = pdata.get("clan_id")
    clan = await get_clan(clan_id)
    if not clan: return

    mission = clan.get("active_mission")
    if not mission or mission.get("completed"):
        return

    mission_type = str(mission.get("type", "")).upper()
    action_type = str(action_type).upper()

    match = False
    
    if mission_type == 'HUNT' and action_type == 'HUNT':
        target_monster = mission.get("target_monster_id")
        if target_monster == target_id:
            match = True
            
    elif mission_type == 'COLLECT' and action_type == 'COLLECT':
        target_item = mission.get("target_item_id")
        if target_item == target_id:
            match = True

    if match:
        clans_col.update_one(
            {"_id": clan_id},
            {"$inc": {"active_mission.current_progress": quantity}}
        )

async def delete_clan(clan_id: str, leader_id: Union[str, int]):
    """
    Apaga permanentemente um clã e remove os membros.
    """
    leader_id_str = _ensure_str(leader_id)
    clan = await get_clan(clan_id)
    if not clan: 
        raise ValueError("Clã não encontrado.")
    
    if _ensure_str(clan.get("leader_id")) != leader_id_str:
        raise ValueError("Apenas o líder pode dissolver o clã.")

    # 1. Remove o documento do Clã
    clans_col.delete_one({"_id": clan_id})

    # 2. Remove o vínculo de TODOS os jogadores na coleção USERS
    if users_col is not None:
        users_col.update_many(
            {"clan_id": clan_id},
            {"$set": {"clan_id": None}}
        )
    
    logger.info(f"[CLAN] Clã {clan_id} foi deletado pelo líder {leader_id_str}.")