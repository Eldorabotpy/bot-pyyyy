# modules/player/core.py (VERSÃO CORRIGIDA, THREAD-SAFE E ASSÍNCRONA)
import os
import logging
import pymongo
from pymongo.errors import ConnectionFailure, ConfigurationError
from typing import Optional, Dict, Any
import asyncio
import certifi

# --- Globals ---
players_collection: Optional[pymongo.collection.Collection] = None
_player_cache: Dict[int, Dict[str, Any]] = {}
_player_cache_lock: asyncio.Lock = asyncio.Lock()  # protege acessos ao cache local

logger = logging.getLogger(__name__)

# --- MongoDB connection (executed at import time) ---
MONGO_CONNECTION_STRING = os.environ.get("MONGO_CONNECTION_STRING")

if not MONGO_CONNECTION_STRING:
    logger.error("CRÍTICO: MONGO_CONNECTION_STRING não definida! players_collection ficará None.")
else:
    try:
        ca = certifi.where()
        client = pymongo.MongoClient(MONGO_CONNECTION_STRING, tlsCAFile=ca)
        client.admin.command('ping')
        logger.info("✅ Conexão com o MongoDB estabelecida!")
        db = client.get_database("eldora_db")
        players_collection = db.get_collection("players")
        # Criar índice se possível (ignora erro se já existe)
        try:
            players_collection.create_index("character_name_normalized")
        except Exception:
            logger.debug("create_index falhou ou já existe; ignorando.")
    except ConfigurationError as e:
        logger.error(f"CRÍTICO: Erro de configuração do MongoDB (verifique a URI): {e}")
        players_collection = None
    except ConnectionFailure as e:
        logger.error(f"CRÍTICO: Falha na conexão com o MongoDB: {e}")
        players_collection = None
    except Exception as e:
        logger.exception(f"CRÍTICO: Erro inesperado ao conectar ao MongoDB: {e}")
        players_collection = None


# ====================================================================
# FUNÇÕES SÍNCRONAS (rodam em thread via asyncio.to_thread)
# ====================================================================

def _load_player_from_db_sync(user_id: int) -> Optional[dict]:
    """
    Carrega um documento do Mongo (síncrono). Retorna None se não encontrado
    ou se players_collection não estiver disponível.
    """
    if players_collection is None:
        return None

    try:
        player_doc = players_collection.find_one({"_id": user_id})
        if player_doc:
            player_copy = dict(player_doc)
            player_copy.pop("_id", None)
            return player_copy
        return None

    except Exception:
        logger.exception(f"Erro ao buscar player {user_id} no DB (sync).")
        return None

def _save_player_data_sync(user_id: int, player_info: dict) -> None:
    """
    Salva no Mongo de forma síncrona. Trabalha sempre sobre uma cópia para
    não mutar o objeto passado pelo chamador. Atualiza o cache apenas no final.
    """
    from . import queries, actions, inventory  # imports locais para evitar circular imports

    if players_collection is None:
        # Não causa exceção; apenas loga e retorna
        logger.error("_save_player_data_sync: players_collection é None (Mongo não conectado).")
        return

    try:
        # Trabalhar sobre uma cópia para não alterar o objeto passado
        to_save = dict(player_info)

        # Remove possíveis campos internos que não queremos salvar
        to_save.pop("_id", None)

        # Normalizações e saneamentos (na cópia)
        try:
            to_save["character_name_normalized"] = queries._normalize_char_name(to_save.get("character_name", ""))
        except Exception:
            logger.exception("Falha ao normalizar character_name durante save.")
        try:
            actions.sanitize_and_cap_energy(to_save)
        except Exception:
            logger.exception("Falha ao sanitizar energia durante save.")
        # Tenta executar a migração/sanitização de inventário de forma síncrona, se existir
        try:
            # inventory._sanitize_and_migrate_gold pode ser síncrono; se não existir, ignora
            if hasattr(inventory, "_sanitize_and_migrate_gold"):
                inventory._sanitize_and_migrate_gold(to_save)
        except Exception:
            logger.exception("Falha na migração síncrona de gold durante save.")

        # Gravamos no DB
        players_collection.replace_one({"_id": user_id}, to_save, upsert=True)

        # Atualiza cache local com uma cópia limpa
        # (a atualização do cache assíncrona/lock está na camada async que chama esta função)
    except Exception:
        logger.exception(f"Erro ao salvar player {user_id} no DB (sync).")


# ====================================================================
# FUNÇÕES ASSÍNCRONAS (INTERFACE)
# ====================================================================

