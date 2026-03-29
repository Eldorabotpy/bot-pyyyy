# handlers/skin_handler.py
# (VERSÃO FINAL: AUTH UNIFICADA + ID SEGURO + RENDERIZAÇÃO DE GÊNERO/HÍBRIDA)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

from modules.player import stats as player_stats
from modules import player_manager, game_data, file_id_manager
from modules.game_data.skins import SKIN_CATALOG, get_skin_avatar
from modules.game_data.classes import get_class_avatar
from modules.auth_utils import get_current_player_id

logger = logging.getLogger(__name__)

async def show_skin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # 🔒 SEGURANÇA: ID via Auth Central
    user_id = get_current_player_id(update, context)
    if not user_id:
        await query.answer("Sessão inválida. Use /start.", show_alert=True)
        return
    
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        try:
            await query.edit_message_caption(
                caption="Erro ao carregar dados. Tente /start.", 
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="profile")]])
            )
        except: pass
        return
        
    try:
        player_class_key = player_stats._get_class_key_normalized(player_data)
    except Exception:
        player_class_key = (player_data.get("class") or "").lower()
    
    if not player_class_key:
        await query.answer("Você precisa ter uma classe para mudar de aparência!", show_alert=True)
        return

    unlocked_skins = player_data.get("unlocked_skins", [])
    equipped_skin = player_data.get("equipped_skin")
    player_gender = player_data.get("gender", "masculino")
    gender_suffix = "_female" if player_gender == "feminino" else "_male"
    
    # ==========================================
    # LÓGICA DE BUSCA DA IMAGEM (HÍBRIDA)
    # ==========================================
    file_data = None
    avatar_url = None

    if equipped_skin and equipped_skin in SKIN_CATALOG:
        skin_info = SKIN_CATALOG[equipped_skin]
        base_file_name = skin_info.get("media_key")
        
        # 1. Tenta pegar a imagem da skin no Telegram com sufixo de gênero
        if base_file_name:
            file_data = file_id_manager.get_file_data(f"{base_file_name}{gender_suffix}")
            # Fallback sem gênero
            if not file_data:
                file_data = file_id_manager.get_file_data(base_file_name)
        
        # 2. Fallback Web App (GitHub) para Skins
        if not file_data:
            avatar_url = get_skin_avatar(equipped_skin, player_gender)
    else:
        # 3. Tenta pegar a imagem PADRÃO da classe no Telegram
        file_data = file_id_manager.get_file_data(f"classe_{player_class_key}_media{gender_suffix}")
        if not file_data:
            file_data = file_id_manager.get_file_data(f"classe_{player_class_key}_media")
        
        # 4. Fallback Web App (GitHub) para Classes
        if not file_data:
            avatar_url = get_class_avatar(player_class_key, player_gender)

    # ==========================================
    # MONTAGEM DO MENU E BOTÕES
    # ==========================================
    caption = "🎨 <b>Mudar Aparência</b>\n\nSelecione uma aparência que já desbloqueou para a equipar."
    keyboard = []
    
    available_skins = {
        skin_id: data for skin_id, data in SKIN_CATALOG.items() 
        if data.get('class') == player_class_key and skin_id in unlocked_skins
    }
    
    if equipped_skin is None:
        keyboard.append([InlineKeyboardButton("✅ Aparência Padrão (Equipada)", callback_data="noop_skin_equipped")])
    else:
        keyboard.append([InlineKeyboardButton("🎨 Usar Aparência Padrão", callback_data="unequip_skin")])

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
    reply_markup = InlineKeyboardMarkup(keyboard)

    # ==========================================
    # ATUALIZAÇÃO DA MENSAGEM COM A FOTO NOVA
    # ==========================================
    try:
        # Se achou no Telegram:
        if file_data and file_data.get("id"):
            media = InputMediaPhoto(media=file_data["id"], caption=caption, parse_mode="HTML")
            await query.edit_message_media(media=media, reply_markup=reply_markup)
        
        # Se achou no GitHub:
        elif avatar_url and avatar_url.startswith("http"):
            media = InputMediaPhoto(media=avatar_url, caption=caption, parse_mode="HTML")
            await query.edit_message_media(media=media, reply_markup=reply_markup)
        
        # Se não achou nada, edita só o texto:
        else:
            await query.edit_message_caption(caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            
    except BadRequest as e:
        # O Telegram dá erro se tentarmos trocar a foto pela MESMA foto (ex: clicou na skin que já estava). 
        # Ignoramos esse erro específico silenciosamente.
        if "Message is not modified" not in str(e):
            logger.warning(f"Falha ao editar media em show_skin_menu: {e}")
            try:
                await query.edit_message_text(text=caption, reply_markup=reply_markup, parse_mode="HTML")
            except Exception:
                pass

async def equip_skin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    user_id = get_current_player_id(update, context)
    if not user_id:
        await query.answer("Sessão inválida.", show_alert=True)
        return
    
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
    await query.answer("Aparência equipada com sucesso!", show_alert=False)
    
    # Chama o menu de novo para ele trocar a imagem instantaneamente!
    await show_skin_menu(update, context)


async def unequip_skin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    user_id = get_current_player_id(update, context)
    if not user_id:
        await query.answer("Sessão inválida.", show_alert=True)
        return
    
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await query.answer("Erro ao carregar dados do jogador.", show_alert=True)
        return

    if player_data.get("equipped_skin") is None:
        await query.answer("Você já está com a aparência padrão.", show_alert=False)
        return

    player_data["equipped_skin"] = None
    
    await player_manager.save_player_data(user_id, player_data)
    await query.answer("Aparência padrão restaurada!", show_alert=False)
    
    # Atualiza a imagem de volta para o padrão
    await show_skin_menu(update, context)

async def noop_skin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Você já está usando a aparência padrão.")

# --- REGISTO DOS HANDLERS ---
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