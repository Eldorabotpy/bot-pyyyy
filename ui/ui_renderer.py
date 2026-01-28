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
    store = context.user_data.get(_UI_KEY)
    if not isinstance(store, dict):
        store = {}
        context.user_data[_UI_KEY] = store
    return store

async def _safe_delete(chat_id: int, message_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

def _is_wrong_file_id(err: Exception) -> bool:
    msg = str(err).lower()
    return ("wrong file identifier" in msg) or ("wrong file_id" in msg) or ("http url specified" in msg)

async def render_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    *,
    scope: str = "default",
    parse_mode: str = ParseMode.HTML,
    delete_previous_on_send: bool = True,
    allow_edit: bool = True,
) -> None:
    """
    Renderiza uma "tela" de texto:
    - Se veio de callback_query: tenta editar a mensagem atual.
    - Se não der para editar: envia uma nova e (opcional) apaga a anterior daquele scope.
    - Se veio de comando/mensagem normal: apaga a anterior (scope) e envia nova.
    """
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None:
        return

    store = _get_store(context)

    # 1) Tentativa de EDIT (mantém o fluxo limpo sem novas mensagens)
    if allow_edit and update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
            # não atualiza store aqui porque a msg já é a mesma
            return
        except Exception:
            # Cai para send abaixo
            pass

    # 2) SEND (com limpeza do anterior por scope)
    if delete_previous_on_send:
        last_id = store.get(scope)
        if isinstance(last_id, int):
            await _safe_delete(chat_id, last_id, context)

    sent = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=parse_mode,
        reply_markup=reply_markup
    )
    store[scope] = sent.message_id

async def render_photo_or_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    photo_file_id: Optional[str],
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    *,
    scope: str = "default",
    parse_mode: str = ParseMode.HTML,
    delete_previous_on_send: bool = True,
    allow_edit: bool = True,
) -> None:
    """
    Renderiza uma "tela" com FOTO + legenda, mas se não houver mídia ou der erro (BadRequest 400),
    envia só texto.
    """
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None:
        return

    store = _get_store(context)

    # Se não tem mídia: só texto.
    if not photo_file_id:
        await render_text(
            update, context, text, reply_markup,
            scope=scope, parse_mode=parse_mode,
            delete_previous_on_send=delete_previous_on_send,
            allow_edit=allow_edit
        )
        return

    # 1) Tenta EDIT caption se veio de callback
    if allow_edit and update.callback_query:
        try:
            # Se a mensagem atual já é foto, edita caption
            await update.callback_query.edit_message_caption(
                caption=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
            return
        except BadRequest as e:
            # Se a msg atual não tem caption (era texto), ou o file_id está ruim, cai para send
            if _is_wrong_file_id(e):
                logger.warning("[UI] file_id inválido, fallback para texto: %s", e)
                await render_text(
                    update, context, text, reply_markup,
                    scope=scope, parse_mode=parse_mode,
                    delete_previous_on_send=delete_previous_on_send,
                    allow_edit=False
                )
                return
        except Exception:
            pass

    # 2) SEND foto (apaga anterior do scope)
    if delete_previous_on_send:
        last_id = store.get(scope)
        if isinstance(last_id, int):
            await _safe_delete(chat_id, last_id, context)

    try:
        sent = await context.bot.send_photo(
            chat_id=chat_id,
            photo=photo_file_id,
            caption=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )
        store[scope] = sent.message_id
    except BadRequest as e:
        if _is_wrong_file_id(e):
            logger.warning("[UI] sendPhoto 400 (file_id inválido). Enviando só texto. Err=%s", e)
            await render_text(
                update, context, text, reply_markup,
                scope=scope, parse_mode=parse_mode,
                delete_previous_on_send=delete_previous_on_send,
                allow_edit=False
            )
        else:
            raise

# --- Compatibilidade: nomes usados em handlers antigos ---

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
    file_id: Optional[str],
    file_type: Optional[str] = "photo",
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    *,
    scope: str = "default",
    parse_mode: str = ParseMode.HTML,
    delete_previous_on_send: bool = True,
    allow_edit: bool = True,
) -> None:
    """
    Para callbacks: tenta editar (caption se for photo/video), senão envia novo.
    Observação: editar vídeo é bem limitado; aqui a gente prioriza SEND limpo.
    """
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None:
        return

    store = _get_store(context)

    if not file_id:
        return await render_text(
            update, context, text, reply_markup,
            scope=scope, parse_mode=parse_mode,
            delete_previous_on_send=delete_previous_on_send,
            allow_edit=allow_edit
        )

    ftype = (file_type or "photo").lower().strip()

    # Para foto, tenta editar caption (melhor UX)
    if ftype != "video":
        return await render_photo_or_text(
            update, context, text, file_id, reply_markup,
            scope=scope, parse_mode=parse_mode,
            delete_previous_on_send=delete_previous_on_send,
            allow_edit=allow_edit
        )

    # Para vídeo: não tenta edit (Telegram costuma falhar); faz SEND limpo
    if delete_previous_on_send:
        last_id = store.get(scope)
        if isinstance(last_id, int):
            await _safe_delete(chat_id, last_id, context)

    try:
        sent = await context.bot.send_video(
            chat_id=chat_id,
            video=file_id,
            caption=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )
        store[scope] = sent.message_id
    except BadRequest as e:
        if _is_wrong_file_id(e):
            await render_text(
                update, context, text, reply_markup,
                scope=scope, parse_mode=parse_mode,
                delete_previous_on_send=delete_previous_on_send,
                allow_edit=False
            )
        else:
            raise