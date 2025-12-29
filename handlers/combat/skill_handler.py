# handlers/combat/skill_handler.py
# (VERSÃO REFATORADA E LIMPA)

import logging
from typing import Optional, Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

from modules import player_manager
# Importamos a nova função centralizada aqui 👇
from modules.game_data.skills import SKILL_DATA, get_skill_data_with_rarity
from handlers.utils import format_combat_message
from handlers.combat.main_handler import combat_callback 
from modules.player.actions import spend_mana 
from modules.cooldowns import verificar_cooldown

logger = logging.getLogger(__name__)


# 🛠️ HELPER
def _get_combat_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data and "logged_player_id" in context.user_data:
        return context.user_data["logged_player_id"]
    return update.callback_query.from_user.id

async def _safe_answer(query):
    """Helper para responder callbacks sem gerar erro se já foi respondido."""
    if not query: return
    try: await query.answer()
    except BadRequest: pass
    except Exception: pass

async def combat_skill_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Mostra a lista de skills, exibindo o relógio ⏳ se estiverem em recarga.
    """
    query = update.callback_query
    await _safe_answer(query)
    user_id = _get_combat_user_id(update, context)
    
    player_data = await player_manager.get_player_data(user_id)

    # Migração/Correção: Garante que skills conhecidas estejam equipadas se a lista estiver vazia
    if not player_data.get("equipped_skills") and player_data.get("skills"):
        all_known_skills = list(player_data["skills"].keys())
        player_data["equipped_skills"] = all_known_skills
        await player_manager.save_player_data(user_id, player_data)
    
    equipped_skills = player_data.get("equipped_skills", [])
    active_cooldowns = player_data.get("cooldowns", {})

    keyboard_rows = [] 
    
    for skill_id in equipped_skills: 
        # ✅ USA A FUNÇÃO CENTRALIZADA
        skill_info = get_skill_data_with_rarity(player_data, skill_id)

        if not skill_info or skill_info.get("type") not in ("active", "support"):
            continue

        skill_name = skill_info.get("display_name", skill_id)
        mana_cost = skill_info.get("mana_cost", 0) 
        turns_left = active_cooldowns.get(skill_id, 0)

        use_button = None
        info_button = InlineKeyboardButton("ℹ️ Info", callback_data=f"combat_info_skill:{skill_id}")

        if turns_left > 0:
            # 🔴 Botão Bloqueado (Cooldown)
            use_button = InlineKeyboardButton(
                f"⏳ {skill_name} ({turns_left})", 
                callback_data=f"combat_skill_on_cooldown:{turns_left}"
            )
        else:
            # 🟢 Botão Liberado
            button_text = f"✨ {skill_name}"
            if mana_cost > 0:
                button_text += f" ({mana_cost} MP)"
            use_button = InlineKeyboardButton(button_text, callback_data=f"combat_use_skill:{skill_id}")
        
        keyboard_rows.append([use_button, info_button])

    if not keyboard_rows:
        keyboard_rows.append([InlineKeyboardButton("Você não tem skills ativas equipadas.", callback_data="noop")])

    keyboard_rows.append([InlineKeyboardButton("⬅️ Voltar à Batalha", callback_data="combat_attack_menu")])

    try:
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard_rows))
    except BadRequest:
        pass
            
async def combat_skill_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        user_id = _get_combat_user_id(update, context)
        player_data = await player_manager.get_player_data(user_id)
        skill_id = query.data.split(':', 1)[1]
        
        # ✅ USA A FUNÇÃO CENTRALIZADA
        skill_info = get_skill_data_with_rarity(player_data, skill_id)
    except Exception:
        await query.answer("Erro ao buscar info.", show_alert=True)
        return

    if not skill_info:
        await query.answer("Skill não encontrada.", show_alert=True)
        return

    name = skill_info.get("display_name", skill_id)
    desc = skill_info.get("description", "Sem descrição.")
    cost = skill_info.get("mana_cost", 0)
    cooldown = skill_info.get("effects", {}).get("cooldown_turns", 0)
    
    popup_text = [f"ℹ️ {name}", f"Custo: {cost} MP"]
    if cooldown > 0:
        popup_text.append(f"Recarga: {cooldown} turnos")
    popup_text.append(f"\n{desc}")
    
    await query.answer("\n".join(popup_text), show_alert=True)


async def combat_use_skill_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Processa a tentativa de uso da skill.
    """
    query = update.callback_query
    user_id = _get_combat_user_id(update, context)

    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return
    
    try:
        skill_id = query.data.split(':')[1]
    except IndexError:
        return

    # 1. Verificação de Cooldown (Dupla segurança)
    pode_usar, msg = verificar_cooldown(player_data, skill_id)
    if not pode_usar:
        await query.answer(msg, show_alert=True)
        await combat_skill_menu_callback(update, context)
        return

    # ✅ USA A FUNÇÃO CENTRALIZADA
    skill_info = get_skill_data_with_rarity(player_data, skill_id)
    if not skill_info: return

    battle_cache = context.user_data.get('battle_cache')
    mana_cost = skill_info.get("mana_cost", 0)
    is_support = skill_info.get("type") == "support"
    
    # 2. Verifica Mana
    current_mp = 0
    if battle_cache and battle_cache.get('player_id') == user_id:
        current_mp = battle_cache.get('player_mp', 0)
    else:
        current_mp = player_data.get('current_mp', 0)

    if current_mp < mana_cost:
        await query.answer(f"Sem Mana! Precisa de {mana_cost}.", show_alert=True)
        return

    # 3. Prepara a ação para o main_handler processar
    if battle_cache:
        # Consome mana visualmente no cache para feedback imediato
        battle_cache['player_mp'] = max(0, int(battle_cache.get('player_mp', 0)) - mana_cost)
        battle_cache['skill_to_use'] = skill_id
        battle_cache['action_type'] = "support" if is_support else "attack"
    else:
        # Fallback para sistemas legados/dungeon sem cache
        spend_mana(player_data, mana_cost)
        state = player_data.get('player_state', {})
        if state.get('details'):
            state['details']['skill_to_use'] = skill_id
            state['details']['action_type'] = "support" if is_support else "attack"
            await player_manager.save_player_data(user_id, player_data)

    await _safe_answer(query)
    
    # Chama o ataque principal no main_handler
    await combat_callback(update, context, action="combat_attack")

