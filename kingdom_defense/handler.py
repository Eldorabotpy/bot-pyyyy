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

def _format_battle_caption(player_state: dict, player_data: dict, total_stats: dict) -> str:
    # ... (CÓDIGO DA FUNÇÃO DE FORMATAÇÃO MANTIDO) ...
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
    """Gera um teclado com os aliados ativos como alvos de uma skill (por HP atual)."""
    
    active_fighters_ids = list(event_manager.active_fighters)
    
    keyboard = []
    
    # Ordenar por HP percentual para que os alvos mais feridos apareçam primeiro (melhor para cura)
    target_list = []
    for fighter_id in active_fighters_ids:
        player_data = await player_manager.get_player_data(fighter_id)
        player_state = event_manager.get_battle_data(fighter_id)
        
        if not player_data or not player_state: continue
        
        current_hp = player_state.get('player_hp', 0)
        max_hp = player_state.get('player_max_hp', 1)
        
        # Calcular HP percentual para ordenação (100 = cheio, 0 = vazio)
        hp_percent = (current_hp / max_hp) * 100 if max_hp > 0 else 0
        
        target_list.append({
            "id": fighter_id,
            "name": player_data.get('character_name', f'Herói {fighter_id}'),
            "hp_str": f"HP: {current_hp}/{max_hp}",
            "hp_percent": hp_percent
        })

    # Ordenar pelos mais feridos (menor HP percentual)
    sorted_targets = sorted(target_list, key=lambda t: t['hp_percent'])
    
    for target in sorted_targets:
        # Se for uma skill de cura, é útil saber o HP
        button_text = f"🛡️ {target['name']} ({target['hp_str']})"
        
        # Callback para a função apply_skill_handler com o alvo
        callback_data = f"apply_skill:{skill_id}:{target['id']}"
        
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
    # Adiciona botão de voltar
    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="show_skill_menu")])
    
    return InlineKeyboardMarkup(keyboard)

async def _resolve_battle_turn(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, result: dict):
    # ... (CÓDIGO DE RESOLUÇÃO MANTIDO E CORRIGIDO) ...
    user_id = query.from_user.id
    
    if "aoe_results" in result:
        for event in result["aoe_results"]:
            affected_id = event["user_id"]
            if affected_id == user_id: continue
            try:
                message_to_edit_id = query.message.message_id 
                affected_player_data = await player_manager.get_player_data(affected_id) 
                affected_player_state = event_manager.get_battle_data(affected_id)
                
                if not affected_player_data or not affected_player_state: continue
                
                affected_player_stats = await player_manager.get_player_total_stats(affected_player_data)

                if event["was_defeated"]:
                    caption = "☠️ <b>FIM DE JOGO</b> ☠️\n\nVocê foi derrotado por um ataque em área do chefe."
                    await context.bot.edit_message_caption(chat_id=affected_id, message_id=message_to_edit_id, caption=caption, reply_markup=_get_game_over_keyboard(), parse_mode='HTML')
                else:
                    new_caption = _format_battle_caption(affected_player_state, affected_player_data, affected_player_stats) 
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
        final_log = result.get('action_log', 'Você foi derrotado.'); caption = f"☠️ <b>FIM DE JOGO</b> ☠️\n\nSua jornada na defesa chegou ao fim.\n\n<b>Última Ação:</b>\n<code>{html.escape(final_log)}</code>";
        try: defeat_media_id = file_ids.get_file_id('game_over_skull'); media = InputMediaPhoto(media=defeat_media_id, caption=caption, parse_mode="HTML"); await query.edit_message_media(media=media, reply_markup=_get_game_over_keyboard())
        except Exception: await query.edit_message_caption(caption=caption, reply_markup=_get_game_over_keyboard(), parse_mode='HTML')
        return

    player_data = await player_manager.get_player_data(user_id) 
    player_full_stats = await player_manager.get_player_total_stats(player_data)

    if result.get("monster_defeated"):
        await query.answer(f"Inimigo derrotado! {result.get('loot_message', '')}", cache_time=1)
        
        player_state = event_manager.get_battle_data(user_id)
        
        if not player_data or not player_state:
             await query.edit_message_caption(caption="Erro ao carregar dados pós-vitória.", reply_markup=_get_game_over_keyboard())
             return
             
        player_state['action_log'] = result.get('action_log', '')
        media_key = player_state['current_mob'].get('media_key')
        file_data = file_ids.get_file_data(media_key) if media_key else None
        
        caption = _format_battle_caption(player_state, player_data, player_full_stats) 
        
        if file_data and file_data.get("id"):
             media = InputMediaPhoto(media=file_data["id"], caption=caption, parse_mode="HTML")
             await query.edit_message_media(media=media, reply_markup=_get_battle_keyboard())
        else:
             await query.edit_message_caption(caption=caption, reply_markup=_get_battle_keyboard(), parse_mode='HTML')
        return
    
    else:
        player_state = event_manager.get_battle_data(user_id)
        if player_state and player_data:
            player_state['action_log'] = result.get('action_log', '')
            caption = _format_battle_caption(player_state, player_data, player_full_stats) 
            await query.edit_message_caption(caption=caption, reply_markup=_get_battle_keyboard(), parse_mode='HTML')
        elif not player_state:
             await query.edit_message_caption(caption="A batalha terminou.", reply_markup=_get_game_over_keyboard())

