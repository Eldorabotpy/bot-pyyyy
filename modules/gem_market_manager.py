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

try:
    from modules.game_data.skins import SKIN_CATALOG
except ImportError:
    SKIN_CATALOG = {}

MONGO_CONN_STR = os.getenv("MONGO_CONNECTION_STRING")
log = logging.getLogger(__name__)

# Configuração do DB
try:
    ca = certifi.where()
    client = MongoClient(MONGO_CONN_STR, tlsCAFile=ca)
    db = client["eldora_db"] 
    gem_market_col = db["gem_market_listings"]
    counters_col = db["counters"]
    players_col = db["users"] 
    
    # Cria índices se não existirem
    gem_market_col.create_index("id", unique=True)
    gem_market_col.create_index("active")
    gem_market_col.create_index("seller_id")
    log.info("✅ CONEXÃO COM MONGODB BEM SUCEDIDA (MERCADO DE GEMAS)!")
except Exception as e:
    log.critical(f"🔥 FALHA CRÍTICA (GEMAS): {e}")
    gem_market_col = None

# ==============================================================================
# CONFIGURAÇÃO DE PREÇOS
# ==============================================================================
MAX_GEM_PRICE = 9_999_999 

MIN_GEM_EVO_PRICE = 10     # Preço mínimo para Itens de Evolução
MIN_GEM_SKILL_PRICE = 50   # Preço mínimo para Skills (Tomos)
SKIN_ITEM_IDS = set(SKIN_CATALOG)
SKIN_BOX_ITEM_IDS = {f"caixa_{skin_id}" for skin_id in SKIN_CATALOG}

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

    base_id_text = str(base_id or "")
    if (
        t == "skin"
        or base_id_text in SKIN_ITEM_IDS
        or base_id_text in SKIN_BOX_ITEM_IDS
        or base_id_text.startswith(("caixa_", "skin_"))
    ):
        raise InvalidListing("Caixas e itens de desbloqueio de skin não são mais negociados neste mercado.")

    # Lista expandida de tipos permitidos para evitar erro 'item_stack'
    allowed_types = ("skill", "evo_item", "item_stack", "misc", "consumable")
    
    is_evolution = base_id in EVOLUTION_ITEMS_DATA
    
    if t not in allowed_types and not is_evolution:
        raise InvalidListing(f"Tipo '{t}' não permitido no Mercado de Gemas.")

    if not base_id: raise InvalidListing("Item sem ID.")

# =========================
# API Pública do Gestor
# =========================

