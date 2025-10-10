# Arquivo: kingdom_defense/handler.py (VERSÃO FINAL E CORRIGIDA)

import logging
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaAnimation
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler
from .engine import event_manager
from modules import player_manager, file_ids

logger = logging.getLogger(__name__)

# --- FUNÇÕES DE LÓGICA DA BATALHA PRIVADA ---

def _format_battle_caption(player_state: dict, player_data: dict) -> str:
    mob = player_state['current_mob']
    action_log = player_state.get('action_log', '')
    total_stats = player_manager.get_player_total_stats(player_data)
    p_max_hp = int(total_stats.get('max_hp', 0))
    p_atk = int(total_stats.get('attack', 0))
    p_def = int(total_stats.get('defense', 0))
    hero_block = (
        f"<b>{player_data.get('character_name', 'Herói')}</b>\n"
        f"❤️ 𝐇𝐏: {player_state['player_hp']}/{p_max_hp}\n"
        f"⚔️ 𝐀𝐓𝐊: {p_atk} 🛡️ 𝐃𝐄𝐅: {p_def}"
    )
    m_hp = mob['hp']
    m_max_hp = mob['max_hp']
    m_atk = int(mob.get('attack', 0))
    m_def = int(mob.get('defense', 0))
    enemy_block = (
        f"<b>{mob['name']}</b>\n"
        f"❤️ 𝐇𝐏: {m_hp}/{m_max_hp}\n"
        f"⚔️ 𝐀𝐓𝐊: {m_atk} 🛡️ 𝐃𝐄𝐅: {m_def}"
    )
    log_section = "Aguardando sua ação..."
    if action_log:
        log_section = html.escape(action_log)
    header = "╔═══════ ◆◈◆ COMBATE◆◈◆ ═══════╗"
    separator = "═════════════ 𝐕𝐒 ═════════════"
    footer = "╚════════════ ◆◈◆ ════════════╝"
    return (
        f"{header}\n\n{hero_block}\n\n{separator}\n\n{enemy_block}\n\n"
        f"<b>Última Ação:</b>\n<code>{log_section}</code>\n\n{footer}"
    )

def _get_battle_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("💥 ATACAR 💥", callback_data='kd_marathon_attack')]])

def _get_waiting_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Atualizar Status", callback_data='kd_check_queue_status')]])

