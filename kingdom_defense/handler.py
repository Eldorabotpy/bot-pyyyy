# Arquivo: kingdom_defense/handler.py
# (VERSÃO: DELETE & SEND - Sempre apaga a anterior e envia nova para evitar erros)

import logging
import html
import time
import traceback
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, CallbackQuery
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

# Módulos Internos
from .engine import event_manager
from modules import player_manager, file_ids
from handlers.menu.kingdom import show_kingdom_menu
from modules.game_data.skills import SKILL_DATA
from modules.game_data.class_evolution import can_player_use_skill
from modules.auth_utils import get_current_player_id

logger = logging.getLogger(__name__)

# Imagens de Fallback (Caso a media_key falhe ou não exista)
DEFAULT_TEST_IMAGE_ID = "AgACAgEAAxkBAAIMYWkeGkMHPgg2krbl_XdLH-evWuSRAAI1C2sbRHzxRHd5LKc3RFg1AQADAgADeAADNgQ"
VICTORY_PHOTO_ID = "AgACAgEAAxkBAAIW52jztXfEWirRJSoo9yUx5pjGQ7u_AAInC2sbR-agR7yizwIUvB1jAQADAgADeQADNgQ" 

# =============================================================================
# 🛠️ FUNÇÃO CENTRAL DE INTERFACE (DELETE & SEND)
# =============================================================================
async def _force_refresh_interface(context, player_id, chat_id, caption, media_key, keyboard, msg_to_delete=None):
    """
    1. Tenta deletar a mensagem anterior (se fornecida).
    2. Verifica se há mídia válida.
    3. Envia NOVA mensagem (Foto ou Texto).
    4. Atualiza o ID da mensagem no engine.
    """
    # 1. Deletar Anterior
    if msg_to_delete:
        try:
            await msg_to_delete.delete()
        except Exception:
            pass # Ignora se já foi deletada ou não pode ser deletada

    # 2. Preparar Mídia
    file_data = file_ids.get_file_data(media_key) if media_key else None
    specific_file_id = file_data.get("id") if file_data else None
    
    new_msg = None

    try:
        # Tenta enviar com a Mídia do Monstro
        if specific_file_id:
            new_msg = await context.bot.send_photo(
                chat_id=chat_id, 
                photo=specific_file_id, 
                caption=caption, 
                reply_markup=keyboard, 
                parse_mode="HTML"
            )
        
        # Se não tem mídia específica, tenta a imagem padrão de teste
        elif DEFAULT_TEST_IMAGE_ID:
            new_msg = await context.bot.send_photo(
                chat_id=chat_id, 
                photo=DEFAULT_TEST_IMAGE_ID, 
                caption=caption, 
                reply_markup=keyboard, 
                parse_mode="HTML"
            )
            
        # Se não tem imagem nenhuma configurada, envia apenas TEXTO
        else:
            new_msg = await context.bot.send_message(
                chat_id=chat_id, 
                text=caption, 
                reply_markup=keyboard, 
                parse_mode="HTML"
            )

        # 4. Registra no Engine para referência futura
        if new_msg:
            event_manager.store_player_message_id(player_id, new_msg.message_id)

    except Exception as e:
        logger.error(f"❌ Erro ao enviar interface para {player_id}: {e}")
        # Fallback final de emergência: Texto simples
        try:
            await context.bot.send_message(chat_id=chat_id, text=f"{caption}\n⚠️ Erro visual: {e}", reply_markup=keyboard)
        except: pass


# =============================================================================
# 🧩 HELPERS E FORMATADORES
# =============================================================================

def _get_player_skill_data_by_rarity(pdata: dict, skill_id: str) -> dict | None:
    # (Mantido igual)
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
    # (Mantido igual - Lógica de formatação de texto)
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

async def _get_target_selection_keyboard(player_id: str, skill_id: str) -> InlineKeyboardMarkup:
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
            "name": player_data.get('character_name', f'Herói'),
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

# =============================================================================
# 🎮 LÓGICA PRINCIPAL (RESOLVE BATTLE TURN)
# =============================================================================

