# modules/events/catacumbas/raid_manager.py
# (VERSÃO BLINDADA: Auth Híbrida + Normalização de IDs)

import time
import random
import string
from typing import Dict, Optional, Union
from . import config

LOBBIES: Dict[str, Dict] = {} 
# Mapeia ID (str) -> Código da Sala
PLAYER_LOCATION: Dict[str, str] = {}
ACTIVE_RAIDS: Dict[str, Dict] = {}

def _generate_room_code() -> str:
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        if code not in LOBBIES and code not in ACTIVE_RAIDS:
            return code

def create_lobby(leader_id: Union[int, str], leader_name: str) -> Optional[str]:
    uid = str(leader_id)
    if uid in PLAYER_LOCATION: return None
    
    code = _generate_room_code()
    LOBBIES[code] = {
        "code": code,
        "leader_id": uid, # Salva como string
        "players": {uid: leader_name},
        "status": "waiting",
        "created_at": time.time(),
        "ui_message_id": None
    }
    PLAYER_LOCATION[uid] = code
    return code

def register_lobby_message(code: str, message_id: int):
    if code in LOBBIES: LOBBIES[code]['ui_message_id'] = message_id

def join_lobby_by_code(user_id: Union[int, str], user_name: str, code: str) -> str:
    uid = str(user_id)
    code = code.upper().strip()
    
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
    if code: return LOBBIES.get(code)
    return None

def leave_lobby(user_id: Union[int, str]):
    uid = str(user_id)
    code = PLAYER_LOCATION.get(uid)
    if not code: return
    
    lobby = LOBBIES.get(code)
    if lobby and uid in lobby["players"]:
        del lobby["players"][uid]
        del PLAYER_LOCATION[uid]
        
        # Se saiu o líder ou a sala ficou vazia, destroi a sala
        if len(lobby["players"]) == 0 or uid == lobby["leader_id"]:
            players = list(lobby["players"].keys())
            for pid in players:
                if pid in PLAYER_LOCATION: del PLAYER_LOCATION[pid]
            if code in LOBBIES: del LOBBIES[code]

# ==============================================================================
# 🚀 LÓGICA DE PROGRESSÃO (ADAPTADA AO NOVO CONFIG)
# ==============================================================================

def _get_enemy_data_for_floor(floor: int) -> dict:
    """Converte Dataclass (Mob ou Boss) para dicionário de sessão."""
    key = config.FLOOR_MAP.get(floor, "skeleton_warrior")
    
    if key == "BOSS":
        entity = config.BOSS_CONFIG
        return {
            "name": entity.name,
            "current_hp": entity.max_hp,
            "max_hp": entity.max_hp,
            "attack": entity.attack,
            "defense": entity.defense,
            "initiative": entity.initiative,
            "image_normal": entity.image_normal,   # Específico do Boss
            "image_enraged": entity.image_enraged, # Específico do Boss
            "is_boss": True,
            "phase": "normal"
        }
    else:
        # É um Mob Comum
        entity = config.MOBS.get(key, config.MOBS["skeleton_warrior"])
        return {
            "name": entity.name,
            "current_hp": entity.max_hp,
            "max_hp": entity.max_hp,
            "attack": entity.attack,
            "defense": entity.defense,
            "initiative": entity.speed, # Converte 'speed' do mob para 'initiative'
            "image": entity.image_key,  # Específico de Mob
            "is_boss": False,
            "phase": "normal"
        }

def start_raid_from_lobby(leader_id: Union[int, str]) -> Optional[dict]:
    uid = str(leader_id)
    code = PLAYER_LOCATION.get(uid)
    lobby = LOBBIES.get(code)
    
    # Validação segura de líder (ambos str)
    if not lobby or str(lobby["leader_id"]) != uid: return None
    if len(lobby["players"]) < config.MIN_PLAYERS: return None

    start_floor = 1
    first_enemy = _get_enemy_data_for_floor(start_floor)

    session = {
        "raid_id": code,
        "players": lobby["players"], # Dict {uid: name}
        "leader_id": uid,
        "current_floor": start_floor,
        "total_floors": config.TOTAL_FLOORS,
        "boss": first_enemy,
        "turn_log": [f"⚔️ O grupo entrou nas Catacumbas (Andar {start_floor})!"],
        "status": "active",
        "floor_cleared": False,
        "start_time": time.time()
    }
    ACTIVE_RAIDS[code] = session
    if code in LOBBIES: del LOBBIES[code]
    return session

def advance_to_next_floor(session: dict) -> bool:
    next_f = session["current_floor"] + 1
    if next_f > config.TOTAL_FLOORS: return False # Vitória

    session["current_floor"] = next_f
    session["boss"] = _get_enemy_data_for_floor(next_f)
    session["floor_cleared"] = False 
    session["turn_log"] = [f"🚪 O grupo desceu para o Andar {next_f}!"]
    return True# modules/events/catacumbas/raid_manager.py
