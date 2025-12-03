# modules/player_manager.py
# (VERSÃO FINAL COMPLETA: Energia + Runas Corrigidas + Save Seguro Anti-Render)

from __future__ import annotations
import asyncio
import logging
from typing import Any, Optional, Type

logger = logging.getLogger(__name__)

# --- 1. Funções do Core ---
from .player.core import (
    get_player_data, 
    save_player_data, 
    clear_player_cache, 
    clear_all_player_cache,
)

# --- 2. Funções de Busca e Ciclo de Vida do Jogador ---
from .player.queries import (
    create_new_player, 
    get_or_create_player, 
    delete_player, 
    find_player_by_name,
    find_player_by_name_norm, 
    iter_players,
    iter_player_ids
)

# --- 3. Funções de Stats, Classes e Level Up ---
from .player.stats import (
    get_player_total_stats, 
    get_player_dodge_chance, 
    get_player_double_attack_chance,
    check_and_apply_level_up, 
    allowed_points_for_level, 
    reset_stats_and_refund_points,
    needs_class_choice, 
    mark_class_choice_offered, 
    has_completed_dungeon,
    mark_dungeon_as_completed,
    can_see_evolution_menu,
    compute_spent_status_points,
)

# --- 4. Funções de Inventário, Ouro, Gemas e Equipamentos ---
from .player.inventory import (
    get_gold, 
    set_gold, 
    add_gold, 
    spend_gold, 
    get_gems, 
    set_gems, 
    add_gems, 
    spend_gems,
    add_item_to_inventory, 
    add_unique_item, 
    remove_item_from_inventory,
    equip_unique_item_for_user, 
    has_item, 
    consume_item,
)

# --- 5. Funções de Ações, Energia e Estado ---
from .player.actions import (
    get_player_max_energy, 
    # spend_energy, <--- REMOVIDO DAQUI (Redefinido abaixo)
    add_energy, 
    set_last_chat_id,
    ensure_timed_state, 
    try_finalize_timed_action_for_user, 
    get_pvp_entries,
    use_pvp_entry, 
    add_pvp_entries,
    heal_player, 
    add_buff, 
    get_player_max_mana,
    add_mana,
    spend_mana,
    get_pvp_points,
    add_pvp_points,
)

# Importamos a função original com outro nome para usar dentro do nosso Wrapper
from .player.actions import spend_energy as _spend_energy_internal

# =================================================================
# --- 5.1 WRAPPER GLOBAL DE ENERGIA ---
# =================================================================
def spend_energy(player_data: dict, amount: int) -> bool:
    """
    Consome energia do jogador e atualiza missões automaticamente (Fire and Forget).
    """
    success = _spend_energy_internal(player_data, amount)

    if success and amount > 0:
        try:
            user_id = player_data.get("user_id") or player_data.get("_id")
            if user_id:
                async def _bg_mission_update():
                    try:
                        from modules import mission_manager
                        await mission_manager.update_mission_progress(user_id, "spend_energy", "any", amount)
                        await mission_manager.update_mission_progress(user_id, "energy", "any", amount)
                    except Exception as e:
                        logger.error(f"Erro silencioso missão energia: {e}")

                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(_bg_mission_update())
                except RuntimeError:
                    pass
        except Exception as e:
            logger.error(f"Erro no hook de spend_energy: {e}")

    return success

# =================================================================
# --- 6. Funções do Sistema Premium ---
# =================================================================
from .player.premium import PremiumManager

def has_premium_plan(pdata: Optional[dict]) -> bool:
    if not pdata: return False
    try: return PremiumManager(pdata).is_premium()
    except Exception: return False

def get_perk_value(pdata: Optional[dict], perk_name: str, default: Any = 1, cast: Type = None) -> Any:
    if not pdata: return default
    try: return PremiumManager(pdata).get_perk_value(perk_name, default, cast=cast)
    except Exception: return default

