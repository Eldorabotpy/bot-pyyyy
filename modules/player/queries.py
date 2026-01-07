# modules/player/queries.py
# (VERSÃO BLINDADA)

from __future__ import annotations
import re as _re
import logging
import asyncio
from typing import Iterator, Tuple, Optional, Union
from bson import ObjectId

# Imports do Core
from .core import users_collection, get_player_data, save_player_data, clear_player_cache
from .core import get_legacy_data_by_telegram_id

logger = logging.getLogger(__name__)

def _normalize_char_name(_s: str) -> str:
    if not isinstance(_s, str): return ""
    s = _re.sub(r"[\u200B-\u200D\uFEFF]", "", _s)
    s = _re.sub(r"\s+", " ", s).strip().lower()
    return s

async def find_player_by_name(name: str) -> Optional[Tuple[str, dict]]:
    if users_collection is None or not name: 
        return None
    
    raw_text = name.strip()
    norm_text = _normalize_char_name(raw_text)
    user_text = raw_text.lstrip("@").lower()

    # 1. TENTATIVA: NOME DO PERSONAGEM (Exato/Normalizado)
    if norm_text:
        doc = await asyncio.to_thread(users_collection.find_one, {"character_name_normalized": norm_text})
        if doc:
            return (str(doc['_id']), await get_player_data(str(doc['_id'])))

    # 2. TENTATIVA: USERNAME DO TELEGRAM (Exato)
    query_user = {
        "$or": [
            {"username": {"$regex": f"^{_re.escape(user_text)}$", "$options": "i"}},
            {"telegram_username": {"$regex": f"^{_re.escape(user_text)}$", "$options": "i"}},
            {"tg_username": {"$regex": f"^{_re.escape(user_text)}$", "$options": "i"}}
        ]
    }
    doc = await asyncio.to_thread(users_collection.find_one, query_user)
    if doc:
        return (str(doc['_id']), await get_player_data(str(doc['_id'])))

    # 3. TENTATIVA: BUSCA PARCIAL
    try:
        regex_pattern = _re.escape(raw_text)
        aggressive_query = {
            "$or": [
                {"character_name": {"$regex": regex_pattern, "$options": "i"}},
                {"username": {"$regex": regex_pattern, "$options": "i"}},
                {"character_name_normalized": {"$regex": _normalize_char_name(raw_text), "$options": "i"}}
            ]
        }
        doc = await asyncio.to_thread(users_collection.find_one, aggressive_query)
        if doc:
            return (str(doc['_id']), await get_player_data(str(doc['_id'])))
    except: pass

    return None

async def find_player_by_name_norm(name: str) -> Optional[Tuple[str, dict]]:
    return await find_player_by_name(name)

async def find_players_by_name_partial(query: str) -> list:
    if users_collection is None: return []
    nq = _normalize_char_name(query)
    if not nq: return []
    
    q = {"character_name": {"$regex": _re.escape(query), "$options": "i"}}
    out = []
    cursor = users_collection.find(q).limit(10)
    for doc in cursor:
        uid = str(doc["_id"])
        p = await get_player_data(uid)
        if p: out.append((uid, p))
    return out

async def create_new_player(user_id: Union[str, ObjectId], character_name: str) -> dict:
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()
    oid = ObjectId(user_id) if isinstance(user_id, str) else user_id
    new_player_data = {
        "_id": oid,
        "character_name": character_name,
        "character_name_normalized": _normalize_char_name(character_name),
        "level": 1, "xp": 0, "gold": 0, "gems": 0,
        "premium_tier": "free", "premium_expires_at": None,
        "created_at": now_iso
    }
    await save_player_data(oid, new_player_data)
    return new_player_data

async def get_or_create_player(user_id: str, default_name: str = "Aventureiro") -> dict:
    pdata = await get_player_data(user_id)
    if not pdata: pdata = await create_new_player(user_id, default_name)
    return pdata

async def delete_player(user_id: str) -> bool:
    if users_collection is not None and ObjectId.is_valid(user_id):
        await asyncio.to_thread(users_collection.delete_one, {"_id": ObjectId(user_id)})
    await clear_player_cache(user_id)
    return True

async def find_by_username(username: str) -> Optional[dict]:
    if users_collection is None: return None
    u = (username or "").lstrip("@").strip().lower()
    if not u: return None
    q = {"$or": [{"username": u}, {"telegram_username": u}, {"tg_username": u}]}
    doc = await asyncio.to_thread(users_collection.find_one, q)
    if doc: return await get_player_data(str(doc['_id']))
    return None

def iter_player_ids() -> Iterator[str]:
    if users_collection is not None:
        for d in users_collection.find({}, {"_id": 1}): yield str(d["_id"])

async def iter_players():
    if users_collection is not None:
        async for doc in users_collection.find({}): yield str(doc["_id"]), doc

async def check_migration_status(telegram_id: int) -> Tuple[bool, bool, Optional[dict]]:
    already_migrated = False
    if users_collection is not None:
        doc = await asyncio.to_thread(users_collection.find_one, {"telegram_id_owner": telegram_id})
        already_migrated = (doc is not None)
    legacy = await get_legacy_data_by_telegram_id(telegram_id)
    return (legacy is not None), already_migrated, legacy