# (VERSÃO BLINDADA: Auth Híbrida + Normalização de IDs)

import time
import random
import string
from typing import Dict, Optional, Union
from . import config

LOBBIES: Dict[str, Dict] = {} 
# Mapeia ID (str) -> Código da Sala
PLAYER_LOCATION: Dict[str, str] = {}
ACTIVE_RAIDS: Dict[str, Dict] = {}

def _generate_room_code() -> str:
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        if code not in LOBBIES and code not in ACTIVE_RAIDS:
            return code

def create_lobby(leader_id: Union[int, str], leader_name: str) -> Optional[str]:
    uid = str(leader_id)
    if uid in PLAYER_LOCATION: return None
    
    code = _generate_room_code()
    LOBBIES[code] = {
        "code": code,
        "leader_id": uid, # Salva como string
        "players": {uid: leader_name},
        "status": "waiting",
        "created_at": time.time(),
        "ui_message_id": None
    }
    PLAYER_LOCATION[uid] = code
    return code

def register_lobby_message(code: str, message_id: int):
    if code in LOBBIES: LOBBIES[code]['ui_message_id'] = message_id

def join_lobby_by_code(user_id: Union[int, str], user_name: str, code: str) -> str:
    uid = str(user_id)
    code = code.upper().strip()
    
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
    if code: return LOBBIES.get(code)
    return None

def leave_lobby(user_id: Union[int, str]):
    uid = str(user_id)
    code = PLAYER_LOCATION.get(uid)
    if not code: return
    
    lobby = LOBBIES.get(code)
    if lobby and uid in lobby["players"]:
        del lobby["players"][uid]
        del PLAYER_LOCATION[uid]
        
        # Se saiu o líder ou a sala ficou vazia, destroi a sala
        if len(lobby["players"]) == 0 or uid == lobby["leader_id"]:
            players = list(lobby["players"].keys())
            for pid in players:
                if pid in PLAYER_LOCATION: del PLAYER_LOCATION[pid]
            if code in LOBBIES: del LOBBIES[code]

# ==============================================================================
# 🚀 LÓGICA DE PROGRESSÃO (ADAPTADA AO NOVO CONFIG)
# ==============================================================================

def _get_enemy_data_for_floor(floor: int) -> dict:
    """Converte Dataclass (Mob ou Boss) para dicionário de sessão."""
    key = config.FLOOR_MAP.get(floor, "skeleton_warrior")
    
    if key == "BOSS":
        entity = config.BOSS_CONFIG
        return {
            "name": entity.name,
            "current_hp": entity.max_hp,
            "max_hp": entity.max_hp,
            "attack": entity.attack,
            "defense": entity.defense,
            "initiative": entity.initiative,
            "image_normal": entity.image_normal,   # Específico do Boss
            "image_enraged": entity.image_enraged, # Específico do Boss
            "is_boss": True,
            "phase": "normal"
        }
    else:
        # É um Mob Comum
        entity = config.MOBS.get(key, config.MOBS["skeleton_warrior"])
        return {
            "name": entity.name,
            "current_hp": entity.max_hp,
            "max_hp": entity.max_hp,
            "attack": entity.attack,
            "defense": entity.defense,
            "initiative": entity.speed, # Converte 'speed' do mob para 'initiative'
            "image": entity.image_key,  # Específico de Mob
            "is_boss": False,
            "phase": "normal"
        }

def start_raid_from_lobby(leader_id: Union[int, str]) -> Optional[dict]:
    uid = str(leader_id)
    code = PLAYER_LOCATION.get(uid)
    lobby = LOBBIES.get(code)
    
    # Validação segura de líder (ambos str)
    if not lobby or str(lobby["leader_id"]) != uid: return None
    if len(lobby["players"]) < config.MIN_PLAYERS: return None

    start_floor = 1
    first_enemy = _get_enemy_data_for_floor(start_floor)

    session = {
        "raid_id": code,
        "players": lobby["players"], # Dict {uid: name}
        "leader_id": uid,
        "current_floor": start_floor,
        "total_floors": config.TOTAL_FLOORS,
        "boss": first_enemy,
        "turn_log": [f"⚔️ O grupo entrou nas Catacumbas (Andar {start_floor})!"],
        "status": "active",
        "floor_cleared": False,
        "start_time": time.time()
    }
    ACTIVE_RAIDS[code] = session
    if code in LOBBIES: del LOBBIES[code]
    return session

def advance_to_next_floor(session: dict) -> bool:
    next_f = session["current_floor"] + 1
    if next_f > config.TOTAL_FLOORS: return False # Vitória

    session["current_floor"] = next_f
    session["boss"] = _get_enemy_data_for_floor(next_f)
    session["floor_cleared"] = False 
    session["turn_log"] = [f"🚪 O grupo desceu para o Andar {next_f}!"]
    return True