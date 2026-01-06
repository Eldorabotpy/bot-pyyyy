# modules/player/queries.py
# (VERSÃO FINAL MASTER: Contém TODAS as funções necessárias)

from __future__ import annotations
import re as _re
import unicodedata
import logging
import asyncio
from typing import AsyncIterator, Iterator, Tuple, Optional, Union, List
from bson import ObjectId

# Imports do Core
from .core import players_collection, get_player_data, save_player_data, clear_player_cache, users_collection

# [TRUQUE DE AUDITORIA & SEGURANÇA]
# Alias para acessar o banco legado.
_legacy_db = players_collection

logger = logging.getLogger(__name__)

# ========================================
# FUNÇÕES AUXILIARES DE NORMALIZAÇÃO
# ========================================

def _get_users_collection():
    """Retorna a coleção de usuários novos."""
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
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKC", s)
    out = []
    for ch in s:
        cp = ord(ch)
        if cp in _VS_SET or _is_skin_tone(cp):
            continue
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
    from datetime import datetime, timezone
    
    now_iso = datetime.now(timezone.utc).isoformat()

    new_player_data = {
        "character_name": character_name,
        "character_name_normalized": _normalize_char_name(character_name),
        "class": None,
        "level": 1,
        "xp": 0,
        "max_hp": 50,
        "current_hp": 50,
        "attack": 5,
        "defense": 3,
        "initiative": 5,
        "luck": 5,
        "stat_points": 0,
        "energy": 20,
        "max_energy": 20,
        "energy_last_ts": now_iso,
        "gold": 0,
        "gems": 0, 
        "premium_tier": "free",
        "premium_expires_at": None,
        "party_id": None,
        "profession": {},
        "inventory": {},
        "equipment": {
            "arma": None, "elmo": None, "armadura": None, "calca": None,
            "luvas": None, "botas": None, "anel": None, "colar": None, "brinco": None
        },
        "current_location": "reino_eldora",
        "last_travel_time": None,
        "player_state": {'action': 'idle'},
        "last_chat_id": None,
        "class_choice_offered": False,
        "base_stats": {"max_hp": 50, "attack": 5, "defense": 3, "initiative": 5, "luck": 5},
        "created_at": now_iso,
        "last_seen": now_iso,
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

    # 1. Remove do Banco Novo
    if users_collection is not None:
        try:
            if ObjectId.is_valid(str_id):
                res = await asyncio.to_thread(users_collection.delete_one, {"_id": ObjectId(str_id)})
                if res.deleted_count > 0: deleted = True
        except Exception as e:
            logger.error(f"Erro ao deletar do Mongo (Users): {e}")

    # 2. Remove do Banco Antigo
    if _legacy_db is not None:
        try:
            if str_id.isdigit():
                iid = int(str_id)
                res = await asyncio.to_thread(_legacy_db.delete_one, {"_id": iid})
                if res.deleted_count > 0: deleted = True
        except: pass

    await clear_player_cache(user_id)
    return deleted

# ========================================
# VERIFICAÇÃO DE MIGRAÇÃO (A FUNÇÃO QUE FALTAVA)
# ========================================

async def check_migration_status(telegram_id: int) -> Tuple[bool, bool, Optional[dict]]:
    """
    Retorna:
    1. has_legacy (bool): Se existe conta antiga na collection 'players'.
    2. already_migrated (bool): Se já existe conta nova vinculada a este Telegram.
    3. legacy_data (dict): Os dados antigos.
    """
    # 1. Verifica se já migrou (busca no 'users' pelo telegram_id_owner)
    already_migrated = False
    if users_collection is not None:
        migrated_doc = await asyncio.to_thread(users_collection.find_one, {"telegram_id_owner": telegram_id})
        already_migrated = (migrated_doc is not None)
    
    # 2. Busca dados legados
    legacy_data = None
    if _legacy_db is not None:
        legacy_data = await asyncio.to_thread(_legacy_db.find_one, {"_id": telegram_id})
        
    has_legacy = (legacy_data is not None)
    
    return has_legacy, already_migrated, legacy_data

# ========================================
# FUNÇÕES DE BUSCA
# ========================================

async def find_player_by_name(name: str) -> Optional[Tuple[Union[int, str], dict]]:
    """
    Busca jogador por nome (Smart Search).
    """
    target_normalized = _normalize_char_name(name)
    if not target_normalized: return None
    
    # 1. Busca Normalizada (Prioridade)
    if users_collection is not None:
        doc = await asyncio.to_thread(users_collection.find_one, {"character_name_normalized": target_normalized})
        if doc:
            uid = str(doc['_id'])
            return (uid, await get_player_data(uid))

    if _legacy_db is not None:
        doc = await asyncio.to_thread(_legacy_db.find_one, {"character_name_normalized": target_normalized})
        if doc:
            uid = doc['_id']
            full = await get_player_data(uid)
            real_id = full.get("user_id") or uid
            return (real_id, full)

    # 2. Fallback Regex
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

# Alias necessário para player_manager.py
async def find_player_by_name_norm(name: str) -> Optional[Tuple[Union[int, str], dict]]:
    return await find_player_by_name(name)

async def find_players_by_name_partial(query: str) -> list:
    nq = _normalize_char_name(query)
    if not nq: return []
    out = []
    
    regex_q = {"$regex": _re.escape(query), "$options": "i"}
    
    if users_collection is not None:
        q = {"$or": [{"character_name_normalized": {"$regex": nq, "$options": "i"}},
                     {"character_name": regex_q}]}
        cursor = users_collection.find(q).limit(10)
        for doc in cursor:
            uid = str(doc["_id"])
            p = await get_player_data(uid)
            if p: out.append((uid, p))

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

async def iter_players():
    from .core import users_collection 

    if users_collection is not None:
        async for doc in users_collection.find({}):
            user_id = doc.get("user_id")
            if user_id:
                yield user_id, doc
    else:
        pass

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
        