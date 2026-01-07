# handlers/admin/reset_panel.py
# (VERSÃO CORRIGIDA: Await corrigido, Loop seguro e Navegação fluida)

from __future__ import annotations
import os
import logging
import asyncio
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
# HELPER: RECONSTRUÇÃO DO MENU ADMIN (Para o botão Voltar funcionar sem erro circular)
# ==============================================================================
def _get_admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 𝔼𝕟𝕥𝕣𝕖𝕘𝕒𝕣 𝕀𝕥𝕖𝕟𝕤", callback_data="admin_grant_item")],
        [InlineKeyboardButton("🛠️ 𝔾𝕖𝕣𝕒𝕣 𝔼𝕢𝕦𝕚𝕡𝕒𝕞𝕖𝕟𝕥𝕠", callback_data="admin_generate_equip")],
        [InlineKeyboardButton("📚 𝔼𝕟𝕤𝕚𝕟𝕒𝕣 𝕊𝕜𝕚𝕝𝕝", callback_data="admin_grant_skill")],
        [InlineKeyboardButton("🎨 𝔼𝕟𝕥𝕣𝕖𝕘𝕒𝕣 𝕊𝕜𝕚𝕟", callback_data="admin_grant_skin")],
        [InlineKeyboardButton("✏️ 𝐄𝐝𝐢𝐭𝐚𝐫 𝐉𝐨𝐠𝐚𝐝𝐨𝐫", callback_data="admin_edit_player")],
        [InlineKeyboardButton("👥 𝔾𝕖𝕣𝕖𝕟𝕔𝕚𝕒𝕣 𝕁𝕠𝕘𝕒𝕕𝕠𝕣𝕖𝕤", callback_data="admin_pmanage_main")],
        [InlineKeyboardButton("🚀 𝐌𝐈𝐆𝐑𝐀𝐑/CLONAR 𝐈𝐃", callback_data="admin_change_id_start")],
        [InlineKeyboardButton("🏚️ Limpar Clã Fantasma", callback_data="admin_fix_clan_start")],
        [InlineKeyboardButton("💀 𝐃𝐄𝐋𝐄𝐓𝐀𝐑 𝐂𝐎𝐍𝐓𝐀", callback_data="admin_delete_start")],
        [InlineKeyboardButton("🔁 𝔽𝕠𝕣ç𝕒𝕣 𝔻𝕚á𝕣𝕚𝕠𝕤", callback_data="admin_force_daily")],
        [InlineKeyboardButton("💎 𝐕𝐞𝐧𝐝𝐞𝐫 𝐆𝐞𝐦𝐚𝐬", callback_data="admin_sell_gems"),
        InlineKeyboardButton("🔥 Remover Gemas", callback_data="admin_remove_gems")],
        [InlineKeyboardButton("👑 ℙ𝕣𝕖𝕞𝕚𝕦𝕞", callback_data="admin_premium")],
        [InlineKeyboardButton("🎉 𝔾𝕖𝕣𝕖𝕟𝕔𝕚𝕒𝕣 𝔼𝕧𝕖𝕟𝕥𝕠𝕤", callback_data="admin_event_menu")],
        [InlineKeyboardButton("🔬 𝕋𝕖𝕤𝕥𝕖𝕤 𝕕𝕖 𝔼𝕧𝕖𝕟𝕥𝕠", callback_data="admin_test_menu")],
        [InlineKeyboardButton("📁 𝔾𝕖𝕣𝕖𝕟𝕔𝕚𝕒𝕣 𝔽𝕚𝕝𝕖 𝕀𝔻𝕤", callback_data="admin_file_ids")],
        [InlineKeyboardButton("🧹 ℝ𝕖𝕤𝕖𝕥/ℝ𝕖𝕤𝕡𝕖𝕔", callback_data="admin_reset_menu")],
        [InlineKeyboardButton("🧽 𝕃𝕚𝕞𝕡𝕒𝕣 ℂ𝕒𝕔𝕙𝕖", callback_data="admin_clear_cache")],
        [InlineKeyboardButton("ℹ️ 𝐀𝐣𝐮𝐝𝐚", callback_data="admin_help")]
    ])

