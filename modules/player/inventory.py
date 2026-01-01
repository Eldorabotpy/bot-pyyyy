# modules/player/inventory.py
# (VERSÃO BLINDADA: Suporte a Auth Híbrida)

import uuid
import logging
from typing import Tuple, Optional, List, Union, Dict, Any
from bson import ObjectId

from modules import game_data
from . import stats 
from modules.game_data.class_evolution import get_class_ancestry
from modules.game_data.skins import SKIN_CATALOG
from modules.player import stats as player_stats_helper

logger = logging.getLogger(__name__)

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
    if amount < 0: return False
    cur = get_gold(player_data)
    if cur >= amount:
        set_gold(player_data, cur - amount)
        return True
    return False

def get_gems(player_data: dict) -> int:
    # Tenta chaves comuns para gemas
    val = player_data.get("gems") or player_data.get("gemas") or 0
    return int(val)

def set_gems(player_data: dict, value: int) -> dict:
    val = max(0, int(value))
    # Salva nas duas chaves para garantir compatibilidade
    player_data["gems"] = val
    player_data["gemas"] = val
    return player_data

def add_gems(player_data: dict, amount: int) -> dict:
    cur = get_gems(player_data)
    return set_gems(player_data, cur + int(amount))

def spend_gems(player_data: dict, amount: int) -> bool:
    amount = int(amount)
    if amount < 0: return False
    cur = get_gems(player_data)
    if cur >= amount:
        set_gems(player_data, cur - amount)
        return True
    return False

# ========================================
# GERENCIAMENTO DE ITENS
# ========================================

def get_inventory(player_data: dict) -> dict:
    if "inventory" not in player_data:
        player_data["inventory"] = {}
    return player_data["inventory"]

def has_item(player_data: dict, item_id: str, quantity: int = 1) -> bool:
    inv = get_inventory(player_data)
    entry = inv.get(item_id)
    if not entry: return False

    if isinstance(entry, dict):
        # Item unique ou com metadata
        q = int(entry.get("quantity", 1))
        return q >= quantity
    else:
        # Item simples (int)
        return int(entry) >= quantity

def add_item_to_inventory(player_data: dict, item_id: str, quantity: int = 1) -> dict:
    """
    Adiciona item stackable (comum) ao inventário.
    """
    inv = get_inventory(player_data)
    current = inv.get(item_id, 0)
    
    if isinstance(current, dict):
        # Se já existe como dict, soma na quantity
        new_q = int(current.get("quantity", 0)) + quantity
        current["quantity"] = new_q
        inv[item_id] = current
    else:
        # Se é int ou não existe
        inv[item_id] = int(current) + quantity
        
    player_data["inventory"] = inv
    return player_data

def remove_item_from_inventory(player_data: dict, item_id: str, quantity: int = 1) -> bool:
    inv = get_inventory(player_data)
    current = inv.get(item_id)
    if not current: return False

    if isinstance(current, dict):
        q = int(current.get("quantity", 1))
        if q < quantity: return False
        q -= quantity
        if q <= 0:
            del inv[item_id]
        else:
            current["quantity"] = q
            inv[item_id] = current
        return True
    else:
        val = int(current)
        if val < quantity: return False
        val -= quantity
        if val <= 0:
            del inv[item_id]
        else:
            inv[item_id] = val
        return True

def consume_item(player_data: dict, item_id: str, quantity: int = 1) -> bool:
    return remove_item_from_inventory(player_data, item_id, quantity)

# ========================================
# ITENS ÚNICOS (EQUIPAMENTOS)
# ========================================

def add_unique_item(player_data: dict, item_data: dict) -> str:
    """
    Adiciona um item único (dicionário completo) ao inventário.
    Gera um UUID se não tiver.
    Retorna o ID único gerado.
    """
    inv = get_inventory(player_data)
    
    # Garante que tem um ID único
    unique_id = item_data.get("unique_id")
    if not unique_id:
        unique_id = str(uuid.uuid4())
        item_data["unique_id"] = unique_id
    
    # Se já existe, substitui (overwrite) ou gera novo ID? 
    # Por segurança, se colidir, gera novo.
    if unique_id in inv:
        unique_id = str(uuid.uuid4())
        item_data["unique_id"] = unique_id

    # Garante quantidade 1 para uniques
    item_data["quantity"] = 1
    
    inv[unique_id] = item_data
    return unique_id

