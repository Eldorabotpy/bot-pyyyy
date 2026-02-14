# ui/ui_renderer.py
from __future__ import annotations

import logging
from typing import Optional

from telegram import InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Guarda por "tela" (scope) o último message_id que a gente enviou, para limpar o chat.
_UI_KEY = "_ui_last_messages"  # dict: {scope: message_id}

def _get_store(context: ContextTypes.DEFAULT_TYPE) -> dict:
    if _UI_KEY not in context.user_data:
        context.user_data[_UI_KEY] = {}
    return context.user_data[_UI_KEY]

async def _safe_delete(chat_id: int, message_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

def _is_wrong_file_id(err: Exception) -> bool:
    """Verifica se o erro é culpa de um ID de arquivo inválido."""
    msg = str(err).lower()
    return ("wrong remote file identifier" in msg) or \
           ("wrong file identifier" in msg) or \
           ("can't unserialize" in msg) or \
           ("file_id" in msg and "invalid" in msg)

async def render_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    scope: str = "main",
    parse_mode: str = ParseMode.MARKDOWN,
    delete_previous_on_send: bool = False,
    allow_edit: bool = True
):
    """Renderiza apenas texto (Fallback seguro)."""
    chat_id = update.effective_chat.id
    store = _get_store(context)
    last_id = store.get(scope)

    # 1. Tenta EDITAR se permitido
    if allow_edit and last_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=last_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            return
        except BadRequest as e:
            # Se não deu para editar (ex: mensagem antiga era foto), ignora e reenvia
            if "message is not modified" in str(e): return

    # 2. Se pediu para apagar a anterior antes de enviar a nova
    if delete_previous_on_send and last_id:
        await _safe_delete(chat_id, last_id, context)

    # 3. Envia nova mensagem
    try:
        sent = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        store[scope] = sent.message_id
    except Exception as e:
        logger.error(f"Erro ao renderizar texto: {e}")

