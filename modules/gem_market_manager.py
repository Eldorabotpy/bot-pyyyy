# modules/gem_market_manager.py

from __future__ import annotations
import os
import html
import certifi # Necessário para conexões TLS/SSL com MongoDB Atlas
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
import logging
from pymongo import MongoClient, ReturnDocument
import asyncio 
from modules import player_manager 

MONGO_CONN_STR = os.getenv("MONGO_CONNECTION_STRING")
log = logging.getLogger(__name__)

try:
    ca = certifi.where()
    client = MongoClient(MONGO_CONN_STR, tlsCAFile=ca)
    db = client["eldora_db"] 
    
    # COLEÇÕES:
    gem_market_col = db["gem_market_listings"]
    counters_col = db["counters"]
    players_col = db["players"] 
    
    gem_market_col.create_index("id", unique=True)
    gem_market_col.create_index("active")
    log.info("✅ CONEXÃO COM MONGODB BEM SUCEDIDA (MERCADO DE GEMAS)!")
except Exception as e:
    log.critical(f"🔥 FALHA CRÍTICA AO CONECTAR NO MONGODB (GEMAS): {e}")
    gem_market_col = None
    counters_col = None
    players_col = None

MAX_GEM_PRICE = 9_999_999 # Preço máximo em gemas

# --- Erros Específicos ---
class GemMarketError(Exception): ...
class ListingNotFound(GemMarketError): ...
class ListingInactive(GemMarketError): ...
class InvalidListing(GemMarketError): ...
class PermissionDenied(GemMarketError): ...
class InsufficientQuantity(GemMarketError): ...
class InvalidPurchase(GemMarketError): ...
class InsufficientGems(GemMarketError): ...

# =========================
# Validações
# =========================
# modules/gem_market_manager.py (Função _get_next_sequence)

def _get_next_sequence(name: str) -> int:
    """Obtém um ID sequencial (atômico) do MongoDB."""
    if counters_col is None: raise ListingNotFound("MongoDB não conectado.")
    ret = counters_col.find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        # CORREÇÃO: Usar o objeto ReturnDocument.AFTER
        return_document=ReturnDocument.AFTER 
    )
    return ret["seq"]

def _now_iso() -> str:
    """Retorna o timestamp atual no formato ISO 8601 (UTC)."""
    return datetime.now(timezone.utc).isoformat()

def _validate_item_payload(item_payload: dict):
    """
    (CORRIGIDO) Valida o 'item' que está a ser vendido.
    Agora, todos os tipos (skill, skin, evo_item) são tratados como ITENS
    e precisam de um 'base_id' e 'qty' (quantidade por lote).
    """
    if not isinstance(item_payload, dict):
        raise InvalidListing("item_payload inválido.")

    t = item_payload.get("type")
    if t not in ("skill", "skin", "evo_item"):
        raise InvalidListing(f"Tipo de item inválido para o Mercado de Gemas: {t}")

    # --- ESTA É A CORREÇÃO ---
    # Todos os três tipos são ITENS e devem ter um 'base_id' (o ID do item)
    if not item_payload.get("base_id") or not isinstance(item_payload.get("base_id"), str):
        raise InvalidListing(f"Payload do item (tipo {t}) não contém um 'base_id' válido.")
    
    # Todos os três tipos devem definir a 'qty' (quantidade por lote)
    qty = item_payload.get("qty")
    if not isinstance(qty, int) or qty <= 0:
        raise InvalidListing(f"Payload do item (tipo {t}) não contém uma 'qty' (quantidade por lote) válida.")

def _validate_price_qty(unit_price: int, quantity: int):
    if not isinstance(unit_price, int) or unit_price <= 0 or unit_price > MAX_GEM_PRICE:
        raise InvalidListing(f"unit_price (gemas) deve ser entre 1 e {MAX_GEM_PRICE}.")
    if not isinstance(quantity, int) or quantity <= 0:
        raise InvalidListing("quantity (lotes) deve ser > 0.")

# =========================
# API Pública do Gestor
# =========================

def create_listing(
    *, seller_id: int, item_payload: dict, unit_price: int, quantity: int = 1
) -> dict:
    if gem_market_col is None: raise GemMarketError("MongoDB não conectado.")

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
    log.info(f"[GemMarket] Listagem (Gemas) criada: id={lid} price={unit_price} item={item_payload}")
    return listing

def get_listing(listing_id: int) -> Optional[dict]:
    if gem_market_col is None: return None
    return gem_market_col.find_one({"id": int(listing_id)})