def is_unique_item_entry(entry: Any) -> bool:
    return isinstance(entry, dict) and "base_id" in entry

def get_unique_item(player_data: dict, unique_id: str) -> Optional[dict]:
    inv = get_inventory(player_data)
    entry = inv.get(unique_id)
    if is_unique_item_entry(entry):
        return entry
    return None

# ========================================
# EQUIPAR / DESEQUIPAR
# ========================================

def can_equip_slot(slot: str) -> bool:
    valid_slots = {
        "weapon", "helmet", "armor", "legs", "boots", 
        "accessory", "ring", "amulet", "shield", "artifact"
    }
    return slot in valid_slots

def _get_item_slot_from_base(base_id: str) -> Optional[str]:
    # Tenta pegar do game_data se disponível
    if not base_id: return None
    item_info = (game_data.ITEMS_DATA or {}).get(base_id)
    if item_info:
        return item_info.get("slot")
    return None

def _get_unique_item_from_inventory(player_data: dict, unique_id: str) -> Optional[dict]:
    inv = player_data.get("inventory", {}) or {}
    val = inv.get(unique_id)
    return val if is_unique_item_entry(val) else None

async def equip_unique_item_for_user(user_id: Union[int, str], unique_id: str, expected_slot: Optional[str] = None) -> Tuple[bool, str]:
    """
    Equipa um item no jogador.
    Suporta user_id Híbrido (Int ou Str).
    """
    # IMPORTANTE: Usamos o player_manager para garantir a busca segura (blindada)
    # Evitamos importar do .core diretamente pois ele pode não tratar string corretamente ainda
    from modules import player_manager 
    
    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return False, "Jogador não encontrado."

    item = _get_unique_item_from_inventory(pdata, unique_id)
    if not item: return False, "Item não encontrado no inventário."

    base_id = item.get("base_id")
    # Prioridade: Slot salvo no item > Slot do banco de dados > None
    slot_from_item = item.get("slot") or _get_item_slot_from_base(base_id)
    
    if not slot_from_item: return False, "Item sem slot reconhecido."

    slot_from_item = str(slot_from_item).strip().lower()
    if not can_equip_slot(slot_from_item): return False, f"Slot inválido: {slot_from_item}"

    # Validação extra de slot esperado (ex: clicar no slot de Capacete e tentar equipar Bota)
    if expected_slot and expected_slot.strip().lower() != slot_from_item:
        return False, f"Este item é do slot '{slot_from_item}', não '{expected_slot}'."

    # Verifica requisitos de classe/nível (Opcional, mas recomendado)
    req_class = item.get("required_class")
    if req_class:
        p_class = pdata.get("class", "aventueiro")
        # Lógica simples de verificação (pode expandir se tiver subclasses)
        if req_class != "any" and req_class != p_class:
             return False, f"Classe requerida: {req_class}"

    # Lógica de Troca (Swap)
    equipment = pdata.get("equipment", {})
    old_equipped_id = equipment.get(slot_from_item)

    # Se já tem algo equipado, "desequipa" logicamente (o item volta pro pool disponível)
    # Como nosso inventário é único (tudo fica no inventory), não precisamos mover nada,
    # apenas atualizar o ponteiro do slot.
    
    equipment[slot_from_item] = unique_id
    pdata["equipment"] = equipment
    
    # Atualiza stats totais
    await player_manager.save_player_data(user_id, pdata)
    
    return True, f"Item equipado em {slot_from_item}."

async def unequip_item_for_user(user_id: Union[int, str], slot: str) -> Tuple[bool, str]:
    from modules import player_manager
    
    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return False, "Jogador não encontrado."
    
    equipment = pdata.get("equipment", {})
    if not equipment.get(slot):
        return False, "Nada equipado neste slot."
        
    # Remove a referência
    del equipment[slot]
    pdata["equipment"] = equipment
    
    await player_manager.save_player_data(user_id, pdata)
    return True, "Item desequipado."