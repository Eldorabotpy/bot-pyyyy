# handlers/admin/file_id_conv.py
from __future__ import annotations

import html
import logging
from typing import Tuple, Optional
from telegram.error import BadRequest
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# Persistência
from modules import file_ids as file_id_manager

logger = logging.getLogger(__name__)

# =========================
# Estados
# =========================
STATE_GET_FILE, STATE_GET_NAME_FOR_SAVE, STATE_CONFIRM_OVERWRITE = range(3)

# =========================
# Utils
# =========================
def _kb(rows):
    return InlineKeyboardMarkup(rows)

def _human_file_kind(kind_key: str) -> str:
    return "FOTO" if kind_key == "get_photo" else "VÍDEO"

def _extract_file_id_and_type_from_message(msg) -> Tuple[Optional[str], Optional[str]]:
    """Retorna (file_id, file_type) onde file_type ∈ {'photo','video'}."""
    if getattr(msg, "photo", None):
        return msg.photo[-1].file_id, "photo"
    if getattr(msg, "video", None):
        return msg.video.file_id, "video"
    if getattr(msg, "video_note", None):
        return msg.video_note.file_id, "video"
    if getattr(msg, "document", None):
        mime = (msg.document.mime_type or "").lower()
        fid = msg.document.file_id
        if mime.startswith("image/"):
            return fid, "photo"
        if mime.startswith("video/"):
            return fid, "video"
    return None, None

def _store_path_str() -> str:
    try:
        p = file_id_manager.get_store_path()
        return str(p)
    except Exception:
        return "(desconhecido)"

# =========================
# Entradas auxiliares por comando (para teste direto)
# =========================
async def cmd_save_media_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["file_type_to_get"] = "get_photo"
    msg = (
        "🧪 <b>Modo teste (foto)</b>\n"
        "Envie agora a <b>FOTO</b> (pode ser imagem direta ou documento imagem).\n"
        "Use /cancelar para sair."
    )
    await update.message.reply_text(msg, parse_mode="HTML")
    logger.info("[FILEIDS] Entrada por comando: get_photo")
    return STATE_GET_FILE

async def cmd_save_media_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["file_type_to_get"] = "get_video"
    msg = (
        "🧪 <b>Modo teste (vídeo)</b>\n"
        "Envie agora o <b>VÍDEO</b> (pode ser vídeo, video note, ou documento vídeo).\n"
        "Use /cancelar para sair."
    )
    await update.message.reply_text(msg, parse_mode="HTML")
    logger.info("[FILEIDS] Entrada por comando: get_video")
    return STATE_GET_FILE

# =========================
# Passo 0: abrir menu (via callback)
# =========================
async def open_file_id_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    text = (
        "📁 <b>Gerenciador de File IDs</b>\n"
        "Escolha que tipo deseja salvar:"
    )
    kb = _kb([
        [InlineKeyboardButton("📷 Salvar FOTO",  callback_data="get_photo")],
        [InlineKeyboardButton("🎞️ Salvar VÍDEO", callback_data="get_video")],
        [InlineKeyboardButton("⬅️ Voltar",       callback_data="admin_main")],
    ])
    try:
        await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await q.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
    return STATE_GET_FILE

# =========================
# Passo 1: escolher tipo (via callback)
# =========================
async def ask_for_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()

    kind = q.data  # 'get_photo' ou 'get_video'
    context.user_data["file_type_to_get"] = kind
    logger.info("[FILEIDS] Tipo solicitado: %s", kind)

    # --- INICIO DA CORREÇÃO ---
    try:
        await q.edit_message_text(
            text=(
                f"Ok! Envie agora o arquivo de <b>{_human_file_kind(kind)}</b>.\n\n"
                "• Pode ser foto/vídeo direto, video note, ou documento (imagem/vídeo).\n"
                "• Use /cancelar para sair."
            ),
            parse_mode="HTML",
        )
    except BadRequest as e:
        # Se o erro for "não modificado", a gente ignora (pass)
        if "not modified" in str(e):
            pass 
        else:
            # Se for outro erro (ex: texto muito longo), a gente avisa no log e relança
            logger.error(f"Erro ao editar mensagem: {e}")
            raise e
    # --- FIM DA CORREÇÃO ---

    return STATE_GET_FILE