def get_perk_value_float(pdata: Optional[dict], perk_name: str, default: float = 1.0) -> float:
    val = get_perk_value(pdata, perk_name, default, cast=float)
    try: return float(val)
    except Exception: return float(default)

# =================================================================
# --- 7. HELPER: FULL RESTORE ---
# =================================================================
async def full_restore(user_id: int):
    pdata = await get_player_data(user_id)
    if pdata:
        stats = await get_player_total_stats(pdata)
        pdata['current_hp'] = stats.get('max_hp', 100)
        pdata['current_mp'] = stats.get('max_mana', 50)
        pdata['energy'] = get_player_max_energy(pdata)
        await save_player_data(user_id, pdata)
        return True
    return False

async def find_player_by_character_name(name: str):
    result = await find_player_by_name(name)
    if not result: return None
    if isinstance(result, tuple) and len(result) >= 2:
        user_id = result[0]
        player_data = result[1]
        if isinstance(player_data, dict):
            player_data['user_id'] = user_id
            return player_data
    return None

# =================================================================
# --- 8. SISTEMA DE RUNAS (CORRIGIDO) ---
# =================================================================
try:
    from modules.game_data import runes_data
except ImportError:
    runes_data = None

def get_rune_bonuses(player_data: dict) -> dict:
    """
    Varre equipamentos, busca os itens no inventário e soma bônus das runas.
    """
    bonuses = {}
    if not runes_data: return bonuses

    # Pega o mapa {slot: uid}
    equipped_map = player_data.get("equipment") or player_data.get("equipments") or {}
    # Pega o inventário real
    inventory = player_data.get("inventory") or {}
    
    for slot, uid in equipped_map.items():
        if not uid: continue
        
        # BUSCA O ITEM NO INVENTÁRIO
        item = inventory.get(uid)
        if not item or not isinstance(item, dict): continue
        
        sockets = item.get("sockets", [])
        for rune_id in sockets:
            if not rune_id: continue
            
            info = runes_data.get_rune_info(rune_id)
            stat_key = info.get("stat_key")
            value = info.get("value", 0)
            
            if stat_key and value:
                current = bonuses.get(stat_key, 0)
                try: bonuses[stat_key] = current + value
                except Exception: pass
                
    return bonuses

# =================================================================
# --- 9. TRANSAÇÕES SEGURAS (ANTI-LAG & ANTI-PERDA DE DADOS) ---
# =================================================================
# Use estas funções ao dar recompensas para garantir que o save ocorra
# imediatamente no banco de dados, prevenindo perdas se o Render reiniciar.

async def safe_add_gold(user_id: int, amount: int) -> int:
    """Adiciona ouro e salva imediatamente."""
    pdata = await get_player_data(user_id)
    if not pdata: return 0
    
    # Usa a função importada de inventory (que já modifica o dict)
    add_gold(pdata, amount)
    
    # Salva no banco (asyncio.to_thread está no core.py, então não trava)
    await save_player_data(user_id, pdata)
    
    return int(pdata.get("gold", 0))

async def safe_spend_gold(user_id: int, amount: int) -> bool:
    """Gasta ouro e salva imediatamente se houver sucesso."""
    pdata = await get_player_data(user_id)
    if not pdata: return False
    
    if spend_gold(pdata, amount):
        await save_player_data(user_id, pdata)
        return True
    return False

async def safe_add_xp(user_id: int, xp_amount: int) -> tuple[int, str]:
    """Adiciona XP, checa Level Up e salva imediatamente."""
    pdata = await get_player_data(user_id)
    if not pdata: return 0, ""
    
    current_xp = int(pdata.get("xp", 0))
    pdata["xp"] = current_xp + int(xp_amount)
    
    # Verifica level up
    levels_gained, points_gained, msg = check_and_apply_level_up(pdata)
    
    # Salva tudo
    await save_player_data(user_id, pdata)
    
    return levels_gained, msg