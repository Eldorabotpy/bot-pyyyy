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

# ========================================
# FUNÇÕES AUXILIARES
# ========================================

def _normalize_char_name(_s: str) -> str:
    if not isinstance(_s, str): return ""
    # Remove caracteres invisíveis e espaços extras
    s = _re.sub(r"[\u200B-\u200D\uFEFF]", "", _s)
    s = _re.sub(r"\s+", " ", s).strip().lower()
    return s

# ========================================
# FUNÇÕES DE BUSCA (A LÓGICA QUE VOCÊ PEDIU)
# ========================================

async def find_player_by_name(name: str) -> Optional[Tuple[str, dict]]:
    """
    Estratégia de Busca:
    1. Nome do Personagem (Exato/Normalizado)
    2. Username do Telegram (com ou sem @)
    3. Nome do Personagem (Parcial/Regex)
    """
    if not users_collection or not name: return None
    
    # Prepara o texto
    raw_text = name.strip()
    norm_text = _normalize_char_name(raw_text)
    user_text = raw_text.lstrip("@").lower() # Remove @ para buscar username

    # --- 1. TENTATIVA: NOME DO PERSONAGEM (Exato) ---
    if norm_text:
        doc = await asyncio.to_thread(users_collection.find_one, {"character_name_normalized": norm_text})
        if doc:
            return (str(doc['_id']), await get_player_data(str(doc['_id'])))

    # --- 2. TENTATIVA: USERNAME DO TELEGRAM ---
    # Procura nos campos onde o username costuma ser salvo
    query_user = {
        "$or": [
            {"username": user_text},           # Padrão novo
            {"telegram_username": user_text},  # Padrão legado
            {"tg_username": user_text}         # Variação
        ]
    }
    doc = await asyncio.to_thread(users_collection.find_one, query_user)
    if doc:
        return (str(doc['_id']), await get_player_data(str(doc['_id'])))

    # --- 3. TENTATIVA: NOME PARCIAL (Regex) ---
    # Se digitou "Bastos", acha "O Grande Bastos"
    try:
        regex_query = {"character_name": {"$regex": _re.escape(raw_text), "$options": "i"}}
        doc = await asyncio.to_thread(users_collection.find_one, regex_query)
        if doc:
            return (str(doc['_id']), await get_player_data(str(doc['_id'])))
    except: pass

    return None

# Manteve-se as outras funções essenciais para o funcionamento do bot, 
# mas redirecionando a busca principal para a lógica acima.

async def find_player_by_name_norm(name: str) -> Optional[Tuple[str, dict]]:
    return await find_player_by_name(name)

async def find_players_by_name_partial(query: str) -> list:
    if not users_collection: return []
    nq = _normalize_char_name(query)
    if not nq: return []
    
    q = {"character_name_normalized": {"$regex": nq, "$options": "i"}}
    out = []
    # Limita a 10 resultados para não pesar
    cursor = users_collection.find(q).limit(10)
    for doc in cursor:
        uid = str(doc["_id"])
        p = await get_player_data(uid)
        if p: out.append((uid, p))
    return out

# --- Mantendo funções de CRUD para não quebrar imports ---
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
    if users_collection and ObjectId.is_valid(user_id):
        await asyncio.to_thread(users_collection.delete_one, {"_id": ObjectId(user_id)})
    await clear_player_cache(user_id)
    return True

async def find_by_username(username: str) -> Optional[dict]:
    # Alias para compatibilidade
    res = await find_player_by_name(username)
    return res[1] if res else None

# Iteradores
def iter_player_ids() -> Iterator[str]:
    if users_collection:
        for d in users_collection.find({}, {"_id": 1}): yield str(d["_id"])

async def iter_players():
    if users_collection:
        async for doc in users_collection.find({}): yield str(doc["_id"]), doc

async def check_migration_status(telegram_id: int) -> Tuple[bool, bool, Optional[dict]]:
    already_migrated = False
    if users_collection:
        doc = await asyncio.to_thread(users_collection.find_one, {"telegram_id_owner": telegram_id})
        already_migrated = (doc is not None)
    legacy = await get_legacy_data_by_telegram_id(telegram_id)
    return (legacy is not None), already_migrated, legacy