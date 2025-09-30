# repair_daily_cristal_today.py
from datetime import datetime
from zoneinfo import ZoneInfo

from modules.player_manager import iter_players, save_player_data, _ival

DAILY_CRYSTAL_ITEM_ID = "cristal_de_abertura"
DAILY_CRYSTAL_QTY = 4
DAILY_TZ = "America/Fortaleza"

def today_str():
    try:
        return datetime.now(ZoneInfo(DAILY_TZ)).date().isoformat()
    except Exception:
        return datetime.now().date().isoformat()

def main():
    today = today_str()
    touched = 0
    fixed_marked_today = 0
    newly_granted = 0

    for uid, pdata in iter_players():
        inv = pdata.setdefault("inventory", {})
        daily = pdata.get("daily_awards") or {}
        qty = _ival(inv.get(DAILY_CRYSTAL_ITEM_ID), 0)
        last = daily.get("last_crystal_date")

        # Caso 1: já está marcado hoje, mas qty == 0 -> corrige (bug anterior)
        if last == today and qty <= 0:
            inv[DAILY_CRYSTAL_ITEM_ID] = DAILY_CRYSTAL_QTY
            save_player_data(uid, pdata)
            fixed_marked_today += 1
            touched += 1
            continue

        # Caso 2: não está marcado hoje -> concede + marca hoje
        if last != today:
            inv[DAILY_CRYSTAL_ITEM_ID] = qty + DAILY_CRYSTAL_QTY
            daily["last_crystal_date"] = today
            pdata["daily_awards"] = daily
            save_player_data(uid, pdata)
            newly_granted += 1
            touched += 1

    print(f"Backfill concluído. Ajustados: {touched} (corrigidos HOJE: {fixed_marked_today}, concedidos novos HOJE: {newly_granted}).")

if __name__ == "__main__":
    main()
