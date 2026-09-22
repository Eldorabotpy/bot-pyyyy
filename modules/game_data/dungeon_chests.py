# modules/game_data/dungeon_chests.py

# ==============================================================================
# 🎁 RECOMPENSAS DOS BAÚS DE DUNGEON
# ==============================================================================

DUNGEON_CHEST_REWARDS = {

    # ==========================================================================
    # 🏰 DUNGEON 01 — BAÚ DO ENIGMA
    # ==========================================================================

    "bau_dungeon_01": {

        "configured": True,

        # ----------------------------------------------------------------------
        # 💰 OURO
        # ----------------------------------------------------------------------
        # Sempre recebe uma quantidade aleatória dentro da faixa.

        "gold": {
            "min": 100,
            "max": 220,
        },

        # ----------------------------------------------------------------------
        # 📦 DROPS INDEPENDENTES
        # ----------------------------------------------------------------------
        #
        # Cada item possui sua própria chance.
        #
        # chance = 0.45 → 45%
        # chance = 0.12 → 12%
        # ----------------------------------------------------------------------

        "drops": [

            {
                "item_id": "po_runico",
                "chance": 0.45,
                "min": 1,
                "max": 3,
            },

            {
                "item_id": "fragmento_runa_ancestral",
                "chance": 0.12,
                "min": 1,
                "max": 1,
            },

        ],

        # ----------------------------------------------------------------------
        # 🔮 RUNA MENOR
        # ----------------------------------------------------------------------
        #
        # 3% de chance.
        #
        # Se cair, sorteia UMA das runas menores abaixo.
        # ----------------------------------------------------------------------

        "rune_roll": {

            "chance": 0.03,

            "quantity": 1,

            "pool": [

                "runa_crueldade_menor",

                "runa_precisao_menor",

                "runa_vampiro_menor",

                "runa_rocha_menor",

                "runa_mente_menor",

                "runa_eco_menor",

                "runa_midas_menor",

                "runa_sabio_menor",

            ],

        },

    },

}