# ==============================================================================
# LÓGICA DE RESET
# ==============================================================================
async def _reset_points_one(p: dict) -> int:
    try:
        # CORREÇÃO CRÍTICA: Adicionado 'await' pois a função no stats.py é async
        refunded = await reset_stats_and_refund_points(p)
        return refunded
    except Exception as e:
        logger.error(f"Erro reset points one: {e}")
        return 0

# ==============================================================================
# ENTRY POINTS
# ==============================================================================
async def _entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query: await query.answer()
    
    text = "🔧 **PAINEL DE RESET & DEBUG**\n\nSelecione o tipo de operação:"
    kb = [
        [InlineKeyboardButton("🔄 Resetar Status (Pontos)", callback_data="reset_action_points")],
        [InlineKeyboardButton("⚔️ Resetar Classe", callback_data="reset_action_class")],
        [InlineKeyboardButton("⚒️ Resetar Profissão", callback_data="reset_action_prof")],
        [InlineKeyboardButton("💤 Limpar Estado (Idle)", callback_data="reset_action_idle")],
        [InlineKeyboardButton("⚠️ RESET GLOBAL", callback_data="reset_action_points_all")],
        [InlineKeyboardButton("🔙 Voltar ao Menu Admin", callback_data="admin_main_return")]
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
        "👤 Digite o **ID**, **Nome** ou **@Username** para resetar:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="reset_back_to_main")]]),
        parse_mode="Markdown"
    )
    return ASKING_PLAYER_RESPEC

async def _ask_player_for_idle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "💤 Digite o **ID**, **Nome** ou **@Username** para forçar status IDLE:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="reset_back_to_main")]]),
        parse_mode="Markdown"
    )
    return ASKING_PLAYER_IDLE

# --- Busca e Execução ---
async def _process_target_input(update: Update) -> tuple[int | str | None, dict | None]:
    text_input = update.message.text.strip()
    
    # 1. Tenta ID Híbrido
    target_id = parse_hybrid_id(text_input)
    pdata = None

    if target_id:
        pdata = await get_player_data(target_id)
    
    # 2. Busca por nome/username
    if not pdata:
        found = await find_player_by_name(text_input)
        if found:
            target_id, pdata = found

    return target_id, pdata

