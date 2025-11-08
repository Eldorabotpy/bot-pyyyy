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
   
    # Pega apenas as skills EQUIPADAS (Corrigido)
    equipped_skills = player_data.get("equipped_skills", [])

    state = player_data.get('player_state', {})
    combat_details = state.get('details', {})
    active_cooldowns = combat_details.get("skill_cooldowns", {})

    # --- 👇 MUDANÇA: 'skill_buttons' agora é 'keyboard_rows' 👇 ---
    keyboard_rows = [] 
    
    for skill_id in equipped_skills: 
        skill_info = SKILL_DATA.get(skill_id)

        # Filtro de segurança (Corrigido)
        if not skill_info or skill_info.get("type") not in ("active", "support"):
            continue

        skill_name = skill_info.get("display_name", skill_id)
        mana_cost = skill_info.get("mana_cost", 0) 
        turns_left = active_cooldowns.get(skill_id, 0)

        # --- 👇 MUDANÇA: Criação dos botões de 'Usar' e 'Info' 👇 ---
        use_button = None
        info_button = InlineKeyboardButton("ℹ️ Info", callback_data=f"combat_info_skill:{skill_id}")

        if turns_left > 0:
            # Botão Desativado (Em Cooldown)
            use_button = InlineKeyboardButton(f"⏳ {skill_name} ({turns_left}t)", callback_data=f"combat_skill_on_cooldown")
        else:
            # Botão Ativado
            button_text = f"✨ {skill_name}"
            if mana_cost > 0:
                button_text += f" (MP: {mana_cost})"
            use_button = InlineKeyboardButton(button_text, callback_data=f"combat_use_skill:{skill_id}")
        
        # Adiciona a linha [Botão de Usar] [Botão de Info]
        keyboard_rows.append([use_button, info_button])
        # --- 👆 FIM DA MUDANÇA 👆 ---

    if not keyboard_rows: # Se 'keyboard_rows' estiver vazia
        keyboard_rows.append([InlineKeyboardButton("Você não tem skills equipadas.", callback_data="noop")])

    keyboard_rows.append([InlineKeyboardButton("⬅️ Voltar à Batalha", callback_data="combat_attack_menu")])

    try:
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard_rows))
    except BadRequest as e:
        if "not modified" not in str(e):
            logger.warning(f"Erro ao editar markup para menu de skills: {e}")

# --- 👇 NOVA FUNÇÃO (Callback do botão 'Info') 👇 ---
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

    # Pega as informações
    name = skill_info.get("display_name", skill_id)
    desc = skill_info.get("description", "Sem descrição.")
    cost = skill_info.get("mana_cost", 0)
    cooldown = skill_info.get("effects", {}).get("cooldown_turns", 0)
    
    # Formata o texto do pop-up
    popup_text = [
        f"ℹ️ {name}",
        f"Custo: {cost} MP",
    ]
    if cooldown > 0:
        popup_text.append(f"Recarga: {cooldown} turnos")
    
    popup_text.append(f"\n{desc}")
    
    # Mostra o pop-up (alert=True faz a caixa grande)
    await query.answer("\n".join(popup_text), show_alert=True)
# --- 👆 FIM DA NOVA FUNÇÃO 👆 ---

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

    # 2. Lógica de Verificação de Mana (Corrigido)
    mana_cost = skill_info.get("mana_cost", 0)
    if mana_cost > 0:
        total_stats = await player_manager.get_player_total_stats(player_data)
        max_mp = total_stats.get('max_mana', 10)
        current_mp = player_data.get('current_mp', max_mp)

        if current_mp < mana_cost:
            await _safe_answer(query)
            await query.answer(f"Você não tem Mana ({mana_cost}) suficiente!", show_alert=True)
            return

    # 3. Aplicar Cooldown (ANTES de atacar)
    cooldown = skill_info.get("effects", {}).get("cooldown_turns", 0)
    if cooldown > 0:
        active_cooldowns[skill_id] = cooldown + 1 

    # 4. Preparar o estado para o 'main_handler'
    combat_details['skill_to_use'] = skill_id
    player_data['player_state']['details'] = combat_details
    
    await _safe_answer(query)

    # 5. Chamar o handler principal para EXECUTAR o ataque
    await combat_callback(update, context, action="combat_attack")

async def combat_skill_on_cooldown_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback para quando o jogador clica numa skill em cooldown."""
    query = update.callback_query
    await query.answer("Esta habilidade ainda está em recarga!", show_alert=True)

# Exporta os handlers
combat_skill_menu_handler = CallbackQueryHandler(combat_skill_menu_callback, pattern=r'^combat_skill_menu$')
combat_use_skill_handler = CallbackQueryHandler(combat_use_skill_callback, pattern=r'^combat_use_skill:.*$')
combat_skill_on_cooldown_handler = CallbackQueryHandler(combat_skill_on_cooldown_callback, pattern=r'^combat_skill_on_cooldown$')
combat_skill_info_handler = CallbackQueryHandler(combat_skill_info_callback, pattern=r'^combat_info_skill:.*$')