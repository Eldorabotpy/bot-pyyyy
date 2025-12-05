# handlers/admin/pvp_panel_handler.py
# (VERSÃO ATUALIZADA: Com opção de ZERAR PONTOS MANUALMENTE)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

# --- Importação do Banco de Dados para Operações em Massa ---
from modules.player.core import players_collection

# --- 1. Importar as Funções de Job ---
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

from handlers.jobs import distribute_pvp_rewards, reset_pvp_season

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
        [InlineKeyboardButton("🔄 3. Resetar Temporada (Completo)", callback_data="admin_pvp_trigger_reset")],
        # --- NOVO BOTÃO ---
        [InlineKeyboardButton("💀 4. APENAS ZERAR PONTOS (Sem prêmios)", callback_data="admin_pvp_zero_points")],
        # ------------------
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
        await query.edit_message_text(
            "✅ <b>Tickets Entregues!</b>\nTodos os jogadores receberam seus tickets de arena.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Erro tickets pvp: {e}", exc_info=True)
        await query.edit_message_text(f"❌ Erro: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]))

async def admin_trigger_pvp_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dispara manualmente o reset de entradas diárias."""
    query = update.callback_query
    await query.answer("Processando...")
    
    try:
        await daily_pvp_entry_reset_job(context, force_run=True)
        await query.edit_message_text(
            "✅ <b>Entradas Resetadas!</b>\nO contador de lutas diárias foi zerado.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Erro reset entradas: {e}", exc_info=True)
        await query.edit_message_text(f"❌ Erro: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]))

async def admin_trigger_pvp_rewards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dispara a entrega de prêmios."""
    query = update.callback_query
    await query.answer("Processando...")
    
    try:
        await distribute_pvp_rewards(context)
        await query.edit_message_text(
            "✅ <b>Prêmios Distribuídos!</b>\nVerifique os logs para detalhes dos vencedores.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Erro rewards pvp: {e}", exc_info=True)
        await query.edit_message_text(f"❌ Erro: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]))

async def admin_trigger_pvp_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dispara o Reset de Temporada (Geralmente Prêmios + Zerar)."""
    query = update.callback_query
    await query.answer("Iniciando Reset Completo...")
    
    try:
        # Chama a função que você já tem no handlers/jobs.py
        await reset_pvp_season(context)
        
        await query.edit_message_text(
            "✅ <b>Temporada Resetada!</b>\nO ciclo foi reiniciado.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Erro reset season: {e}", exc_info=True)
        await query.edit_message_text(f"❌ Erro: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]))

# --- NOVA FUNÇÃO: ZERAR PONTOS APENAS ---
async def admin_trigger_pvp_zero_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ação Drástica: Zera os pontos de TODOS os jogadores no banco de dados.
    Não entrega prêmios. Apenas limpa a pontuação.
    """
    query = update.callback_query
    
    # 1. Confirmação (Pequena barreira de segurança)
    if "confirm" not in query.data:
        await query.edit_message_text(
            "⚠️ <b>PERIGO: ZERAR PONTOS</b> ⚠️\n\n"
            "Isso vai definir <code>pvp_points = 0</code> para <b>TODOS</b> os jogadores.\n"
            "Nenhum prêmio será entregue.\n\n"
            "Tem certeza?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ SIM, ZERAR TUDO", callback_data="admin_pvp_zero_points_confirm")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="admin_pvp_menu")]
            ]),
            parse_mode="HTML"
        )
        return

    # 2. Execução
    await query.answer("Zerando pontos no banco de dados...")
    
    try:
        if players_collection is None:
            raise Exception("Sem conexão com o banco de dados.")

        # Update Massivo (Muito rápido)
        result = players_collection.update_many(
            {"pvp_points": {"$gt": 0}}, # Filtro: Quem tem mais que 0
            {"$set": {"pvp_points": 0}} # Ação: Setar para 0
        )
        
        msg = (
            f"💀 <b>HARD RESET CONCLUÍDO</b>\n\n"
            f"Jogadores afetados: <b>{result.modified_count}</b>\n"
            f"Todos agora têm 0 pontos de PvP."
        )
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]),
            parse_mode="HTML"
        )
        logger.warning(f"Admin {query.from_user.id} zerou os pontos PvP de {result.modified_count} jogadores.")

    except Exception as e:
        logger.error(f"Erro ao zerar pontos pvp: {e}", exc_info=True)
        await query.edit_message_text(f"❌ Erro Crítico: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]))


# --- Lista de Handlers ---
admin_pvp_menu_handler = CallbackQueryHandler(admin_pvp_menu, pattern=r'^admin_pvp_menu$')
admin_trigger_pvp_tickets_handler = CallbackQueryHandler(admin_trigger_pvp_tickets, pattern=r'^admin_pvp_trigger_tickets$')
admin_trigger_pvp_rewards_handler = CallbackQueryHandler(admin_trigger_pvp_rewards, pattern=r'^admin_pvp_trigger_rewards$')
admin_trigger_pvp_reset_handler = CallbackQueryHandler(admin_trigger_pvp_reset, pattern=r'^admin_pvp_trigger_reset$')
admin_trigger_pvp_give_ticket_handler = CallbackQueryHandler(admin_trigger_pvp_give_ticket, pattern=r'^admin_pvp_trigger_give_ticket$')
# Novo Handler (Captura tanto o clique inicial quanto a confirmação)
admin_trigger_pvp_zero_points_handler = CallbackQueryHandler(admin_trigger_pvp_zero_points, pattern=r'^admin_pvp_zero_points')

pvp_panel_handlers = [
    admin_pvp_menu_handler,
    admin_trigger_pvp_tickets_handler,
    admin_trigger_pvp_rewards_handler,
    admin_trigger_pvp_reset_handler,
    admin_trigger_pvp_give_ticket_handler,
    admin_trigger_pvp_zero_points_handler, # <--- Adicionado
]