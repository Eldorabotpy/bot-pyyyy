# Arquivo: kingdom_defense/handler.py (VERSÃO CORRIGIDA)

import logging
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaAnimation
from telegram.ext import ContextTypes, CallbackQueryHandler
from .engine import event_manager
from modules import player_manager, file_ids
import re
from handlers.menu.kingdom import show_kingdom_menu
logger = logging.getLogger(__name__)

# ... (as funções _strip_html_for_len, _format_battle_caption, _get_battle_keyboard, etc.
# permanecem exatamente as mesmas até handle_marathon_attack)

def _strip_html_for_len(text: str) -> str:
    """Remove tags HTML para medir o comprimento real do texto."""
    return re.sub('<[^<]+?>', '', text)

def _format_battle_caption(player_state: dict, player_data: dict) -> str:
    mob = player_state['current_mob']
    action_log = player_state.get('action_log', '')
    
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
    
    col_width = 17 
    p_row1 = f"{p_hp_str.ljust(col_width)}{p_atk_str.ljust(col_width)}"
    p_row2 = f"{p_def_str.ljust(col_width)}{p_vel_str.ljust(col_width)}"
    p_row3 = f"{p_srt_str.ljust(col_width)}"

    m_row1 = f"{m_hp_str.ljust(col_width)}{m_atk_str.ljust(col_width)}"
    m_row2 = f"{m_def_str.ljust(col_width)}{m_vel_str.ljust(col_width)}"
    m_row3 = f"{m_srt_str.ljust(col_width)}"

    current_wave = player_state.get('current_wave', 1)
    progress_text = event_manager.get_queue_status_text().replace('\n', ' | ')

    max_width = (col_width * 2) 
    
    wave_text = f" 🌊 ONDA {current_wave} 🌊 "
    header = f"╔{wave_text.center(max_width, '═')}╗"
    
    vs_separator = " 𝐕𝐒 ".center(max_width, '─')
    
    footer_text = " ◆◈◆ "
    footer = f"╚{footer_text.center(max_width, '═')}╝"
    
    log_section = "Aguardando sua ação..."
    if action_log:
        log_section = html.escape(action_log)

    final_caption = (
        f"<code>{header}\n"
        f"{progress_text.center(max_width + 2)}\n"
        f"{'─' * (max_width + 2)}\n"
        f"{p_name.center(max_width + 2)}\n"
        f"{p_row1}\n"
        f"{p_row2}\n"
        f"{p_row3}\n\n"
        f"{vs_separator}\n\n"
        f"{m_name.center(max_width + 2)}\n"
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

# _# NOVO: Teclado simples para o fim de jogo #_
def _get_game_over_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data='kd_back_to_kingdom')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def show_battle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    status_text = event_manager.get_queue_status_text()
    await query.answer(text=status_text, show_alert=True, cache_time=5) # Adicionado cache_time

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    leaderboard_text = event_manager.get_leaderboard_text()
    await query.answer(text=leaderboard_text, show_alert=True, cache_time=5) # Adicionado cache_time

async def back_to_kingdom_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_kingdom_menu(update, context)

async def show_event_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()
    
    caption = "📢 **EVENTO: DEFESA DO REINO**\n\n"
    keyboard = []

    if event_manager.is_active:
        caption += "Uma invasão ameaça o reino! Você irá atender ao chamado para a defesa?\n\n"
        caption += event_manager.get_queue_status_text()
        keyboard.append([InlineKeyboardButton("⚔️ PARTICIPAR DA DEFESA ⚔️", callback_data='kd_join_and_start')])
    else:
        caption += "Não há nenhuma invasão acontecendo no momento."
        
    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data='kd_back_to_kingdom')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Lógica para editar a mensagem, seja ela de texto, foto ou animação
    # Usa try-except para evitar erros se a mensagem já foi deletada
    try:
        if query and (query.message.photo or query.message.animation):
            await query.edit_message_caption(caption=caption, reply_markup=reply_markup, parse_mode='HTML')
        elif query:
            await query.edit_message_text(text=caption, reply_markup=reply_markup, parse_mode='HTML')
    except Exception as e:
        logger.warning(f"Não foi possível editar a mensagem no menu de eventos: {e}")


