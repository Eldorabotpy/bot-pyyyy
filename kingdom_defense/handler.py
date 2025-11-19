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

logger = logging.getLogger(__name__)

DEFAULT_TEST_IMAGE_ID = "AgACAgEAAxkBAAEBJQZpHhr7_zu4XnDpjycGn9NwtESL-QACNQtrG0R88USiJW8fbwu24gEAAwIAA3gAAzYE"
VICTORY_PHOTO_ID = "AgACAgEAAxkBAAIW52jztXfEWirRJSoo9yUx5pjGQ7u_AAInC2sbR-agR7yizwIUvB1jAQADAgADeQADNgQ" 


async def _safe_interface_update(query, context, user_id, caption, media_key, keyboard):
    """
    Tenta atualizar a interface na seguinte ordem:
    1. Mídia Específica (Monstro atual)
    2. Mídia Genérica (DEFAULT_TEST_IMAGE_ID)
    3. Apenas Texto (Se tudo falhar)
    """
    file_data = file_ids.get_file_data(media_key) if media_key else None
    specific_file_id = file_data.get("id") if file_data else None
    
    reply_markup = keyboard

    # --- TENTATIVA 1: Imagem Específica ---
    if specific_file_id:
        try:
            media = InputMediaPhoto(media=specific_file_id, caption=caption, parse_mode="HTML")
            msg = await query.edit_message_media(media=media, reply_markup=reply_markup)
            event_manager.store_player_message_id(user_id, msg.message_id)
            return
        except BadRequest as e:
            if "not modified" in str(e): return
            # Se falhar (Wrong File ID), cai para a próxima tentativa
    
    # --- TENTATIVA 2: Imagem Genérica (Para Testes) ---
    if DEFAULT_TEST_IMAGE_ID:
        try:
            media = InputMediaPhoto(media=DEFAULT_TEST_IMAGE_ID, caption=caption, parse_mode="HTML")
            msg = await query.edit_message_media(media=media, reply_markup=reply_markup)
            event_manager.store_player_message_id(user_id, msg.message_id)
            return
        except Exception:
            pass # Se falhar, cai para texto

    # --- TENTATIVA 3: Fallback para Texto ou Reenvio ---
    # Se chegamos aqui, não conseguimos editar a mídia.
    try:
        if query.message.photo:
            # Se a msg original é foto e não conseguimos trocar a foto, editamos só a legenda
            await query.edit_message_caption(caption=caption, reply_markup=reply_markup, parse_mode="HTML")
        else:
            # Se era texto, editamos o texto
            await query.edit_message_text(text=caption, reply_markup=reply_markup, parse_mode="HTML")
    except BadRequest as e:
        if "not modified" in str(e): return
        
        # Se deu erro de "Message content mismatch" (tentar editar texto numa foto ou vice-versa)
        # Apagamos e reenviamos.
        try:
            await query.message.delete()
            # Tenta enviar a genérica de novo como nova mensagem
            if DEFAULT_TEST_IMAGE_ID:
                msg = await context.bot.send_photo(chat_id=user_id, photo=DEFAULT_TEST_IMAGE_ID, caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            else:
                msg = await context.bot.send_message(chat_id=user_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")
            event_manager.store_player_message_id(user_id, msg.message_id)
        except Exception as e_final:
            logger.error(f"Erro crítico na interface: {e_final}")

async def _safe_send_new_message(context, user_id, caption, media_key, keyboard, delete_msg=None):
    """Envia uma NOVA mensagem com segurança (Mídia Específica -> Genérica -> Texto)."""
    # 1. Tenta apagar a mensagem anterior se solicitado
    if delete_msg:
        try: await delete_msg.delete()
        except: pass

    file_data = file_ids.get_file_data(media_key) if media_key else None
    specific_file_id = file_data.get("id") if file_data else None
    
    # 2. Tenta enviar foto específica do monstro
    if specific_file_id:
        try:
            msg = await context.bot.send_photo(chat_id=user_id, photo=specific_file_id, caption=caption, reply_markup=keyboard, parse_mode="HTML")
            event_manager.store_player_message_id(user_id, msg.message_id)
            return
        except Exception: pass # Falhou? Continua...
    
    # 3. Tenta enviar foto genérica de teste (Fallback)
    if DEFAULT_TEST_IMAGE_ID:
        try:
            msg = await context.bot.send_photo(chat_id=user_id, photo=DEFAULT_TEST_IMAGE_ID, caption=caption, reply_markup=keyboard, parse_mode="HTML")
            event_manager.store_player_message_id(user_id, msg.message_id)
            return
        except Exception: pass # Falhou? Continua...
    
    # 4. Último recurso: Envia apenas texto
    try:
        msg = await context.bot.send_message(chat_id=user_id, text=caption, reply_markup=keyboard, parse_mode="HTML")
        event_manager.store_player_message_id(user_id, msg.message_id)
    except Exception as e:
        logger.error(f"Falha total ao enviar mensagem para {user_id}: {e}")
        
# =============================================================================
# HELPER: Raridade de Skills (Essencial para custos e efeitos corretos)
# =============================================================================
def _get_player_skill_data_by_rarity(pdata: dict, skill_id: str) -> dict | None:
    base_skill = SKILL_DATA.get(skill_id)
    if not base_skill: return None
    if "rarity_effects" not in base_skill: return base_skill
    player_skills = pdata.get("skills", {})
    rarity = "comum"
    if isinstance(player_skills, dict):
        player_skill_instance = player_skills.get(skill_id)
        if player_skill_instance: rarity = player_skill_instance.get("rarity", "comum")
    merged_data = base_skill.copy()
    rarity_data = base_skill["rarity_effects"].get(rarity, base_skill["rarity_effects"].get("comum", {}))
    merged_data.update(rarity_data)
    return merged_data

def _strip_html_for_len(text: str) -> str:
    return re.sub('<[^<]+?>', '', text)

def _format_battle_caption(player_state: dict, player_data: dict, total_stats: dict) -> str:
    mob = player_state['current_mob']
    action_log = player_state.get('action_log', '')
    
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
    
    col_width = 16 
    p_row1 = f"{p_hp_str.ljust(col_width)}{p_mp_str.ljust(col_width)}"
    p_row2 = f"{p_atk_str.ljust(col_width)}{p_def_str.ljust(col_width)}"
    p_row3 = f"{p_vel_str.ljust(col_width)}{p_srt_str.ljust(col_width)}"

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

async def _get_target_selection_keyboard(user_id: int, skill_id: str) -> InlineKeyboardMarkup:
    """Gera um teclado com os aliados ativos como alvos de uma skill."""
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
    
    # --- 1. Notificação de AoE (Dano em área) ---
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
            except Exception as e:
                logger.error(f"Falha ao notificar jogador passivo {affected_id} sobre o AoE: {e}")

    # --- 2. Vitória Final ---
    if result.get("event_over"):
        final_log = result.get("action_log", "")
        victory_caption = f"🏆 <b>VITÓRIA!</b> 🏆\n\nO reino está a salvo!\n\n<i>Últimas ações:\n{html.escape(final_log)}</i>"
        
        try:
            media_victory = InputMediaPhoto(media=VICTORY_PHOTO_ID, caption=victory_caption, parse_mode='HTML')
            await query.edit_message_media(media=media_victory, reply_markup=_get_game_over_keyboard())
        except Exception:
            # Fallback: Apaga e reenvia para garantir
            try: await query.message.delete()
            except: pass
            await context.bot.send_photo(chat_id=user_id, photo=VICTORY_PHOTO_ID, caption=victory_caption, reply_markup=_get_game_over_keyboard(), parse_mode='HTML')
        return

    # --- 3. Derrota do Jogador ---
    is_player_defeated = result.get("game_over") or ("aoe_results" in result and any(e['user_id'] == user_id and e['was_defeated'] for e in result["aoe_results"]))
    if is_player_defeated:
        final_log = result.get('action_log', 'Você foi derrotado.')
        caption = f"☠️ <b>FIM DE JOGO</b> ☠️\n\nSua jornada na defesa chegou ao fim.\n\n<b>Última Ação:</b>\n<code>{html.escape(final_log)}</code>"
        try: 
            defeat_media_id = file_ids.get_file_id('game_over_skull')
            if defeat_media_id:
                media = InputMediaPhoto(media=defeat_media_id, caption=caption, parse_mode="HTML")
                await query.edit_message_media(media=media, reply_markup=_get_game_over_keyboard())
            else: raise ValueError("Sem media")
        except Exception:
            # Fallback: Apenas edita texto se a foto falhar
            try: await query.edit_message_caption(caption=caption, reply_markup=_get_game_over_keyboard(), parse_mode='HTML')
            except: 
                try: await query.edit_message_text(text=caption, reply_markup=_get_game_over_keyboard(), parse_mode='HTML')
                except: pass
        return

    player_data = await player_manager.get_player_data(user_id) 
    player_full_stats = await player_manager.get_player_total_stats(player_data)

    # --- 4. Monstro Derrotado (AQUI ESTAVA O ERRO) ---
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
        
        # Tenta editar suavemente
        if file_data and file_data.get("id"):
             try:
                 media = InputMediaPhoto(media=file_data["id"], caption=caption, parse_mode="HTML")
                 # Tenta editar a mídia existente
                 edited_msg = await query.edit_message_media(media=media, reply_markup=_get_battle_keyboard())
                 # Atualiza o ID da mensagem no banco (importante!)
                 event_manager.store_player_message_id(user_id, edited_msg.message_id)
                 return
             except Exception as e:
                 logger.error(f"Falha ao trocar mídia ({media_key}): {e}. Iniciando Fallback de Reenvio.")

        # FALLBACK DE REENVIO (Opção Nuclear)
        # Se chegamos aqui, a edição de mídia falhou ou não temos ID.
        # Apagamos a mensagem velha e enviamos uma nova para limpar qualquer erro de "tipo de mensagem".
        try:
            await query.message.delete()
        except Exception: 
            pass # Mensagem pode já ter sido apagada

        try:
            if file_data and file_data.get("id"):
                # Tenta enviar como foto
                new_msg = await context.bot.send_photo(
                    chat_id=user_id, photo=file_data["id"], caption=caption, 
                    reply_markup=_get_battle_keyboard(), parse_mode="HTML"
                )
            else:
                # Se não tem foto válida, envia como TEXTO (sempre funciona)
                new_msg = await context.bot.send_message(
                    chat_id=user_id, text=caption, 
                    reply_markup=_get_battle_keyboard(), parse_mode="HTML"
                )
            
            # Salva o novo ID da mensagem para o próximo turno
            event_manager.store_player_message_id(user_id, new_msg.message_id)
        
        except Exception as e:
            logger.error(f"Erro crítico no fallback de reenvio: {e}")
            await context.bot.send_message(chat_id=user_id, text="Erro visual na batalha. Digite /start para resetar.", parse_mode="HTML")
        return
    
    # --- 5. Turno Normal ---
    else:
        player_state = event_manager.get_battle_data(user_id)
        if player_state and player_data:
            player_state['action_log'] = result.get('action_log', '')
            caption = _format_battle_caption(player_state, player_data, player_full_stats) 
            
            # Tenta editar caption (se for foto)
            try:
                if query.message.photo:
                    await query.edit_message_caption(caption=caption, reply_markup=_get_battle_keyboard(), parse_mode='HTML')
                else:
                    await query.edit_message_text(text=caption, reply_markup=_get_battle_keyboard(), parse_mode='HTML')
            except Exception as e:
                # Ignora erro "not modified"
                if "not modified" not in str(e):
                    logger.warning(f"Erro ao atualizar turno: {e}")
        
        elif not player_state:
             try: await query.edit_message_caption(caption="A batalha terminou.", reply_markup=_get_game_over_keyboard())
             except: pass

# =============================================================================
# HANDLERS DE SKILLS CORRIGIDOS
# =============================================================================

async def show_skill_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    player_data = await player_manager.get_player_data(user_id) 
    if not player_data: return

    equipped_skills = player_data.get("equipped_skills", [])
    if not equipped_skills:
        await query.answer("Você não tem habilidades ativas EQUIPADAS! Equipe no menu de Classes.", show_alert=True)
        return

    keyboard, current_mana = [], player_data.get("mana", 0)
    
    for skill_id in equipped_skills:
        skill_info = _get_player_skill_data_by_rarity(player_data, skill_id)
        
        if not skill_info or skill_info.get("type", "unknown") not in ("active", "support_heal", "support_buff"):
            continue 
            
        mana_cost = skill_info.get('mana_cost', 0)
        is_single_target_support = skill_info.get("type") == "support_heal" 
        
        button_text_base = f"{skill_info['display_name']} ({mana_cost} MP)"
        
        if is_single_target_support:
            if current_mana < mana_cost:
                 button_text = f"❌ {button_text_base}"
            else:
                 button_text = f"🎯 {button_text_base}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"select_target:{skill_id}")])
        else:
            if current_mana < mana_cost:
                button_text = f"❌ {button_text_base}"
            else:
                button_text = button_text_base
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"use_skill:{skill_id}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="back_to_battle")])
    
    text_content = "<b>Menu de Habilidades</b>\n\nEscolha uma habilidade para usar:"
    
    # ✅ CORREÇÃO: Verifica se edita Caption (Foto) ou Texto (Sem foto)
    if query.message.photo:
        await query.edit_message_caption(caption=text_content, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await query.edit_message_text(text=text_content, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def select_skill_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    try:
        skill_id = query.data.split(':')[1]
    except IndexError:
        await query.answer("Erro: Skill não encontrada.", show_alert=True)
        return
    
    player_data = await player_manager.get_player_data(user_id)
    skill_info = _get_player_skill_data_by_rarity(player_data, skill_id)

    if not skill_info:
        await query.answer("Erro: Habilidade desconhecida.", show_alert=True)
        return
        
    mana_cost = skill_info.get("mana_cost", 0)
    if player_data.get("mana", 0) < mana_cost:
        await query.answer(f"Mana insuficiente! Precisa de {mana_cost}.", show_alert=True)
        return
        
    target_keyboard = await _get_target_selection_keyboard(user_id, skill_id)
    caption = f"🛡️ **{skill_info['display_name']}** ({mana_cost} MP)\n\nEscolha o aliado para curar ou dar suporte:"
    
    # ✅ CORREÇÃO: Verifica se edita Caption (Foto) ou Texto (Sem foto)
    if query.message.photo:
        await query.edit_message_caption(caption=caption, reply_markup=target_keyboard, parse_mode="HTML")
    else:
        await query.edit_message_text(text=caption, reply_markup=target_keyboard, parse_mode="HTML")

async def back_to_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    player_data = await player_manager.get_player_data(user_id)
    total_stats = await player_manager.get_player_total_stats(player_data)
    battle_data = event_manager.get_battle_data(user_id)

    if not battle_data or not player_data:
        # Fallback seguro para Game Over
        try:
            if query.message.photo:
                await query.edit_message_caption(caption="A batalha terminou.", reply_markup=_get_game_over_keyboard())
            else:
                await query.edit_message_text(text="A batalha terminou.", reply_markup=_get_game_over_keyboard())
        except:
            pass
        return

    caption = _format_battle_caption(battle_data, player_data, total_stats) 
    
    # ✅ CORREÇÃO: Verifica se edita Caption (Foto) ou Texto (Sem foto)
    if query.message.photo:
        await query.edit_message_caption(caption=caption, reply_markup=_get_battle_keyboard(), parse_mode="HTML")
    else:
        await query.edit_message_text(text=caption, reply_markup=_get_battle_keyboard(), parse_mode="HTML")

async def handle_marathon_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id

    now = time.time()
    last_attack_time = context.user_data.get('kd_last_attack_time', 0)

    if now - last_attack_time < 2.0:
        await query.answer("Aguarde um momento antes de atacar novamente!", cache_time=1)
        return
    context.user_data['kd_last_attack_time'] = now
    await query.answer()

    try:
        player_data = await player_manager.get_player_data(user_id) 
        if not player_data:
            await query.answer("Erro ao carregar dados do jogador.", show_alert=True)
            return

        player_full_stats = await player_manager.get_player_total_stats(player_data) 
        result = await event_manager.process_player_attack(user_id, player_data, player_full_stats) 

        if result is None:
            logger.error(f"process_player_attack retornou None para user_id {user_id}")
            await query.answer("Erro interno: O estado da batalha não foi retornado corretamente.", show_alert=True)
            return

        if "error" in result:
            await query.answer(result["error"], show_alert=True)
            return

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
                        caption = "☠️ FIM DE JOGO ☠️\n\nVocê foi derrotado por um ataque em área do chefe."
                        await context.bot.edit_message_caption(chat_id=affected_id, message_id=message_to_edit_id, caption=caption, reply_markup=_get_game_over_keyboard(), parse_mode='HTML')
                    else:
                        new_caption = _format_battle_caption(affected_player_state, affected_player_data, affected_player_stats) 
                        await context.bot.edit_message_caption(chat_id=affected_id, message_id=message_to_edit_id, caption=new_caption, reply_markup=_get_battle_keyboard(), parse_mode='HTML')
                except Exception as e:
                      logger.error(f"Falha ao notificar jogador passivo {affected_id} sobre o AoE: {e}")

        await _resolve_battle_turn(query, context, result) 

    except Exception as e:
        logger.error(f"Erro CRÍTICO em handle_marathon_attack: {e}", exc_info=True)
        await query.answer("Ocorreu um erro ao processar seu ataque.", show_alert=True)

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
        await query.answer("Erro: Skill não encontrada.", show_alert=True)
        return

    player_data = await player_manager.get_player_data(user_id) 
    if not player_data: 
         await query.answer("Erro ao carregar dados do jogador.", show_alert=True)
         return

    # ✅ CORREÇÃO: Usa o helper
    skill_info = _get_player_skill_data_by_rarity(player_data, skill_id)
    if not skill_info:
        await query.answer("Erro: Habilidade não encontrada!", show_alert=True)
        return
    
    # ✅ CORREÇÃO: Checa mana com o valor correto (raridade)
    if player_data.get("mana", 0) < skill_info.get("mana_cost", 0):
        await query.answer("Mana insuficiente!", show_alert=True)
        return

    await query.answer()
    # Importante: O 'event_manager.process_player_skill' deve descontar a mana. 
    # Se ele usar 'spend_mana' antigo (com await), pode dar erro lá, mas este handler está seguro.
    result = await event_manager.process_player_skill(user_id, player_data, skill_id)
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
        
        player_data = await player_manager.get_player_data(user_id)
        if not player_data: 
             await query.answer("Erro ao carregar dados do jogador.", show_alert=True)
             return

        # ✅ CORREÇÃO: Checagem de mana aqui também
        skill_info = _get_player_skill_data_by_rarity(player_data, skill_id)
        if skill_info and player_data.get("mana", 0) < skill_info.get("mana_cost", 0):
            await query.answer("Mana insuficiente!", show_alert=True)
            return

        await query.answer()
        result = await event_manager.process_player_skill(user_id, player_data, skill_id, target_id=target_id)
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
    leaderboard_text = await event_manager.get_leaderboard_text() 
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
        
        # ✅ USA A FUNÇÃO SEGURA
        await _safe_send_new_message(
            context, user_id, 
            _format_battle_caption(bdata, player_data, stats), 
            bdata['current_mob'].get('media_key'), 
            _get_battle_keyboard(),
            delete_msg=query.message # Apaga o menu anterior
        )
    
    elif status == "waiting":
        text = f"🛡️ Fila de Reforços 🛡️\n\nAguarde sua vez.\n{event_manager.get_queue_status_text()}"
        await query.edit_message_text(text=text, reply_markup=_get_waiting_keyboard(), parse_mode='HTML')

async def check_queue_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    if not event_manager.is_active:
        await query.edit_message_text("Evento encerrado.", reply_markup=_get_game_over_keyboard()); return

    status = event_manager.get_player_status(user_id)
    if status == "active":
        await query.answer("Sua vez!", show_alert=True)
        player_data = await player_manager.get_player_data(user_id)
        stats = await player_manager.get_player_total_stats(player_data)
        bdata = event_manager.get_battle_data(user_id)
        if not bdata: return
        
        # ✅ USA A FUNÇÃO SEGURA
        await _safe_send_new_message(
            context, user_id, 
            _format_battle_caption(bdata, player_data, stats), 
            bdata['current_mob'].get('media_key'), 
            _get_battle_keyboard(),
            delete_msg=query.message # Apaga a msg de "aguardando"
        )

    elif status == "waiting":
        await query.edit_message_text(text=f"Ainda na fila...\n{event_manager.get_queue_status_text()}", reply_markup=_get_waiting_keyboard(), parse_mode='HTML')
        await query.answer("Aguarde.")
    else: 
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
    application.add_handler(CallbackQueryHandler(select_skill_target, pattern='^select_target:'))