# modules/market_manager.py
# (VERSÃO DEFINITIVA: MONGODB)
from __future__ import annotations
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple

# --- CONEXÃO COM O BANCO DE DADOS ---
# Tenta reaproveitar a conexão existente do player module
try:
    from modules.player.core import players_collection
    # Pega o objeto 'database' a partir da coleção de jogadores
    if players_collection is not None:
        db = players_collection.database
        market_col = db["market_listings"]
        counters_col = db["counters"] # Para gerar IDs numéricos (1, 2, 3...)
    else:
        raise ImportError("players_collection is None")
except (ImportError, AttributeError):
    # Fallback: Se der erro ao importar ou se players_collection for None, tenta conectar direto
    # Isso é útil se o módulo player falhar ou para testes isolados
    from pymongo import MongoClient
    # Pega a URL do ambiente ou usa localhost como padrão
    MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/rpg_bot")
    client = MongoClient(MONGO_URL)
    # Pega o banco padrão da connection string
    db = client.get_default_database()
    market_col = db["market_listings"]
    counters_col = db["counters"]

# Tenta importar display_utils para visualização bonita de itens
try:
    from modules import display_utils
except Exception:
    display_utils = None

from modules import game_data

log = logging.getLogger(__name__)

MAX_PRICE = 100_000_000
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
# Helpers de Banco de Dados
# =========================
def _get_next_sequence(name: str) -> int:
    """
    Gera um ID numérico sequencial (1, 2, 3...) igual ao SQL.
    Isso é necessário porque o MongoDB usa IDs longos e feios por padrão.
    """
    ret = counters_col.find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return ret["seq"]

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# =========================
# Validações
# =========================
def _validate_item_payload(item_payload: dict):
    if not isinstance(item_payload, dict):
        raise InvalidListing("item_payload inválido.")
    t = item_payload.get("type")
    if t not in ("stack", "unique"):
        raise InvalidListing("Tipo deve ser 'stack' ou 'unique'.")
    if t == "stack":
        if not item_payload.get("base_id"): raise InvalidListing("stack.base_id obrigatório.")
    if t == "unique":
        if not item_payload.get("uid"): raise InvalidListing("unique.uid obrigatório.")

def _validate_price_qty(unit_price: int, quantity: int):
    if unit_price <= 0 or unit_price > MAX_PRICE:
        raise InvalidListing(f"Preço deve ser entre 1 e {MAX_PRICE}.")
    if quantity <= 0 or quantity > MAX_QTY:
        raise InvalidListing(f"Quantidade deve ser entre 1 e {MAX_QTY}.")

# =========================
# Funções Principais (CRUD com MongoDB)
# =========================

def create_listing(
    *,
    seller_id: int,
    item_payload: dict,
    unit_price: int,
    quantity: int = 1,
    region_key: Optional[str] = None,
    target_buyer_id: Optional[int] = None,   # <--- PRIVADO
    target_buyer_name: Optional[str] = None  # <--- PRIVADO
) -> dict:
    """Cria um anúncio e salva no MongoDB."""
    _validate_item_payload(item_payload)
    _validate_price_qty(unit_price, quantity)

    # Gera próximo ID (ex: #150)
    lid = _get_next_sequence("market_id")

    listing = {
        "id": lid, # ID Inteiro legível
        "seller_id": int(seller_id),
        "item": item_payload,
        "unit_price": int(unit_price),
        "quantity": int(quantity),
        "created_at": _now_iso(),
        "region_key": region_key,
        "active": True,
        # Campos de Venda Privada
        "target_buyer_id": int(target_buyer_id) if target_buyer_id else None,
        "target_buyer_name": str(target_buyer_name) if target_buyer_name else None
    }

    market_col.insert_one(listing)
    
    log.info(f"[MARKET] Listagem #{lid} criada (MongoDB). Privado: {bool(target_buyer_id)}")
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
    """
    Lista itens ativos do MongoDB com suporte a filtro privado.
    """
    # Filtro base: Ativo = True
    query = {"active": True}

    if region_key:
        query["region_key"] = region_key
    
    if base_id:
        query["item.base_id"] = base_id

    # --- LÓGICA DE PRIVACIDADE ---
    if viewer_id:
        # Mostra itens públicos OU itens onde o usuário é o alvo/vendedor
        query["$or"] = [
            {"target_buyer_id": None},           # Públicos
            {"target_buyer_id": {"$exists": False}}, # Compatibilidade (itens antigos)
            {"target_buyer_id": int(viewer_id)}, # Sou o comprador alvo
            {"seller_id": int(viewer_id)}        # Sou o vendedor (meus itens)
        ]
    else:
        # Se não tem viewer_id, mostra só públicos
        query["target_buyer_id"] = None

    # Ordenação
    sort_dir = 1 if ascending else -1
    mongo_sort = [("created_at", sort_dir)]
    if sort_by == "price":
        # Se for preço por unidade, o mongo ordena direto pelo unit_price (simplificado)
        mongo_sort = [("unit_price", sort_dir)]

    # Paginação
    skip = (page - 1) * page_size
    
    # Executa a busca no banco
    cursor = market_col.find(query).sort(mongo_sort).skip(skip).limit(page_size)
    return list(cursor)

