from __future__ import annotations

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
    spend_energy, add_energy, 
    set_last_chat_id,
    ensure_timed_state, 
    try_finalize_timed_action_for_user, 
    get_pvp_entries,
    use_pvp_entry, 
    add_pvp_entries,
    heal_player, 
    add_buff, 
    
    # ==================================
    # 👇 FUNÇÕES DE PVP ADICIONADAS 👇
    # ==================================
    get_pvp_points,
    add_pvp_points,
)

# =================================================================
# --- 6. Funções do Sistema Premium (VERSÃO REATORADA) ---
# =================================================================
# Agora, importamos a CLASSE, não as funções antigas.
from .player.premium import PremiumManager
from typing import Any, Optional, Type

def has_premium_plan(pdata: Optional[dict]) -> bool:
    """
    Recebe player_data (pdata) e retorna True se o jogador tem premium ativo.
    Defensive: aceita pdata == None.
    """
    if not pdata:
        return False
    try:
        return PremiumManager(pdata).is_premium()
    except Exception:
        # Em caso de erro, não quebremos o fluxo — assume que não tem premium
        return False

def get_perk_value(pdata: Optional[dict], perk_name: str, default: Any = 1, cast: Type = None) -> Any:
    """
    Retorna o valor do perk para um jogador.
    Se 'cast' for fornecido (ex: float, int), tenta converter o valor antes de devolver.
    Uso recomendado para multiplicadores: get_perk_value(pdata, 'xp_multiplier', 1.0, cast=float)
    """
    if not pdata:
        return default
    try:
        return PremiumManager(pdata).get_perk_value(perk_name, default, cast=cast)
    except Exception:
        return default

def get_perk_value_float(pdata: Optional[dict], perk_name: str, default: float = 1.0) -> float:
    """
    Conveniência: retorna o perk convertido para float com fallback seguro.
    Use isto quando você espera um multiplicador numérico.
    """
    val = get_perk_value(pdata, perk_name, default, cast=float)
    try:
        return float(val)
    except Exception:
        return float(default)
