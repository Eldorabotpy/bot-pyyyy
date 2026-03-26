# modules/player/core.py
# (VERSÃO CORRIGIDA: Reintroduz suporte a Legado para Migração + Cache com TTL)

import logging
import asyncio
import certifi
import time
from typing import Optional, Dict, Any, Union
from bson import ObjectId
from pymongo import MongoClient

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. CONEXÃO MONGODB
# ==============================================================================
MONGO_STR = "mongodb+srv://eldora-cluster:pb060987@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
users_collection = None    # Novo (ObjectId)
players_collection = None  # Antigo (Int ID) - Apenas para Migração

try:
    client = MongoClient(MONGO_STR, tlsCAFile=certifi.where())
    db = client["eldora_db"]
    
    users_collection = db["users"]
    players_collection = db["players"] # Recuperado para consultas de migração
    
    logger.info("✅ [CORE] Conexão MongoDB: SUCESSO (Users + Players Legacy).")
except Exception as e:
    logger.critical(f"❌ [CORE] FALHA CRÍTICA MONGODB: {e}")

# --- 2. SISTEMA DE CACHE ---
_player_cache: Dict[str, Dict[str, Any]] = {}
_player_cache_time: Dict[str, float] = {} # <--- NOVO: Guarda a hora exata do último cache
_player_cache_lock: asyncio.Lock = asyncio.Lock()

CACHE_TTL = 30 # <--- O bot vai buscar dados frescos do Web App a cada 30 segundos

def _get_cache_key(user_id: Union[str, ObjectId]) -> str:
    return str(user_id)

# ==============================================================================
# CRUD (USERS - STRICT OBJECTID)
# ==============================================================================

async def get_player_data(user_id: Union[str, ObjectId]) -> Optional[Dict[str, Any]]:
    """
    Busca dados EXCLUSIVAMENTE na coleção 'users'.
    Retorna None se user_id for int ou inválido.
    """
    if not user_id: return None
    
    # 🚫 Fim do Legado: Rejeita Inteiros para gameplay
    if isinstance(user_id, int):
        return None

    cache_key = _get_cache_key(user_id)
    
    # 1. Cache
    async with _player_cache_lock:
        if cache_key in _player_cache:
            last_saved = _player_cache_time.get(cache_key, 0)
            if time.time() - last_saved < CACHE_TTL:
                return dict(_player_cache[cache_key]) # Cache ainda tá fresco, usa ele!
            else:
                del _player_cache[cache_key]
                if cache_key in _player_cache_time:
                    del _player_cache_time[cache_key]

    # 2. Banco (Users Collection)
    doc = None
    try:
        if users_collection is not None:
            oid = None
            if isinstance(user_id, ObjectId):
                oid = user_id
            elif isinstance(user_id, str) and ObjectId.is_valid(user_id):
                oid = ObjectId(user_id)
            
            if oid:
                doc = await asyncio.to_thread(users_collection.find_one, {"_id": oid})
                
    except Exception as e:
        logger.error(f"Erro ao buscar player_data para {user_id}: {e}")
        return None

    # 3. Salva no cache
    if doc:
        async with _player_cache_lock:
            _player_cache[cache_key] = dict(doc)
            _player_cache_time[cache_key] = time.time() # <--- CORREÇÃO: Registra o tempo do cache
        return dict(doc)
        
    return None

async def save_player_data(user_id: Union[str, ObjectId], data: Dict[str, Any]) -> None:
    """
    Salva dados EXCLUSIVAMENTE via ObjectId na coleção 'users'.
    """
    if not user_id or not data: return
    
    # 🚫 Fim do Legado
    if isinstance(user_id, int): return 
    
    cache_key = _get_cache_key(user_id)
    
    # 1. Atualiza Cache
    async with _player_cache_lock:
        _player_cache[cache_key] = dict(data)
        _player_cache_time[cache_key] = time.time() # <--- CORREÇÃO: Renova o tempo de vida do cache

    # 2. Persiste no Banco
    try:
        if users_collection is not None:
            oid = None
            if isinstance(user_id, ObjectId):
                oid = user_id
            elif isinstance(user_id, str) and ObjectId.is_valid(user_id):
                oid = ObjectId(user_id)

            if oid:
                # Garante integridade do _id no documento
                data["_id"] = oid
                await asyncio.to_thread(
                    users_collection.replace_one, 
                    {"_id": oid}, 
                    data, 
                    upsert=True
                )
    except Exception as e:
        logger.error(f"Erro ao salvar player {user_id}: {e}")

# ==============================================================================
# 3. LEGADO / MIGRAÇÃO (A FUNÇÃO QUE FALTAVA)
# ==============================================================================

async def get_legacy_data_by_telegram_id(telegram_id: int) -> Optional[Dict[str, Any]]:
    """
    Busca dados na coleção antiga 'players'.
    Usado APENAS pelo check_migration_status no queries.py.
    """
    if players_collection is None:
        return None
    try:
        # A coleção antiga usava _id = Inteiro (Telegram ID)
        doc = await asyncio.to_thread(players_collection.find_one, {"_id": int(telegram_id)})
        return dict(doc) if doc else None
    except Exception as e:
        logger.error(f"Erro busca legado {telegram_id}: {e}")
        return None

# ==============================================================================
# CACHE UTILS
# ==============================================================================

async def clear_player_cache(user_id: Union[str, ObjectId]):
    cache_key = _get_cache_key(user_id)
    async with _player_cache_lock:
        if cache_key in _player_cache:
            del _player_cache[cache_key]
        if cache_key in _player_cache_time: # <--- Adicionado limpeza de tempo
            del _player_cache_time[cache_key]

def clear_all_player_cache():
    _player_cache.clear()
    _player_cache_time.clear() # <--- Adicionado limpeza de tempo global
    logger.info("🧹 Cache de jogadores limpo.")