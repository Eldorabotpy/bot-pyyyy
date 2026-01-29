# handlers/action_lock_handler.py
# Middleware de bloqueio global por ação em andamento (LOCK TOTAL)

from telegram import Update
from telegram.ext import (
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from modules.action_guard import guard_or_notify


async def block_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    allowed = await guard_or_notify(update, context)
    if not allowed:
        return


async def block_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    allowed = await guard_or_notify(update, context)
    if not allowed:
        return


# 🔒 CALLBACKS — SEM pattern (captura absolutamente tudo)
action_lock_callback_handler = CallbackQueryHandler(
    block_callbacks,
    block=True
)

# 🔒 MENSAGENS / COMANDOS
action_lock_message_handler = MessageHandler(
    filters.ALL,
    block_messages,
    block=True
)
