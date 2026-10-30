import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes, CommandHandler

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    # ⚠️ ATENÇÃO: Atualize este link com o seu Cloudflare atual! (precisa ter https://)
    url_do_jogo = "https://eldora-rpg.modappmania.workers.dev"

    payload = context.args[0] if context.args else ""
    handoff_match = re.fullmatch(r"eldora_([A-Za-z0-9_-]{43})", payload)
    if handoff_match:
        from modules.portal_auth import claim_telegram_google_handoff
        telegram_user = update.effective_user
        claimed = (
            update.effective_chat
            and update.effective_chat.type == "private"
            and telegram_user
            and claim_telegram_google_handoff(handoff_match.group(1), telegram_user.id)
        )
        if not claimed:
            await update.message.reply_text(
                "Este acesso expirou ou já foi confirmado por outra conta. Volte ao jogo e repita a entrada com Google."
            )
            return
        handoff_url = f"{url_do_jogo}/login?google_handoff_token={handoff_match.group(1)}"
        keyboard = [[InlineKeyboardButton(
            "🎮 VOLTAR AO JOGO",
            web_app=WebAppInfo(url=handoff_url),
        )]]
        await update.message.reply_text(
            "✅ Google confirmado. Toque abaixo para entrar no Eldora com sua conta.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    keyboard = [
        [
            InlineKeyboardButton(
                "🎮 ENTRAR EM ELDORA 🎮",
                web_app=WebAppInfo(url=url_do_jogo)
            )
        ],
        [
            InlineKeyboardButton(
                "🌐 JOGAR NA WEB",
                url="https://eldora-rpg.modappmania.workers.dev"
            ),
            InlineKeyboardButton(
                "👥 COMUNIDADE",
                url="https://t.me/+rA1Xiom4I_E5MmY5"
            )
        ]
    ]

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
