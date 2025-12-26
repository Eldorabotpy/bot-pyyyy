# modules/market_manager.py
# (VERSÃO CORRIGIDA: Transação de Ouro e Entrega de Itens Blindada)
from __future__ import annotations
import logging
import os
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from pymongo import MongoClient
from modules import player_manager

# --- CONFIGURAÇÃO DE LOGGING ---
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
MONGO_CONN_STR = os.getenv("MONGO_CONNECTION_STRING") or os.getenv("MONGO_URL")
if not MONGO_CONN_STR:
    MONGO_CONN_STR = "mongodb://localhost:27017/rpg_bot"

try:
    import certifi
    ca = certifi.where()
    client = MongoClient(MONGO_CONN_STR, tlsCAFile=ca)
    db = client["eldora_db"] 
    market_col = db["market_listings"]
    counters_col = db["counters"]
    # Garante índices
    market_col.create_index("id", unique=True)
    market_col.create_index("active")
except Exception as e:
    log.critical(f"🔥 FALHA AO CONECTAR MONGODB (MARKET): {e}")
    market_col = None
    counters_col = None

# Tenta importar utilitários de display e dados de jogo
try:
    from modules import display_utils
    from modules import game_data
    from modules.game_data.items_evolution import EVOLUTION_ITEMS_DATA
except ImportError:
    display_utils = None
    game_data = None
    EVOLUTION_ITEMS_DATA = {}

# --- LISTA NEGRA MANUAL ---
_BLOCKED_SPECIFIC_IDS = {
    "sigilo_protecao", "ticket_arena", "chave_da_catacumba", 
    "cristal_de_abertura", "gems", 
}

# =========================
# Erros e Helpers
# =========================
class MarketError(Exception): ...
class ListingNotFound(MarketError): ...
class ListingInactive(MarketError): ...
class InvalidListing(MarketError): ...
class PermissionDenied(MarketError): ...
class InsufficientQuantity(MarketError): ...
class InvalidPurchase(MarketError): ...

def _get_next_sequence(name: str) -> int:
    if counters_col is None: return 0
    ret = counters_col.find_one_and_update(
        {"_id": name}, {"$inc": {"seq": 1}}, upsert=True, return_document=True
    )
    return ret["seq"]

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _validate_price_qty(unit_price: int, quantity: int):
    if unit_price <= 0: raise InvalidListing("Preço deve ser maior que 0.")
    if quantity <= 0: raise InvalidListing("Quantidade deve ser maior que 0.")

# =========================
# CRUD
# =========================

def create_listing(
    *,
    seller_id: int,
    item_payload: dict,
    unit_price: int,
    quantity: int = 1,
    region_key: Optional[str] = None,
    target_buyer_id: Optional[int] = None,
    target_buyer_name: Optional[str] = None,
    seller_name: Optional[str] = None
) -> dict:
    if market_col is None: raise MarketError("Banco de dados offline.")
    
    _validate_price_qty(unit_price, quantity)

    base_id = item_payload.get("base_id")

    # Bloqueios de Itens
    if base_id and base_id in EVOLUTION_ITEMS_DATA:
        item_name = EVOLUTION_ITEMS_DATA[base_id].get("display_name", "Item de Evolução")
        raise InvalidListing(f"🚫 '{item_name}' deve ser vendido no Comércio de Relíquias (Gemas).")

    if base_id and base_id in _BLOCKED_SPECIFIC_IDS:
        raise InvalidListing(f"🚫 Este item ('{base_id}') não pode ser comercializado aqui.")

    lid = _get_next_sequence("market_id")

    listing = {
        "id": lid,
        "seller_id": int(seller_id),
        "seller_name": str(seller_name) if seller_name else None,
        "item": item_payload,
        "unit_price": int(unit_price),
        "quantity": int(quantity),
        "created_at": _now_iso(),
        "region_key": region_key,
        "active": True,
        "target_buyer_id": int(target_buyer_id) if target_buyer_id else None,
        "target_buyer_name": str(target_buyer_name) if target_buyer_name else None
    }

    market_col.insert_one(listing)
    log.info(f"[MARKET] Item #{lid} criado por {seller_id}.")
    return listing

