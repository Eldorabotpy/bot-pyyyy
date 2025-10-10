# Arquivo: kingdom_defense/handler.py (versão MARATONA PRIVADA)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaAnimation
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler, filters
from .engine import event_manager
from modules import player_manager, file_ids # Assumindo que file_ids gerencia seus IDs de mídia

logger = logging.getLogger(__name__)

# --- 1. FUNÇÕES NO GRUPO (ANÚNCIO E REDIRECIONAMENTO) ---

async def show_event_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra a mensagem inicial do evento no grupo."""
    query = update.callback_query
    await query.answer()
    
    caption = "📢 **ALERTA DE INVASÃO!**\n\nHordas de monstros se aproximam do reino. Atenda ao chamado para defender Eldora!"
    if not event_manager.is_active:
        caption = "Não há nenhuma invasão acontecendo no momento."
        
    keyboard = []
    if event_manager.is_active:
        keyboard.append([InlineKeyboardButton("⚔️ PARTICIPAR DA DEFESA ⚔️", callback_data='kd_join_event')])
    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data='go_to_kingdom')])
    
    await query.edit_message_text(text=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# Em kingdom_defense/handler.py
async def join_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("\n--- [HANDLER] Função 'join_event' foi chamada! ---") # LANTERNA 1
    query = update.callback_query
    user_id = update.effective_user.id
    
    player_data = player_manager.get_player_data(user_id)
    if not player_manager.has_item(player_data, 'ticket_defesa_reino'):
        print("--- [HANDLER] ERRO: Jogador SEM ticket! Saindo da função. ---") # LANTERNA 2
        await query.answer("Você precisa de um Ticket de Defesa do Reino para participar!", show_alert=True)
        return
    
    print("--- [HANDLER] SUCESSO: Jogador TEM o ticket! Continuando... ---") # LANTERNA 3
    
    bot_username = context.bot.username
    battle_url = f"https://t.me/{bot_username}?start=kd_private_battle"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ir para a Batalha Privada ✅", url=battle_url)]
    ])
    
    await query.edit_message_text(
        text="Você atendeu ao chamado! Sua bravura será recompensada.\n\nClique no botão abaixo para ser transportado para a linha de frente!",
        reply_markup=keyboard
    )
    await query.answer()
    
# --- 2. FUNÇÕES NO PRIVADO (O CORAÇÃO DA BATALHA) ---

def _format_battle_caption(player_state: dict) -> str:
    """Formata o texto da mensagem de batalha."""
    mob = player_state['current_mob']
    return (
        f"⚔️ **{mob['name']}** ⚔️\n\n"
        f"HP do Monstro: {mob['hp']}\n"
        f"Seu HP: {player_state['player_hp']}/{player_state['player_max_hp']}\n\n"
        f"{player_state.get('action_log', '')}"
    )

def _get_battle_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("💥 ATACAR 💥", callback_data='kd_marathon_attack')]])

def _get_waiting_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Atualizar Status", callback_data='kd_check_queue_status')]])

async def start_private_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia a batalha ou a fila de espera no chat privado (acionado pelo deep link)."""
    print("\n--- [HANDLER] Função 'start_private_battle' foi chamada! (Deep Link funcionou) ---")
    user_id = update.effective_user.id
    player_data = player_manager.get_player_data(user_id)

    if not event_manager.is_active:
        print("--- [HANDLER] ERRO: Evento não está ativo. Saindo. ---")
        await update.message.reply_text("A invasão já terminou. Obrigado por sua disposição, herói!")
        return

    print("--- [HANDLER] Perguntando à engine qual o status do jogador... ---")
    status = event_manager.add_player_to_event(user_id, player_data)
    print(f"--- [HANDLER] Engine respondeu: status = '{status}' ---")

    if status == "active":
        battle_data = event_manager.get_battle_data(user_id)
        mob_media_key = battle_data['current_mob']['media_key']
        file_id = file_ids.get_file_id(mob_media_key, "animation") # Busca o ID da animação
        
        caption = _format_battle_caption(battle_data)
        await update.message.reply_animation(animation=file_id, caption=caption, reply_markup=_get_battle_keyboard(), parse_mode="HTML")
        
    elif status == "waiting":
        status_text = event_manager.get_queue_status_text()
        text = f"🛡️ **Fila de Reforços** 🛡️\n\nA linha de frente está cheia!\n\n{status_text}\n\nAguarde. Você entrará na batalha assim que uma vaga for liberada."
        await update.message.reply_text(text=text, reply_markup=_get_waiting_keyboard())

