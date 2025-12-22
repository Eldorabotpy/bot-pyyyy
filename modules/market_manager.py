# modules/gem_market_manager.py
# (VERSÃO CORRIGIDA: FIX TOMO_TOMO E VISIBILIDADE)

from __future__ import annotations
import os
import certifi
from datetime import datetime, timezone
from typing import Optional, List, Tuple
import logging
from pymongo import MongoClient, ReturnDocument
from modules import player_manager

MONGO_CONN_STR = os.getenv("MONGO_CONNECTION_STRING")
log = logging.getLogger(__name__)

try:
    ca = certifi.where()
    client = MongoClient(MONGO_CONN_STR, tlsCAFile=ca)
    db = client["eldora_db"] 
    
    gem_market_col = db["gem_market_listings"]
    counters_col = db["counters"]
    players_col = db["players"] 
    
    # Índices para performance e unicidade
    gem_market_col.create_index("id", unique=True)
    gem_market_col.create_index("active")
    gem_market_col.create_index("created_at") # Ajuda na ordenação
    
    log.info("✅ CONEXÃO COM MONGODB BEM SUCEDIDA (MERCADO DE GEMAS)!")
except Exception as e:
    log.critical(f"🔥 FALHA CRÍTICA AO CONECTAR NO MONGODB (GEMAS): {e}")
    gem_market_col = None
    counters_col = None
    players_col = None

MAX_GEM_PRICE = 9_999_999 

class GemMarketError(Exception): ...
class ListingNotFound(GemMarketError): ...
class ListingInactive(GemMarketError): ...
class InvalidListing(GemMarketError): ...
class PermissionDenied(GemMarketError): ...
class InsufficientQuantity(GemMarketError): ...
class InvalidPurchase(GemMarketError): ...
class InsufficientGems(GemMarketError): ...

def _get_next_sequence(name: str) -> int:
    if counters_col is None: raise ListingNotFound("MongoDB não conectado.")
    ret = counters_col.find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER 
    )
    return ret["seq"]

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _validate_item_payload(item_payload: dict):
    if not isinstance(item_payload, dict):
        raise InvalidListing("Payload inválido.")

    # Aceita skill, skin e evo_item
    t = item_payload.get("type")
    valid_types = ("skill", "skin", "evo_item", "stack") # Adicionado stack por segurança
    if t not in valid_types:
        raise InvalidListing(f"Tipo inválido: {t}")

    if not item_payload.get("base_id") or not isinstance(item_payload.get("base_id"), str):
        raise InvalidListing("Item sem 'base_id' válido.")
    
    qty = item_payload.get("qty")
    if not isinstance(qty, int) or qty <= 0:
        raise InvalidListing("Quantidade inválida.")

# --- API PÚBLICA ---

def create_listing(*, seller_id: int, item_payload: dict, unit_price: int, quantity: int = 1) -> dict:
    if gem_market_col is None: raise GemMarketError("BD Offline.")
    
    _validate_item_payload(item_payload)

    # Limpeza preventiva do ID (Remove prefixos duplicados antes de salvar)
    base_id = item_payload.get("base_id", "")
    if item_payload.get("type") == "skill" and base_id.startswith("tomo_tomo_"):
        item_payload["base_id"] = base_id.replace("tomo_tomo_", "tomo_", 1)
    
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
    log.info(f"[GemMarket] Criado #{lid} (Price: {unit_price})")
    return listing

def get_listing(listing_id: int) -> Optional[dict]:
    if gem_market_col is None: return None
    return gem_market_col.find_one({"id": int(listing_id)})

def list_active(page: int = 1, page_size: int = 30, viewer_id: int = None) -> List[dict]:
    if gem_market_col is None: return []
    # Retorna APENAS ativos, ordenados do mais recente pro mais antigo
    cursor = gem_market_col.find({"active": True}).sort("created_at", -1)
    return list(cursor)

def list_by_seller(seller_id: int) -> List[dict]:
    if gem_market_col is None: return [] 
    return list(gem_market_col.find({"active": True, "seller_id": int(seller_id)}))

