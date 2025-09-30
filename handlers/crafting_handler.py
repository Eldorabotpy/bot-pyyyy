# handlers/crafting_handler.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

logger = logging.getLogger(__name__)

# tenta importar o menu real da forja com alguns nomes comuns
CRAFT_IMPL = None
try:
    # 1) se você tem menu/crafting.py
    from .menu.crafting import show_crafting_menu as CRAFT_IMPL  # type: ignore
except Exception:
    try:
        # 2) se você usa crafting_handler com função craft_main/craft_open
        from .crafting_handler import craft_main as CRAFT_IMPL  # type: ignore
    except Exception:
        try:
            from .crafting_handler import craft_open as CRAFT_IMPL  # type: ignore
        except Exception:
            CRAFT_IMPL = None

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception:
        pass
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception:
        pass
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

async def craft_open_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Roteia o callback do botão 'Forjar item' para a implementação real."""
    q = update.callback_query
    await q.answer()
    chat_id = q.message.chat.id

    if CRAFT_IMPL:
        # chama o menu real da forja
        try:
            await CRAFT_IMPL(update, context)
            return
        except Exception:
            logger.exception("Falha ao chamar a implementação real da Forja")
            # cai no fallback abaixo
    # fallback visual para não travar
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar", callback_data="navigate_reino_eldora")]
    ])
    await _safe_edit_or_send(q, context, chat_id, "⚒️ Forja: não encontrei o handler de craft configurado.", kb)

# Capture vários nomes possíveis usados no seu projeto
craft_open_handler = CallbackQueryHandler(
    craft_open_router,
    pattern=r'^(open_crafting|craft_main|craft_open|forge_craft)$'
)
