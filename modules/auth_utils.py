# modules/auth_utils.py

import logging
from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from modules.player.core import users_collection #

logger = logging.getLogger(__name__)

def get_current_player_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str | None:
    """
    Retorna o User ID (Mongo _id) baseado estritamente na sessão ativa.
    O resgate automático por Telegram ID foi removido para permitir a troca de contas (Logout).
    """
    if context.user_data and 'logged_player_id' in context.user_data:
        return str(context.user_data['logged_player_id'])
    
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