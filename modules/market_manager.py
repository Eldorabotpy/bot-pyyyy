# modules/market_manager.py
# (VERSÃO CORRIGIDA: VARIÁVEL LOG)
from __future__ import annotations
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
from pymongo import MongoClient
import certifi

# --- CONFIGURAÇÃO DE LOGGING ---
logging.basicConfig(level=logging.INFO)
# CORREÇÃO: Agora a variável se chama 'log' para bater com o resto do código
log = logging.getLogger(__name__)

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
MONGO_CONN_STR = os.getenv("MONGO_CONNECTION_STRING")

# TRAVA DE SEGURANÇA
if not MONGO_CONN_STR:
    # Tenta ler a antiga por garantia
    MONGO_CONN_STR = os.getenv("MONGO_URL") 
    if not MONGO_CONN_STR:
        log.critical("❌ ERRO FATAL: A variável 'MONGO_CONNECTION_STRING' não foi encontrada!")
        # Fallback apenas para evitar crash de importação, mas a conexão falhará no Render
        MONGO_CONN_STR = "mongodb://localhost:27017/rpg_bot"

try:
    # Tenta conectar
    ca = certifi.where()
    client = MongoClient(MONGO_CONN_STR, tlsCAFile=ca)
    
    # Força teste
    client.admin.command('ping')
    log.info("✅ CONEXÃO COM MONGODB BEM SUCEDIDA (MERCADO)!")
    
    db = client["eldora_db"] 
    market_col = db["market_listings"]
    counters_col = db["counters"]
    
    # Índices
    market_col.create_index("id", unique=True)
    market_col.create_index("active")
    
except Exception as e:
    log.critical(f"🔥 FALHA CRÍTICA AO CONECTAR NO MONGODB: {e}")
    market_col = None
    counters_col = None

# Tenta importar display_utils
try:
    from modules import display_utils
except Exception:
    display_utils = None

from modules import game_data

MAX_PRICE = 100_000_000_000 
MAX_QTY = 1_000_000

# =========================
# Erros
# =========================
class MarketError(Exception): ...
class ListingNotFound(MarketError): ...
class ListingInactive(MarketError): ...
class InvalidListing(MarketError): ...
class PermissionDenied(MarketError): ...
class InsufficientQuantity(MarketError): ...
class InvalidPurchase(MarketError): ...

# =========================
# Helpers
# =========================
def _get_next_sequence(name: str) -> int:
    ret = counters_col.find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
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
    target_buyer_name: Optional[str] = None
) -> dict:
    _validate_price_qty(unit_price, quantity)

    lid = _get_next_sequence("market_id")

    listing = {
        "id": lid,
        "seller_id": int(seller_id),
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
    return list(market_col.find({"active": True, "seller_id": int(seller_id)}))

def get_listing(listing_id: int) -> Optional[dict]:
    return market_col.find_one({"id": int(listing_id)})

def delete_listing(listing_id: int):
    market_col.update_one({"id": int(listing_id)}, {"$set": {"active": False}})

def purchase_listing(
    *,
    buyer_id: int,
    listing_id: int,
    quantity: int = 1,
    context=None
) -> Tuple[dict, int]:
    listing = get_listing(listing_id)
    if not listing: raise ListingNotFound("Anúncio não encontrado.")
    if not listing.get("active"): raise ListingInactive("Anúncio inativo.")
    if int(listing["seller_id"]) == int(buyer_id): raise InvalidPurchase("Não pode comprar seu item.")

    target = listing.get("target_buyer_id")
    if target is not None and int(target) != int(buyer_id):
        raise PermissionDenied(f"🔒 Item reservado para: {listing.get('target_buyer_name')}")

    available = int(listing.get("quantity", 0))
    if quantity > available:
        raise InsufficientQuantity(f"Estoque insuficiente ({available}).")

    new_qty = available - quantity
    update_doc = {"quantity": new_qty}
    if new_qty <= 0: update_doc["active"] = False
    
    market_col.update_one({"_id": listing["_id"]}, {"$set": update_doc})
    
    listing["quantity"] = new_qty
    listing["active"] = (new_qty > 0)
    
    total_price = int(listing["unit_price"]) * quantity
    return listing, total_price

# =========================
# Renderização Visual
# =========================
RARITY_LABEL = {"comum": "Comum", "bom": "Boa", "raro": "Rara", "epico": "Épica", "lendario": "Lendária"}
_CLASS_DMG_EMOJI_FALLBACK = {"guerreiro": "⚔️", "berserker": "🪓", "cacador": "🏹", "assassino": "🗡", "bardo": "🎵", "monge": "🙏", "mago": "✨", "samurai": "🗡"}

def _viewer_class_key(pdata: dict, fallback="guerreiro"):
    if not pdata: return fallback
    c = pdata.get("class") or pdata.get("class_type") or pdata.get("classe")
    if isinstance(c, dict): return c.get("type", fallback).lower()
    if isinstance(c, str): return c.lower()
    return fallback

def _class_dmg_emoji(pclass: str) -> str:
    return getattr(game_data, "CLASS_DMG_EMOJI", {}).get(pclass, _CLASS_DMG_EMOJI_FALLBACK.get(pclass, "🗡"))

def _get_item_info(base_id: str) -> dict:
    try:
        info = game_data.get_item_info(base_id)
        if info: return dict(info)
    except: pass
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

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
    return f"{emoji}{name} ×{qty}"

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
    pack_qty = int(it.get("qty", 1))
    core = _stack_inv_display(base_id, pack_qty)
    
    suffix = f" — <b>{unit_price} 🪙</b>/lote"
    if show_price_per_unit and pack_qty > 0:
        ppu = int(round(unit_price / pack_qty))
        suffix += f" (~{ppu} 🪙/un)"
    
    if include_id: suffix += f" (#{lid})"
    return f"{prefix}{core}{suffix}{reserved_suf}"