async def _resolve_battle_turn(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, result: dict):
    player_id = get_current_player_id(Update(query.message.message_id), context)
    if not player_id: player_id = context.user_data.get("logged_player_id")
    
    # ID Numérico para envio de mensagens
    chat_id = query.from_user.id
    
    # --- 1. Notificações AOE (Para outros jogadores) ---
    if "aoe_results" in result:
        for event in result["aoe_results"]:
            affected_id = event["user_id"] # ObjectId String
            if affected_id == player_id: continue # Atualiza o player atual no fluxo normal
            
            try:
                # Carrega dados do alvo
                affected_player_data = await player_manager.get_player_data(affected_id) 
                affected_player_state = event_manager.get_battle_data(affected_id)
                if not affected_player_data or not affected_player_state: continue
                
                # Dados para envio
                affected_tg_id = affected_player_state.get('telegram_id') 
                affected_msg_id = affected_player_state.get('message_id')
                
                if not affected_tg_id: continue # Sem TG ID não tem como enviar
                
                affected_player_stats = await player_manager.get_player_total_stats(affected_player_data)
                
                # Cria objeto "fake" de mensagem para deletar (se tiver ID)
                msg_to_del = None
                # Nota: Não temos o objeto message real aqui facilmente, então o delete pode falhar se não usarmos bot.delete_message
                # Mas nossa função _force_refresh aceita msg_to_delete. Vamos tentar deletar via API.
                
                if event["was_defeated"]:
                    caption = "☠️ <b>FIM DE JOGO</b> ☠️\n\nVocê foi derrotado por um ataque em área do chefe."
                    # Força envio direto pois é outro usuário
                    try:
                        if affected_msg_id: await context.bot.delete_message(chat_id=affected_tg_id, message_id=affected_msg_id)
                        await context.bot.send_message(chat_id=affected_tg_id, text=caption, reply_markup=_get_game_over_keyboard(), parse_mode='HTML')
                    except: pass
                else:
                    new_caption = _format_battle_caption(affected_player_state, affected_player_data, affected_player_stats) 
                    media_key = affected_player_state['current_mob'].get('media_key')
                    
                    # Usa a função de refresh, mas precisamos passar None para msg_to_delete e deletar manualmente antes
                    if affected_msg_id: 
                        try: await context.bot.delete_message(chat_id=affected_tg_id, message_id=affected_msg_id)
                        except: pass
                        
                    await _force_refresh_interface(context, affected_id, affected_tg_id, new_caption, media_key, _get_battle_keyboard(), msg_to_delete=None)
                    
            except Exception as e: logger.error(f"Falha ao notificar jogador passivo {affected_id}: {e}")

    # --- 2. Vitória do Evento ---
    if result.get("event_over"):
        final_log = result.get("action_log", "")
        victory_caption = f"🏆 <b>VITÓRIA!</b> 🏆\n\nO reino está a salvo!\n\n<i>Últimas ações:\n{html.escape(final_log)}</i>"
        
        # Deleta anterior e manda a foto da vitória
        try: await query.message.delete()
        except: pass
        
        await context.bot.send_photo(chat_id=chat_id, photo=VICTORY_PHOTO_ID, caption=victory_caption, reply_markup=_get_game_over_keyboard(), parse_mode='HTML')
        return

    # --- 3. Derrota do Jogador ---
    is_player_defeated = result.get("game_over") or (
        "aoe_results" in result and 
        any(e['user_id'] == player_id and e['was_defeated'] for e in result["aoe_results"])
    )

    if is_player_defeated:
        final_log = result.get('action_log', 'Você foi derrotado.')
        caption = f"☠️ <b>FIM DE JOGO</b> ☠️\n\nSua jornada na defesa chegou ao fim.\n\n<b>Última Ação:</b>\n<code>{html.escape(final_log)}</code>"
        
        # Deleta e manda Game Over
        try: await query.message.delete()
        except: pass
        
        # Tenta mandar imagem de caveira se tiver, senão texto
        try:
            defeat_media_id = file_ids.get_file_id('game_over_skull')
            if defeat_media_id:
                await context.bot.send_photo(chat_id=chat_id, photo=defeat_media_id, caption=caption, reply_markup=_get_game_over_keyboard(), parse_mode="HTML")
            else:
                await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=_get_game_over_keyboard(), parse_mode="HTML")
        except:
             await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=_get_game_over_keyboard(), parse_mode="HTML")
        return

    # --- 4. Turno Normal (Monstro vivo ou Novo Monstro) ---
    player_data = await player_manager.get_player_data(player_id) 
    player_full_stats = await player_manager.get_player_total_stats(player_data)
    
    if result.get("monster_defeated"):
        # Se matou monstro, mostra notificação rápida
        await query.answer(f"Inimigo derrotado! {result.get('loot_message', '')}", cache_time=1)
    
    # Reconstrói a interface
    player_state = event_manager.get_battle_data(player_id)
    if not player_data or not player_state:
         # Se perdeu o estado, manda pro menu
         try: await query.message.delete()
         except: pass
         await show_kingdom_menu(Update(query.message.message_id), context) # Hack para voltar
         return

    # Atualiza o log no estado para ser exibido
    player_state['action_log'] = result.get('action_log', '')
    
    # Gera caption e pega imagem
    caption = _format_battle_caption(player_state, player_data, player_full_stats) 
    media_key = player_state['current_mob'].get('media_key')
    
    # ✅ AQUI ESTÁ A MÁGICA: CHAMA O REFRESH FORÇADO
    await _force_refresh_interface(
        context, 
        player_id, 
        chat_id, 
        caption, 
        media_key, 
        _get_battle_keyboard(), 
        msg_to_delete=query.message # Passa a mensagem atual para deletar
    )


