# modules/player/queries.py
# (VERSÃO FINAL SEGURA: Funções de Gameplay APENAS no Novo Sistema)

from __future__ import annotations
import re as _re
import unicodedata
import logging
import asyncio
from typing import AsyncIterator, Iterator, Tuple, Optional, Union, List
from bson import ObjectId

# Imports do Core
from .core import users_collection, get_player_data, save_player_data, clear_player_cache
# Importamos a função de legado ESPECÍFICA para a migração
from .core import get_legacy_data_by_telegram_id

logger = logging.getLogger(__name__)

# ========================================
# FUNÇÕES AUXILIARES DE NORMALIZAÇÃO
# ========================================

def _normalize_char_name(_s: str) -> str:
    if not isinstance(_s, str):
        return ""
    INVISIBLE_CHARS = r"[\u200B-\u200D\uFEFF]"
    s = _re.sub(INVISIBLE_CHARS, "", _s)
    s = _re.sub(r"[\r\n\t]+", " ", s)
    s = _re.sub(r"\s+", " ", s).strip().lower()
    return s

# ========================================
# CICLO DE VIDA DO JOGADOR
# ========================================

async def create_new_player(user_id: Union[str, ObjectId], character_name: str) -> dict:
    """Cria jogador novo no banco 'users'. user_id DEVE ser ObjectId."""
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()
    
    # Validação e Conversão de ID
    oid = None
    if isinstance(user_id, ObjectId): oid = user_id
    elif isinstance(user_id, str) and ObjectId.is_valid(user_id): oid = ObjectId(user_id)
    
    if not oid:
        raise ValueError("ID inválido para criação de jogador (deve ser ObjectId).")

    new_player_data = {
        "_id": oid,
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
        "inventory": {},
        "equipment": {
            "arma": None, "elmo": None, "armadura": None, "calca": None,
            "luvas": None, "botas": None, "anel": None, "colar": None, "brinco": None
        },
        "current_location": "reino_eldora",
        "player_state": {'action': 'idle'},
        "class_choice_offered": False,
        "base_stats": {"max_hp": 50, "attack": 5, "defense": 3, "initiative": 5, "luck": 5},
        "created_at": now_iso,
        "last_seen": now_iso,
    }
    await save_player_data(oid, new_player_data)
    return new_player_data

async def get_or_create_player(user_id: str, default_name: str = "Aventureiro") -> dict:
    pdata = await get_player_data(user_id)
    if pdata is None:
        pdata = await create_new_player(user_id, default_name)
    return pdata

async def delete_player(user_id: str) -> bool:
    deleted = False
    if users_collection is not None and ObjectId.is_valid(user_id):
        try:
            res = await asyncio.to_thread(users_collection.delete_one, {"_id": ObjectId(user_id)})
            if res.deleted_count > 0: deleted = True
        except Exception as e:
            logger.error(f"Erro ao deletar do Mongo (Users): {e}")

    await clear_player_cache(user_id)
    return deleted

# ========================================
# VERIFICAÇÃO DE MIGRAÇÃO (USADA NO AUTH)
# ========================================

async def check_migration_status(telegram_id: int) -> Tuple[bool, bool, Optional[dict]]:
    """
    Retorna:
    1. has_legacy (bool): Se existe conta antiga na collection 'players'.
    2. already_migrated (bool): Se já existe conta nova vinculada a este Telegram.
    3. legacy_data (dict): Os dados antigos (para exibição/migração).
    """
    # 1. Verifica se já migrou (busca no 'users' pelo telegram_id_owner)
    already_migrated = False
    if users_collection is not None:
        migrated_doc = await asyncio.to_thread(users_collection.find_one, {"telegram_id_owner": telegram_id})
        already_migrated = (migrated_doc is not None)
    
    # 2. Busca dados legados usando a função isolada do core
    legacy_data = await get_legacy_data_by_telegram_id(telegram_id)
        
    has_legacy = (legacy_data is not None)
    
    return has_legacy, already_migrated, legacy_data

# ========================================
# FUNÇÕES DE BUSCA (SOMENTE USERS)
# ========================================

async def find_player_by_name(name: str) -> Optional[Tuple[str, dict]]:
    target_normalized = _normalize_char_name(name)
    if not target_normalized or not users_collection: return None
    
    # 1. Busca Normalizada
    doc = await asyncio.to_thread(users_collection.find_one, {"character_name_normalized": target_normalized})
    if doc:
        uid = str(doc['_id'])
        return (uid, await get_player_data(uid))

    # 2. Fallback Regex
    regex_query = {"character_name": {"$regex": f"^{_re.escape(name)}$", "$options": "i"}}
    doc = await asyncio.to_thread(users_collection.find_one, regex_query)
    if doc:
        uid = str(doc['_id'])
        return (uid, await get_player_data(uid))

    return None

async def find_player_by_name_norm(name: str) -> Optional[Tuple[str, dict]]:
    return await find_player_by_name(name)

async def find_players_by_name_partial(query: str) -> list:
    if not users_collection: return []
    nq = _normalize_char_name(query)
    if not nq: return []
    
    regex_q = {"$regex": _re.escape(query), "$options": "i"}
    q = {"$or": [{"character_name_normalized": {"$regex": nq, "$options": "i"}},
                 {"character_name": regex_q}]}
                 
    out = []
    cursor = users_collection.find(q).limit(10)
    for doc in cursor:
        uid = str(doc["_id"])
        p = await get_player_data(uid)
        if p: out.append((uid, p))
    return out

async def find_by_username(username: str) -> Optional[dict]:
    if not users_collection: return None
    u = (username or "").lstrip("@").strip().lower()
    if not u: return None
    
    q = {"$or": [{"username": u}, {"telegram_username": u}, {"tg_username": u}]}
    doc = await asyncio.to_thread(users_collection.find_one, q)
    if doc: return await get_player_data(str(doc['_id']))
    return None

# ========================================
# FUNÇÕES DE ITERAÇÃO
# ========================================

def iter_player_ids() -> Iterator[str]:
    if users_collection:
        for d in users_collection.find({}, {"_id": 1}): 
            yield str(d["_id"])

async def iter_players():
    if users_collection:
        async for doc in users_collection.find({}):
            uid = str(doc["_id"])
            yield uid, doc