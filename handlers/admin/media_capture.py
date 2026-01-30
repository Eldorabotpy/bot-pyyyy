# handlers/admin/media_capture.py
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_ID
from modules import file_ids


def _is_admin(update: Update) -> bool:
    uid = update.effective_user.id if update.effective_user else None
    return str(uid) == str(ADMIN_ID)


def _extract_key(caption: str) -> str | None:
    """
    Aceita:
      "#startup"
      "#startup alguma coisa"
      "#welcome"
    Retorna a chave sem '#', em lowercase.
    """
    if not caption:
        return None
    c = caption.strip()
    if not c.startswith("#"):
        return None
    first = c.split()[0]  # só a primeira "palavra"
    key = first.lstrip("#").strip().lower()
    return key or None


async def admin_auto_capture_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Envie uma mídia com legenda começando com #chave no chat com o bot (ou no grupo admin).
    Exemplos:
      Foto + legenda:  "#startup"
      Vídeo + legenda: "#welcome"
      Documento (imagem) + legenda: "#event_natal"

    O bot salva o file_id no Mongo via modules/file_ids.py e já atualiza cache.
    """
    if not _is_admin(update):
        return

    msg = update.message
    if not msg:
        return

    key = _extract_key(msg.caption or "")
    if not key:
        return

    file_id = None
    file_type = None

    # Prioridade: photo > video > animation > document (image)
    if msg.photo:
        file_id = msg.photo[-1].file_id
        file_type = "photo"
    elif msg.video:
        file_id = msg.video.file_id
        file_type = "video"
    elif msg.animation:
        file_id = msg.animation.file_id
        file_type = "animation"
    elif msg.document:
        # útil quando você manda "arquivo" (jpg/png)
        file_id = msg.document.file_id
        file_type = "document"

    if not file_id:
        await msg.reply_text("❌ Envie uma FOTO/VÍDEO/ANIMAÇÃO/ARQUIVO com legenda #chave.")
        return

    # Salva e atualiza cache (seu file_ids.py já faz isso)
    try:
        file_ids.save_file_id(key, file_id, file_type)
    except Exception as e:
        await msg.reply_text(f"❌ Falha ao salvar mídia: {e}")
        return

    await msg.reply_text(
        "✅ Mídia atualizada automaticamente!\n"
        f"🔑 Chave: <code>{key}</code>\n"
        f"🧩 Tipo: <code>{file_type}</code>",
        parse_mode="HTML",
    )
