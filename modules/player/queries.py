# modules/player/queries.py
# (VERSÃO CORRIGIDA: Reintroduz get_or_create_player e corrige imports)

from __future__ import annotations
import re as _re
import unicodedata
import logging
import asyncio
from typing import AsyncIterator, Iterator, Tuple, Optional, Union, List
from bson import ObjectId

# Imports do Core Sanitizado
from .core import (
    users_collection, 
    get_player_data, 
    save_player_data, 
    clear_player_cache, 
    get_legacy_data_by_telegram_id
)

# Tenta importar utcnow, fallback para datetime
try:
    from .actions import utcnow
except ImportError:
    from datetime import datetime, timezone
    def utcnow(): return datetime.now(timezone.utc)

logger = logging.getLogger(__name__)

# ========================================
# FUNÇÕES AUXILIARES
# ========================================

def _normalize_char_name(_s: str) -> str:
    if not isinstance(_s, str): return ""
    INVISIBLE_CHARS = r"[\u200B-\u200D\uFEFF]"
    s = _re.sub(INVISIBLE_CHARS, "", _s)
    s = _re.sub(r"[\r\n\t]+", " ", s)
    s = _re.sub(r"\s+", " ", s).strip().lower()
    return s

_VS_SET = {0xFE0E, 0xFE0F}
def _is_skin_tone(cp: int) -> bool: return 0x1F3FB <= cp <= 0x1F3FF

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
    if "\u200D" in base: yield base.replace("\u200D", "")

# ========================================
# CICLO DE VIDA DO JOGADOR
# ========================================

async def create_new_player(user_id: Union[str, ObjectId], character_name: str, telegram_owner_id: int = None) -> dict:
    """Cria um jogador na collection 'users'."""
    now_iso = utcnow().isoformat()
    new_player_data = {
        "character_name": character_name,
        "character_name_normalized": _normalize_char_name(character_name),
        "telegram_id_owner": telegram_owner_id,
        "class": None,
        "level": 1, "xp": 0,
        "max_hp": 50, "current_hp": 50,
        "attack": 5, "defense": 3, "initiative": 5, "luck": 5,
        "stat_points": 0,
        "energy": 20, "max_energy": 20, "energy_last_ts": now_iso,
        "gold": 0, "gems": 0, 
        "premium_tier": "free", "premium_expires_at": None,
        "party_id": None,
        "inventory": {}, "equipment": {},
        "current_location": "reino_eldora",
        "player_state": {'action': 'idle'},
        "base_stats": {"max_hp": 50, "attack": 5, "defense": 3, "initiative": 5, "luck": 5},
        "created_at": now_iso, "last_seen": now_iso,
    }
    await save_player_data(user_id, new_player_data)
    return new_player_data

# [CORREÇÃO] Esta função foi re-adicionada para compatibilidade
async def get_or_create_player(user_id: Union[str, ObjectId], default_name: str = "Aventureiro") -> dict:
    pdata = await get_player_data(user_id)
    if pdata: return pdata
    # Se for ID numérico (legado), não cria automatico, retorna None para forçar Auth
    if isinstance(user_id, int): return None
    return await create_new_player(user_id, default_name)

async def delete_player(user_id):
    if users_collection:
        try: await asyncio.to_thread(users_collection.delete_one, {"_id": ObjectId(str(user_id))})
        except: pass
    await clear_player_cache(user_id)
    return True

# ========================================
# VERIFICAÇÃO DE MIGRAÇÃO
# ========================================

async def check_migration_status(tid: int):
    migrated = await asyncio.to_thread(users_collection.find_one, {"telegram_id_owner": tid}) if users_collection else None
    legacy = await get_legacy_data_by_telegram_id(tid)
    return (legacy is not None), (migrated is not None), legacy
# ========================================
# BUSCAS (APENAS USERS)
# ========================================

async def find_player_by_name(name: str):
    target = _normalize_char_name(name)
    if users_collection:
        doc = await asyncio.to_thread(users_collection.find_one, {"character_name_normalized": target})
        if doc: return (str(doc['_id']), await get_player_data(str(doc['_id'])))
    return None

async def find_player_by_name_norm(name: str) -> Optional[Tuple[str, dict]]:
    """Alias para compatibilidade."""
    return await find_player_by_name(name)

async def find_players_by_name_partial(query: str) -> list:
    nq = _normalize_char_name(query)
    if not nq or users_collection is None: return []
    out = []
    cursor = users_collection.find({"character_name_normalized": {"$regex": nq, "$options": "i"}})
    for doc in cursor:
        uid = str(doc["_id"])
        full_data = await get_player_data(uid)
        if full_data: out.append((uid, full_data))
    return out

async def find_by_username(username: str) -> Optional[dict]:
    u = (username or "").lstrip("@").strip().lower()
    if not u or users_collection is None: return None
    doc = await asyncio.to_thread(users_collection.find_one, {"username": u})
    if doc: return await get_player_data(str(doc['_id']))
    return None

# ========================================
# ITERADORES
# ========================================

def iter_player_ids():
    if users_collection:
        for doc in users_collection.find({}, {"_id": 1}): yield str(doc["_id"])
        

async def iter_players() -> AsyncIterator[Tuple[str, dict]]:
    if users_collection is not None:
        try:
            cursor = users_collection.find({}, {"_id": 1})
            for doc in cursor:
                uid = str(doc["_id"])
                pdata = await get_player_data(uid)
                if pdata: yield uid, pdata
        except Exception as e: logger.error(f"Erro iter_players: {e}")
