# modules/player/core.py (VERSÃO HÍBRIDA: MONGO + MONGITA)
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

# ====================================================================
# CONFIGURAÇÃO INTELIGENTE DE BANCO DE DADOS
# ====================================================================

# Lê o modo do bot ('dev' localmente, 'prod' no Render/Production)
# Se não estiver definido, assume 'prod' por segurança.
BOT_MODE = os.environ.get("BOT_MODE", "prod").lower()

if BOT_MODE == "dev":
    # === MODO DE TESTE LOCAL (MONGITA) ===
    logger.warning("⚠️ RODANDO EM MODO LOCAL (DEV). USANDO BANCO DE DADOS DE ARQUIVO (MONGITA).")
    try:
        from mongita import MongitaClientDisk
        
        # Cria (ou carrega) o banco na pasta local protegida pelo .gitignore
        client = MongitaClientDisk(host="./.local_db_data")
        
        # Usa um nome de banco diferente para garantir isolamento visual
        db = client.get_database("eldora_test_db")
        players_collection = db.get_collection("players")
        
        logger.info("✅ Conectado ao Mongita Local com sucesso!")
        logger.info("📁 Os dados estão sendo salvos em: ./.local_db_data")
        
    except ImportError:
        logger.error("❌ ERRO: A biblioteca 'mongita' não está instalada.")
        logger.error("👉 Rode: pip install mongita")
        logger.error("Ou mude BOT_MODE para 'prod' no seu .env")
        players_collection = None
    except Exception as e:
        logger.exception(f"Erro inesperado ao iniciar Mongita: {e}")
        players_collection = None

else:
    # === MODO DE PRODUÇÃO (MONGODB ATLAS / RENDER) ===
    MONGO_CONNECTION_STRING = os.environ.get("MONGO_CONNECTION_STRING")

    if not MONGO_CONNECTION_STRING:
        logger.error("CRÍTICO: MONGO_CONNECTION_STRING não definida! players_collection ficará None.")
    else:
        try:
            ca = certifi.where()
            client = pymongo.MongoClient(MONGO_CONNECTION_STRING, tlsCAFile=ca)
            # Teste de conexão (Ping)
            client.admin.command('ping')
            
            logger.info("✅ Conexão com o MongoDB (Produção) estabelecida!")
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
        pass


        # Gravamos no DB
        players_collection.replace_one({"_id": user_id}, to_save, upsert=True)

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

    async with _player_cache_lock:
        cached = _player_cache.get(user_id)
        if cached is not None:
            logger.debug(f"[CACHE_DEBUG] Hit para user_id {user_id}")
            return dict(cached)

    logger.debug(f"[CACHE_DEBUG] Miss para user_id {user_id}. Buscando no DB...")
    try:
        raw_data = await asyncio.to_thread(_load_player_from_db_sync, user_id)
    except Exception as e:
        logger.exception(f"[DB_DEBUG] Exceção chamando _load_player_from_db_sync para {user_id}: {e}")
        raw_data = None

    if raw_data is None:
        logger.debug(f"[CACHE_DEBUG] get_player_data: nenhum registro encontrado para {user_id}")
        return None

    data = dict(raw_data)
    data["user_id"] = user_id

    try:
        changed_by_migration = False
        if hasattr(inventory, "_sanitize_and_migrate_gold"):
            try:
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

        # --- Migração do Sistema de Skills (Lista -> Dicionário -> com Progress) ---
        if 'skills' not in data or not isinstance(data.get('skills'), dict):
            logger.info(f"Migrando 'skills' (era lista) para o formato de dicionário para o user: {data.get('user_id', '???')}")
           
            # Se 'skills' existe e é uma lista antiga
            if isinstance(data.get('skills'), list):
                old_skills_list = data.get('skills', [])
                new_skills_dict = {}
                for skill_id in old_skills_list:
                    if skill_id and skill_id not in new_skills_dict:
                        # Adiciona a skill antiga com a raridade 'comum' E o novo contador
                        new_skills_dict[skill_id] = {"rarity": "comum", "progress": 0}
                data['skills'] = new_skills_dict
            else:
                # É um jogador novo ou 'skills' está ausente
                data['skills'] = {}
            is_newly_updated = True

        else:
            # O jogador JÁ TEM um dicionário de skills.
            skills_dict = data.get('skills', {})
            # Usamos list(skills_dict.keys()) para evitar 'dictionary changed size during iteration'
            for skill_id in list(skills_dict.keys()): 
                if isinstance(skills_dict.get(skill_id), dict):
                    if "progress" not in skills_dict[skill_id]:
                        # Esta é uma skill migrada (dict) mas antiga (sem progress)
                        skills_dict[skill_id]["progress"] = 0
                        is_newly_updated = True # Força o salvamento
                else:
                    # O dicionário está corrompido
                    logger.warning(f"Corrigindo skill mal formatada: {skill_id} para user {data.get('user_id', '???')}")
                    if skill_id in skills_dict:
                        del skills_dict[skill_id]
                    skills_dict[skill_id] = {"rarity": "comum", "progress": 0}
                    is_newly_updated = True
        # --- Fim da Migração ---
    
    except Exception:
        logger.exception("Erro ao aplicar migrações/saneamentos em player data.")

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


# ====================================================================
# FUNÇÕES DE LIMPEZA DE CACHE (CORRIGIDAS)
# ====================================================================

async def clear_player_cache(user_id: int) -> bool:
    """
    Remove entrada do cache local de forma assíncrona e segura.
    Retorna True se foi removida.
    """
    async with _player_cache_lock:
        if user_id in _player_cache:
            del _player_cache[user_id]
            return True
        return False

async def clear_all_player_cache() -> int:
    """
    Limpa todo o cache local de forma assíncrona.
    Retorna o número de itens removidos.
    """
    async with _player_cache_lock:
        num = len(_player_cache)
        _player_cache.clear()
        return num