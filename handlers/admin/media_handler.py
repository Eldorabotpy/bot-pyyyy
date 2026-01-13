# handlers/admin/media_handler.py
from telegram import Update
from telegram.ext import ContextTypes

from modules import file_ids as file_id_manager
from modules.auth_utils import get_current_player_id_async
from modules import player_manager
from config import ADMIN_ID  # agora deve ser ObjectId (string)

async def set_media_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Guarda o ID de uma foto/vídeo no banco de dados.
    Uso: /setmedia nome_da_chave (em resposta a uma mídia)
    """

    # 🔐 Recupera jogador logado (ObjectId)
    player_id = await get_current_player_id_async(update, context)
    if not player_id:
        return

    # 🔐 Validação de admin (ObjectId)
    if str(player_id) != str(ADMIN_ID):
        return

    if not update.message or not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Responda a uma Foto ou Vídeo com:\n`/setmedia nome_da_chave`",
            parse_mode="Markdown"
        )
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Informe o nome da chave.\nEx: `autohunt_start_media`",
            parse_mode="Markdown"
        )
        return

    key = context.args[0].lower().strip()
    reply = update.message.reply_to_message

    file_id = None
    media_type = "photo"

    # Detecção automática do tipo de mídia
    if reply.video:
        file_id = reply.video.file_id
        media_type = "video"
    elif reply.photo:
        file_id = reply.photo[-1].file_id  # maior qualidade
        media_type = "photo"
    elif reply.animation:
        file_id = reply.animation.file_id
        media_type = "video"

    if not file_id:
        await update.message.reply_text("❌ Nenhuma mídia válida detectada.")
        return

    # Salva via gestor central
    file_id_manager.set_file_data(key, file_id, media_type)

    await update.message.reply_text(
        f"✅ **Mídia cadastrada com sucesso!**\n\n"
        f"🔑 Chave: `{key}`\n"
        f"📁 Tipo: `{media_type.upper()}`",
        parse_mode="Markdown"
    )
