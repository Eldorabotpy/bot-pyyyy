# handlers/autohunt_handler.py (VERSÃO KILL SWITCH)

import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

from modules import player_manager
from modules.player.premium import PremiumManager
from handlers.hunt_handler import hunt_job

logger = logging.getLogger(__name__)

async def start_autohunt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ativa o modo de auto-caça."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    # 1. Carrega dados FRESCOS do banco (evita cache velho)
    player_data = await player_manager.get_player_data(user_id)

    # Verificações
    if not PremiumManager(player_data).is_premium(): 
        await query.answer("Recurso exclusivo para jogadores Premium.", show_alert=True)
        return
        
    # Se já estiver caçando, avisa e para.
    current_action = player_data.get('player_state', {}).get('action')
    
    # Adicionando verificação explícita: se for qualquer coisa, exceto idle ou auto_hunting
    if current_action not in [None, 'idle', 'auto_hunting']:
        await query.answer(f"Ocupado com outra ação: {current_action}", show_alert=True)
        return
    
    # Verificação de Energia
    if player_data.get('energy', 0) <= 0:
        await query.answer("Sem energia!", show_alert=True)
        return

    # 2. Define estado e SALVA
    # Se estava preso em auto_hunting, sobrescreve o estado, o que é seguro.
    player_data['player_state'] = {'action': 'auto_hunting'}
    await player_manager.save_player_data(user_id, player_data)

    try:
        await query.edit_message_caption(caption="♾️ Caça Automática INICIADA. Buscando monstros...", reply_markup=None)
    except BadRequest:
        try: await query.edit_message_text("♾️ Caça Automática INICIADA. Buscando monstros...", reply_markup=None)
        except BadRequest: pass

    # 3. Limpa jobs antigos (por segurança) antes de criar um novo
    job_name = f"autohunt_{user_id}"
    old_jobs = context.job_queue.get_jobs_by_name(job_name)
    for j in old_jobs: j.schedule_removal()

    # 4. Agenda o loop
    context.job_queue.run_once(
        hunt_job,
        when=1,
        data={'user_id': user_id, 'chat_id': query.message.chat.id},
        name=job_name
    )

async def stop_autohunt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    KILL SWITCH: Força a parada, removendo jobs e limpando o banco.
    Funciona mesmo após reinício do bot.
    """
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Feedback visual imediato (para o usuário não clicar 10 vezes)
    await query.answer("Parando...", show_alert=False)

    # 1. TENTATIVA DE MATAR O PROCESSO NA MEMÓRIA (JobQueue)
    # Isso para o loop se o bot NÃO tiver reiniciado.
    job_name = f"autohunt_{user_id}"
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    jobs_found = len(current_jobs)
    
    for job in current_jobs:
        job.schedule_removal()
    
    logger.info(f"[AUTOHUNT] Parando {user_id}. Jobs removidos: {jobs_found}")

    # 2. LIMPEZA DO BANCO DE DADOS (Persistência)
    # Pegamos os dados frescos
    player_data = await player_manager.get_player_data(user_id)
    
    # Independente de estar 'auto_hunting' ou travado, forçamos 'idle'
    if player_data.get('player_state', {}).get('action') == 'auto_hunting':
        player_data['player_state'] = {'action': 'idle'}
        await player_manager.save_player_data(user_id, player_data)
        msg_text = "🛑 Caça automática finalizada com sucesso."
    else:
        # Se já estava idle (caso de reinício onde o user já clicou antes), apenas confirma
        msg_text = "🛑 O sistema já está parado."

    # 3. Atualiza a mensagem
    try:
        await query.edit_message_caption(caption=msg_text, reply_markup=None)
    except BadRequest:
        try: await query.edit_message_text(msg_text, reply_markup=None)
        except BadRequest: pass

# Exporta os handlers
autohunt_start_handler = CallbackQueryHandler(start_autohunt_callback, pattern=r'^autohunt_start$')
autohunt_stop_handler = CallbackQueryHandler(stop_autohunt_callback, pattern=r'^autohunt_stop$')
all_autohunt_handlers = [autohunt_start_handler, autohunt_stop_handler]