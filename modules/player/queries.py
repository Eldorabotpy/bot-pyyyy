# modules/player/queries.py
# (VERSÃO CORRIGIDA: Busca Híbrida Inteligente + Fallback Regex)

from __future__ import annotations
import re as _re
import unicodedata
import logging
import asyncio
from typing import AsyncIterator, Iterator, Tuple, Optional, Union, List
from bson import ObjectId

# Imports do Core
from .core import players_collection, get_player_data, save_player_data, clear_player_cache, users_collection

# Alias para banco legado
_legacy_db = players_collection

logger = logging.getLogger(__name__)

# ========================================
# FUNÇÕES AUXILIARES DE NORMALIZAÇÃO
# ========================================

def _get_users_collection():
    return users_collection

def _normalize_char_name(_s: str) -> str:
    if not isinstance(_s, str):
        return ""
    INVISIBLE_CHARS = r"[\u200B-\u200D\uFEFF]"
    s = _re.sub(INVISIBLE_CHARS, "", _s)
    s = _re.sub(r"[\r\n\t]+", " ", s)
    s = _re.sub(r"\s+", " ", s).strip().lower()
    return s

_VS_SET = {0xFE0E, 0xFE0F}
def _is_skin_tone(cp: int) -> bool:
    return 0x1F3FB <= cp <= 0x1F3FF

def _strip_vs_and_tones(s: str) -> str:
    if not isinstance(s, str): return ""
    s = unicodedata.normalize("NFKC", s)
    out = []
    for ch in s:
        cp = ord(ch)
        if cp in _VS_SET or _is_skin_tone(cp): continue
        out.append(ch)
    return "".join(out).strip()

def _emoji_variants(s: str):
    base = _strip_vs_and_tones(s)
    yield base
    if "\u200D" in base:
        yield base.replace("\u200D", "")

# ========================================
# CICLO DE VIDA DO JOGADOR
# ========================================

async def create_new_player(user_id: Union[int, str], character_name: str) -> dict:
    # (Mantido igual, mas usa import local para evitar ciclo)
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()

    new_player_data = {
        "character_name": character_name,
        "character_name_normalized": _normalize_char_name(character_name), # Importante gravar isso
        "class": None, "level": 1, "xp": 0, "gold": 0,
        "premium_tier": "free", "premium_expires_at": None,
        "base_stats": {"max_hp": 50, "attack": 5, "defense": 3, "initiative": 5, "luck": 5},
        "current_hp": 50, "created_at": now_iso, "last_seen": now_iso,
    }
    await save_player_data(user_id, new_player_data)
    return new_player_data

async def get_or_create_player(user_id: Union[int, str], default_name: str = "Aventureiro") -> dict:
    pdata = await get_player_data(user_id)
    if pdata is None:
        pdata = await create_new_player(user_id, default_name)
    return pdata

async def delete_player(user_id: Union[int, str]) -> bool:
    deleted = False
    str_id = str(user_id)
    if users_collection is not None:
        try:
            if ObjectId.is_valid(str_id):
                res = await asyncio.to_thread(users_collection.delete_one, {"_id": ObjectId(str_id)})
                if res.deleted_count > 0: deleted = True
        except: pass

    if _legacy_db is not None:
        try:
            if str_id.isdigit():
                res = await asyncio.to_thread(_legacy_db.delete_one, {"_id": int(str_id)})
                if res.deleted_count > 0: deleted = True
        except: pass

    await clear_player_cache(user_id)
    return deleted

# ========================================
# FUNÇÕES DE BUSCA (AQUI ESTÁ A CORREÇÃO)
# ========================================

