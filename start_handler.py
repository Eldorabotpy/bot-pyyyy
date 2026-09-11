import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes, CommandHandler

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    # ⚠️ ATENÇÃO: Atualize este link com o seu Cloudflare atual! (precisa ter https://)
    url_do_jogo = "https://163-176-44-198.sslip.io"

    keyboard = [[
        InlineKeyboardButton(
            "🎮 ENTRAR EM ELDORA 🎮", 
            web_app=WebAppInfo(url=url_do_jogo)
        )
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg_text = (
        "⚔️ <b>Bem-vindo ao Mundo de Eldora!</b>\n\n"
        "Os portões do reino estão abertos. Todo o seu progresso, login e aventuras acontecem diretamente no mapa.\n\n"
        "👇 <b>Clique no botão abaixo para iniciar:</b>"
    )

    video_url = "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/loguin/start.mp4"

    mensagem = await update.message.reply_video(
        video=video_url,
        caption=msg_text,
        reply_markup=reply_markup,
        parse_mode="HTML",
        supports_streaming=True
    )

    if mensagem.video:
        file_id = mensagem.video.file_id

        logger.info(
            f"🎬 FILE_ID START ELDORA: {file_id}"
        )

# Handler para registrar no seu main.py
start_command_handler = CommandHandler(['start', 'menu'], start_command)