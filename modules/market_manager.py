# modules/market_manager.py
from __future__ import annotations
import json, os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
from threading import Lock
import logging

from modules import game_data

# display_utils é usado para igualar a saída da Forja
try:
    from modules import display_utils  # deve ter: formatar_item_para_exibicao(dict) -> str
except Exception:
    display_utils = None  # fallback abaixo cuida

log = logging.getLogger(__name__)

# =========================
# Caminhos (ABSOLUTOS)
# =========================
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
FILE_PATH = DATA_DIR / "market_listings.json"
_IO_LOCK = Lock()

MAX_PRICE = 10_000_000
MAX_QTY = 1_000_000

# =========================
# Erros específicos
# =========================
class MarketError(Exception): ...
class ListingNotFound(MarketError): ...
class ListingInactive(MarketError): ...
class InvalidListing(MarketError): ...
class PermissionDenied(MarketError): ...
class InsufficientQuantity(MarketError): ...
class InvalidPurchase(MarketError): ...

# =========================
# Utilitários
# =========================
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _ensure_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(FILE_PATH):
        # Apenas cria se o arquivo REALMENTE não existir
        initial_data = {"seq": 1, "listings": []}
        with open(FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, ensure_ascii=False, indent=2)

def _load() -> Dict:
    _ensure_file()
    try:
        with _IO_LOCK, open(FILE_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                # Arquivo existe mas está vazio
                return {"seq": 1, "listings": []}
            
            data = json.loads(content)
            
            if not isinstance(data, dict) or "listings" not in data or "seq" not in data:
                log.error(f"[MARKET] Estrutura inválida no arquivo: {FILE_PATH}")
                # Não salva por cima! Retorna vazio na memória, mas mantém arquivo para análise
                return {"seq": 1, "listings": []}
                
            return data
            
    except json.JSONDecodeError as e:
        log.error(f"[MARKET] JSON corrompido ao carregar: {e}")
        # Opcional: Fazer backup do arquivo corrompido antes de permitir sobrescrever futuramente
        if os.path.exists(FILE_PATH):
            try:
                os.rename(FILE_PATH, str(FILE_PATH) + ".bak_corrupted")
                log.info("[MARKET] Arquivo corrompido renomeado para .bak_corrupted")
            except OSError:
                pass
        return {"seq": 1, "listings": []}
        
    except Exception as e:
        log.error(f"[MARKET] Erro genérico ao carregar: {e}")
        # AQUI ESTAVA O ERRO: Removemos o _save(data) daqui.
        # Se der erro de leitura, não queremos apagar o banco de dados.
        return {"seq": 1, "listings": []}

def _save(data: Dict):
    tmp_path = str(FILE_PATH) + ".tmp"
    try:
        with _IO_LOCK:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                # Força o sistema a escrever no disco físico imediatamente
                f.flush()
                os.fsync(f.fileno())
            # Troca atômica (mais seguro contra falhas no meio da escrita)
            os.replace(tmp_path, str(FILE_PATH))
    except Exception as e:
        log.error(f"[MARKET] Erro crítico ao salvar mercado: {e}")

def _norm_region(s):
    if s is None:
        return None
    s = str(s).strip()
    return s or None

# =========================
# Validações
# =========================
def _validate_item_payload(item_payload: dict):
    if not isinstance(item_payload, dict):
        raise InvalidListing("item_payload inválido.")

    t = item_payload.get("type")
    if t not in ("stack", "unique"):
        raise InvalidListing("item_payload.type deve ser 'stack' ou 'unique'.")

    if t == "stack":
        if not item_payload.get("base_id") or not isinstance(item_payload.get("base_id"), str):
            raise InvalidListing("stack.base_id obrigatório.")
        qty = item_payload.get("qty")
        if not isinstance(qty, int) or qty <= 0:
            raise InvalidListing("stack.qty deve ser inteiro > 0.")

    if t == "unique":
        if not item_payload.get("uid") or not isinstance(item_payload.get("uid"), str):
            raise InvalidListing("unique.uid obrigatório.")
        if not isinstance(item_payload.get("item"), dict):
            raise InvalidListing("unique.item deve ser um dict de instância do item.")

def _validate_price_qty(unit_price: int, quantity: int):
    if not isinstance(unit_price, int) or unit_price <= 0 or unit_price > MAX_PRICE:
        raise InvalidListing(f"unit_price deve ser inteiro entre 1 e {MAX_PRICE}.")
    if not isinstance(quantity, int) or quantity <= 0 or quantity > MAX_QTY:
        raise InvalidListing(f"quantity deve ser inteiro entre 1 e {MAX_QTY}.")

# =========================
# Helpers de exibição (mesmos ícones/nomes do inventário/forja)
# =========================
RARITY_LABEL: Dict[str, str] = {
    "comum": "Comum",
    "bom": "Boa",
    "raro": "Rara",
    "epico": "Épica",
    "lendario": "Lendária",
}

_CLASS_DMG_EMOJI_FALLBACK = {
    "guerreiro": "⚔️", "berserker": "🪓", "cacador": "🏹", "caçador": "🏹",
    "assassino": "🗡", "bardo": "🎵", "monge": "🙏", "mago": "✨", "samurai": "🗡",
}
_STAT_EMOJI_FALLBACK = {
    "dmg": "🗡", "hp": "❤️‍🩹", "vida": "❤️‍🩹", "defense": "🛡️", "defesa": "🛡️",
    "initiative": "🏃", "agilidade": "🏃", "luck": "🍀", "sorte": "🍀",
    "forca": "💪", "força": "💪", "foco": "🧘", "carisma": "😎", "bushido": "🥷",
    "inteligencia": "🧠", "inteligência": "🧠", "precisao": "🎯", "precisão": "🎯",
    "letalidade": "☠️", "furia": "🔥", "fúria": "🔥",
}

def _viewer_class_key(pdata: Optional[dict], fallback: str = "guerreiro") -> str:
    pdata = pdata or {}
    for c in [
        (pdata.get("class") or pdata.get("classe")),
        pdata.get("class_type"), pdata.get("classe_tipo"),
        pdata.get("class_key"), pdata.get("classe"),
    ]:
        if isinstance(c, dict):
            t = c.get("type")
            if isinstance(t, str) and t.strip():
                return t.strip().lower()
        if isinstance(c, str) and c.strip():
            return c.strip().lower()
    return fallback

def _class_dmg_emoji(pclass: str) -> str:
    try:
        return getattr(game_data, "CLASS_DMG_EMOJI", {}).get((pclass or "").lower(),
                _CLASS_DMG_EMOJI_FALLBACK.get((pclass or "").lower(), "🗡"))
    except Exception:
        return _CLASS_DMG_EMOJI_FALLBACK.get((pclass or "").lower(), "🗡")

def _attribute_emoji(stat: str, pclass: str) -> str:
    s = (stat or "").lower()
    try:
        attr_mod = getattr(game_data, "attributes", None)
        if attr_mod and hasattr(attr_mod, "ATTRIBUTE_ICONS"):
            em = attr_mod.ATTRIBUTE_ICONS.get(s)
            if em:
                return _class_dmg_emoji(pclass) if s == "dmg" else em
    except Exception:
        pass
    if s == "dmg":
        return _class_dmg_emoji(pclass)
    return _STAT_EMOJI_FALLBACK.get(s, "❔")

def _get_item_info(base_id: str) -> dict:
    if not base_id:
        return {}
    data = getattr(game_data, "ITEMS_DATA", {}).get(base_id, {}) or {}
    base = getattr(game_data, "ITEM_BASES", {}).get(base_id, {}) or {}
    info = {}
    info.update(base)
    info.update(data)
    return info

def _render_unique_core_line(inst: dict, viewer_class: str) -> str:
    """Fallback quando não houver display_utils: igual ao inventário."""
    base_id = inst.get("base_id") or inst.get("tpl") or inst.get("id") or "item"
    info = _get_item_info(base_id)
    name = inst.get("display_name") or info.get("display_name") or info.get("nome_exibicao") or base_id
    item_emoji = inst.get("emoji") or info.get("emoji") or _class_dmg_emoji(viewer_class)

    try:
        cur_d, max_d = inst.get("durability", [20, 20])
        cur_d, max_d = int(cur_d), int(max_d)
    except Exception:
        cur_d, max_d = 20, 20

    tier = int(inst.get("tier", 1))
    rarity_key = str(inst.get("rarity", "comum")).lower()
    rarity_label = RARITY_LABEL.get(rarity_key, rarity_key.capitalize())

    parts: List[str] = []
    ench = inst.get("enchantments") or {}
    if isinstance(ench, dict):
        for stat, data in ench.items():
            try:
                val = int((data or {}).get("value", 1))
            except Exception:
                val = int(data) if isinstance(data, (int, float)) else 1
            emo = _attribute_emoji(stat, viewer_class)
            parts.append(f"{emo}+{val}")
    stats_str = ", ".join(parts) if parts else "—"

    # Deliberadamente usamos colchetes simples para ficar próximo do display_utils
    return f"[{cur_d}/{max_d}] {item_emoji}{name} [ {tier} ] [ {rarity_label} ]: {stats_str}"

def _stack_inv_display(base_id: str, qty: int) -> str:
    info = _get_item_info(base_id)
    name = info.get("display_name") or info.get("nome_exibicao") or base_id
    emoji = info.get("emoji", "")
    return f"{(emoji or '')}{name} ×{qty}"

# =========================
# CRUD básico
# =========================
def create_listing(
    *,
    seller_id: int,
    item_payload: dict,
    unit_price: int,
    quantity: int = 1,
    region_key: Optional[str] = None,
    target_buyer_id: Optional[int] = None,   # <--- NOVO
    target_buyer_name: Optional[str] = None  # <--- NOVO (Para exibição)
) -> dict:
    _validate_item_payload(item_payload)
    _validate_price_qty(unit_price, quantity)

    data = _load()
    lid = data["seq"]
    data["seq"] += 1

    listing = {
        "id": lid,
        "seller_id": int(seller_id),
        "item": item_payload,
        "unit_price": int(unit_price),
        "quantity": int(quantity),
        "created_at": _now_iso(),
        "region_key": _norm_region(region_key),
        "active": True,
        # Adiciona os campos de reserva se existirem
        "target_buyer_id": int(target_buyer_id) if target_buyer_id else None,
        "target_buyer_name": str(target_buyer_name) if target_buyer_name else None
    }
    data["listings"].append(listing)
    _save(data)
    
    # Log ajustado para mostrar se é privado
    dest = f"-> {target_buyer_id}" if target_buyer_id else "Public"
    log.info("[market_manager] listing criada: id=%s active=%s qty=%s dest=%s",
             lid, listing["active"], listing["quantity"], dest)
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
    viewer_id: Optional[int] = None # <--- ADICIONE ESTE ARGUMENTO
) -> List[dict]:
    data = _load()
    
    # Filtro inicial: Ativos
    items = [l for l in data["listings"] if l.get("active")]

    # Filtro de Região
    if region_key:
        items = [l for l in items if l.get("region_key") == region_key]

    # --- LÓGICA DE VISUALIZAÇÃO DE PRIVADOS ---
    # Regra:
    # 1. Se não tiver target_buyer_id (Público) -> Mostra pra todos
    # 2. Se tiver target_buyer_id -> Só mostra se o viewer_id for o dono ou o destinatário
    filtered_items = []
    for l in items:
        target = l.get("target_buyer_id")
        seller = l.get("seller_id")
        
        if target is None:
            # Item público
            filtered_items.append(l)
        else:
            # Item privado: Só mostra se quem está vendo é o alvo ou o vendedor
            if viewer_id and (int(viewer_id) == int(target) or int(viewer_id) == int(seller)):
                filtered_items.append(l)
    
    items = filtered_items
    # ------------------------------------------

    # Filtro de Base ID (busca específica)
    if base_id:
        items = [
            l for l in items
            if l.get("item", {}).get("type") == "stack"
            and l["item"].get("base_id") == base_id
        ]

    if sort_by == "price":
        if price_per_unit:
            def key(l):
                it = l.get("item", {})
                if it.get("type") == "stack":
                    q = max(1, int(it.get("qty", 1)))
                    return l.get("unit_price", 0) / q
                return l.get("unit_price", 0)
            items.sort(key=key, reverse=not ascending)
        else:
            items.sort(key=lambda l: l.get("unit_price", 0), reverse=not ascending)
    else:
        items.sort(key=lambda l: l.get("created_at", ""), reverse=not ascending)

    page = max(1, int(page))
    page_size = max(1, min(100, int(page_size)))
    start = (page - 1) * page_size
    end = start + page_size
    log.info("[market_manager] list_active -> %d itens ativos (arquivo: %s)",
             len(items), FILE_PATH)
    return items[start:end]

