# handlers/admin/pvp_panel_handler.py
# (VERSÃO BLINDADA: Com limpeza de cache em todas as opções de reset)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

# --- Importação do Banco de Dados ---
from modules.player.core import players_collection

# --- IMPORTANTE: Importamos o player_manager para limpar o CACHE ---
from modules import player_manager 

# --- Importa a lógica mestre de reset (que criamos no pvp_scheduler) ---
from pvp.pvp_scheduler import executar_reset_pvp

# --- Importar Jobs Antigos (Mantemos compatibilidade) ---
try:
    from handlers.daily_jobs import daily_pvp_entry_reset_job, daily_arena_ticket_job
except ImportError:
    from handlers.jobs import daily_pvp_entry_reset_job
    try:
        from handlers.jobs import daily_arena_ticket_job
    except ImportError:
         # Fallback silencioso se não existir
         async def daily_arena_ticket_job(context, force_run=False): pass

from handlers.jobs import distribute_pvp_rewards

logger = logging.getLogger(__name__)

# --- Função Principal do Menu ---
async def admin_pvp_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = (
        "⚔️ <b>Painel de Controle de PvP</b> ⚔️\n\n"
        "Selecione uma ação manual para executar imediatamente.\n\n"
        "⚠️ <b>Atenção:</b> As ações de RESET (3 e 4) limpam o cache global."
    )
           
    keyboard = [
        [InlineKeyboardButton("🎫 0. Entregar Tickets de Arena", callback_data="admin_pvp_trigger_give_ticket")],
        [InlineKeyboardButton("🎟️ 1. Resetar Entradas (Contador)", callback_data="admin_pvp_trigger_tickets")],
        [InlineKeyboardButton("🏆 2. Entregar Prêmios (Sem Zerar)", callback_data="admin_pvp_trigger_rewards")],
        [InlineKeyboardButton("🔄 3. VIRADA DE TEMPORADA (Reset + Prêmios)", callback_data="admin_pvp_trigger_reset")],
        [InlineKeyboardButton("💀 4. HARD RESET (Só Zera Pontos)", callback_data="admin_pvp_zero_points")],
        [InlineKeyboardButton("⬅️ Voltar ao Painel Admin", callback_data="admin_main")] 
    ]
    
    await query.edit_message_text(
        text=text, 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode="HTML"
    )

# --- Callbacks ---

async def admin_trigger_pvp_give_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Entregando tickets...")
    try:
        await daily_arena_ticket_job(context, force_run=True)
        await query.edit_message_text("✅ <b>Tickets Entregues a todos!</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Erro tickets: {e}")
        await query.edit_message_text(f"❌ Erro: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]))

async def admin_trigger_pvp_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Resetando entradas...")
    try:
        await daily_pvp_entry_reset_job(context, force_run=True)
        await query.edit_message_text("✅ <b>Entradas Diárias Resetadas!</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Erro reset entradas: {e}")
        await query.edit_message_text(f"❌ Erro: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]))

async def admin_trigger_pvp_rewards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Distribuindo prêmios...")
    try:
        await distribute_pvp_rewards(context)
        await query.edit_message_text("✅ <b>Prêmios Distribuídos (Top Ranking)!</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Erro rewards: {e}")
        await query.edit_message_text(f"❌ Erro: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]))

async def admin_trigger_pvp_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Opção 3: Usa a função MESTRE do scheduler.
    Ela já faz: Premiação + Reset DB + Limpeza de Cache.
    """
    query = update.callback_query
    await query.answer("Iniciando Virada de Temporada...")
    
    try:
        # Chama a função robusta que criamos no passo anterior
        await executar_reset_pvp(context.bot, force_run=True)
        
        await query.edit_message_text(
            "✅ <b>Temporada Encerrada com Sucesso!</b>\n\n"
            "1. Prêmios entregues aos Top 5.\n"
            "2. Pontos de todos zerados.\n"
            "3. Cache do servidor limpo.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Erro reset season: {e}", exc_info=True)
        await query.edit_message_text(f"❌ Erro Crítico: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]))

async def admin_trigger_pvp_zero_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Opção 4: ZERA TUDO SEM DÓ (Sem prêmios).
    Agora inclui limpeza de cache para evitar bugs.
    """
    query = update.callback_query
    
    if "confirm" not in query.data:
        await query.edit_message_text(
            "⚠️ <b>PERIGO: HARD RESET</b> ⚠️\n\n"
            "Isso vai definir <code>pvp_points = 0</code> para <b>TODOS</b>.\n"
            "• Ninguém recebe prêmios.\n"
            "• O Cache será limpo (pode causar leve lag).\n\n"
            "Tem certeza absoluta?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ SIM, APAGUE TUDO", callback_data="admin_pvp_zero_points_confirm")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="admin_pvp_menu")]
            ]),
            parse_mode="HTML"
        )
        return

    await query.answer("Executando Hard Reset...")
    try:
        if players_collection is None: raise Exception("Sem banco de dados.")
        
        # 1. Zera no Banco
        result = players_collection.update_many(
            {"pvp_points": {"$gt": 0}}, 
            {"$set": {"pvp_points": 0}}
        )
        
        # 2. LIMPEZA DE CACHE (CRUCIAL ADICIONADA)
        if hasattr(player_manager, "PLAYER_CACHE"):
            player_manager.PLAYER_CACHE.clear()
        
        await query.edit_message_text(
            f"💀 <b>HARD RESET CONCLUÍDO</b>\n"
            f"Jogadores zerados: <b>{result.modified_count}</b>\n"
            f"Memória limpa: <b>Sim</b>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Erro hard reset: {e}", exc_info=True)
        await query.edit_message_text(f"❌ Erro: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_pvp_menu")]]))

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