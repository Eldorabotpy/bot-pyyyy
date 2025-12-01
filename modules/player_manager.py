# modules/player_manager.py
# (VERSÃO FINAL: ENERGIA CONECTADA ÀS MISSÕES GLOBALMENTE)

from __future__ import annotations
from typing import Any, Optional, Type
import asyncio # Necessário para atualizar missão em segundo plano
import logging

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
    # spend_energy, <--- REMOVIDO DAQUI (Vamos redefinir abaixo)
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
# --- 5.1 WRAPPER GLOBAL DE ENERGIA (A MÁGICA ACONTECE AQUI) ---
# =================================================================
def spend_energy(player_data: dict, amount: int) -> bool:
    """
    Consome energia do jogador e atualiza missões automaticamente.
    Esta função substitui a original para garantir que TODO gasto conte.
    """
    # 1. Executa a lógica original (desconta do dicionário)
    success = _spend_energy_internal(player_data, amount)

    # 2. Se gastou com sucesso, dispara atualização da missão
    if success and amount > 0:
        try:
            user_id = player_data.get("user_id") or player_data.get("_id")
            
            if user_id:
                # Função assíncrona interna para rodar no background
                async def _bg_mission_update():
                    try:
                        from modules import mission_manager
                        # Tenta atualizar com as chaves mais comuns
                        await mission_manager.update_mission_progress(user_id, "spend_energy", "any", amount)
                        await mission_manager.update_mission_progress(user_id, "energy", "any", amount)
                    except Exception as e:
                        logger.error(f"Erro silencioso ao atualizar missão de energia: {e}")

                # Dispara a tarefa sem travar o código principal (Fire and Forget)
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(_bg_mission_update())
                except RuntimeError:
                    # Caso não haja loop rodando (testes unitários, etc)
                    pass

        except Exception as e:
            logger.error(f"Erro no hook de spend_energy: {e}")

    return success

# =================================================================
# --- 6. Funções do Sistema Premium ---
# =================================================================
from .player.premium import PremiumManager

def has_premium_plan(pdata: Optional[dict]) -> bool:
    if not pdata:
        return False
    try:
        return PremiumManager(pdata).is_premium()
    except Exception:
        return False

def get_perk_value(pdata: Optional[dict], perk_name: str, default: Any = 1, cast: Type = None) -> Any:
    if not pdata:
        return default
    try:
        return PremiumManager(pdata).get_perk_value(perk_name, default, cast=cast)
    except Exception:
        return default

def get_perk_value_float(pdata: Optional[dict], perk_name: str, default: float = 1.0) -> float:
    val = get_perk_value(pdata, perk_name, default, cast=float)
    try:
        return float(val)
    except Exception:
        return float(default)

# =================================================================
# --- 7. HELPER: FULL RESTORE ---
# =================================================================
async def full_restore(user_id: int):
    """
    Restaura totalmente HP, MP e Energia.
    """
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
    """
    Busca jogador pelo nome do personagem (Case Insensitive).
    Retorna o dicionário completo do jogador (com 'user_id' injetado).
    """
    result = await find_player_by_name(name)
    
    if not result:
        return None
        
    if isinstance(result, tuple) and len(result) >= 2:
        user_id = result[0]
        player_data = result[1]
        
        if isinstance(player_data, dict):
            player_data['user_id'] = user_id
            return player_data
            
    return None