async def render_photo_or_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    file_id: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    scope: str = "main",
    parse_mode: str = ParseMode.MARKDOWN,
    delete_previous_on_send: bool = False,
    allow_edit: bool = True
):
    """
    Renderiza Foto + Texto. 
    🔥 BLINDAGEM: Se a foto falhar, chama render_text automaticamente.
    """
    chat_id = update.effective_chat.id
    store = _get_store(context)
    last_id = store.get(scope)

    # Se não tiver ID, vai direto pro texto
    if not file_id or str(file_id) == "None":
        return await render_text(update, context, text, reply_markup, scope, parse_mode, delete_previous_on_send, allow_edit)

    # 1. Tenta EDITAR (apenas Caption)
    if allow_edit and last_id:
        try:
            await context.bot.edit_message_caption(
                chat_id=chat_id,
                message_id=last_id,
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            return
        except BadRequest as e:
            # Se o erro for de ID inválido no edit, avisa e tenta reenviar
            if _is_wrong_file_id(e):
                logger.warning(f"⚠️ ID inválido no Edit: {file_id}. Tentando reenvio limpo.")
            elif "message is not modified" in str(e):
                return
            # Se não conseguiu editar, continua para o envio normal

    # 2. Apaga anterior se necessário
    if delete_previous_on_send and last_id:
        await _safe_delete(chat_id, last_id, context)

    # 3. Tenta ENVIAR NOVA FOTO
    try:
        sent = await context.bot.send_photo(
            chat_id=chat_id,
            photo=file_id,
            caption=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )
        store[scope] = sent.message_id
        
    except BadRequest as e:
        # 🔥 AQUI ESTÁ A CORREÇÃO:
        if _is_wrong_file_id(e):
            logger.error(f"❌ Erro de Imagem (ID Inválido): {file_id}. Usando Fallback Texto.")
            # Chama o renderizador de texto para o jogo não parar
            await render_text(
                update, context, 
                text=f"⚠️ [Imagem Quebrada]\n\n{text}", 
                reply_markup=reply_markup, 
                scope=scope, 
                parse_mode=parse_mode,
                delete_previous_on_send=False 
            )
        else:
            logger.error(f"Erro desconhecido ao enviar foto: {e}")

async def render_menu(
    update,
    context,
    text: str,
    reply_markup=None,
    *,
    scope: str = "default",
    parse_mode=ParseMode.HTML,
    delete_previous_on_send: bool = True,
    allow_edit: bool = True,
):
    # menu de texto (padrão)
    return await render_text(
        update,
        context,
        text,
        reply_markup=reply_markup,
        scope=scope,
        parse_mode=parse_mode,
        delete_previous_on_send=delete_previous_on_send,
        allow_edit=allow_edit,
    )

async def notify(
    update,
    context,
    text: str,
    *,
    scope: str = "notify",
    parse_mode=ParseMode.HTML,
):
    # notificação curta: não precisa tentar editar sempre; mantém limpo por scope
    return await render_text(
        update,
        context,
        text,
        reply_markup=None,
        scope=scope,
        parse_mode=parse_mode,
        delete_previous_on_send=True,
        allow_edit=False,
    )

# Adicione no ui/ui_renderer.py

async def render_scope_text(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    text: str,
    reply_markup=None,
    *,
    scope: str = "default",
    parse_mode: str = ParseMode.HTML,
) -> bool:
    """
    Edita a mensagem do 'scope' mesmo sem callback_query.
    Retorna True se conseguiu editar, False se não havia msg ou falhou.
    """
    store = _get_store(context)
    msg_id = store.get(scope)
    if not isinstance(msg_id, int):
        return False

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
        return True
    except Exception:
        return False


async def clear_scope(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    *,
    scope: str = "default",
) -> None:
    """Apaga a mensagem registrada no scope e remove do store."""
    store = _get_store(context)
    msg_id = store.get(scope)
    if isinstance(msg_id, int):
        await _safe_delete(chat_id, msg_id, context)
    store.pop(scope, None)

async def send_scope_media_or_text(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    text: str,
    file_id: Optional[str],
    file_type: Optional[str] = "photo",
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    *,
    scope: str = "default",
    parse_mode: str = ParseMode.HTML,
    delete_previous_on_send: bool = True,
) -> int | None:
    """
    Para JOBs (sem Update): envia photo/video + caption (ou texto) e registra message_id no scope.
    """
    store = _get_store(context)

    if delete_previous_on_send:
        last_id = store.get(scope)
        if isinstance(last_id, int):
            await _safe_delete(chat_id, last_id, context)

    if not file_id:
        sent = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
        store[scope] = sent.message_id
        return sent.message_id

    ftype = (file_type or "photo").lower().strip()
    try:
        if ftype == "video":
            sent = await context.bot.send_video(
                chat_id=chat_id,
                video=file_id,
                caption=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
            )
        else:
            sent = await context.bot.send_photo(
                chat_id=chat_id,
                photo=file_id,
                caption=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
            )
        store[scope] = sent.message_id
        return sent.message_id

    except BadRequest as e:
        if _is_wrong_file_id(e):
            sent = await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
            )
            store[scope] = sent.message_id
            return sent.message_id
        raise


async def render_media_or_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    media_key: str, # Pode ser chave do gerenciador ou ID direto
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    scope: str = "main",
    parse_mode: str = ParseMode.MARKDOWN,
    delete_previous_on_send: bool = False,
    allow_edit: bool = True,
    file_type: str = "photo"
):
    """Resolve a chave de mídia e chama a função apropriada."""
    
    final_file_id = media_key
    
    # Tenta resolver o ID via file_id_manager (se existir no projeto)
    try:
        from modules import file_id_manager
        file_data = file_id_manager.get_file_data(media_key)
        if file_data and "id" in file_data:
            final_file_id = file_data["id"]
            if "type" in file_data: file_type = file_data["type"]
    except ImportError:
        pass 
    except Exception:
        pass

    ftype = (file_type or "photo").lower().strip()

    if ftype == "video":
        # Lógica simplificada para vídeo (costuma dar erro em edit, então enviamos novo)
        if delete_previous_on_send:
            last = _get_store(context).get(scope)
            if last: await _safe_delete(update.effective_chat.id, last, context)
        
        try:
            sent = await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=final_file_id,
                caption=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
            _get_store(context)[scope] = sent.message_id
        except Exception:
            # Fallback vídeo
            await render_text(update, context, f"⚠️ [Vídeo Indisponível]\n\n{text}", reply_markup, scope)
    else:
        # Foto (ou padrão)
        await render_photo_or_text(
            update, context, text, final_file_id, reply_markup,
            scope=scope, parse_mode=parse_mode,
            delete_previous_on_send=delete_previous_on_send,
            allow_edit=allow_edit
        )