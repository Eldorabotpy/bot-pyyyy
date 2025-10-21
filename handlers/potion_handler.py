# handlers/potion_handler.py (NOVO ARQUIVO)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, game_data

logger = logging.getLogger(__name__)

# Esta função será chamada para mostrar o menu de poções
async def show_potion_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    player_data = player_manager.get_player_data(user_id)
    inventory = player_data.get("inventory", {})
    
    caption = "🧪 **Poções & Consumíveis**\n\nSelecione um item para usar."
    keyboard = []
    
    # Procura no inventário por itens do tipo "potion"
    found_potions = False
    for item_id, quantity in inventory.items():
        item_info = game_data.ITEMS_DATA.get(item_id, {})
        if item_info.get("type") == "potion":
            found_potions = True
            item_name = item_info.get("display_name", item_id)
            item_emoji = item_info.get("emoji", "🧪")
            # Cria um botão para cada poção que o jogador possui
            keyboard.append([
                InlineKeyboardButton(
                    f"{item_emoji} {item_name} (x{quantity})",
                    callback_data=f"use_potion:{item_id}"
                )
            ])

    if not found_potions:
        caption += "\n\nVocê não possui nenhuma poção no seu inventário."

    # Adiciona um botão para voltar (sugiro voltar ao perfil)
    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Perfil", callback_data="profile")])
    
    await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


# Esta função será chamada quando o jogador clicar para usar uma poção
async def use_potion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        item_id_to_use = query.data.split(':')[1]
    except IndexError:
        await query.answer("Erro: Item não especificado.", show_alert=True)
        return

    player_data = player_manager.get_player_data(user_id)
    item_info = game_data.ITEMS_DATA.get(item_id_to_use, {})
    effects = item_info.get("effects", {})

    if not effects:
        await query.answer("Este item não tem efeito.", show_alert=True)
        return
        
    # --- LÓGICA DE APLICAÇÃO DOS EFEITOS ---
    success_message = ""

    # Efeito de Cura
    if 'heal' in effects:
        heal_amount = effects['heal']
        player_manager.heal_player(player_data, heal_amount) # Precisaremos de criar esta função
        success_message = f"Você usou {item_info.get('display_name')} e recuperou {heal_amount} HP!"

    # Efeito de Energia
    elif 'add_energy' in effects:
        energy_amount = effects['add_energy']
        player_manager.add_energy(player_data, energy_amount)
        success_message = f"Você usou {item_info.get('display_name')} e recuperou {energy_amount} de Energia!"
        
    # Efeito de XP
    elif 'add_xp' in effects:
        xp_amount = effects['add_xp']
        player_data['xp'] = player_data.get('xp', 0) + xp_amount
        success_message = f"Você usou {item_info.get('display_name')} e ganhou {xp_amount} XP!"
        # Verifica se o jogador subiu de nível
        _, _, level_up_msg = player_manager.check_and_apply_level_up(player_data)
        if level_up_msg:
            success_message += level_up_msg

    # Efeito de Buff (bónus temporário) - Implementaremos a aplicação no próximo passo
    elif 'buff' in effects:
        buff = effects['buff']
        player_manager.add_buff(player_data, buff) # Precisaremos de criar esta função
        stat_name = buff.get('stat', '').capitalize()
        success_message = f"Você usou {item_info.get('display_name')} e ganhou um bónus de {stat_name}!"

    # Remove 1 poção do inventário e salva os dados
    player_manager.remove_item_from_inventory(player_data, item_id_to_use, 1)
    player_manager.save_player_data(user_id, player_data)

    # Dá o feedback ao jogador e atualiza o menu
    await query.answer(success_message, show_alert=True)
    await show_potion_menu(update, context) # Atualiza o menu de poções


# --- REGISTO DOS HANDLERS ---
potion_menu_handler = CallbackQueryHandler(show_potion_menu, pattern=r"^potion_menu$")
use_potion_handler = CallbackQueryHandler(use_potion_callback, pattern=r"^use_potion:.*$")

all_potion_handlers = [potion_menu_handler, use_potion_handler]