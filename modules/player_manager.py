# modules/player_manager.py
# (VERSÃO FINAL BLINDADA: Suporte Híbrido Total Int/Str)

from __future__ import annotations
import asyncio
import logging
from typing import Any, Optional, Type, Union
from bson import ObjectId

logger = logging.getLogger(__name__)

# --- 1. Funções do Core ---
from .player.core import (
    get_player_data as _get_player_data_core, 
    save_player_data as _save_player_data_core, 
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

def _ensure_id_format(user_id: Union[int, str, ObjectId]) -> Union[int, ObjectId]:
    """
    Converte o ID para o formato correto do banco:
    - Se for int: Mantém int (Conta Legada)
    - Se for str de 24 chars: Converte para ObjectId (Conta Nova)
    - Se for str numérico: Converte para int (Conta Legada vinda como str)
    - Se for ObjectId: Mantém
    """
    if isinstance(user_id, ObjectId):
        return user_id
        
    if isinstance(user_id, int):
        return user_id
        
    if isinstance(user_id, str):
        # Tenta converter para int primeiro (caso seja ID do telegram em string)
        if user_id.isdigit():
            return int(user_id)
        # Se for um ObjectId válido em string
        if ObjectId.is_valid(user_id):
            return ObjectId(user_id)
            
    # Se falhar, retorna como está (provavelmente vai dar erro no find, mas evita crash aqui)
    return user_id

# =================================================================
# --- 5.1 WRAPPER GLOBAL DE ENERGIA ---
# =================================================================
def spend_energy(player_data: dict, amount: int) -> bool:
    """
    Consome energia do jogador e atualiza missões automaticamente (Fire and Forget).
    """
    # Executa a lógica interna de gasto (matemática)
    success = _spend_energy_internal(player_data, amount)

    if success and amount > 0:
        try:
            # ✅ CORREÇÃO: Força conversão para STR para evitar erro no Mission Manager
            raw_id = player_data.get("user_id") or player_data.get("_id")
            user_id = str(raw_id) 
            
            if user_id:
                async def _bg_mission_update():
                    try:
                        from modules import mission_manager
                        # Atualiza missão de "gastar X energia" e "gastar energia total"
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
async def full_restore(user_id: Union[int, str]):
    # ✅ CORREÇÃO: Aceita int ou str (ObjectId)
    # Usa o wrapper seguro
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
# --- 8. SISTEMA DE RUNAS ---
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

async def safe_add_gold(user_id: Union[int, str], amount: int) -> int:
    """Adiciona ouro e salva imediatamente."""
    pdata = await get_player_data(user_id)
    if not pdata: return 0
    
    add_gold(pdata, amount)
    await save_player_data(user_id, pdata)
    return int(pdata.get("gold", 0))

async def get_player_data(user_id: Union[int, str]):
    """Wrapper seguro para buscar dados de qualquer tipo de conta."""
    real_id = _ensure_id_format(user_id)
    return await _get_player_data_core(real_id)

async def save_player_data(user_id: Union[int, str], data: dict):
    """Wrapper seguro para salvar dados de qualquer tipo de conta."""
    real_id = _ensure_id_format(user_id)
    return await _save_player_data_core(real_id, data)

async def safe_spend_gold(user_id: Union[int, str], amount: int) -> bool:
    """Gasta ouro e salva imediatamente se houver sucesso."""
    pdata = await get_player_data(user_id)
    if not pdata: return False
    
    if spend_gold(pdata, amount):
        await save_player_data(user_id, pdata)
        return True
    return False

async def safe_add_xp(user_id: Union[int, str], xp_amount: int) -> tuple[int, str]:
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

# --- FERRAMENTAS DE CORREÇÃO ---

async def corrigir_inventario_automatico(user_id: Union[int, str]):
    """
    Detecta itens com IDs antigos/errados e funde com os oficiais.
    """
    pdata = await get_player_data(user_id)
    if not pdata: return
    
    inventory = pdata.get("inventory", {})
    mudou = False

    migracoes = {
        "minerio_ferro": "minerio_de_ferro",
        "iron_ore": "minerio_de_ferro",
        "pedra_ferro": "minerio_de_ferro",
        "minerio_bruto": "minerio_de_ferro",
        "minerio_estanho": "minerio_de_estanho",
        "tin_ore": "minerio_de_estanho",
        "minerio_prata": "minerio_de_prata",
        "silver_ore": "minerio_de_prata",
        "madeira_rara_bruta": "madeira_rara",
        "wood_rare": "madeira_rara",
        "carvao_mineral": "carvao",
        "coal": "carvao"
    }

    for id_velho, id_novo in migracoes.items():
        if id_velho in inventory:
            item_data = inventory[id_velho]
            qtd_velha = 0
            
            if isinstance(item_data, dict):
                qtd_velha = int(item_data.get("quantity", 1))
            else:
                qtd_velha = int(item_data)

            if qtd_velha > 0:
                if id_novo not in inventory:
                    inventory[id_novo] = 0
                
                if isinstance(inventory[id_novo], dict):
                    inventory[id_novo]["quantity"] = int(inventory[id_novo].get("quantity", 0)) + qtd_velha
                else:
                    inventory[id_novo] = int(inventory[id_novo]) + qtd_velha

                print(f"🔧 FIX: {user_id} | {qtd_velha}x {id_velho} -> {id_novo}")
                mudou = True
            
            del inventory[id_velho]
            mudou = True

    if mudou:
        await save_player_data(user_id, pdata)
        return True
    return False

async def corrigir_bug_tomos_duplicados(user_id: Union[int, str]):
    """
    Corrige IDs duplicados como 'tomo_tomo_'.
    """
    pdata = await get_player_data(user_id)
    if not pdata: return False
    
    inventory = pdata.get("inventory", {})
    mudou = False
    
    lista_itens = list(inventory.keys())

    for item_id in lista_itens:
        if item_id.startswith("tomo_tomo_"):
            dados_item = inventory[item_id]
            qtd = 0
            if isinstance(dados_item, dict):
                qtd = int(dados_item.get("quantity", 1))
            else:
                qtd = int(dados_item)

            if qtd > 0:
                id_correto = item_id.replace("tomo_tomo_", "tomo_", 1)
                add_item_to_inventory(pdata, id_correto, qtd)
                print(f"🔧 FIX TOMO: Jogador {user_id} | {qtd}x {item_id} -> {id_correto}")
            
            del inventory[item_id]
            mudou = True

    if mudou:
        await save_player_data(user_id, pdata)
        return True
    return False