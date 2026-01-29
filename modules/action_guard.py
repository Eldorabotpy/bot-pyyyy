# modules/action_guard.py
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from modules import player_manager
from modules.auth_utils import get_current_player_id_async

logger = logging.getLogger(__name__)

DEFAULT_ALLOWED_CALLBACKS = {
    "action_status",
    "action_refresh",
    "continue_after_action",
    "noop",
}


def _parse_finish_time(finish_time_str: str | None) -> datetime | None:
    if not finish_time_str:
        return None
    try:
        dt = datetime.fromisoformat(str(finish_time_str).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None

def _format_remaining(finish_dt: datetime | None) -> str | None:
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

def _action_label(action: str) -> str:
    # você pode mapear nomes bonitos aqui
    return action

def is_busy(pdata: dict) -> Tuple[bool, str, dict]:
    state = (pdata or {}).get("player_state") or {}
    action = (state.get("action") or "idle")
    if not action or action == "idle":
        return (False, "idle", state)
    return (True, action, state)

def _is_allowed_callback_data(data: str | None, allow: set[str]) -> bool:
    if not data:
        return False
    # permitido exato
    if data in allow:
        return True
    # permitido por prefixo (caso você queira)
    # ex: "action_status:" ou "continue_after_action"
    for a in allow:
        if a and data.startswith(a):
            return True
    return False

async def guard_or_notify(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    allow_callback_data: Optional[set[str]] = None,
    allow_actions: Optional[set[str]] = None,
) -> bool:
    """
    Retorna True se pode prosseguir.
    Retorna False se bloqueou e já notificou o usuário.

    - allow_actions: se action atual estiver aqui, não bloqueia
    - allow_callback_data: allowlist de callback_data durante lock
    """
    allow_callback_data = allow_callback_data or set(DEFAULT_ALLOWED_CALLBACKS)
    allow_actions = allow_actions or set()

    pid = await get_current_player_id_async(update, context)
    if not pid:
        return True  # sem sessão -> deixa o fluxo de login agir

    try:
        pdata = await player_manager.get_player_data(pid)
    except Exception:
        return True

    if not pdata:
        return True

    busy, action, state = is_busy(pdata)
    if not busy:
        return True

    if action in allow_actions:
        return True

    # callback allowlist
    if update.callback_query:
        data = update.callback_query.data
        if _is_allowed_callback_data(data, allow_callback_data):
            return True

    finish_dt = _parse_finish_time(state.get("finish_time"))
    remaining = _format_remaining(finish_dt)


    base_msg = f"⏳ Você está em ação: <b>{_action_label(action)}</b>."
    if remaining:
        base_msg += f"\n⏱️ Tempo restante: <b>{remaining}</b>"

    # ✅ versão curta (para comandos /start /menu)
    msg_short = base_msg + "\n\n✅ Aguarde concluir para iniciar outra ação."

    # ✅ versão completa (só para callbacks -> show_alert, não gera lixo no chat)
    msg_full = (
        base_msg
        + "\n\n✅ Aguarde concluir para iniciar outra ação."
        + "\n\n<b>Você ainda pode:</b>\n"
          "• 📍 Ver ação atual\n"
          "• 🔄 Atualizar\n"
          "• ⬅️ Voltar\n"
          "• ℹ️ Info da região"
    )

    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📍 Ver ação atual", callback_data="action_status")],
            [InlineKeyboardButton("🔄 Atualizar", callback_data="action_refresh")],
        ]
    )

    if update.callback_query:
        q = update.callback_query

        # popup (zero lixo)
        try:
            await q.answer(msg_full, show_alert=True)
        except Exception:
            try:
                await q.answer("⏳ Você já está em uma ação. Aguarde.", show_alert=True)
            except Exception:
                pass

        # ✅ trava a UI atual (mapa/menus) substituindo os botões
        try:
            await q.edit_message_reply_markup(reply_markup=kb)
        except Exception:
            pass

        return False