def create_listing(
    *, seller_id: str, item_payload: dict, unit_price: int, quantity: int = 1
) -> dict:
    """Cria uma listagem. Aceita seller_id como string (ObjectId)."""
    if gem_market_col is None: raise GemMarketError("MongoDB Off")

    base_id = item_payload.get("base_id")
    item_type = item_payload.get("type")
    
    # -----------------------------------------------------------
    # REGRAS DE PREÇO MÍNIMO E TIPO
    # -----------------------------------------------------------
    
    # 1. Regra para Itens de Evolução
    if base_id in EVOLUTION_ITEMS_DATA or item_type == "evo_item":
        if unit_price < MIN_GEM_EVO_PRICE:
            raise InvalidListing(f"⚠️ Preço muito baixo! Mínimo para Evolução: {MIN_GEM_EVO_PRICE} Gemas.")
        item_payload["qty"] = 1
        item_payload["type"] = "evo_item"

    # 2. Regra para Skills (Tomos)
    elif item_type == "skill" or "tomo_" in str(base_id):
        if unit_price < MIN_GEM_SKILL_PRICE:
            raise InvalidListing(f"⚠️ Preço muito baixo! Mínimo para Skills: {MIN_GEM_SKILL_PRICE} Gemas.")
        # Opcional: Forçar qty=1 para skills se desejar
        # item_payload["qty"] = 1 
        item_payload["type"] = "skill"

    # -----------------------------------------------------------

    _validate_item_payload(item_payload)
    if unit_price <= 0: raise InvalidListing("Preço inválido.")
    if quantity <= 0: raise InvalidListing("Quantidade inválida.")

    lid = _get_next_sequence("gem_market_id")
    
    listing = {
        "id": lid,
        "seller_id": str(seller_id), # Garante string
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
    # Retorna listagens ativas ordenadas por data (mais recentes primeiro)
    listings = gem_market_col.find({"active": True}).sort("created_at", -1)
    return list(listings)

def list_by_seller(seller_id: str) -> List[dict]:
    if gem_market_col is None: return [] 
    return list(gem_market_col.find({"active": True, "seller_id": str(seller_id)}))

async def cancel_listing(*, seller_id: str, listing_id: int) -> dict:
    if gem_market_col is None: raise GemMarketError("MongoDB não conectado.")
    
    # 1. Busca e valida permissão/status
    listing = gem_market_col.find_one({"id": int(listing_id)})
    if not listing: raise ListingNotFound("Anúncio não existe.")
    if not listing.get("active"): raise ListingInactive("Anúncio já inativo.")
    
    # Comparação segura de IDs (String)
    if str(listing["seller_id"]) != str(seller_id): 
        raise PermissionDenied("Não autorizado.")
    
    # Cálculos de devolução
    item_payload = listing.get("item", {})
    quantity_left = listing.get("quantity", 0) # Lotes restantes no estoque
    pack_qty = item_payload.get("qty", 1)      # Itens por lote
    total_return_qty = quantity_left * pack_qty

    seller_pdata = await player_manager.get_player_data(seller_id)
    if not seller_pdata:
        raise GemMarketError("Não foi possível carregar sua mochila para devolver o item.")
    base_id_limpo = item_payload.get("base_id")
    if total_return_qty > 0:
        from modules.player.inventory import can_add_item
        fits_bag, bag_error = can_add_item(seller_pdata, base_id_limpo, total_return_qty)
        if not fits_bag:
            raise InvalidPurchase(f"{bag_error} Libere espaço para cancelar o anúncio.")
    
    # 2. Atualiza o status no MongoDB
    result = gem_market_col.update_one(
        {"id": int(listing_id), "active": True, "quantity": quantity_left},
        {"$set": {"active": False}}
    )
    
    if result.modified_count == 0:
        raise ListingInactive("Falha ao cancelar (Anúncio já inativo ou vendido).")
    
    # 3. Devolve o item ao vendedor
    if total_return_qty > 0:
        from modules.player.inventory import try_add_item_to_inventory
        if not try_add_item_to_inventory(seller_pdata, base_id_limpo, total_return_qty):
            # A validação acima evita essa situação no fluxo normal. Reabre o
            # anúncio se o inventário mudou entre a validação e a entrega.
            gem_market_col.update_one(
                {"id": int(listing_id), "active": False, "quantity": quantity_left},
                {"$set": {"active": True}},
            )
            raise InvalidPurchase("A mochila mudou durante o cancelamento. Atualize e tente novamente.")
        await player_manager.save_player_data(seller_id, seller_pdata)
        await player_manager.clear_player_cache(seller_id)
    
    listing["active"] = False 
    log.info(f"[GemMarket] Listagem {listing_id} cancelada. Devolvidos {total_return_qty}x {base_id_limpo}.")
    return listing

async def purchase_listing(
    *, buyer_pdata: dict, seller_pdata: dict, listing_id: int, quantity: int = 1
) -> Tuple[dict, int]:
    
    if gem_market_col is None or players_col is None: 
        raise GemMarketError("MongoDB não conectado.")
        
    buyer_id = str(buyer_pdata.get("user_id") or buyer_pdata.get("_id"))
    seller_id = str(seller_pdata.get("user_id") or seller_pdata.get("_id"))
    
    listing = gem_market_col.find_one({"id": listing_id})
    if not listing or not listing.get("active"): raise ListingNotFound("Anúncio não ativo.")
    
    if str(listing["seller_id"]) == buyer_id: 
        raise InvalidPurchase("Não é possível comprar o próprio anúncio.")
    
    available = int(listing.get("quantity", 0))
    if quantity > available: raise InsufficientQuantity("Estoque insuficiente.")

    total_price_gems = int(listing["unit_price_gems"]) * int(quantity)

    # Verifica saldo do comprador
    buyer_gems = player_manager.get_gems(buyer_pdata)
    if buyer_gems < total_price_gems:
        raise InsufficientGems(f"Gemas insuficientes. Necessário: {total_price_gems}")

    # ATUALIZA A LISTAGEM (Decrementa estoque)
    remaining_qty = available - quantity
    update_doc = {"quantity": remaining_qty}
    if remaining_qty <= 0: update_doc["active"] = False
        
    result_update_listing = gem_market_col.update_one(
        {"_id": listing["_id"], "active": True, "quantity": available}, 
        {"$set": update_doc}
    )
    
    if result_update_listing.modified_count == 0:
        raise InvalidPurchase("Falha na baixa do estoque (concorrência ou já vendido).")
    
    # PAGAMENTO AO VENDEDOR (Update direto no banco Users)
    from bson import ObjectId
    try:
        seller_oid = ObjectId(seller_id) if ObjectId.is_valid(seller_id) else seller_id
        result_payment = players_col.update_one(
            {"_id": seller_oid}, 
            {"$inc": {"gems": total_price_gems}}
        )
        
        if result_payment.modified_count > 0:
            log.info(f"💰 [GemMarket] Vendedor {seller_id} recebeu +{total_price_gems} GEMAS.")
            # Limpa cache do vendedor para ele ver as gemas
            await player_manager.clear_player_cache(seller_id) 
            
    except Exception as e:
        log.error(f"Erro ao pagar vendedor {seller_id}: {e}")

    listing["quantity"] = remaining_qty
    listing["active"] = (remaining_qty > 0)
    
    return listing, total_price_gems
