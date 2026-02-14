# modules/events/catacumbas/raid_manager.py
# (VERSÃO CORRIGIDA: Tratamento de Erro 'NoneType' e Logger Definido)

import time
import random
import string
import logging
from typing import Dict, Optional, Union
from . import config
from modules import player_manager

# ✅ 1. Definindo o Logger para evitar erro de "logger not defined"
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

# ==============================================================================
# 🧹 LIMPEZA ABSOLUTA DE JOGADOR
# ==============================================================================
def force_clear_player(user_id: Union[int, str]):
    """Remove o jogador de TUDO incondicionalmente."""
    uid = str(user_id)
    
    # 1. Remove de qualquer Lobby fantasma
    for code, lobby in list(LOBBIES.items()):
        if uid in lobby.get("players", {}):
            del lobby["players"][uid]
            if len(lobby["players"]) == 0: del LOBBIES[code]
            
    # 2. Remove de qualquer Raid fantasma
    for code, raid in list(ACTIVE_RAIDS.items()):
        if uid in raid.get("players", {}):
            del raid["players"][uid]
            if len(raid["players"]) == 0: del ACTIVE_RAIDS[code]
            
    # 3. APAGA A LOCALIZAÇÃO (Isto é o que te estava a prender)
    if uid in PLAYER_LOCATION:
        del PLAYER_LOCATION[uid]


# ==============================================================================
# 🏰 GESTÃO DE LOBBY
# ==============================================================================
def create_lobby(leader_id: Union[int, str], leader_name: str) -> Optional[str]:
    uid = str(leader_id)
    
    # 🔥 A MÁGICA ACONTECE AQUI: Limpa qualquer lixo antes de criar a sala
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

def leave_lobby(user_id: Union[int, str]):
    # Agora o leave_lobby apenas chama a nossa limpeza absoluta
    force_clear_player(user_id)

def register_lobby_message(code: str, message_id: int, chat_id: int = None):
    if code in LOBBIES: 
        LOBBIES[code]['ui_message_id'] = message_id
        if chat_id: LOBBIES[code]['chat_id'] = chat_id

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


# ==============================================================================
# 🚀 LÓGICA DE ESCALONAMENTO E CRIAÇÃO DE RAID
# ==============================================================================

async def calculate_group_scaling(player_ids: list) -> float:
    """Calcula dificuldade baseada nos stats reais, ignorando erros."""
    total_atk = 0
    total_hp = 0
    count = 0
    
    for pid in player_ids:
        try:
            if str(pid) == 'None': continue 
            
            pdata = await player_manager.get_player_data(pid)
            if not pdata: continue # Pula jogador inexistente

            stats = await player_manager.get_player_total_stats(pdata)
            
            total_atk += stats.get('attack', 20)
            total_hp += stats.get('max_hp', 100)
            count += 1
        except Exception as e:
            logger.error(f"Erro calc scaling {pid}: {e}")

    if count == 0: return 1.0

    avg_atk = total_atk / count
    avg_hp = total_hp / count

    # Fórmula: Dificuldade baseada na média do grupo
    power_mult = (avg_hp / 100) * 0.4 + (avg_atk / 20) * 0.6
    size_mult = 1.0 + (count - 1) * 0.25 # +25% por player extra
    
    return round(power_mult * size_mult, 2)

def _get_enemy_data_for_floor(floor: int, scaling: float = 1.0) -> dict:
    key = config.FLOOR_MAP.get(floor, "skeleton_warrior")
    
    if key == "BOSS":
        base = config.BOSS_CONFIG
        hp = int(base.max_hp * scaling)
        atk = int(base.attack * scaling)
        df = int(base.defense * (1 + (scaling - 1) * 0.5))
        
        return {
            "name": base.name,
            "current_hp": hp, "max_hp": hp,
            "attack": atk, "defense": df,
            "initiative": base.initiative,
            "image_normal": base.image_normal,
            "image_enraged": base.image_enraged,
            "is_boss": True, "_effects": []
        }
    else:
        base = config.MOBS.get(key, config.MOBS["skeleton_warrior"])
        hp = int(base.max_hp * scaling)
        atk = int(base.attack * scaling)
        df = int(base.defense * (1 + (scaling - 1) * 0.5))
        
        return {
            "name": base.name,
            "current_hp": hp, "max_hp": hp,
            "attack": atk, "defense": df,
            "initiative": base.speed,
            "image": base.image_key,
            "is_boss": False, "_effects": []
        }

async def start_raid_from_lobby(leader_id: Union[int, str]) -> Optional[dict]:
    uid = str(leader_id)
    code = PLAYER_LOCATION.get(uid)
    lobby = LOBBIES.get(code)
    
    if not lobby or str(lobby["leader_id"]) != uid: return None
    
    # ✅ CORREÇÃO CRÍTICA: Filtra apenas jogadores válidos antes de começar
    raw_players = list(lobby["players"].keys())
    valid_players_dict = {}
    
    for pid in raw_players:
        if not pid or str(pid) == 'None': continue
        
        # Verifica se existe no banco para evitar crash depois
        p_data = await player_manager.get_player_data(pid)
        if p_data:
            valid_players_dict[pid] = lobby["players"][pid]
        else:
            logger.warning(f"Jogador fantasma removido da raid: {pid}")

    if len(valid_players_dict) < config.MIN_PLAYERS: 
        logger.warning("Raid abortada: Jogadores insuficientes após filtro.")
        return None

    # Recalcula lista de IDs válidos
    player_ids = list(valid_players_dict.keys())
    scaling = await calculate_group_scaling(player_ids)
    
    start_floor = 1
    first_enemy = _get_enemy_data_for_floor(start_floor, scaling)

    session = {
        "raid_id": code,
        "players": valid_players_dict, # Usa o dicionário limpo
        "leader_id": uid,
        "current_floor": start_floor,
        "total_floors": config.TOTAL_FLOORS,
        "scaling_factor": scaling,
        "boss": first_enemy,
        "turn_log": [f"⚔️ Grupo ({len(player_ids)}) entrou. Nível de Desafio: {scaling}x"],
        "status": "active",
        "floor_cleared": False,
        "start_time": time.time()
    }
    
    ACTIVE_RAIDS[code] = session
    
    # Remove do lobby de espera, pois agora é uma raid ativa
    if code in LOBBIES: del LOBBIES[code]
    
    return session

def advance_to_next_floor(session: dict) -> bool:
    next_f = session["current_floor"] + 1
    if next_f > config.TOTAL_FLOORS: return False

    scaling = session.get("scaling_factor", 1.0)
    session["current_floor"] = next_f
    session["boss"] = _get_enemy_data_for_floor(next_f, scaling)
    session["floor_cleared"] = False 
    session["turn_log"].append(f"🚪 Descendo para o Andar {next_f}...")
    return True