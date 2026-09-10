# modules/market_manager.py
# (VERSÃO CORRIGIDA: Suporte Híbrido ObjectId + Int)

from __future__ import annotations
import logging
import os
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Union
from pymongo import MongoClient, ReturnDocument
from bson import ObjectId # Importante

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
    market_col.create_index("id", unique=True)
    market_col.create_index("active")
except Exception as e:
    log.critical(f"🔥 FALHA AO CONECTAR MONGODB (MARKET): {e}")
    market_col = None
    counters_col = None

try:
    from modules import display_utils
    from modules import game_data
    from modules.game_data.items_evolution import EVOLUTION_ITEMS_DATA
except ImportError:
    display_utils = None
    game_data = None
    EVOLUTION_ITEMS_DATA = {}

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
    seller_id: Union[int, str],
    item_payload: dict,
    unit_price: int,
    quantity: int = 1,
    region_key: Optional[str] = None,
    target_buyer_id: Optional[Union[int, str]] = None,
    target_buyer_name: Optional[str] = None,
    seller_name: Optional[str] = None,
    currency: str = "ouro" # 👈 1. ADICIONE O PARÂMETRO AQUI
) -> dict:
    if market_col is None: raise MarketError("Banco de dados offline.")
    
    _validate_price_qty(unit_price, quantity)

    base_id = item_payload.get("base_id")

    if base_id and base_id in EVOLUTION_ITEMS_DATA:
        item_name = EVOLUTION_ITEMS_DATA[base_id].get("display_name", "Item de Evolução")
        raise InvalidListing(f"🚫 '{item_name}' deve ser vendido no Comércio de Relíquias (Gemas).")

    if base_id and base_id in _BLOCKED_SPECIFIC_IDS:
        raise InvalidListing(f"🚫 Este item ('{base_id}') não pode ser comercializado aqui.")

    lid = _get_next_sequence("market_id")

    def _safe_id(uid):
        if uid is None: return None
        if isinstance(uid, int): return uid
        if isinstance(uid, str) and uid.isdigit(): return int(uid)
        return str(uid) 

    listing = {
        "id": lid,
        "seller_id": _safe_id(seller_id),
        "seller_name": str(seller_name) if seller_name else None,
        "item": item_payload,
        "unit_price": int(unit_price),
        "quantity": int(quantity),
        "currency": currency, # 👈 2. ADICIONE AQUI PARA SALVAR NO BANCO
        "created_at": _now_iso(),
        "region_key": region_key,
        "active": True,
        "target_buyer_id": _safe_id(target_buyer_id),
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
    viewer_id: Optional[Union[int, str]] = None
) -> List[dict]:
    if market_col is None: return []
    query = {"active": True}

    if region_key: query["region_key"] = region_key
    if base_id: query["item.base_id"] = base_id

    if viewer_id:
        vid_str = str(viewer_id)
        vid_val = int(viewer_id) if str(viewer_id).isdigit() else viewer_id
        
        query["$or"] = [
            {"target_buyer_id": None},
            {"target_buyer_id": vid_val},
            {"target_buyer_id": vid_str},
            {"seller_id": vid_val},
            {"seller_id": vid_str}
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

def list_by_seller(seller_id: Union[int, str]) -> List[dict]:
    if market_col is None: return []
    sid_val = int(seller_id) if str(seller_id).isdigit() else seller_id
    sid_str = str(seller_id)
    # Busca tanto por ID antigo quanto novo
    return list(market_col.find({
        "active": True, 
        "$or": [{"seller_id": sid_val}, {"seller_id": sid_str}]
    }))

def get_listing(listing_id: Union[int, str, ObjectId]) -> Optional[dict]:
    """
    Busca flexível: Aceita ID numérico (legado) ou ObjectId (novo).
    """
    if market_col is None: return None
    
    # 1. Se for ObjectId puro
    if isinstance(listing_id, ObjectId):
        return market_col.find_one({"_id": listing_id})
    
    # 2. Se for String
    if isinstance(listing_id, str):
        # É ObjectId em string?
        if ObjectId.is_valid(listing_id):
            return market_col.find_one({"_id": ObjectId(listing_id)})
        # É número em string?
        if listing_id.isdigit():
            return market_col.find_one({"id": int(listing_id)})
            
    # 3. Se for Inteiro
    if isinstance(listing_id, int):
        return market_col.find_one({"id": listing_id})

    return None

def delete_listing(listing_id: Union[int, str, ObjectId]):
    """Desativa listagem de forma segura."""
    if market_col is not None:
        listing = get_listing(listing_id)
        if listing:
            # Usa o _id recuperado para garantir update correto
            market_col.update_one({"_id": listing["_id"]}, {"$set": {"active": False}})

# ==============================================================================
#  FUNÇÃO DE COMPRA
# ==============================================================================

async def purchase_listing(
    *,
    buyer_id: Union[int, str],
    listing_id: Union[int, str, ObjectId],
    quantity: int = 1,
    context=None
) -> Tuple[dict, int]:

    from modules.player import inventory as inv_module

    try:
        quantity = int(quantity or 1)
    except Exception:
        quantity = 0

    if quantity <= 0:
        raise InvalidPurchase("Quantidade inválida.")

    listing = get_listing(listing_id)

    if not listing:
        raise ListingNotFound("Anúncio não encontrado.")

    if not listing.get("active"):
        raise ListingInactive("Anúncio inativo ou já vendido.")

    seller_id = listing["seller_id"]
    buyer_id_str = str(buyer_id)
    seller_id_str = str(seller_id)

    if seller_id_str == buyer_id_str:
        raise InvalidPurchase("Você não pode comprar seu próprio item.")

    target = listing.get("target_buyer_id")
    if target is not None and str(target) != buyer_id_str:
        raise PermissionDenied(f"🔒 Item reservado para: {listing.get('target_buyer_name')}")

    available = int(listing.get("quantity", 0) or 0)
    if quantity > available:
        raise InsufficientQuantity(f"Estoque insuficiente ({available} disponíveis).")

    item_payload = listing.get("item", {}) or {}
    unit_price = int(listing.get("unit_price", 0) or 0)
    total_price = unit_price * quantity

    moeda = str(listing.get("currency", "ouro") or "ouro").lower()
    campo_moeda = "gems" if moeda in ["gema", "gemas"] else "gold"
    simbolo = "💎" if campo_moeda == "gems" else "🪙"

    buyer_data = await player_manager.get_player_data(buyer_id)
    if not buyer_data:
        raise ValueError("Comprador não encontrado.")

    buyer_balance = int(buyer_data.get(campo_moeda, 0) or 0)

    if buyer_balance < total_price:
        raise ValueError(f"Saldo insuficiente. Necessário: {total_price:,} {simbolo}")

    # =========================================================
    # TRAVA ANTI-FRAUDE / ANTI-CLIQUE DUPLO
    # Reserva o estoque direto no MongoDB antes de entregar item.
    # Se outro jogador comprar ao mesmo tempo, só um passa.
    # =========================================================
    reserved_listing = market_col.find_one_and_update(
        {
            "_id": listing["_id"],
            "active": True,
            "quantity": {"$gte": quantity}
        },
        {
            "$inc": {"quantity": -quantity}
        },
        return_document=ReturnDocument.AFTER
    )

    if not reserved_listing:
        raise ListingInactive("Este anúncio acabou de ser comprado por outro jogador.")

    comprador_salvo = False

    try:
        # 1. Cobra comprador
        buyer_data[campo_moeda] = buyer_balance - total_price

        # 2. Entrega item exatamente conforme o anúncio
        item_type = item_payload.get("type")

        if item_type == "stack":
            base_id = item_payload.get("base_id")
            stack_size = int(item_payload.get("qty", 1) or 1)
            total_items_to_give = quantity * stack_size

            if not base_id or total_items_to_give <= 0:
                raise InvalidPurchase("Item empilhável inválido no anúncio.")

            inv_module.add_item_to_inventory(buyer_data, base_id, total_items_to_give)

        elif item_type == "unique":
            base_item_data = item_payload.get("item", {})

            if not isinstance(base_item_data, dict) or not base_item_data:
                raise InvalidPurchase("Item único inválido no anúncio.")

            for _ in range(quantity):
                inv_module.add_unique_item(buyer_data, base_item_data.copy())

        else:
            raise InvalidPurchase("Tipo de anúncio inválido.")

        await player_manager.save_player_data(buyer_id, buyer_data)
        comprador_salvo = True

    except Exception:
        # Se falhou antes de salvar o comprador, devolve o estoque ao anúncio.
        if not comprador_salvo:
            market_col.update_one(
                {"_id": listing["_id"]},
                {
                    "$inc": {"quantity": quantity},
                    "$set": {"active": True}
                }
            )
        raise

    # 3. Fecha anúncio se zerou
    new_qty = int(reserved_listing.get("quantity", 0) or 0)

    if new_qty <= 0:
        market_col.update_one(
            {"_id": listing["_id"]},
            {
                "$set": {
                    "active": False,
                    "sold_at": _now_iso()
                }
            }
        )

    # 4. Taxa real da Coroa: 10%
    taxa_reino = int(total_price * 0.10)
    valor_vendedor = max(0, total_price - taxa_reino)

    # 5. Paga vendedor já descontando taxa
    try:
        seller_data = await player_manager.get_player_data(seller_id)

        if seller_data:
            current_seller_balance = int(seller_data.get(campo_moeda, 0) or 0)
            seller_data[campo_moeda] = current_seller_balance + valor_vendedor
            await player_manager.save_player_data(seller_id, seller_data)
        else:
            if isinstance(seller_id, int) or (isinstance(seller_id, str) and seller_id.isdigit()):
                db["players"].update_one(
                    {"_id": int(seller_id)},
                    {"$inc": {campo_moeda: valor_vendedor}}
                )
            else:
                q_id = ObjectId(seller_id) if ObjectId.is_valid(str(seller_id)) else seller_id
                db["users"].update_one(
                    {"_id": q_id},
                    {"$inc": {campo_moeda: valor_vendedor}}
                )

    except Exception as e:
        log.error(f"🔥 [MARKET] Erro pagando vendedor {seller_id}: {e}")

    listing["quantity"] = new_qty
    listing["active"] = new_qty > 0
    listing["tax"] = taxa_reino
    listing["seller_amount"] = valor_vendedor
    listing["currency"] = moeda

    return listing, total_price

# =========================
#  FUNÇÃO DE CANCELAMENTO
# =========================

async def cancel_listing(listing_id: Union[int, str, ObjectId]) -> bool:
    from modules.player import inventory as inv_module

    listing = get_listing(listing_id)
    if not listing: raise ListingNotFound("Anúncio não encontrado.")
    if not listing.get("active"): raise ListingInactive("Este anúncio já foi finalizado ou cancelado.")

    seller_id = listing["seller_id"] 
    quantity_left = int(listing.get("quantity", 0))

    if quantity_left <= 0:
        market_col.update_one({"_id": listing["_id"]}, {"$set": {"active": False}})
        return True

    seller_data = await player_manager.get_player_data(seller_id)
    if not seller_data:
        raise MarketError("Erro: Conta vendedora não encontrada.")

    item_payload = listing.get("item", {})
    item_type = item_payload.get("type")
    items_refunded_count = 0

    if item_type == "stack":
        base_id = item_payload.get("base_id")
        stack_size = int(item_payload.get("qty", 1))
        total_to_give = quantity_left * stack_size
        inv_module.add_item_to_inventory(seller_data, base_id, total_to_give)
        items_refunded_count = total_to_give

    elif item_type == "unique":
        base_item_data = item_payload.get("item", {}).copy()
        for _ in range(quantity_left):
            inv_module.add_unique_item(seller_data, base_item_data)
        items_refunded_count = quantity_left

    await player_manager.save_player_data(seller_id, seller_data)
    
    # IMPORTANTE: Usa _id para cancelar
    market_col.update_one({"_id": listing["_id"]}, {"$set": {"active": False}})
    
    log.info(f"♻️ [MARKET] Anúncio {listing_id} cancelado. {items_refunded_count} itens devolvidos.")
    return listing