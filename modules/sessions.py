# modules/sessions.py
import logging
import certifi
import asyncio
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)

# Conexão direta e blindada para garantir que as sessões sempre funcionem
MONGO_STR = "mongodb+srv://eldora-cluster:pb060987@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    client = MongoClient(MONGO_STR, tlsCAFile=certifi.where())
    db = client["eldora_db"]
    sessions_collection = db["active_sessions"]
    logger.info("✅ [SESSIONS] Conexão MongoDB: SUCESSO.")
except Exception as e:
    logger.critical(f"❌ [SESSIONS] Erro conexão: {e}")
    sessions_collection = None


async def asyncio_wrap(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)


def _normalize_telegram_id(telegram_user_id) -> str | None:
    """
    Normaliza telegram_user_id para string.
    Aceita int/str, retorna string apenas com dígitos.
    """
    if telegram_user_id is None:
        return None

    # int -> string
    if isinstance(telegram_user_id, int):
        return str(telegram_user_id)

    # str -> apenas dígitos
    if isinstance(telegram_user_id, str):
        tid = telegram_user_id.strip()
        if tid.isdigit():
            return tid
        return None

    try:
        tid = str(telegram_user_id).strip()
        if tid.isdigit():
            return tid
    except Exception:
        pass

    return None


def _normalize_player_id(player_id) -> str | None:
    """
    Aceita qualquer coisa, mas só retorna string de ObjectId válido.
    """
    if player_id is None:
        return None

    if isinstance(player_id, ObjectId):
        return str(player_id)

    if isinstance(player_id, str):
        pid = player_id.strip()
        if ObjectId.is_valid(pid):
            return pid
        return None

    if isinstance(player_id, int):
        return None

    try:
        pid = str(player_id).strip()
        if ObjectId.is_valid(pid):
            return pid
    except Exception:
        pass

    return None


async def save_persistent_session(telegram_user_id, player_id):
    """
    Salva sessão persistente do Telegram -> player ObjectId (string).
    """
    if sessions_collection is None:
        return

    tid = _normalize_telegram_id(telegram_user_id)
    if not tid:
        return

    pid = _normalize_player_id(player_id)
    if not pid:
        return

    try:
        await asyncio_wrap(
            sessions_collection.replace_one,
            {"_id": tid},
            {
                "_id": tid,
                "telegram_id": tid,
                "player_id": pid,  # sempre string ObjectId válida
                "last_login": datetime.now(timezone.utc).isoformat(),
            },
            upsert=True,
        )
    except Exception as e:
        logger.error(f"[SESSIONS] Erro save_session: {e}")


async def get_persistent_session(telegram_user_id) -> str | None:
    """
    Retorna string ObjectId válida ou None.
    """
    if sessions_collection is None:
        return None

    tid = _normalize_telegram_id(telegram_user_id)
    if not tid:
        return None

    try:
        doc = await asyncio_wrap(sessions_collection.find_one, {"_id": tid})
        if not doc:
            return None

        pid = doc.get("player_id")
        pid_norm = _normalize_player_id(pid)
        if not pid_norm:
            try:
                await clear_persistent_session(tid)
            except Exception:
                pass
            return None

        return pid_norm

    except Exception as e:
        logger.error(f"[SESSIONS] Erro get_session: {e}")
        return None


async def clear_persistent_session(telegram_user_id):
    if sessions_collection is None:
        return

    tid = _normalize_telegram_id(telegram_user_id)
    if not tid:
        return

    try:
        await asyncio_wrap(sessions_collection.delete_one, {"_id": tid})
    except Exception:
        pass