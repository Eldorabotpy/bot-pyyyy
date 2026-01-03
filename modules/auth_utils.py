# modules/auth_utils.py

import logging
from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from modules.player.core import users_collection #

logger = logging.getLogger(__name__)

def get_current_player_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str | None:
    """
    Retorna o User ID (Mongo _id). 
    O Telegram ID serve APENAS para resgatar a sessão se a RAM falhar.
    """
    # 1. Prioridade Máxima: Sessão na RAM
    if context.user_data and 'logged_player_id' in context.user_data:
        return str(context.user_data['logged_player_id'])

    # 2. Resgate: Se a RAM sumiu, busca o User ID vinculado ao Telegram ID
    if update.effective_user and users_collection is not None:
        tg_id = update.effective_user.id
        try:
            # Busca o documento para recuperar o _id real
            user = users_collection.find_one({"telegram_id_owner": tg_id}, {"_id": 1})
            if user:
                user_id_mongo = str(user["_id"])
                # Restaura na RAM para os próximos cliques
                context.user_data['logged_player_id'] = user_id_mongo
                return user_id_mongo
        except Exception as e:
            logger.error(f"Erro no resgate de sessão: {e}")

    return None

def requires_login(func):
    """Protege funções garantindo que o User ID seja recuperado."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = get_current_player_id(update, context)
        if not user_id:
            if update.callback_query:
                await update.callback_query.answer("⚠️ Conta não identificada. Use /start.", show_alert=True)
                return
            if update.message:
                await update.message.reply_text("⛔ Digite /start para acessar sua conta.")
                return
        return await func(update, context, *args, **kwargs)
    return wrapper