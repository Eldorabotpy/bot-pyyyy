# handlers/menu/kingdom.py
# (VERSÃO FINAL: COM OURO E GEMAS NO RODAPÉ)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes
from modules import player_manager, game_data, file_ids
from kingdom_defense import leaderboard 

logger = logging.getLogger(__name__)

async def show_kingdom_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, player_data: dict | None = None):
    """Mostra o menu principal do Reino de Eldora."""
    query = update.callback_query
    user = update.effective_user
    chat_id = update.effective_chat.id

    if player_data is None:
        player_data = await player_manager.get_player_data(user.id)
        if not player_data:
            await context.bot.send_message(chat_id=chat_id, text="Personagem não encontrado. Use /start para criar um.")
            return

    # Atualiza localização
    player_data['current_location'] = 'reino_eldora'
    await player_manager.save_player_data(user.id, player_data) 

    # Dados para o rodapé
    character_name = player_data.get("character_name", "Aventureiro(a)")
    total_stats = await player_manager.get_player_total_stats(player_data)
    
    # --- STATUS BÁSICOS ---
    p_hp = int(player_data.get('current_hp', 0))
    p_max_hp = int(total_stats.get('max_hp', 0))
    p_energy = int(player_data.get('energy', 0))
    max_energy = int(player_manager.get_player_max_energy(player_data))
    p_mp = int(player_data.get('current_mp', 0))
    p_max_mp = int(total_stats.get('max_mana', 0))

    # --- ECONOMIA (NOVO) ---
    p_gold = player_manager.get_gold(player_data)
    p_gems = player_manager.get_gems(player_data)

    leaderboard_text = leaderboard.get_top_score_text()
    
    # --- RODAPÉ ATUALIZADO ---
    status_footer = (
        f"\n\n═════════════ ◆◈◆ ══════════════\n"
        f"💰 𝐎𝐮𝐫𝐨: {p_gold:,}   💎 𝐆𝐞𝐦𝐚𝐬: {p_gems:,}\n"
        f"❤️ 𝐇𝐏: {p_hp}/{p_max_hp}   💙 𝐌𝐚𝐧𝐚: {p_mp}/{p_max_mp}\n"
        f"⚡️ 𝐄𝐧𝐞𝐫𝐠𝐢𝐚: {p_energy}/{max_energy}"
    )

    caption = (
        f"🏰 <b>REINO DE ELDORA</b>\n"
        f"Bem-vindo(a), {character_name}! As muralhas da cidade oferecem segurança e oportunidades.\n"
        f"O que você gostaria de fazer hoje?"
        + status_footer
    )
    
    if leaderboard_text:
        caption += f"\n\n🏆 <b>Destaque:</b> {leaderboard_text}"

    keyboard = [
        [InlineKeyboardButton("🗺 𝐕𝐢𝐚𝐣𝐚𝐫 🗺", callback_data='travel')],
        [InlineKeyboardButton("🏰 𝐆𝐮𝐢𝐥𝐝𝐚 𝐝𝐞 𝐀𝐯𝐞𝐧𝐭𝐮𝐫𝐞𝐢𝐫𝐨𝐬 🏰", callback_data='adventurer_guild_main')],
        [
            InlineKeyboardButton("🏪 𝐌𝐞𝐫𝐜𝐚𝐝𝐨 🏪", callback_data='market'),
            InlineKeyboardButton("⚒️ 𝐅𝐨𝐫𝐣𝐚 ⚒️", callback_data='forge:main'),
        ],
        [InlineKeyboardButton("🧪 𝐑𝐞𝐟𝐢𝐧𝐨 🧪", callback_data='refining_main')],
        [InlineKeyboardButton("🆅🆂 𝐀𝐫𝐞𝐧𝐚 𝐝𝐞 𝐄𝐥𝐝𝐨𝐫𝐚 🆅🆂", callback_data='pvp_arena')], 
        [InlineKeyboardButton("💀 𝐄𝐯𝐞𝐧𝐭𝐨𝐬 𝐄𝐬𝐩𝐞𝐜𝐢𝐚𝐢𝐬 💀", callback_data='evt_hub_principal')],
        [InlineKeyboardButton("👤 𝐏𝐞𝐫𝐬𝐨𝐧𝐚𝐠𝐞𝐦 👤", callback_data='profile')],
        [InlineKeyboardButton("ℹ️ 𝐒𝐨𝐛𝐫𝐞 𝐨 𝐑𝐞𝐢𝐧𝐨", callback_data='region_info:reino_eldora')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Lógica de Envio Inteligente (Mídia ou Edição)
    fd = file_ids.get_file_data('regiao_reino_eldora')
    media_id = fd.get("id") if fd else None
    media_type = (fd.get("type") or "photo").lower() if fd else "photo"

    if query and query.message:
        try:
            if media_id:
                media = InputMediaVideo(media_id, caption=caption, parse_mode='HTML') if media_type == "video" else InputMediaPhoto(media_id, caption=caption, parse_mode='HTML')
                await query.edit_message_media(media=media, reply_markup=reply_markup)
            else:
                await query.edit_message_text(text=caption, reply_markup=reply_markup, parse_mode='HTML')
            return
        except Exception:
            try: await query.delete_message()
            except: pass

    # Envio Limpo (Nova Mensagem)
    if media_id:
        try:
            if media_type == "video":
                await context.bot.send_video(chat_id=chat_id, video=media_id, caption=caption, reply_markup=reply_markup, parse_mode='HTML')
            else:
                await context.bot.send_photo(chat_id=chat_id, photo=media_id, caption=caption, reply_markup=reply_markup, parse_mode='HTML')
            return
        except Exception as e:
            logger.debug("Falha ao enviar mídia do reino: %s", e)

    await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode='HTML')