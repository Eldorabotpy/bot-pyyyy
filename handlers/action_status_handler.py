# handlers/action_status_handler.py

from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules.auth_utils import get_current_player_id_async
from modules import player_manager


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


async def action_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
    await q.answer()

    user_id = await get_current_player_id_async(update, context)
    if not user_id:
        await q.answer("❌ Sessão não encontrada.", show_alert=True)
        return

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        await q.answer("❌ Jogador não encontrado.", show_alert=True)
        return

    state = pdata.get("player_state", {}) or {}
    action = (state.get("action") or "idle")
    finish_dt = _parse_finish_time(state.get("finish_time"))
    remaining = _format_remaining(finish_dt)

    if action in ("idle", None):
        await q.answer("✅ Você não está em ação agora.", show_alert=True)
        return

    msg = f"⏳ Ação atual: <b>{action}</b>"
    if remaining:
        msg += f"\n⏱️ Tempo restante: <b>{remaining}</b>"

    # Se você quiser, aqui dá pra redirecionar para a tela da ação (coleta/forja),
    # mas por enquanto vamos manter como status rápido e confiável.
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔄 Atualizar", callback_data="action_refresh")],
            [InlineKeyboardButton("⬅️ Voltar", callback_data="continue_after_action")],
        ]
    )

    # Preferência: editar a mensagem do bloqueio (não gera lixo)
    try:
        await q.edit_message_text(msg, parse_mode="HTML", reply_markup=kb)
    except Exception:
        # fallback: popup
        await q.answer(msg.replace("<b>", "").replace("</b>", ""), show_alert=True)


async def action_refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Só chama status novamente (mais simples e estável)
    return await action_status_callback(update, context)


# exports
action_status_handler = CallbackQueryHandler(action_status_callback, pattern=r"^action_status$")
action_refresh_handler = CallbackQueryHandler(action_refresh_callback, pattern=r"^action_refresh$")