# =============================================================================
# ⚔️ HANDLERS DE AÇÃO
# =============================================================================

async def handle_marathon_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    player_id = get_current_player_id(update, context)
    now = time.time()
    last_attack_time = context.user_data.get('kd_last_attack_time', 0)
    
    # Anti-Spam (2s)
    if now - last_attack_time < 2.0: 
        await query.answer("Aguarde...", cache_time=1)
        return
    context.user_data['kd_last_attack_time'] = now
    
    await query.answer() # Confirma clique para parar loading

    try:
        player_data = await player_manager.get_player_data(player_id) 
        if not player_data: return
        player_full_stats = await player_manager.get_player_total_stats(player_data) 
        
        # Processa Ataque
        result = await event_manager.process_player_attack(player_id, player_data, player_full_stats) 
        
        if not result: return
        if "error" in result: 
            await query.answer(result["error"], show_alert=True)
            return
        
        # Atualiza Interface
        await _resolve_battle_turn(query, context, result) 
    except Exception as e:
        logger.error(f"Erro CRÍTICO em attack: {e}", exc_info=True)
        await query.answer("Erro no ataque.", show_alert=True)

async def use_skill_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    player_id = get_current_player_id(update, context)
    now = time.time()
    last_action_time = context.user_data.get('kd_last_action_time', 0)
    
    if now - last_action_time < 2.0: 
        await query.answer("Aguarde...", cache_time=1)
        return
    context.user_data['kd_last_action_time'] = now
    
    try: skill_id = query.data.split(':')[1]
    except (IndexError, AttributeError): return

    # Validações Prévias
    player_data = await player_manager.get_player_data(player_id) 
    if not player_data: return
    skill_info = _get_player_skill_data_by_rarity(player_data, skill_id)
    if not skill_info: 
        await query.answer("Erro: Habilidade não encontrada.", show_alert=True)
        return

    mana_cost = skill_info.get("mana_cost", 0)
    current_mana = player_data.get("mana", 0)
    if current_mana < mana_cost: 
        await query.answer(f"Mana insuficiente! ({current_mana}/{mana_cost})", show_alert=True)
        return
        
    await query.answer()
    
    try:
        # Processa Skill
        result = await event_manager.process_player_skill(player_id, player_data, skill_id)
        if "error" in result: 
            await query.answer(result["error"], show_alert=True)
            return
            
        # Atualiza Interface
        await _resolve_battle_turn(query, context, result)
    except Exception as e:
        logger.error(f"Erro crítico ao usar skill {skill_id}: {e}", exc_info=True)
        await query.answer("Ocorreu um erro ao executar a habilidade.", show_alert=True)

async def apply_skill_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    player_id = get_current_player_id(update, context)
    
    # Anti-spam
    now = time.time()
    last_action_time = context.user_data.get('kd_last_action_time', 0)
    if now - last_action_time < 2.0: 
        await query.answer("Aguarde...", cache_time=1)
        return
    context.user_data['kd_last_action_time'] = now

    try:
        _, skill_id, target_id_str = query.data.split(':')
        target_id = str(target_id_str) 
        player_data = await player_manager.get_player_data(player_id)
        if not player_data: return
        
        skill_info = _get_player_skill_data_by_rarity(player_data, skill_id)
        if skill_info and player_data.get("mana", 0) < skill_info.get("mana_cost", 0):
            await query.answer("Mana insuficiente!", show_alert=True)
            return

        await query.answer()
        result = await event_manager.process_player_skill(player_id, player_data, skill_id, target_id=target_id)
        
        if "error" in result: 
            await query.answer(result["error"], show_alert=True)
            return
            
        await _resolve_battle_turn(query, context, result)
    except Exception:
        traceback.print_exc()
        await query.answer("Erro ao aplicar skill.", show_alert=True)

