# handlers/combat/potion_handler.py
# (VERSÃO CORRIGIDA: Prioriza Battle Cache para evitar "Recuperou 0 HP")

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules import player_manager, game_data
from modules.player import actions as player_actions
from handlers.utils import format_combat_message, format_combat_message_from_cache
from telegram.error import BadRequest
from modules.auth_utils import requires_login

logger = logging.getLogger(__name__)

# 🛠️ HELPER (ESTRITO)
def _get_combat_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str | None:
    if context.user_data and "logged_player_id" in context.user_data:
        return str(context.user_data["logged_player_id"])
    return None

@requires_login
async def combat_potion_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = context.user_data["logged_player_id"]
    if not user_id:
        await query.answer("⚠️ Erro de sessão. Relogue.", show_alert=True)
        return

    player_data = await player_manager.get_player_data(user_id)
    inventory = player_data.get("inventory", {})
    
    potion_buttons = []
    for item_id, quantity in inventory.items():
        item_info = game_data.ITEMS_DATA.get(item_id, {})
        if item_info.get("type") in ("potion", "food", "consumable"):
            item_name = item_info.get("display_name", item_id)
            item_emoji = item_info.get("emoji", "🧪")
            potion_buttons.append(InlineKeyboardButton(f"{item_emoji} {item_name} (x{quantity})", callback_data=f"combat_use:{item_id}"))

    keyboard = [[btn] for btn in potion_buttons]
    keyboard.append([InlineKeyboardButton("⬅️ Voltar à Batalha", callback_data="combat_attack_menu")])
    
    try:
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
    except BadRequest:
        pass

@requires_login
async def combat_use_potion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = _get_combat_user_id(update, context)
    if not user_id:
        await query.answer("⚠️ Sessão inválida.", show_alert=True)
        return
    
    try:
        item_id_to_use = query.data.split(':')[1]
    except IndexError:
        await query.answer("Erro ao usar o item.", show_alert=True)
        return

    player_data = await player_manager.get_player_data(user_id)
    
    # 1. Remove do inventário
    if not player_manager.remove_item_from_inventory(player_data, item_id_to_use, 1):
        await query.answer("Você não tem este item!", show_alert=True)
        await combat_potion_menu_callback(update, context) 
        return

    # 2. Prepara dados
    item_info = game_data.ITEMS_DATA.get(item_id_to_use, {})
    effects = item_info.get("effects", {})
    feedback_message = ""
    level_up_msg = None

    # Detecta se está em combate ativo (Cache)
    battle_cache = context.user_data.get('battle_cache')
    in_combat = battle_cache and str(battle_cache.get('player_id')) == str(user_id)

    # Variáveis de Ganho Real (O que vai aparecer na mensagem)
    real_gain_hp = 0
    real_gain_mp = 0
    real_gain_energy = 0

    # --- LÓGICA DE HP ---
    if 'heal' in effects:
        heal_amount = effects['heal']
        
        if in_combat:
            # Cálculo baseado no CACHE (O que você vê na tela)
            cur_hp = int(battle_cache.get('player_hp', 0))
            max_hp = int(battle_cache.get('player_stats', {}).get('max_hp', 100))
            new_hp = min(max_hp, cur_hp + heal_amount)
            real_gain_hp = new_hp - cur_hp
            
            # Atualiza Cache
            battle_cache['player_hp'] = new_hp
            
            # Atualiza DB também (blindly)
            await player_actions.heal_player(player_data, heal_amount)
        else:
            # Cálculo baseado no DB
            old_hp = player_data.get("current_hp", 0)
            await player_actions.heal_player(player_data, heal_amount)
            real_gain_hp = player_data.get("current_hp", 0) - old_hp
            
        feedback_message = f"Recuperou {real_gain_hp} HP!"

    # --- LÓGICA DE ENERGIA ---
    elif 'add_energy' in effects:
        energy_amount = effects['add_energy']
        player_actions.add_energy(player_data, energy_amount)
        real_gain_energy = energy_amount
        feedback_message = f"Recuperou {energy_amount} Energia!"

    # --- LÓGICA DE MANA ---
    elif 'add_mana' in effects:
        mana_amount = effects['add_mana']
        
        if in_combat:
            cur_mp = int(battle_cache.get('player_mp', 0))
            max_mp = int(battle_cache.get('player_stats', {}).get('max_mana', 100))
            new_mp = min(max_mp, cur_mp + mana_amount)
            real_gain_mp = new_mp - cur_mp
            
            battle_cache['player_mp'] = new_mp
            await player_actions.add_mana(player_data, mana_amount)
        else:
            old_mp = player_data.get("current_mp", 0)
            await player_actions.add_mana(player_data, mana_amount)
            real_gain_mp = player_data.get("current_mp", 0) - old_mp
            
        feedback_message = f"Recuperou {real_gain_mp} Mana!"

    # --- LÓGICA DE XP ---
    elif 'add_xp' in effects:
        xp_amount = effects['add_xp']
        player_data['xp'] = player_data.get('xp', 0) + xp_amount
        niveis, pontos, level_up_msg = player_manager.check_and_apply_level_up(player_data)
        feedback_message = f"Ganhou {xp_amount} XP!"
        if level_up_msg: feedback_message += " " + level_up_msg

    # --- BUFFS ---
    elif 'buff' in effects:
        buff = effects['buff']
        player_actions.add_buff(player_data, buff)
        stat_name = buff.get('stat', 'atributo').replace("_", " ").capitalize()
        feedback_message = f"Buff de {stat_name} aplicado!"
    
    else:
        await query.answer("Sem efeito em combate.", show_alert=True)
        player_manager.add_item_to_inventory(player_data, item_id_to_use, 1) # Devolve
        await player_manager.save_player_data(user_id, player_data)
        return

    # Registra no log visual
    item_display = item_info.get('display_name', item_id_to_use)
    full_msg = f"🧪 Usou {item_display}: {feedback_message}"
    
    if in_combat:
        log = battle_cache.get('battle_log', [])
        log.append(full_msg)
        battle_cache['battle_log'] = log[-12:]

    # Salva DB
    await player_manager.save_player_data(user_id, player_data)
    
    # Toast Notification
    await query.answer(feedback_message, show_alert=True)
    
    # Atualiza a mensagem
    try:
        if in_combat:
            new_text = await format_combat_message_from_cache(battle_cache)
        else:
            new_text = await format_combat_message(player_data)

        kb = [
            [InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), InlineKeyboardButton("✨ Skills", callback_data='combat_skill_menu')],
            [InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu'), InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')]
        ]
        
        if "Inimigo" in new_text or "HP:" in new_text: 
            await query.edit_message_caption(caption=new_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
            
    except Exception:
        pass

combat_potion_menu_handler = CallbackQueryHandler(combat_potion_menu_callback, pattern=r'^combat_potion_menu$')
combat_use_potion_handler = CallbackQueryHandler(combat_use_potion_callback, pattern=r'^combat_use:.*$')