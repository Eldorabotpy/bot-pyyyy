# modules/player/queries.py
# (VERSÃO BLINDADA: Compatível com PyMongo Síncrono e Asyncio)

from __future__ import annotations
import re as _re
import logging
import asyncio
from typing import Iterator, Tuple, Optional, Union, Dict, Any, List
from bson import ObjectId
from datetime import datetime, timezone

# Imports do Core (Garante que usamos a conexão centralizada)
from .core import users_collection, get_player_data, save_player_data, clear_player_cache
from .core import get_legacy_data_by_telegram_id

logger = logging.getLogger(__name__)

# ==============================================================================
# HELPERS
# ==============================================================================
def _normalize_char_name(_s: str) -> str:
    """Remove caracteres especiais invisíveis e normaliza espaços."""
    if not isinstance(_s, str): return ""
    # Remove caracteres de formatação invisíveis
    s = _re.sub(r"[\u200B-\u200D\uFEFF]", "", _s)
    # Remove emojis e espaços extras
    s = _re.sub(r"\s+", " ", s).strip().lower()
    return s

# ==============================================================================
# BUSCAS (FINDERS)
# ==============================================================================

async def find_player_by_name(name: str) -> Optional[Tuple[str, dict]]:
    """
    Busca um jogador pelo nome do personagem (prioridade) ou username.
    Retorna: (user_id_str, player_data_dict) ou None
    """
    if users_collection is None or not name: 
        return None
    
    raw_text = name.strip()
    norm_text = _normalize_char_name(raw_text)
    user_text = raw_text.lstrip("@").lower()

    # 1. TENTATIVA: NOME DO PERSONAGEM (Exato/Normalizado)
    # Busca por 'name_normalized' ou 'character_name_normalized' (compatibilidade)
    if norm_text:
        query_norm = {
            "$or": [
                {"name_normalized": norm_text},
                {"character_name_normalized": norm_text},
                {"character_name": {"$regex": f"^{_re.escape(raw_text)}$", "$options": "i"}}
            ]
        }
        # Executa em thread separada para não bloquear o loop
        doc = await asyncio.to_thread(users_collection.find_one, query_norm)
        if doc:
            return (str(doc['_id']), await get_player_data(str(doc['_id'])))

    # 2. TENTATIVA: USERNAME DO TELEGRAM (Exato)
    # Regex case-insensitive para username
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

    # 3. TENTATIVA: BUSCA PARCIAL (Agressiva - Último Recurso)
    try:
        regex_pattern = _re.escape(raw_text)
        aggressive_query = {
            "$or": [
                {"name": {"$regex": regex_pattern, "$options": "i"}},
                {"character_name": {"$regex": regex_pattern, "$options": "i"}},
                {"username": {"$regex": regex_pattern, "$options": "i"}},
                {"name_normalized": {"$regex": norm_text, "$options": "i"}}
            ]
        }
        doc = await asyncio.to_thread(users_collection.find_one, aggressive_query)
        if doc:
            return (str(doc['_id']), await get_player_data(str(doc['_id'])))
    except: pass

    return None

async def find_player_by_name_norm(name: str) -> Optional[dict]:
    """Alias para compatibilidade com partes antigas do sistema."""
    res = await find_player_by_name(name)
    if res:
        return res[1]
    return None

async def find_players_by_name_partial(query: str) -> List[Tuple[str, dict]]:
    """Retorna lista de jogadores que dão match parcial no nome (para auto-complete)."""
    if users_collection is None: return []
    nq = _normalize_char_name(query)
    if not nq: return []
    
    q = {
        "$or": [
            {"name": {"$regex": _re.escape(query), "$options": "i"}},
            {"character_name": {"$regex": _re.escape(query), "$options": "i"}}
        ]
    }
    out = []
    
    def _run_query():
        # Limita a 10 resultados para não pesar
        return list(users_collection.find(q).limit(10))
    
    docs = await asyncio.to_thread(_run_query)
    
    for doc in docs:
        uid = str(doc["_id"])
        # Usa get_player_data para garantir cache e dados atualizados
        p = await get_player_data(uid)
        if p: out.append((uid, p))
    return out

async def find_by_username(username: str) -> Optional[dict]:
    """Busca rápida específica por username."""
    if users_collection is None: return None
    u = (username or "").lstrip("@").strip().lower()
    if not u: return None
    
    q = {"$or": [{"username": u}, {"telegram_username": u}, {"tg_username": u}]}
    doc = await asyncio.to_thread(users_collection.find_one, q)
    
    if doc: 
        return await get_player_data(str(doc['_id']))
    return None