async def _receive_player_for_respec(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    target_id, pdata = await _process_target_input(update)
    
    if not pdata:
        await update.message.reply_text("❌ Jogador não encontrado. Tente o @Username.")
        return ASKING_PLAYER_RESPEC

    action = context.user_data.get('reset_action')
    name = pdata.get('character_name', 'Unknown')
    msg = "Feito."

    if action == "reset_action_points":
        pts = await _reset_points_one(pdata)
        msg = f"✅ Status de **{name}** resetados.\nNível {pdata.get('level')}.\n💰 **{pts}** pontos devolvidos para redistribuição."
        
    elif action == "reset_action_class":
        # Limpa todos os dados de classe
        pdata['class'] = None
        pdata['class_key'] = None
        pdata['class_tier'] = 0
        pdata['subclass'] = None
        # Garante que o jogo ofereça a escolha novamente
        pdata['class_choice_offered'] = False
        
        # Reseta stats para o base (sem classe)
        pts = await _reset_points_one(pdata) 
        msg = f"✅ Classe de **{name}** removida.\nO jogador poderá escolher novamente ao logar.\nPontos resetados ({pts} devolvidos)."
        
    elif action == "reset_action_prof":
        pdata['profession'] = {}
        msg = f"✅ Profissão de **{name}** zerada."

    await save_player_data(target_id, pdata)
    
    await update.message.reply_text(
        msg, 
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Voltar", callback_data="admin_reset_menu")]]), 
        parse_mode="Markdown"
    )
    return MAIN_MENU

async def _receive_player_for_idle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    target_id, pdata = await _process_target_input(update)
    if not pdata:
        await update.message.reply_text("❌ Não encontrado.")
        return ASKING_PLAYER_IDLE
        
    pdata['player_state'] = {'action': 'idle'}
    await save_player_data(target_id, pdata)
    
    await update.message.reply_text(
        f"✅ **{pdata.get('character_name')}** agora está IDLE (Livre/Parado).", 
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Voltar", callback_data="admin_reset_menu")]]), 
        parse_mode="Markdown"
    )
    return MAIN_MENU

async def _reset_all_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    kb = [
        [InlineKeyboardButton("🚨 CONFIRMAR RESET GLOBAL 🚨", callback_data="do_reset_all")], 
        [InlineKeyboardButton("Cancelar", callback_data="admin_reset_menu")]
    ]
    await query.edit_message_text(
        "⚠️ **RESET GLOBAL DE PONTOS**\n"
        "Isso vai recalcular os pontos de **TODOS** os jogadores do banco de dados e devolver os pontos investidos.\n\n"
        "Isso pode levar algum tempo. Tem certeza?", 
        reply_markup=InlineKeyboardMarkup(kb), 
        parse_mode="Markdown"
    )
    return CONFIRM_ALL

async def _do_reset_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.edit_message_text("⏳ Processando Reset Global... (Isso não bloqueia o bot)")
    
    count = 0
    erros = 0
    try:
        # Iteração assíncrona (agora corrigida no queries.py)
        async for uid, pdata in iter_players():
            try:
                await _reset_points_one(pdata)
                await save_player_data(uid, pdata)
                count += 1
            except Exception as e_inner:
                logger.error(f"Erro ao resetar user {uid}: {e_inner}")
                erros += 1
                
            # Pausa a cada 50 jogadores para garantir estabilidade
            if count % 50 == 0:
                await asyncio.sleep(0.01)
                
        final_msg = f"✅ Reset Global finalizado.\n👥 Jogadores: {count}"
        if erros > 0:
            final_msg += f"\n⚠️ Falhas: {erros}"
            
    except Exception as e:
        logger.error(f"CRITICAL ERROR IN RESET ALL: {e}")
        final_msg = f"❌ Erro Crítico no Reset: {str(e)}"

    await context.bot.send_message(
        update.effective_chat.id, 
        final_msg,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Voltar ao Admin", callback_data="admin_main")]])
    )
    return ConversationHandler.END

async def _exit_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sai da conversa e mostra o menu principal de admin."""
    query = update.callback_query
    if query:
        await query.answer()
        # Mostra o menu principal novamente
        await query.edit_message_text(
            "🎛️ <b>Painel do Admin</b>\nEscolha uma opção:",
            reply_markup=_get_admin_main_kb(),
            parse_mode="HTML"
        )
    return ConversationHandler.END

# --- Handler ---
reset_panel_conversation_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(_entry_point, pattern=r'^admin_reset_menu$')],
    states={
        MAIN_MENU: [
            CallbackQueryHandler(_ask_player_for_respec, pattern=r'^reset_action_(points|class|prof)$'),
            CallbackQueryHandler(_ask_player_for_idle_reset, pattern=r'^reset_action_idle$'),
            CallbackQueryHandler(_reset_all_confirm, pattern=r'^reset_action_points_all$'),
            CallbackQueryHandler(_exit_to_admin, pattern=r'^admin_main_return$'), # Botão Voltar
            CallbackQueryHandler(_exit_to_admin, pattern=r'^admin_main$')        # Fallback se clicar no menu antigo
        ],
        ASKING_PLAYER_RESPEC: [MessageHandler(filters.TEXT & ~filters.COMMAND, _receive_player_for_respec)],
        ASKING_PLAYER_IDLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, _receive_player_for_idle_reset)],
        CONFIRM_ALL: [
            CallbackQueryHandler(_do_reset_all, pattern=r'^do_reset_all$'), 
            CallbackQueryHandler(_entry_point, pattern=r'^admin_reset_menu$')
        ]
    },
    fallbacks=[
        CommandHandler('cancel', _exit_to_admin), 
        CallbackQueryHandler(_entry_point, pattern=r'^reset_back_to_main$'),
        CallbackQueryHandler(_exit_to_admin, pattern=r'^admin_main$')
    ],
    per_chat=True
)