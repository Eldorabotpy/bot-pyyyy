# handlers/admin/pvp_panel_handler.py
# (VERSÃO FINAL E CORRIGIDA)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

# --- Importação do Banco de Dados para Operações em Massa ---
from modules.player.core import players_collection

# --- IMPORTANTE: Importa a nova lógica de reset robusta ---
# (Essa linha estava faltando no seu código!)
from pvp.pvp_scheduler import executar_reset_pvp

# --- Importar Jobs Antigos (Mantemos para tickets/rewards) ---
try:
    from handlers.daily_jobs import daily_pvp_entry_reset_job, daily_arena_ticket_job
except ImportError:
    from handlers.jobs import daily_pvp_entry_reset_job
    try:
        from handlers.jobs import daily_arena_ticket_job
    except ImportError:
         logging.error("NÃO FOI POSSÍVEL encontrar 'daily_arena_ticket_job'.")
         async def daily_arena_ticket_job(context: ContextTypes.DEFAULT_TYPE, force_run=False):
             raise ImportError("Função daily_arena_ticket_job não encontrada.")

from handlers.jobs import distribute_pvp_rewards

logger = logging.getLogger(__name__)

# --- Função Principal do Menu ---
async def admin_pvp_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = (
        "⚔️ <b>Painel de Controle de PvP</b> ⚔️\n\n"
        "Selecione uma ação manual para executar imediatamente.\n\n"
        "⚠️ <b>Atenção:</b> Estas ações afetam <u>todos</u> os jogadores."
    )
           
    keyboard = [
        [InlineKeyboardButton("🎫 0. Entregar Tickets de Arena", callback_data="admin_pvp_trigger_give_ticket")],
        [InlineKeyboardButton("🎟️ 1. Resetar Entradas (Contador)", callback_data="admin_pvp_trigger_tickets")],
        [InlineKeyboardButton("🏆 2. Entregar Prêmios da Temporada", callback_data="admin_pvp_trigger_rewards")],
        # Este botão agora chama a função NOVA e SEGURA
        [InlineKeyboardButton("🔄 3. Resetar Temporada (Completo)", callback_data="admin_pvp_trigger_reset")],
        [InlineKeyboardButton("💀 4. APENAS ZERAR PONTOS (Sem prêmios)", callback_data="admin_pvp_zero_points")],
        [InlineKeyboardButton("⬅️ Voltar ao Painel Admin", callback_data="admin_main")] 
    ]
    
    await query.edit_message_text(
        text=text, 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode="HTML"
    )

# --- Callbacks dos Botões ---

async def admin_trigger_pvp_give_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dispara manualmente o job de entregar 'ticket_arena'."""
    query = update.callback_query
    await query.answer("Processando...")
    try:
        await daily_arena_ticket_job(context, force_run=True)
        await query.edit_message_text("✅ <b>Tickets Entregues!</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Erro tickets pvp: {e}", exc_info=True)
        await query.edit_message_text(f"❌ Erro: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]))

async def admin_trigger_pvp_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dispara manualmente o reset de entradas diárias."""
    query = update.callback_query
    await query.answer("Processando...")
    try:
        await daily_pvp_entry_reset_job(context, force_run=True)
        await query.edit_message_text("✅ <b>Entradas Resetadas!</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Erro reset entradas: {e}", exc_info=True)
        await query.edit_message_text(f"❌ Erro: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]))

async def admin_trigger_pvp_rewards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dispara a entrega de prêmios."""
    query = update.callback_query
    await query.answer("Processando...")
    try:
        await distribute_pvp_rewards(context)
        await query.edit_message_text("✅ <b>Prêmios Distribuídos!</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Erro rewards pvp: {e}", exc_info=True)
        await query.edit_message_text(f"❌ Erro: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]))

async def admin_trigger_pvp_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Dispara o Reset de Temporada COMPLETO.
    Usa a nova função 'executar_reset_pvp' que é segura e atômica.
    """
    query = update.callback_query
    await query.answer("Iniciando Reset Completo...")
    
    try:
        # AQUI ESTÁ A MUDANÇA: Usamos a função nova do scheduler
        # force_run=True obriga a rodar mesmo não sendo dia 1º
        await executar_reset_pvp(context.bot, force_run=True)
        
        await query.edit_message_text(
            "✅ <b>Temporada Resetada com Sucesso!</b>\n"
            "Os prêmios foram entregues (Top 5) e todos os pontos foram zerados via MongoDB.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Erro reset season: {e}", exc_info=True)
        await query.edit_message_text(f"❌ Erro: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]))

async def admin_trigger_pvp_zero_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ação Drástica: Zera os pontos de TODOS sem dar prêmios."""
    query = update.callback_query
    
    if "confirm" not in query.data:
        await query.edit_message_text(
            "⚠️ <b>PERIGO: ZERAR PONTOS</b> ⚠️\n\n"
            "Isso vai definir <code>pvp_points = 0</code> para <b>TODOS</b>.\n"
            "Nenhum prêmio será entregue.\n\n"
            "Tem certeza?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ SIM, ZERAR TUDO", callback_data="admin_pvp_zero_points_confirm")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="admin_pvp_menu")]
            ]),
            parse_mode="HTML"
        )
        return

    await query.answer("Zerando pontos...")
    try:
        if players_collection is None: raise Exception("Sem banco de dados.")
        
        result = players_collection.update_many(
            {"pvp_points": {"$gt": 0}}, 
            {"$set": {"pvp_points": 0}}
        )
        
        await query.edit_message_text(
            f"💀 <b>HARD RESET CONCLUÍDO</b>\nJogadores zerados: <b>{result.modified_count}</b>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Erro ao zerar pontos pvp: {e}", exc_info=True)
        await query.edit_message_text(f"❌ Erro Crítico: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]))

# --- Lista de Handlers ---
admin_pvp_menu_handler = CallbackQueryHandler(admin_pvp_menu, pattern=r'^admin_pvp_menu$')
admin_trigger_pvp_tickets_handler = CallbackQueryHandler(admin_trigger_pvp_tickets, pattern=r'^admin_pvp_trigger_tickets$')
admin_trigger_pvp_rewards_handler = CallbackQueryHandler(admin_trigger_pvp_rewards, pattern=r'^admin_pvp_trigger_rewards$')
admin_trigger_pvp_reset_handler = CallbackQueryHandler(admin_trigger_pvp_reset, pattern=r'^admin_pvp_trigger_reset$')
admin_trigger_pvp_give_ticket_handler = CallbackQueryHandler(admin_trigger_pvp_give_ticket, pattern=r'^admin_pvp_trigger_give_ticket$')
admin_trigger_pvp_zero_points_handler = CallbackQueryHandler(admin_trigger_pvp_zero_points, pattern=r'^admin_pvp_zero_points')

pvp_panel_handlers = [
    admin_pvp_menu_handler,
    admin_trigger_pvp_tickets_handler,
    admin_trigger_pvp_rewards_handler,
    admin_trigger_pvp_reset_handler,
    admin_trigger_pvp_give_ticket_handler,
    admin_trigger_pvp_zero_points_handler,
]