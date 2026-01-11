# modules/player_manager.py
# (VERSÃO CORRIGIDA: Exporta iter_player_ids corretamente)

from __future__ import annotations
import asyncio
import logging
from typing import Any, Optional, Type, Union
from bson import ObjectId

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. IMPORTAÇÕES DO SISTEMA (CORE & QUERIES)
# ==============================================================================

# Core & Banco
from .player.core import (
    get_player_data as _get_player_data_core, 
    save_player_data as _save_player_data_core, 
    clear_player_cache, 
    clear_all_player_cache,
)

# Queries & Busca (AQUI ESTÁ A CORREÇÃO: iter_player_ids)
from .player.queries import (
    create_new_player, 
    get_or_create_player, 
    delete_player, 
    find_player_by_name,
    find_player_by_name_norm, 
    iter_players,
    iter_player_ids  # <--- Essencial para o handlers/jobs.py
)

# Stats & Nível
from .player.stats import (
    get_player_total_stats, 
    get_player_dodge_chance, 
    get_player_double_attack_chance,
    check_and_apply_level_up, 
    add_xp,
    allowed_points_for_level, 
    reset_stats_and_refund_points,
    needs_class_choice, 
    mark_class_choice_offered, 
    has_completed_dungeon,
    mark_dungeon_as_completed,
    can_see_evolution_menu,
    compute_spent_status_points,
)

# Inventário & Economia
from .player.inventory import (
    get_gold, set_gold, add_gold, spend_gold, 
    get_gems, set_gems, add_gems, spend_gems,
    add_item_to_inventory, add_unique_item, 
    remove_item_from_inventory,
    equip_unique_item_for_user,
    unequip_item_for_user, 
    has_item, consume_item,
)

# Ações & Energia
from .player.actions import (
    get_player_max_energy, add_energy, set_last_chat_id,
    ensure_timed_state, try_finalize_timed_action_for_user, 
    get_pvp_entries, use_pvp_entry, add_pvp_entries,
    heal_player, add_buff, 
    get_player_max_mana, add_mana, spend_mana,
    get_pvp_points, add_pvp_points,
)
# Alias interno para evitar circular imports
from .player.actions import spend_energy as _spend_energy_internal

# Premium
from .player.premium import PremiumManager

# ==============================================================================
# 2. HELPER DE ID (STRICT OBJECTID)
# ==============================================================================
def _ensure_id_format(user_id: Union[str, ObjectId]) -> ObjectId:
    if isinstance(user_id, ObjectId): return user_id
    if isinstance(user_id, str) and ObjectId.is_valid(user_id): return ObjectId(user_id)
    # logger.error(f"❌ [ID ERROR] ID Inválido: {user_id}")
    return None

# ==============================================================================
# 3. WRAPPERS E LÓGICA
# ==============================================================================

async def get_player_data(user_id: Union[str, ObjectId]):
    real_id = _ensure_id_format(user_id)
    if not real_id: return None
    pdata = await _get_player_data_core(real_id)

    # Auto-Fix VIP Expirado
    if pdata:
        tier = str(pdata.get("premium_tier", "free")).lower()
        if tier not in ["free", "admin"]:
            try:
                expires_at = pdata.get("premium_expires_at")
                if expires_at:
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc)
                    dt = datetime.fromisoformat(expires_at)
                    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                    if dt < now:
                        pdata["premium_tier"] = "free"
                        pdata["premium_expires_at"] = None
                        await _save_player_data_core(real_id, pdata)
            except Exception: pass
            
    return pdata

async def save_player_data(user_id: Union[str, ObjectId], data: dict):
    real_id = _ensure_id_format(user_id)
    if not real_id: return
    return await _save_player_data_core(real_id, data)

def spend_energy(player_data: dict, amount: int) -> bool:
    success = _spend_energy_internal(player_data, amount)
    if success and amount > 0:
        try:
            user_id = str(player_data.get("user_id") or player_data.get("_id"))
            # Tenta atualizar missão em background
            async def _bg_mission():
                try:
                    from modules import mission_manager
                    await mission_manager.update_mission_progress(user_id, "spend_energy", "any", amount)
                except: pass
            try: asyncio.get_running_loop().create_task(_bg_mission())
            except: pass
        except: pass
    return success

# --- Wrappers de Transação ---

async def safe_add_gold(user_id: Union[str, ObjectId], amount: int) -> int:
    pdata = await get_player_data(user_id)
    if not pdata: return 0
    add_gold(pdata, amount)
    await save_player_data(user_id, pdata)
    return int(pdata.get("gold", 0))

async def safe_spend_gold(user_id: Union[str, ObjectId], amount: int) -> bool:
    pdata = await get_player_data(user_id)
    if not pdata: return False
    if spend_gold(pdata, amount):
        await save_player_data(user_id, pdata)
        return True
    return False

async def safe_add_xp(user_id: Union[str, ObjectId], xp_amount: int) -> tuple[int, str]:
    pdata = await get_player_data(user_id)
    if not pdata: return 0, ""
    
    current = int(pdata.get("xp", 0))
    pdata["xp"] = current + int(xp_amount)
    
    lvls, pts, msg = check_and_apply_level_up(pdata)
    await save_player_data(user_id, pdata)
    return lvls, msg

async def full_restore(user_id: Union[str, ObjectId]):
    pdata = await get_player_data(user_id)
    if pdata:
        stats = await get_player_total_stats(pdata)
        pdata['current_hp'] = stats.get('max_hp', 100)
        pdata['current_mp'] = stats.get('max_mana', 50)
        pdata['energy'] = get_player_max_energy(pdata)
        await save_player_data(user_id, pdata)
        return True
    return False

# --- Helpers Diversos ---

def has_premium_plan(pdata: Optional[dict]) -> bool:
    if not pdata: return False
    try: return PremiumManager(pdata).is_premium()
    except: return False

def get_perk_value(pdata: Optional[dict], perk_name: str, default: Any = 1, cast: Type = None) -> Any:
    if not pdata: return default
    try: return PremiumManager(pdata).get_perk_value(perk_name, default, cast=cast)
    except: return default

# Runas (Fallback)
try:
    from modules.game_data import runes_data
except ImportError:
    runes_data = None

def get_rune_bonuses(player_data: dict) -> dict:
    bonuses = {}
    if not runes_data: return bonuses
    equipped = player_data.get("equipment", {})
    inv = player_data.get("inventory", {})
    for uid in equipped.values():
        if not uid: continue
        item = inv.get(uid)
        if isinstance(item, dict):
            for rid in item.get("sockets", []):
                if not rid: continue
                info = runes_data.get_rune_info(rid)
                if info and "stat_key" in info:
                    k = info["stat_key"]
                    bonuses[k] = bonuses.get(k, 0) + info.get("value", 0)
    return bonuses