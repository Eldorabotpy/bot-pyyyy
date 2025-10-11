# Arquivo: kingdom_defense/handler.py (VERSÃO FINAL E CORRIGIDA)

import logging
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaAnimation
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler
from .engine import event_manager
from modules import player_manager, file_ids
import re
from handlers.menu.kingdom import show_kingdom_menu 
logger = logging.getLogger(__name__)


def _strip_html_for_len(text: str) -> str:
    """Remove tags HTML para medir o comprimento real do texto."""
    return re.sub('<[^<]+?>', '', text)

# Em kingdom_defense/handler.py

def _format_battle_caption(player_state: dict, player_data: dict) -> str:
    mob = player_state['current_mob']
    action_log = player_state.get('action_log', '')
    
    # --- Monta os blocos de texto em colunas ---
    total_stats = player_manager.get_player_total_stats(player_data)
    
    p_name = player_data.get('character_name', 'Herói')
    p_hp_str = f"❤️ HP: {player_state['player_hp']}/{int(total_stats.get('max_hp', 0))}"
    p_atk_str = f"⚔️ ATK: {int(total_stats.get('attack', 0))}"
    p_def_str = f"🛡️ DEF: {int(total_stats.get('defense', 0))}"
    p_vel_str = f"🏃‍♂️ VEL: {int(total_stats.get('initiative', 0))}"
    p_srt_str = f"🍀 SRT: {int(total_stats.get('luck', 0))}"

    m_name = mob['name']
    m_hp_str = f"❤️ HP: {mob.get('hp', 0)}/{mob.get('max_hp', 0)}"
    m_atk_str = f"⚔️ ATK: {int(mob.get('attack', 0))}"
    m_def_str = f"🛡️ DEF: {int(mob.get('defense', 0))}"
    m_vel_str = f"🏃‍♂️ VEL: {int(mob.get('initiative', 0))}"
    m_srt_str = f"🍀 SRT: {int(mob.get('luck', 0))}"
    
    # Define a largura das colunas
    col_width = 17 # Largura de cada coluna
    p_row1 = f"{p_hp_str.ljust(col_width)}{p_atk_str.ljust(col_width)}"
    p_row2 = f"{p_def_str.ljust(col_width)}{p_vel_str.ljust(col_width)}"
    p_row3 = f"{p_srt_str.ljust(col_width)}"

    m_row1 = f"{m_hp_str.ljust(col_width)}{m_atk_str.ljust(col_width)}"
    m_row2 = f"{m_def_str.ljust(col_width)}{m_vel_str.ljust(col_width)}"
    m_row3 = f"{m_srt_str.ljust(col_width)}"

    current_wave = player_state.get('current_wave', 1)
    progress_text = event_manager.get_queue_status_text().replace(':', '➜').replace('\n', ' | ')

    # --- Lógica da Caixa Dinâmica ---
    # Mede a largura total necessária (2 colunas + espaço)
    max_width = (col_width * 2) 
    
    wave_text = f" 🌊 ONDA {current_wave} 🌊 "
    header = f"╔{wave_text.center(max_width, '═')}╗"
    
    vs_separator = " 𝐕𝐒 ".center(max_width, '─')
    
    footer_text = " ◆◈◆ "
    footer = f"╚{footer_text.center(max_width, '═')}╝"
    
    log_section = "Aguardando sua ação..."
    if action_log:
        log_section = html.escape(action_log)

    # --- Montagem Final ---
    # Envolve a caixa em tags <code> para forçar fonte de largura fixa
    final_caption = (
        f"<code>{header}\n"
        f"{progress_text.center(max_width)}\n"
        f"{'─' * (max_width + 2)}\n" # Separador
        f"{p_name.center(max_width)}\n"
        f"{p_row1}\n"
        f"{p_row2}\n"
        f"{p_row3}\n\n"
        f"{vs_separator}\n\n"
        f"{m_name.center(max_width)}\n"
        f"{m_row1}\n"
        f"{m_row2}\n"
        f"{m_row3}\n"
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

async def back_to_kingdom_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Função de callback para o botão 'Voltar'.
    Chama diretamente a função que exibe o menu principal do reino.
    """
    query = update.callback_query
    await query.answer()
    
    # Chama a função importada do outro arquivo
    await show_kingdom_menu(update, context)

async def show_event_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra o menu do evento, com o botão de participar SE o evento estiver ativo."""
    query = update.callback_query
    await query.answer()
    
    caption = "📢 **EVENTOS ESPECIAIS**\n\n"
    if event_manager.is_active:
        caption += "Uma invasão ameaça o reino! Você irá atender ao chamado para a defesa?"
    else:
        caption += "Não há nenhuma invasão acontecendo no momento."
        
    keyboard = []
    if event_manager.is_active:
        keyboard.append([InlineKeyboardButton("⚔️ PARTICIPAR DA DEFESA ⚔️", callback_data='kd_join_and_start')])
    
    # Este botão é importante para o jogador poder sair do menu de eventos
    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data='kd_back_to_kingdom')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Lógica inteligente para editar a mensagem, seja ela de texto ou de mídia
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
    # --- LÓGICA DA TRAVA E DEBUG ---
    print("\n--- [DEBUG] Clique em ATACAR recebido! ---")
    query = update.callback_query
    
    is_attacking_flag = context.user_data.get('is_attacking', False)
    print(f"--- [DEBUG] Verificando trava de ataque. Status atual: {is_attacking_flag} ---")

    if is_attacking_flag:
        print("--- [DEBUG] ATAQUE BLOQUEADO PELA TRAVA! Função encerrada. ---")
        await query.answer("Aguarde o resultado do seu último ataque!", cache_time=1)
        return

    context.user_data['is_attacking'] = True
    print("--- [DEBUG] Trava ativada. Processando o ataque... ---")
    # --- FIM DA LÓGICA DA TRAVA ---

    try:
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

    finally:
        # --- BLOCO FINALLY PARA GARANTIR QUE A TRAVA SEJA LIBERADA ---
        print("--- [DEBUG] Trava liberada no bloco FINALLY. ---")
        context.user_data['is_attacking'] = False
        
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
    application.add_handler(CallbackQueryHandler(back_to_kingdom_menu, pattern='^kd_back_to_kingdom$'))