# Em modules/player_manager.py

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
)

# =================================================================
# --- 6. Funções do Sistema Premium (VERSÃO REATORADA) ---
# =================================================================
# Agora, importamos a CLASSE, não as funções antigas.
from .player.premium import PremiumManager

def has_premium_plan(user_id: int) -> bool:
    """
    Verifica se um jogador tem um plano premium ativo.
    Esta é a "ponte" simplificada que o resto do código usará.
    """
    pdata = get_player_data(user_id)
    if not pdata:
        return False
    # A mágica acontece aqui: usamos o Manager internamente.
    return PremiumManager(pdata).is_premium()

def get_perk_value(user_id: int, perk_name: str, default=1):
    """
    Obtém o valor de um perk específico para o jogador, já considerando seu tier.
    Interface simplificada para consultar vantagens.
    """
    pdata = get_player_data(user_id)
    if not pdata:
        return default
    return PremiumManager(pdata).get_perk_value(perk_name, default)

# Nota: Não exportamos mais 'grant_premium_status' daqui.
# As partes do código que concedem premium (loja, painel admin) devem
# importar e usar o PremiumManager diretamente, pois é uma ação complexa.