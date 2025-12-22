# modules/market_manager.py
# (VERSÃO CORRIGIDA: VARIÁVEL LOG)
from __future__ import annotations
import logging
import os
import sys
import certifi
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
from pymongo import MongoClient
import asyncio
from modules import player_manager

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
    market_col = db["market"]
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
    # --- Validações e Buscas ---
    listing = get_listing(listing_id)
    if not listing: raise ListingNotFound("Anúncio não encontrado.")
    if not listing.get("active"): raise ListingInactive("Anúncio inativo.")
    
    seller_id = int(listing["seller_id"])
    buyer_id = int(buyer_id)

    if seller_id == buyer_id: raise InvalidPurchase("Não pode comprar seu próprio item.")

    target = listing.get("target_buyer_id")
    if target is not None and int(target) != buyer_id:
        raise PermissionDenied(f"🔒 Item reservado para: {listing.get('target_buyer_name')}")

    available = int(listing.get("quantity", 0))
    if quantity > available:
        raise InsufficientQuantity(f"Estoque insuficiente ({available}).")

    # --- Cálculos e Atualização do Anúncio ---
    total_price = int(listing["unit_price"]) * quantity
    new_qty = available - quantity
    
    update_doc = {"quantity": new_qty}
    if new_qty <= 0: update_doc["active"] = False
    
    # Atualiza o anúncio no banco
    market_col.update_one({"_id": listing["_id"]}, {"$set": update_doc})
    
    # --- PAGAMENTO E LIMPEZA DE CACHE (A CORREÇÃO) ---
    try:
        # 1. Paga no Banco de Dados (Isso você já tinha e funcionava)
        result = db["players"].update_one(
            {"_id": seller_id}, 
            {"$inc": {"gold": total_price}}
        )
        
        if result.modified_count > 0:
            log.info(f"💰 [MARKET] Vendedor {seller_id} recebeu +{total_price} gold no banco.")
            
            # 2. LIMPEZA DE CACHE (A PEÇA QUE FALTAVA)
            # Isso obriga o bot a ler o banco novamente na próxima ação, 
            # impedindo que ele sobrescreva o ouro novo com o velho da memória.
            try:
                # Cria um novo loop de eventos temporário apenas para rodar essa limpeza
                # ou usa o loop existente se já estivermos dentro de um.
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(player_manager.clear_player_cache(seller_id))
                except RuntimeError:
                    # Se não houver loop rodando, usamos run()
                    asyncio.run(player_manager.clear_player_cache(seller_id))
                
                log.info(f"🧹 [MARKET] Cache do vendedor {seller_id} limpo (Async).")
            except Exception as e_cache:
                log.warning(f"⚠️ [MARKET] Falha ao limpar cache: {e_cache}")

        else:
            log.warning(f"⚠️ [MARKET] Venda ok, mas vendedor {seller_id} não encontrado no banco.")
            
    except Exception as e:
        log.error(f"🔥 [MARKET] Erro crítico no pagamento: {e}")

    # Retorno
    listing["quantity"] = new_qty
    listing["active"] = (new_qty > 0)
    
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

# No arquivo modules/market_manager.py

# --- NOVOS ÍCONES DE RARIDADE (Estilo RPG) ---
RARITY_ICONS = {
    "comum": "⚪️",      # Common (Cinza/Branco)
    "incomum": "🟢",    # Uncommon (Verde)
    "bom": "🟢",        # (Compatibilidade)
    "raro": "🔵",       # Rare (Azul)
    "epico": "🟣",      # Epic (Roxo)
    "lendario": "🟠",   # Legendary (Laranja/Dourado)
    "mitico": "🔴",     # Mythic (Vermelho)
    "divino": "✨"      # Divine
}

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
    available_lots = int(listing.get("quantity", 1))
    
    # Identificação do alvo (Venda Privada)
    target_id = listing.get("target_buyer_id")
    target_name = listing.get("target_buyer_name", "Alguém")
    is_private = target_id is not None
    
    # Ícones de estado
    lock_icon = "🔒" if is_private else "🛒"
    
    # --- RENDERIZAÇÃO: ITEM ÚNICO (Equipamentos, etc) ---
    if it.get("type") == "unique":
        inst = it.get("item") or {}
        
        # Dados básicos
        base_id = inst.get("base_id") or "item"
        name = inst.get("display_name") or base_id
        emoji = inst.get("emoji") or "⚔️"
        tier = inst.get("tier", 1)
        rarity_str = str(inst.get("rarity", "comum")).lower()
        rarity_icon = RARITY_ICONS.get(rarity_str, "⚪️")
        
        # Formatação dos Atributos (Simplificada para caber na linha)
        stats_txt = ""
        ench = inst.get("enchantments") or {}
        if isinstance(ench, dict):
            primary_stats = []
            for k, v in ench.items():
                if isinstance(v, dict) and "value" in v:
                    # Tenta pegar um emoji legal para o stat, ou usa o padrão
                    val = v["value"]
                    if val > 0:
                        primary_stats.append(f"{k.upper()}+{val}")
            
            # Pega os 2 primeiros atributos para não poluir
            if primary_stats:
                stats_txt = f" │ 🔥 {', '.join(primary_stats[:2])}"

        # Montagem da Linha 1: Identificação visual forte
        line1 = f"<b>{emoji} {name}</b> {rarity_icon} <code>[T{tier}]</code>{stats_txt}"
        
        # Montagem da Linha 2: Preço e ID (estilo "ficha técnica")
        line2_parts = [f"💰 <b>{unit_price}</b>"]
        if is_private:
            line2_parts.append(f"👤 Reservado: {target_name}")
        
        if include_id:
            # ID fica discreto no final
            id_tag = f"🆔 <code>#{lid}</code>"
        
        return f"{line1}\n   └ {id_tag} │ {' │ '.join(line2_parts)}"

    # --- RENDERIZAÇÃO: STACK (Poções, Materiais, etc) ---
    else:
        base_id = it.get("base_id", "")
        pack_qty = int(it.get("qty", 1))
        
        # Tenta pegar info do game_data
        info = _get_item_info(base_id)
        name = info.get("display_name") or base_id
        emoji = info.get("emoji") or "📦"
        rarity_str = str(info.get("rarity", "comum")).lower()
        rarity_icon = RARITY_ICONS.get(rarity_str, "⚪️")

        # Linha 1: Nome e Quantidade do Lote
        line1 = f"<b>{emoji} {name}</b> {rarity_icon} <code>x{pack_qty}</code>"

        # Linha 2: Preço e Estoque
        price_txt = f"💰 <b>{unit_price}</b>"
        stock_txt = ""
        
        if available_lots > 1:
            stock_txt = f"📦 Restam: {available_lots}"
        else:
            stock_txt = "📦 Último lote!"
            
        unit_calc = ""
        if show_price_per_unit and pack_qty > 1:
            ppu = int(unit_price / pack_qty)
            unit_calc = f"({ppu}/un)"

        parts_l2 = [price_txt + unit_calc]
        if stock_txt: parts_l2.append(stock_txt)
        if is_private: parts_l2.append(f"🔒 {target_name}")

        id_tag = f"🆔 <code>#{lid}</code>" if include_id else ""

        return f"{line1}\n   └ {id_tag} │ {' │ '.join(parts_l2)}"