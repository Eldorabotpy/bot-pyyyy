# handlers/potion_handler.py
# (VERSÃO FINAL: AUTH UNIFICADA + ID SEGURO)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, game_data
from modules.auth_utils import get_current_player_id  # <--- ÚNICA FONTE DE VERDADE

logger = logging.getLogger(__name__)

# Esta função será chamada para mostrar o menu de poções
async def show_potion_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # 🔒 SEGURANÇA: ID via Auth Central
    user_id = get_current_player_id(update, context)
    if not user_id:
        if query: await query.answer("Sessão inválida. Use /start.", show_alert=True)
        return

    # <<< CORREÇÃO 1: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        if query: await query.answer("Dados do jogador não encontrados.", show_alert=True)
        return

    inventory = player_data.get("inventory", {})

    caption = "🧪 **Poções & Consumíveis**\n\nSelecione um item para usar."
    keyboard = []

    # Procura no inventário por itens do tipo "potion" (Síncrono)
    found_potions = False
    for item_id, quantity in inventory.items():
        # Verifica se é um dicionário (item único) ou int (stack)
        if isinstance(quantity, dict):
             # Lógica para itens únicos (se houver poções únicas)
             continue
        
        item_info = game_data.ITEMS_DATA.get(item_id, {})
        if item_info.get("type") == "potion":
            found_potions = True
            item_name = item_info.get("display_name", item_id)
            item_emoji = item_info.get("emoji", "🧪")
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

    # Tenta editar caption, se falhar (ex: msg de texto), tenta editar texto
    try:
        await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    except Exception:
         try:
              await query.edit_message_text(text=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
         except Exception as e:
              logger.warning(f"Falha ao editar menu de poções: {e}")

# Esta função será chamada quando o jogador clicar para usar uma poção
async def use_potion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # 🔒 SEGURANÇA: ID via Auth Central
    user_id = get_current_player_id(update, context)
    if not user_id:
        await query.answer("Sessão inválida. Use /start.", show_alert=True)
        return

    try:
        item_id_to_use = query.data.split(':')[1]
    except IndexError:
        await query.answer("Erro: Item não especificado.", show_alert=True)
        return

    # <<< CORREÇÃO 2: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await query.answer("Perfil não encontrado.", show_alert=True)
        return

    item_info = game_data.ITEMS_DATA.get(item_id_to_use, {}) # Síncrono
    effects = item_info.get("effects", {}) # Síncrono

    if not effects:
        await query.answer("Este item não tem efeito.", show_alert=True)
        return

    # Verifica se tem o item ANTES de aplicar o efeito (Boa prática)
    if not player_manager.has_item(player_data, item_id_to_use, 1): # Síncrono
        await query.answer("Você não tem mais este item!", show_alert=True)
        await show_potion_menu(update, context) # Atualiza o menu (já usa await)
        return

    # --- LÓGICA DE APLICAÇÃO DOS EFEITOS (Síncrona) ---
    success_message = ""
    level_up_msg = "" # Inicializa level_up_msg

    if 'heal' in effects:
        heal_amount = effects['heal']
        player_manager.heal_player(player_data, heal_amount) # Síncrono
        success_message = f"Você usou {item_info.get('display_name')} e recuperou {heal_amount} HP!"
    elif 'add_energy' in effects:
        energy_amount = effects['add_energy']
        player_manager.add_energy(player_data, energy_amount) # Síncrono
        success_message = f"Você usou {item_info.get('display_name')} e recuperou {energy_amount} de Energia!"
    elif 'add_xp' in effects:
        xp_amount = effects['add_xp']
        player_data['xp'] = player_data.get('xp', 0) + xp_amount # Síncrono
        success_message = f"Você usou {item_info.get('display_name')} e ganhou {xp_amount} XP!"
        _, _, level_up_msg_result = player_manager.check_and_apply_level_up(player_data) # Síncrono
        if level_up_msg_result:
            level_up_msg = level_up_msg_result # Armazena a mensagem de level up
    elif 'buff' in effects:
        buff = effects['buff']
        player_manager.add_buff(player_data, buff) # Síncrono
        stat_name = buff.get('stat', '').capitalize()
        success_message = f"Você usou {item_info.get('display_name')} e ganhou um bónus de {stat_name}!"
    else:
         # Se nenhum efeito foi aplicado, não faz nada
         await query.answer("Efeito desconhecido.", show_alert=True)
         return

    # Remove 1 poção do inventário E salva os dados
    player_manager.remove_item_from_inventory(player_data, item_id_to_use, 1) # Síncrono

    # <<< CORREÇÃO 3: Adiciona await >>>
    await player_manager.save_player_data(user_id, player_data)

    # Se houve uma mensagem de level up, adiciona ao feedback
    if level_up_msg:
        success_message += "\n" + level_up_msg

    # Dá o feedback ao jogador e atualiza o menu
    await query.answer(success_message, show_alert=True)
    await show_potion_menu(update, context) # Atualiza o menu de poções (já usa await)

# --- REGISTO DOS HANDLERS ---
potion_menu_handler = CallbackQueryHandler(show_potion_menu, pattern=r"^potion_menu$")
use_potion_handler = CallbackQueryHandler(use_potion_callback, pattern=r"^use_potion:.*$")

all_potion_handlers = [potion_menu_handler, use_potion_handler]