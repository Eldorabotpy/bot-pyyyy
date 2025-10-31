# Em modules/player/core.py (VERSÃO CORRIGIDA E LIMPA)

import os
import logging
import pymongo
from pymongo.errors import ConnectionFailure, ConfigurationError # Importa o ConfigurationError
from typing import Optional, Dict, Any, TYPE_CHECKING
import asyncio # Essencial para a execução assíncrona moderna
import certifi # Mantém a importação do certifi

# --- Configuração de Variáveis Globais ---
players_collection: Optional[pymongo.collection.Collection] = None
_player_cache: Dict[int, Dict[str, Any]] = {}
# A variável _application_instance e a função init_core são REMOVIDAS.

# --- Configuração de Logging ---
logger = logging.getLogger(__name__)

# --- Conexão ao MongoDB (Mantida Síncrona na Inicialização) ---
MONGO_CONNECTION_STRING = os.environ.get("MONGO_CONNECTION_STRING")

if not MONGO_CONNECTION_STRING:
    logger.error("CRÍTICO: MONGO_CONNECTION_STRING não definida!")
else:
    try:
        # <<< ESTA É A VERSÃO CORRETA (HEAD) >>>
        # Obtém o caminho para o ficheiro de certificados do certifi
        ca = certifi.where()
        # Adiciona tlsCAFile=ca à chamada do MongoClient
        client = pymongo.MongoClient(MONGO_CONNECTION_STRING, tlsCAFile=ca)

        client.admin.command('ping') # Testa a conexão
        logger.info("✅ Conexão com o MongoDB estabelecida!")
        db = client.get_database("eldora_db") # <<< Confirma se "eldora_db" é o nome correto
        players_collection = db.get_collection("players") # <<< Confirma se "players" é o nome correto
        players_collection.create_index("character_name_normalized") # <<< Indexação mantida
    # <<< Captura erros específicos para melhor diagnóstico >>>
    except ConfigurationError as e:
        logger.error(f"CRÍTICO: Erro de configuração do MongoDB (verifique a URI): {e}")
        players_collection = None # Garante que a coleção fica None
    except ConnectionFailure as e:
        logger.error(f"CRÍTICO: Falha na conexão com o MongoDB (verifique rede/firewall/certificados): {e}")
        players_collection = None # Garante que a coleção fica None
    except Exception as e:
        logger.error(f"CRÍTICO: Erro inesperado ao conectar ao MongoDB: {e}", exc_info=True) # Log completo para outros erros
        players_collection = None # Garante que a coleção fica None

# ====================================================================
# FUNÇÕES SÍNCRONAS (EXECUÇÃO DE BLOQUEIO)
# ====================================================================
def _load_player_from_db_sync(user_id: int) -> dict | None:
    """Função SÍNCRONA: Carrega dados do MongoDB."""
    if players_collection is None: return None
    player_doc = players_collection.find_one({"_id": user_id})
    if player_doc:
        player_doc.pop('_id', None)
    return player_doc

def _save_player_data_sync(user_id: int, player_info: dict) -> None:
    """Função SÍNCRONA: Salva dados no MongoDB e atualiza o cache local."""
    from . import queries, actions, inventory # <<< ADICIONA 'inventory' AQUI
    if players_collection is None: return

    _player_cache[user_id] = player_info.copy()
    player_info.pop('_id', None)

    # Normalizações
    player_info["character_name_normalized"] = queries._normalize_char_name(player_info.get("character_name", ""))
    actions.sanitize_and_cap_energy(player_info)

    # <<< ADICIONA ESTA LINHA >>>
    #inventory._sanitize_and_migrate_gold(player_info) # Executa a migração síncrona

    players_collection.replace_one({"_id": user_id}, player_info, upsert=True)

# ====================================================================
# FUNÇÕES ASSÍNCRONAS (INTERFACE EXTERNA)
# ====================================================================

# Em modules/player/core.py

async def get_player_data(user_id: int) -> dict | None:
    from . import actions, stats, inventory 
    logger.debug(f"[CACHE_DEBUG] Tentando buscar user_id {user_id}") # Log 1: Início

    if user_id in _player_cache:
        raw_data = _player_cache[user_id].copy()
        logger.debug(f"[CACHE_DEBUG] Encontrado no cache para {user_id}") # Log 2: Cache Hit
    else:
        logger.debug(f"[CACHE_DEBUG] Não encontrado no cache. Buscando no DB para {user_id}...") # Log 3: Cache Miss
        try:
            # Chama a função síncrona numa thread separada
            raw_data = await asyncio.to_thread(_load_player_from_db_sync, user_id) 
            
            # <<< LOG IMPORTANTE AQUI >>>
            logger.debug(f"[DB_DEBUG] Resultado de _load_player_from_db_sync para {user_id}: Tipo={type(raw_data)}, Valor={repr(raw_data)[:200]}") # Log 4: Resultado DB
            
            if raw_data is not None and isinstance(raw_data, dict): # Verifica se é um dict válido
                _player_cache[user_id] = raw_data.copy() # Guarda no cache SÓ SE FOR VÁLIDO
                logger.debug(f"[CACHE_DEBUG] Adicionado ao cache: {user_id}") # Log 5: Adicionado ao Cache
            elif raw_data is not None:
                logger.warning(f"[DB_DEBUG] _load_player_from_db_sync retornou tipo inesperado para {user_id}: {type(raw_data)}") # AVISO se não for dict
                # Decide o que fazer: retornar None ou tentar corrigir? Por agora, retornamos None.
                raw_data = None 
                
        except Exception as e:
            logger.error(f"[DB_DEBUG] Erro ao carregar {user_id} do DB via thread: {e}", exc_info=True) # Log de Erro na Thread
            raw_data = None # Garante None em caso de exceção

    # Verifica se raw_data é None (seja por não encontrar ou por erro/tipo inválido)
    if raw_data is None: 
        logger.debug(f"[CACHE_DEBUG] Retornando None para {user_id}") # Log 6: Retornando None
        return None 

    # Se chegou aqui, raw_data é um dicionário
    data = raw_data 
    data["user_id"] = user_id
    
    # ... (resto da lógica de migração, energia, stats - mantém como está) ...
    changed_by_migration = await inventory._sanitize_and_migrate_gold(data)
    changed_by_energy = actions._apply_energy_autoregen_inplace(data)
    changed_by_sync = await stats._sync_all_stats_inplace(data)
    is_newly_updated = False # (Move a definição para antes do if)
    if 'mana' not in data: data['mana'] = 50; data['max_mana'] = 50; is_newly_updated = True
    if 'skills' not in data: data['skills'] = []; is_newly_updated = True
    
    if changed_by_energy or changed_by_sync or is_newly_updated or changed_by_migration:
        logger.debug(f"[SAVE_DEBUG] Salvando dados atualizados para {user_id}...") # Log 7: Salvando
        await save_player_data(user_id, data)
            
    # Retorna o dicionário processado
    return data

async def save_player_data(user_id: int, player_info: dict) -> None:
    """Salva dados no DB de forma assíncrona usando asyncio.to_thread."""
    if players_collection is None: return

    # <<< CORREÇÃO PRINCIPAL: Usa asyncio.to_thread para não bloquear o loop >>>
    await asyncio.to_thread(_save_player_data_sync, user_id, player_info.copy())
    
def clear_player_cache(user_id: int) -> bool:
    """Limpa o cache do jogador."""
    if user_id in _player_cache:
        del _player_cache[user_id]
        return True
    return False

def clear_all_player_cache() -> int:
    """Limpa todo o cache."""
    num_items = len(_player_cache)
    _player_cache.clear()
    return num_items