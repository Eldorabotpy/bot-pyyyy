# handlers/status_handler.py (VERSÃO FINAL E COMPATÍVEL)

import logging
import re
import unicodedata
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.error import BadRequest

from modules import player_manager, game_data, file_ids

logger = logging.getLogger(__name__)

PROFILE_KEYS = ['max_hp', 'attack', 'defense', 'initiative', 'luck']

def _slugify(text: str) -> str:
    if not text: return ""
    norm = unicodedata.normalize("NFKD", text)
    norm = norm.encode("ascii", "ignore").decode("ascii")
    norm = re.sub(r"\s+", "_", norm.strip().lower())
    norm = re.sub(r"[^a-z0-9_]", "", norm)
    return norm

def _get_class_media(player_data: dict, purpose: str = "status"):
    raw_cls = (player_data.get("class") or "").strip()
    cls = _slugify(raw_cls)
    classes_data = getattr(game_data, "CLASSES_DATA", {}) or {}
    cls_cfg = classes_data.get(raw_cls) or classes_data.get(cls) or {}
    candidates = [cls_cfg.get(k) for k in ("status_file_id_key",) if cls_cfg.get(k)]
    if cls:
        candidates += [f"status_video_{cls}", f"status_{cls}", f"class_{cls}_status"]
    candidates.append("status_video")
    for key in [k for k in candidates if k]:
        fd = file_ids.get_file_data(key)
        if fd and fd.get("id"):
            return fd
    return None

def _get_status_content(player_data: dict) -> tuple[str, InlineKeyboardMarkup]:
    """Gera o texto e o teclado do menu de status."""
    total_stats = player_manager.get_player_total_stats(player_data)
    char_name = player_data.get('character_name', 'Aventureiro(a)')
    status_text = f"👤 <b>Status de {char_name}</b>\n\n"
    emoji_map = {'max_hp': '❤️', 'attack': '⚔️', 'defense': '🛡️', 'initiative': '🏃', 'luck': '🍀'}
    name_map = {'max_hp': 'HP Máximo', 'attack': 'Ataque', 'defense': 'Defesa', 'initiative': 'Iniciativa', 'luck': 'Sorte'}
    for stat in PROFILE_KEYS:
        val = int(total_stats.get(stat, 0))
        status_text += f"{emoji_map[stat]} <b>{name_map[stat]}:</b> {val}\n"
    available_points = int(player_data.get('stat_points', 0) or 0)
    status_text += f"\n✨ <b>Pontos disponíveis:</b> {available_points}"
    keyboard_rows = []
    if available_points > 0:
        keyboard_rows.append([InlineKeyboardButton("➕ HP (+3)", callback_data='upgrade_max_hp'), InlineKeyboardButton("➕ ATK (+1)", callback_data='upgrade_attack')])
        keyboard_rows.append([InlineKeyboardButton("➕ DEF (+1)", callback_data='upgrade_defense'), InlineKeyboardButton("➕ INI (+1)", callback_data='upgrade_initiative')])
        keyboard_rows.append([InlineKeyboardButton("➕ SORTE (+1)", callback_data='upgrade_luck')])
    keyboard_rows.append([InlineKeyboardButton("🎐 𝐄𝐯𝐨𝐥𝐮çã𝐨 𝐝𝐞 𝐂𝐥𝐚𝐬𝐬𝐞", callback_data="status_evolution_open")])
    keyboard_rows.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data='profile')])
    return status_text, InlineKeyboardMarkup(keyboard_rows)

async def show_status_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a tela de status, funcionando para comando /status e botão."""
    user_id = update.effective_user.id
    player_data = player_manager.get_player_data(user_id)
    if not player_data:
        text = "Você precisa criar um personagem. Use /start."
        if update.callback_query: await update.callback_query.edit_message_text(text)
        else: await update.message.reply_text(text)
        return
    status_text, reply_markup = _get_status_content(player_data)
    chat_id = update.effective_chat.id
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        media = _get_class_media(player_data, "status")
        if media and media.get("id"):
            try: await query.delete_message()
            except BadRequest: pass
            media_id, media_type = media["id"], (media.get("type") or "photo").lower()
            if media_type == "video":
                await context.bot.send_video(chat_id=chat_id, video=media_id, caption=status_text, reply_markup=reply_markup, parse_mode='HTML')
            else:
                await context.bot.send_photo(chat_id=chat_id, photo=media_id, caption=status_text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            try: await query.edit_message_text(status_text, reply_markup=reply_markup, parse_mode='HTML')
            except BadRequest: await context.bot.send_message(chat_id, status_text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(text=status_text, reply_markup=reply_markup, parse_mode='HTML')

async def upgrade_stat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aplica o upgrade de stat e edita a mensagem existente."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    player_data = player_manager.get_player_data(user_id)
    pool = int(player_data.get("stat_points", 0) or 0)
    if pool <= 0:
        await query.answer("Você não tem pontos de atributo para gastar!", show_alert=True)
        return
    profile_stat = query.data.replace('upgrade_', '')
    if profile_stat not in PROFILE_KEYS: return
    player_data["stat_points"] = pool - 1
    inc = 3 if profile_stat == "max_hp" else 1
    player_data[profile_stat] = int(player_data.get(profile_stat, 0)) + inc
    if profile_stat == "max_hp":
        player_data["current_hp"] = int(player_data.get("current_hp", 0)) + inc
    player_manager.save_player_data(user_id, player_data)
    status_text, reply_markup = _get_status_content(player_data)
    try:
        await query.edit_message_caption(caption=status_text, reply_markup=reply_markup, parse_mode='HTML')
    except BadRequest:
        try:
            await query.edit_message_text(text=status_text, reply_markup=reply_markup, parse_mode='HTML')
        except BadRequest as e:
            logger.error(f"Falha crítica ao editar menu de status: {e}")
            
async def close_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fecha (apaga) a mensagem de status."""
    query = update.callback_query
    await query.answer()
    try:
        await query.delete_message()
    except Exception:
        pass

# ==== EXPORTS ====
status_command_handler = CommandHandler("status", show_status_menu)
status_open_handler = CallbackQueryHandler(show_status_menu, pattern=r'^status_open$')
status_callback_handler = CallbackQueryHandler(upgrade_stat_callback, pattern=r'^upgrade_')
close_status_handler = CallbackQueryHandler(close_status_callback, pattern=r'^close_status$')