def list_by_seller(seller_id: int) -> List[dict]:
    return list(market_col.find({"active": True, "seller_id": int(seller_id)}))

def get_listing(listing_id: int) -> Optional[dict]:
    return market_col.find_one({"id": int(listing_id)})

def delete_listing(listing_id: int):
    """Marca como inativo (soft delete)."""
    res = market_col.update_one({"id": int(listing_id)}, {"$set": {"active": False}})
    if res.modified_count == 0:
        # Se não achou ativo, tenta ver se existe inativo, só pra não dar erro
        if not market_col.find_one({"id": int(listing_id)}):
             raise ListingNotFound(f"Listing {listing_id} não encontrada.")

def purchase_listing(
    *,
    buyer_id: int,
    listing_id: int,
    quantity: int = 1,
    context=None 
) -> Tuple[dict, int]:
    """
    Processa a compra atomicamente no MongoDB.
    """
    listing = get_listing(listing_id)
    if not listing:
        raise ListingNotFound("Anúncio não encontrado.")
    
    if not listing.get("active"):
        raise ListingInactive("Anúncio já foi vendido ou cancelado.")
    
    if int(listing["seller_id"]) == int(buyer_id):
        raise InvalidPurchase("Não pode comprar o próprio item.")

    # Validação de Venda Privada
    target = listing.get("target_buyer_id")
    if target is not None and int(target) != int(buyer_id):
        target_name = listing.get("target_buyer_name", "outro jogador")
        raise PermissionDenied(f"🔒 Item reservado exclusivamente para: {target_name}")

    available = int(listing.get("quantity", 0))
    if quantity > available:
        raise InsufficientQuantity(f"Estoque insuficiente. Restam {available}.")

    total_price = int(listing["unit_price"]) * quantity

    # Atualiza estoque atomicamente no banco
    new_qty = available - quantity
    update_doc = {"quantity": new_qty}
    if new_qty <= 0:
        update_doc["active"] = False

    market_col.update_one({"_id": listing["_id"]}, {"$set": update_doc})
    
    # Retorna listagem atualizada para o handler
    listing["quantity"] = new_qty
    listing["active"] = (new_qty > 0)
    
    return listing, total_price

# =========================
# Renderização Visual
# =========================
RARITY_LABEL = {"comum": "Comum", "bom": "Boa", "raro": "Rara", "epico": "Épica", "lendario": "Lendária"}
_CLASS_DMG_EMOJI_FALLBACK = {"guerreiro": "⚔️", "berserker": "🪓", "cacador": "🏹", "assassino": "🗡", "bardo": "🎵", "monge": "🙏", "mago": "✨", "samurai": "🗡"}
_STAT_EMOJI_FALLBACK = {"dmg": "🗡", "hp": "❤️‍🩹", "defense": "🛡️", "initiative": "🏃", "luck": "🍀", "forca": "💪", "inteligencia": "🧠", "furia": "🔥"}

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
    """Gera a linha de texto para o menu do Telegram."""
    it = listing.get("item") or {}
    unit_price = int(listing.get("unit_price", 0))
    lid = listing.get("id")
    
    # A quantidade a mostrar depende se é único ou stack
    # Mas geralmente é a quantidade de 'lotes' restantes
    lots = int(listing.get("quantity", 1))
    
    viewer_class = _viewer_class_key(viewer_player_data, "guerreiro")

    # Prefixo de Segurança (Cadeado)
    target_id = listing.get("target_buyer_id")
    target_name = listing.get("target_buyer_name", "Alguém")
    is_private = target_id is not None
    prefix = "🔒 " if is_private else ""
    reserved_suf = f" [RESERVADO: {target_name}]" if is_private else ""

    text = ""
    # --- TIPO UNIQUE ---
    if it.get("type") == "unique":
        inst = it.get("item") or {}
        try:
            if display_utils: text = display_utils.formatar_item_para_exibicao(inst)
        except: pass
        if not text: text = _render_unique_core_line(inst, viewer_class)
        
        suffix = f" — <b>{unit_price} 🪙</b>"
        if include_id: suffix += f" (#{lid})"
        return f"{prefix}{text}{suffix}{reserved_suf}"

    # --- TIPO STACK ---
    base_id = it.get("base_id", "")
    # Em stacks, a 'quantidade' do item payload é o tamanho do lote (ex: 10 poções por lote)
    pack_qty = int(it.get("qty", 1))
    
    # O display mostra: "Poção de Vida x10" (tamanho do lote)
    core = _stack_inv_display(base_id, pack_qty)
    
    suffix = f" — <b>{unit_price} 🪙</b>/lote"
    
    # Calcula preço por unidade para ajudar o jogador
    if show_price_per_unit and pack_qty > 0:
        ppu = int(round(unit_price / pack_qty))
        suffix += f" (~{ppu} 🪙/un)"
    
    if include_id: suffix += f" (#{lid})"
    
    return f"{prefix}{core}{suffix}{reserved_suf}"