# Em handlers/skin_handler.py (NOVO ARQUIVO)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, game_data
from modules.game_data.skins import SKIN_CATALOG

logger = logging.getLogger(__name__)

async def show_skin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    player_data = player_manager.get_player_data(user_id)
    player_class = player_data.get("class")
    
    if not player_class:
        await query.answer("Você precisa de ter uma classe para mudar de aparência!", show_alert=True)
        return

    unlocked_skins = player_data.get("unlocked_skins", [])
    equipped_skin = player_data.get("equipped_skin")
    
    caption = "🎨 **Mudar Aparência**\n\nSelecione uma aparência que já desbloqueou para a equipar."
    keyboard = []
    
    # Filtra o catálogo para mostrar apenas skins da classe do jogador que ele já desbloqueou
    available_skins = {skin_id: data for skin_id, data in SKIN_CATALOG.items() if data['class'] == player_class and skin_id in unlocked_skins}
    
    if not available_skins:
        caption += "\n\nVocê ainda não desbloqueou nenhuma aparência para a sua classe."
    else:
        for skin_id, skin_data in available_skins.items():
            prefix = "✅" if skin_id == equipped_skin else "➡️"
            keyboard.append([
                InlineKeyboardButton(
                    f"{prefix} {skin_data['display_name']}",
                    callback_data=f"equip_skin:{skin_id}"
                )
            ])

    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Perfil", callback_data="profile")])
    await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def equip_skin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        skin_id_to_equip = query.data.split(':')[1]
    except IndexError:
        await query.answer("Erro: Skin não especificada.", show_alert=True)
        return
        
    player_data = player_manager.get_player_data(user_id)
    
    # Segurança: verifica se o jogador realmente possui a skin
    if skin_id_to_equip not in player_data.get("unlocked_skins", []):
        await query.answer("Você não possui esta aparência!", show_alert=True)
        return
        
    player_data["equipped_skin"] = skin_id_to_equip
    player_manager.save_player_data(user_id, player_data)
    
    await query.answer("Aparência equipada com sucesso!", show_alert=True)
    
    # Atualiza o menu para mostrar o "✅" no sítio certo
    await show_skin_menu(update, context)

# --- REGISTO DOS HANDLERS ---
skin_menu_handler = CallbackQueryHandler(show_skin_menu, pattern=r"^skin_menu$")
equip_skin_handler = CallbackQueryHandler(equip_skin_callback, pattern=r"^equip_skin:.*$")

all_skin_handlers = [skin_menu_handler, equip_skin_handler]