# Em: kingdom_defense/handler.py
# SUBSTITUA a função 'show_skill_menu' por esta versão corrigida:

async def show_skill_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    player_data = await player_manager.get_player_data(user_id) 
    if not player_data: return

    # --- !!! CORREÇÃO APLICADA AQUI !!! ---
    # Agora lê a lista de skills EQUIPADAS, não todas as skills aprendidas.
    equipped_skills = player_data.get("equipped_skills", [])
    # ------------------------------------

    if not equipped_skills:
        await query.answer("Você não tem habilidades ativas EQUIPADAS!", show_alert=True)
        return

    keyboard, current_mana = [], player_data.get("mana", 0)
    
    # Pega o estado da batalha para verificar cooldowns
    player_state = event_manager.get_battle_data(user_id)
    active_cooldowns = {}
    if player_state:
        # (O teu engine não parece estar a guardar cooldowns entre menus,
        # mas se guardasse, a lógica viria aqui.)
        pass 

    # -------------------------------------------------------------
    # Lógica de exibição (mantida, mas agora usa 'equipped_skills')
    # -------------------------------------------------------------
    for skill_id in equipped_skills: # <-- USA A LISTA CORRIGIDA
        skill_info = SKILL_DATA.get(skill_id)
        
        # Garante que a skill existe e é ativa (filtro de segurança)
        if not skill_info or skill_info.get("type", "unknown") not in ("active", "support_heal", "support_buff"):
            continue 
            
        mana_cost = skill_info.get('mana_cost', 0)
        
        # (Simplifiquei a tua lógica de alvo, podes ajustar se tiveres mais tipos)
        is_single_target_support = skill_info.get("type") == "support_heal" 
        
        button_text_base = f"{skill_info['display_name']} ({mana_cost} MP)"
        
        if is_single_target_support:
            # Redireciona para a seleção de alvo
            if current_mana < mana_cost:
                 button_text = f"❌ {button_text_base}"
            else:
                 button_text = f"🎯 {button_text_base}"
            
            # Novo callback para seleção
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"select_target:{skill_id}")])
            
        else:
            # Uso direto (ataque, party-heal/buff, self-buff)
            if current_mana < mana_cost:
                button_text = f"❌ {button_text_base}"
            else:
                button_text = button_text_base
            
            # Callback para uso imediato (o target_id será None)
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"use_skill:{skill_id}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="back_to_battle")])
    await query.edit_message_caption(caption="Escolha uma habilidade para usar:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    
async def select_skill_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    try:
        # Padrão: select_target:skill_id
        skill_id = query.data.split(':')[1]
    except IndexError:
        await query.answer("Erro: Skill não encontrada.", show_alert=True)
        return
    
    skill_info = SKILL_DATA.get(skill_id)
    if not skill_info:
        await query.answer("Erro: Habilidade desconhecida.", show_alert=True)
        return
        
    # Verifica se o jogador tem mana suficiente (para desabilitar o botão de voltar)
    player_data = await player_manager.get_player_data(user_id)
    mana_cost = skill_info.get("mana_cost", 0)
    if player_data.get("mana", 0) < mana_cost:
        await query.answer("Mana insuficiente!", show_alert=True)
        # Não retorna, apenas mostra a tela sem mana suficiente
        
    # Gera o teclado de seleção de alvo (ASYNC)
    target_keyboard = await _get_target_selection_keyboard(user_id, skill_id)
    
    caption = f"🛡️ **{skill_info['display_name']}** ({mana_cost} MP)\n\nEscolha o aliado para curar ou dar suporte:"
    
    await query.edit_message_caption(caption=caption, reply_markup=target_keyboard, parse_mode="HTML")


async def back_to_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redesenha a tela de batalha principal ao sair do menu de skills."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    player_data = await player_manager.get_player_data(user_id)
    total_stats = await player_manager.get_player_total_stats(player_data)
    battle_data = event_manager.get_battle_data(user_id)

    if not battle_data or not player_data:
        await query.edit_message_caption(caption="A batalha terminou.", reply_markup=_get_game_over_keyboard())
        return

    caption = _format_battle_caption(battle_data, player_data, total_stats) 
    await query.edit_message_caption(caption=caption, reply_markup=_get_battle_keyboard(), parse_mode="HTML")

# Arquivo: kingdom_defense/handler.py

async def handle_marathon_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id

    # 1. Verifica delay (síncrono)
    now = time.time()
    last_attack_time = context.user_data.get('kd_last_attack_time', 0)

    if now - last_attack_time < 2.0:
        await query.answer("Aguarde um momento antes de atacar novamente!", cache_time=1)
        return
    context.user_data['kd_last_attack_time'] = now
    await query.answer()

    try:
        # 2. Carrega player_data e total_stats (ASYNC)
        player_data = await player_manager.get_player_data(user_id) 
        if not player_data:
            await query.answer("Erro ao carregar dados do jogador.", show_alert=True)
            return

        player_full_stats = await player_manager.get_player_total_stats(player_data) 

        # 3. Processa o ataque no Engine (que deve ser ASYNC)
        result = await event_manager.process_player_attack(user_id, player_data, player_full_stats) 

        if result is None:
            logger.error(f"process_player_attack retornou None para user_id {user_id}")
            await query.answer("Erro interno: O estado da batalha não foi retornado corretamente.", show_alert=True)
            return

        if "error" in result:
            await query.answer(result["error"], show_alert=True)
            return

        # --- BLOCO DE NOTIFICAÇÃO AOE ---
        if "aoe_results" in result:
            for event in result["aoe_results"]:
                affected_id = event["user_id"]
                if affected_id == user_id: continue 
                try:
                    # --- INÍCIO DA CORREÇÃO (Bug 2: AoE) ---
                    affected_player_data = await player_manager.get_player_data(affected_id)
                    affected_player_state = event_manager.get_battle_data(affected_id)
 
                    if not affected_player_data or not affected_player_state:
                        continue

                    # Busca o ID da mensagem guardado no estado do JOGADOR AFETADO
                    message_to_edit_id = affected_player_state.get('message_id')

                    if not message_to_edit_id:
                        logger.warning(f"Não foi possível encontrar o message_id para o jogador passivo {affected_id}")
                        continue
                    # --- FIM DA CORREÇÃO ---

                    # O CÓDIGO ANTIGO (incorreto) era:
                    # message_to_edit_id = query.message.message_id 

                    affected_player_stats = await player_manager.get_player_total_stats(affected_player_data)

                    if event["was_defeated"]:
                        caption = "☠️ FIM DE JOGO ☠️\n\nVocê foi derrotado por um ataque em área do chefe."
                        # Usa o chat_id (affected_id) e o message_id (message_to_edit_id) corretos
                        await context.bot.edit_message_caption(chat_id=affected_id, message_id=message_to_edit_id, caption=caption, reply_markup=_get_game_over_keyboard(), parse_mode='HTML')
                    else:
                        new_caption = _format_battle_caption(affected_player_state, affected_player_data, affected_player_stats) 
                        # Usa o chat_id (affected_id) e o message_id (message_to_edit_id) corretos
                        await context.bot.edit_message_caption(chat_id=affected_id, message_id=message_to_edit_id, caption=new_caption, reply_markup=_get_battle_keyboard(), parse_mode='HTML')
                except Exception as e:
                     logger.error(f"Falha ao notificar jogador passivo {affected_id} sobre o AoE: {e}")
        # --- FIM DO BLOCO DE NOTIFICAÇÃO AOE ---

        # 4. Resolve o Turno (vitória ou contra-ataque)
        await _resolve_battle_turn(query, context, result) 

    except Exception as e:
        print(f"!!!!!!!! ERRO CRÍTICO EM handle_marathon_attack !!!!!!!!!!")
        traceback.print_exc()
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        logger.error(f"Erro CRÍTICO em handle_marathon_attack: {e}", exc_info=True)
        await query.answer("Ocorreu um erro ao processar seu ataque. Avise um administrador.", show_alert=True)

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

    skill_info = SKILL_DATA.get(skill_id)
    if not skill_info:
        await query.answer("Erro: Habilidade não encontrada!", show_alert=True)
        return
    
    if player_data.get("mana", 0) < skill_info.get("mana_cost", 0):
        await query.answer("Mana insuficiente!", show_alert=True)
        return

    await query.answer()
    # O target_id é None aqui, pois esta função só lida com self/party/monstro (uso direto)
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
        # CORREÇÃO: Adiciona await
        player_data = await player_manager.get_player_data(user_id)
        if not player_data: 
             await query.answer("Erro ao carregar dados do jogador.", show_alert=True)
             return

        await query.answer()
        # CORREÇÃO: Adiciona await
        result = await event_manager.process_player_skill(user_id, player_data, skill_id, target_id=target_id)
        # CORREÇÃO: Adiciona await
        await _resolve_battle_turn(query, context, result)
    except Exception:
        traceback.print_exc()
        await query.answer("Ocorreu um erro ao aplicar a skill.", show_alert=True)

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
        # Padrao: apply_skill:skill_id:target_id
        _, skill_id, target_id_str = query.data.split(':')
        target_id = int(target_id_str)
        
        player_data = await player_manager.get_player_data(user_id)
        if not player_data: 
             await query.answer("Erro ao carregar dados do jogador.", show_alert=True)
             return

        await query.answer()
        # O target_id agora é passado corretamente!
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
    # CORREÇÃO: Adiciona await para o método async
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
    
    # 1. Carrega player_data e verifica ticket (Mantido)
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
         await query.answer("Erro ao carregar dados. Tente /start.", show_alert=True)
         return
         
    ticket_id = 'ticket_defesa_reino'
    player_inventory = player_data.get('inventory', {})
    
    if player_inventory.get(ticket_id, 0) <= 0:
        await query.answer("Você precisa de um Ticket da Defesa para entrar!", show_alert=True)
        return

    await query.answer("Ticket validado! Verificando seu lugar na linha de frente...")

    if not event_manager.is_active:
        await query.edit_message_text("A invasão já terminou.", reply_markup=_get_game_over_keyboard())
        return

    # Consome ticket e salva (correto)
    player_manager.remove_item_from_inventory(player_data, ticket_id, 1)
    await player_manager.save_player_data(user_id, player_data)
    
    # 2. Chama add_player_to_event (que é async e configura o estado)
    status = await event_manager.add_player_to_event(user_id, player_data) 
    
    if status == "active":
        # CORREÇÃO PRINCIPAL: CARREGA total_stats AQUI
        total_stats = await player_manager.get_player_total_stats(player_data) 
        battle_data = event_manager.get_battle_data(user_id)
        
        if not battle_data:
             await query.edit_message_caption(caption="Ocorreu um erro ao buscar seus dados de batalha. Tente novamente.", reply_markup=_get_game_over_keyboard(), parse_mode='HTML')
             return
        
        media_key = battle_data['current_mob'].get('media_key')
        file_data = file_ids.get_file_data(media_key) if media_key else None
        
        if not file_data or not file_data.get("id"):
             logger.error(f"MEDIA NÃO ENCONTRADA PARA A CHAVE: {media_key}")
             await query.edit_message_text(f"⚠️ Erro de configuração!\n\nA mídia para '{media_key}' não foi encontrada. Avise um administrador.")
             return

        # 3. Formata e Envia, PASSANDO total_stats
        caption = _format_battle_caption(battle_data, player_data, total_stats)
        
        media = InputMediaPhoto(media=file_data["id"], caption=caption, parse_mode="HTML")
        edited_message = await query.edit_message_media(media=media, reply_markup=_get_battle_keyboard())
        # Guarda o ID da mensagem editada
        event_manager.store_player_message_id(user_id, edited_message.message_id)
    
    elif status == "waiting":
        status_text = event_manager.get_queue_status_text()
        text = f"🛡️ Fila de Reforços 🛡️\n\nA linha de frente está cheia!\n\n{status_text}\n\nAguarde sua vez."
        await query.edit_message_text(text=text, reply_markup=_get_waiting_keyboard(), parse_mode='HTML')

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

        # CORREÇÃO: Adiciona await
        player_data = await player_manager.get_player_data(user_id)
        # CORREÇÃO: Carrega total_stats
        total_stats = await player_manager.get_player_total_stats(player_data)
        battle_data = event_manager.get_battle_data(user_id)

        if not player_data or not battle_data:
            await query.edit_message_text("Erro ao iniciar sua batalha. Tente entrar novamente.", reply_markup=_get_game_over_keyboard())
            return

        media_key = battle_data['current_mob'].get('media_key')
        file_data = file_ids.get_file_data(media_key) if media_key else None

        if not file_data or not file_data.get("id"):
            await query.message.edit_text("Erro: Mídia do monstro não encontrada.")
            return

        # CORREÇÃO: Passa total_stats para a função de formatação
        caption = _format_battle_caption(battle_data, player_data, total_stats)

        # Apaga a mensagem "Aguarde na fila"
        await query.message.delete()

        # Envia a nova mensagem de batalha e guarda a resposta
        new_message = await context.bot.send_photo(
            chat_id=user_id, photo=file_data["id"], caption=caption, 
            reply_markup=_get_battle_keyboard(), parse_mode="HTML"
        )

        # --- INÍCIO DA CORREÇÃO (Bug 2: AoE) ---
        # Armazena o ID da nova mensagem no estado do jogador
        event_manager.store_player_message_id(user_id, new_message.message_id)
        # --- FIM DA CORREÇÃO ---

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
    application.add_handler(CallbackQueryHandler(select_skill_target, pattern='^select_target:'))