def list_by_seller(seller_id: int) -> List[dict]:
    data = _load()
    return [l for l in data["listings"] if l.get("active") and l.get("seller_id") == int(seller_id)]

def get_listing(listing_id: int) -> Optional[dict]:
    data = _load()
    for l in data["listings"]:
        if l["id"] == int(listing_id):
            return l
    return None

def update_listing(listing: dict):
    data = _load()
    for i, l in enumerate(data["listings"]):
        if l["id"] == listing["id"]:
            data["listings"][i] = listing
            _save(data)
            return
    raise ListingNotFound(f"Listing {listing.get('id')} não encontrado.")

def delete_listing(listing_id: int):
    data = _load()
    for i, l in enumerate(data["listings"]):
        if l["id"] == int(listing_id):
            data["listings"][i]["active"] = False
            _save(data)
            return
    raise ListingNotFound(f"Listing {listing_id} não encontrado.")

# =========================
# Ações de mercado
# =========================
def cancel_listing(*, seller_id: int, listing_id: int) -> dict:
    listing = get_listing(listing_id)
    if not listing:
        raise ListingNotFound("Anúncio não existe.")
    if not listing.get("active"):
        raise ListingInactive("Anúncio já inativo.")
    if int(listing["seller_id"]) != int(seller_id):
        raise PermissionDenied("Você não pode cancelar um anúncio de outro jogador.")

    listing["active"] = False
    update_listing(listing)
    return listing

