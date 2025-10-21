# Arquivo: kingdom_defense/handler.py (VERSÃO FINAL COM TELA DE VITÓRIA)

import logging
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, CallbackQuery
from telegram.ext import ContextTypes, CallbackQueryHandler
from .engine import event_manager
from modules import player_manager, file_ids
import re
import time
import traceback
from handlers.menu.kingdom import show_kingdom_menu
from modules.game_data.skills import SKILL_DATA

logger = logging.getLogger(__name__)


VICTORY_PHOTO_ID = "AgACAgEAAxkBAAIW52jztXfEWirRJSoo9yUx5pjGQ7u_AAInC2sbR-agR7yizwIUvB1jAQADAgADeQADNgQ" 

def _strip_html_for_len(text: str) -> str:
    """Remove tags HTML para medir o comprimento real do texto."""
    return re.sub('<[^<]+?>', '', text)

def _format_battle_caption(player_state: dict, player_data: dict) -> str:
    mob = player_state['current_mob']
    action_log = player_state.get('action_log', '')
    total_stats = player_manager.get_player_total_stats(player_data)
    
    p_name = player_data.get('character_name', 'Herói')
    p_hp_str = f"❤️ HP: {player_state['player_hp']}/{int(total_stats.get('max_hp', 0))}"
    p_mp_str = f"💙 MP: {player_data.get('mana', 0)}/{int(total_stats.get('max_mana', 0))}"
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
    p_row1 = f"{p_hp_str.ljust(col_width)}{p_mp_str.ljust(col_width)}"
    p_row2 = f"{p_atk_str.ljust(col_width)}{p_def_str.ljust(col_width)}"
    p_row3 = f"{p_vel_str.ljust(col_width)}{p_srt_str.ljust(col_width)}" # Ajustado para VEL e SRT

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
        [
            InlineKeyboardButton("💥 Atacar", callback_data='kd_marathon_attack'),
            InlineKeyboardButton("✨ Skills", callback_data='show_skill_menu')
        ],
        [
            InlineKeyboardButton("📊 Status", callback_data='kd_show_battle_status'),
            InlineKeyboardButton("🏆 Ranking", callback_data='kd_show_leaderboard')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def _get_waiting_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Atualizar Status", callback_data='kd_check_queue_status')]])

def _get_game_over_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data='kd_back_to_kingdom')]
    ]
    return InlineKeyboardMarkup(keyboard)

#
# ADICIONE ESTA FUNÇÃO COMPLETA AO SEU handler.py
#
async def _resolve_battle_turn(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, result: dict):
    user_id = query.from_user.id
    
    if "aoe_results" in result:
        for event in result["aoe_results"]:
            affected_id = event["user_id"]
            if affected_id == user_id: continue
            try:
                message_to_edit_id = query.message.message_id 
                if event["was_defeated"]:
                    caption = "☠️ <b>FIM DE JOGO</b> ☠️\n\nVocê foi derrotado por um ataque em área do chefe."
                    await context.bot.edit_message_caption(chat_id=affected_id, message_id=message_to_edit_id, caption=caption, reply_markup=_get_game_over_keyboard(), parse_mode='HTML')
                else:
                    affected_player_data = player_manager.get_player_data(affected_id)
                    affected_player_state = event_manager.get_battle_data(affected_id)
                    if affected_player_data and affected_player_state:
                        new_caption = _format_battle_caption(affected_player_state, affected_player_data)
                        await context.bot.edit_message_caption(chat_id=affected_id, message_id=message_to_edit_id, caption=new_caption, reply_markup=_get_battle_keyboard(), parse_mode='HTML')
            except Exception as e:
                logger.error(f"Falha ao notificar jogador passivo {affected_id} sobre o AoE: {e}")

    if result.get("event_over"):
        final_log = result.get("action_log", "")
        victory_caption = f"🏆 <b>VITÓRIA!</b> 🏆\n\nO reino está a salvo!\n\n<i>Últimas ações:\n{html.escape(final_log)}</i>"
        media_victory = InputMediaPhoto(media=VICTORY_PHOTO_ID, caption=victory_caption, parse_mode='HTML')
        await query.edit_message_media(media=media_victory, reply_markup=_get_game_over_keyboard())
        return

    is_player_defeated = result.get("game_over") or ("aoe_results" in result and any(e['user_id'] == user_id and e['was_defeated'] for e in result["aoe_results"]))
    if is_player_defeated:
        final_log = result.get('action_log', 'Você foi derrotado.')
        caption = f"☠️ <b>FIM DE JOGO</b> ☠️\n\nSua jornada na defesa chegou ao fim.\n\n<b>Última Ação:</b>\n<code>{html.escape(final_log)}</code>"
        try:
            defeat_media_id = file_ids.get_file_id('game_over_skull')
            media = InputMediaPhoto(media=defeat_media_id, caption=caption, parse_mode="HTML")
            await query.edit_message_media(media=media, reply_markup=_get_game_over_keyboard())
        except Exception:
            await query.edit_message_caption(caption=caption, reply_markup=_get_game_over_keyboard(), parse_mode='HTML')
        return

    if result.get("monster_defeated"):
        await query.answer(f"Inimigo derrotado! {result.get('loot_message', '')}", cache_time=1)
        player_data = player_manager.get_player_data(user_id)
        player_state = event_manager.get_battle_data(user_id)
        player_state['action_log'] = result.get('action_log', '')
        media_key = player_state['current_mob']['media_key']
        file_data = file_ids.get_file_data(media_key)
        
        caption = _format_battle_caption(player_state, player_data)
        media = InputMediaPhoto(media=file_data["id"], caption=caption, parse_mode="HTML")
        await query.edit_message_media(media=media, reply_markup=_get_battle_keyboard())
        return
    
    else:
        player_data = player_manager.get_player_data(user_id)
        player_state = event_manager.get_battle_data(user_id)
        if player_state:
            player_state['action_log'] = result.get('action_log', '')
            caption = _format_battle_caption(player_state, player_data)
            await query.edit_message_caption(caption=caption, reply_markup=_get_battle_keyboard(), parse_mode='HTML')