async def combat_skill_on_cooldown_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback simples para avisar quantos turnos faltam."""
    query = update.callback_query
    data = query.data
    turnos = "alguns"
    
    if ":" in data:
        turnos = data.split(":")[-1]
        
    await query.answer(f"⏳ Habilidade recarregando! Aguarde {turnos} turnos.", show_alert=True)

async def combat_attack_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Retorna ao menu principal de ataque."""
    query = update.callback_query
    await _safe_answer(query)
    
    kb = [
        [InlineKeyboardButton("⚔️ Atacar", callback_data="combat_attack"), InlineKeyboardButton("✨ Skills", callback_data="combat_skill_menu")],
        [InlineKeyboardButton("🧪 Poções", callback_data="combat_potion_menu"), InlineKeyboardButton("🏃 Fugir", callback_data="combat_flee")]
    ]
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))

# Exports
combat_skill_menu_handler = CallbackQueryHandler(combat_skill_menu_callback, pattern=r'^combat_skill_menu$')
combat_use_skill_handler = CallbackQueryHandler(combat_use_skill_callback, pattern=r'^combat_use_skill:.*$')
combat_skill_on_cooldown_handler = CallbackQueryHandler(combat_skill_on_cooldown_callback, pattern=r'^combat_skill_on_cooldown')
combat_skill_info_handler = CallbackQueryHandler(combat_skill_info_callback, pattern=r'^combat_info_skill:.*$')
combat_attack_menu_handler = CallbackQueryHandler(combat_attack_menu_callback, pattern=r'^combat_attack_menu$')