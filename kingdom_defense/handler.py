# Arquivo: kingdom_defense/handler.py (VERSÃO FINAL CORRIGIDA)

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
from telegram.error import BadRequest
from modules.game_data.class_evolution import can_player_use_skill
from modules.auth_utils import get_current_player_id

logger = logging.getLogger(__name__)

DEFAULT_TEST_IMAGE_ID = "AgACAgEAAxkBAAIMYWkeGkMHPgg2krbl_XdLH-evWuSRAAI1C2sbRHzxRHd5LKc3RFg1AQADAgADeAADNgQ"
VICTORY_PHOTO_ID = "AgACAgEAAxkBAAIW52jztXfEWirRJSoo9yUx5pjGQ7u_AAInC2sbR-agR7yizwIUvB1jAQADAgADeQADNgQ" 

async def _safe_interface_update(query, context, user_id, caption, media_key, keyboard):
    file_data = file_ids.get_file_data(media_key) if media_key else None
    specific_file_id = file_data.get("id") if file_data else None
    reply_markup = keyboard
    if specific_file_id:
        try:
            media = InputMediaPhoto(media=specific_file_id, caption=caption, parse_mode="HTML")
            msg = await query.edit_message_media(media=media, reply_markup=reply_markup)
            event_manager.store_player_message_id(user_id, msg.message_id)
            return
        except BadRequest as e:
            if "not modified" in str(e): return
    if DEFAULT_TEST_IMAGE_ID:
        try:
            media = InputMediaPhoto(media=DEFAULT_TEST_IMAGE_ID, caption=caption, parse_mode="HTML")
            msg = await query.edit_message_media(media=media, reply_markup=reply_markup)
            event_manager.store_player_message_id(user_id, msg.message_id)
            return
        except Exception: pass
    try:
        if query.message.photo:
            await query.edit_message_caption(caption=caption, reply_markup=reply_markup, parse_mode="HTML")
        else:
            await query.edit_message_text(text=caption, reply_markup=reply_markup, parse_mode="HTML")
    except BadRequest as e:
        if "not modified" in str(e): return
        try:
            await query.message.delete()
            if DEFAULT_TEST_IMAGE_ID:
                msg = await context.bot.send_photo(chat_id=user_id, photo=DEFAULT_TEST_IMAGE_ID, caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            else:
                msg = await context.bot.send_message(chat_id=user_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")
            event_manager.store_player_message_id(user_id, msg.message_id)
        except Exception as e_final:
            logger.error(f"Erro crítico na interface: {e_final}")

async def _safe_send_new_message(context, user_id, caption, media_key, keyboard, delete_msg=None):
    if delete_msg:
        try: await delete_msg.delete()
        except: pass
    file_data = file_ids.get_file_data(media_key) if media_key else None
    specific_file_id = file_data.get("id") if file_data else None
    if specific_file_id:
        try:
            msg = await context.bot.send_photo(chat_id=user_id, photo=specific_file_id, caption=caption, reply_markup=keyboard, parse_mode="HTML")
            event_manager.store_player_message_id(user_id, msg.message_id)
            return
        except Exception: pass 
    if DEFAULT_TEST_IMAGE_ID:
        try:
            msg = await context.bot.send_photo(chat_id=user_id, photo=DEFAULT_TEST_IMAGE_ID, caption=caption, reply_markup=keyboard, parse_mode="HTML")
            event_manager.store_player_message_id(user_id, msg.message_id)
            return
        except Exception: pass 
    try:
        msg = await context.bot.send_message(chat_id=user_id, text=caption, reply_markup=keyboard, parse_mode="HTML")
        event_manager.store_player_message_id(user_id, msg.message_id)
    except Exception as e:
        logger.error(f"Falha total ao enviar mensagem para {user_id}: {e}")

def _get_player_skill_data_by_rarity(pdata: dict, skill_id: str) -> dict | None:
    base_skill = SKILL_DATA.get(skill_id)
    if not base_skill: return None
    merged_data = base_skill.copy()
    if "rarity_effects" in base_skill:
        player_skills = pdata.get("skills", {})
        rarity = "comum"
        if isinstance(player_skills, dict):
            player_skill_instance = player_skills.get(skill_id)
            if player_skill_instance: rarity = player_skill_instance.get("rarity", "comum")
        rarity_data = base_skill["rarity_effects"].get(rarity, base_skill["rarity_effects"].get("comum", {}))
        merged_data.update(rarity_data)
    player_class = (pdata.get("class_key") or pdata.get("class") or "").lower()
    high_mana_classes = ["mago", "feiticeiro", "elementalista", "arquimago"]
    if player_class in high_mana_classes:
        original_cost = merged_data.get("mana_cost", 0)
        new_cost = int(original_cost * 2.0) 
        merged_data["mana_cost"] = new_cost
    return merged_data

def _format_battle_caption(player_state: dict, player_data: dict, total_stats: dict) -> str:
    mob = player_state['current_mob']
    action_log = player_state.get('action_log', '')
    p_name = player_data.get('character_name', 'Herói')
    current_hp = player_state.get('player_hp', 0)
    max_hp = int(total_stats.get('max_hp', 0))
    current_mp = player_state.get('player_mp', 0) 
    max_mp = int(total_stats.get('max_mana', 0))
    
    p_hp_str = f"❤️ HP: {current_hp}/{max_hp}"
    p_mp_str = f"💙 MP: {current_mp}/{max_mp}"
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
    
    col_width = 14 
    p_row1 = f"{p_hp_str.ljust(col_width)}{p_mp_str.ljust(col_width)}"
    p_row2 = f"{p_atk_str.ljust(col_width)}{p_def_str.ljust(col_width)}"
    p_row3 = f"{p_vel_str.ljust(col_width)}{p_srt_str.ljust(col_width)}"
    m_row1 = f"{m_hp_str.ljust(col_width)}{m_atk_str.ljust(col_width)}"
    m_row2 = f"{m_def_str.ljust(col_width)}{m_vel_str.ljust(col_width)}"
    m_row3 = f"{m_srt_str.ljust(col_width)}"

    current_wave = player_state.get('current_wave', 1)
    progress_text = event_manager.get_queue_status_text().replace('\n', ' | ')

    max_width = (col_width * 2) 
    wave_text = f"🌊 ONDA {current_wave} 🌊"
    header = f"╔{wave_text.center(max_width, '═')}╗"
    vs_separator = " 𝐕𝐒 ".center(max_width, '─')
    footer_text = " ◆◈◆ "
    footer = f"╚{footer_text.center(max_width, '═')}╝"
    
    log_section = "Aguardando sua ação..."
    if action_log: log_section = html.escape(action_log)

    final_caption = (
        f"<code>{header}\n{progress_text.center(max_width + 2)}\n{'─' * (max_width + 2)}\n"
        f"{p_name.center(max_width + 2)}\n{p_row1}\n{p_row2}\n{p_row3}\n\n"
        f"{vs_separator}\n\n{m_name.center(max_width + 2)}\n"
        f"{m_row1}\n{m_row2}\n{m_row3}\n{footer}</code>\n\n"
        f"<b>Última Ação:</b>\n<code>{log_section}</code>"
    )
    return final_caption

def _get_battle_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("💥 Atacar", callback_data='kd_marathon_attack'), InlineKeyboardButton("✨ Skills", callback_data='show_skill_menu')],
        [InlineKeyboardButton("📊 Status", callback_data='kd_show_battle_status'), InlineKeyboardButton("🏆 Ranking", callback_data='kd_show_leaderboard')]
    ]
    return InlineKeyboardMarkup(keyboard)

