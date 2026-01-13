# modules/clan_manager.py
# (VERSÃO FINAL COMPLETA: PERMISSÕES HIERÁRQUICAS, SET_RANK E FUNÇÕES DE GERENCIAMENTO)

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
# CONFIGURAÇÃO DE CARGOS E HIERARQUIA
# ==============================================================================
# Value: Nível de autoridade (Maior = Mais poder)
CLAN_RANKS = {
    "leader": {"val": 4, "name": "Líder",   "emoji": "👑"},
    "vice":   {"val": 3, "name": "General", "emoji": "⚔️"},
    "elder":  {"val": 2, "name": "Ancião",  "emoji": "📜"},
    "member": {"val": 1, "name": "Membro",  "emoji": "👤"}
}

# ==============================================================================
# CONFIGURAÇÃO BLINDADA DO MONGODB
# ==============================================================================
MONGO_STR = "mongodb+srv://eldora-cluster:pb060987@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
clans_col = None
users_col = None 

try:
    client = MongoClient(MONGO_STR, tlsCAFile=certifi.where())
    db = client["eldora_db"]
    clans_col = db["clans"]
    users_col = db["users"] 
    
    clans_col.create_index("name_lower", unique=True)
    logger.info("✅ [CLAN MANAGER] Conectado ao MongoDB Atlas (Clans + Users).")
except Exception as e:
    logger.critical(f"❌ [CLAN MANAGER] Falha crítica na conexão: {e}")
    clans_col = None

# ==============================================================================
# HELPERS DE DATA E ID
# ==============================================================================
def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def _generate_clan_id() -> str:
    return f"clan_{uuid.uuid4().hex[:8]}"

def _ensure_str(value: Any) -> str:
    return str(value)

# ==============================================================================
# FUNÇÕES DE LEITURA (GETTERS)
# ==============================================================================

async def get_clan(clan_id: str) -> Optional[dict]:
    if clans_col is None or not clan_id: return None
    return clans_col.find_one({"_id": clan_id})

async def find_clan_by_display_name(name: str) -> Optional[dict]:
    if clans_col is None: return None
    return clans_col.find_one({"name_lower": name.strip().lower()})

async def get_member_rank(clan: dict, user_id: str) -> str:
    """Retorna a chave do rank (leader, vice, elder, member)."""
    user_id = _ensure_str(user_id)
    if user_id == _ensure_str(clan.get("leader_id")):
        return "leader"
    
    ranks = clan.get("member_ranks", {})
    return ranks.get(user_id, "member")

async def get_rank_value(rank_key: str) -> int:
    """Retorna o valor numérico de autoridade do cargo."""
    return CLAN_RANKS.get(rank_key, CLAN_RANKS["member"])["val"]

# ==============================================================================
# SISTEMA DE PERMISSÕES
# ==============================================================================

async def check_permission(clan: dict, actor_id: str, action: str, target_id: str = None) -> bool:
    """
    Centraliza a lógica de quem pode fazer o quê baseada na hierarquia.
    Actions: 'kick', 'invite_manage', 'mission_manage', 'change_rank'
    """
    actor_rank_key = await get_member_rank(clan, actor_id)
    actor_val = await get_rank_value(actor_rank_key)
    
    # 1. Gerenciar Convites (Ancião, General, Líder)
    if action == 'invite_manage':
        return actor_val >= 2 # Elder(2), Vice(3), Leader(4)

    # 2. Gerenciar Missões (General, Líder)
    if action == 'mission_manage':
        return actor_val >= 3 # Vice(3), Leader(4)

    # 3. Ações contra outro membro (Expulsar, Alterar Cargo)
    if target_id:
        # Ninguém pode afetar a si mesmo aqui (transferência de líder é outra função)
        if str(actor_id) == str(target_id): return False
        
        target_rank_key = await get_member_rank(clan, target_id)
        target_val = await get_rank_value(target_rank_key)

        # Regra de Ouro: Só pode mexer em quem tem rank ESTRITAMENTE INFERIOR
        if actor_val <= target_val: return False
        
        if action == 'kick':
            # Ancião (2) pode chutar Membro (1).
            # General (3) pode chutar Ancião (2) e Membro (1).
            # Líder (4) pode chutar todos.
            return True 

        if action == 'change_rank':
            # Apenas General (3) e Líder (4) podem alterar cargos
            # Ancião não promove ninguém.
            return actor_val >= 3

    return False

