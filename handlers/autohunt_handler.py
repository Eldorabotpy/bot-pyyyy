# handlers/autohunt_handler.py (VERSÃO FINAL E CORRIGIDA)

import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

from modules import player_manager
from modules.player.premium import PremiumManager
from handlers.hunt_handler import hunt_job

logger = logging.getLogger(__name__)

async def start_autohunt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ativa o modo de auto-caça e agenda a primeira tarefa."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    player_data = player_manager.get_player_data(user_id)

    # Verificações de segurança
    if not PremiumManager(player_data).is_premium(): return
    if player_data.get('player_state', {}).get('action') != 'idle':
        await query.answer("Você precisa terminar sua ação atual primeiro!", show_alert=True)
        return
    if player_data.get('energy', 0) <= 0:
        await query.answer("Você não tem energia para iniciar a caça automática!", show_alert=True)
        return

    player_data['player_state'] = {'action': 'auto_hunting'}
    player_manager.save_player_data(user_id, player_data)

    try:
        await query.edit_message_caption(caption="👑 Modo de Caça Automática ativado. A preparar a primeira batalha...", reply_markup=None)
    except BadRequest:
        try: await query.edit_message_text("👑 Modo de Caça Automática ativado. A preparar a primeira batalha...", reply_markup=None)
        except BadRequest: pass

    # Agenda a primeira tarefa de caça para ser executada em 1 segundo
    context.job_queue.run_once(
        hunt_job,
        when=1,
        data={'user_id': user_id, 'chat_id': query.message.chat.id},
        name=f"autohunt_{user_id}" # Um nome único para a tarefa
    )

async def stop_autohunt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Interrompe o ciclo de tarefas de auto-caça."""
    query = update.callback_query
    await query.answer("Caça automática será interrompida após esta batalha.", show_alert=True)

    user_id = update.effective_user.id
    player_data = player_manager.get_player_data(user_id)

    # Apenas remove a flag. O loop irá parar naturalmente na próxima verificação.
    if player_data.get('player_state', {}).get('action') == 'auto_hunting':
        player_data['player_state'] = {'action': 'idle'}
        player_manager.save_player_data(user_id, player_data)
        
# Exporta os handlers
autohunt_start_handler = CallbackQueryHandler(start_autohunt_callback, pattern=r'^autohunt_start$')
autohunt_stop_handler = CallbackQueryHandler(stop_autohunt_callback, pattern=r'^autohunt_stop$')
all_autohunt_handlers = [autohunt_start_handler, autohunt_stop_handler]