def list_active(
    *,
    region_key: Optional[str] = None,
    base_id: Optional[str] = None,
    sort_by: str = "created_at",
    ascending: bool = False,
    page: int = 1,
    page_size: int = 20,
    price_per_unit: bool = False,
    viewer_id: Optional[int] = None
) -> List[dict]:
    if market_col is None: return []
    query = {"active": True}

    if region_key: query["region_key"] = region_key
    if base_id: query["item.base_id"] = base_id

    if viewer_id:
        viewer_id = int(viewer_id)
        query["$or"] = [
            {"target_buyer_id": None},
            {"target_buyer_id": viewer_id},
            {"seller_id": viewer_id}
        ]
    else:
        query["target_buyer_id"] = None

    sort_dir = 1 if ascending else -1
    mongo_sort = [("created_at", sort_dir)]
    if sort_by == "price":
        mongo_sort = [("unit_price", sort_dir)]

    skip = (max(1, page) - 1) * page_size
    cursor = market_col.find(query).sort(mongo_sort).skip(skip).limit(page_size)
    return list(cursor)

def list_by_seller(seller_id: int) -> List[dict]:
    if market_col is None: return []
    return list(market_col.find({"active": True, "seller_id": int(seller_id)}))

def get_listing(listing_id: int) -> Optional[dict]:
    if market_col is None: return None
    return market_col.find_one({"id": int(listing_id)})

def delete_listing(listing_id: int):
    if market_col:
        market_col.update_one({"id": int(listing_id)}, {"$set": {"active": False}})

# ==============================================================================
#  FUNÇÃO DE COMPRA (CORRIGIDA E BLINDADA)
# ==============================================================================

async def purchase_listing(
    *,
    buyer_id: int,
    listing_id: int,
    quantity: int = 1, # Quantidade de LOTES comprados
    context=None
) -> Tuple[dict, int]:
    
    # 1. Importação Local para evitar erro circular (CRUCIAL PARA O COMPRADOR RECEBER O ITEM)
    from modules.player import inventory as inv_module

    # --- Validações ---
    listing = get_listing(listing_id)
    if not listing: raise ListingNotFound("Anúncio não encontrado.")
    if not listing.get("active"): raise ListingInactive("Anúncio inativo ou já vendido.")
    
    seller_id = int(listing["seller_id"])
    buyer_id = int(buyer_id)

    if seller_id == buyer_id: raise InvalidPurchase("Você não pode comprar seu próprio item.")

    target = listing.get("target_buyer_id")
    if target is not None and int(target) != buyer_id:
        raise PermissionDenied(f"🔒 Item reservado para: {listing.get('target_buyer_name')}")

    available = int(listing.get("quantity", 0))
    if quantity > available:
        raise InsufficientQuantity(f"Estoque insuficiente ({available} disponíveis).")

    # --- Cálculos ---
    item_payload = listing.get("item", {})
    unit_price = int(listing["unit_price"])
    total_price = unit_price * quantity

    # --- A. PROCESSAMENTO DO COMPRADOR ---
    buyer_data = await player_manager.get_player_data(buyer_id)
    if not buyer_data: raise ValueError("Comprador não encontrado.")

    # Verifica saldo
    buyer_gold = int(buyer_data.get("gold", 0))
    if buyer_gold < total_price:
        raise ValueError(f"Saldo insuficiente. Necessário: {total_price:,} 🪙")

    # 1. Remove o Ouro (Memória)
    buyer_data["gold"] = buyer_gold - total_price

    # 2. Adiciona o Item (Memória)
    item_type = item_payload.get("type")
    
    if item_type == "stack":
        base_id = item_payload.get("base_id")
        stack_size = int(item_payload.get("qty", 1)) # Ex: 100 ferros por lote
        total_items_to_give = quantity * stack_size
        inv_module.add_item_to_inventory(buyer_data, base_id, total_items_to_give)
        
    elif item_type == "unique":
        base_item_data = item_payload.get("item", {}).copy()
        for _ in range(quantity):
            inv_module.add_unique_item(buyer_data, base_item_data)

    # 3. SALVA O COMPRADOR (Atomicidade: Ouro sai e Item entra ao mesmo tempo)
    await player_manager.save_player_data(buyer_id, buyer_data)

    # --- B. ATUALIZAÇÃO DO ANÚNCIO ---
    new_qty = available - quantity
    update_doc = {"quantity": new_qty}
    if new_qty <= 0: update_doc["active"] = False
    
    market_col.update_one({"_id": listing["_id"]}, {"$set": update_doc})
    
    # --- C. PAGAMENTO AO VENDEDOR (CORRIGIDO) ---
    # Usamos o player_manager para garantir que o cache seja atualizado
    # se o vendedor estiver online.
    try:
        seller_data = await player_manager.get_player_data(seller_id)
        if seller_data:
            current_seller_gold = int(seller_data.get("gold", 0))
            seller_data["gold"] = current_seller_gold + total_price
            await player_manager.save_player_data(seller_id, seller_data)
            log.info(f"💰 [MARKET] Vendedor {seller_id} recebeu {total_price} (Via Cache/Manager).")
        else:
            # Fallback se não conseguir carregar dados (muito raro, ex: bug no DB)
            db["players"].update_one({"_id": seller_id}, {"$inc": {"gold": total_price}})
            log.info(f"💰 [MARKET] Vendedor {seller_id} recebeu {total_price} (Via Update Direto).")
            
    except Exception as e:
        log.error(f"🔥 [MARKET] Erro crítico ao pagar vendedor {seller_id}: {e}")
        # Tenta fallback de emergência
        try: db["players"].update_one({"_id": seller_id}, {"$inc": {"gold": total_price}})
        except: pass

    # Retorna estado atualizado
    listing["quantity"] = new_qty
    listing["active"] = (new_qty > 0)
    
    return listing, total_price