# ==============================================================================
# GERENCIAMENTO DE MEMBROS E CARGOS (SET_RANK)
# ==============================================================================

async def set_member_rank(clan_id: str, actor_id: str, target_id: str, new_rank_key: str) -> Tuple[bool, str]:
    """Define um cargo específico para um membro."""
    clan = await get_clan(clan_id)
    if not clan: return False, "Clã não encontrado."

    actor_id = _ensure_str(actor_id)
    target_id = _ensure_str(target_id)
    
    # Validações de Permissão
    if not await check_permission(clan, actor_id, 'change_rank', target_id):
        return False, "Você não tem autoridade sobre este membro."

    # Validação: Não pode promover alguém para um cargo igual ou maior que o seu próprio
    actor_rank_key = await get_member_rank(clan, actor_id)
    actor_val = await get_rank_value(actor_rank_key)
    new_rank_val = await get_rank_value(new_rank_key)

    if new_rank_val >= actor_val:
        return False, "Você não pode promover alguém ao seu nível ou superior."

    if new_rank_key == "leader":
        return False, "Use a função de transferir liderança para trocar o líder."

    # Aplica a mudança
    update_data = {}
    if new_rank_key == "member":
        # Se virou membro comum, remove do dicionário para economizar espaço
        update_data["$unset"] = {f"member_ranks.{target_id}": ""}
    else:
        update_data["$set"] = {f"member_ranks.{target_id}": new_rank_key}

    clans_col.update_one({"_id": clan_id}, update_data)
    
    rank_name = CLAN_RANKS.get(new_rank_key, {}).get("name", new_rank_key)
    return True, f"Cargo alterado para **{rank_name}** com sucesso."

# ==============================================================================
# FUNÇÕES DE GERENCIAMENTO (CRIAR, ENTRAR, SAIR)
# ==============================================================================

