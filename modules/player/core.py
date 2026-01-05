# modules/player/core.py
# (VERSÃO FINAL: Com a função de legado necessária para o Auth)

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
MONGO_STR = "mongodb+srv://eldora-cluster:pb060987@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
players_collection = None
users_collection = None

try:
    # Tenta conectar DIRETAMENTE
    client = MongoClient(MONGO_STR, tlsCAFile=certifi.where())
    db = client["eldora_db"]
    
    players_collection = db["players"] # Legado
    users_collection = db["users"]     # Novo Sistema
    
    logger.info("✅ [CORE] Conexão MongoDB Direta: SUCESSO.")
except Exception as e:
    logger.critical(f"❌ [CORE] FALHA CRÍTICA AO CONECTAR MONGODB: {e}")

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
    """
    Busca dados do jogador.
    - Se for Int: Busca na coleção 'players' (Legado).
    - Se for ObjectId/Str(24): Busca na coleção 'users' (Novo).
    """
    if not user_id: return None
    
    cache_key = _get_cache_key(user_id)
    
    # 1. Tenta buscar no Cache primeiro
    async with _player_cache_lock:
        if cache_key in _player_cache:
            return dict(_player_cache[cache_key])

    # 2. Se não está no cache, busca no Banco
    doc = None
    try:
        # --- ROTEAMENTO HÍBRIDO ---
        if isinstance(user_id, int):
            # CASO 1: ID Numérico -> Coleção Legada 'players'
            if players_collection is not None:
                doc = await asyncio.to_thread(players_collection.find_one, {"_id": user_id})
        
        else:
            # CASO 2: ID Novo (ObjectId ou String) -> Coleção Nova 'users'
            oid = None
            if isinstance(user_id, ObjectId):
                oid = user_id
            elif isinstance(user_id, str):
                if ObjectId.is_valid(user_id):
                    oid = ObjectId(user_id)
                elif user_id.isdigit():
                    # Fallback: String numérica tratada como int legado
                    if players_collection is not None:
                         doc = await asyncio.to_thread(players_collection.find_one, {"_id": int(user_id)})
            
            if oid and users_collection is not None:
                doc = await asyncio.to_thread(users_collection.find_one, {"_id": oid})
                
    except Exception as e:
        logger.error(f"Erro ao buscar player_data para {user_id} ({type(user_id)}): {e}")
        return None

    # 3. Se encontrou, salva no cache e retorna
    if doc:
        async with _player_cache_lock:
            _player_cache[cache_key] = dict(doc)
        return dict(doc)
        
    return None

async def save_player_data(user_id: Union[int, str, ObjectId], data: Dict[str, Any]) -> None:
    """
    Salva dados do jogador na coleção correta baseada no tipo do ID.
    """
    if not user_id or not data: return
    
    cache_key = _get_cache_key(user_id)
    
    # 1. Atualiza Cache Imediatamente
    async with _player_cache_lock:
        _player_cache[cache_key] = dict(data)

    # 2. Persiste no Banco (Async)
    try:
        # --- ROTEAMENTO HÍBRIDO ---
        if isinstance(user_id, int):
            # CASO 1: Salva no Legado (players)
            if players_collection is not None:
                await asyncio.to_thread(
                    players_collection.replace_one, 
                    {"_id": user_id}, 
                    data, 
                    upsert=True
                )
        else:
            # CASO 2: Salva no Novo (users)
            oid = None
            if isinstance(user_id, ObjectId):
                oid = user_id
            elif isinstance(user_id, str): 
                if ObjectId.is_valid(user_id):
                    oid = ObjectId(user_id)
                elif user_id.isdigit():
                    # Fallback: Salvando int legado que veio como string
                    if players_collection is not None:
                        await asyncio.to_thread(players_collection.replace_one, {"_id": int(user_id)}, data, upsert=True)
                    return

            if oid and users_collection is not None:
                # Garante que o campo _id no documento seja o ObjectId correto
                data["_id"] = oid 
                
                await asyncio.to_thread(
                    users_collection.replace_one, 
                    {"_id": oid}, 
                    data, 
                    upsert=True
                )
                
    except Exception as e:
        logger.error(f"Erro crítico ao salvar player {user_id}: {e}")

# ==============================================================================
# FUNÇÃO DE SUPORTE PARA MIGRAÇÃO (A QUE FALTAVA)
# ==============================================================================
async def get_legacy_data_by_telegram_id(telegram_id: int) -> Optional[Dict[str, Any]]:
    """
    Busca dados EXPLICITAMENTE na coleção antiga 'players'.
    Usado pelo auth_handler para migrar contas.
    """
    if players_collection is None:
        return None
    try:
        # No sistema antigo, o _id era o próprio telegram_id (int)
        return await asyncio.to_thread(players_collection.find_one, {"_id": telegram_id})
    except Exception as e:
        logger.error(f"Erro ao buscar legado para {telegram_id}: {e}")
        return None

# ==============================================================================
# GERENCIAMENTO DE CACHE
# ==============================================================================

async def clear_player_cache(user_id: Union[int, str, ObjectId]):
    """Remove um jogador específico do cache."""
    cache_key = _get_cache_key(user_id)
    async with _player_cache_lock:
        if cache_key in _player_cache:
            del _player_cache[cache_key]

def clear_all_player_cache():
    """Limpa todo o cache."""
    _player_cache.clear()
    logger.info("🧹 Cache de jogadores limpo.")