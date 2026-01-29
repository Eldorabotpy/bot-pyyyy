# modules/action_guard.py
import logging
from datetime import datetime, timezone
from typing import Tuple

from telegram import Update
from telegram.ext import ContextTypes

from modules import player_manager
from modules.auth_utils import get_current_player_id_async

logger = logging.getLogger(__name__)


def _parse_finish_time(finish_time_str: str | None):
    if not finish_time_str:
        return None
    try:
        dt = datetime.fromisoformat(str(finish_time_str).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _format_remaining(finish_dt):
    if not finish_dt:
        return None
    now = datetime.now(timezone.utc)
    sec = int((finish_dt - now).total_seconds())
    if sec <= 0:
        return "finalizando..."
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h {m}m"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def is_busy(pdata: dict) -> Tuple[bool, str, dict]:
    state = (pdata or {}).get("player_state") or {}
    action = state.get("action") or "idle"
    if action == "idle":
        return False, "idle", state
    return True, action, state


async def guard_or_notify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    🔒 LOCK TOTAL:
    - Se estiver em ação: BLOQUEIA TUDO
    - Não edita mensagens
    - Não edita teclados
    - Não permite navegação
    - Apenas notifica e encerra
    """

    pid = await get_current_player_id_async(update, context)
    if not pid:
        # deixa o middleware de sessão agir
        return True

    try:
        pdata = await player_manager.get_player_data(pid)
    except Exception:
        return True

    if not pdata:
        return True

    busy, action, state = is_busy(pdata)
    if not busy:
        return True

    finish_dt = _parse_finish_time(state.get("finish_time"))
    remaining = _format_remaining(finish_dt)

    msg = f"⏳ Você está em ação: <b>{action}</b>."
    if remaining:
        msg += f"\n⏱️ Tempo restante: <b>{remaining}</b>"
    msg += "\n\nAguarde concluir."

    # CALLBACK → só popup, nada mais
    if update.callback_query:
        try:
            await update.callback_query.answer(msg, show_alert=True)
        except Exception:
            pass
        return False

    # COMANDO / TEXTO → mensagem simples
    try:
        if update.effective_chat:
            await context.bot.send_message(
                update.effective_chat.id,
                msg,
                parse_mode="HTML",
            )
    except Exception:
        pass

    return False
