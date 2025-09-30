# handlers/events/party_handler.py (FINAL)

import logging
from telegram.ext import (
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    CommandHandler,
)

from .party_actions import (
    party_create_callback,
    party_disband_callback,
    show_party_lobby,
    invite_response_callback,
    party_leave_callback,
)
from .party_conversation import (
    AWAITING_INVITEE_NAME,
    ask_for_invitee_name,
    send_invite_to_player,
    cancel_invite,
)

logger = logging.getLogger(__name__)


async def party_router_callback(update, context):
    query = update.callback_query
    if not query:
        return
    await query.answer()

    try:
        prefix, action_type, *params = (query.data or "").split("_")
    except ValueError:
        logger.error(f"Callback de grupo inválido: {query.data}")
        return

    actions = {
        "create": party_create_callback,
        "disband": party_disband_callback,
        "lobby": show_party_lobby,
        "accept": invite_response_callback,
        "decline": invite_response_callback,
        "leave": party_leave_callback,
    }

    fn = actions.get(action_type)
    if fn:
        await fn(update, context, params)
    else:
        logger.warning(f"Ação de grupo desconhecida: {action_type}")


# BOTÕES DE GRUPO
party_callback_handler = CallbackQueryHandler(
    party_router_callback,
    pattern=r"^party_(create|disband|lobby|accept|decline|leave)_"
)

# CONVERSA DE CONVITE — prioridade alta e per_message=True
invite_conversation_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(ask_for_invitee_name, pattern=r"^party_invite_")],
    states={
        AWAITING_INVITEE_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, send_invite_to_player)
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel_invite)],
    per_user=True,
    per_chat=True,
    per_message=True,   # <- evita problemas com callbacks em mensagens “antigas”
    allow_reentry=True,
)