def purchase_listing(
    *,
    buyer_id: int,
    listing_id: int,
    quantity: int = 1
) -> Tuple[dict, int]:
    if not isinstance(quantity, int) or quantity <= 0:
        raise InvalidPurchase("quantity deve ser inteiro > 0.")

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

    item_payload = listing.get("item") or {}
    _validate_item_payload(item_payload)

    if item_payload["type"] == "unique" and quantity != 1:
        raise InvalidPurchase("Anúncio 'unique' só pode ser comprado em quantidade 1.")

    available = int(listing.get("quantity", 0))
    if quantity > available:
        raise InsufficientQuantity(f"Quantidade solicitada ({quantity}) > disponível ({available}).")

    total_price = int(listing["unit_price"]) * int(quantity)

    remaining = available - quantity
    listing["quantity"] = remaining
    if remaining <= 0:
        listing["active"] = False

    data["listings"][idx] = listing
    _save(data)

    return listing, total_price

# =========================
# Renderização p/ UI (usado pelos handlers)
# =========================
def render_listing_line(
    listing: dict,
    *,
    viewer_player_data: Optional[dict] = None,
    show_price_per_unit: bool = False,
    include_id: bool = True
) -> str:
    """
    - unique: usa display_utils.formatar_item_para_exibicao (igual Forja).
      Cai em fallback bonito se display_utils não existir.
    - stack : emoji+nome ×qtd no estilo inventário.
    Sempre anexa preço; opcionalmente preço/unidade (stacks) e (#id).
    """
    it = listing.get("item") or {}
    unit_price = int(listing.get("unit_price", 0))
    lid = listing.get("id")
    lots = int(listing.get("quantity", 1))

    # --- LÓGICA DE VENDA PRIVADA (Adicionado) ---
    target_id = listing.get("target_buyer_id")
    target_name = listing.get("target_buyer_name", "Desconhecido")
    is_private = target_id is not None

    # Prefixo: Cadeado se for privado
    security_prefix = "🔒 " if is_private else ""
    # Sufixo: Mostra pra quem está reservado
    reserved_suffix = f" [RESERVADO: {target_name}]" if is_private else ""
    # --------------------------------------------

    viewer_class = _viewer_class_key(viewer_player_data, "guerreiro")

    # --- TIPO UNIQUE ---
    if it.get("type") == "unique":
        inst = it.get("item") or {}
        line = None
        if display_utils and hasattr(display_utils, "formatar_item_para_exibicao"):
            try:
                line = display_utils.formatar_item_para_exibicao(inst)
            except Exception:
                line = None
        if not line:
            line = _render_unique_core_line(inst, viewer_class)

        # preço em negrito + info de lotes se houver
        suffix = f" — <b>{unit_price} 🪙</b>"
        if lots > 1:
            suffix += f" — {lots} lote(s)"
        if include_id and lid is not None:
            suffix += f" (#{lid})"
        
        # Retorna com o prefixo de segurança e o aviso de reserva
        return f"{security_prefix}{line}{suffix}{reserved_suffix}"

    # --- TIPO STACK ---
    base_id = it.get("base_id", "")
    pack_qty = int(it.get("qty", 1))
    core = _stack_inv_display(base_id, pack_qty)

    if show_price_per_unit and pack_qty > 0:
        ppu = unit_price / pack_qty
        # arredonda de forma simpática (ex.: 33.3 -> 33; 33.6 -> 34)
        ppu_disp = int(round(ppu))
        suffix = f" — <b>{unit_price} 🪙</b>/lote (~{ppu_disp} 🪙/un)"
    else:
        suffix = f" — <b>{unit_price} 🪙</b>/lote"

    if lots > 1:
        suffix += f" — {lots} lote(s)"
    if include_id and lid is not None:
        suffix += f" (#{lid})"

    # Retorna com o prefixo de segurança e o aviso de reserva
    return f"{security_prefix}{core}{suffix}{reserved_suffix}"# modules/market_manager.py