async def find_player_by_name(name: str) -> Optional[Tuple[Union[int, str], dict]]:
    """
    Busca jogador por nome.
    1. Tenta nome normalizado (rápido).
    2. Tenta regex no nome original (fallback para contas antigas/bugadas).
    """
    target_normalized = _normalize_char_name(name)
    if not target_normalized: return None
    
    # --- TENTATIVA 1: Busca Normalizada (Prioridade) ---
    if users_collection is not None:
        doc = await asyncio.to_thread(users_collection.find_one, {"character_name_normalized": target_normalized})
        if doc:
            uid = str(doc['_id'])
            return (uid, await get_player_data(uid))

    if _legacy_db is not None:
        doc = await asyncio.to_thread(_legacy_db.find_one, {"character_name_normalized": target_normalized})
        if doc:
            uid = doc['_id']
            # Verifica se não é um alias migrado
            full = await get_player_data(uid)
            real_id = full.get("user_id") or uid
            return (real_id, full)

    # --- TENTATIVA 2: Fallback Regex (Salva-vidas) ---
    # Procura pelo nome "visual" ignorando maiúsculas/minúsculas
    # Isso resolve se o campo 'character_name_normalized' não existir
    regex_query = {"character_name": {"$regex": f"^{_re.escape(name)}$", "$options": "i"}}
    
    if users_collection is not None:
        doc = await asyncio.to_thread(users_collection.find_one, regex_query)
        if doc:
            uid = str(doc['_id'])
            return (uid, await get_player_data(uid))

    if _legacy_db is not None:
        doc = await asyncio.to_thread(_legacy_db.find_one, regex_query)
        if doc:
            uid = doc['_id']
            full = await get_player_data(uid)
            real_id = full.get("user_id") or uid
            return (real_id, full)

    return None

async def find_players_by_name_partial(query: str) -> list:
    nq = _normalize_char_name(query)
    if not nq: return []
    out = []
    
    # Busca parcial também usa regex
    regex_q = {"$regex": _re.escape(query), "$options": "i"}
    
    # 1. Coleção Nova
    if users_collection is not None:
        # Tenta campo normalizado OU campo visual
        q = {"$or": [{"character_name_normalized": {"$regex": nq, "$options": "i"}},
                     {"character_name": regex_q}]}
        cursor = users_collection.find(q).limit(10)
        for doc in cursor:
            uid = str(doc["_id"])
            p = await get_player_data(uid)
            if p: out.append((uid, p))

    # 2. Coleção Antiga
    if _legacy_db is not None:
        q = {"$or": [{"character_name_normalized": {"$regex": nq, "$options": "i"}},
                     {"character_name": regex_q}]}
        cursor = _legacy_db.find(q).limit(10)
        for doc in cursor:
            uid = doc["_id"]
            p = await get_player_data(uid)
            if p:
                real = str(p.get("user_id") or p.get("_id"))
                if not any(str(x[0]) == real for x in out):
                    out.append((uid, p))
    return out

async def find_by_username(username: str) -> Optional[dict]:
    u = (username or "").lstrip("@").strip().lower()
    if not u: return None
    q = {"$or": [{"username": u}, {"telegram_username": u}, {"tg_username": u}]}
    
    if users_collection:
        doc = await asyncio.to_thread(users_collection.find_one, q)
        if doc: return await get_player_data(str(doc['_id']))
        
    if _legacy_db:
        doc = await asyncio.to_thread(_legacy_db.find_one, q)
        if doc: return await get_player_data(doc['_id'])
            
    return None

# ========================================
# FUNÇÕES DE ITERAÇÃO
# ========================================
def iter_player_ids() -> Iterator[Union[int, str]]:
    if users_collection:
        for d in users_collection.find({}, {"_id": 1}): yield str(d["_id"])
    if _legacy_db:
        for d in _legacy_db.find({}, {"_id": 1}): yield d["_id"]

async def iter_players() -> AsyncIterator[Tuple[Union[int, str], dict]]:
    if users_collection:
        try:
            for d in users_collection.find({}, {"_id": 1}):
                uid = str(d["_id"])
                p = await get_player_data(uid)
                if p: yield uid, p
        except: pass

    if _legacy_db:
        try:
            for d in _legacy_db.find({}, {"_id": 1}):
                uid = d["_id"]
                p = await get_player_data(uid)
                if p:
                    real = p.get("user_id") or p.get("_id")
                    if str(real) != str(uid) and not isinstance(real, int): continue
                    yield uid, p
        except: pass