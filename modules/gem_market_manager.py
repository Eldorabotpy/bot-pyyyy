# modules/gem_market_manager.py
from __future__ import annotations
import os
import html
import certifi
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
import logging
from pymongo import MongoClient, ReturnDocument
import asyncio 
from modules import player_manager 

# Importa a lista de itens de evolução
try:
    from modules.game_data.items_evolution import EVOLUTION_ITEMS_DATA
except ImportError:
    EVOLUTION_ITEMS_DATA = {} 

MONGO_CONN_STR = os.getenv("MONGO_CONNECTION_STRING")
log = logging.getLogger(__name__)

try:
    ca = certifi.where()
    client = MongoClient(MONGO_CONN_STR, tlsCAFile=ca)
    db = client["eldora_db"] 
    gem_market_col = db["gem_market_listings"]
    counters_col = db["counters"]
    players_col = db["players"] 
    gem_market_col.create_index("id", unique=True)
    gem_market_col.create_index("active")
    log.info("✅ CONEXÃO COM MONGODB BEM SUCEDIDA (MERCADO DE GEMAS)!")
except Exception as e:
    log.critical(f"🔥 FALHA CRÍTICA (GEMAS): {e}")
    gem_market_col = None

MAX_GEM_PRICE = 9_999_999 
MIN_GEM_EVO_PRICE = 10    # <--- Preço mínimo para itens de evolução

class GemMarketError(Exception): ...
class ListingNotFound(GemMarketError): ...
class ListingInactive(GemMarketError): ...
class InvalidListing(GemMarketError): ...
class PermissionDenied(GemMarketError): ...
class InsufficientQuantity(GemMarketError): ...
class InvalidPurchase(GemMarketError): ...
class InsufficientGems(GemMarketError): ...

def _get_next_sequence(name: str) -> int:
    if counters_col is None: raise ListingNotFound("MongoDB Off")
    ret = counters_col.find_one_and_update(
        {"_id": name}, {"$inc": {"seq": 1}}, upsert=True, return_document=ReturnDocument.AFTER 
    )
    return ret["seq"]

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _validate_item_payload(item_payload: dict):
    if not isinstance(item_payload, dict): raise InvalidListing("Payload inválido.")
    t = item_payload.get("type")
    base_id = item_payload.get("base_id")

    # Verifica permissão
    allowed_types = ("skill", "skin", "evo_item")
    is_evolution = base_id in EVOLUTION_ITEMS_DATA
    
    if t not in allowed_types and not is_evolution:
        raise InvalidListing(f"Tipo '{t}' não permitido no Mercado de Gemas.")

    if not base_id: raise InvalidListing("Item sem ID.")

def _validate_price_qty(unit_price: int, quantity: int):
    if not isinstance(unit_price, int) or unit_price <= 0 or unit_price > MAX_GEM_PRICE:
        raise InvalidListing(f"unit_price (gemas) deve ser entre 1 e {MAX_GEM_PRICE}.")
    if not isinstance(quantity, int) or quantity <= 0:
        raise InvalidListing("quantity (estoque) deve ser > 0.")

# =========================
# API Pública do Gestor
# =========================

def create_listing(
    *, seller_id: int, item_payload: dict, unit_price: int, quantity: int = 1
) -> dict:
    if gem_market_col is None: raise GemMarketError("MongoDB Off")

    base_id = item_payload.get("base_id")
    is_evo = base_id in EVOLUTION_ITEMS_DATA

    # === REGRA DE NEGÓCIO: ITENS DE EVOLUÇÃO ===
    if is_evo:
        # 1. Valida Preço Mínimo
        if unit_price < MIN_GEM_EVO_PRICE:
            raise InvalidListing(f"⚠️ Preço baixo demais! Mínimo para itens de evolução: {MIN_GEM_EVO_PRICE} Gemas.")
        
        # 2. Força Lote Unitário
        # O 'qty' dentro do payload (itens por lote) DEVE ser 1.
        item_payload["qty"] = 1
        item_payload["type"] = "evo_item" # Garante o tipo

    # Validações gerais
    _validate_item_payload(item_payload)
    if unit_price <= 0: raise InvalidListing("Preço inválido.")
    if quantity <= 0: raise InvalidListing("Quantidade inválida.")

    lid = _get_next_sequence("gem_market_id")
    listing = {
        "id": lid,
        "seller_id": int(seller_id),
        "item": item_payload,
        "unit_price_gems": int(unit_price),
        "quantity": int(quantity),
        "created_at": _now_iso(),
        "active": True,
    }
    gem_market_col.insert_one(listing)
    log.info(f"[GemMarket] Criado #{lid} por {seller_id} (Item: {base_id}, Preço: {unit_price})")
    return listing

def get_listing(listing_id: int) -> Optional[dict]:
    if gem_market_col is None: return None
    return gem_market_col.find_one({"id": int(listing_id)})

def list_active(page: int = 1, page_size: int = 30) -> List[dict]:
    if gem_market_col is None: return []
    # Retorna listagens ativas ordenadas por data
    listings = gem_market_col.find({"active": True}).sort("created_at", -1)
    return list(listings)

