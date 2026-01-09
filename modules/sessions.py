# modules/sessions.py
import logging
import certifi
import asyncio
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)

MONGO_STR = "mongodb+srv://eldora-cluster:pb060987@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
sessions_collection = None

try:
    client = MongoClient(MONGO_STR, tlsCAFile=certifi.where())
    db = client["eldora_db"]
    sessions_collection = db["active_sessions"]
    # Cria indice para busca rápida
    sessions_collection.create_index("telegram_id", unique=True)
except Exception as e:
    logger.error(f"❌ [SESSIONS] Erro conexão: {e}")

async def asyncio_wrap(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)

async def save_persistent_session(telegram_user_id: int, player_id: str):
    if sessions_collection is None: return
    try:
        await asyncio_wrap(
            sessions_collection.replace_one,
            {"_id": telegram_user_id},
            {
                "_id": telegram_user_id,
                "telegram_id": telegram_user_id,
                "player_id": str(player_id), # Garante salvar como string
                "last_login": datetime.now(timezone.utc)
            },
            upsert=True
        )
    except Exception as e:
        logger.error(f"Erro save_session: {e}")

async def get_persistent_session(telegram_user_id: int) -> str | None:
    if sessions_collection is None: return None
    try:
        doc = await asyncio_wrap(sessions_collection.find_one, {"_id": telegram_user_id})
        if doc and "player_id" in doc:
            # O SEGREDO ESTÁ AQUI:
            # Mesmo que no banco esteja ObjectId, converte pra string
            return str(doc["player_id"])
    except Exception as e:
        logger.error(f"Erro get_session: {e}")
    return None

async def clear_persistent_session(telegram_user_id: int):
    if sessions_collection is None: return
    try:
        await asyncio_wrap(sessions_collection.delete_one, {"_id": telegram_user_id})
    except Exception: pass