def _get_waiting_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Atualizar Status", callback_data='kd_check_queue_status')]])

def _get_game_over_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🚪 Sair do Evento", callback_data='kd_exit_event')],
        [InlineKeyboardButton("🏆 Ver Ranking Final", callback_data='kd_show_leaderboard')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def handle_exit_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Saindo do campo de batalha...")
    
    try:
        await query.message.delete()
    except:
        pass

    await show_kingdom_menu(update, context)

async def _get_target_selection_keyboard(user_id: int, skill_id: str) -> InlineKeyboardMarkup:
    active_fighters_ids = list(event_manager.active_fighters)
    keyboard = []
    target_list = []
    for fighter_id in active_fighters_ids:
        player_data = await player_manager.get_player_data(fighter_id)
        player_state = event_manager.get_battle_data(fighter_id)
        if not player_data or not player_state: continue
        current_hp = player_state.get('player_hp', 0)
        max_hp = player_state.get('player_max_hp', 1)
        hp_percent = (current_hp / max_hp) * 100 if max_hp > 0 else 0
        target_list.append({
            "id": fighter_id,
            "name": player_data.get('character_name', f'Herói {fighter_id}'),
            "hp_str": f"HP: {current_hp}/{max_hp}",
            "hp_percent": hp_percent
        })
    sorted_targets = sorted(target_list, key=lambda t: t['hp_percent'])
    for target in sorted_targets:
        button_text = f"🛡️ {target['name']} ({target['hp_str']})"
        callback_data = f"apply_skill:{skill_id}:{target['id']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="show_skill_menu")])
    return InlineKeyboardMarkup(keyboard)

async def _resolve_battle_turn(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, result: dict):
    user_id = query.from_user.id
    if "aoe_results" in result:
        for event in result["aoe_results"]:
            affected_id = event["user_id"]
            if affected_id == user_id: continue
            try:
                affected_player_data = await player_manager.get_player_data(affected_id) 
                affected_player_state = event_manager.get_battle_data(affected_id)
                if not affected_player_data or not affected_player_state: continue
                message_to_edit_id = affected_player_state.get('message_id')
                if not message_to_edit_id: continue
                affected_player_stats = await player_manager.get_player_total_stats(affected_player_data)
                if event["was_defeated"]:
                    caption = "☠️ <b>FIM DE JOGO</b> ☠️\n\nVocê foi derrotado por um ataque em área do chefe."
                    try: await context.bot.edit_message_caption(chat_id=affected_id, message_id=message_to_edit_id, caption=caption, reply_markup=_get_game_over_keyboard(), parse_mode='HTML')
                    except: pass
                else:
                    new_caption = _format_battle_caption(affected_player_state, affected_player_data, affected_player_stats) 
                    try: await context.bot.edit_message_caption(chat_id=affected_id, message_id=message_to_edit_id, caption=new_caption, reply_markup=_get_battle_keyboard(), parse_mode='HTML')
                    except: pass
            except Exception as e: logger.error(f"Falha ao notificar jogador passivo {affected_id}: {e}")

    # -------------------------------------------------------------------------
    # 1. VERIFICAÇÃO DE VITÓRIA (FIM DO EVENTO)
    # -------------------------------------------------------------------------
    if result.get("event_over"):
        final_log = result.get("action_log", "")
        victory_caption = f"🏆 <b>VITÓRIA!</b> 🏆\n\nO reino está a salvo!\n\n<i>Últimas ações:\n{html.escape(final_log)}</i>"
        
        try:
            # Tenta editar a mensagem atual trocando a foto pela de vitória
            media_victory = InputMediaPhoto(media=VICTORY_PHOTO_ID, caption=victory_caption, parse_mode='HTML')
            await query.edit_message_media(media=media_victory, reply_markup=_get_game_over_keyboard())
        except Exception:
            # Fallback: Se não der para editar (ex: imagem antiga expirou), apaga e envia nova
            try: await query.message.delete()
            except: pass
            await context.bot.send_photo(
                chat_id=user_id, 
                photo=VICTORY_PHOTO_ID, 
                caption=victory_caption, 
                reply_markup=_get_game_over_keyboard(), 
                parse_mode='HTML'
            )
        return

    # -------------------------------------------------------------------------
    # 2. VERIFICAÇÃO DE DERROTA (GAME OVER DO JOGADOR)
    # -------------------------------------------------------------------------
    # Verifica se morreu por ataque normal OU por dano em área (AOE)
    is_player_defeated = result.get("game_over") or (
        "aoe_results" in result and 
        any(e['user_id'] == user_id and e['was_defeated'] for e in result["aoe_results"])
    )

    if is_player_defeated:
        final_log = result.get('action_log', 'Você foi derrotado.')
        caption = f"☠️ <b>FIM DE JOGO</b> ☠️\n\nSua jornada na defesa chegou ao fim.\n\n<b>Última Ação:</b>\n<code>{html.escape(final_log)}</code>"
        
        try: 
            # Tenta pegar a imagem de caveira/game over
            defeat_media_id = file_ids.get_file_id('game_over_skull')
            
            if defeat_media_id:
                media = InputMediaPhoto(media=defeat_media_id, caption=caption, parse_mode="HTML")
                await query.edit_message_media(media=media, reply_markup=_get_game_over_keyboard())
            else: 
                raise ValueError("Imagem de Game Over não encontrada")
        except Exception:
            # Fallback 1: Tenta editar apenas a legenda mantendo a imagem atual
            try: 
                await query.edit_message_caption(caption=caption, reply_markup=_get_game_over_keyboard(), parse_mode='HTML')
            except: 
                # Fallback 2: Se não tiver imagem, edita o texto
                try: 
                    await query.edit_message_text(text=caption, reply_markup=_get_game_over_keyboard(), parse_mode='HTML')
                except: pass
        return

    player_data = await player_manager.get_player_data(user_id) 
    player_full_stats = await player_manager.get_player_total_stats(player_data)

    if result.get("monster_defeated"):
        await query.answer(f"Inimigo derrotado! {result.get('loot_message', '')}", cache_time=1)
        player_state = event_manager.get_battle_data(user_id)
        if not player_data or not player_state:
             try: await query.edit_message_text(text="Erro ao carregar dados.", reply_markup=_get_game_over_keyboard())
             except: pass
             return
        player_state['action_log'] = result.get('action_log', '')
        caption = _format_battle_caption(player_state, player_data, player_full_stats) 
        media_key = player_state['current_mob'].get('media_key')
        file_data = file_ids.get_file_data(media_key) if media_key else None
        if file_data and file_data.get("id"):
             try:
                 media = InputMediaPhoto(media=file_data["id"], caption=caption, parse_mode="HTML")
                 edited_msg = await query.edit_message_media(media=media, reply_markup=_get_battle_keyboard())
                 event_manager.store_player_message_id(user_id, edited_msg.message_id)
                 return
             except Exception as e: logger.error(f"Falha ao trocar mídia: {e}. Fallback.")
        try: await query.message.delete()
        except: pass 
        try:
            if file_data and file_data.get("id"):
                new_msg = await context.bot.send_photo(chat_id=user_id, photo=file_data["id"], caption=caption, reply_markup=_get_battle_keyboard(), parse_mode="HTML")
            else:
                new_msg = await context.bot.send_message(chat_id=user_id, text=caption, reply_markup=_get_battle_keyboard(), parse_mode="HTML")
            event_manager.store_player_message_id(user_id, new_msg.message_id)
        except Exception:
            await context.bot.send_message(chat_id=user_id, text="Erro visual. Digite /start.", parse_mode="HTML")
        return
    else:
        player_state = event_manager.get_battle_data(user_id)
        if player_state and player_data:
            player_state['action_log'] = result.get('action_log', '')
            caption = _format_battle_caption(player_state, player_data, player_full_stats) 
            try:
                if query.message.photo: await query.edit_message_caption(caption=caption, reply_markup=_get_battle_keyboard(), parse_mode='HTML')
                else: await query.edit_message_text(text=caption, reply_markup=_get_battle_keyboard(), parse_mode='HTML')
            except Exception as e:
                if "not modified" not in str(e): logger.warning(f"Erro ao atualizar turno: {e}")
        elif not player_state:
             try: await query.edit_message_caption(caption="A batalha terminou.", reply_markup=_get_game_over_keyboard())
             except: pass

# =============================================================================
# HANDLERS DE SKILLS CORRIGIDOS
# =============================================================================

async def show_skill_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # 1. Responde imediatamente para parar o "reloginho" de carregamento
    try: await query.answer()
    except: pass
    
    user_id = query.from_user.id
    player_data = await player_manager.get_player_data(user_id) 
    if not player_data: return
    
    # Previne erro se o player não tiver classe definida (comum em ADMs ou contas novas)
    player_class = (player_data.get("class_key") or player_data.get("class") or "aventureiro").lower()
    
    # Garante que equipped_skills seja uma lista
    equipped_skills = player_data.get("equipped_skills", [])
    if not equipped_skills:
        # Tenta pegar todas as skills se não tiver nenhuma equipada (fallback)
        if player_data.get("skills"):
            equipped_skills = list(player_data["skills"].keys())
        else:
            await query.answer("Nenhuma habilidade aprendida!", show_alert=True)
            return

    active_cooldowns = player_data.get("cooldowns", {})
    current_mana = player_data.get("mana", 0)
    
    keyboard = []
    
    for skill_id in equipped_skills:
        # Usa a função local que lida com raridade
        skill_info = _get_player_skill_data_by_rarity(player_data, skill_id)
        
        # Pula se a skill não existir ou for passiva
        if not skill_info or skill_info.get("type") == "passive": 
            continue 

        # --- PROTEÇÃO CONTRA ERRO DE CLASSE ---
        allowed_classes = skill_info.get("allowed_classes", [])
        try:
            # Se a lista de permitidos não for vazia, verifica se pode usar
            if allowed_classes and can_player_use_skill:
                if not can_player_use_skill(player_class, allowed_classes):
                    continue 
        except Exception as e:
            # Se der erro na verificação (ex: função não existe), PERMITE o uso para não travar
            logger.error(f"Erro ao verificar classe da skill {skill_id}: {e}")
        # ----------------------------------------

        mana_cost = skill_info.get('mana_cost', 0)
        turns_left = active_cooldowns.get(skill_id, 0)
        
        # Formata o texto do botão
        status_icon = "💥"
        if turns_left > 0:
            status_icon = f"⏳ ({turns_left})"
        elif current_mana < mana_cost:
            status_icon = "💧" # Sem mana
            
        button_text = f"{status_icon} {skill_info['display_name']} ({mana_cost} MP)"
        
        # Lógica de alvo (Single Target vs Auto)
        skill_type = skill_info.get("type", "active")
        is_single_target = skill_type == "support_heal" # Exemplo de target manual
        
        callback_action = ""
        if turns_left > 0:
            # Botão de cooldown (apenas informativo)
            callback_action = f"kd_cooldown_alert:{turns_left}" 
        elif current_mana < mana_cost:
            # Botão de sem mana
            callback_action = "kd_no_mana_alert"
        else:
            if is_single_target:
                callback_action = f"select_target:{skill_id}"
            else:
                callback_action = f"use_skill:{skill_id}"
                
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_action)])
    
    # Se depois de filtrar não sobrou nada
    if not keyboard:
        keyboard.append([InlineKeyboardButton("🚫 Nenhuma skill ativa disponível", callback_data="noop")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="back_to_battle")])
    
    text_content = f"<b>Menu de Habilidades</b>\nClasse: {player_class.title()}\nMana: {current_mana}\n\nEscolha uma habilidade:"
    
    try:
        if query.message.photo: 
            await query.edit_message_caption(caption=text_content, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        else: 
            await query.edit_message_text(text=text_content, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Erro ao exibir menu de skills: {e}")
        # Tenta mandar uma mensagem nova se a edição falhar
        await context.bot.send_message(chat_id=user_id, text="Erro ao abrir skills. Tente novamente.", parse_mode="HTML")

async def select_skill_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    try: skill_id = query.data.split(':')[1]
    except: await query.answer("Erro na skill.", show_alert=True); return
    
    player_data = await player_manager.get_player_data(user_id)
    skill_info = _get_player_skill_data_by_rarity(player_data, skill_id)
    if not skill_info: await query.answer("Habilidade desconhecida.", show_alert=True); return
        
    mana_cost = skill_info.get("mana_cost", 0)
    if player_data.get("mana", 0) < mana_cost:
        await query.answer(f"Mana insuficiente! Precisa de {mana_cost}.", show_alert=True); return
        
    target_keyboard = await _get_target_selection_keyboard(user_id, skill_id)
    caption = f"🛡️ **{skill_info['display_name']}** ({mana_cost} MP)\n\nEscolha o aliado:"
    if query.message.photo: await query.edit_message_caption(caption=caption, reply_markup=target_keyboard, parse_mode="HTML")
    else: await query.edit_message_text(text=caption, reply_markup=target_keyboard, parse_mode="HTML")

async def back_to_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    player_data = await player_manager.get_player_data(user_id)
    total_stats = await player_manager.get_player_total_stats(player_data)
    battle_data = event_manager.get_battle_data(user_id)
    if not battle_data or not player_data:
        try: await query.edit_message_caption(caption="Batalha encerrada.", reply_markup=_get_game_over_keyboard())
        except: pass
        return
    caption = _format_battle_caption(battle_data, player_data, total_stats) 
    if query.message.photo: await query.edit_message_caption(caption=caption, reply_markup=_get_battle_keyboard(), parse_mode="HTML")
    else: await query.edit_message_text(text=caption, reply_markup=_get_battle_keyboard(), parse_mode="HTML")

async def handle_marathon_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    now = time.time()
    last_attack_time = context.user_data.get('kd_last_attack_time', 0)
    if now - last_attack_time < 2.0: await query.answer("Aguarde!", cache_time=1); return
    context.user_data['kd_last_attack_time'] = now
    await query.answer()

    try:
        player_data = await player_manager.get_player_data(user_id) 
        if not player_data: return
        player_full_stats = await player_manager.get_player_total_stats(player_data) 
        result = await event_manager.process_player_attack(user_id, player_data, player_full_stats) 
        if not result: return
        if "error" in result: await query.answer(result["error"], show_alert=True); return
        
        await _resolve_battle_turn(query, context, result) 
    except Exception as e:
        logger.error(f"Erro CRÍTICO em attack: {e}", exc_info=True)
        await query.answer("Erro no ataque.", show_alert=True)

async def use_skill_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    now = time.time()
    
    # Controle de Spam (Cooldown de clique)
    last_action_time = context.user_data.get('kd_last_action_time', 0)
    if now - last_action_time < 2.0: 
        await query.answer("Aguarde!", cache_time=1)
        return
    context.user_data['kd_last_action_time'] = now
    
    # Tenta extrair o ID da skill do botão
    try: 
        skill_id = query.data.split(':')[1]
    except (IndexError, AttributeError): 
        return

    # Carrega dados do jogador
    player_data = await player_manager.get_player_data(user_id) 
    if not player_data: 
        return

    # Carrega dados da skill com raridade para verificar custo de mana
    skill_info = _get_player_skill_data_by_rarity(player_data, skill_id)
    if not skill_info: 
        await query.answer("Erro: Habilidade não encontrada.", show_alert=True)
        return

    # Verificação de Mana
    mana_cost = skill_info.get("mana_cost", 0)
    current_mana = player_data.get("mana", 0)
    if current_mana < mana_cost:
        await query.answer(f"Mana insuficiente! ({current_mana}/{mana_cost})", show_alert=True)
        return

    # Confirma o clique para a UI parar de carregar
    await query.answer()
    
    try:
        # Processa a skill no engine
        result = await event_manager.process_player_skill(user_id, player_data, skill_id)
        
        # Se o engine retornou erro explícito (ex: Cooldown)
        if "error" in result:
            await query.answer(result["error"], show_alert=True)
            return

        # Resolve o turno (atualiza a mensagem com log de batalha e dano)
        await _resolve_battle_turn(query, context, result)
        
    except Exception as e:
        logger.error(f"Erro crítico ao usar skill {skill_id}: {e}", exc_info=True)
        await query.answer("Ocorreu um erro ao executar a habilidade.", show_alert=True)

async def apply_skill_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    now = time.time()
    last_action_time = context.user_data.get('kd_last_action_time', 0)
    if now - last_action_time < 2.0: await query.answer("Aguarde!", cache_time=1); return
    context.user_data['kd_last_action_time'] = now

    try:
        _, skill_id, target_id_str = query.data.split(':')
        target_id = int(target_id_str)
        player_data = await player_manager.get_player_data(user_id)
        if not player_data: return
        skill_info = _get_player_skill_data_by_rarity(player_data, skill_id)
        if skill_info and player_data.get("mana", 0) < skill_info.get("mana_cost", 0):
            await query.answer("Mana insuficiente!", show_alert=True); return

        await query.answer()
        result = await event_manager.process_player_skill(user_id, player_data, skill_id, target_id=target_id)
        
        # CORREÇÃO IMPORTANTE: Checa erro antes de atualizar UI
        if "error" in result:
            await query.answer(result["error"], show_alert=True)
            return

        await _resolve_battle_turn(query, context, result)
    except Exception:
        traceback.print_exc()
        await query.answer("Erro ao aplicar skill.", show_alert=True)

async def show_battle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    status_text = event_manager.get_queue_status_text()
    await query.answer(text=status_text, show_alert=True, cache_time=5)

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    leaderboard_text = await event_manager.get_leaderboard_text() 
    await query.answer(text=leaderboard_text, show_alert=True, cache_time=5)

async def back_to_kingdom_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_kingdom_menu(update, context)

async def show_event_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query: await query.answer()
    caption = "📢 **EVENTO: DEFESA DO REINO**\n\n"
    keyboard = []
    if event_manager.is_active:
        caption += "Uma invasão ameaça o reino!\n\n" + event_manager.get_queue_status_text()
        keyboard.append([InlineKeyboardButton("⚔️ PARTICIPAR", callback_data='kd_join_and_start')])
    else: caption += "Sem invasões no momento."
    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data='kd_back_to_kingdom')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        if query and (query.message.photo or query.message.animation):
            await query.edit_message_caption(caption=caption, reply_markup=reply_markup, parse_mode='HTML')
        elif query:
            await query.edit_message_text(text=caption, reply_markup=reply_markup, parse_mode='HTML')
    except: pass

async def handle_join_and_start_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return
    if player_data.get('inventory', {}).get('ticket_defesa_reino', 0) <= 0:
        await query.answer("Sem Ticket!", show_alert=True); return

    await query.answer("Entrando...")
    if not event_manager.is_active:
        await query.edit_message_text("Evento encerrado.", reply_markup=_get_game_over_keyboard()); return

    player_manager.remove_item_from_inventory(player_data, 'ticket_defesa_reino', 1)
    await player_manager.save_player_data(user_id, player_data)
    status = await event_manager.add_player_to_event(user_id, player_data) 
    
    if status == "active":
        stats = await player_manager.get_player_total_stats(player_data) 
        bdata = event_manager.get_battle_data(user_id)
        if not bdata: return
        await _safe_send_new_message(context, user_id, _format_battle_caption(bdata, player_data, stats), bdata['current_mob'].get('media_key'), _get_battle_keyboard(), delete_msg=query.message)
    elif status == "waiting":
        text = f"🛡️ Fila de Reforços\n\nAguarde.\n{event_manager.get_queue_status_text()}"
        await query.edit_message_text(text=text, reply_markup=_get_waiting_keyboard(), parse_mode='HTML')

async def check_queue_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    if not event_manager.is_active:
        await query.edit_message_text("Evento encerrado.", reply_markup=_get_game_over_keyboard()); return

    status = event_manager.get_player_status(user_id)
    if status == "active":
        await query.answer("Sua vez!", show_alert=True)
        player_data = await player_manager.get_player_data(user_id)
        stats = await player_manager.get_player_total_stats(player_data)
        bdata = event_manager.get_battle_data(user_id)
        if not bdata: return
        await _safe_send_new_message(context, user_id, _format_battle_caption(bdata, player_data, stats), bdata['current_mob'].get('media_key'), _get_battle_keyboard(), delete_msg=query.message)
    elif status == "waiting":
        await query.edit_message_text(text=f"Ainda na fila...\n{event_manager.get_queue_status_text()}", reply_markup=_get_waiting_keyboard(), parse_mode='HTML')
        await query.answer("Aguarde.")
    else: await show_event_menu(update, context)

async def alert_cooldown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    turns = query.data.split(":")[1]
    await query.answer(f"Habilidade recarregando! Aguarde {turns} turnos.", show_alert=True)

async def alert_no_mana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Mana insuficiente!", show_alert=True)

def register_handlers(application):
    application.add_handler(CallbackQueryHandler(show_event_menu, pattern='^defesa_reino_main$'))
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
    application.add_handler(CallbackQueryHandler(select_skill_target, pattern='^select_target:'))
    application.add_handler(CallbackQueryHandler(handle_exit_event, pattern='^kd_exit_event$'))
    application.add_handler(CallbackQueryHandler(alert_cooldown, pattern='^kd_cooldown_alert:'))
    application.add_handler(CallbackQueryHandler(alert_no_mana, pattern='^kd_no_mana_alert$'))
