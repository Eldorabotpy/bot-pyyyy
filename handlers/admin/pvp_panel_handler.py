# handlers/admin/pvp_panel_handler.py
# (VERSÃO CORRIGIDA - Chama a função CERTA)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

# --- 1. Importar as Funções de Job ---
try:
    # Importa o reset de entradas E o NOVO job de ticket de arena
    from handlers.daily_jobs import daily_pvp_entry_reset_job, daily_arena_ticket_job
except ImportError:
    # Fallback 
    from handlers.jobs import daily_pvp_entry_reset_job
    try:
        from handlers.jobs import daily_arena_ticket_job
    except ImportError:
         logging.error("NÃO FOI POSSÍVEL encontrar 'daily_arena_ticket_job'. O botão falhará.")
         async def daily_arena_ticket_job(context: ContextTypes.DEFAULT_TYPE):
             raise ImportError("Função daily_arena_ticket_job não encontrada.")

from handlers.jobs import distribute_pvp_rewards, reset_pvp_season
# (Já não precisamos de 'daily_event_ticket_job' aqui)

logger = logging.getLogger(__name__)

# --- Função Principal do Menu (Correta) ---
async def admin_pvp_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "⚔️ <b>Painel de Controle de PvP</b> ⚔️\n\n" \
           "Selecione uma ação manual para executar imediatamente.\n\n" \
           "<b>Atenção:</b> Estas ações afetam <u>todos</u> os jogadores."
           
    keyboard = [
        [InlineKeyboardButton("🎫 0. Entregar Tickets de Arena", callback_data="admin_pvp_trigger_give_ticket")],
        [InlineKeyboardButton("🎟️ 1. Resetar Entradas (Contador)", callback_data="admin_pvp_trigger_tickets")],
        [InlineKeyboardButton("🏆 2. Entregar Prêmios da Temporada", callback_data="admin_pvp_trigger_rewards")],
        [InlineKeyboardButton("🔄 3. Resetar Temporada (!! CUIDADO !!)", callback_data="admin_pvp_trigger_reset")],
        [InlineKeyboardButton("⬅️ Voltar ao Painel Admin", callback_data="admin_panel")] 
    ]
    
    await query.edit_message_text(
        text=text, 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode="HTML"
    )

# --- Callbacks dos Botões (Corrigidos) ---

async def admin_trigger_pvp_give_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dispara manualmente o job de entregar 'ticket_arena', forçando a execução."""
    query = update.callback_query
    await query.answer("Iniciando job: FORÇAR Entrega de Tickets...")
    admin_id = query.from_user.id
    logger.info(f"Admin {admin_id} disparou 'daily_arena_ticket_job' (FORÇADO).") 
    
    try:
        # <<< CORREÇÃO APLICADA: Passa force_run=True >>>
        await daily_arena_ticket_job(context, force_run=True) 
        
        await query.edit_message_text(
            "✅ <b>Job Forçado Concluído!</b>\n"
            "Os <b>Tickets de Arena</b> foram (re)entregues a todos os jogadores elegíveis.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Painel PvP", callback_data="admin_pvp_menu")]]),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Erro ao forçar 'daily_arena_ticket_job': {e}", exc_info=True) 
        await query.edit_message_text(
            f"❌ <b>Erro ao executar job:</b>\n<code>{e}</code>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Painel PvP", callback_data="admin_pvp_menu")]]),
            parse_mode="HTML"
        )

async def admin_trigger_pvp_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dispara manualmente o job de resetar entradas diárias, forçando a execução."""
    query = update.callback_query
    await query.answer("Iniciando job: FORÇAR Reset de Entradas...")
    admin_id = query.from_user.id
    logger.info(f"Admin {admin_id} disparou 'daily_pvp_entry_reset_job' (FORÇADO).")
    
    try:
        # <<< CORREÇÃO APLICADA: Passa force_run=True >>>
        await daily_pvp_entry_reset_job(context, force_run=True)
        
        await query.edit_message_text(
            "✅ <b>Job Forçado Concluído!</b>\n"
            "As entradas diárias de PvP (contador) foram (re)resetadas para todos.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]),
            parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Erro ao forçar 'daily_pvp_entry_reset_job': {e}", exc_info=True)
        await query.edit_message_text(
            f"Erro ao executar job: {e}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]),
            parse_mode="HTML"
            )
        
async def admin_trigger_pvp_rewards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dispara manualmente a distribuição de prêmios da temporada."""
    query = update.callback_query
    await query.answer("Iniciando job: Entregar Prêmios da Temporada...")
    admin_id = query.from_user.id
    logger.info(f"Admin {admin_id} disparou 'distribute_pvp_rewards' manualmente.")
    
    try:
        await distribute_pvp_rewards(context)
        await query.edit_message_text(
            "✅ Job 'Entregar Prêmios da Temporada' executado com sucesso!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]))
    except Exception as e:
        logger.error(f"Erro ao disparar 'distribute_pvp_rewards': {e}", exc_info=True)
        await query.edit_message_text(
            f"Erro ao executar job: {e}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]))

async def admin_trigger_pvp_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dispara manualmente o reset da temporada PvP."""
    query = update.callback_query
    await query.answer("Iniciando job: Resetar Temporada PvP...")
    admin_id = query.from_user.id
    logger.info(f"Admin {admin_id} disparou 'reset_pvp_season' manualmente.")
    
    try:
        await reset_pvp_season(context)
        await query.edit_message_text(
            "✅ Job 'Resetar Temporada PvP' executado com sucesso!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]))
    except Exception as e:
        logger.error(f"Erro ao disparar 'reset_pvp_season': {e}", exc_info=True)
        await query.edit_message_text(
            f"Erro ao executar job: {e}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]))


# --- Lista de Handlers (Correta) ---
admin_pvp_menu_handler = CallbackQueryHandler(admin_pvp_menu, pattern=r'^admin_pvp_menu$')
admin_trigger_pvp_tickets_handler = CallbackQueryHandler(admin_trigger_pvp_tickets, pattern=r'^admin_pvp_trigger_tickets$')
admin_trigger_pvp_rewards_handler = CallbackQueryHandler(admin_trigger_pvp_rewards, pattern=r'^admin_pvp_trigger_rewards$')
admin_trigger_pvp_reset_handler = CallbackQueryHandler(admin_trigger_pvp_reset, pattern=r'^admin_pvp_trigger_reset$')
admin_trigger_pvp_give_ticket_handler = CallbackQueryHandler(admin_trigger_pvp_give_ticket, pattern=r'^admin_pvp_trigger_give_ticket$')

pvp_panel_handlers = [
    admin_pvp_menu_handler,
    admin_trigger_pvp_tickets_handler,
    admin_trigger_pvp_rewards_handler,
    admin_trigger_pvp_reset_handler,
    admin_trigger_pvp_give_ticket_handler, # (A tua lista já estava correta aqui)
]