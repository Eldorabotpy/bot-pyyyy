# handlers/action_lock_handler.py
# Firewall global: se player_state.action != idle, BLOQUEIA TUDO

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


# ✅ SEM pattern = pega absolutamente todos os callbacks
action_lock_callback_handler = CallbackQueryHandler(
    block_callbacks,
    block=True
)

action_lock_message_handler = MessageHandler(
    filters.ALL,
    block_messages,
    block=True
)