async def create_clan(leader_id: Union[str, int], clan_name: str, payment_method: str = 'gold') -> str:
    if clans_col is None: raise ValueError("Banco de dados offline.")
    
    leader_id_str = _ensure_str(leader_id)
    name_clean = clan_name.strip()
    
    if clans_col.find_one({"name_lower": name_clean.lower()}):
        raise ValueError(f"O nome '{name_clean}' já está em uso.")

    clan_id = _generate_clan_id()
    
    new_clan = {
        "_id": clan_id,
        "name": name_clean,
        "name_lower": name_clean.lower(),
        "display_name": name_clean,
        "leader_id": leader_id_str,
        "created_at": _now_iso(),
        "level": 1,
        "xp": 0,
        "prestige_level": 1,
        "prestige_points": 0,
        "bank": 0, 
        "members": [leader_id_str],
        "member_ranks": {}, # Armazena cargos extras: {user_id: "vice", user_id2: "elder"}
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
    user_id_str = _ensure_str(user_id)
    clan = await get_clan(clan_id)
    if not clan: raise ValueError("Clã não encontrado.")
    
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
    app_id_str = _ensure_str(applicant_id)
    clan = await get_clan(clan_id)
    if not clan: raise ValueError("Clã inválido.")
    
    if len(clan.get("members", [])) >= clan.get("max_members", 10):
        raise ValueError("O clã está lotado!")
        
    clans_col.update_one(
        {"_id": clan_id},
        {
            "$pull": {"pending_applications": app_id_str},
            "$addToSet": {"members": app_id_str}
        }
    )

async def decline_application(clan_id: str, applicant_id: Union[str, int]):
    app_id_str = _ensure_str(applicant_id)
    clans_col.update_one(
        {"_id": clan_id},
        {"$pull": {"pending_applications": app_id_str}}
    )

async def remove_member(clan_id: str, user_id: Union[str, int], kicked_by_leader: bool = True):
    user_id_str = _ensure_str(user_id)
    clan = await get_clan(clan_id)
    if not clan: raise ValueError("Clã não encontrado.")
    
    if user_id_str == _ensure_str(clan.get("leader_id")):
        raise ValueError("O líder não pode sair. Transfira a liderança primeiro.")
        
    clans_col.update_one(
        {"_id": clan_id},
        {
            "$pull": {"members": user_id_str},
            "$unset": {f"member_ranks.{user_id_str}": ""} # Remove o cargo também
        }
    )

async def transfer_leadership(clan_id: str, old_leader_id: Union[str, int], new_leader_id: Union[str, int]):
    new_leader_str = _ensure_str(new_leader_id)
    old_leader_str = _ensure_str(old_leader_id)
    
    clan = await get_clan(clan_id)
    members_str = [_ensure_str(m) for m in clan.get("members", [])]
    
    if new_leader_str not in members_str:
        raise ValueError("O novo líder deve ser um membro do clã.")
        
    clans_col.update_one(
        {"_id": clan_id},
        {
            "$set": {"leader_id": new_leader_str},
            "$unset": {f"member_ranks.{new_leader_str}": ""} # Novo líder não precisa de rank no dict
        }
    )
    # Opcional: O antigo líder vira Vice (General) automaticamente
    clans_col.update_one(
        {"_id": clan_id},
        {"$set": {f"member_ranks.{old_leader_str}": "vice"}}
    )

async def set_clan_media(clan_id: str, user_id: str, media_data: dict):
    clans_col.update_one(
        {"_id": clan_id},
        {"$set": {"logo_media_key": f"clan_logo_{clan_id}", "custom_logo_data": media_data}}
    )

# ==============================================================================
# MÉTODOS DE COMPATIBILIDADE (PROMOTE/DEMOTE LEGADO)
# ==============================================================================
# Estes métodos são mantidos para não quebrar chamadas antigas, mas usam a nova lógica internamente se possível.

async def promote_member(clan_id: str, actor_id: str, target_id: str) -> tuple[bool, str]:
    """
    Método legado de promoção cíclica (Membro -> Elder -> Vice).
    Agora usa set_member_rank internamente.
    """
    clan = await get_clan(clan_id)
    if not clan: return False, "Clã não encontrado."

    target_rank_key = await get_member_rank(clan, target_id)
    
    next_rank = None
    if target_rank_key == "member": next_rank = "elder"
    elif target_rank_key == "elder": next_rank = "vice"
    elif target_rank_key == "vice": return False, "Cargo máximo atingido! Transfira a liderança."
    elif target_rank_key == "leader": return False, "Não pode promover o líder."

    return await set_member_rank(clan_id, actor_id, target_id, next_rank)

async def demote_member(clan_id: str, actor_id: str, target_id: str) -> tuple[bool, str]:
    """
    Método legado de rebaixamento cíclico (Vice -> Elder -> Membro).
    """
    clan = await get_clan(clan_id)
    if not clan: return False, "Clã não encontrado."
    
    target_rank_key = await get_member_rank(clan, target_id)

    prev_rank = None
    if target_rank_key == "vice": prev_rank = "elder"
    elif target_rank_key == "elder": prev_rank = "member"
    elif target_rank_key == "member": return False, "Já está no cargo mais baixo."
    elif target_rank_key == "leader": return False, "Não pode rebaixar o líder."

    return await set_member_rank(clan_id, actor_id, target_id, prev_rank)

# ==============================================================================
# BANCO, ECONOMIA, PROGRESSO E MISSÕES
# ==============================================================================

async def bank_deposit(clan_id: str, user_id: Union[str, int], amount: int) -> Tuple[bool, str]:
    if amount <= 0: return False, "Valor inválido."
    user_id_str = _ensure_str(user_id)
    try:
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
                        "$each": [{"action": "depositou", "player_id": user_id_str, "player_name": player_name, "amount": amount, "timestamp": _now_iso()}],
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
    user_id_str = _ensure_str(user_id)
    clan = await get_clan(clan_id)
    if not clan: return False, "Clã não encontrado."
    if _ensure_str(clan.get("leader_id")) != user_id_str: return False, "Apenas o líder pode sacar."
    if clan.get("bank", 0) < amount: return False, "Saldo insuficiente."
        
    clans_col.update_one(
        {"_id": clan_id},
        {"$inc": {"bank": -amount}, "$push": {"bank_log": {"$each": [{"action": "sacou", "player_id": user_id_str, "player_name": "Líder", "amount": amount, "timestamp": _now_iso()}], "$slice": -20}}}
    )
    return True, f"Saque de {amount} realizado."

async def level_up_clan(clan_id: str, user_id: str, payment_method: str):
    clan = await get_clan(clan_id)
    if not clan: raise ValueError("Clã não encontrado.")
    
    current_lvl = clan.get("prestige_level", 1)
    current_pts = clan.get("prestige_points", 0)
    next_lvl_info = CLAN_PRESTIGE_LEVELS.get(current_lvl + 1)
    if not next_lvl_info: raise ValueError("Nível máximo atingido!")
    req_pts = next_lvl_info.get("points_to_next_level", 999999)
    cost = next_lvl_info.get("upgrade_cost", {})
    if current_pts < req_pts: raise ValueError(f"Faltam pontos de prestígio.")
    cost_val = cost.get(payment_method, 0)
    update_query = {}
    if payment_method == 'gold':
        if clan.get("bank", 0) < cost_val: raise ValueError("Ouro insuficiente.")
        update_query = {"$inc": {"bank": -cost_val, "prestige_level": 1, "prestige_points": -req_pts}, "$set": {"max_members": next_lvl_info.get("max_members", 10)}}
    elif payment_method == 'dimas':
        update_query = {"$inc": {"prestige_level": 1, "prestige_points": -req_pts}, "$set": {"max_members": next_lvl_info.get("max_members", 10)}}
    clans_col.update_one({"_id": clan_id}, update_query)

async def get_active_guild_mission(clan_id: str) -> Optional[dict]:
    clan = await get_clan(clan_id)
    return clan.get("active_mission") if clan else None

async def assign_mission_to_clan(clan_id: str, mission_id: str, user_id: str):
    from modules.game_data.guild_missions import GUILD_MISSIONS_CATALOG
    mission_template = GUILD_MISSIONS_CATALOG.get(mission_id)
    if not mission_template: raise ValueError("Missão inválida.")
    active_mission = {"id": mission_id, "title": mission_template["title"], "type": mission_template["type"], "target_monster_id": mission_template.get("target_monster_id"), "target_item_id": mission_template.get("target_item_id"), "target_count": mission_template["target_count"], "current_progress": 0, "start_date": _now_iso(), "rewards": mission_template["rewards"], "description": mission_template.get("description", ""), "completed": False}
    clans_col.update_one({"_id": clan_id}, {"$set": {"active_mission": active_mission}})

async def update_guild_mission_progress(user_id: Union[str, int], action_type: str, target_id: str, quantity: int = 1):
    user_id_str = _ensure_str(user_id)
    from modules import player_manager
    pdata = await player_manager.get_player_data(user_id_str)
    if not pdata or not pdata.get("clan_id"): return
    clan_id = pdata.get("clan_id")
    clan = await get_clan(clan_id)
    if not clan: return
    mission = clan.get("active_mission")
    if not mission or mission.get("completed"): return
    mission_type = str(mission.get("type", "")).upper()
    action_type = str(action_type).upper()
    match = False
    if mission_type == 'HUNT' and action_type == 'HUNT':
        if mission.get("target_monster_id") == target_id: match = True
    elif mission_type == 'COLLECT' and action_type == 'COLLECT':
        if mission.get("target_item_id") == target_id: match = True
    if match: clans_col.update_one({"_id": clan_id}, {"$inc": {"active_mission.current_progress": quantity}})

async def delete_clan(clan_id: str, leader_id: Union[str, int]):
    leader_id_str = _ensure_str(leader_id)
    clan = await get_clan(clan_id)
    if not clan: raise ValueError("Clã não encontrado.")
    if _ensure_str(clan.get("leader_id")) != leader_id_str: raise ValueError("Apenas o líder pode dissolver o clã.")
    clans_col.delete_one({"_id": clan_id})
    if users_col is not None: users_col.update_many({"clan_id": clan_id}, {"$set": {"clan_id": None}})
    logger.info(f"[CLAN] Clã {clan_id} foi deletado pelo líder {leader_id_str}.")