# ==============================================================================
# CRUD
# ==============================================================================

async def create_new_player(user_id: Union[str, ObjectId], character_name: str, username: str = None) -> dict:
    """
    Cria um novo jogador no banco de dados.
    Garante a estrutura inicial correta e uso de ObjectId.
    """
    # Garante que user_id seja ObjectId se possível
    oid = ObjectId(user_id) if isinstance(user_id, str) and ObjectId.is_valid(user_id) else user_id
    
    now_iso = datetime.now(timezone.utc).isoformat()
    norm = _normalize_char_name(character_name)

    new_player_data = {
        "_id": oid,
        "name": character_name,             # Padrão novo
        "character_name": character_name,   # Compatibilidade
        "name_normalized": norm,
        "character_name_normalized": norm,
        "username": username,
        "level": 1, 
        "xp": 0, 
        "gold": 0, 
        "gems": 0,
        "premium_tier": "free", 
        "premium_expires_at": None,
        "created_at": now_iso,
        # Status Iniciais Balanceados
        "stats": {"hp": 50, "attack": 5, "defense": 3, "initiative": 5, "luck": 5},
        "base_stats": {"max_hp": 50, "attack": 5, "defense": 3, "initiative": 5, "luck": 5},
        "current_hp": 50,
        "energy": 20,
        "max_energy": 20,
        "inventory": {},
        "equipment": {}
    }
    
    # Salva usando a função do core para garantir cache e persistência
    await save_player_data(oid, new_player_data)
        
    return new_player_data

async def get_or_create_player(user_id: str, default_name: str = "Aventureiro") -> dict:
    """Tenta buscar; se não existir, cria."""
    pdata = await get_player_data(user_id)
    if not pdata: 
        pdata = await create_new_player(user_id, default_name)
    return pdata

async def delete_player(user_id: str) -> bool:
    """Remove permanentemente um jogador."""
    if users_collection is not None:
        try:
            oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
            await asyncio.to_thread(users_collection.delete_one, {"_id": oid})
        except: 
            pass 
            
    await clear_player_cache(user_id)
    return True

# ==============================================================================
# ITERADORES (CORRIGIDO)
# ==============================================================================

def iter_player_ids() -> Iterator[str]:
    """
    Iterador síncrono apenas de IDs.
    Usado por handlers/jobs.py e scripts de manutenção.
    Retorna IDs como string.
    """
    if users_collection is None:
        return iter([])

    try:
        # Retorna apenas o campo _id para ser rápido e leve
        cursor = users_collection.find({}, {"_id": 1})
        for d in cursor:
            yield str(d["_id"])
    except Exception as e:
        logger.error(f"Erro em iter_player_ids: {e}")
        return iter([])

async def iter_players():
    """
    Itera sobre todos os jogadores de forma segura para PyMongo + Asyncio.
    IMPORTANTE: Não usar 'async for' direto no cursor do pymongo sem motor async (Motor).
    Aqui usamos yield manual com sleep para não bloquear o loop.
    """
    if users_collection is not None:
        try:
            # Pega o cursor síncrono
            cursor = users_collection.find({})
            
            # Itera sincronamente, mas cede o controle ao event loop a cada passo
            for doc in cursor:
                yield str(doc["_id"]), doc
                # Isso impede que o bot trave enquanto processa milhares de jogadores
                await asyncio.sleep(0)
        except Exception as e:
            logger.error(f"Erro em iter_players: {e}")

# ==============================================================================
# MIGRAÇÃO
# ==============================================================================

async def check_migration_status(telegram_id: int) -> Tuple[bool, bool, Optional[dict]]:
    """
    Verifica se o usuário tem dados no banco antigo e se já migrou para o novo.
    Retorna: (has_legacy_data, already_migrated, legacy_data)
    """
    already_migrated = False
    legacy_data = None
    
    # 1. Verifica se já existe um usuário linkado a este Telegram ID na collection nova
    if users_collection is not None:
        try:
            # Procura por telegram_id ou owner_id na coleção nova
            q = {"$or": [{"telegram_id": telegram_id}, {"telegram_owner_id": telegram_id}]}
            doc = await asyncio.to_thread(users_collection.find_one, q)
            already_migrated = (doc is not None)
        except Exception as e:
            logger.error(f"Erro ao checar status de migração (novo): {e}")
    
    # 2. Busca dados no banco legado (players_collection) se ainda não migrou
    if not already_migrated:
        legacy_data = await get_legacy_data_by_telegram_id(telegram_id)
    
    return (legacy_data is not None), already_migrated, legacy_data