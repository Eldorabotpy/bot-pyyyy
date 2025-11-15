# tools/hard_respec_all.py (CORRIGIDO com asyncio)

import os
import sys
import asyncio # <-- 1. Importar asyncio

# Adiciona o diretório raiz ao path (mantido)
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from modules import player_manager

# <-- 2. Mudar a função para "async def"
async def hard_respec_all_players():
    total = 0
    changed = 0
    
    # iter_players é síncrono, o que está OK
    for uid, _ in player_manager.iter_players():
        total += 1
        
        try:
            # <-- 3. Adicionar "await" para todas as chamadas async
            pdata = await player_manager.get_player_data(uid)
            if not pdata:
                continue

            if "point_pool" in pdata:
                pdata.pop("point_pool", None)

            # reset_stats_and_refund_points também é async
            spent_before = await player_manager.reset_stats_and_refund_points(pdata)

            # save_player_data também é async
            await player_manager.save_player_data(uid, pdata)
            changed += 1

            print(f"[OK] uid={uid} respec aplicado; pontos reembolsados (aprox): {spent_before}")
        
        except Exception as e:
            print(f"[ERRO] Falha ao processar uid={uid}: {e}")

    print(f"\nConcluído! Jogadores varridos: {total} | Respecs aplicados: {changed}")

if __name__ == "__main__":
    # <-- 4. Usar asyncio.run() para executar a função async
    print("Iniciando script de reset assíncrono...")
    asyncio.run(hard_respec_all_players())
    print("Script finalizado.")