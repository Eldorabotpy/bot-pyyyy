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
# 🏅 MEDALHAS DE CLÃ
# ==============================================================================

def get_medalhas_cla(
    player_data: dict,
) -> int:
    return int(
        player_data.get(
            "medalhas_cla",
            0,
        )
        or 0
    )


def set_medalhas_cla(
    player_data: dict,
    value: int,
) -> dict:

    player_data[
        "medalhas_cla"
    ] = max(
        0,
        int(value),
    )

    return player_data


def add_medalhas_cla(
    player_data: dict,
    amount: int,
) -> dict:

    return set_medalhas_cla(
        player_data,
        get_medalhas_cla(
            player_data
        )
        +
        int(amount),
    )


def spend_medalhas_cla(
    player_data: dict,
    amount: int,
) -> bool:

    amount = int(
        amount
    )

    if amount <= 0:
        return False


    atual = get_medalhas_cla(
        player_data
    )


    if atual < amount:
        return False


    set_medalhas_cla(
        player_data,
        atual - amount,
    )

    return True

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
    if item_id not in inventory: 
        return False
    
    current = inventory[item_id]
    
    # SE FOR DICIONÁRIO (Seu caso atual para materiais)
    if isinstance(current, dict):
        current_qty = int(current.get("quantity", 0))
        if current_qty < quantity: 
            return False
        
        new_qty = current_qty - quantity
        if new_qty <= 0:
            del inventory[item_id] # Remove se zerar
        else:
            inventory[item_id]["quantity"] = new_qty # ✅ CORREÇÃO: Atualiza apenas a quantidade
        
        player_data["inventory"] = inventory
        return True
        
    # Se for item empilhável (int)
    current_qty = int(current)
    if current_qty < quantity: 
        return False
    
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

async def _recalcular_status_e_salvar(user_id: str, pdata: dict) -> dict:
    """Recalcula status oficiais, salva o documento inteiro e limpa cache."""
    from modules import player_manager
    from modules.player.combat_stats import get_combat_stats, aplicar_combat_stats_no_player
    from modules.player.core import clear_player_cache

    stats = await get_combat_stats(pdata)
    pdata = aplicar_combat_stats_no_player(pdata, stats)

    await player_manager.save_player_data(user_id, pdata)

    try:
        await clear_player_cache(user_id)
        if pdata.get("_id"):
            await clear_player_cache(pdata.get("_id"))
    except Exception:
        pass

    return stats


