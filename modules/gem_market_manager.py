# modules/gem_market_manager.py

from __future__ import annotations
import json, os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
from threading import Lock
import logging

# --- IMPORTANTE: Helpers de Jogador para Gemas ---
# Precisamos de uma forma de ler/escrever gemas.
# Vamos assumir que o teu player_manager ou outro módulo tem estas funções.
# Se não tiver, teremos de as criar.
try:
    # Tenta importar as funções reais
    from modules.player_manager import get_gems, spend_gems, add_gems
except ImportError:
    # Se não existirem, cria funções "fallback" para usar pdata["gems"]
    logging.warning("[GemMarket] Funções get/spend/add_gems não encontradas no player_manager. A usar fallback (pdata['gems']).")
    
    def _ival(v, default=0):
        try: return int(v)
        except: return default

    def get_gems(pdata: dict) -> int:
        return _ival(pdata.get("gems"), 0)

    def spend_gems(pdata: dict, amount: int) -> bool:
        gems = get_gems(pdata)
        amount = _ival(amount)
        if gems < amount:
            return False
        pdata["gems"] = gems - amount
        return True

    def add_gems(pdata: dict, amount: int):
        gems = get_gems(pdata)
        amount = _ival(amount)
        pdata["gems"] = gems + amount

# --- Configuração do Gestor ---

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
# --- NOVO ARQUIVO DE DADOS ---
FILE_PATH = DATA_DIR / "gem_market_listings.json"
_IO_LOCK = Lock()

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
# Gestão do JSON (Igual ao market_manager)
# =========================
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _ensure_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(FILE_PATH):
        _save({"seq": 1, "listings": []}) # Começa a sequência de ID em 1

def _load() -> Dict:
    _ensure_file()
    try:
        with _IO_LOCK, open(FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict) or "listings" not in data or "seq" not in data:
                raise ValueError("Formato inválido")
            return data
    except Exception:
        data = {"seq": 1, "listings": []}
        _save(data)
        return data

def _save(data: Dict):
    tmp_path = str(FILE_PATH) + ".tmp"
    with _IO_LOCK:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, str(FILE_PATH))

# =========================
# Validações
# =========================
def _validate_item_payload(item_payload: dict):
    """
    Valida o 'item' que está a ser vendido.
    Pode ser 'skill', 'skin', ou 'evo_item'.
    """
    if not isinstance(item_payload, dict):
        raise InvalidListing("item_payload inválido.")

    t = item_payload.get("type")
    if t not in ("skill", "skin", "evo_item"):
        raise InvalidListing("item_payload.type deve ser 'skill', 'skin', ou 'evo_item'.")

    if t == "skill":
        if not item_payload.get("skill_id"):
            raise InvalidListing("skill.skill_id obrigatório.")
    
    elif t == "skin":
        if not item_payload.get("skin_id"):
            raise InvalidListing("skin.skin_id obrigatório.")
    
    elif t == "evo_item":
        if not item_payload.get("base_id"):
            raise InvalidListing("evo_item.base_id obrigatório.")
        qty = item_payload.get("qty")
        if not isinstance(qty, int) or qty <= 0:
            raise InvalidListing("evo_item.qty deve ser inteiro > 0.")

def _validate_price_qty(unit_price: int, quantity: int):
    if not isinstance(unit_price, int) or unit_price <= 0 or unit_price > MAX_GEM_PRICE:
        raise InvalidListing(f"unit_price (gemas) deve ser entre 1 e {MAX_GEM_PRICE}.")
    if not isinstance(quantity, int) or quantity <= 0:
        raise InvalidListing("quantity (lotes) deve ser > 0.")

# =========================
# API Pública do Gestor
# =========================

def create_listing(
    *,
    seller_id: int,
    item_payload: dict,
    unit_price: int, # Preço em GEMAS
    quantity: int = 1  # Quantos lotes (para evo_items)
) -> dict:
    """
    Cria uma nova listagem no gem_market_listings.json.
    NÃO mexe nas gemas do jogador, apenas cria a listagem.
    """
    _validate_item_payload(item_payload)
    _validate_price_qty(unit_price, quantity)

    data = _load()
    lid = data["seq"]
    data["seq"] += 1

    listing = {
        "id": lid,
        "seller_id": int(seller_id),
        "item": item_payload,
        "unit_price_gems": int(unit_price), # Preço em Gemas
        "quantity": int(quantity),        # Lotes disponíveis
        "created_at": _now_iso(),
        "active": True,
    }
    data["listings"].append(listing)
    _save(data)
    log.info(f"[GemMarket] Listagem (Gemas) criada: id={lid} price={unit_price} item={item_payload}")
    return listing

