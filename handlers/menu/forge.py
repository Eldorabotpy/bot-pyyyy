from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
import logging

logger = logging.getLogger(__name__)

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    """
    Função utilitária para editar a mensagem se possível (caption ou texto),
    ou enviar uma nova se a edição falhar.
    """
    try:
        # Tenta editar a legenda da mensagem (se for uma foto)
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except Exception:
        pass
    try:
        # Tenta editar o texto da mensagem (se for só texto)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except Exception:
        pass
    # Se a edição falhar, envia uma nova mensagem (fallback)
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

async def show_forge_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Abre e exibe o menu principal da Forja com as opções: Forjar Item, Refino e Voltar.
    """
    q = getattr(update, "callback_query", None)

    # 1. Definição dos botões
    # ATENÇÃO: O botão "Forjar item" agora usa um callback diferente ("open_crafting")
    # que deve ser capturado pelo `craft_open_handler` em handlers/crafting_handler.py
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔨 𝐅𝐨𝐫𝐣𝐚𝐫 𝐢𝐭𝐞𝐦", callback_data="open_crafting")],
        [InlineKeyboardButton("🧪 𝐑𝐞𝐟𝐢𝐧𝐨", callback_data="refining_main")],
        [InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="show_kingdom_menu")],
    ])
    
    text = "⚒️ 𝐅𝐨𝐫𝐣𝐚 𝐝𝐞 𝐄𝐥𝐝𝐨𝐫𝐚\n𝑬𝒔𝒄𝒐𝒍𝒉𝒂 𝒖𝒎𝒂 𝒐𝒑𝒄̧𝒂̃𝒐:"

    # 2. Resposta e envio da mensagem
    if q:
        # Confirma o recebimento do clique, crucial para a performance
        await q.answer()
        chat_id = q.message.chat_id
        await _safe_edit_or_send(q, context, chat_id, text, kb)
    else:
        # Caso seja chamado diretamente por um comando (ex: /forge)
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

# 3. Definição do Handler
# Este handler é responsável por ABRIR o menu da forja (show_forge_menu) 
# quando o callback "forge:main" é recebido (ex: do menu do Reino).
forge_menu_handler = CallbackQueryHandler(
    show_forge_menu,
    # O padrão agora está dedicado a responder ao botão que abre este menu.
    pattern=r'^(forge:main)$'
)