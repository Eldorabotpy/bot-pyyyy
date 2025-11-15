# Em modules/player/inventory.py
# (VERSÃO CORRIGIDA - 'equip_unique_item_for_user' ASSÍNCRONA E LÓGICA DE CLASSE CORRIGIDA)

import uuid
from typing import Tuple, Optional, List
from modules import game_data
from . import stats # Importa o nosso novo módulo de stats para usar as suas funções
# --- CORREÇÃO 1: Importa a função de ancestralidade ---
from modules.game_data.class_evolution import get_class_ancestry


# ========================================
# CONSTANTES
# ========================================
GOLD_KEY = "ouro"
GEMS_KEY_PT = "gemas"
GEMS_KEY_EN = "gems"
GEM_KEYS = {GEMS_KEY_PT, GEMS_KEY_EN}

# ========================================
# OURO E GEMAS
# ========================================

def get_gold(player_data: dict) -> int:
    return int(player_data.get("gold", 0))

def set_gold(player_data: dict, value: int) -> dict:
    player_data["gold"] = max(0, int(value))
    return player_data

def add_gold(player_data: dict, amount: int) -> dict:
    cur = get_gold(player_data)
    return set_gold(player_data, cur + int(amount))

def spend_gold(player_data: dict, amount: int) -> bool:
    amount = int(amount)
    if amount <= 0:
        return True
    cur = get_gold(player_data)
    if cur < amount:
        return False
    set_gold(player_data, cur - amount)
    return True

def get_gems(player_data: dict) -> int:
    try:
        return int(player_data.get("gems", player_data.get(GEMS_KEY_PT, 0)))
    except Exception:
        return 0

def set_gems(player_data: dict, value: int) -> dict:
    val = max(0, int(value))
    player_data["gems"] = val
    if GEMS_KEY_PT in player_data:
        player_data[GEMS_KEY_PT] = val
    return player_data

def add_gems(player_data: dict, amount: int) -> dict:
    cur = get_gems(player_data)
    return set_gems(player_data, cur + int(amount))

def spend_gems(player_data: dict, amount: int) -> bool:
    amt = int(amount)
    if amt <= 0:
        return True
    cur = get_gems(player_data)
    if cur < amt:
        return False
    set_gems(player_data, cur - amt)
    return True

async def _sanitize_and_migrate_gold(player_data: dict) -> bool:
    """Migra ouro/gemas legados do inventário para campos de topo."""
    inv = player_data.get("inventory", {}) or {}
    changed = False 
    
    raw_gold = inv.get(GOLD_KEY)
    
    try:
        player_data["gold"] = int(player_data.get("gold", 0))
    except Exception:
        player_data["gold"] = 0
        
    if isinstance(raw_gold, (int, float)):
        add_gold(player_data, int(raw_gold)) # Síncrono
        inv.pop(GOLD_KEY, None)
        changed = True # Marca que mudou

    for gk in GEM_KEYS:
        raw_gems = inv.get(gk)
        if isinstance(raw_gems, (int, float)):
            set_gems(player_data, get_gems(player_data) + int(raw_gems)) # Síncrono
            inv.pop(gk, None)
            changed = True # Marca que mudou

    player_data["inventory"] = inv
    return changed

# ========================================
# INVENTÁRIO E ITENS
# ========================================

def add_item_to_inventory(player_data: dict, item_id: str, quantity: int = 1):
    qty = int(quantity)
    if qty == 0:
        return player_data
    
    if item_id == GOLD_KEY:
        if qty > 0: add_gold(player_data, qty)
        else: spend_gold(player_data, -qty)
        return player_data

    if item_id in GEM_KEYS:
        if qty > 0: add_gems(player_data, qty)
        else: spend_gems(player_data, -qty)
        return player_data

    inventory = player_data.setdefault('inventory', {})
    current = int(inventory.get(item_id, 0))
    new_val = current + qty
    if new_val <= 0:
        if item_id in inventory:
            del inventory[item_id]
    else:
        inventory[item_id] = new_val
    return player_data

def add_unique_item(player_data: dict, item_instance: dict) -> str:
    inventory = player_data.setdefault('inventory', {})
    unique_id = str(uuid.uuid4())
    inventory[unique_id] = item_instance
    return unique_id

def remove_item_from_inventory(player_data: dict, item_id: str, quantity: int = 1) -> bool:
    if item_id == GOLD_KEY:
        return spend_gold(player_data, int(quantity))
    if item_id in GEM_KEYS:
        return spend_gems(player_data, int(quantity))
    inventory = player_data.get('inventory', {})
    if item_id not in inventory:
        return False
    if isinstance(inventory[item_id], dict):
        del inventory[item_id]
        return True
    qty = int(quantity)
    have = int(inventory[item_id])
    if have >= qty > 0:
        new_val = have - qty
        if new_val <= 0:
            del inventory[item_id]
        else:
            inventory[item_id] = new_val
        return True
    return False

def has_item(player_data: dict, item_id: str, quantity: int = 1) -> bool:
    inv = player_data.get("inventory", {})
    return inv.get(item_id, 0) >= int(quantity)

def consume_item(player_data: dict, item_id: str, quantity: int = 1) -> bool:
    if not has_item(player_data, item_id, quantity):
        return False
    return remove_item_from_inventory(player_data, item_id, quantity)

