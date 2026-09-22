# modules/game_data/dungeon_events.py

# ==============================================================================
# 🏰 CONFIGURAÇÃO DOS EVENTOS DE DUNGEON
# ==============================================================================

DUNGEON_EVENTS = {
    "dungeon_01": {
        "bau_01": {
            "event_type": "mimic_sequence",

            # Monstro especial ativado pelo puzzle
            "monster_id": "mimico_dungeon_01",

            # Recompensa do baú
            "loot_id": "bau_dungeon_01",

            # Pedras disponíveis no puzzle
            "available_lights": [
                1,
                2,
                3,
                4,
                5,
                6,
            ],

            # Quantidade de pedras corretas
            "sequence_length": 3,

            # A combinação é criada aleatoriamente
            "random_sequence": True,

            # Errou uma pedra = Mímico
            "trigger_mimic_on_wrong": True,

            # Tentou abrir o baú antes de resolver = Mímico
            "trigger_mimic_on_early_chest": True,

            # Controle de versão do estado salvo
            "state_version": 2,
        }
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