async def get_player_data(user_id: int) -> Optional[dict]:
    """
    Carrega player data (tenta cache primeiro). Realiza migrações/saneamentos
    e atualiza o cache com a versão final do objeto.
    """
    from . import actions, stats, inventory  # imports locais

    if players_collection is None:
        logger.error("get_player_data: players_collection é None — retorna None.")
        return None

    # 1) Tenta cache (protegido)
    async with _player_cache_lock:
        cached = _player_cache.get(user_id)
        if cached is not None:
            # Retorna uma cópia para evitar mutações externas no cache
            logger.debug(f"[CACHE_DEBUG] Hit para user_id {user_id}")
            return dict(cached)

    # 2) Cache miss: buscar do DB em thread
    logger.debug(f"[CACHE_DEBUG] Miss para user_id {user_id}. Buscando no DB...")
    try:
        raw_data = await asyncio.to_thread(_load_player_from_db_sync, user_id)
    except Exception as e:
        logger.exception(f"[DB_DEBUG] Exceção chamando _load_player_from_db_sync para {user_id}: {e}")
        raw_data = None

    if raw_data is None:
        logger.debug(f"[CACHE_DEBUG] get_player_data: nenhum registro encontrado para {user_id}")
        return None

    # 3) Trabalhar sobre uma cópia e aplicar migrações/saneamentos
    data = dict(raw_data)
    data["user_id"] = user_id

    try:
        # Migrações / saneamentos que podem alterar o objeto
        changed_by_migration = False
        if hasattr(inventory, "_sanitize_and_migrate_gold"):
            try:
                # can be async or sync; support both
                maybe = inventory._sanitize_and_migrate_gold(data)
                if asyncio.iscoroutine(maybe):
                    changed_by_migration = await maybe
                else:
                    changed_by_migration = bool(maybe)
            except Exception:
                logger.exception("Erro em _sanitize_and_migrate_gold ao carregar player.")
        else:
            changed_by_migration = False

        try:
            changed_by_energy = actions._apply_energy_autoregen_inplace(data)
        except Exception:
            logger.exception("Erro em _apply_energy_autoregen_inplace.")
            changed_by_energy = False

        try:
            changed_by_sync = await stats._sync_all_stats_inplace(data)
        except Exception:
            logger.exception("Erro em _sync_all_stats_inplace.")
            changed_by_sync = False

        is_newly_updated = False
        # Campos mínimos de compatibilidade
        if 'mana' not in data:
            data['mana'] = 50
            data['max_mana'] = 50
            is_newly_updated = True
        if 'skills' not in data:
            data['skills'] = []
            is_newly_updated = True
    except Exception:
        logger.exception("Erro ao aplicar migrações/saneamentos em player data.")
        # Mesmo em caso de erro, seguimos com o raw_data parcialmente processado

    # 4) Atualiza cache com a versão final (protegido)
    try:
        async with _player_cache_lock:
            _player_cache[user_id] = dict(data)  # salva uma cópia
            logger.debug(f"[CACHE_DEBUG] Adicionado/Atualizado no cache: {user_id}")
    except Exception:
        logger.exception("Falha ao atualizar cache local.")

    # 5) Se alguma migração/sanitização alterou os dados, salva de volta no DB (não bloqueante)
    try:
        if changed_by_migration or changed_by_energy or changed_by_sync or is_newly_updated:
            logger.debug(f"[SAVE_DEBUG] Salvando alterações automáticas para {user_id} (migração/regen/stats).")
            # salvamos assincronamente (usa to_thread dentro)
            await save_player_data(user_id, data)
    except Exception:
        logger.exception("Erro ao salvar dados após migração.")

    return dict(data)


async def save_player_data(user_id: int, player_info: dict) -> None:
    """
    Salva player_info no DB de forma assíncrona usando asyncio.to_thread.
    Atualiza o cache local com a versão que foi salva (cópia).
    """
    if players_collection is None:
        logger.error("save_player_data: players_collection é None (Mongo não conectado); não salvando.")
        return

    # Trabalhar com cópia para não mutar o objeto do chamador
    to_save = dict(player_info)

    # Garantir que user_id está correto
    to_save["user_id"] = user_id

    # Executar o save síncrono em thread
    try:
        await asyncio.to_thread(_save_player_data_sync, user_id, to_save)
    except Exception:
        logger.exception(f"save_player_data: erro ao persistir {user_id} no DB via thread.")
        # mesmo em caso de exceção, tentamos atualizar cache local para evitar leituras inconsistentes
    finally:
        # Atualiza cache com a versão final que tentamos salvar
        try:
            async with _player_cache_lock:
                _player_cache[user_id] = dict(to_save)
        except Exception:
            logger.exception("save_player_data: falha ao atualizar cache local após save.")


def clear_player_cache(user_id: int) -> bool:
    """
    Remove entrada do cache local (thread-safe).
    Retorna True se foi removida.
    """
    # lock síncrono não disponível; usar loop atual
    try:
        loop = asyncio.get_running_loop()
        # se estamos dentro do event loop, usamos uma chamada síncrona sobre o lock
        # mas aqui simplificamos: apenas removemos sem lock (caso raro), ou schedule uma remoção segura
    except RuntimeError:
        # Não há event loop rodando — podemos acessar diretamente
        if user_id in _player_cache:
            del _player_cache[user_id]
            return True
        return False

    # Se há event loop, agendamos a remoção com lock via coroutine
    async def _remove():
        async with _player_cache_lock:
            if user_id in _player_cache:
                del _player_cache[user_id]
                return True
            return False

    fut = asyncio.run_coroutine_threadsafe(_remove(), loop)
    return bool(fut.result())


def clear_all_player_cache() -> int:
    """
    Limpa todo o cache local. Retorna o número de itens removidos.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # sem loop, acesso direto
        num = len(_player_cache)
        _player_cache.clear()
        return num

    async def _clear():
        async with _player_cache_lock:
            n = len(_player_cache)
            _player_cache.clear()
            return n

    fut = asyncio.run_coroutine_threadsafe(_clear(), loop)
    return int(fut.result())
