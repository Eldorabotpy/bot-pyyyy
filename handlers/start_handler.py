# handlers/start_handler.py (VERSÃO DE DIAGNÓSTICO COMPLETA)

import logging
import re
import html
import traceback # <--- IMPORTAÇÃO ADICIONADA
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from handlers.menu.kingdom import show_kingdom_menu
from handlers.menu.region import show_region_menu
from modules import player_manager

try:
    from modules import file_ids
except Exception:
    file_ids = None

logger = logging.getLogger(__name__)
VIDEO_ABERTURA_ID_FALLBACK = "BAACAgEAAxkBAAM5aNrRNqEQEYGUN8-fmcmCdOJOa0EAAsYIAAKCq9lGZ0eFyPq7_lw2BA"
INVISIBLE_CHARS = r"[\u200B-\u200D\uFEFF]"


def _sanitize_name(raw: str) -> str:
    name = re.sub(INVISIBLE_CHARS, "", raw or "")
    name = re.sub(r"[\r\n\t]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def _is_valid_name(name: str) -> tuple[bool, str | None]:
    if not name: return False, "O nome não pode estar vazio."
    if len(name) < 1 or len(name) > 24: return False, "O nome deve ter entre 1 e 24 caracteres."
    return True, None

def _get_video_abertura_id() -> str | None:
    if file_ids:
        fd = file_ids.get_file_data("video_abertura")
        if fd and fd.get("id"):
            return fd["id"]
    return VIDEO_ABERTURA_ID_FALLBACK

# --- Função /start com a "Caixa Preta" ---
# Em handlers/start_handler.py

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    uid = update.effective_user.id
    chat_id = update.effective_chat.id
    logger.info("[START] /start uid=%s", uid)

    player_data = await player_manager.get_player_data(uid) 

    # JÁ TEM CONTA (Verifica se tem nome para garantir que não é conta fantasma)
    if player_data and player_data.get("character_name"):
        try:
            await player_manager.set_last_chat_id(uid, chat_id) 
        except Exception as e:
            logger.debug("set_last_chat_id falhou: %s", e)

        try:
            await update.message.reply_text("🎒 Retomando sua aventura… abrindo o menu.")
        except Exception:
            pass

        try:
            await resume_game_state(update, context, player_data=player_data) 
        except Exception as e:
            logger.error("resume_game_state falhou: %s", e, exc_info=True)
            await update.message.reply_text(
                "⚠️ Não consegui abrir o menu agora. Tenta /menu."
            )
        return

    # NÃO TEM CONTA (ou dados corrompidos sem nome) -> fluxo de criação
    if not context.user_data.get("intro_sent"):
        vid = _get_video_abertura_id()
        if vid:
            try:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=vid,
                    caption="🌟 Bem-vindo(a) ao <b>🏰𝙼𝚞𝚗𝚍𝚘 𝚍𝚎 𝙴𝚕𝚍𝚘𝚛𝚊🏰</b>! 🌟",
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning("Falha ao enviar vídeo de abertura: %s", e)
        context.user_data["intro_sent"] = True

    # Ativa o estado de espera de nome
    context.user_data["awaiting_name"] = True
    texto = (
        f"Olá, <b>{html.escape(update.effective_user.first_name)}</b>!\n\n"
        "📜 <b>Envie o nome do seu personagem</b> (1–24 chars).\n"
        "Se preferir: /nome <b>SEU_NOME</b>."
    )
    await update.message.reply_text(texto, parse_mode="HTML")

async def _finalize_creation_with_name(update: Update, context: ContextTypes.DEFAULT_TYPE, raw_name: str):
    # (Sua função original completa aqui)
    uid = update.effective_user.id
    chat_id = update.effective_chat.id
    name = _sanitize_name(raw_name)
    logger.info("[CREATE] uid=%s nome='%s'", uid, name)
    ok, err = _is_valid_name(name)
    if not ok:
        await update.message.reply_text(f"{err}\n\nTenta outro nome 🙂")
        return
    try:
        existing = await player_manager.find_player_by_name(name)
    except Exception:
        existing = None
    if existing:
        await update.message.reply_text("Este nome já é de outro aventureiro. Escolha outro 🙂")
        return
    try:
        await player_manager.create_new_player(uid, name)
        await player_manager.set_last_chat_id(uid, chat_id)
    except Exception as e:
        logger.error("Falha ao criar personagem: %s", e, exc_info=True)
        await update.message.reply_text("⚠️ Erro ao criar o personagem. Tenta /start novamente.")
        context.user_data.pop("awaiting_name", None)
        return
    await update.message.reply_text(f"Perfeito! Seu personagem <b>{html.escape(name)}</b> foi criado!", parse_mode="HTML")
    context.user_data.pop("awaiting_name", None)
    await resume_game_state(update, context)

async def handle_character_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    if not (update.message and isinstance(update.message.text, str)): return
    if not context.user_data.get("awaiting_name"): return
    await _finalize_creation_with_name(update, context, update.message.text)

async def name_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not context.user_data.get("awaiting_name"):
        await update.message.reply_text("Você já tem personagem. Use /menu.")
        return
    args = context.args or []
    if not args:
        await update.message.reply_text("Uso: /nome SEU_NOME")
        return
    await _finalize_creation_with_name(update, context, " ".join(args))

async def resume_game_state(update: Update, context: ContextTypes.DEFAULT_TYPE, player_data: dict | None = None):
    """
    Retoma o estado do jogo para um jogador existente e abre o menu de localização.
    Aceita player_data já carregado ou carrega-o.
    """
    uid = update.effective_user.id
    chat_id = update.effective_chat.id # Adicionado para uso em set_last_chat_id

    # <<< CORREÇÃO DE LÓGICA: Carrega os dados APENAS se não foram passados >>>
    if player_data is None:
        player_data = await player_manager.get_player_data(uid)
    
    if not player_data:
        # Se os dados não forem encontrados (erro)
        if update.message:
            await update.message.reply_text("Não encontrei seus dados. Use /start para começar.")
        elif update.callback_query:
            await update.callback_query.edit_message_text("Não encontrei seus dados. Use /start para começar.")
        return

    # Atualiza o último chat ID (usa chat_id definido no início)
    try:
        await player_manager.set_last_chat_id(uid, chat_id)
    except Exception as e:
        logger.debug("set_last_chat_id falhou: %s", e)


    current_location = player_data.get('current_location', 'reino_eldora')
    # CORRIGIDO:

    try:
        if current_location == 'reino_eldora':
            # Chama o menu do reino com os dados JÁ carregados
            await show_kingdom_menu(update, context, player_data=player_data) 
        else:
            # CORREÇÃO: Passa a localização atual do jogador
            await show_region_menu(update, context, region_key=current_location) 
    except Exception as e:
        logger.error("Erro abrindo menu (%s): %s", current_location, e, exc_info=True)
        if update.message:
            await update.message.reply_text("⚠️ Erro ao abrir o menu. Tenta /menu.")
        elif update.callback_query:
            await update.callback_query.edit_message_text("⚠️ Erro ao abrir o menu. Tenta /menu.")
                        
# --- Handlers para registrar ---
start_command_handler = CommandHandler("start", start_command)
name_command_handler = CommandHandler("nome", name_command)
character_creation_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_character_creation)