def get_listing(listing_id: int) -> Optional[dict]:
    data = _load()
    for l in data["listings"]:
        if l["id"] == int(listing_id):
            return l
    return None

def list_active(page: int = 1, page_size: int = 30) -> List[dict]:
    """Lista todas as listagens ativas, ordenadas da mais recente para a mais antiga."""
    data = _load()
    items = [l for l in data["listings"] if l.get("active")]
    
    # Ordena por 'created_at' descendente (mais novo primeiro)
    items.sort(key=lambda l: l.get("created_at", ""), reverse=True)

    page = max(1, int(page))
    page_size = max(1, min(100, int(page_size)))
    start = (page - 1) * page_size
    end = start + page_size
    log.info(f"[GemMarket] list_active -> {len(items)} itens ativos (arquivo: {FILE_PATH})")
    return items[start:end]

def list_by_seller(seller_id: int) -> List[dict]:
    data = _load()
    return [l for l in data["listings"] if l.get("active") and l.get("seller_id") == int(seller_id)]

def cancel_listing(*, seller_id: int, listing_id: int) -> dict:
    """
    Cancela uma listagem. Chamado pelo handler, que é responsável
    por devolver o item (skill/skin/evo_item) ao inventário do vendedor.
    """
    data = _load()
    idx = None
    listing = None
    for i, l in enumerate(data["listings"]):
        if l["id"] == int(listing_id):
            idx = i
            listing = l
            break

    if listing is None:
        raise ListingNotFound("Anúncio não existe.")
    if not listing.get("active"):
        raise ListingInactive("Anúncio já inativo.")
    if int(listing["seller_id"]) != int(seller_id):
        raise PermissionDenied("Você não pode cancelar um anúncio de outro jogador.")

    listing["active"] = False
    data["listings"][idx] = listing
    _save(data)
    log.info(f"[GemMarket] Listagem {listing_id} cancelada pelo vendedor {seller_id}.")
    return listing

def purchase_listing(
    *,
    buyer_pdata: dict, # pdata completo do comprador
    seller_pdata: dict, # pdata completo do vendedor
    listing_id: int,
    quantity: int = 1
) -> Tuple[dict, int]:
    """
    Processa a compra COMPLETA.
    Esta função FAZ a transação de gemas.
    """
    if not isinstance(quantity, int) or quantity <= 0:
        raise InvalidPurchase("quantity deve ser inteiro > 0.")
    
    buyer_id = buyer_pdata.get("user_id") or buyer_pdata.get("_id")
    seller_id = seller_pdata.get("user_id") or seller_pdata.get("_id")

    data = _load()
    idx = None
    listing = None
    for i, l in enumerate(data["listings"]):
        if l["id"] == int(listing_id):
            idx = i
            listing = l
            break

    if listing is None:
        raise ListingNotFound("Anúncio não encontrado.")
    if not listing.get("active"):
        raise ListingInactive("Anúncio inativo.")
    if int(listing["seller_id"]) == int(buyer_id):
        raise InvalidPurchase("Não é possível comprar o próprio anúncio.")
    
    available = int(listing.get("quantity", 0))
    if quantity > available:
        raise InsufficientQuantity(f"Quantidade solicitada ({quantity}) > disponível ({available}).")

    total_price_gems = int(listing["unit_price_gems"]) * int(quantity)

    # 1. Tenta gastar as gemas do comprador
    if not spend_gems(buyer_pdata, total_price_gems):
        raise InsufficientGems(f"Gemas insuficientes. Você precisa de {total_price_gems} 💎.")
    
    # 2. Adiciona as gemas ao vendedor (pode ter uma taxa no futuro)
    add_gems(seller_pdata, total_price_gems)
    
    # 3. Atualiza a listagem no JSON
    remaining = available - quantity
    listing["quantity"] = remaining
    if remaining <= 0:
        listing["active"] = False

    data["listings"][idx] = listing
    _save(data)

    log.info(f"[GemMarket] Compra concluída: L{listing_id} por B{buyer_id} de S{seller_id} por {total_price_gems} gemas.")
    
    # Retorna a listagem atualizada e o preço total pago
    return listing, total_price_gems