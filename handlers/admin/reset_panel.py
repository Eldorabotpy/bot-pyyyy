# handlers/admin/reset_panel.py
# (VERSÃO CORRIGIDA: Import asyncio adicionado)

from __future__ import annotations
import os
import logging
import asyncio  # <--- FALTAVA ISSO AQUI
from bson import ObjectId
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

# Imports do Core e Queries
from modules.player.core import get_player_data, save_player_data
from modules.player.queries import find_player_by_name, iter_players

# IMPORTE DIRETO DA MATEMÁTICA
from modules.player.stats import reset_stats_and_refund_points

logger = logging.getLogger(__name__)
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# --- Estados ---
MAIN_MENU, ASKING_PLAYER_RESPEC, ASKING_PLAYER_IDLE, CONFIRM_ALL, CONFIRM_IDLE = range(5)

# ==============================================================================
# LÓGICA DE RESET
# ==============================================================================
async def _reset_points_one(p: dict) -> int:
    """
    Executa o reset matemático em um dicionário de jogador.
    Retorna a quantidade de pontos devolvidos.
    """
    try:
        # A função no stats.py é ASYNC.
        # Tem que usar await, senão retorna um objeto coroutine e nada acontece.
        refunded = await reset_stats_and_refund_points(p)
        return refunded
    except Exception as e:
        logger.error(f"Erro reset points one: {e}", exc_info=True)
        return 0

# ==============================================================================
# ENTRY POINTS
# ==============================================================================
async def _entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query: await query.answer()
    
    text = "🔧 **PAINEL DE RESET & DEBUG (Users System)**\n\nSelecione o tipo de operação:"
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
        "👤 Digite o **ID (Novo/Antigo)** ou **Nome do Personagem** para resetar:",
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
async def _process_target_input(update: Update) -> tuple[int | str | None, dict | None]:
    text_input = update.message.text.strip()
    
    # 1. Tenta ID direto (ObjectId ou Int)
    target_id = None
    pdata = None

    # Verifica se é ObjectId válido (Sistema Users)
    if ObjectId.is_valid(text_input):
        target_id = str(text_input) # Mantém como str para o core lidar
        pdata = await get_player_data(target_id)
    
    # Verifica se é int (Sistema Antigo)
    elif text_input.isdigit():
        target_id = int(text_input)
        pdata = await get_player_data(target_id)
        # Se não achou como int, tenta como string (caso raro de ID numérico no sistema novo)
        if not pdata:
            pdata = await get_player_data(str(target_id))
            if pdata: target_id = str(target_id)

    # 2. Se falhar por ID, tenta por Nome
    if not pdata:
        found = await find_player_by_name(text_input)
        if found:
            target_id, pdata = found

    return target_id, pdata

async def _receive_player_for_respec(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    target_id, pdata = await _process_target_input(update)
    
    if not pdata:
        await update.message.reply_text("❌ Jogador não encontrado no banco (Users ou Legacy).")
        return ASKING_PLAYER_RESPEC

    action = context.user_data.get('reset_action')
    name = pdata.get('character_name', 'Unknown')
    msg = "Feito."

    try:
        if action == "reset_action_points":
            pts = await _reset_points_one(pdata)
            msg = f"✅ Status de **{name}** resetados.\nFoi recalculado para o Nível {pdata.get('level')}.\n💰 **{pts}** pontos devolvidos."
            
        elif action == "reset_action_class":
            pdata['class'] = None
            pdata['class_key'] = None
            # Ao tirar classe, reseta pontos também para evitar status base fantasma
            pts = await _reset_points_one(pdata) 
            msg = f"✅ Classe de **{name}** removida.\nPontos resetados ({pts} devolvidos)."
            
        elif action == "reset_action_prof":
            pdata['profession'] = {}
            msg = f"✅ Profissão de **{name}** zerada."

        # Salva as alterações
        await save_player_data(target_id, pdata)
        
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Voltar", callback_data="admin_reset_panel")]]), parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Erro no reset handler: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Erro ao processar: {e}")

    return MAIN_MENU

async def _receive_player_for_idle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    target_id, pdata = await _process_target_input(update)
    if not pdata:
        await update.message.reply_text("❌ Não encontrado.")
        return ASKING_PLAYER_IDLE
        
    pdata['player_state'] = {'action': 'idle'}
    await save_player_data(target_id, pdata)
    
    await update.message.reply_text(f"✅ **{pdata.get('character_name')}** agora está IDLE (Livre).", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Voltar", callback_data="admin_reset_panel")]]), parse_mode="Markdown")
    return MAIN_MENU

async def _reset_all_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    kb = [[InlineKeyboardButton("CONFIRMAR RESET GLOBAL", callback_data="do_reset_all")], [InlineKeyboardButton("Cancelar", callback_data="admin_reset_panel")]]
    await query.edit_message_text("⚠️ **RESET GLOBAL**\nIsso vai recalcular os pontos de TODOS os jogadores baseados no nível atual.\n\nTem certeza?", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    return CONFIRM_ALL

async def _do_reset_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.edit_message_text("⏳ Processando Reset Global... (Isso pode demorar)")
    
    count = 0
    try:
        # Usa o iterador otimizado do queries.py
        async for uid, pdata in iter_players():
            await _reset_points_one(pdata)
            await save_player_data(uid, pdata)
            count += 1
            if count % 50 == 0:
                await asyncio.sleep(0.01) # Cede o controle para não travar o bot
                
        await context.bot.send_message(update.effective_chat.id, f"✅ Reset Global finalizado.\n{count} jogadores processados.")
    except Exception as e:
        logger.error(f"Erro no global reset: {e}")
        await context.bot.send_message(update.effective_chat.id, f"❌ Erro no Reset Global: {e}")
        
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