def list_active(page: int = 1, page_size: int = 30) -> List[dict]:
    if gem_market_col is None: return []

    # ⚠️ CORREÇÃO CRÍTICA: Retorna todas as listagens ATIVAS. 
    # A paginação é feita no handler, mas para garantir que o filtro funciona, 
    # vamos retornar todas as ativas (sem paginação por enquanto)
    
    # 1. Encontra todos os documentos ativos
    listings = gem_market_col.find({"active": True}).sort("created_at", -1)
    
    # 2. Converte o cursor para uma lista
    return list(listings)

def list_by_seller(seller_id: int) -> List[dict]:
    # Use 'is None' instead of 'if not collection'
    if gem_market_col is None: return [] 
    return list(gem_market_col.find({"active": True, "seller_id": int(seller_id)}))

def cancel_listing(*, seller_id: int, listing_id: int) -> dict:
    # CORREÇÃO: Usar 'is None' em vez de 'if not gem_market_col:'
    if gem_market_col is None: raise GemMarketError("MongoDB não conectado.")

    # 1. Busca e valida permissão/status (Necessário para devolver item)
    listing = gem_market_col.find_one({"id": int(listing_id)})
    if not listing: raise ListingNotFound("Anúncio não existe.")
    if not listing.get("active"): raise ListingInactive("Anúncio já inativo.")
    if int(listing["seller_id"]) != int(seller_id): raise PermissionDenied("Não autorizado.")

    # 2. Atualiza o status no MongoDB
    result = gem_market_col.update_one(
        {"id": int(listing_id)}, 
        {"$set": {"active": False}}
    )
    
    if result.modified_count > 0:
        listing["active"] = False # Retorna o objeto atualizado
        log.info(f"[GemMarket] Listagem {listing_id} cancelada por {seller_id}.")
        return listing
    else:
        # Falha de concorrência/inativo
        raise ListingInactive("Falha ao cancelar (Status já inativo).")
    
# Módulos: modules/gem_market_manager.py

async def purchase_listing( # 👈 Adicionar 'async' aqui é a correção principal
    *, buyer_pdata: dict, seller_pdata: dict, listing_id: int, quantity: int = 1
) -> Tuple[dict, int]:
    
    # Validação de Conexão
    if gem_market_col is None or players_col is None: 
        raise GemMarketError("MongoDB não conectado.")
        
    buyer_id = buyer_pdata.get("user_id") or buyer_pdata.get("_id")
    seller_id = seller_pdata.get("user_id") or seller_pdata.get("_id")
    
    # 1. Busca e validação (omitindo validações complexas, focando no flow)
    listing = gem_market_col.find_one({"id": listing_id})
    if not listing or not listing.get("active"): raise ListingNotFound("Anúncio não ativo.")
    if int(listing["seller_id"]) == int(buyer_id): raise InvalidPurchase("Não é possível comprar o próprio anúncio.")
    
    available = int(listing.get("quantity", 0))
    if quantity > available: raise InsufficientQuantity("Estoque insuficiente.")

    total_price_gems = int(listing["unit_price_gems"]) * int(quantity)

    # 2. ATUALIZA A LISTAGEM (Baixa o estoque de forma atômica)
    remaining_qty = available - quantity
    update_doc = {"quantity": remaining_qty}
    if remaining_qty <= 0: update_doc["active"] = False
        
    result_update_listing = gem_market_col.update_one( # <--- LINHA CORRETA
        {"_id": listing["_id"], "active": True, "quantity": available}, 
        {"$set": update_doc}
    )
    
    if result_update_listing.modified_count == 0:
        raise InvalidPurchase("Falha na baixa do estoque (concorrência ou já vendido).")

    # 3. PAGAMENTO AO VENDEDOR (Transação de Gemas no Banco)
    result_payment = players_col.update_one(
        {"_id": seller_id}, 
        {"$inc": {"gems": total_price_gems}}
    )
    
    # 4. LIMPEZA DE CACHE (CRÍTICO PARA SEGURANÇA)
    if result_payment.modified_count > 0:
        log.info(f"💰 [GemMarket] Vendedor {seller_id} recebeu +{total_price_gems} GEMAS no banco.")
        
        try:
            # Esta chamada agora é válida porque a função é 'async'
            await player_manager.clear_player_cache(seller_id) 
            log.info(f"🧹 [GemMarket] Cache do vendedor {seller_id} limpo.")

        except Exception as e_cache:
            log.warning(f"⚠️ [GemMarket] Falha ao limpar cache: {e_cache}")

    # Retorno (com status atualizado)
    listing["quantity"] = remaining_qty
    listing["active"] = (remaining_qty > 0)
    
    return listing, total_price_gems