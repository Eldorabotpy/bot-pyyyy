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
# Certifique-se de ter este utils ou ajuste para sua lógica de ID
from handlers.admin.utils import parse_hybrid_id
from modules import player_manager

logger = logging.getLogger(__name__)
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# --- Estados da Conversa ---
MAIN_MENU, ASKING_PLAYER_RESPEC, ASKING_PLAYER_IDLE, CONFIRM_ALL, CONFIRM_IDLE = range(5)

# ==============================================================================
# LÓGICA DE RESET (ASSÍNCRONA)
# ==============================================================================
async def _reset_points_one(p: dict) -> int:
    """Reseta status e devolve pontos (Async)."""
    try:
        # Usa await pois a função no player_manager é async
        refunded = await player_manager.reset_stats_and_refund_points(p)
        
        # Recalcula totais para corrigir HP/MP
        totals = await player_manager.get_player_total_stats(p)
        max_hp = int(totals.get("max_hp", p.get("max_hp", 50)))
        p["current_hp"] = max(1, min(int(p.get("current_hp", max_hp)), max_hp))
        
        return refunded
    except Exception as e:
        logger.error(f"Erro reset points one: {e}")
        return 0

# ==============================================================================
# HANDLERS (MENUS E AÇÕES)
# ==============================================================================

async def _entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Abre o menu de Reset."""
    query = update.callback_query
    if query:
        await query.answer()
    
    # Verifica Admin
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        if query: await query.edit_message_text("⛔ Acesso negado.")
        else: await update.message.reply_text("⛔ Acesso negado.")
        return ConversationHandler.END

    text = "🔧 **PAINEL DE RESET & DEBUG**\n\nSelecione o tipo de operação:"
    kb = [
        [InlineKeyboardButton("🔄 Resetar Status (Pontos)", callback_data="reset_action_points")],
        [InlineKeyboardButton("⚔️ Resetar Classe", callback_data="reset_action_class")],
        [InlineKeyboardButton("⚒️ Resetar Profissão", callback_data="reset_action_prof")],
        [InlineKeyboardButton("💤 Limpar Estado (Idle Fix)", callback_data="reset_action_idle")],
        [InlineKeyboardButton("⚠️ RESET GLOBAL (TODOS)", callback_data="reset_action_points_all")],
        [InlineKeyboardButton("🔙 Fechar", callback_data="reset_back_to_main")]
    ]
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        
    return MAIN_MENU

async def _ask_player_for_respec(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pede o ID/Nome do jogador para resetar."""
    query = update.callback_query
    await query.answer()
    
    action = query.data  # ex: reset_action_points
    context.user_data['reset_action'] = action
    
    readable = "Status"
    if "class" in action: readable = "Classe"
    if "prof" in action: readable = "Profissão"

    text = f"👤 **Resetar {readable}**\n\nDigite o **ID Numérico**, **@Username** ou **Nome** do jogador:"
    kb = [[InlineKeyboardButton("🔙 Cancelar", callback_data="reset_back_to_main")]]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    return ASKING_PLAYER_RESPEC