async def show_skill_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    player_data = player_manager.get_player_data(user_id)
    player_skill_ids = player_data.get("skills", [])
    active_skills = [skill_id for skill_id in player_skill_ids if SKILL_DATA.get(skill_id, {}).get("type") == "active"]

    if not active_skills:
        await query.answer("Você não possui habilidades ativas para usar!", show_alert=True)
        return

    keyboard, current_mana = [], player_data.get("mana", 0)
    for skill_id in active_skills:
        skill_info = SKILL_DATA[skill_id]
        mana_cost = skill_info.get('mana_cost', 0)
        button_text = f"{skill_info['display_name']} ({mana_cost} MP)"
        if current_mana < mana_cost:
            button_text = f"❌ {button_text}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"use_skill:{skill_id}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="back_to_battle")])
    await query.edit_message_caption(caption="Escolha uma habilidade para usar:", reply_markup=InlineKeyboardMarkup(keyboard))

async def back_to_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    player_data = player_manager.get_player_data(user_id)
    battle_data = event_manager.get_battle_data(user_id)
    if not battle_data:
        await query.edit_message_caption(caption="A batalha terminou.", reply_markup=_get_game_over_keyboard())
        return
    caption = _format_battle_caption(battle_data, player_data)
    await query.edit_message_caption(caption=caption, reply_markup=_get_battle_keyboard(), parse_mode="HTML")

async def handle_marathon_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    now = time.time()
    last_action_time = context.user_data.get('kd_last_action_time', 0)
    if now - last_action_time < 2.0:
        await query.answer("Aguarde um momento!", cache_time=1)
        return
    context.user_data['kd_last_action_time'] = now
    await query.answer()
    
    try:
        player_data = player_manager.get_player_data(user_id)
        if not player_data: return
        result = event_manager.process_player_attack(user_id, player_data)
        await _resolve_battle_turn(query, context, result)
    except Exception:
        traceback.print_exc()
        await query.answer("Ocorreu um erro crítico.", show_alert=True)

async def back_to_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redesenha a tela de batalha principal ao sair do menu de skills."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    player_data = player_manager.get_player_data(user_id)
    # Precisamos dos dados da batalha para redesenhar a tela
    battle_data = event_manager.get_battle_data(user_id)

    if not battle_data:
        # Se por algum motivo a batalha terminou enquanto o jogador olhava as skills
        await query.edit_message_caption(caption="A batalha terminou.", reply_markup=_get_game_over_keyboard())
        return

    # Formata a legenda da batalha e edita a mensagem de volta para a tela principal
    caption = _format_battle_caption(battle_data, player_data)
    await query.edit_message_caption(caption=caption, reply_markup=_get_battle_keyboard(), parse_mode="HTML")

