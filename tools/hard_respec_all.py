# tools/hard_respec_all.py

from modules import player_manager
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

def hard_respec_all_players():
    total = 0
    changed = 0
    for uid, _ in player_manager.iter_players():
        total += 1
        # carrega sincronizando baseline por classe/nível e migrando saves antigos
        pdata = player_manager.get_player_data(uid)
        if not pdata:
            continue

        # opcional: remover point_pool legado (get_player_data já migra, mas garantimos)
        if "point_pool" in pdata:
            pdata.pop("point_pool", None)

        # aplica o respec completo: volta para base_stats e devolve pontos
        spent_before = player_manager.reset_stats_and_refund_points(pdata)

        # salva
        player_manager.save_player_data(uid, pdata)
        changed += 1

        # log opcional
        print(f"[OK] uid={uid} respec aplicado; pontos reembolsados (aprox): {spent_before}")

    print(f"\nConcluído! Jogadores varridos: {total} | Respecs aplicados: {changed}")

if __name__ == "__main__":
    hard_respec_all_players()
