# Arquivo: kingdom_defense/handler.py (VERSÃO FINAL E CORRIGIDA)

import logging
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaAnimation
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler
from .engine import event_manager
from modules import player_manager, file_ids
import re
logger = logging.getLogger(__name__)


def _strip_html_for_len(text: str) -> str:
    """Remove tags HTML para medir o comprimento real do texto."""
    return re.sub('<[^<]+?>', '', text)

def _format_battle_caption(player_state: dict, player_data: dict) -> str:
    """
    Formata a mensagem de combate com uma 'caixa dinâmica' que se adapta ao conteúdo.
    """
    mob = player_state['current_mob']
    action_log = player_state.get('action_log', '')
    
    # --- Monta os blocos de texto como listas de linhas ---
    total_stats = player_manager.get_player_total_stats(player_data)
    p_max_hp = int(total_stats.get('max_hp', 0))
    p_atk = int(total_stats.get('attack', 0))
    p_def = int(total_stats.get('defense', 0))
    p_vel = int(total_stats.get('initiative', 0))
    p_srt = int(total_stats.get('luck', 0))
    hero_block_lines = [
        f"<b>{player_data.get('character_name', 'Herói')}</b>",
        f"❤️ 𝐇𝐏: {player_state['player_hp']}/{p_max_hp}",
        f"⚔️ 𝐀𝐓𝐊: {p_atk}  🛡️ 𝐃𝐄𝐅: {p_def}",
        f"🏃‍♂️ 𝐕𝐄𝐋: {p_vel}  🍀 𝐒𝐑𝐓: {p_srt}"
    ]
    
    m_hp = mob.get('hp', 0)
    m_max_hp = mob.get('max_hp', mob.get('hp', 0))
    m_atk = int(mob.get('attack', 0))
    m_def = int(mob.get('defense', 0))
    m_vel = int(mob.get('initiative', 0))
    m_srt = int(mob.get('luck', 0))
    enemy_block_lines = [
        f"<b>{mob['name']}</b>",
        f"❤️ 𝐇𝐏: {m_hp}/{m_max_hp}",
        f"⚔️ 𝐀𝐓𝐊: {m_atk}  🛡️ 𝐃𝐄𝐅: {m_def}",
        f"🏃‍♂️ 𝐕𝐄𝐋: {m_vel}  🍀 𝐒𝐑𝐓: {m_srt}"
    ]
    
    current_wave = player_state.get('current_wave', 1)
    progress_text = event_manager.get_queue_status_text()
    progress_text_formatted = progress_text.replace(':', '➜').replace('\n', ' | ')
    
    # --- Lógica da Caixa Dinâmica ---
    # 1. Junta todas as linhas de conteúdo que ficarão dentro da caixa
    all_lines_in_box = [progress_text_formatted] + hero_block_lines + enemy_block_lines
    
    # 2. Encontra o comprimento da linha mais longa (ignorando tags HTML)
    # Adicionamos +2 para um pequeno espaço de respiro nas laterais
    max_width = 0
    if all_lines_in_box:
        max_width = max(len(_strip_html_for_len(line)) for line in all_lines_in_box) + 2
    
    # 3. Cria as bordas e separadores com o tamanho dinâmico
    wave_text = f" 🌊 ONDA {current_wave} 🌊 "
    header = f"╔{wave_text.center(max_width, '═')}╗"
    
    vs_separator = " 𝐕𝐒 ".center(max_width, '─')
    
    footer_text = " ◆◈◆ "
    footer = f"╚{footer_text.center(max_width, '═')}╝"
    
    log_section = "Aguardando sua ação..."
    if action_log:
        log_section = html.escape(action_log)

    # --- Montagem Final ---
    # Centraliza o texto de progresso e junta os blocos de herói/inimigo
    full_hero_block = "\n".join(hero_block_lines)
    full_enemy_block = "\n".join(enemy_block_lines)

    # Envolve a caixa em tags <code> para tentar forçar uma fonte de largura fixa
    final_caption = (
        f"<code>{header}\n"
        f"{progress_text_formatted.center(max_width)}\n\n"
        f"{full_hero_block}\n\n"
        f"{vs_separator}\n\n"
        f"{full_enemy_block}\n\n"
        f"{footer}</code>\n\n"
        f"<b>Última Ação:</b>\n<code>{log_section}</code>"
    )
    return final_caption

def _get_battle_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("💥 ATACAR 💥", callback_data='kd_marathon_attack')],
        [
            InlineKeyboardButton("📊 Status", callback_data='kd_show_battle_status'),
            InlineKeyboardButton("🏆 Ranking", callback_data='kd_show_leaderboard')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def _get_waiting_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Atualizar Status", callback_data='kd_check_queue_status')]])

async def show_battle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o status geral do evento em um pop-up."""
    query = update.callback_query
    status_text = event_manager.get_queue_status_text()
    await query.answer(text=status_text, show_alert=True)

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o ranking de dano em um pop-up."""
    query = update.callback_query
    leaderboard_text = event_manager.get_leaderboard_text()
    await query.answer(text=leaderboard_text, show_alert=True)

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
    
    if not player_state: # O jogador pode ter sido removido após ser derrotado
        return

    # Se o monstro foi derrotado...
    if result.get("monster_defeated"):
        await query.answer(f"Inimigo derrotado! {result['loot_message']}")
        
        next_mob_data = result['next_mob_data']
        player_state['current_mob'] = next_mob_data
        player_state['action_log'] = result['action_log']
        
        media_key = next_mob_data['media_key']
        file_data = file_ids.get_file_data(media_key)
        
        if not file_data or not file_data.get("id"):
            await query.edit_message_caption(caption="Erro: Mídia do próximo monstro não encontrada.")
            return

        caption = _format_battle_caption(player_state, player_data)
        media = InputMediaAnimation(media=file_data["id"], caption=caption, parse_mode="HTML")
        await query.edit_message_media(media=media, reply_markup=_get_battle_keyboard())

    # Se a batalha continua...
    else:
        player_state['action_log'] = result['action_log']
        caption = _format_battle_caption(player_state, player_data)
        await query.edit_message_caption(caption=caption, reply_markup=_get_battle_keyboard(), parse_mode='HTML')
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
    application.add_handler(CallbackQueryHandler(show_battle_status, pattern='^kd_show_battle_status$'))
    application.add_handler(CallbackQueryHandler(show_leaderboard, pattern='^kd_show_leaderboard$'))