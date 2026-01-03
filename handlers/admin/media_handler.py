# No topo do ficheiro de admin
from config import ADMIN_ID  #
from telegram import Update
from telegram.ext import ContextTypes
from modules import file_ids as file_id_manager

async def set_media_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Guarda o ID de uma foto/vídeo no banco de dados.
    Uso: /setmedia nome_da_chave (em resposta a uma média)
    """
    # Comparação segura de IDs
    if str(update.effective_user.id) != str(ADMIN_ID):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Responda a uma Foto ou Vídeo com: `/setmedia nome_da_chave`")
        return

    if not context.args:
        await update.message.reply_text("❌ Informe o nome da chave. Ex: `autohunt_start_media`")
        return

    key = context.args[0].lower().strip()
    reply = update.message.reply_to_message
    
    file_id = None
    media_type = "photo"

    # Detecção automática do tipo de ficheiro
    if reply.video:
        file_id = reply.video.file_id
        media_type = "video"
    elif reply.photo:
        file_id = reply.photo[-1].file_id # Pega a maior qualidade
        media_type = "photo"
    elif reply.animation:
        file_id = reply.animation.file_id
        media_type = "video" # GIFs são tratados como vídeo pelo Telegram

    if file_id:
        # Salva no MongoDB através do gestor central
        file_id_manager.set_file_data(key, file_id, media_type)
        await update.message.reply_text(f"✅ Mídia cadastrada!\n🔑 Chave: `{key}`\n📁 Tipo: {media_type.upper()}")
    else:
        await update.message.reply_text("❌ Nenhuma média válida detetada na mensagem respondida.")