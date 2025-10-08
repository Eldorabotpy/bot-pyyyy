# Em modules/player/actions.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import time
from typing import Optional

from .premium import PremiumManager 
from .core import get_player_data, save_player_data

# ========================================
# FUNÇÕES AUXILIARES DE TEMPO E TIPO
# ========================================

def utcnow():
    return datetime.now(timezone.utc)

def _parse_iso(dt_str: str) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None

def _ival(x, default=0):
    try: return int(x)
    except Exception: return int(default)

# ========================================
# ENERGIA
# ========================================

def get_player_max_energy(player_data: dict) -> int:
    """Calcula a energia máxima de um jogador, incluindo o bônus de perks."""
    base_max = _ival(player_data.get('max_energy'), 20)
    premium = PremiumManager(player_data)
    bonus = _ival(premium.get_perk_value('max_energy_bonus', 0))
    return base_max + bonus

def spend_energy(player_data: dict, amount: int = 1) -> bool:
    amount = max(0, int(amount))
    cur = _ival(player_data.get('energy'))
    if cur < amount: return False
    player_data['energy'] = cur - amount
    return True

def add_energy(player_data: dict, amount: int = 1) -> dict:
    max_e = get_player_max_energy(player_data)
    cur = _ival(player_data.get('energy'))
    new_val = min(cur + int(amount), max_e)
    player_data['energy'] = max(0, new_val)
    return player_data
    
def sanitize_and_cap_energy(player_data: dict):
    """Garante que a energia está dentro dos limites e o timestamp existe."""
    max_e = get_player_max_energy(player_data)
    player_data["energy"] = max(0, min(_ival(player_data.get("energy"), max_e), max_e))
    if not player_data.get('energy_last_ts'):
        anchor = _parse_iso(player_data.get('last_energy_ts')) or utcnow()
        player_data['energy_last_ts'] = anchor.isoformat()
    if player_data.get('last_energy_ts'): player_data.pop('last_energy_ts', None)


def _get_regen_seconds(player_data: dict) -> int:
    """Obtém o tempo de regeneração de energia com base nos perks do jogador."""
    # Usando o PremiumManager para buscar o perk de forma segura
    premium = PremiumManager(player_data)
    return int(premium.get_perk_value('energy_regen_seconds', 300))

def _apply_energy_autoregen_inplace(player_data: dict) -> bool:
    
    changed = False
    max_e = get_player_max_energy(player_data)
    cur = _ival(player_data.get('energy'), 0)
    last_raw = player_data.get('energy_last_ts') or player_data.get('last_energy_ts')
    last_ts = _parse_iso(last_raw) or utcnow()
    regen_s = _get_regen_seconds(player_data)
    now = utcnow()
    if cur >= max_e:
        player_data['energy_last_ts'] = now.isoformat()
        return last_raw != player_data['energy_last_ts']
    if regen_s <= 0:
        if cur < max_e:
            player_data['energy'] = max_e
            changed = True
        player_data['energy_last_ts'] = now.isoformat()
        return changed or (last_raw != player_data['energy_last_ts'])
    elapsed = (now - last_ts).total_seconds()
    if elapsed < regen_s: return False
    gained = int(elapsed // regen_s)
    if gained > 0:
        new_energy = min(max_e, cur + gained)
        if new_energy != cur:
            player_data['energy'] = new_energy
            changed = True
        remainder_seconds = elapsed % regen_s
        new_anchor = now - timedelta(seconds=remainder_seconds)
        player_data['energy_last_ts'] = new_anchor.isoformat()
        changed = True
    return changed

# ========================================
# AÇÕES TEMPORIZADAS E ESTADO
# ========================================
def set_last_chat_id(user_id: int, chat_id: int):
    pdata = get_player_data(user_id)
    if not pdata: return
    pdata["last_chat_id"] = int(chat_id)
    save_player_data(user_id, pdata)

def ensure_timed_state(pdata: dict, action: str, seconds: int, details: dict | None, chat_id: int | None):
    start = utcnow().replace(microsecond=0)
    finish = start + timedelta(seconds=int(seconds))
    pdata["player_state"] = {
        "action": action,
        "started_at": start.isoformat(),
        "finish_time": finish.isoformat(),
        "details": details or {}
    }
    if chat_id is not None:
        pdata["last_chat_id"] = int(chat_id)
    return pdata

def try_finalize_timed_action_for_user(user_id: int) -> bool:
    player_data = get_player_data(user_id)
    state = player_data.get("player_state") or {}
    action = state.get("action")

    actions_com_timer = ("refining", "crafting", "collecting", "exploring", "travel")
    if action not in actions_com_timer:
        return False
    
    try:
        finish_time_iso = state.get("finish_time")
        hora_de_termino = datetime.fromisoformat(finish_time_iso).timestamp()
        
        if time.time() >= hora_de_termino:
            if action == "travel":
                dest = state.get("travel_dest") or (state.get("details") or {}).get("destination")
                if dest:
                    player_data["current_location"] = dest
            
            player_data["player_state"] = {"action": "idle"}
            save_player_data(user_id, player_data)
            return True
    except Exception:
        player_data["player_state"] = {"action": "idle"}
        save_player_data(user_id, player_data)
        return True
    
    return False

# ========================================
# ENTRADAS DE PVP
# ========================================
DEFAULT_PVP_ENTRIES = 10

def get_pvp_entries(player_data: dict) -> int:
    today = utcnow().date().isoformat()
    if player_data.get("last_pvp_entry_reset") != today:
        player_data["pvp_entries_left"] = DEFAULT_PVP_ENTRIES
        player_data["last_pvp_entry_reset"] = today
    return player_data.get("pvp_entries_left", DEFAULT_PVP_ENTRIES)

def use_pvp_entry(player_data: dict) -> bool:
    current_entries = get_pvp_entries(player_data)
    if current_entries > 0:
        player_data["pvp_entries_left"] = current_entries - 1
        return True
    return False

def add_pvp_entries(player_data: dict, amount: int):
    current_entries = get_pvp_entries(player_data)
    player_data["pvp_entries_left"] = current_entries + amount