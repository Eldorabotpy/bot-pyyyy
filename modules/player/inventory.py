# modules/player/inventory.py
# (VERSÃO FINAL: CORRIGIDA PARA add_unique_item INTELIGENTE)

import logging
import uuid
from typing import Tuple, Union, Dict
from modules import game_data

logger = logging.getLogger(__name__)

# ==============================================================================
# ECONOMIA (GOLD & GEMS)
# ==============================================================================
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

# ==============================================================================
# GERENCIAMENTO DE ITENS (INVENTÁRIO)
# ==============================================================================

def add_item_to_inventory(player_data: dict, item_id: str, quantity: int = 1) -> dict:
    inventory = player_data.get("inventory", {})
    
    # Se o item já existe como dicionário (item único/equipamento), não empilha
    if item_id in inventory and isinstance(inventory[item_id], dict):
        # Gera um novo ID único para evitar sobreposição
        new_uid = f"{item_id}_{str(uuid.uuid4())[:8]}"
        return add_item_to_inventory(player_data, new_uid, quantity)

    current_qty = inventory.get(item_id, 0)
    # Proteção: se por acaso existir um dict onde deveria ser int
    if isinstance(current_qty, dict): current_qty = 1 
    
    inventory[item_id] = int(current_qty) + int(quantity)
    player_data["inventory"] = inventory
    return player_data

def remove_item_from_inventory(player_data: dict, item_id: str, quantity: int = 1) -> bool:
    inventory = player_data.get("inventory", {})
    if item_id not in inventory: return False
    
    current = inventory[item_id]
    
    # Se for item único (dict), remove direto (quantidade irrelevante, remove 1 unidade lógica)
    if isinstance(current, dict):
        del inventory[item_id]
        player_data["inventory"] = inventory
        return True
        
    # Se for item empilhável (int)
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

# ✅ CORREÇÃO AQUI: Função inteligente que aceita 2 ou 3 argumentos
def add_unique_item(player_data: dict, unique_id_or_item: Union[str, dict], item_data: dict = None) -> str:
    """
    Adiciona um item único ao inventário.
    Compatível com chamadas:
      1. add_unique_item(pdata, item_dict)          -> Novo padrão (extrai 'uuid' do dict)
      2. add_unique_item(pdata, uid_str, item_dict) -> Padrão antigo/manual
    Retorna o UID do item adicionado.
    """
    final_uid = None
    final_item = None

    # Caso 1: Chamada nova (2 argumentos: pdata, item_dict)
    # O segundo argumento é o dicionário do item
    if isinstance(unique_id_or_item, dict) and item_data is None:
        final_item = unique_id_or_item
        final_uid = final_item.get("uuid")
        
        # Se o item não tiver UID, geramos um agora
        if not final_uid:
            final_uid = str(uuid.uuid4())
            final_item["uuid"] = final_uid 
            
    # Caso 2: Chamada antiga (3 argumentos: pdata, uid_str, item_dict)
    elif isinstance(unique_id_or_item, str) and isinstance(item_data, dict):
        final_uid = unique_id_or_item
        final_item = item_data
        # Garante que o UUID esteja dentro do item também
        if "uuid" not in final_item:
            final_item["uuid"] = final_uid
        
    else:
        # Fallback de erro
        logger.error(f"add_unique_item: Assinatura inválida. Args: {type(unique_id_or_item)}, {type(item_data)}")
        return None

    # Adiciona ao inventário
    inventory = player_data.get("inventory", {})
    inventory[final_uid] = final_item
    player_data["inventory"] = inventory
    
    return final_uid

# ==============================================================================
# ⚔️ LÓGICA DE EQUIPAMENTOS (FIX: APENAS STR ID)
# ==============================================================================

async def equip_unique_item_for_user(user_id: str, unique_id: str, slot_from_item: str = None) -> Tuple[bool, str]:
    """
    Equipa um item.
    user_id DEVE ser a string do ObjectId da collection 'users'.
    """
    from modules import player_manager
    from modules.player.stats import get_player_total_stats
    
    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return False, "Jogador não encontrado."
    
    inventory = pdata.get("inventory", {})
    item = inventory.get(unique_id)
    
    if not item or not isinstance(item, dict):
        return False, "Item não encontrado no inventário ou inválido."

    # 1. Determina o slot correto
    if not slot_from_item:
        base_id = item.get("base_id")
        # Busca metadados estáticos do jogo
        info = (game_data.ITEMS_DATA or {}).get(base_id) or (game_data.ITEM_BASES or {}).get(base_id, {})
        slot_from_item = info.get("slot")
        
    if not slot_from_item:
        return False, "Este item não pode ser equipado (sem slot definido)."

    slot_key = slot_from_item.lower()

    # 2. Verifica Requisitos de Classe
    req_class = item.get("required_class")
    if req_class and str(req_class).lower() != "any":
        p_class = str(pdata.get("class") or "aventureiro").lower()
        if str(req_class).lower() != p_class:
             return False, f"Classe requerida: {str(req_class).capitalize()}"

    # 3. Atualiza Equipamento
    equipment = pdata.get("equipment", {})
    if not isinstance(equipment, dict): equipment = {}
    
    # Se já tiver algo equipado, o sistema de inventário apenas troca os ponteiros
    equipment[slot_key] = unique_id
    pdata["equipment"] = equipment
    
    # 4. Recalcula Status Imediatamente (Para persistir Max HP/MP corretos)
    totals = await get_player_total_stats(pdata)
    for stat in ['attack', 'defense', 'initiative', 'luck', 'max_hp', 'max_mana']:
        if stat in totals:
            pdata[stat] = totals.get(stat)
    
    # Ajusta HP/MP atual para não ultrapassar o novo máximo
    pdata['current_hp'] = min(pdata.get('current_hp', 1), pdata.get('max_hp', 50))
    
    # 5. Salva
    await player_manager.save_player_data(user_id, pdata)
    
    return True, f"✅ Item equipado em: <b>{slot_key.capitalize()}</b>."

async def unequip_item_for_user(user_id: str, slot: str) -> Tuple[bool, str]:
    """
    Desequipa um item.
    user_id DEVE ser a string do ObjectId da collection 'users'.
    """
    from modules import player_manager
    from modules.player.stats import get_player_total_stats
    
    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return False, "Erro de dados."
    
    equipment = pdata.get("equipment", {})
    if not isinstance(equipment, dict) or not equipment.get(slot):
        return False, "Nada para desequipar neste slot."
        
    # 1. Remove a referência do slot
    equipment[slot] = None
    pdata["equipment"] = equipment
    
    # 2. Recalcula Status
    totals = await get_player_total_stats(pdata)
    for stat in ['attack', 'defense', 'initiative', 'luck', 'max_hp', 'max_mana']:
        if stat in totals:
            pdata[stat] = totals[stat]
    
    # Ajusta HP atual
    pdata['current_hp'] = min(pdata.get('current_hp', 1), pdata.get('max_hp', 50))
    
    # 3. Salva
    await player_manager.save_player_data(user_id, pdata)
    
    return True, f"Item desequipado de {slot.capitalize()}."