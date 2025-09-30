# debug_check_cristal.py
from modules.player_manager import iter_players, _ival

print("Checando cristais de abertura...")
for uid, pdata in iter_players():
    inv = pdata.get("inventory", {})
    qtd = _ival(inv.get("cristal_de_abertura"))
    print(f"{uid} -> {qtd} itens")