# =========================
# Passo 2: receber arquivo
# =========================
async def get_id_and_ask_for_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    file_id, file_type_for_save = _extract_file_id_and_type_from_message(update.message)
    logger.info("[FILEIDS] get_id_and_ask_for_name -> fid=%r type=%r", file_id, file_type_for_save)

    if not file_id:
        await update.message.reply_text("❌ Não reconheci esse arquivo. Envie uma FOTO ou um VÍDEO.")
        return STATE_GET_FILE

    expected = context.user_data.get("file_type_to_get")
    if expected == "get_photo" and file_type_for_save != "photo":
        await update.message.reply_text("❌ Eu pedi uma FOTO. Envie uma foto, por favor.")
        return STATE_GET_FILE
    if expected == "get_video" and file_type_for_save != "video":
        await update.message.reply_text("❌ Eu pedi um VÍDEO. Envie um vídeo, por favor.")
        return STATE_GET_FILE

    context.user_data["last_file_id"] = file_id
    context.user_data["last_file_type"] = file_type_for_save

    safe_file_id = html.escape(file_id)
    where = _store_path_str()
    text = (
        "✅ Arquivo recebido com sucesso!\n\n"
        "<b>ID do Arquivo:</b>\n"
        f"<code>{safe_file_id}</code>\n\n"
        "Agora, envie um <b>nome</b> para salvar este ID (qualquer texto).\n"
        "Você também pode enviar como comando: <code>/nome meu_identificador</code>\n\n"
        f"<i>Arquivo de dados:</i> <code>{html.escape(where)}</code>\n"
        "Use /cancelar para sair."
    )
    await update.message.reply_text(text, parse_mode="HTML")
    logger.info("[FILEIDS] Aguardando nome… (store=%s)", where)
    return STATE_GET_NAME_FOR_SAVE

# =========================
# Passo 3: salvar (sem regex restritiva)
# =========================
_NAME_MAXLEN = 64

def _extract_candidate(raw: str) -> str:
    raw = (raw or "").strip()
    if raw.startswith("/nome"):
        parts = raw.split(maxsplit=1)
        raw = parts[1].strip() if len(parts) > 1 else ""
    return raw[:_NAME_MAXLEN]

async def save_named_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Em alguns casos raros, update.message pode ser None (evitar crash)
    if not update.message:
        logger.warning("[FILEIDS] save_named_id sem update.message")
        return STATE_GET_NAME_FOR_SAVE

    raw = (update.message.text or "")
    candidate = _extract_candidate(raw)
    logger.info("[FILEIDS] save_named_id recebeu: %r | user_data=%r", raw, context.user_data)

    if not candidate:
        await update.message.reply_text(
            "❌ O nome não pode ser vazio. Envie um texto (ou use <code>/nome meu_identificador</code>).",
            parse_mode="HTML",
        )
        return STATE_GET_NAME_FOR_SAVE

    name_to_save = candidate
    file_id = context.user_data.get("last_file_id")
    file_type = context.user_data.get("last_file_type")

    if not file_id or not file_type:
        await update.message.reply_text("❌ Dados ausentes. Reabra em /admin → Gerenciar File IDs.")
        logger.warning("[FILEIDS] Abortei: sem file_id/file_type em user_data | user_data=%r", context.user_data)
        return ConversationHandler.END

    existing = file_id_manager.get_file_data(name_to_save)
    logger.info("[FILEIDS] existing=%r para nome=%s", existing, name_to_save)
    if existing and existing.get("id"):
        context.user_data["pending_name"] = name_to_save
        await update.message.reply_text(
            f"⚠️ Já existe um ID salvo com o nome <b>{html.escape(name_to_save)}</b>.\n"
            "Responda <b>SIM</b> para sobrescrever ou <b>NAO</b> para escolher outro nome.",
            parse_mode="HTML",
        )
        return STATE_CONFIRM_OVERWRITE

    try:
        file_id_manager.save_file_id(name_to_save, file_id, file_type)
        file_id_manager.refresh_cache()
        logger.info("[FILEIDS] SALVO: %s -> (%s) %s", name_to_save, file_type, file_id)
    except Exception as e:
        logger.exception("[FILEIDS] Erro ao salvar %s: %s", name_to_save, e)
        await update.message.reply_text(f"❌ Erro ao salvar: {e}")
        return STATE_GET_NAME_FOR_SAVE

    path_txt = _store_path_str()
    await update.message.reply_text(
        "✅ ID salvo com sucesso como: "
        f"<code>{html.escape(name_to_save)}</code>\n"
        f"<i>Arquivo:</i> <code>{html.escape(path_txt)}</code>",
        parse_mode="HTML",
    )

    for k in ("file_type_to_get", "last_file_id", "last_file_type", "pending_name"):
        context.user_data.pop(k, None)
    return ConversationHandler.END