# =========================
# Renderização Visual
# =========================
RARITY_LABEL = {"comum": "Comum", "bom": "Boa", "raro": "Rara", "epico": "Épica", "lendario": "Lendária"}

def _viewer_class_key(pdata: dict, fallback="guerreiro"):
    if not pdata: return fallback
    c = pdata.get("class") or pdata.get("class_type") or pdata.get("classe")
    if isinstance(c, dict): return c.get("type", fallback).lower()
    if isinstance(c, str): return c.lower()
    return fallback

def _class_dmg_emoji(pclass: str) -> str:
    fallback_map = {"guerreiro": "⚔️", "berserker": "🪓", "cacador": "🏹", "assassino": "🗡", "bardo": "🎵", "monge": "🙏", "mago": "✨", "samurai": "🗡"}
    if game_data:
        return getattr(game_data, "CLASS_DMG_EMOJI", {}).get(pclass, fallback_map.get(pclass, "🗡"))
    return fallback_map.get(pclass, "🗡")

def _get_item_info(base_id: str) -> dict:
    try:
        if game_data:
            info = game_data.get_item_info(base_id)
            if info: return dict(info)
            return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}
    except: pass
    return {}

def _render_unique_core_line(inst: dict, viewer_class: str) -> str:
    base_id = inst.get("base_id") or inst.get("tpl") or "item"
    info = _get_item_info(base_id)
    name = inst.get("display_name") or info.get("display_name") or base_id
    emoji = inst.get("emoji") or info.get("emoji") or _class_dmg_emoji(viewer_class)
    tier = inst.get("tier", 1)
    rarity = RARITY_LABEL.get(str(inst.get("rarity", "comum")).lower(), "Comum")
    return f"{emoji}{name} [T{tier}] [{rarity}]"

def _stack_inv_display(base_id: str, qty: int) -> str:
    info = _get_item_info(base_id)
    name = info.get("display_name") or info.get("nome_exibicao") or base_id
    emoji = info.get("emoji", "")
    return f"{emoji}{name} (Lote: {qty} un.)"

def render_listing_line(
    listing: dict,
    *,
    viewer_player_data: Optional[dict] = None,
    show_price_per_unit: bool = False,
    include_id: bool = True
) -> str:
    it = listing.get("item") or {}
    unit_price = int(listing.get("unit_price", 0))
    lid = listing.get("id")
    viewer_class = _viewer_class_key(viewer_player_data, "guerreiro")

    target_id = listing.get("target_buyer_id")
    target_name = listing.get("target_buyer_name", "Alguém")
    is_private = target_id is not None
    prefix = "🔒 " if is_private else ""
    reserved_suf = f" [RESERVADO: {target_name}]" if is_private else ""

    text = ""
    if it.get("type") == "unique":
        inst = it.get("item") or {}
        try:
            if display_utils: text = display_utils.formatar_item_para_exibicao(inst)
        except: pass
        if not text: text = _render_unique_core_line(inst, viewer_class)
        
        suffix = f" — <b>{unit_price} 🪙</b>"
        if include_id: suffix += f" (#{lid})"
        return f"{prefix}{text}{suffix}{reserved_suf}"

    base_id = it.get("base_id", "")
    pack_size = int(it.get("qty", 1))
    core = _stack_inv_display(base_id, pack_size)
    
    suffix = f" — <b>{unit_price} 🪙</b>/lote"
    if show_price_per_unit and pack_size > 0:
        ppu = int(round(unit_price / pack_size))
        suffix += f" (~{ppu} 🪙/un)"
    
    if include_id: suffix += f" (#{lid})"
    return f"{prefix}{core}{suffix}{reserved_suf}"