# modules/events/catacumbas/raid_manager.py
# (VERSÃO CORRIGIDA: INTEGRAÇÃO TOTAL COM EFFECT ENGINE)

import time
import random
import string
import logging
from typing import Dict, Optional, Union
from . import config
from modules import player_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LOBBIES: Dict[str, Dict] = {} 
PLAYER_LOCATION: Dict[str, str] = {}
ACTIVE_RAIDS: Dict[str, Dict] = {}

def _generate_room_code() -> str:
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        if code not in LOBBIES and code not in ACTIVE_RAIDS:
            return code

def force_clear_player(user_id: Union[int, str]):
    """Remove o jogador de Lobbies, Raids e Localização de forma absoluta."""
    uid = str(user_id)
    for code, lobby in list(LOBBIES.items()):
        if uid in lobby.get("players", {}):
            del lobby["players"][uid]
            if len(lobby["players"]) == 0: del LOBBIES[code]
    for code, raid in list(ACTIVE_RAIDS.items()):
        if uid in raid.get("players", {}):
            del raid["players"][uid]
            if len(raid["players"]) == 0: del ACTIVE_RAIDS[code]
    if uid in PLAYER_LOCATION:
        del PLAYER_LOCATION[uid]

def create_lobby(leader_id: Union[int, str], leader_name: str) -> Optional[str]:
    uid = str(leader_id)
    force_clear_player(uid)
    code = _generate_room_code()
    LOBBIES[code] = {
        "code": code,
        "leader_id": uid,
        "players": {uid: leader_name},
        "status": "waiting",
        "created_at": time.time(),
        "ui_message_id": None,
        "chat_id": None
    }
    PLAYER_LOCATION[uid] = code
    return code

def join_lobby_by_code(user_id: Union[int, str], user_name: str, code: str) -> str:
    uid, code = str(user_id), code.upper().strip()
    lobby = LOBBIES.get(code)
    if not lobby: return "not_found"
    if lobby["status"] != "waiting": return "started"
    if len(lobby["players"]) >= config.MAX_PLAYERS: return "full"
    if uid in lobby["players"]: return "already_in"
    if uid in PLAYER_LOCATION: return "in_another_lobby"
    lobby["players"][uid] = user_name
    PLAYER_LOCATION[uid] = code
    return "success"

def get_player_lobby(user_id: Union[int, str]) -> Optional[dict]:
    uid = str(user_id)
    code = PLAYER_LOCATION.get(uid)
    return LOBBIES.get(code) if code else None

async def calculate_group_scaling(player_ids: list) -> float:
    """Calcula dificuldade baseada nos stats reais, com limites de segurança."""
    total_atk, total_hp, count = 0, 0, 0
    for pid in player_ids:
        try:
            pdata = await player_manager.get_player_data(pid)
            if not pdata: continue
            stats = await player_manager.get_player_total_stats(pdata)
            total_atk += stats.get('attack', 20)
            total_hp += stats.get('max_hp', 100)
            count += 1
        except: continue

    if count == 0: return 1.0

    avg_atk = total_atk / count
    avg_hp = total_hp / count

    # FÓRMULA SUAVIZADA: Divide por valores base mais altos (250 HP / 80 ATK)
    power_mult = (avg_hp / 250) * 0.4 + (avg_atk / 80) * 0.4 + 0.2
    size_mult = 1.0 + (count - 1) * 0.15 # +15% por player extra (em vez de 25%)
    
    # CAP: Máximo de 4.5x de dificuldade total
    return min(4.5, max(1.0, round(power_mult * size_mult, 2)))

def _get_enemy_data_for_floor(floor: int, scaling: float = 1.0) -> dict:
    key = config.FLOOR_MAP.get(floor, "skeleton_warrior")
    is_boss = (key == "BOSS")
    base = config.BOSS_CONFIG if is_boss else config.MOBS.get(key)
    
    hp = int(base.max_hp * scaling)
    atk = int(base.attack * scaling)
    # DEFESA: Scaling reduzido (0.2) para evitar mobs imunes a dano
    df = int(base.defense * (1 + (scaling - 1) * 0.2)) 
    
    return {
        "name": base.name,
        "current_hp": hp, "max_hp": hp, "hp_max": hp,
        "attack": atk, "defense": df,
        "initiative": base.initiative if is_boss else base.speed,
        "image": base.image_normal if is_boss else base.image_key,
        "is_boss": is_boss, "_effects": []
    }

async def start_raid_from_lobby(leader_id: Union[int, str]) -> Optional[dict]:
    uid = str(leader_id)
    code = PLAYER_LOCATION.get(uid)
    lobby = LOBBIES.get(code)
    if not lobby or str(lobby["leader_id"]) != uid: return None
    
    valid_players_dict = {}
    for pid in list(lobby["players"].keys()):
        if not pid or str(pid) == 'None': continue
        p_data = await player_manager.get_player_data(pid)
        if p_data: valid_players_dict[pid] = lobby["players"][pid]

    if len(valid_players_dict) < config.MIN_PLAYERS: return None

    scaling = await calculate_group_scaling(list(valid_players_dict.keys()))
    session = {
        "raid_id": code,
        "players": valid_players_dict,
        "leader_id": uid,
        "current_floor": 1,
        "total_floors": config.TOTAL_FLOORS,
        "scaling_factor": scaling,
        "boss": _get_enemy_data_for_floor(1, scaling),
        "turn_log": [f"⚔️ Grupo ({len(valid_players_dict)}) entrou. Desafio: {scaling}x"],
        "status": "active",
        "floor_cleared": False,
        "monster_turn_counter": 0,
        "monster_turn_threshold": max(3, len(valid_players_dict) * 2) 
    }
    ACTIVE_RAIDS[code] = session
    if code in LOBBIES: del LOBBIES[code]
    return session

def advance_to_next_floor(session: dict) -> bool:
    next_f = session["current_floor"] + 1
    if next_f > config.TOTAL_FLOORS: return False
    session["current_floor"] = next_f
    session["boss"] = _get_enemy_data_for_floor(next_f, session.get("scaling_factor", 1.0))
    session["floor_cleared"] = False 
    session["turn_log"].append(f"🚪 Descendo para o Andar {next_f}...")
    return True