async def handle_marathon_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa o clique no botão 'Atacar' e atualiza a mensagem de batalha."""
    query = update.callback_query
    user_id = update.effective_user.id
    player_data = player_manager.get_player_data(user_id)

    result = event_manager.process_player_attack(user_id, player_data)
    player_state = event_manager.get_battle_data(user_id)

    # Caso 1: O jogador foi derrotado
    if result.get("game_over"):
        await query.edit_message_caption(caption=f"☠️ Você foi derrotado! ☠️\n\n{result['action_log']}", reply_markup=None)
        await query.answer("Sua jornada na defesa termina aqui.", show_alert=True)
        return
    
    # Caso 2: O monstro foi derrotado
    if result.get("monster_defeated"):
        await query.answer(f"Inimigo derrotado! {result['loot_message']}", show_alert=True)
        next_mob = result['next_mob_data']
        file_id = file_ids.get_file_id(next_mob['media_key'], "animation")
        
        # Atualiza o estado do jogador com o log da ação para exibição
        player_state['action_log'] = result['action_log']
        caption = _format_battle_caption(player_state)
        
        media = InputMediaAnimation(media=file_id, caption=caption, parse_mode="HTML")
        await query.edit_message_media(media=media, reply_markup=_get_battle_keyboard())

    # Caso 3: A batalha continua (ninguém morreu)
    else:
        player_state['action_log'] = result['action_log']
        caption = _format_battle_caption(player_state)
        await query.edit_message_caption(caption=caption, reply_markup=_get_battle_keyboard())
        await query.answer()

async def check_queue_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verifica se um jogador na fila já pode entrar na batalha."""
    query = update.callback_query
    user_id = update.effective_user.id
    status = event_manager.get_player_status(user_id)

    if status == "active":
        await query.answer("Sua vez chegou! Prepare-se!", show_alert=True)
        battle_data = event_manager.get_battle_data(user_id)
        file_id = file_ids.get_file_id(battle_data['current_mob']['media_key'], "animation")
        caption = _format_battle_caption(battle_data)
        media = InputMediaAnimation(media=file_id, caption=caption, parse_mode="HTML")
        # Transforma a mensagem de texto em uma mensagem de mídia
        await query.message.delete()
        await context.bot.send_animation(chat_id=user_id, animation=file_id, caption=caption, reply_markup=_get_battle_keyboard(), parse_mode="HTML")
    else:
        status_text = event_manager.get_queue_status_text()
        text = f"🛡️ **Fila de Reforços** 🛡️\n\nAinda aguardando vaga...\n\n{status_text}"
        await query.edit_message_text(text=text, reply_markup=_get_waiting_keyboard())
        await query.answer("Ainda não há vagas. Continue alerta!")

# --- 3. REGISTRO DOS HANDLERS ---

def register_handlers(application):

    """Registra todos os handlers necessários para o evento."""
    # Handlers de botões (CallbackQuery)
    application.add_handler(CallbackQueryHandler(show_event_menu, pattern='^show_events_menu$'))
    application.add_handler(CallbackQueryHandler(join_event, pattern='^kd_join_event$'))
    application.add_handler(CallbackQueryHandler(handle_marathon_attack, pattern='^kd_marathon_attack$'))
    application.add_handler(CallbackQueryHandler(check_queue_status, pattern='^kd_check_queue_status$'))
    
    # Handler de Comando para o deep link do chat privado
    application.add_handler(CommandHandler("start", start_private_battle, filters=filters.Regex("kd_private_battle")))