from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_ID
from modules import file_ids

async def admin_auto_capture_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user:
        return
    if str(update.effective_user.id) != str(ADMIN_ID):
        return

    msg = update.message
    if not msg or not msg.photo:
        return

    caption = (msg.caption or "").strip().lower()
    if not caption.startswith("#"):
        return

    # chave vem da hashtag
    key = caption.replace("#", "").strip()
    if not key:
        return

    # pega a melhor resolução
    file_id = msg.photo[-1].file_id

    file_ids.save_file_id(key, file_id, "photo")

    await msg.reply_text(
        f"✅ Mídia atualizada com sucesso.\n"
        f"🔑 Chave: <code>{key}</code>",
        parse_mode="HTML"
    )
