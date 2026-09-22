# modules/game_data/dungeon_chests.py
# Recompensas dos baús de dungeon.
#
# O evento do Mímico já funciona sem recompensa configurada.
# Enquanto "configured" estiver False, o baú NÃO será marcado como aberto,
# evitando que o jogador perca a recompensa durante os testes.

DUNGEON_CHEST_REWARDS = {
    "bau_dungeon_01": {
        "configured": False,

        # Preencha quando definirmos o prêmio final:
        "gold": 0,

        # Formato:
        # "items": {
        #     "cristal_mana_bruto": 2,
        #     "elixir_de_experiencia": 1,
        # }
        "items": {},
    }
}