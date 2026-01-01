# modules/player/core.py
# (VERSÃO BLINDADA: Suporte Híbrido Players/Users + Cache Seguro)

import logging
import asyncio
from typing import Optional, Dict, Any, Union
from bson import ObjectId

# Configuração de Logs
logger = logging.getLogger(__name__)

# --- 1. CONFIGURAÇÃO DAS COLEÇÕES ---
players_collection = None
users_collection = None

try:
    # Tenta importar do módulo central de database
    from modules.database import players_col as pc
    players_collection = pc
    # Se conseguiu players, tenta pegar users do mesmo database
    if players_collection is not None:
        db = players_collection.database
        users_collection = db["users"]
        logger.info("✅ [CORE] Conectado a Players (Legado) e Users (Novo).")
except ImportError:
    logger.error("❌ [CORE] Erro ao importar players_collection. O banco pode estar inacessível.")

# --- 2. SISTEMA DE CACHE ---
# Cache em memória para evitar chamadas excessivas ao Mongo
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
            # Retorna uma cópia para evitar modificação direta no cache por referência
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
            elif isinstance(user_id, str) and ObjectId.is_valid(user_id):
                oid = ObjectId(user_id)
            
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
    
    # 1. Atualiza Cache Imediatamente (para a UI ficar rápida)
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
            elif isinstance(user_id, str) and ObjectId.is_valid(user_id):
                oid = ObjectId(user_id)
            
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
# GERENCIAMENTO DE CACHE
# ==============================================================================

async def clear_player_cache(user_id: Union[int, str, ObjectId]):
    """Remove um jogador específico do cache (útil após logout ou update manual)."""
    cache_key = _get_cache_key(user_id)
    async with _player_cache_lock:
        if cache_key in _player_cache:
            del _player_cache[cache_key]

def clear_all_player_cache():
    """Limpa todo o cache (útil para manutenção)."""
    # Não precisa ser async se usarmos ensure_future, mas para segurança de thread:
    # (Como limpar tudo é raro e drástico, podemos fazer um clear direto no dict se o lock permitir)
    _player_cache.clear()
    logger.info("🧹 Cache de jogadores limpo.")