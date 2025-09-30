# audit_daily_cristal.py
from datetime import datetime
from zoneinfo import ZoneInfo

from modules.player_manager import iter_players, _ival

DAILY_CRYSTAL_ITEM_ID = "cristal_de_abertura"
DAILY_TZ = "America/Fortaleza"

def today_str():
    try:
        return datetime.now(ZoneInfo(DAILY_TZ)).date().isoformat()
    except Exception:
        # Se faltar tzdata no Windows, cai no local
        return datetime.now().date().isoformat()

def main():
    today = today_str()
    has_item = 0
    no_item = 0
    marked_today_but_zero = 0
    marked_other_date = 0
    never_marked = 0

    print(f"Hoje (tz={DAILY_TZ}): {today}\n")
    print("UID | qtd | last_crystal_date")
    print("-" * 40)

    for uid, pdata in iter_players():
        inv = (pdata.get("inventory") or {})
        daily = (pdata.get("daily_awards") or {})
        qty = _ival(inv.get(DAILY_CRYSTAL_ITEM_ID), 0)
        last = daily.get("last_crystal_date")

        if qty > 0:
            has_item += 1
        else:
            no_item += 1

        if last == today and qty <= 0:
            marked_today_but_zero += 1
        elif last and last != today:
            marked_other_date += 1
        elif not last:
            never_marked += 1

        print(f"{uid} -> {qty} | {last}")

    print("\nResumo:")
    print(f"Com item: {has_item}")
    print(f"Sem item: {no_item}")
    print(f"Marcado HOJE mas sem item: {marked_today_but_zero}")
    print(f"Marcado OUTRA data: {marked_other_date}")
    print(f"Nunca marcado: {never_marked}")

if __name__ == '__main__':
    main()