# (VERSÃO DEFINITIVA: MONGODB)
from __future__ import annotations
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple

# --- CONEXÃO COM O BANCO DE DADOS ---
# Aqui está o segredo: Tenta pegar a conexão que já existe para os jogadores.
# Assim não precisamos configurar a senha de novo aqui.
try:
    from modules.player.core import players_collection
    # Pega o objeto 'database' a partir da coleção de jogadores
    db = players_collection.database
    market_col = db["market_listings"]
    counters_col = db["counters"] # Para gerar IDs numéricos (1, 2, 3...)
except ImportError:
    # Fallback: Se der erro ao importar, tenta conectar direto (útil para testes)
    from pymongo import MongoClient
    MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/rpg_bot")
    client = MongoClient(MONGO_URL)
    db = client.get_default_database()
    market_col = db["market_listings"]
    counters_col = db["counters"]

# Tenta importar display_utils para visual
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
        query["$or"] = [
            {"target_buyer_id": None},           # Públicos
            {"target_buyer_id": {"$exists": False}}, # Compatibilidade
            {"target_buyer_id": int(viewer_id)}, # Sou o comprador
            {"seller_id": int(viewer_id)}        # Sou o vendedor
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
    
    # Retorna listagem atualizada
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
    it = listing.get("item") or {}
    unit_price = int(listing.get("unit_price", 0))
    lid = listing.get("id")
    lots = int(listing.get("quantity", 1))
    viewer_class = _viewer_class_key(viewer_player_data, "guerreiro")

    # Prefixo de Segurança
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

    # Stack
    base_id = it.get("base_id", "")
    pack_qty = int(it.get("qty", 1))
    core = _stack_inv_display(base_id, pack_qty)
    
    suffix = f" — <b>{unit_price} 🪙</b>/lote"
    if show_price_per_unit and pack_qty > 0:
        ppu = int(round(unit_price / pack_qty))
        suffix += f" (~{ppu} 🪙/un)"
    
    if include_id: suffix += f" (#{lid})"
    return f"{prefix}{core}{suffix}{reserved_suf}"