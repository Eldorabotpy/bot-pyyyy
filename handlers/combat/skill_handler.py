# handlers/combat/skill_handler.py

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

from modules import player_manager
from modules.game_data.skills import SKILL_DATA
from handlers.utils import format_combat_message
from handlers.combat.main_handler import combat_callback 
from modules.player.actions import spend_mana 

logger = logging.getLogger(__name__)

async def _safe_answer(query):
    try: await query.answer()
    except BadRequest: pass

# --- 👇 FUNÇÃO ATUALIZADA (HÍBRIDA) 👇 ---
async def combat_skill_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Mostra a lista de skills ATIVAS.
    (Versão Híbrida: Funciona com battle_cache e player_state)
    """
    query = update.callback_query
    await _safe_answer(query)
    user_id = query.from_user.id

    battle_cache = context.user_data.get('battle_cache')
    
    player_data = await player_manager.get_player_data(user_id)
    equipped_skills = player_data.get("equipped_skills", [])
    
    active_cooldowns = {}

    if battle_cache and battle_cache.get('player_id') == user_id:

        active_cooldowns = battle_cache.get("skill_cooldowns", {})
        
    else:
        # --- MODO CALABOUÇO (LEGADO) ---
        state = player_data.get('player_state', {})
        combat_details = state.get('details', {})
        active_cooldowns = combat_details.get("skill_cooldowns", {})

    keyboard_rows = [] 
    
    for skill_id in equipped_skills: 
        skill_info = SKILL_DATA.get(skill_id)

        if not skill_info or skill_info.get("type") not in ("active", "support"):
            continue

        skill_name = skill_info.get("display_name", skill_id)
        mana_cost = skill_info.get("mana_cost", 0) 
        
        turns_left = active_cooldowns.get(skill_id, 0)

        use_button = None
        info_button = InlineKeyboardButton("ℹ️ Info", callback_data=f"combat_info_skill:{skill_id}")

        if turns_left > 0:
            use_button = InlineKeyboardButton(f"⏳ {skill_name} ({turns_left}t)", callback_data=f"combat_skill_on_cooldown")
        else:
            button_text = f"✨ {skill_name}"
            if mana_cost > 0:
                button_text += f" (MP: {mana_cost})"
            use_button = InlineKeyboardButton(button_text, callback_data=f"combat_use_skill:{skill_id}")
        
        keyboard_rows.append([use_button, info_button])

    if not keyboard_rows:
        keyboard_rows.append([InlineKeyboardButton("Você não tem skills equipadas.", callback_data="noop")])

    keyboard_rows.append([InlineKeyboardButton("⬅️ Voltar à Batalha", callback_data="combat_attack_menu")])

    try:
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard_rows))
    except BadRequest as e:
        if "not modified" not in str(e):
            logger.warning(f"Erro ao editar markup para menu de skills: {e}")

async def combat_skill_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra um pop-up (alert) com a descrição da skill."""
    query = update.callback_query
    
    try:
        skill_id = query.data.split(':', 1)[1]
        skill_info = SKILL_DATA.get(skill_id)
    except Exception:
        await query.answer("Erro: Skill não encontrada.", show_alert=True)
        return

    if not skill_info:
        await query.answer("Erro: Skill não encontrada.", show_alert=True)
        return

    name = skill_info.get("display_name", skill_id)
    desc = skill_info.get("description", "Sem descrição.")
    cost = skill_info.get("mana_cost", 0)
    cooldown = skill_info.get("effects", {}).get("cooldown_turns", 0)
    
    popup_text = [
        f"ℹ️ {name}",
        f"Custo: {cost} MP",
    ]
    if cooldown > 0:
        popup_text.append(f"Recarga: {cooldown} turnos")
    
    popup_text.append(f"\n{desc}")
    
    await query.answer("\n".join(popup_text), show_alert=True)


# --- 👇 FUNÇÃO ATUALIZADA (HÍBRIDA) 👇 ---
async def combat_use_skill_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Processa o uso de uma skill em combate.
    (Versão Híbrida: Funciona com battle_cache e player_state)
    """
    query = update.callback_query
    user_id = query.from_user.id

    try:
        skill_id = query.data.split(':')[1]
    except IndexError:
        await _safe_answer(query)
        await query.answer("Erro ao usar a skill.", show_alert=True)
        return

    skill_info = SKILL_DATA.get(skill_id)
    if not skill_info:
        await _safe_answer(query)
        await query.answer("Skill não encontrada.", show_alert=True)
        return

    battle_cache = context.user_data.get('battle_cache')
    mana_cost = skill_info.get("mana_cost", 0)
    cooldown = skill_info.get("effects", {}).get("cooldown_turns", 0)

    if battle_cache and battle_cache.get('player_id') == user_id:
            
        active_cooldowns = battle_cache.setdefault("skill_cooldowns", {})
        
        if active_cooldowns.get(skill_id, 0) > 0:
            await _safe_answer(query)
            await query.answer(f"{skill_info['display_name']} está em recarga!", show_alert=True)
            return

        if mana_cost > 0:
            current_mp = battle_cache.get('player_mp', 0)
            if current_mp < mana_cost:
                await _safe_answer(query)
                await query.answer(f"Você não tem Mana ({mana_cost}) suficiente!", show_alert=True)
                return

        if cooldown > 0:
            active_cooldowns[skill_id] = cooldown + 1 


        battle_cache['skill_to_use'] = skill_id
        
    else:
        # --- MODO CALABOUÇO (LEGADO) ---

        player_data = await player_manager.get_player_data(user_id)
        state = player_data.get('player_state', {})
        if state.get('action') != 'in_combat':
            await _safe_answer(query)
            await query.answer("Você não está em combate.", show_alert=True)
            return

        combat_details = state.get('details', {})
        active_cooldowns = combat_details.setdefault("skill_cooldowns", {})
        
        if active_cooldowns.get(skill_id, 0) > 0:
            await _safe_answer(query)
            await query.answer(f"{skill_info['display_name']} está em recarga!", show_alert=True)
            return

        if mana_cost > 0:
            total_stats = await player_manager.get_player_total_stats(player_data)
            max_mp = total_stats.get('max_mana', 10)
            current_mp = player_data.get('current_mp', max_mp)

            if current_mp < mana_cost:
                await _safe_answer(query)
                await query.answer(f"Você não tem Mana ({mana_cost}) suficiente!", show_alert=True)
                return

        if cooldown > 0:
            active_cooldowns[skill_id] = cooldown + 1 

        combat_details['skill_to_use'] = skill_id
        player_data['player_state']['details'] = combat_details
        
        await player_manager.save_player_data(user_id, player_data)

    await _safe_answer(query)
    
    await combat_callback(update, context, action="combat_attack")

async def combat_skill_on_cooldown_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback para quando o jogador clica numa skill em cooldown."""
    query = update.callback_query
    await query.answer("Esta habilidade ainda está em recarga!", show_alert=True)

# Exporta os handlers
combat_skill_menu_handler = CallbackQueryHandler(combat_skill_menu_callback, pattern=r'^combat_skill_menu$')
combat_use_skill_handler = CallbackQueryHandler(combat_use_skill_callback, pattern=r'^combat_use_skill:.*$')
combat_skill_on_cooldown_handler = CallbackQueryHandler(combat_skill_on_cooldown_callback, pattern=r'^combat_skill_on_cooldown_')
combat_skill_info_handler = CallbackQueryHandler(combat_skill_info_callback, pattern=r'^combat_info_skill:.*$')