async def equip_unique_item_for_user(user_id: str, unique_id: str, slot_from_item: str = None) -> Tuple[bool, str]:
    """
    Equipa item único e sincroniza status oficiais.
    user_id DEVE ser ObjectId string da collection users.
    """
    from modules import player_manager

    user_id = str(user_id or "").strip()
    unique_id = str(unique_id or "").strip()

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        return False, "Jogador não encontrado."

    inventory = pdata.get("inventory", {})
    if not isinstance(inventory, dict):
        inventory = {}

    item = inventory.get(unique_id)
    if not item or not isinstance(item, dict):
        return False, "Item não encontrado no inventário ou inválido."

    base_id = item.get("base_id") or unique_id
    info = (game_data.ITEMS_DATA or {}).get(base_id) or (game_data.ITEM_BASES or {}).get(base_id, {}) or {}

    if not slot_from_item:
        slot_from_item = item.get("slot") or info.get("slot")

    if not slot_from_item:
        return False, "Este item não pode ser equipado (sem slot definido)."

    slot_key = str(slot_from_item).strip().lower()

    # Requisito de classe: aceita required_class, class_req e lista.
    req_class = item.get("required_class") or info.get("required_class") or item.get("class_req") or info.get("class_req")
    if req_class:
        p_class = str(pdata.get("class") or pdata.get("class_key") or "aventureiro").lower()
        if isinstance(req_class, (list, tuple, set)):
            permitidas = [str(x).lower() for x in req_class]
            if "any" not in permitidas and p_class not in permitidas:
                return False, f"Classe requerida: {', '.join(permitidas)}"
        elif str(req_class).lower() != "any" and str(req_class).lower() != p_class:
            return False, f"Classe requerida: {str(req_class).capitalize()}"

    equipment = pdata.get("equipment", {})
    if not isinstance(equipment, dict):
        equipment = {}

    # Ferramentas ficam em equipment_tools por profissão.
    if slot_key == "tool":
        equipment_tools = pdata.get("equipment_tools", {})
        if not isinstance(equipment_tools, dict):
            equipment_tools = {}

        tool_type = str(
            info.get("tool_type") or item.get("tool_type") or ""
        ).strip().lower()

        if not tool_type:
            return False, "Ferramenta sem tipo de profissão."

        # Migra slot antigo, se existir.
        legacy_uid = equipment.get("tool")
        if legacy_uid and legacy_uid in inventory:
            legacy_item = inventory.get(legacy_uid)
            if isinstance(legacy_item, dict):
                legacy_base = legacy_item.get("base_id") or legacy_uid
                legacy_info = (game_data.ITEMS_DATA or {}).get(legacy_base) or (game_data.ITEM_BASES or {}).get(legacy_base, {}) or {}
                legacy_type = str(legacy_info.get("tool_type") or legacy_item.get("tool_type") or "").strip().lower()
                if legacy_type and legacy_type not in equipment_tools:
                    equipment_tools[legacy_type] = legacy_uid

        equipment.pop("tool", None)
        equipment_tools[tool_type] = unique_id
        pdata["equipment_tools"] = equipment_tools
    else:
        equipment[slot_key] = unique_id

    pdata["equipment"] = equipment

    stats = await _recalcular_status_e_salvar(user_id, pdata)

    print(
        f"✅ [EQUIPAR] {pdata.get('character_name', user_id)} slot={slot_key} item={base_id} "
        f"ATK={stats.get('attack')} DEF={stats.get('defense')} HP={stats.get('max_hp')} MP={stats.get('max_mana')}"
    )

    return True, f"✅ Item equipado em: <b>{slot_key.capitalize()}</b>."


async def unequip_item_for_user(user_id: str, slot: str) -> Tuple[bool, str]:
    """
    Desequipa item e sincroniza status oficiais.
    user_id DEVE ser ObjectId string da collection users.
    """
    from modules import player_manager

    user_id = str(user_id or "").strip()
    slot = str(slot or "").strip().lower()

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        return False, "Erro de dados."

    equipment = pdata.get("equipment", {})
    if not isinstance(equipment, dict):
        equipment = {}

    equipment_tools = pdata.get("equipment_tools", {})
    if not isinstance(equipment_tools, dict):
        equipment_tools = {}

    removeu = False

    if slot.startswith("tool_"):
        prof_key = slot.replace("tool_", "", 1)
        if equipment_tools.get(prof_key):
            equipment_tools.pop(prof_key, None)
            removeu = True
    elif slot == "tool":
        if equipment.get("tool"):
            equipment.pop("tool", None)
            removeu = True
        elif equipment_tools:
            # fallback: remove a primeira ferramenta encontrada.
            first_key = next(iter(equipment_tools.keys()))
            equipment_tools.pop(first_key, None)
            removeu = True
    else:
        if equipment.get(slot):
            equipment[slot] = None
            removeu = True

    if not removeu:
        return False, "Nada para desequipar neste slot."

    pdata["equipment"] = equipment
    pdata["equipment_tools"] = equipment_tools

    stats = await _recalcular_status_e_salvar(user_id, pdata)

    print(
        f"✅ [DESEQUIPAR] {pdata.get('character_name', user_id)} slot={slot} "
        f"ATK={stats.get('attack')} DEF={stats.get('defense')} HP={stats.get('max_hp')} MP={stats.get('max_mana')}"
    )

    return True, f"Item desequipado de {slot.capitalize()}."