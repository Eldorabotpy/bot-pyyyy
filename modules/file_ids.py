# modules/file_ids.py
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Iterable
import threading
import tempfile

# ---------------------------------------------------------
# Config
# ---------------------------------------------------------
_DEFAULT_PATHS: Tuple[Path, ...] = (
    Path("assets/file_ids.json"),      # caminho padrão do seu projeto
    Path("bot/assets/file_ids.json"),  # compat opcional
)

_JSON_CACHE: Dict[str, Any] | None = None
_JSON_PATH: Path | None = None
_LOCK = threading.RLock()  # segurança contra concorrência


# ---------------------------------------------------------
# Path / I/O
# ---------------------------------------------------------
def _resolve_path() -> Path:
    """
    Resolve o caminho do JSON. Se nenhum existir, escolhe o primeiro
    da lista (_DEFAULT_PATHS[0]).
    """
    global _JSON_PATH
    if _JSON_PATH:
        return _JSON_PATH
    for p in _DEFAULT_PATHS:
        if p.exists():
            _JSON_PATH = p
            return p
    _JSON_PATH = _DEFAULT_PATHS[0]
    return _JSON_PATH


def _ensure_file_exists() -> Path:
    """
    Garante que o diretório exista e o arquivo JSON também (inicializa com {}).
    """
    path = _resolve_path()
    os.makedirs(path.parent, exist_ok=True)
    if not path.exists():
        # gravação atômica para criar o arquivo vazio
        tmp_fd, tmp_name = tempfile.mkstemp(prefix="file_ids_", suffix=".json.tmp", dir=str(path.parent))
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False)
            os.replace(tmp_name, path)
        finally:
            try:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
            except Exception:
                pass
    return path


def get_store_path() -> Path:
    """
    Caminho absoluto do arquivo JSON de armazenamento.
    Útil para logar/mostrar onde está salvando.
    """
    return _ensure_file_exists().resolve()


def _load() -> Dict[str, Any]:
    """
    Carrega o JSON em cache de processo.
    """
    global _JSON_CACHE
    with _LOCK:
        if _JSON_CACHE is not None:
            return _JSON_CACHE
        path = _ensure_file_exists()
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw) if raw.strip() else {}
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}
        _JSON_CACHE = data
        return _JSON_CACHE


def _atomic_save_json(path: Path, data: Dict[str, Any]) -> None:
    """
    Grava JSON de forma atômica: escreve em arquivo temporário e faz os.replace().
    """
    tmp_fd, tmp_name = tempfile.mkstemp(prefix="file_ids_", suffix=".json.tmp", dir=str(path.parent))
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        except Exception:
            pass


def _save(db: Dict[str, Any]) -> None:
    """
    Persiste no disco. Mantém o mesmo objeto referenciado no cache.
    """
    global _JSON_CACHE
    with _LOCK:
        path = _ensure_file_exists()
        _atomic_save_json(path, db)
        _JSON_CACHE = db  # garante que o cache aponte para o mesmo conteúdo


# ---------------------------------------------------------
# Normalizações / validações
# ---------------------------------------------------------
def _norm_key(key: str | None) -> str:
    """
    Normaliza a chave de mídia (remove espaços nas pontas).
    """
    if key is None:
        return ""
    return str(key).strip()


def _norm_type(file_type: str | None) -> str:
    """
    Normaliza o tipo ('photo'|'video'), padrão 'photo'.
    """
    t = (file_type or "photo").strip().lower()
    if t not in {"photo", "video"}:
        t = "photo"
    return t


# ---------------------------------------------------------
# API principal
# ---------------------------------------------------------
def get_file_data(key: str) -> Optional[Dict[str, str]]:
    """
    Retorna {'id': '...', 'type': 'photo'|'video'} ou None.
    Aceita formato legado (valor string => assume 'photo').
    """
    k = _norm_key(key)
    if not k:
        return None
    db = _load()
    val = db.get(k)
    if val is None:
        return None
    if isinstance(val, str):
        return {"id": val, "type": "photo"}
    fid = (val or {}).get("id")
    if not fid:
        return None
    ftype = _norm_type((val or {}).get("type"))
    return {"id": fid, "type": ftype}


def get_file_id(key: str) -> Optional[str]:
    """
    Retorna apenas o file_id (ou None).
    """
    fd = get_file_data(key)
    return fd["id"] if fd else None


def get_file_type(key: str) -> Optional[str]:
    """
    Retorna apenas o tipo salvo ('photo'|'video') (ou None).
    """
    fd = get_file_data(key)
    return fd["type"] if fd else None


def set_file_data(key: str, file_id: str, file_type: str = "photo") -> None:
    """
    Cria/atualiza a entrada de mídia.
    file_type: 'photo' ou 'video'
    """
    k = _norm_key(key)
    if not k:
        raise ValueError("A chave (nome) não pode ser vazia.")
    fid = str(file_id or "").strip()
    if not fid:
        raise ValueError("file_id não pode ser vazio.")
    ftype = _norm_type(file_type)

    with _LOCK:
        db = _load()
        # _load() pode ter retornado o objeto de cache; copiamos para
        # evitar mutação visível em caso de erro de gravação.
        new_db = dict(db)
        new_db[k] = {"id": fid, "type": ftype}
        _save(new_db)


# Alias para compatibilidade com conversas que chamam save_file_id(...)
def save_file_id(key: str, file_id: str, file_type: str = "photo") -> None:
    set_file_data(key, file_id, file_type)


def delete_file_data(key: str) -> bool:
    """
    Remove a entrada. Retorna True se removeu.
    """
    k = _norm_key(key)
    if not k:
        return False
    with _LOCK:
        db = _load()
        if k in db:
            new_db = dict(db)
            del new_db[k]
            _save(new_db)
            return True
        return False


def list_keys() -> Tuple[str, ...]:
    """
    Lista todas as chaves cadastradas (ordenadas por nome).
    """
    with _LOCK:
        return tuple(sorted(_load().keys()))


def exists(key: str) -> bool:
    """
    Verifica se a chave existe.
    """
    k = _norm_key(key)
    if not k:
        return False
    with _LOCK:
        return k in _load()


def items() -> Iterable[Tuple[str, Dict[str, str] | str]]:
    """
    Itera sobre os itens crus do banco (pode conter formato legado).
    """
    with _LOCK:
        return tuple(_load().items())


def get_all_normalized() -> Dict[str, Dict[str, str]]:
    """
    Retorna um dicionário {key: {'id':..., 'type':...}} já normalizado,
    convertendo valores legados (string → {'id':..., 'type':'photo'}).
    """
    with _LOCK:
        src = _load()
        out: Dict[str, Dict[str, str]] = {}
        for k, v in src.items():
            if isinstance(v, str):
                out[k] = {"id": v, "type": "photo"}
            else:
                fid = (v or {}).get("id")
                if fid:
                    out[k] = {"id": fid, "type": _norm_type((v or {}).get("type"))}
        return out


def refresh_cache() -> None:
    """
    Descarta o cache e recarrega do disco (útil se você editar o JSON manualmente).
    """
    global _JSON_CACHE
    with _LOCK:
        _JSON_CACHE = None
        _load()
