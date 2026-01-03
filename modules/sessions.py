# modules/sessions.py
# (NOVO ARQUIVO: Gerencia Login Automático Persistente)

from modules.player.core import db
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Coleção dedicada para sessões ativas
# Estrutura: { "_id": TelegramID (int), "player_id": "ObjectId_String", "last_login": Date }
sessions_collection = db["active_sessions"]

async def save_persistent_session(telegram_user_id: int, player_id: str):
    """Salva o login no banco para resistir a reinicializações."""
    try:
        await asyncio_wrap(sessions_collection.replace_one, 
            {"_id": telegram_user_id},
            {
                "_id": telegram_user_id,
                "player_id": str(player_id),
                "last_login": datetime.utcnow()
            },
            upsert=True
        )
    except Exception as e:
        logger.error(f"Erro ao salvar sessão persistente: {e}")

async def get_persistent_session(telegram_user_id: int) -> str | None:
    """Verifica se existe um login salvo no banco."""
    try:
        doc = await asyncio_wrap(sessions_collection.find_one, {"_id": telegram_user_id})
        if doc:
            return doc.get("player_id")
    except Exception as e:
        logger.error(f"Erro ao recuperar sessão persistente: {e}")
    return None

async def clear_persistent_session(telegram_user_id: int):
    """Remove o login do banco (Logout Real)."""
    try:
        await asyncio_wrap(sessions_collection.delete_one, {"_id": telegram_user_id})
    except Exception as e:
        logger.error(f"Erro ao limpar sessão: {e}")

# Helper simples para rodar pymongo em async
import asyncio
async def asyncio_wrap(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)