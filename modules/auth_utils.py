from __future__ import annotations

from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from bson import ObjectId
from telegram.constants import ParseMode
from modules.player.account_lock import check_account_lock
from modules import player_manager



try:
    from modules.sessions import get_persistent_session
except ImportError:
    async def get_persistent_session(tid):  # type: ignore
        return None


def _normalize_player_id(pid) -> str | None:
    """
    Aceita qualquer valor e retorna SOMENTE string ObjectId válida.
    """
    if pid is None:
        return None

    if isinstance(pid, ObjectId):
        return str(pid)

    if isinstance(pid, str):
        pid = pid.strip()
        if ObjectId.is_valid(pid):
            return pid
        return None

    # legado (int) ou outros tipos: rejeita
    return None


def get_current_player_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str | None:
    """
    Versão síncrona: consulta apenas RAM (context.user_data).
    Retorna ObjectId string válida ou None.
    """
    user_data = getattr(context, "user_data", None)
    if not user_data:
        return None

    pid = user_data.get("logged_player_id")
    return _normalize_player_id(pid)


async def get_current_player_id_async(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str | None:
    """
    Versão robusta: tenta RAM; se falhar, tenta sessão persistente no banco e repõe RAM.
    Retorna ObjectId string válida ou None.
    """
    # 1) RAM
    pid = get_current_player_id(update, context)
    if pid:
        return pid

    # 2) Persistência
    if not update.effective_user:
        return None

    tg_id = update.effective_user.id
    saved_player_id = await get_persistent_session(tg_id)

    pid2 = _normalize_player_id(saved_player_id)
    if pid2:
        # repõe RAM para o restante do fluxo
        try:
            if getattr(context, "user_data", None) is not None:
                context.user_data["logged_player_id"] = pid2
        except Exception:
            pass
        return pid2

    return None


def requires_login(func):
    """
    Decorator blindado:
    - Garante sessão válida (RAM ou persistência).
    - BLOQUEIA contas com account_lock ativo.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        # Permite injeção manual para testes
        if kwargs.get("player_data"):
            return await func(update, context, *args, **kwargs)

        pid = await get_current_player_id_async(update, context)
        if not pid:
            msg = "⚠️ <b>Sessão expirada.</b>\nPor favor, digite /start para reconectar."
            try:
                if update.callback_query:
                    try:
                        await update.callback_query.answer(
                            "⚠️ Sessão expirada. Use /start.",
                            show_alert=True
                        )
                    except Exception:
                        pass
                elif update.effective_message:
                    await update.effective_message.reply_text(msg, parse_mode=ParseMode.HTML)
            except Exception:
                pass
            return

        # ===============================
        # 🔒 BLOQUEIO GLOBAL DE CONTA
        # ===============================
        try:
            pdata = await player_manager.get_player_data(pid)
            if pdata:
                locked, lock_msg = check_account_lock(pdata)
                if locked:
                    if update.callback_query:
                        await update.callback_query.answer()
                        try:
                            await update.callback_query.edit_message_text(
                                lock_msg,
                                parse_mode=ParseMode.HTML
                            )
                        except Exception:
                            # fallback se a msg for mídia
                            await update.callback_query.message.reply_text(
                                lock_msg,
                                parse_mode=ParseMode.HTML
                            )
                    elif update.effective_message:
                        await update.effective_message.reply_text(
                            lock_msg,
                            parse_mode=ParseMode.HTML
                        )
                    return  # 🚫 BLOQUEIA QUALQUER AÇÃO
        except Exception:
            # segurança: nunca quebra fluxo por erro de bloqueio
            pass

        # Sessão válida e conta liberada
        return await func(update, context, *args, **kwargs)

    return wrapper