#
# SUBSTITUA SUA FUNÇÃO use_skill_handler PELA VERSÃO COMPLETA ABAIXO
#
async def use_skill_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    now = time.time()
    last_action_time = context.user_data.get('kd_last_action_time', 0)
    if now - last_action_time < 2.0:
        await query.answer("Aguarde um momento!", cache_time=1)
        return
    context.user_data['kd_last_action_time'] = now
    
    try:
        skill_id = query.data.split(':')[1]
    except IndexError:
        return

    player_data = player_manager.get_player_data(user_id)
    if not player_data: return

    skill_info = SKILL_DATA.get(skill_id)
    if not skill_info:
        await query.answer("Erro: Habilidade não encontrada!", show_alert=True)
        return
    
    if player_data.get("mana", 0) < skill_info.get("mana_cost", 0):
        await query.answer("Mana insuficiente!", show_alert=True)
        return

    await query.answer()
    result = event_manager.process_player_skill(user_id, player_data, skill_id)
    await _resolve_battle_turn(query, context, result)

async def apply_skill_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    now = time.time()
    last_action_time = context.user_data.get('kd_last_action_time', 0)
    if now - last_action_time < 2.0:
        await query.answer("Aguarde um momento!", cache_time=1)
        return
    context.user_data['kd_last_action_time'] = now

    try:
        _, skill_id, target_id_str = query.data.split(':')
        target_id = int(target_id_str)
        player_data = player_manager.get_player_data(user_id)
        if not player_data: return

        await query.answer()
        result = event_manager.process_player_skill(user_id, player_data, skill_id, target_id=target_id)
        await _resolve_battle_turn(query, context, result)
    except Exception:
        traceback.print_exc()
        await query.answer("Ocorreu um erro ao aplicar a skill.", show_alert=True)

async def show_battle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    status_text = event_manager.get_queue_status_text()
    await query.answer(text=status_text, show_alert=True, cache_time=5)

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    leaderboard_text = event_manager.get_leaderboard_text()
    await query.answer(text=leaderboard_text, show_alert=True, cache_time=5)

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
    
    ticket_id = 'ticket_defesa_reino'
    player_inventory = player_data.get('inventory', {})
    
    if player_inventory.get(ticket_id, 0) <= 0:
        await query.answer("Você precisa de um Ticket da Defesa para entrar!", show_alert=True)
        return

    await query.answer("Ticket validado! Verificando seu lugar na linha de frente...")

    if not event_manager.is_active:
        await query.edit_message_text("A invasão já terminou.", reply_markup=_get_game_over_keyboard())
        return

    player_manager.remove_item_from_inventory(player_data, ticket_id, 1)
    player_manager.save_player_data(user_id, player_data)
    
    status = event_manager.add_player_to_event(user_id, player_data)
    
    if status == "active":
        battle_data = event_manager.get_battle_data(user_id)
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
        media = InputMediaPhoto(media=file_data["id"], caption=caption, parse_mode="HTML")
        await query.edit_message_media(media=media, reply_markup=_get_battle_keyboard())
        
    elif status == "waiting":
        status_text = event_manager.get_queue_status_text()
        text = f"🛡️ Fila de Reforços 🛡️\n\nA linha de frente está cheia!\n\n{status_text}\n\nAguarde sua vez."
        await query.edit_message_text(text=text, reply_markup=_get_waiting_keyboard(), parse_mode='HTML')

