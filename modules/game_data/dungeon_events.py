# modules/game_data/dungeon_events.py

# ==============================================================================
# 🏰 CONFIGURAÇÃO DOS EVENTOS DE DUNGEON
# ==============================================================================

DUNGEON_EVENTS = {
    "dungeon_01": {

        # ====================================================
        # 🧩 BAÚ ESPECIAL — PUZZLE DAS PEDRAS
        # ====================================================

        "bau_01": {
            "event_type": "mimic_sequence",
            "monster_id": "mimico_dungeon_01",
            "loot_id": "bau_dungeon_01",

            "available_lights": [
                1,
                2,
                3,
                4,
                5,
                6,
            ],

            "sequence_length": 3,
            "random_sequence": True,

            "trigger_mimic_on_wrong": True,
            "trigger_mimic_on_early_chest": True,

            "state_version": 1,
        },


        # ====================================================
        # 📦 BAÚS COMUNS — 30% DE CHANCE DE MÍMICO
        # ====================================================

        "bau_02": {
            "event_type": "common_chest",
            "monster_id": "mimico_dungeon_01",
            "loot_id": "bau_dungeon_01_comum",
            "mimic_chance": 0.30,
            "state_version": 1,
        },

        "bau_03": {
            "event_type": "common_chest",
            "monster_id": "mimico_dungeon_01",
            "loot_id": "bau_dungeon_01_comum",
            "mimic_chance": 0.30,
            "state_version": 1,
        },

        "bau_04": {
            "event_type": "common_chest",
            "monster_id": "mimico_dungeon_01",
            "loot_id": "bau_dungeon_01_comum",
            "mimic_chance": 0.30,
            "state_version": 1,
        },

        "bau_05": {
            "event_type": "common_chest",
            "monster_id": "mimico_dungeon_01",
            "loot_id": "bau_dungeon_01_comum",
            "mimic_chance": 0.30,
            "state_version": 1,
        },
    }
}


def get_dungeon_event_config(
    dungeon_id,
    puzzle_id,
):
    """
    Retorna a configuração de um evento específico
    dentro de uma dungeon.
    """

    dungeon_id = str(dungeon_id or "")
    puzzle_id = str(puzzle_id or "")

    dungeon_data = DUNGEON_EVENTS.get(
        dungeon_id,
        {}
    )

    config = dungeon_data.get(
        puzzle_id
    )

    if not isinstance(config, dict):
        return None

    return config.copy()