async def cancel_listing(*, seller_id: int, listing_id: int) -> dict:
    if gem_market_col is None: raise GemMarketError("BD Offline.")

    # 1. Validações
    listing = gem_market_col.find_one({"id": int(listing_id)})
    if not listing: raise ListingNotFound("Anúncio não existe.")
    if not listing.get("active"): raise ListingInactive("Já cancelado ou vendido.")
    if int(listing["seller_id"]) != int(seller_id): raise PermissionDenied("Não é seu anúncio.")
    
    # 2. Desativa Atomicamente
    result = gem_market_col.update_one(
        {"id": int(listing_id), "active": True},
        {"$set": {"active": False}}
    )
    
    if result.modified_count == 0:
        raise ListingInactive("Erro de concorrência: Item já vendido.")
    
    # 3. Devolução Inteligente (CORREÇÃO TOMO_TOMO)
    item_payload = listing.get("item", {})
    qty_left = listing.get("quantity", 0)
    pack_qty = item_payload.get("qty", 1)
    total_return = qty_left * pack_qty
    
    if total_return > 0:
        raw_base_id = item_payload.get("base_id")
        item_type = item_payload.get("type")
        
        # Lógica de reconstrução de ID corrigida:
        base_id_final = raw_base_id
        
        if item_type == "skill":
            # SÓ ADICIONA O PREFIXO SE NÃO TIVER
            if not raw_base_id.startswith("tomo_"):
                base_id_final = f"tomo_{raw_base_id}"
            else:
                base_id_final = raw_base_id
                
        elif item_type == "skin":
             if not raw_base_id.startswith("caixa_"):
                base_id_final = f"caixa_{raw_base_id}"
             else:
                base_id_final = raw_base_id

        # Devolve ao jogador
        pdata = await player_manager.get_player_data(seller_id)
        if pdata:
            # Força correção de bug de prefixo duplo se existir
            if base_id_final.startswith("tomo_tomo_"):
                base_id_final = base_id_final.replace("tomo_tomo_", "tomo_", 1)
                
            player_manager.add_item_to_inventory(pdata, base_id_final, total_return)
            await player_manager.save_player_data(seller_id, pdata)
            log.info(f"♻️ [GemMarket] Devolvido: {total_return}x {base_id_final} para {seller_id}")
            
    listing["active"] = False 
    return listing

async def purchase_listing(*, buyer_pdata: dict, seller_pdata: dict, listing_id: int, quantity: int = 1) -> Tuple[dict, int]:
    if gem_market_col is None: raise GemMarketError("BD Offline.")
        
    buyer_id = buyer_pdata.get("user_id") or buyer_pdata.get("_id")
    seller_id = seller_pdata.get("user_id") or seller_pdata.get("_id")
    
    listing = gem_market_col.find_one({"id": listing_id})
    if not listing or not listing.get("active"): raise ListingNotFound("Item indisponível.")
    if int(listing["seller_id"]) == int(buyer_id): raise InvalidPurchase("Você não pode comprar seu item.")
    
    available = int(listing.get("quantity", 0))
    if quantity > available: raise InsufficientQuantity(f"Só restam {available} lotes.")

    total_price = int(listing["unit_price_gems"]) * int(quantity)

    # Baixa estoque
    rem = available - quantity
    update_doc = {"quantity": rem}
    if rem <= 0: update_doc["active"] = False
        
    res = gem_market_col.update_one(
        {"_id": listing["_id"], "active": True, "quantity": available}, 
        {"$set": update_doc}
    )
    
    if res.modified_count == 0:
        raise InvalidPurchase("Erro na transação. Tente novamente.")
    
    # Pagamento (Gemas vão direto pro Banco/Perfil)
    players_col.update_one({"_id": seller_id}, {"$inc": {"gems": total_price}})
    
    # Limpa cache do vendedor para ele ver as gemas logo
    await player_manager.clear_player_cache(seller_id)

    listing["quantity"] = rem
    listing["active"] = (rem > 0)
    
    return listing, total_price