# ========================================
# EQUIPAMENTOS
# ========================================

def is_unique_item_entry(value) -> bool:
    return isinstance(value, dict) and ("base_id" in value or "tpl" in value or "id" in value)

def get_equipped_map(player_data: dict) -> dict:
    inv = player_data.get("inventory", {}) or {}
    eq  = player_data.get("equipment", {}) or {}
    out = {}
    for slot, uid in (eq or {}).items():
        if not uid:
            out[slot] = (None, None); continue
        inst = inv.get(uid)
        if is_unique_item_entry(inst):
            out[slot] = (uid, inst)
        else:
            out[slot] = (None, None)
    return out

def can_equip_slot(slot: str) -> bool:
    # Garante que a verificação é robusta, mesmo que slot seja None
    return (slot or "").lower() in {"arma","elmo","armadura","calca","luvas","botas","colar","anel","brinco"}

def _class_req_from_base(base_id: Optional[str]):
    if not base_id:
        return None
    base = game_data.ITEMS_DATA.get(base_id) or {}
    return base.get("class_req")

# =========================================================================
# --- CORREÇÃO 2: LÓGICA DE VERIFICAÇÃO DE CLASSE (SUBSTITUIR) ---
# =========================================================================
def is_item_allowed_for_player_class(player_data: dict, item: dict) -> Tuple[bool, Optional[str]]:
    """
    Verifica se o jogador pode equipar o item, checando a ancestralidade da classe.
    (Ex: "Arquimago" pode equipar itens "Mago").
    """
    player_class_key = stats._get_class_key_normalized(player_data)
    req = item.get("class_req") or _class_req_from_base(item.get("base_id"))
    
    if not req:
        return True, None # Item não tem restrição de classe

    # Garante que req_list_lower seja uma lista de strings
    if isinstance(req, str):
        req_list_lower = [req.strip().lower()]
    elif isinstance(req, (list, tuple)):
        req_list_lower = [str(x).strip().lower() for x in req]
    else:
        req_list_lower = [] # Formato desconhecido
    
    if not req_list_lower:
        return True, None # Lista de restrição vazia
        
    if not player_class_key:
        return False, "Classe do jogador não definida."

    # --- LÓGICA DE ANCESTRALIDADE ---
    # Pega a lista de classes (ex: ['arquimago', 'elementalista', 'mago'])
    ancestry = get_class_ancestry(player_class_key)
    
    for class_node in ancestry:
        if class_node in req_list_lower:
            return True, None # Encontrou! (ex: "mago" está em ["mago"])

    # Se chegou aqui, não pode equipar
    disp = item.get("display_name") or item.get("base_id") or "item"
    
    # --- !!! AQUI ESTÁ A CORREÇÃO (NameError) !!! ---
    # Usando 'req_list_lower' em vez de 'req_list'
    return False, f"⚠️ {disp} é exclusivo para {', '.join(req_list_lower)}."
# =========================================================================
# --- FIM DA CORREÇÃO 2 ---
# =========================================================================

def _get_item_slot_from_base(base_id: Optional[str]) -> Optional[str]:
    if not base_id: return None
    entry = game_data.ITEMS_DATA.get(base_id) or {}
    
    # (Lógica melhorada que usamos no equipment_handler)
    slot = entry.get("slot")
    if slot and isinstance(slot, str):
        slot_lower = slot.strip().lower()
        if can_equip_slot(slot_lower):
            return slot_lower
        
    slot_type = entry.get("type")
    if slot_type and isinstance(slot_type, str):
        slot_type_lower = slot_type.strip().lower()
        if can_equip_slot(slot_type_lower):
            return slot_type_lower
            
    return None

def _get_unique_item_from_inventory(player_data: dict, unique_id: str) -> Optional[dict]:
    inv = player_data.get("inventory", {}) or {}
    val = inv.get(unique_id)
    return val if is_unique_item_entry(val) else None

# (Função já estava corrigida com 'async' e 'await' na sua versão)
async def equip_unique_item_for_user(user_id: int, unique_id: str, expected_slot: Optional[str] = None) -> Tuple[bool, str]:
    from .core import get_player_data, save_player_data 
    
    pdata = await get_player_data(user_id)
    if not pdata:
        return False, "Jogador não encontrado."

    item = _get_unique_item_from_inventory(pdata, unique_id)
    if not item:
        return False, "Item não encontrado no inventário."

    base_id = item.get("base_id")
    slot_from_item = _get_item_slot_from_base(base_id) or item.get("slot")
    if not slot_from_item:
        return False, "Item sem slot reconhecido."

    slot_from_item = str(slot_from_item).strip().lower()
    if not can_equip_slot(slot_from_item):
        return False, f"Slot inválido: {slot_from_item}"

    if expected_slot and expected_slot.strip().lower() != slot_from_item:
        return False, f"Este item é do slot '{slot_from_item}', não '{expected_slot.strip().lower()}'."

    # (Agora chama a função de verificação CORRIGIDA)
    ok, err = is_item_allowed_for_player_class(pdata, item)
    if not ok:
        return False, err or "Sua classe não pode equipar este item."

    eq = pdata.setdefault("equipment", {})
    eq[slot_from_item] = unique_id

    await save_player_data(user_id, pdata)
    name = item.get("display_name") or base_id or "Item"
    return True, f"Equipado {name} em {slot_from_item}."