# =============================================================================
# 🚪 MENUS E OUTROS HANDLERS
# =============================================================================

async def handle_exit_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Saindo do campo de batalha...")
    try: await query.message.delete()
    except: pass
    await show_kingdom_menu(update, context)

async def show_skill_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    player_id = get_current_player_id(update, context)
    chat_id = query.from_user.id
    
    try: await query.answer()
    except: pass
    
    player_data = await player_manager.get_player_data(player_id) 
    if not player_data: return
    
    # ... (Lógica de construção do teclado de skills mantida) ...
    player_class = (player_data.get("class_key") or player_data.get("class") or "aventureiro").lower()
    equipped_skills = player_data.get("equipped_skills", [])
    if not equipped_skills:
        if player_data.get("skills"): equipped_skills = list(player_data["skills"].keys())
        else: await query.answer("Nenhuma habilidade aprendida!", show_alert=True); return

    active_cooldowns = player_data.get("cooldowns", {})
    current_mana = player_data.get("mana", 0)
    
    keyboard = []
    for skill_id in equipped_skills:
        skill_info = _get_player_skill_data_by_rarity(player_data, skill_id)
        if not skill_info or skill_info.get("type") == "passive": continue 
        allowed_classes = skill_info.get("allowed_classes", [])
        try:
            if allowed_classes and can_player_use_skill:
                if not can_player_use_skill(player_class, allowed_classes): continue 
        except: pass

        mana_cost = skill_info.get('mana_cost', 0)
        turns_left = active_cooldowns.get(skill_id, 0)
        status_icon = "💥"
        if turns_left > 0: status_icon = f"⏳ ({turns_left})"
        elif current_mana < mana_cost: status_icon = "💧"
        button_text = f"{status_icon} {skill_info['display_name']} ({mana_cost} MP)"
        
        is_single_target = skill_info.get("type") == "support_heal"
        
        callback_action = ""
        if turns_left > 0: callback_action = f"kd_cooldown_alert:{turns_left}" 
        elif current_mana < mana_cost: callback_action = "kd_no_mana_alert"
        else:
            if is_single_target: callback_action = f"select_target:{skill_id}"
            else: callback_action = f"use_skill:{skill_id}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_action)])
    
    if not keyboard: keyboard.append([InlineKeyboardButton("🚫 Nenhuma skill ativa disponível", callback_data="noop")])
    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="back_to_battle")])
    
    text_content = f"<b>Menu de Habilidades</b>\nClasse: {player_class.title()}\nMana: {current_mana}\n\nEscolha uma habilidade:"
    
    # Usa DELETE & SEND também para o menu de skills
    await _force_refresh_interface(
        context, player_id, chat_id, 
        text_content, None, # Sem imagem
        InlineKeyboardMarkup(keyboard), 
        msg_to_delete=query.message
    )

async def select_skill_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    player_id = get_current_player_id(update, context)
    chat_id = query.from_user.id
    
    try: skill_id = query.data.split(':')[1]
    except: await query.answer("Erro na skill.", show_alert=True); return
    
    player_data = await player_manager.get_player_data(player_id)
    skill_info = _get_player_skill_data_by_rarity(player_data, skill_id)
    if not skill_info: await query.answer("Habilidade desconhecida.", show_alert=True); return
        
    mana_cost = skill_info.get("mana_cost", 0)
    if player_data.get("mana", 0) < mana_cost:
        await query.answer(f"Mana insuficiente! Precisa de {mana_cost}.", show_alert=True); return
        
    target_keyboard = await _get_target_selection_keyboard(player_id, skill_id)
    caption = f"🛡️ **{skill_info['display_name']}** ({mana_cost} MP)\n\nEscolha o aliado:"
    
    # Delete & Send
    await _force_refresh_interface(context, player_id, chat_id, caption, None, target_keyboard, msg_to_delete=query.message)

