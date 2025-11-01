# handlers/combat/potion_handler.py


import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules import player_manager, game_data
from modules.player import actions as player_actions
from handlers.utils import format_combat_message
from telegram.error import BadRequest

logger = logging.getLogger(__name__)

async def combat_potion_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a lista de poções disponíveis em combate."""
    query = update.callback_query
    await query.answer()
    
    player_data = await player_manager.get_player_data(query.from_user.id)
    inventory = player_data.get("inventory", {})
    
    potion_buttons = []
    for item_id, quantity in inventory.items():
        item_info = game_data.ITEMS_DATA.get(item_id, {})
        if item_info.get("type") == "potion":
            item_name = item_info.get("display_name", item_id)
            item_emoji = item_info.get("emoji", "🧪")
            potion_buttons.append(InlineKeyboardButton(f"{item_emoji} {item_name} (x{quantity})", callback_data=f"combat_use:{item_id}"))

    keyboard = [[btn] for btn in potion_buttons]
    keyboard.append([InlineKeyboardButton("⬅️ Voltar à Batalha", callback_data="combat_attack_menu")])
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

async def combat_use_potion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa o uso de uma poção em combate."""
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        item_id_to_use = query.data.split(':')[1]
    except IndexError:
        await query.answer("Erro ao usar o item.", show_alert=True)
        return

    player_data = await player_manager.get_player_data(user_id)
    
    # Etapa 1: Tenta consumir o item
    if not player_manager.remove_item_from_inventory(player_data, item_id_to_use, 1):
        await query.answer("Você não tem este item para usar!", show_alert=True)
        await combat_potion_menu_callback(update, context) 
        return

    # Etapa 2: Aplica os efeitos
    item_info = game_data.ITEMS_DATA.get(item_id_to_use, {})
    effects = item_info.get("effects", {})
    feedback_message = ""
    level_up_msg = None

    if 'heal' in effects:
        heal_amount = effects['heal']
        
        # <<< [MUDANÇA] Adiciona 'await' >>>
        await player_actions.heal_player(player_data, heal_amount)
        
        feedback_message = f"Você usou {item_info.get('display_name')} e recuperou {heal_amount} HP!"
    
    elif 'add_energy' in effects:
        energy_amount = effects['add_energy']
        player_actions.add_energy(player_data, energy_amount)
        feedback_message = f"Você usou {item_info.get('display_name')} e recuperou {energy_amount} de Energia!"
    
    elif 'add_mana' in effects:
        mana_amount = effects['add_mana']
        
        # <<< [MUDANÇA] Adiciona 'await' >>>
        await player_actions.add_mana(player_data, mana_amount)
        
        feedback_message = f"Você usou {item_info.get('display_name')} e recuperou {mana_amount} de Mana!"
        
    elif 'add_xp' in effects:
        xp_amount = effects['add_xp']
        player_data['xp'] = player_data.get('xp', 0) + xp_amount
        niveis, pontos, level_up_msg = player_manager.check_and_apply_level_up(player_data)
        
        feedback_message = f"Você usou {item_info.get('display_name')} e ganhou {xp_amount} XP!"
        if level_up_msg:
            feedback_message += "\n\n" + level_up_msg
            
    elif 'buff' in effects:
        buff = effects['buff']
        player_actions.add_buff(player_data, buff)
        stat_name = buff.get('stat', 'um atributo').replace("_", " ").capitalize()
        feedback_message = f"Você usou {item_info.get('display_name')} e ganhou um bónus de {stat_name}!"
    
    else:
        await query.answer("Esta poção não tem um efeito reconhecido.", show_alert=True)
        # Devolve o item
        player_manager.add_item_to_inventory(player_data, item_id_to_use, 1)
        await player_manager.save_player_data(user_id, player_data)
        return

    # Adiciona a ação ao log de combate
    state = player_data.get('player_state', {})
    if state.get('action') == 'in_combat':
        state['details']['battle_log'].append(f"✨ {feedback_message.splitlines()[0]}")

    # Salva os dados
    await player_manager.save_player_data(user_id, player_data)
    
    await query.answer(feedback_message, show_alert=True)
    
    # <<< [MUDANÇA] Adiciona 'await' >>>
    # (Este era o segundo crash 'TypeError: coroutine not serializable')
    new_text = await format_combat_message(player_data)
    
    kb = [
        [InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), InlineKeyboardButton("✨ Skills", callback_data='combat_skill_menu')],
        [InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu')],
        [InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')]
    ]
    
    try:
        await query.edit_message_caption(caption=new_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    except BadRequest as e:
        # Fallback se a msg for de texto (ex: /start)
        if "message can't be edited" in str(e).lower():
            try:
                await query.message.delete()
                # (Precisamos de uma função 'send_battle_media' aqui, mas por agora
                # vamos apenas enviar texto para evitar mais erros)
                await context.bot.send_message(chat_id=user_id, text=new_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
            except Exception:
                pass # Ignora se falhar
        elif "message is not modified" not in str(e).lower():
            logger.warning(f"Erro ao editar caption em potion_handler: {e}")

# Exporta os handlers
combat_potion_menu_handler = CallbackQueryHandler(combat_potion_menu_callback, pattern=r'^combat_potion_menu$')
combat_use_potion_handler = CallbackQueryHandler(combat_use_potion_callback, pattern=r'^combat_use:.*$')