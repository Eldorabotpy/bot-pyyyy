# modules/gem_market_manager.py
# (VERSÃO CORRIGIDA: ANTI-DUPLICAÇÃO DE PREFIXOS E CORREÇÃO DE VISIBILIDADE)

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
    
    # Garante índices
    gem_market_col.create_index("id", unique=True)
    gem_market_col.create_index("active")
    gem_market_col.create_index("created_at")
    
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

    t = item_payload.get("type")
    # Aceita stack também para garantir compatibilidade
    valid_types = ("skill", "skin", "evo_item", "stack", "unique") 
    if t not in valid_types:
        raise InvalidListing(f"Tipo inválido: {t}")

    if not item_payload.get("base_id") and not item_payload.get("uid"):
        raise InvalidListing("Item sem identificador (base_id ou uid).")
    
    qty = item_payload.get("qty")
    if t != "unique" and (not isinstance(qty, int) or qty <= 0):
        # Para unique a qty interna pode não existir, mas checamos a quantidade do anuncio
        pass

# --- HELPERS DE LIMPEZA DE ID ---
def _sanitize_base_id(base_id: str, item_type: str) -> str:
    """Garante que o ID não tenha prefixos duplicados (ex: tomo_tomo_)."""
    if not base_id: return base_id
    
    clean_id = base_id
    
    # 1. Remove duplicações conhecidas
    while clean_id.startswith("tomo_tomo_"):
        clean_id = clean_id.replace("tomo_tomo_", "tomo_", 1)
    while clean_id.startswith("caixa_caixa_"):
        clean_id = clean_id.replace("caixa_caixa_", "caixa_", 1)
        
    # 2. Garante o prefixo correto se não tiver
    if item_type == "skill" and not clean_id.startswith("tomo_"):
        clean_id = f"tomo_{clean_id}"
    elif item_type == "skin" and not clean_id.startswith("caixa_"):
        clean_id = f"caixa_{clean_id}"
        
    return clean_id

# --- API PÚBLICA ---

def create_listing(*, seller_id: int, item_payload: dict, unit_price: int, quantity: int = 1, target_buyer_id=None, target_buyer_name=None) -> dict:
    if gem_market_col is None: raise GemMarketError("BD Offline.")
    
    _validate_item_payload(item_payload)

    # --- CORREÇÃO CRÍTICA NA CRIAÇÃO ---
    # Limpa o ID antes de salvar no banco para evitar que entre "tomo_tomo"
    if "base_id" in item_payload:
        item_payload["base_id"] = _sanitize_base_id(item_payload["base_id"], item_payload.get("type"))

    lid = _get_next_sequence("gem_market_id")

    listing = {
        "id": lid,
        "seller_id": int(seller_id),
        "item": item_payload,
        "unit_price_gems": int(unit_price),
        "quantity": int(quantity),
        "created_at": _now_iso(),
        "active": True,
        # Suporte a venda privada se necessário no futuro
        "target_buyer_id": target_buyer_id,
        "target_buyer_name": target_buyer_name
    }

    gem_market_col.insert_one(listing)
    log.info(f"[GemMarket] Criado #{lid} (Price: {unit_price})")
    return listing

def get_listing(listing_id: int) -> Optional[dict]:
    if gem_market_col is None: return None
    return gem_market_col.find_one({"id": int(listing_id)})

def list_active(page: int = 1, page_size: int = 30, viewer_id: int = None) -> List[dict]:
    if gem_market_col is None: return []
    
    query = {"active": True}
    
    # Se viewer_id for passado, filtra itens privados corretamente
    if viewer_id:
        # Mostra itens públicos OU itens privados destinados a este viewer
        query["$or"] = [
            {"target_buyer_id": None},
            {"target_buyer_id": int(viewer_id)},
            {"seller_id": int(viewer_id)} # O vendedor sempre vê os seus
        ]
    else:
        # Se não tem viewer, mostra só públicos
        query["target_buyer_id"] = None

    cursor = gem_market_col.find(query).sort("created_at", -1)
    return list(cursor)

def list_by_seller(seller_id: int) -> List[dict]:
    if gem_market_col is None: return [] 
    return list(gem_market_col.find({"active": True, "seller_id": int(seller_id)}).sort("created_at", -1))

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
    
    # 3. Devolução Inteligente (FIX TOMO_TOMO)
    item_payload = listing.get("item", {})
    qty_left = listing.get("quantity", 0)
    
    # Quantidade total = (Qtd Lotes) * (Itens por Lote)
    pack_qty = item_payload.get("qty", 1)
    total_return = qty_left * pack_qty
    
    if total_return > 0:
        item_type = item_payload.get("type")
        
        # Lógica de reconstrução de ID corrigida:
        if item_type == "unique":
            # Devolve item único
            pdata = await player_manager.get_player_data(seller_id)
            if pdata:
                inv = pdata.get("inventory", {}) or {}
                uid = item_payload.get("uid")
                if uid in inv: uid = f"{uid}_ret"
                inv[uid] = item_payload.get("item")
                pdata["inventory"] = inv
                await player_manager.save_player_data(seller_id, pdata)
        else:
            # Devolve Stack (Skill, Skin, Material)
            raw_base_id = item_payload.get("base_id")
            # --- O FIX MÁGICO AQUI ---
            base_id_final = _sanitize_base_id(raw_base_id, item_type)
            
            pdata = await player_manager.get_player_data(seller_id)
            if pdata:
                player_manager.add_item_to_inventory(pdata, base_id_final, total_return)
                await player_manager.save_player_data(seller_id, pdata)
                
            log.info(f"♻️ [GemMarket] Devolvido: {total_return}x {base_id_final} para {seller_id}")
            
    listing["active"] = False 
    return listing

async def purchase_listing(*, buyer_pdata: dict, listing_id: int, quantity: int = 1) -> Tuple[dict, int]:
    if gem_market_col is None: raise GemMarketError("BD Offline.")
        
    buyer_id = buyer_pdata.get("user_id") or buyer_pdata.get("_id")
    
    listing = gem_market_col.find_one({"id": listing_id})
    if not listing or not listing.get("active"): raise ListingNotFound("Item indisponível.")
    
    # Validações de venda privada
    target = listing.get("target_buyer_id")
    if target and int(target) != int(buyer_id):
        raise InvalidPurchase("Este item está reservado para outro jogador.")

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
    
    # Pagamento (Gemas vão direto pro Banco/Perfil do vendedor)
    seller_id = listing["seller_id"]
    players_col.update_one({"_id": seller_id}, {"$inc": {"gems": total_price}})
    
    # Limpa cache do vendedor para ele ver as gemas logo
    await player_manager.clear_player_cache(seller_id)

    listing["quantity"] = rem
    listing["active"] = (rem > 0)
    
    return listing, total_price

def delete_listing(listing_id: int):
    """Deleta fisicamente (apenas para limpeza admin ou cancelamento total manual)"""
    if gem_market_col:
        gem_market_col.delete_one({"id": int(listing_id)})