async def show_event_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    caption = "📢 **ALERTA DE INVASÃO!**\n\nHordas se aproximam. Você irá atender ao chamado para defender Eldora?"
    if not event_manager.is_active:
        caption = "Não há nenhuma invasão acontecendo no momento."
    keyboard = []
    if event_manager.is_active:
        keyboard.append([InlineKeyboardButton("⚔️ PARTICIPAR DA DEFESA ⚔️", callback_data='kd_join_and_start')])
    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data='go_to_kingdom')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if query.message.photo or query.message.animation:
        await query.edit_message_caption(caption=caption, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await query.edit_message_text(text=caption, reply_markup=reply_markup, parse_mode='HTML')

async def handle_join_and_start_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    FUNÇÃO TUDO-EM-UM: Chamada pelo clique em 'PARTICIPAR'.
    Registra o jogador e transforma a tela em batalha ou espera.
    """
    query = update.callback_query
    user_id = update.effective_user.id
    player_data = player_manager.get_player_data(user_id)
    
    await query.answer("Verificando seu lugar na linha de frente...")

    if not event_manager.is_active:
        await query.edit_message_text("A invasão já terminou.")
        return

    # A engine faz a lógica de adicionar à batalha ou à fila
    status = event_manager.add_player_to_event(user_id, player_data)
    
    # Se entrou na batalha, transforma a mensagem em uma animação de combate
    if status == "active":
        battle_data = event_manager.get_battle_data(user_id)
        media_key = battle_data['current_mob']['media_key']
        file_data = file_ids.get_file_data(media_key)
        
        # Rede de segurança para evitar crashes se a mídia não for encontrada
        if not file_data or not file_data.get("id"):
            logger.error(f"MEDIA NÃO ENCONTRADA PARA A CHAVE: {media_key}")
            await query.edit_message_text(
                f"⚠️ Erro de configuração!\n\nA mídia para '{media_key}' não foi encontrada. Avise um administrador."
            )
            return

        battle_data['current_mob']['max_hp'] = battle_data['current_mob']['hp']
        caption = _format_battle_caption(battle_data, player_data)
        media = InputMediaAnimation(media=file_data["id"], caption=caption, parse_mode="HTML")
        await query.edit_message_media(media=media, reply_markup=_get_battle_keyboard())
        
    # Se entrou na fila, transforma a mensagem em um texto de espera
    elif status == "waiting":
        status_text = event_manager.get_queue_status_text()
        text = f"🛡️ **Fila de Reforços** 🛡️\n\nA linha de frente está cheia!\n\n{status_text}\n\nAguarde."
        await query.edit_message_text(text=text, reply_markup=_get_waiting_keyboard())
async def handle_marathon_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    player_data = player_manager.get_player_data(user_id)
    result = event_manager.process_player_attack(user_id, player_data)
    if "error" in result:
        await query.answer(result["error"], show_alert=True)
        return
    player_state = event_manager.get_battle_data(user_id)
    if result.get("game_over"):
        player_state['action_log'] = result.get('action_log', '')
        await query.edit_message_caption(caption=f"☠️ Você foi derrotado! ☠️\n\n{player_state['action_log']}", reply_markup=None)
        await query.answer("Sua jornada na defesa termina aqui.", show_alert=True)
        return
    if result.get("monster_defeated"):
        await query.answer(f"Inimigo derrotado! {result['loot_message']}", show_alert=True)
        next_mob = result['next_mob_data']
        media_key = next_mob['media_key']
        file_data = file_ids.get_file_data(media_key)
        if not file_data or not file_data.get("id"):
            await query.edit_message_caption(caption="Erro: Mídia do próximo monstro não encontrada.")
            return
        player_state['action_log'] = result['action_log']
        caption = _format_battle_caption(player_state, player_data) # <-- CORRIGIDO
        media = InputMediaAnimation(media=file_data["id"], caption=caption, parse_mode="HTML")
        await query.edit_message_media(media=media, reply_markup=_get_battle_keyboard())
    else:
        player_state['action_log'] = result['action_log']
        caption = _format_battle_caption(player_state, player_data) # <-- CORRIGIDO
        await query.edit_message_caption(caption=caption, reply_markup=_get_battle_keyboard())
        await query.answer()

async def check_queue_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    status = event_manager.get_player_status(user_id)
    if status == "active":
        await query.answer("Sua vez chegou! Prepare-se!", show_alert=True)
        player_data = player_manager.get_player_data(user_id) # <-- CORRIGIDO
        battle_data = event_manager.get_battle_data(user_id)
        media_key = battle_data['current_mob']['media_key']
        file_data = file_ids.get_file_data(media_key) # <-- CORRIGIDO
        if not file_data or not file_data.get("id"):
            await query.message.delete()
            await context.bot.send_message(chat_id=user_id, text="Erro: Mídia do monstro não encontrada.")
            return
        caption = _format_battle_caption(battle_data, player_data) # <-- CORRIGIDO
        await query.message.delete()
        await context.bot.send_animation(
            chat_id=user_id, animation=file_data["id"], caption=caption, 
            reply_markup=_get_battle_keyboard(), parse_mode="HTML"
        )
    else:
        status_text = event_manager.get_queue_status_text()
        text = f"🛡️ Fila de Reforços 🛡️\n\nAinda aguardando vaga...\n\n{status_text}"
        await query.edit_message_text(text=text, reply_markup=_get_waiting_keyboard())
        await query.answer("Ainda não há vagas. Continue alerta!")

def register_handlers(application):
    application.add_handler(CallbackQueryHandler(show_event_menu, pattern='^show_events_menu$'))
    application.add_handler(CallbackQueryHandler(handle_join_and_start_battle, pattern='^kd_join_and_start$'))
    application.add_handler(CallbackQueryHandler(handle_marathon_attack, pattern='^kd_marathon_attack$'))
    application.add_handler(CallbackQueryHandler(check_queue_status, pattern='^kd_check_queue_status$'))