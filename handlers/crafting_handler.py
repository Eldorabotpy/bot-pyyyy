# handlers/crafting_handler.py

import logging

from telegram import (
    Update,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules.auth_utils import requires_login  # ✅ PROTEÇÃO DE ROTA

# --- Importação da Função de Destino ---
try:
    from .forge_handler import show_forge_professions_menu
    CRAFT_IMPL = show_forge_professions_menu
except ImportError:
    logging.getLogger(__name__).error(
        "CRITICAL: A função 'show_forge_professions_menu' não foi encontrada em 'handlers/forge_handler.py'."
    )
    CRAFT_IMPL = None

from modules import crafting_registry

logger = logging.getLogger(__name__)


async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    """
    Função utilitária para editar a mensagem se possível.
    """
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except Exception: pass
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except Exception: pass
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

# ✅ PROTEÇÃO ADICIONADA: Garante sessão antes de entrar na lógica da forja
@requires_login
async def craft_open_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback principal do botão 'Forjar item'.
    Redireciona para o menu de profissões.
    """
    query = update.callback_query
    try: await query.answer()
    except: pass

    if CRAFT_IMPL:
        try:
            # Chama o menu de profissões
            await CRAFT_IMPL(update, context)
            return 
        except Exception as e:
            logger.exception(f"Falha ao executar a implementação da forja (CRAFT_IMPL): {e}")

    # Fallback de erro
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar", callback_data="show_kingdom_menu")]
    ])
    error_text = "⚒️ **Erro na Forja** ⚒️\n\nNão foi possível iniciar o sistema de forja. Por favor, avise um administrador."
    
    await _safe_edit_or_send(query, context, query.message.chat.id, error_text, kb)

# --- Definição do Handler ---
craft_open_handler = CallbackQueryHandler(
    craft_open_callback, pattern="^open_crafting$"
)