async def handle_marathon_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id # ID do jogador que clicou no botão
    
    now = time.time()
    last_attack_time = context.user_data.get('kd_last_attack_time', 0)
    
    if now - last_attack_time < 2.0:
        await query.answer("Aguarde um momento antes de atacar novamente!", cache_time=1)
        return

    context.user_data['kd_last_attack_time'] = now
    
    try:
        player_data = player_manager.get_player_data(user_id)
        result = event_manager.process_player_attack(user_id, player_data)
        
        if "error" in result:
            await query.answer(result["error"], show_alert=True)
            return

        # --- INÍCIO DO NOVO BLOCO DE NOTIFICAÇÃO AOE ---
        if "aoe_results" in result:
            # Notifica todos os jogadores que foram afetados, EXCETO o que atacou
            for event in result["aoe_results"]:
                affected_id = event["user_id"]
                if affected_id == user_id:
                    continue # Pula o jogador que atacou, pois a tela dele será atualizada no final

                try:
                    message_to_edit_id = query.message.message_id 

                    if event["was_defeated"]:
                        caption = "☠️ FIM DE JOGO ☠️\n\nVocê foi derrotado por um ataque em área do chefe."
                        await context.bot.edit_message_caption(chat_id=affected_id, message_id=message_to_edit_id, caption=caption, reply_markup=_get_game_over_keyboard(), parse_mode='HTML')
                    else:
                        affected_player_data = player_manager.get_player_data(affected_id)
                        affected_player_state = event_manager.get_battle_data(affected_id)
                        if affected_player_data and affected_player_state:
                            new_caption = _format_battle_caption(affected_player_state, affected_player_data)
                            await context.bot.edit_message_caption(chat_id=affected_id, message_id=message_to_edit_id, caption=new_caption, reply_markup=_get_battle_keyboard(), parse_mode='HTML')
                except Exception as e:
                    logger.error(f"Falha ao notificar jogador passivo {affected_id} sobre o AoE: {e}")
        # --- FIM DO NOVO BLOCO DE NOTIFICAÇÃO AOE ---

        if result.get("event_over"):
            final_log = result.get("action_log", "")
            victory_caption = (
                f"🏆 VITÓRIA! 🏆\n\n"
                f"O reino está a salvo graças à sua bravura!\n"
                f"Todos os inimigos foram derrotados.\n\n"
                f"<i>Últimas ações:\n{html.escape(final_log)}</i>"
            )
            media_victory = InputMediaPhoto(
                media=VICTORY_PHOTO_ID,
                caption=victory_caption,
                parse_mode='HTML'
            )
            await query.edit_message_media(media=media_victory, reply_markup=_get_game_over_keyboard())
            return
        
        # --- BLOCO DE FIM DE JOGO (AJUSTADO PARA INCLUIR DERROTA POR AOE) ---
        is_player_defeated = result.get("game_over") or (
            "aoe_results" in result and any(e['user_id'] == user_id and e['was_defeated'] for e in result["aoe_results"])
        )
        if is_player_defeated:
            final_log = result.get('action_log', 'Você foi derrotado em combate.')
            caption = f"☠️ FIM DE JOGO ☠️\n\nSua jornada na defesa do reino chegou ao fim.\n\n<b>Última Ação:</b>\n<code>{html.escape(final_log)}</code>"
            
            try:
                defeat_media_id = file_ids.get_file_id('game_over_skull')
                media = InputMediaPhoto(media=defeat_media_id, caption=caption, parse_mode="HTML")
                await query.edit_message_media(media=media, reply_markup=_get_game_over_keyboard())
            except Exception:
                await query.edit_message_caption(caption=caption, reply_markup=_get_game_over_keyboard(), parse_mode='HTML')
            return
        # --- FIM DO BLOCO DE FIM DE JOGO ---

        player_state = event_manager.get_battle_data(user_id)
        if not player_state:
            await query.edit_message_caption(caption="Sua batalha terminou.", reply_markup=_get_game_over_keyboard())
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
            media = InputMediaPhoto(media=file_data["id"], caption=caption, parse_mode="HTML")
            await query.edit_message_media(media=media, reply_markup=_get_battle_keyboard())
        else:
            player_state['action_log'] = result['action_log']
            caption = _format_battle_caption(player_state, player_data)
            await query.edit_message_caption(caption=caption, reply_markup=_get_battle_keyboard(), parse_mode='HTML')
            await query.answer()

    except Exception as e:
        print(f"!!!!!!!! ERRO CRÍTICO EM handle_marathon_attack !!!!!!!!!!")
        traceback.print_exc()
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        await query.answer("Ocorreu um erro ao processar seu ataque. Avise um administrador.", show_alert=True)

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
        
        if not battle_data:
            await query.edit_message_text("Erro ao iniciar sua batalha. Tente entrar novamente.", reply_markup=_get_game_over_keyboard())
            return
            
        media_key = battle_data['current_mob']['media_key']
        file_data = file_ids.get_file_data(media_key)
        
        if not file_data or not file_data.get("id"):
            await query.message.edit_text("Erro: Mídia do monstro não encontrada.")
            return

        caption = _format_battle_caption(battle_data, player_data)
        
        await query.message.delete()
        # Mudei para send_photo para garantir compatibilidade
        await context.bot.send_photo(
            chat_id=user_id, photo=file_data["id"], caption=caption, 
            reply_markup=_get_battle_keyboard(), parse_mode="HTML"
        )
    elif status == "waiting":
        status_text = event_manager.get_queue_status_text()
        text = f"🛡️ Fila de Reforços 🛡️\n\nAinda aguardando vaga...\n\n{status_text}"
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
    application.add_handler(CallbackQueryHandler(show_skill_menu, pattern='^show_skill_menu$'))
    application.add_handler(CallbackQueryHandler(back_to_battle, pattern='^back_to_battle$'))
    application.add_handler(CallbackQueryHandler(use_skill_handler, pattern='^use_skill:'))
    application.add_handler(CallbackQueryHandler(apply_skill_handler, pattern='^apply_skill:'))
