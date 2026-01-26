from __future__ import annotations
from datetime import datetime, timezone

def _parse_iso(dt_str: str):
    try:
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None

def check_account_lock(pdata: dict) -> tuple[bool, str | None]:
    lock = (pdata or {}).get("account_lock") or {}
    if not lock.get("active"):
        return False, None

    reason = lock.get("reason") or "Não informado."
    until_iso = lock.get("until")

    # auto-unlock se expirou
    if until_iso:
        dt = _parse_iso(until_iso)
        if dt and dt <= datetime.now(timezone.utc):
            pdata.pop("account_lock", None)
            return False, None

    msg = (
        "⛔ <b>Conta bloqueada</b>\n\n"
        f"📝 <b>Motivo:</b> {reason}\n"
    )
    if until_iso:
        msg += f"\n⏳ <b>Desbloqueio automático em:</b>\n<code>{until_iso}</code>\n"
    else:
        msg += "\n⏳ <b>Duração:</b> Indeterminada\n"

    msg += "\nSe você acredita que é um engano, contate a administração."
    return True, msg