async def handle_join_and_start_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    player_data = player_manager.get_player_data(user_id)
    
    # --- LÓGICA DE VERIFICAÇÃO DO TICKET (NOVA) ---
    ticket_id = 'ticket_defesa_reino' # Defina o ID do seu item aqui
    player_inventory = player_data.get('inventory', {})
    
    # Verifica se o jogador tem o ticket
    if ticket_id not in player_inventory or player_inventory[ticket_id].get('quantity', 0) <= 0:
        await query.answer("Você precisa de um Ticket da Defesa para entrar!", show_alert=True)
        return # Para a execução aqui se não tiver o ticket

    # --- FIM DA LÓGICA DE VERIFICAÇÃO ---

    await query.answer("Ticket validado! Verificando seu lugar na linha de frente...")

    if not event_manager.is_active:
        await query.edit_message_text("A invasão já terminou.", reply_markup=_get_game_over_keyboard())
        return

    player_manager.remove_item_from_inventory(player_data, ticket_id, 1)
    player_manager.save_player_data(user_id, player_data) # Salva a alteração no inventário
    
    # --- FIM DA LÓGICA DE COBRANÇA ---

    status = event_manager.add_player_to_event(user_id, player_data)
    
    if status == "active":
        battle_data = event_manager.get_battle_data(user_id)
        # Segurança: se por algum motivo não houver dados, não quebra
        if not battle_data:
            await query.edit_message_text("Ocorreu um erro ao buscar seus dados de batalha. Tente novamente.", reply_markup=_get_game_over_keyboard())
            return
            
        media_key = battle_data['current_mob']['media_key']
        file_data = file_ids.get_file_data(media_key)
        
        if not file_data or not file_data.get("id"):
            logger.error(f"MEDIA NÃO ENCONTRADA PARA A CHAVE: {media_key}")
            await query.edit_message_text(
                f"⚠️ Erro de configuração!\n\nA mídia para '{media_key}' não foi encontrada. Avise um administrador."
            )
            return

        caption = _format_battle_caption(battle_data, player_data)
        media = InputMediaAnimation(media=file_data["id"], caption=caption, parse_mode="HTML")
        await query.edit_message_media(media=media, reply_markup=_get_battle_keyboard())
        
    elif status == "waiting":
        status_text = event_manager.get_queue_status_text()
        text = f"🛡️ **Fila de Reforços** 🛡️\n\nA linha de frente está cheia!\n\n{status_text}\n\nAguarde sua vez."
        await query.edit_message_text(text=text, reply_markup=_get_waiting_keyboard(), parse_mode='HTML')