def list_by_seller(seller_id: int) -> List[dict]:
    if gem_market_col is None: return [] 
    return list(gem_market_col.find({"active": True, "seller_id": int(seller_id)}))

async def cancel_listing(*, seller_id: int, listing_id: int) -> dict:
    if gem_market_col is None: raise GemMarketError("MongoDB não conectado.")
    if players_col is None: raise GemMarketError("Coleção de jogadores não conectada.")

    # 1. Busca e valida permissão/status
    listing = gem_market_col.find_one({"id": int(listing_id)})
    if not listing: raise ListingNotFound("Anúncio não existe.")
    if not listing.get("active"): raise ListingInactive("Anúncio já inativo.")
    if int(listing["seller_id"]) != int(seller_id): raise PermissionDenied("Não autorizado.")
    
    # Cálculos de devolução
    item_payload = listing.get("item", {})
    quantity_left = listing.get("quantity", 0) # Lotes restantes no estoque
    pack_qty = item_payload.get("qty", 1)      # Itens por lote (será 1 para evo_items)
    total_return_qty = quantity_left * pack_qty
    
    # 2. Atualiza o status no MongoDB
    result = gem_market_col.update_one(
        {"id": int(listing_id), "active": True},
        {"$set": {"active": False}}
    )
    
    if result.modified_count == 0:
        raise ListingInactive("Falha ao cancelar (Anúncio já inativo ou vendido).")
    
    # 3. Devolve o item ao vendedor
    if total_return_qty > 0:
        base_id_limpo = item_payload.get("base_id")
        item_type = item_payload.get("type")
        
        # Prefixo correto para devolução
        base_id_final = base_id_limpo
        if item_type == "skin" and not base_id_limpo.startswith("caixa_"):
            base_id_final = f"caixa_{base_id_limpo}" 
        elif item_type == "skill" and not base_id_limpo.startswith("tomo_"):
            base_id_final = f"tomo_{base_id_limpo}" 
            
        # Devolução segura
        seller_pdata = await player_manager.get_player_data(seller_id)
        if seller_pdata:
            player_manager.add_item_to_inventory(seller_pdata, base_id_final, total_return_qty) 
            await player_manager.save_player_data(seller_id, seller_pdata)
            await player_manager.clear_player_cache(seller_id)
        else:
            log.error(f"[GemMarket] Falha ao carregar pdata para devolução {listing_id} -> {seller_id}")
    
    listing["active"] = False 
    log.info(f"[GemMarket] Listagem {listing_id} cancelada. Devolvidos {total_return_qty}x {base_id_limpo}.")
    return listing

async def purchase_listing(
    *, buyer_pdata: dict, seller_pdata: dict, listing_id: int, quantity: int = 1
) -> Tuple[dict, int]:
    
    if gem_market_col is None or players_col is None: 
        raise GemMarketError("MongoDB não conectado.")
        
    buyer_id = buyer_pdata.get("user_id") or buyer_pdata.get("_id")
    seller_id = seller_pdata.get("user_id") or seller_pdata.get("_id")
    
    listing = gem_market_col.find_one({"id": listing_id})
    if not listing or not listing.get("active"): raise ListingNotFound("Anúncio não ativo.")
    if int(listing["seller_id"]) == int(buyer_id): raise InvalidPurchase("Não é possível comprar o próprio anúncio.")
    
    available = int(listing.get("quantity", 0))
    if quantity > available: raise InsufficientQuantity("Estoque insuficiente.")

    total_price_gems = int(listing["unit_price_gems"]) * int(quantity)

    # Verifica saldo do comprador (apenas segurança extra, o handler principal já deve checar)
    buyer_gems = player_manager.get_gems(buyer_pdata)
    if buyer_gems < total_price_gems:
        raise InsufficientGems(f"Gemas insuficientes. Necessário: {total_price_gems}")

    # ATUALIZA A LISTAGEM
    remaining_qty = available - quantity
    update_doc = {"quantity": remaining_qty}
    if remaining_qty <= 0: update_doc["active"] = False
        
    result_update_listing = gem_market_col.update_one(
        {"_id": listing["_id"], "active": True, "quantity": available}, 
        {"$set": update_doc}
    )
    
    if result_update_listing.modified_count == 0:
        raise InvalidPurchase("Falha na baixa do estoque (concorrência ou já vendido).")
    
    # PAGAMENTO AO VENDEDOR
    result_payment = players_col.update_one(
        {"_id": seller_id}, 
        {"$inc": {"gems": total_price_gems}}
    )
    
    if result_payment.modified_count > 0:
        log.info(f"💰 [GemMarket] Vendedor {seller_id} recebeu +{total_price_gems} GEMAS.")
        try:
            await player_manager.clear_player_cache(seller_id) 
        except Exception as e_cache:
            log.warning(f"⚠️ [GemMarket] Falha ao limpar cache: {e_cache}")

    listing["quantity"] = remaining_qty
    listing["active"] = (remaining_qty > 0)
    
    return listing, total_price_gems