async def _ask_player_for_idle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pede o ID para limpar estado travado."""
    query = update.callback_query
    await query.answer()
    context.user_data['reset_action'] = "idle_fix"
    
    text = "💤 **Limpar Estado (Anti-Bug)**\n\nDigite o **ID Numérico** ou **@Username** do jogador travado:"
    kb = [[InlineKeyboardButton("🔙 Cancelar", callback_data="reset_back_to_main")]]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    return ASKING_PLAYER_IDLE

# --- EXECUÇÃO DO RESET INDIVIDUAL ---
async def _receive_player_for_respec(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text_input = update.message.text.strip()
    action = context.user_data.get('reset_action')
    
    # Busca Jogador
    target_id = parse_hybrid_id(text_input)
    if not target_id:
        # Tenta buscar por nome se o ID falhar
        from modules.player.queries import find_player_by_name_norm
        found = await find_player_by_name_norm(text_input)
        if found:
            target_id = found[0]

    pdata = await player_manager.get_player_data(target_id)
    if not pdata:
        await update.message.reply_text("❌ Jogador não encontrado. Tente o ID numérico.")
        return ASKING_PLAYER_RESPEC

    # Executa a ação
    msg_result = ""
    
    if action == "reset_action_points":
        refunded = await _reset_points_one(pdata)
        msg_result = f"✅ Status resetados! {refunded} pontos devolvidos."
        
    elif action == "reset_action_class":
        # Remove classe e devolve pontos
        pdata["class"] = None
        pdata["class_key"] = None
        pdata["subclass"] = None
        # Opcional: Resetar skills também
        await _reset_points_one(pdata)
        msg_result = "✅ Classe removida e pontos resetados."

    elif action == "reset_action_prof":
        pdata["profession"] = {}
        pdata["profession_xp"] = 0
        msg_result = "✅ Profissão zerada."

    # Salva
    await player_manager.save_player_data(target_id, pdata)
    
    await update.message.reply_text(
        f"{msg_result}\n👤 Jogador: {pdata.get('character_name')}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar", callback_data="reset_back_to_main")]])
    )
    return MAIN_MENU

# --- EXECUÇÃO DO IDLE FIX ---
async def _receive_player_for_idle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text_input = update.message.text.strip()
    target_id = parse_hybrid_id(text_input)
    
    pdata = await player_manager.get_player_data(target_id)
    if not pdata:
        await update.message.reply_text("❌ Jogador não encontrado.")
        return ASKING_PLAYER_IDLE

    pdata["player_state"] = {"action": "idle"}
    await player_manager.save_player_data(target_id, pdata)
    
    await update.message.reply_text(
        f"✅ Estado forçado para **IDLE**.\n👤 {pdata.get('character_name')}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar", callback_data="reset_back_to_main")]])
    )
    return MAIN_MENU

# --- RESET GLOBAL (CUIDADO) ---
async def _reset_all_points_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    text = "⚠️ **PERIGO: RESET GLOBAL** ⚠️\n\nIsso irá resetar os status de **TODOS** os jogadores do banco de dados.\nTem certeza absoluta?"
    kb = [
        [InlineKeyboardButton("✅ SIM, RESETAR TUDO", callback_data="reset_execute_points_all")],
        [InlineKeyboardButton("🔙 NÃO! Cancelar", callback_data="reset_back_to_main")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    return CONFIRM_ALL

async def _reset_all_points_execute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⏳ Iniciando reset global... Isso pode demorar.")
    
    count = 0
    async for uid, pdata in player_manager.iter_players():
        try:
            await _reset_points_one(pdata)
            await player_manager.save_player_data(uid, pdata)
            count += 1
        except: pass
        
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"✅ **Reset Global Concluído!**\n\nTotal de jogadores afetados: {count}"
    )
    return ConversationHandler.END

# --- CANCELAR / FECHAR ---
async def _cancel_op(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query: 
        await query.answer()
        await query.delete_message()
    else:
        await update.message.reply_text("Operação fechada.")
    return ConversationHandler.END

# ==============================================================================
# CONFIGURAÇÃO DO CONVERSATION HANDLER
# ==============================================================================
reset_panel_conversation_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(_entry_point, pattern=r'^admin_reset_panel$')],
    states={
        MAIN_MENU: [
            CallbackQueryHandler(_ask_player_for_idle_reset, pattern=r'^reset_action_idle$'),
            CallbackQueryHandler(_ask_player_for_respec, pattern=r'^(reset_action_points|reset_action_class|reset_action_prof)$'),
            CallbackQueryHandler(_reset_all_points_confirm, pattern=r'^reset_action_points_all$'),
            CallbackQueryHandler(_cancel_op, pattern=r'^reset_back_to_main$'),
        ],
        ASKING_PLAYER_RESPEC: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, _receive_player_for_respec),
            CallbackQueryHandler(_entry_point, pattern=r'^reset_back_to_main$'),
        ],
        ASKING_PLAYER_IDLE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, _receive_player_for_idle_reset),
            CallbackQueryHandler(_entry_point, pattern=r'^reset_back_to_main$'),
        ],
        CONFIRM_ALL: [
            CallbackQueryHandler(_reset_all_points_execute, pattern=r'^reset_execute_points_all$'),
            CallbackQueryHandler(_entry_point, pattern=r'^reset_back_to_main$'),
        ],
        CONFIRM_IDLE: [ # Estado reserva caso implemente confirmação de idle no futuro
            CallbackQueryHandler(_entry_point, pattern=r'^reset_back_to_main$'),
        ]
    },
    fallbacks=[
        CommandHandler('cancel', _cancel_op),
        CallbackQueryHandler(_cancel_op, pattern=r'^reset_back_to_main$')
    ],
    per_chat=True
)