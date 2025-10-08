# Arquivo: kingdom_defense/handler.py (versão final e completa)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes, CallbackQueryHandler
from .engine import event_manager
from modules import player_manager

logger = logging.getLogger(__name__)

# --- FUNÇÃO AUXILIAR DE TECLADO ---

def _get_battle_keyboard() -> InlineKeyboardMarkup:
    """Retorna o teclado com as ações de batalha para anexar à mensagem principal."""
    keyboard = [
        [InlineKeyboardButton("💥 ATACAR 💥", callback_data='kd_attack_wave')],
        [InlineKeyboardButton("📊 Ver Status Detalhado", callback_data='kd_show_status')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_event_from_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia o evento e envia a mensagem de batalha inicial (foto ou texto) no chat."""
    query = update.callback_query
    await query.answer("Iniciando evento...")
    result = event_manager.start_event()

    if "message" in result and "já está ativo" in result["message"]:
        await query.answer(result["message"], show_alert=True)
        return

    if file_id := result.get("file_id"):
        message = await context.bot.send_photo(
            chat_id=update.effective_chat.id, photo=file_id, caption=result.get("caption"),
            reply_markup=_get_battle_keyboard(), parse_mode="HTML"
        )
    else:
        message = await context.bot.send_message(
            chat_id=update.effective_chat.id, text=result.get("text", "Erro ao iniciar evento."),
            reply_markup=_get_battle_keyboard(), parse_mode="HTML"
        )
    
    context.chat_data['kd_battle_message_id'] = message.message_id
    await query.delete_message()

# --- FUNÇÕES CHAMADAS PELOS JOGADORES ---

async def show_event_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra o menu de entrada do evento se ele estiver ativo."""
    query = update.callback_query
    await query.answer()
    
    if not event_manager.is_active:
        caption = "Não há nenhuma invasão acontecendo no momento."
        keyboard = [[InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data='go_to_kingdom')]]
    else:
        caption = "📢 **ALERTA DE INVASÃO!**\n\nHordas de monstros se aproximam do reino. Você irá atender ao chamado para defender Eldora?"
        keyboard = [
            [InlineKeyboardButton("⚔️ PARTICIPAR DA DEFESA ⚔️", callback_data='kd_join_event')],
            [InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data='go_to_kingdom')]
        ]
    
    await query.edit_message_text(
        text=caption, 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode='HTML'
    )

async def join_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adiciona o jogador ao evento após verificar e consumir o ticket."""
    query = update.callback_query
    user_id = update.effective_user.id
    player_data = player_manager.get_player_data(user_id)

    # Lógica de verificação e consumo de ticket
    if not player_manager.has_item(player_data, 'ticket_defesa_reino'):
        await query.answer("Você precisa de um Ticket de Defesa do Reino para participar!", show_alert=True)
        return
    
    player_manager.remove_item_from_inventory(player_data, 'ticket_defesa_reino', 1)

    if event_manager.add_participant(user_id, player_data):
        player_manager.save_player_data(user_id, player_data)
        await query.answer("Você se juntou à defesa de Eldora! Boa sorte!", show_alert=True)
        # Apenas fecha o menu de 'join', o jogador irá interagir pela mensagem principal
        await query.edit_message_text("Agora acompanhe a batalha na mensagem principal do evento!")
    else:
        # Devolve o ticket em caso de falha ao entrar
        player_manager.add_item_to_inventory(player_data, 'ticket_defesa_reino', 1)
        await query.answer("Não foi possível entrar na defesa no momento. Tente novamente.", show_alert=True)


async def attack_wave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa o ataque do jogador e atualiza a mensagem de batalha, mantendo os botões."""
    query = update.callback_query
    user_id = update.effective_user.id
    player_data = player_manager.get_player_data(user_id)
    if not player_data:
        await query.answer("Erro ao encontrar seus dados!", show_alert=True)
        return
        
    result = event_manager.process_attack(user_id, player_data)
    
    if private_message := result.get("private_message"):
        await query.answer(private_message, show_alert=True)
        return
    
    await query.answer("Ataque realizado!")

    battle_message_id = context.chat_data.get('kd_battle_message_id')
    if not battle_message_id:
        logger.warning("Não foi encontrado um ID de mensagem de batalha para atualizar.")
        return

    try:
        # MUDANÇA: Como a imagem da onda não muda, só precisamos atualizar a legenda ou o texto.
        if caption := result.get("caption"):
            await context.bot.edit_message_caption(chat_id=update.effective_chat.id, message_id=battle_message_id, caption=caption, parse_mode="HTML", reply_markup=_get_battle_keyboard())
        elif text := result.get("text"):
            await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=battle_message_id, text=text, parse_mode="HTML", reply_markup=_get_battle_keyboard())
    except Exception as e:
        logger.error(f"Falha ao editar mensagem de batalha: {e}")

async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra o status atual da batalha como um pop-up de texto formatado."""
    query = update.callback_query
    status_text = event_manager.get_battle_status_text()
    await query.answer(text=status_text, show_alert=True)


# --- REGISTRO DOS HANDLERS ---

def register_handlers(application):
    """Registra todos os handlers do evento de defesa."""
    application.add_handler(CallbackQueryHandler(show_event_menu, pattern='^show_events_menu$'))
    application.add_handler(CallbackQueryHandler(join_event, pattern='^kd_join_event$'))
    application.add_handler(CallbackQueryHandler(attack_wave, pattern='^kd_attack_wave$'))
    application.add_handler(CallbackQueryHandler(show_status, pattern='^kd_show_status$'))
    # A função 'start_event_from_admin' é registada corretamente no 'admin_handler.py'.