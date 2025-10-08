# handlers/menu/kingdom.py

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from modules import player_manager, game_data, file_ids


logger = logging.getLogger(__name__)

async def show_kingdom_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o menu principal do Reino de Eldora."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    player_data = player_manager.get_player_data(user.id)

    if not player_data:
        await context.bot.send_message(chat_id=chat_id, text="Personagem não encontrado. Use /start para criar um.")
        return

    player_data['current_location'] = 'reino_eldora'
    player_manager.save_player_data(user.id, player_data)

    character_name = player_data.get("character_name", "Aventureiro(a)")
    total_stats = player_manager.get_player_total_stats(player_data)

    p_hp = int(player_data.get('current_hp', 0))
    p_max_hp = int(total_stats.get('max_hp', 0))
    p_energy = int(player_data.get('energy', 0))
    max_energy = int(player_manager.get_player_max_energy(player_data))

    status_footer = (
        f"\n\n═════════════ ◆◈◆ ══════════════\n"
        f"❤️ 𝐇𝐏: {p_hp}/{p_max_hp}   "
        f"⚡️🔋𝐄𝐧𝐞𝐫𝐠𝐢𝐚🪫⚡️: {p_energy}/{max_energy}"
    )

    caption = (
        f"𝐎 𝐪𝐮𝐞 𝐯𝐨𝐜ê 𝐠𝐨𝐬𝐭𝐚𝐫𝐢𝐚 𝐝𝐞 𝐟𝐚𝐳𝐞𝐫 𝐧𝐨 𝐑𝐞𝐢𝐧𝐨 𝐝𝐞 𝐄𝐥𝐝𝐨𝐫𝐚, {character_name}?"
        + status_footer
    )

    keyboard = [
        [InlineKeyboardButton("🗺 𝐕𝐢𝐚𝐣𝐚𝐫 🗺", callback_data='travel')],
        [InlineKeyboardButton("🛡️ 𝐆𝐮𝐢𝐥𝐝𝐚 🛡️", callback_data='guild_menu')],
        [
            InlineKeyboardButton("🏪 𝐌𝐞𝐫𝐜𝐚𝐝𝐨 🏪", callback_data='market'),
            InlineKeyboardButton("⚒️ 𝐅𝐨𝐫𝐣𝐚 ⚒️", callback_data='forge:main'),
        ],
        [InlineKeyboardButton("🧪 𝐑𝐞𝐟𝐢𝐧𝐨 🧪", callback_data='refining_main')],
        [InlineKeyboardButton("🆅🆂 𝐀𝐫𝐞𝐧𝐚 𝐝𝐞 𝐄𝐥𝐝𝐨𝐫𝐚 🆅🆂", callback_data='pvp_arena')], 
        [InlineKeyboardButton("💀 𝐄𝐯𝐞𝐧𝐭𝐨𝐬 𝐄𝐬𝐩𝐞𝐜𝐢𝐚𝐢𝐬 💀", callback_data='show_events_menu')],
        [InlineKeyboardButton("👤 𝐏𝐞𝐫𝐬𝐨𝐧𝐚𝐠𝐞𝐦 👤", callback_data='profile')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # se veio de callback, remove a mensagem anterior
    if update.callback_query:
        try:
            await update.callback_query.delete_message()
        except Exception as e:
            logger.debug("Não foi possível apagar mensagem anterior: %s", e)

    # usa file_ids (photo/video) se existir; senão, texto
    fd = file_ids.get_file_data('regiao_reino_eldora')
    if fd and fd.get("id"):
        try:
            if (fd.get("type") or "photo").lower() == "video":
                await context.bot.send_video(
                    chat_id=chat_id, video=fd["id"],
                    caption=caption, reply_markup=reply_markup, parse_mode='HTML'
                )
            else:
                await context.bot.send_photo(
                    chat_id=chat_id, photo=fd["id"],
                    caption=caption, reply_markup=reply_markup, parse_mode='HTML'
                )
            return
        except Exception as e:
            logger.debug("Falha ao enviar mídia do reino (%s): %s", fd, e)

    await context.bot.send_message(
        chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode='HTML'
    )
