# handlers/combat/skill_handler.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

from modules import player_manager
# Importa o teu novo ficheiro de DADOS
from modules.game_data.skills import SKILL_DATA
from handlers.utils import format_combat_message
from handlers.combat.main_handler import combat_callback # Importa o handler principal de combate
from modules.player import actions as player_actions

logger = logging.getLogger(__name__)

async def _safe_answer(query):
    try: await query.answer()
    except BadRequest: pass

async def combat_skill_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a lista de skills ATIVAS que o jogador pode usar."""
    query = update.callback_query
    await _safe_answer(query)

    player_data = await player_manager.get_player_data(query.from_user.id)
   
    # Pega as skills que o jogador APRENDEU
    learned_skills = player_data.get("learned_skills", [])

    # Pega o estado do combate para verificar cooldowns
    state = player_data.get('player_state', {})
    combat_details = state.get('details', {})
    active_cooldowns = combat_details.get("skill_cooldowns", {})

    skill_buttons = []
    for skill_id in learned_skills:
        skill_info = SKILL_DATA.get(skill_id)

        # Mostra apenas skills ATIVAS no menu
        if not skill_info or skill_info.get("type") != "active":
            continue

        skill_name = skill_info.get("display_name", skill_id)
        mana_cost = skill_info.get("mana_cost", 0) # Pega o custo de mana

        # Verifica se a skill está em cooldown
        turns_left = active_cooldowns.get(skill_id, 0)

        if turns_left > 0:
            # Botão Desativado (Em Cooldown)
            skill_buttons.append(
            InlineKeyboardButton(f"⏳ {skill_name} ({turns_left}t)", callback_data=f"combat_skill_on_cooldown")
            )
        else:
            # Botão Ativado
            button_text = f"✨ {skill_name}"
            if mana_cost > 0:
                button_text += f" (MP: {mana_cost})"
 
            skill_buttons.append(
                InlineKeyboardButton(button_text, callback_data=f"combat_use_skill:{skill_id}")
            )

    if not skill_buttons:
        skill_buttons.append(InlineKeyboardButton("Você não tem skills ativas.", callback_data="noop"))

    keyboard = [[btn] for btn in skill_buttons]
    keyboard.append([InlineKeyboardButton("⬅️ Voltar à Batalha", callback_data="combat_attack_menu")])

    # Edita apenas os botões, mantendo o caption (texto) da batalha
    try:
       await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
    except BadRequest as e:
        if "not modified" not in str(e):
            logger.warning(f"Erro ao editar markup para menu de skills: {e}")


async def combat_use_skill_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa o uso de uma skill em combate."""
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

    player_data = await player_manager.get_player_data(user_id)
    state = player_data.get('player_state', {})
    if state.get('action') != 'in_combat':
        await _safe_answer(query)
        await query.answer("Você não está em combate.", show_alert=True)
        return
    
    combat_details = state.get('details', {})
    active_cooldowns = combat_details.setdefault("skill_cooldowns", {})
    
    # 1. Verificar Cooldown
    if active_cooldowns.get(skill_id, 0) > 0:
        await _safe_answer(query)
        await query.answer(f"{skill_info['display_name']} está em recarga!", show_alert=True)
        return

    # --- 👇 LÓGICA DE MANA CORRIGIDA 👇 ---
    mana_cost = skill_info.get("mana_cost", 0)
    if mana_cost > 0:
        # 2. Usar a nova função 'spend_mana' de actions.py
        if not player_actions.spend_mana(player_data, mana_cost):
            await _safe_answer(query)
            await query.answer(f"Você não tem Mana ({mana_cost}) suficiente!", show_alert=True)
            return
    # --- 👆 FIM DA LÓGICA DE MANA 👆 ---

    # 3. Aplicar Cooldown (ANTES de atacar)
    cooldown = skill_info["effects"].get("cooldown_turns", 0)
    if cooldown > 0:
        active_cooldowns[skill_id] = cooldown + 1 
    
    # 4. Salvar o estado (gasto de mana/cooldown)
    player_data['player_state']['details'] = combat_details
    # Nota: O 'spend_mana' já modificou o player_data, 
    # então este save já guarda a mana gasta.
    await player_manager.save_player_data(user_id, player_data)
    
    # 5. INICIAR O ATAQUE
    player_data['player_state']['details']['skill_to_use'] = skill_id
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
combat_skill_on_cooldown_handler = CallbackQueryHandler(combat_skill_on_cooldown_callback, pattern=r'^combat_skill_on_cooldown$')
