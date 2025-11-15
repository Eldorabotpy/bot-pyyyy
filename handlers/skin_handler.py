# handlers/skin_handler.py
# (VERSÃO FINAL E LIMPA)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest
from modules.player import stats as player_stats
from modules import player_manager, game_data
from modules.game_data.skins import SKIN_CATALOG

logger = logging.getLogger(__name__)

async def show_skin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await query.edit_message_caption(caption="Erro ao carregar dados. Tente /start.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="profile")]]))
        return
        
    try:
        player_class_key = player_stats._get_class_key_normalized(player_data)
    except Exception:
        player_class_key = (player_data.get("class") or "").lower() # Fallback
    
    if not player_class_key:
        await query.answer("Você precisa de ter uma classe para mudar de aparência!", show_alert=True)
        return

    unlocked_skins = player_data.get("unlocked_skins", [])
    equipped_skin = player_data.get("equipped_skin") # Pode ser None
    
    caption = "🎨 **Mudar Aparência**\n\nSelecione uma aparência que já desbloqueou para a equipar."
    keyboard = []
    
    available_skins = {
        skin_id: data for skin_id, data in SKIN_CATALOG.items() 
        if data.get('class') == player_class_key and skin_id in unlocked_skins
    }
    
    # Adiciona o botão "Aparência Padrão"
    if equipped_skin is None:
        keyboard.append([
            InlineKeyboardButton("✅ Aparência Padrão (Equipada)", callback_data="noop_skin_equipped")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("🎨 Usar Aparência Padrão", callback_data="unequip_skin")
        ])

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

    try:
        await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    except BadRequest as e: 
        logger.warning(f"Falha ao editar caption em show_skin_menu (provavelmente era texto): {e}")
        try:
            await query.edit_message_text(text=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        except Exception as e_text:
            logger.error(f"Falha crítica ao editar menu de skin: {e_text}")
    except Exception as e_geral:
        logger.error(f"Erro inesperado em show_skin_menu: {e_geral}", exc_info=True)


async def equip_skin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        skin_id_to_equip = query.data.split(':')[1]
    except IndexError:
        await query.answer("Erro: Skin não especificada.", show_alert=True)
        return
        
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await query.answer("Erro ao carregar dados do jogador.", show_alert=True)
        return

    if skin_id_to_equip not in player_data.get("unlocked_skins", []):
        await query.answer("Você não possui esta aparência!", show_alert=True)
        return
    
    if player_data.get("equipped_skin") == skin_id_to_equip:
        await query.answer("Essa aparência já está equipada.", show_alert=False)
        return

    player_data["equipped_skin"] = skin_id_to_equip
    
    await player_manager.save_player_data(user_id, player_data)
    await query.answer("Aparência equipada com sucesso!", show_alert=True)
    await show_skin_menu(update, context) # Recarrega o menu


async def unequip_skin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await query.answer("Erro ao carregar dados do jogador.", show_alert=True)
        return

    if player_data.get("equipped_skin") is None:
        await query.answer("Você já está com a aparência padrão.", show_alert=False)
        return

    player_data["equipped_skin"] = None
    
    await player_manager.save_player_data(user_id, player_data)
    
    await query.answer("Aparência padrão restaurada!", show_alert=True)
    
    await show_skin_menu(update, context) # Recarrega o menu

async def noop_skin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback para o botão "Padrão (Equipada)" que não faz nada."""
    await update.callback_query.answer("Você já está usando a aparência padrão.")

# --- REGISTO DOS HANDLERS (Atualizado) ---
skin_menu_handler = CallbackQueryHandler(show_skin_menu, pattern=r"^skin_menu$")
equip_skin_handler = CallbackQueryHandler(equip_skin_callback, pattern=r"^equip_skin:.*$")
unequip_skin_handler = CallbackQueryHandler(unequip_skin_callback, pattern=r"^unequip_skin$")
noop_skin_handler = CallbackQueryHandler(noop_skin_callback, pattern=r"^noop_skin_equipped$")

all_skin_handlers = [
    skin_menu_handler, 
    equip_skin_handler, 
    unequip_skin_handler, 
    noop_skin_handler
]