async def back_to_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    player_id = get_current_player_id(update, context)
    chat_id = query.from_user.id
    
    player_data = await player_manager.get_player_data(player_id)
    total_stats = await player_manager.get_player_total_stats(player_data)
    battle_data = event_manager.get_battle_data(player_id)
    
    if not battle_data or not player_data:
        try: await query.message.delete()
        except: pass
        await show_kingdom_menu(update, context)
        return

    caption = _format_battle_caption(battle_data, player_data, total_stats) 
    media_key = battle_data['current_mob'].get('media_key')

    # Delete & Send (Retornando ao combate)
    await _force_refresh_interface(context, player_id, chat_id, caption, media_key, _get_battle_keyboard(), msg_to_delete=query.message)

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
    try: await query.message.delete()
    except: pass
    await show_kingdom_menu(update, context)

async def show_event_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query: await query.answer()
    
    caption = "📢 **EVENTO: DEFESA DO REINO**\n\n"
    keyboard = []
    if event_manager.is_active:
        caption += "Uma invasão ameaça o reino!\n\n" + event_manager.get_queue_status_text()
        keyboard.append([InlineKeyboardButton("⚔️ PARTICIPAR", callback_data='kd_join_and_start')])
    else: 
        caption += "Sem invasões no momento."
    
    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data='kd_back_to_kingdom')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Usa o refresh aqui também para limpar
    if query:
        # Pega player_id apenas para logar, pode ser null se for first access
        player_id = context.user_data.get("logged_player_id", "unknown")
        await _force_refresh_interface(context, player_id, query.from_user.id, caption, None, reply_markup, msg_to_delete=query.message)

async def handle_join_and_start_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    player_id = get_current_player_id(update, context) 
    tg_id = update.effective_user.id 
    
    player_data = await player_manager.get_player_data(player_id)
    if not player_data: return
    if player_data.get('inventory', {}).get('ticket_defesa_reino', 0) <= 0:
        await query.answer("Sem Ticket!", show_alert=True); return

    await query.answer("Entrando...")
    if not event_manager.is_active:
        await query.edit_message_text("Evento encerrado.", reply_markup=_get_game_over_keyboard()); return

    player_manager.remove_item_from_inventory(player_data, 'ticket_defesa_reino', 1)
    await player_manager.save_player_data(player_id, player_data)
    status = await event_manager.add_player_to_event(player_id, player_data) 
    
    if status == "active":
        stats = await player_manager.get_player_total_stats(player_data) 
        bdata = event_manager.get_battle_data(player_id)
        if not bdata: return
        
        # INICIO DA BATALHA: Apaga menu, manda foto
        caption = _format_battle_caption(bdata, player_data, stats)
        media_key = bdata['current_mob'].get('media_key')
        await _force_refresh_interface(context, player_id, tg_id, caption, media_key, _get_battle_keyboard(), msg_to_delete=query.message)
        
    elif status == "waiting":
        text = f"🛡️ Fila de Reforços\n\nAguarde.\n{event_manager.get_queue_status_text()}"
        # Fila é apenas texto
        await _force_refresh_interface(context, player_id, tg_id, text, None, _get_waiting_keyboard(), msg_to_delete=query.message)

async def check_queue_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    player_id = get_current_player_id(update, context)
    tg_id = update.effective_user.id
    
    if not event_manager.is_active:
        await query.edit_message_text("Evento encerrado.", reply_markup=_get_game_over_keyboard()); return

    status = event_manager.get_player_status(player_id)
    if status == "active":
        await query.answer("Sua vez!", show_alert=True)
        player_data = await player_manager.get_player_data(player_id)
        stats = await player_manager.get_player_total_stats(player_data)
        bdata = event_manager.get_battle_data(player_id)
        if not bdata: return
        
        # Entrou da fila para combate: Refresh com mídia
        caption = _format_battle_caption(bdata, player_data, stats)
        media_key = bdata['current_mob'].get('media_key')
        await _force_refresh_interface(context, player_id, tg_id, caption, media_key, _get_battle_keyboard(), msg_to_delete=query.message)
        
    elif status == "waiting":
        text = f"Ainda na fila...\n{event_manager.get_queue_status_text()}"
        await _force_refresh_interface(context, player_id, tg_id, text, None, _get_waiting_keyboard(), msg_to_delete=query.message)
        await query.answer("Aguarde.")
    else: 
        await show_event_menu(update, context)

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