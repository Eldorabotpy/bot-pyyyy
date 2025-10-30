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
    
    # <<< CORREÇÃO 1: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
         # Adiciona um fallback se os dados do jogador não forem encontrados
         await query.edit_message_caption(caption="Erro ao carregar dados. Tente /start.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="profile")]]))
         return
         
    player_class = player_data.get("class") # Síncrono
    
    if not player_class:
        await query.answer("Você precisa de ter uma classe para mudar de aparência!", show_alert=True)
        return

    # Lógica síncrona
    unlocked_skins = player_data.get("unlocked_skins", [])
    equipped_skin = player_data.get("equipped_skin")
    
    caption = "🎨 **Mudar Aparência**\n\nSelecione uma aparência que já desbloqueou para a equipar."
    keyboard = []
    
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
    # Await já estava correto aqui
    try:
         await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    except Exception as e:
         # Fallback se a mensagem original não tiver mídia
         logger.warning(f"Falha ao editar caption em show_skin_menu (provavelmente era texto): {e}")
         try:
              await query.edit_message_text(text=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
         except Exception as e_text:
              logger.error(f"Falha crítica ao editar menu de skin: {e_text}")

async def equip_skin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        skin_id_to_equip = query.data.split(':')[1]
    except IndexError:
        await query.answer("Erro: Skin não especificada.", show_alert=True)
        return
        
    # <<< CORREÇÃO 2: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
         await query.answer("Erro ao carregar dados do jogador.", show_alert=True)
         return

    # Segurança (síncrona)
    if skin_id_to_equip not in player_data.get("unlocked_skins", []):
        await query.answer("Você não possui esta aparência!", show_alert=True)
        return
        
    player_data["equipped_skin"] = skin_id_to_equip # Síncrono
    
    # <<< CORREÇÃO 3: Adiciona await >>>
    await player_manager.save_player_data(user_id, player_data)
    
    await query.answer("Aparência equipada com sucesso!", show_alert=True)
    
    # <<< CORREÇÃO 4: Adiciona await >>>
    await show_skin_menu(update, context) # Chama a função async

# --- REGISTO DOS HANDLERS ---
skin_menu_handler = CallbackQueryHandler(show_skin_menu, pattern=r"^skin_menu$")
equip_skin_handler = CallbackQueryHandler(equip_skin_callback, pattern=r"^equip_skin:.*$")

all_skin_handlers = [skin_menu_handler, equip_skin_handler]