async def confirm_overwrite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    answer = (update.message.text or "").strip().lower()
    file_id = context.user_data.get("last_file_id")
    file_type = context.user_data.get("last_file_type")
    name_to_save = context.user_data.get("pending_name")

    if answer not in ("sim", "nao", "não"):
        await update.message.reply_text("Responda 'SIM' para sobrescrever ou 'NAO' para escolher outro nome.")
        return STATE_CONFIRM_OVERWRITE

    if answer == "sim":
        if not (file_id and file_type and name_to_save):
            await update.message.reply_text("❌ Dados ausentes. Operação cancelada.")
            return ConversationHandler.END
        try:
            file_id_manager.save_file_id(name_to_save, file_id, file_type)
            file_id_manager.refresh_cache()
            logger.info("[FILEIDS] OVERWRITE: %s -> (%s) %s", name_to_save, file_type, file_id)
        except Exception as e:
            logger.exception("[FILEIDS] Erro overwrite %s: %s", name_to_save, e)
            await update.message.reply_text(f"❌ Erro ao salvar: {e}")
            return STATE_CONFIRM_OVERWRITE

        path_txt = _store_path_str()
        await update.message.reply_text(
            "✅ Sobrescrito com sucesso para o nome: "
            f"<code>{html.escape(name_to_save)}</code>\n"
            f"<i>Arquivo:</i> <code>{html.escape(path_txt)}</code>",
            parse_mode="HTML",
        )
        for k in ("file_type_to_get", "last_file_id", "last_file_type", "pending_name"):
            context.user_data.pop(k, None)
        return ConversationHandler.END

    await update.message.reply_text("Ok. Envie outro nome (ou /cancelar).")
    return STATE_GET_NAME_FOR_SAVE

# =========================
# Sair / Cancelar
# =========================
async def exit_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    if q:
        try:
            await q.answer()
        except Exception:
            pass
        try:
            await q.edit_message_text("Saindo do Gerenciador de File IDs…")
        except Exception:
            try:
                await q.message.reply_text("Saindo do Gerenciador de File IDs…")
            except Exception:
                pass
    for k in ("file_type_to_get", "last_file_id", "last_file_type", "pending_name"):
        context.user_data.pop(k, None)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        await update.message.reply_text("Operação cancelada.")
    except Exception:
        if update.callback_query:
            await update.callback_query.message.reply_text("Operação cancelada.")
    for k in ("file_type_to_get", "last_file_id", "last_file_type", "pending_name"):
        context.user_data.pop(k, None)
    return ConversationHandler.END

# =========================
# ConversationHandler
# =========================
file_id_conv_handler = ConversationHandler(
    entry_points=[
        # Painel admin
        CallbackQueryHandler(open_file_id_menu, pattern=r'^admin_file_ids$'),
        CallbackQueryHandler(ask_for_file, pattern=r'^get_(photo|video)$'),
        # Entradas diretas por comando (TESTE rápido)
        CommandHandler("save_media_photo", cmd_save_media_photo),
        CommandHandler("save_media_video", cmd_save_media_video),
    ],
    states={
        STATE_GET_FILE: [
            CallbackQueryHandler(ask_for_file, pattern=r'^get_(photo|video)$'),
            CallbackQueryHandler(exit_to_admin, pattern=r'^admin_main$'),
            MessageHandler(
                filters.PHOTO
                | filters.VIDEO
                | filters.Document.IMAGE
                | filters.Document.VIDEO
                | filters.VIDEO_NOTE,
                get_id_and_ask_for_name,
            ),
        ],
        # Pega praticamente tudo (evita perder a mensagem de nome)
        STATE_GET_NAME_FOR_SAVE: [
            CallbackQueryHandler(exit_to_admin, pattern=r'^admin_main$'),
            MessageHandler(filters.ALL & ~filters.StatusUpdate.ALL, save_named_id),
            CommandHandler("nome", save_named_id),  # redundante, mas mantemos
        ],
        STATE_CONFIRM_OVERWRITE: [
            CallbackQueryHandler(exit_to_admin, pattern=r'^admin_main$'),
            MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_overwrite),
        ],
    },
    fallbacks=[CommandHandler('cancelar', cancel)],
    per_user=True,
    per_chat=True,
    name="file_id_conv",
    persistent=False,
    block=True,   # bloqueia outros handlers durante a conversa
)
