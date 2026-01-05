# modules/player/core.py
# (VERSÃO CORRIGIDA: Reintroduz 'players_collection' para compatibilidade)

import logging
import asyncio
import certifi
from typing import Optional, Dict, Any, Union
from bson import ObjectId
from pymongo import MongoClient

# Configuração de Logs
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. CONEXÃO MONGODB CENTRALIZADA E BLINDADA
# ==============================================================================
try:
    from config import MONGO_CONNECTION_STRING
except ImportError:
    MONGO_CONNECTION_STRING = "mongodb+srv://eldora-cluster:pb060987@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
logger = logging.getLogger(__name__)

client = None
db = None
players_collection = None # <--- CRÍTICO: Actions.py busca isso
users_collection = None
legacy_collection = None

try:
    client = MongoClient(MONGO_CONNECTION_STRING, tlsCAFile=certifi.where())
    db = client["eldora_db"]
    
    # Definições obrigatórias para compatibilidade
    users_collection = db["users"]     # Novo
    players_collection = db["players"] # Legado (Necessário para actions.py)
    legacy_collection = players_collection # Alias
    
    logger.info("✅ [CORE] MongoDB Conectado.")
except Exception as e:
    logger.critical(f"❌ [CORE] Erro MongoDB: {e}")

# --- 2. SISTEMA DE CACHE ---
_player_cache: Dict[str, Dict[str, Any]] = {}
_player_cache_lock: asyncio.Lock = asyncio.Lock()

def _get_cache_key(user_id: Union[int, str, ObjectId]) -> str:
    """Normaliza o ID para string para usar como chave de cache."""
    return str(user_id)

# ==============================================================================
# FUNÇÕES PRINCIPAIS (CRUD)
# ==============================================================================

async def get_player_data(user_id: Union[int, str, ObjectId]) -> Optional[Dict[str, Any]]:
    if not user_id: return None
    key = _get_cache_key(user_id)
    
    # Cache
    async with _player_cache_lock:
        if key in _player_cache: return dict(_player_cache[key])

    doc = None
    try:
        # Roteamento Inteligente
        if isinstance(user_id, int):
            if players_collection is not None:
                doc = await asyncio.to_thread(players_collection.find_one, {"_id": user_id})
        else:
            # ObjectId ou String numérica
            oid = None
            if isinstance(user_id, ObjectId): oid = user_id
            elif isinstance(user_id, str):
                if ObjectId.is_valid(user_id): oid = ObjectId(user_id)
                elif user_id.isdigit() and players_collection is not None:
                     # Fallback para legado se vier string numérica
                     doc = await asyncio.to_thread(players_collection.find_one, {"_id": int(user_id)})
            
            if oid and users_collection is not None:
                doc = await asyncio.to_thread(users_collection.find_one, {"_id": oid})
                
    except Exception as e:
        logger.error(f"Erro get_player_data {user_id}: {e}")

    if doc:
        async with _player_cache_lock: _player_cache[key] = dict(doc)
        return dict(doc)
    return None

async def save_player_data(user_id: Union[int, str, ObjectId], data: Dict[str, Any]) -> None:
    if not user_id or not data: return
    key = _get_cache_key(user_id)
    
    # Atualiza Cache
    async with _player_cache_lock: _player_cache[key] = dict(data)

    try:
        if isinstance(user_id, int):
            if players_collection is not None:
                await asyncio.to_thread(players_collection.replace_one, {"_id": user_id}, data, upsert=True)
        else:
            oid = None
            if isinstance(user_id, ObjectId): oid = user_id
            elif isinstance(user_id, str):
                if ObjectId.is_valid(user_id): oid = ObjectId(user_id)
                elif user_id.isdigit() and players_collection is not None:
                    await asyncio.to_thread(players_collection.replace_one, {"_id": int(user_id)}, data, upsert=True)
                    return

            if oid and users_collection is not None:
                data["_id"] = oid
                await asyncio.to_thread(users_collection.replace_one, {"_id": oid}, data, upsert=True)
                
    except Exception as e:
        logger.error(f"Erro save_player_data {user_id}: {e}")

async def get_legacy_data_by_telegram_id(tid: int):
    if players_collection is None: return None
    return await asyncio.to_thread(players_collection.find_one, {"_id": tid})

# ==============================================================================
# GERENCIAMENTO DE CACHE
# ==============================================================================

async def clear_player_cache(user_id: Union[int, str, ObjectId]):
    key = _get_cache_key(user_id)
    async with _player_cache_lock:
        if key in _player_cache: del _player_cache[key]

def clear_all_player_cache():
    """Limpa todo o cache."""
    _player_cache.clear()
    logger.info("🧹 Cache de jogadores limpo.")