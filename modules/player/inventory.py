# modules/player/inventory.py
# (VERSÃO CORRIGIDA: Equipar, Desequipar e Atualização de Status)

import logging
from typing import Tuple, Union
from modules import game_data

logger = logging.getLogger(__name__)

# --- Getters e Setters Básicos (Mantidos) ---
def get_gold(player_data: dict) -> int:
    return int(player_data.get("gold", 0))

def set_gold(player_data: dict, value: int) -> dict:
    player_data["gold"] = max(0, int(value))
    return player_data

def add_gold(player_data: dict, amount: int) -> dict:
    return set_gold(player_data, get_gold(player_data) + int(amount))

def spend_gold(player_data: dict, amount: int) -> bool:
    cur = get_gold(player_data)
    if cur >= amount:
        set_gold(player_data, cur - amount)
        return True
    return False

def get_gems(player_data: dict) -> int:
    return int(player_data.get("gems", 0))

def set_gems(player_data: dict, value: int) -> dict:
    player_data["gems"] = max(0, int(value))
    return player_data

def add_gems(player_data: dict, amount: int) -> dict:
    return set_gems(player_data, get_gems(player_data) + int(amount))

def spend_gems(player_data: dict, amount: int) -> bool:
    cur = get_gems(player_data)
    if cur >= amount:
        set_gems(player_data, cur - amount)
        return True
    return False

# --- Gerenciamento de Itens ---
def add_item_to_inventory(player_data: dict, item_id: str, quantity: int = 1) -> dict:
    inventory = player_data.get("inventory", {})
    
    # Se o item já existe como dicionário (item único/equipamento), não empilha
    if item_id in inventory and isinstance(inventory[item_id], dict):
        # Gera um novo ID único se for equipamento repetido (lógica simplificada)
        import uuid
        new_uid = f"{item_id}_{str(uuid.uuid4())[:8]}"
        return add_item_to_inventory(player_data, new_uid, quantity)

    current_qty = inventory.get(item_id, 0)
    if isinstance(current_qty, dict): current_qty = 1 
    
    inventory[item_id] = int(current_qty) + int(quantity)
    player_data["inventory"] = inventory
    return player_data

def remove_item_from_inventory(player_data: dict, item_id: str, quantity: int = 1) -> bool:
    inventory = player_data.get("inventory", {})
    if item_id not in inventory: return False
    
    current = inventory[item_id]
    
    # Se for item único (dict), remove direto
    if isinstance(current, dict):
        del inventory[item_id]
        player_data["inventory"] = inventory
        return True
        
    # Se for quantidade
    current_qty = int(current)
    if current_qty < quantity: return False
    
    new_qty = current_qty - quantity
    if new_qty <= 0:
        del inventory[item_id]
    else:
        inventory[item_id] = new_qty
        
    player_data["inventory"] = inventory
    return True

def has_item(player_data: dict, item_id: str, quantity: int = 1) -> bool:
    inv = player_data.get("inventory", {})
    val = inv.get(item_id)
    if val is None: return False
    if isinstance(val, dict): return quantity == 1
    return int(val) >= quantity

def consume_item(player_data: dict, item_id: str, quantity: int = 1) -> bool:
    return remove_item_from_inventory(player_data, item_id, quantity)

def add_unique_item(player_data: dict, unique_id: str, item_data: dict):
    inventory = player_data.get("inventory", {})
    inventory[unique_id] = item_data
    player_data["inventory"] = inventory

# ==============================================================================
# ⚔️ LÓGICA DE EQUIPAMENTOS (CORRIGIDA)
# ==============================================================================

async def equip_unique_item_for_user(user_id: Union[int, str], unique_id: str, slot_from_item: str = None) -> Tuple[bool, str]:
    from modules import player_manager
    from modules.player.stats import get_player_total_stats # Import local para evitar ciclo
    
    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return False, "Jogador não encontrado."
    
    inventory = pdata.get("inventory", {})
    item = inventory.get(unique_id)
    
    if not item or not isinstance(item, dict):
        return False, "Item não encontrado ou inválido."

    # Determina o slot correto
    if not slot_from_item:
        base_id = item.get("base_id")
        # Busca no ITEMS_DATA ou ITEM_BASES
        info = (game_data.ITEMS_DATA or {}).get(base_id) or (game_data.ITEM_BASES or {}).get(base_id, {})
        slot_from_item = info.get("slot")
        
    if not slot_from_item:
        return False, "Este item não pode ser equipado (sem slot definido)."

    slot_key = slot_from_item.lower()

    # Verifica requisitos de classe (Melhorado)
    req_class = item.get("required_class")
    if req_class and req_class.lower() != "any":
        p_class = str(pdata.get("class") or "aventureiro").lower()
        if req_class.lower() != p_class:
             return False, f"Classe requerida: {req_class.capitalize()}"

    # Lógica de Troca
    equipment = pdata.get("equipment", {})
    if not isinstance(equipment, dict): equipment = {}
    
    # Atualiza o slot
    equipment[slot_key] = unique_id
    pdata["equipment"] = equipment
    
    totals = await get_player_total_stats(pdata)
    for stat in ['attack', 'defense', 'initiative', 'luck', 'max_hp']:
        pdata[stat] = totals.get(stat, 1)
    
    # Garante que o HP atual não ultrapasse o novo máximo
    pdata['current_hp'] = min(pdata.get('current_hp', 1), pdata['max_hp'])
    
    # Salva no banco
    await player_manager.save_player_data(user_id, pdata)
    
    return True, f"✅ Item equipado em: <b>{slot_key.capitalize()}</b>."

async def unequip_item_for_user(user_id: Union[int, str], slot: str) -> Tuple[bool, str]:
    from modules import player_manager
    from modules.player.stats import get_player_total_stats
    
    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return False, "Erro de dados."
    
    equipment = pdata.get("equipment", {})
    if not isinstance(equipment, dict) or not equipment.get(slot):
        return False, "Nada para desequipar."
        
    # Remove a referência
    equipment[slot] = None
    pdata["equipment"] = equipment
    
    # --- Recalcula status após remover ---
    totals = await get_player_total_stats(pdata)
    for stat in ['attack', 'defense', 'initiative', 'luck', 'max_hp']:
        if stat in totals:
            pdata[stat] = totals[stat]
    
    pdata['current_hp'] = min(pdata.get('current_hp', 1), pdata['max_hp'])
    
    await player_manager.save_player_data(user_id, pdata)
    return True, f"Item desequipado de {slot.capitalize()}."