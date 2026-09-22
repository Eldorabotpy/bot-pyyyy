# modules/game_data/dungeon_events.py
# Configuração dos eventos interativos das dungeons.

DUNGEON_EVENTS = {
    "dungeon_01": {
        "bau_01": {
            "event_type": "mimic_sequence",
            "monster_id": "mimico_dungeon_01",
            "loot_id": "bau_dungeon_01",

            # Existem 6 pedras no mapa, mas a senha usa somente 3.
            "available_lights": [1, 2, 3, 4, 5, 6],
            "sequence_length": 3,

            # O servidor sorteia uma sequência sem repetição.
            # Exemplo:
            # [2, 6, 4]
            # [1, 5, 3]
            # [6, 2, 1]
            "random_sequence": True,

            # Se errar a sequência, desperta o Mímico.
            "trigger_mimic_on_wrong": True,

            # Se tentar abrir o baú antes de resolver,
            # também desperta o Mímico.
            "trigger_mimic_on_early_chest": True,

            # Versão do estado salvo.
            "state_version": 1,
        }
    }
}


def get_dungeon_event_config(
    dungeon_id: str,
    puzzle_id: str
) -> dict | None:

    dungeon = DUNGEON_EVENTS.get(
        str(dungeon_id),
        {}
    )

    config = dungeon.get(
        str(puzzle_id)
    )

    if isinstance(config, dict):
        return dict(config)

    return None