async def handle_marathon_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Trava para evitar cliques duplos
    if context.user_data.get('is_attacking', False):
        await query.answer("Aguarde o resultado do seu último ataque!", cache_time=2)
        return
    context.user_data['is_attacking'] = True

    try:
        user_id = update.effective_user.id
        player_data = player_manager.get_player_data(user_id)
        result = event_manager.process_player_attack(user_id, player_data)
        
        if "error" in result:
            await query.answer(result["error"], show_alert=True)
            return
        
        # _# CORRIGIDO: Lógica para lidar com a derrota do jogador #_
        if result.get("game_over"):
            final_log = result.get('action_log', 'Você foi derrotado em combate.')
            caption = f"☠️ **FIM DE JOGO** ☠️\n\nSua jornada na defesa do reino chegou ao fim.\n\n<b>Última Ação:</b>\n<code>{html.escape(final_log)}</code>"
            
            # Tenta editar a mídia para uma imagem de derrota, se falhar, edita o texto
            try:
                defeat_anim_id = file_ids.get_file_id('game_over_skull') # Precisa ter essa ID no seu file_ids
                media = InputMediaAnimation(media=defeat_anim_id, caption=caption, parse_mode="HTML")
                await query.edit_message_media(media=media, reply_markup=_get_game_over_keyboard())
            except Exception:
                 await query.edit_message_caption(caption=caption, reply_markup=_get_game_over_keyboard(), parse_mode='HTML')
            return

        player_state = event_manager.get_battle_data(user_id)
        
        if not player_state:
            # Se o jogador não tem mais estado, provavelmente foi derrotado ou o evento acabou
            await query.edit_message_text("Sua batalha terminou.", reply_markup=_get_game_over_keyboard())
            return

        if result.get("monster_defeated"):
            await query.answer(f"Inimigo derrotado! {result['loot_message']}", cache_time=1)
            
            next_mob_data = result['next_mob_data']
            player_state['current_mob'] = next_mob_data
            player_state['action_log'] = result['action_log']
            
            media_key = next_mob_data['media_key']
            file_data = file_ids.get_file_data(media_key)
            
            if not file_data or not file_data.get("id"):
                await query.edit_message_caption(caption="Erro: Mídia do próximo monstro não encontrada.", reply_markup=_get_game_over_keyboard())
                return

            caption = _format_battle_caption(player_state, player_data)
            media = InputMediaAnimation(media=file_data["id"], caption=caption, parse_mode="HTML")
            await query.edit_message_media(media=media, reply_markup=_get_battle_keyboard())
        else:
            player_state['action_log'] = result['action_log']
            caption = _format_battle_caption(player_state, player_data)
            await query.edit_message_caption(caption=caption, reply_markup=_get_battle_keyboard(), parse_mode='HTML')
            await query.answer()

    finally:
        context.user_data['is_attacking'] = False
        
async def check_queue_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    
    if not event_manager.is_active:
        await query.answer("O evento já terminou.", show_alert=True)
        await query.edit_message_text("A invasão já terminou.", reply_markup=_get_game_over_keyboard())
        return

    status = event_manager.get_player_status(user_id)
    
    if status == "active":
        await query.answer("Sua vez chegou! Prepare-se!", show_alert=True)
        
        player_data = player_manager.get_player_data(user_id)
        battle_data = event_manager.get_battle_data(user_id)
        
        if not battle_data: # Segurança
            await query.edit_message_text("Erro ao iniciar sua batalha. Tente entrar novamente.", reply_markup=_get_game_over_keyboard())
            return
            
        media_key = battle_data['current_mob']['media_key']
        file_data = file_ids.get_file_data(media_key)
        
        if not file_data or not file_data.get("id"):
            await query.message.edit_text("Erro: Mídia do monstro não encontrada.")
            return

        caption = _format_battle_caption(battle_data, player_data)
        
        # Substitui a mensagem de texto por uma animação
        await query.message.delete()
        await context.bot.send_animation(
            chat_id=user_id, animation=file_data["id"], caption=caption, 
            reply_markup=_get_battle_keyboard(), parse_mode="HTML"
        )
    elif status == "waiting":
        status_text = event_manager.get_queue_status_text()
        text = f"🛡️ **Fila de Reforços** 🛡️\n\nAinda aguardando vaga...\n\n{status_text}"
        await query.edit_message_text(text=text, reply_markup=_get_waiting_keyboard(), parse_mode='HTML')
        await query.answer("Ainda não há vagas. Continue alerta!")
    else: # not_in_event
         await query.answer("Você não está mais na fila.", show_alert=True)
         await show_event_menu(update, context)


def register_handlers(application):
    application.add_handler(CallbackQueryHandler(show_event_menu, pattern='^show_events_menu$'))
    application.add_handler(CallbackQueryHandler(handle_join_and_start_battle, pattern='^kd_join_and_start$'))
    application.add_handler(CallbackQueryHandler(handle_marathon_attack, pattern='^kd_marathon_attack$'))
    application.add_handler(CallbackQueryHandler(check_queue_status, pattern='^kd_check_queue_status$'))
    application.add_handler(CallbackQueryHandler(show_battle_status, pattern='^kd_show_battle_status$'))
    application.add_handler(CallbackQueryHandler(show_leaderboard, pattern='^kd_show_leaderboard$'))
    application.add_handler(CallbackQueryHandler(back_to_kingdom_menu, pattern='^kd_back_to_kingdom$'))