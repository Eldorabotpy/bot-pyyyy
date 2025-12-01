# modules/file_ids.py
# (VERSÃO CORRIGIDA: Comparação explícita 'is not None')
from __future__ import annotations

import logging
import threading
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Iterable

# Importa a conexão central do banco
from modules.database import db

logger = logging.getLogger(__name__)

# ==============================================================================
# CONFIGURAÇÃO E CACHE
# ==============================================================================

COLLECTION_NAME = "file_assets"

_CACHE: Dict[str, Dict[str, str]] = {}
_LOCK = threading.RLock()
_INITIALIZED = False

# ==============================================================================
# LÓGICA DE BANCO DE DADOS
# ==============================================================================

def _get_collection():
    """Retorna a coleção do Mongo ou None se não conectado."""
    if db is not None:
        return db[COLLECTION_NAME]
    return None

def _load_cache_from_db():
    """Baixa todos os IDs do Mongo para a memória RAM."""
    global _CACHE
    col = _get_collection()
    
    # [CORREÇÃO] Comparação explícita
    if col is None:
        return

    with _LOCK:
        new_cache = {}
        try:
            cursor = col.find({})
            for doc in cursor:
                key = doc["_id"]
                new_cache[key] = {
                    "id": doc.get("file_id"),
                    "type": doc.get("file_type", "photo")
                }
            _CACHE = new_cache
            logger.info(f"[FILE_IDS] Cache carregado com {len(_CACHE)} arquivos de mídia.")
        except Exception as e:
            logger.error(f"[FILE_IDS] Erro ao carregar cache do Mongo: {e}")

def _migrate_json_to_mongo():
    """Migra dados do JSON local para o Mongo se estiver vazio."""
    col = _get_collection()
    
    # [CORREÇÃO] Comparação explícita
    if col is None: return

    try:
        if col.count_documents({}, limit=1) > 0:
            return
    except:
        return

    json_path = Path("assets/file_ids.json")
    if not json_path.exists():
        json_path = Path("bot/assets/file_ids.json")
    
    if json_path.exists():
        logger.warning("[FILE_IDS] Iniciando migração de JSON para MongoDB...")
        try:
            raw = json_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            
            for key, val in data.items():
                if not key: continue
                
                if isinstance(val, str):
                    fid = val
                    ftype = "photo"
                else:
                    fid = val.get("id")
                    ftype = val.get("type", "photo")
                
                if fid:
                    col.replace_one(
                        {"_id": key.strip()}, 
                        {"_id": key.strip(), "file_id": fid, "file_type": ftype}, 
                        upsert=True
                    )
            
            logger.info("[FILE_IDS] Migração concluída com sucesso!")
            try:
                os.rename(json_path, str(json_path) + ".bak")
            except:
                pass
            
        except Exception as e:
            logger.error(f"[FILE_IDS] Falha na migração JSON->Mongo: {e}")

# ==============================================================================
# INICIALIZAÇÃO
# ==============================================================================
def _ensure_initialized():
    global _INITIALIZED
    if not _INITIALIZED:
        with _LOCK:
            if not _INITIALIZED:
                _migrate_json_to_mongo()
                _load_cache_from_db()
                _INITIALIZED = True

# ==============================================================================
# FUNÇÕES PUBLICAS
# ==============================================================================

def get_file_data(key: str) -> Optional[Dict[str, str]]:
    _ensure_initialized()
    k = str(key).strip()
    return _CACHE.get(k)

def get_file_id(key: str) -> Optional[str]:
    data = get_file_data(key)
    return data["id"] if data else None

def get_file_type(key: str) -> Optional[str]:
    data = get_file_data(key)
    return data["type"] if data else None

def set_file_data(key: str, file_id: str, file_type: str = "photo") -> None:
    _ensure_initialized()
    col = _get_collection()
    
    k = str(key).strip()
    fid = str(file_id).strip()
    ftype = "video" if file_type.lower() == "video" else "photo"

    if not k or not fid:
        raise ValueError("Chave ou File ID inválidos.")

    # [CORREÇÃO] Alterado 'if col:' para 'if col is not None:'
    if col is not None:
        try:
            col.update_one(
                {"_id": k},
                {"$set": {"file_id": fid, "file_type": ftype}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"[FILE_IDS] Erro ao salvar no Mongo: {e}")
    
    with _LOCK:
        _CACHE[k] = {"id": fid, "type": ftype}

def save_file_id(key: str, file_id: str, file_type: str = "photo") -> None:
    set_file_data(key, file_id, file_type)

def delete_file_data(key: str) -> bool:
    _ensure_initialized()
    col = _get_collection()
    k = str(key).strip()

    if not k: return False

    # [CORREÇÃO] Alterado 'if col:' para 'if col is not None:'
    if col is not None:
        try:
            col.delete_one({"_id": k})
        except Exception as e:
            logger.error(f"[FILE_IDS] Erro ao deletar do Mongo: {e}")

    with _LOCK:
        if k in _CACHE:
            del _CACHE[k]
            return True
    return False

def list_keys() -> Tuple[str, ...]:
    _ensure_initialized()
    with _LOCK:
        return tuple(sorted(_CACHE.keys()))

def exists(key: str) -> bool:
    _ensure_initialized()
    return str(key).strip() in _CACHE

def refresh_cache() -> None:
    _load_cache_from_db()

def get_all_normalized() -> Dict[str, Dict[str, str]]:
    _ensure_initialized()
    return _CACHE.copy()

def get_store_path() -> Path:
    return Path("MONGODB_CLOUD_STORAGE")