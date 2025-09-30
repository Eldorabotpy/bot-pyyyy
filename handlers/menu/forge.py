# handlers/menu/forge.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except Exception:
        pass
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except Exception:
        pass
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

async def show_forge_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = getattr(update, "callback_query", None)

    # Botões compatíveis com os handlers registrados no main.py
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔨 𝐅𝐨𝐫𝐣𝐚𝐫 𝐢𝐭𝐞𝐦", callback_data="forge:main")],
        [InlineKeyboardButton("🧪 𝐑𝐞𝐟𝐢𝐧𝐨", callback_data="refining_main")],  # <- compatível
        [InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="show_kingdom_menu")],  # <- mantém padrão global
    ])
    text = "⚒️ 𝐅𝐨𝐫𝐣𝐚 𝐝𝐞 𝐄𝐥𝐝𝐨𝐫𝐚\n𝑬𝒔𝒄𝒐𝒍𝒉𝒂 𝒖𝒎𝒂 𝒐𝒑𝒄̧𝒂̃𝒐:"

    if q:
        await q.answer()
        chat_id = q.message.chat_id
        await _safe_edit_or_send(q, context, chat_id, text, kb)
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
