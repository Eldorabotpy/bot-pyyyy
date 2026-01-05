from __future__ import annotations
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CommandHandler,
)
from handlers.admin.utils import parse_hybrid_id
from modules import player_manager
from modules.player.core import get_player_data, save_player_data
from modules.player.queries import find_player_by_name
from modules.auth_utils import get_current_player_id

logger = logging.getLogger(__name__)
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# --- Estados ---
MAIN_MENU, ASKING_PLAYER_RESPEC, ASKING_PLAYER_IDLE, CONFIRM_ALL, CONFIRM_IDLE = range(5)

# --- Lógica Reset ---
async def _reset_points_one(p: dict) -> int:
    try:
        # Chama a função do stats.py que faz o cálculo limpo
        refunded = await player_manager.reset_stats_and_refund_points(p)
        return refunded
    except Exception as e:
        logger.error(f"Erro reset points one: {e}")
        return 0

# --- Entry Points ---
async def _entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query: await query.answer()
    
    # Validação simples de admin
    if get_current_player_id(update, context) != ADMIN_ID:
        # Se preferir usar ensure_admin do utils, pode importar e usar
        pass 

    text = "🔧 **PAINEL DE RESET & DEBUG**\n\nSelecione o tipo de operação:"
    kb = [
        [InlineKeyboardButton("🔄 Resetar Status (Pontos)", callback_data="reset_action_points")],
        [InlineKeyboardButton("⚔️ Resetar Classe", callback_data="reset_action_class")],
        [InlineKeyboardButton("⚒️ Resetar Profissão", callback_data="reset_action_prof")],
        [InlineKeyboardButton("💤 Limpar Estado (Idle)", callback_data="reset_action_idle")],
        [InlineKeyboardButton("⚠️ RESET GLOBAL", callback_data="reset_action_points_all")],
        [InlineKeyboardButton("🔙 Voltar", callback_data="admin_main")]
    ]
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    return MAIN_MENU

async def _ask_player_for_respec(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['reset_action'] = query.data
    
    await query.edit_message_text(
        "👤 Digite o **ID** ou **Nome do Personagem** para resetar:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="reset_back_to_main")]]),
        parse_mode="Markdown"
    )
    return ASKING_PLAYER_RESPEC

async def _ask_player_for_idle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "💤 Digite o **ID** ou **Nome** para forçar status IDLE:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="reset_back_to_main")]]),
        parse_mode="Markdown"
    )
    return ASKING_PLAYER_IDLE

# --- Busca e Execução ---
async def _process_target_input(update: Update) -> tuple[int | None, dict | None]:
    text_input = update.message.text.strip()
    target_id = parse_hybrid_id(text_input)
    pdata = None

    if target_id:
        pdata = await get_player_data(target_id)
    
    if not pdata:
        found = await find_player_by_name(text_input)
        if found:
            target_id, pdata = found

    return target_id, pdata

async def _receive_player_for_respec(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    target_id, pdata = await _process_target_input(update)
    
    if not pdata:
        await update.message.reply_text("❌ Jogador não encontrado.")
        return ASKING_PLAYER_RESPEC

    action = context.user_data.get('reset_action')
    name = pdata.get('character_name', 'Unknown')
    msg = "Feito."

    if action == "reset_action_points":
        pts = await _reset_points_one(pdata)
        msg = f"✅ Status de **{name}** resetados. {pts} pontos devolvidos."
        
    elif action == "reset_action_class":
        pdata['class'] = None
        pdata['class_key'] = None
        await _reset_points_one(pdata) # Reseta pontos ao tirar classe
        msg = f"✅ Classe de **{name}** removida."
        
    elif action == "reset_action_prof":
        pdata['profession'] = {}
        msg = f"✅ Profissão de **{name}** zerada."

    await save_player_data(target_id, pdata)
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Voltar", callback_data="admin_reset_panel")]]))
    return MAIN_MENU

async def _receive_player_for_idle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    target_id, pdata = await _process_target_input(update)
    if not pdata:
        await update.message.reply_text("❌ Não encontrado.")
        return ASKING_PLAYER_IDLE
        
    pdata['player_state'] = {'action': 'idle'}
    await save_player_data(target_id, pdata)
    await update.message.reply_text(f"✅ **{pdata.get('character_name')}** agora está IDLE.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Voltar", callback_data="admin_reset_panel")]]), parse_mode="Markdown")
    return MAIN_MENU

async def _reset_all_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    kb = [[InlineKeyboardButton("CONFIRMAR RESET GLOBAL", callback_data="do_reset_all")], [InlineKeyboardButton("Cancelar", callback_data="admin_reset_panel")]]
    await query.edit_message_text("⚠️ **RESET GLOBAL**\nResetar status de TODOS os jogadores?\nIsso não pode ser desfeito.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    return CONFIRM_ALL

async def _do_reset_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.edit_message_text("⏳ Processando... (Isso pode demorar)")
    c = 0
    from modules.player.queries import iter_players
    async for uid, pdata in iter_players():
        await _reset_points_one(pdata)
        await save_player_data(uid, pdata)
        c += 1
    await context.bot.send_message(update.effective_chat.id, f"✅ Reset Global finalizado. {c} jogadores processados.")
    return ConversationHandler.END

async def _cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query: await update.callback_query.edit_message_text("Cancelado.")
    return ConversationHandler.END

# --- Handler ---
reset_panel_conversation_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(_entry_point, pattern=r'^admin_reset_panel$')],
    states={
        MAIN_MENU: [
            CallbackQueryHandler(_ask_player_for_respec, pattern=r'^reset_action_(points|class|prof)$'),
            CallbackQueryHandler(_ask_player_for_idle_reset, pattern=r'^reset_action_idle$'),
            CallbackQueryHandler(_reset_all_confirm, pattern=r'^reset_action_points_all$'),
            CallbackQueryHandler(_cancel, pattern=r'^admin_main$') # Voltar ao menu principal
        ],
        ASKING_PLAYER_RESPEC: [MessageHandler(filters.TEXT & ~filters.COMMAND, _receive_player_for_respec)],
        ASKING_PLAYER_IDLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, _receive_player_for_idle_reset)],
        CONFIRM_ALL: [CallbackQueryHandler(_do_reset_all, pattern=r'^do_reset_all$'), CallbackQueryHandler(_entry_point, pattern=r'^admin_reset_panel$')]
    },
    fallbacks=[CommandHandler('cancel', _cancel), CallbackQueryHandler(_cancel, pattern=r'^reset_back_to_main$')],
    per_chat=True
)