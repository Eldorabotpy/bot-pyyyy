# Em kingdom_defense/data.py

WAVE_DEFINITIONS = {
    1: {
        "mobs": [
            {
                "name": "Goblin Batedor", "hp": 50, "reward": 1, "media_key": "kd_goblin_batedor",
                # 👇 ADICIONE ESTES ATRIBUTOS 👇
                "attack": 10, "defense": 2, "initiative": 5, "luck": 5 
            },
            {
                "name": "Goblin Lanceiro", "hp": 75, "reward": 2, "media_key": "kd_goblin_lanceiro",
                # 👇 ADICIONE ESTES ATRIBUTOS 👇
                "attack": 15, "defense": 5, "initiative": 3, "luck": 8
            },
        ],
        "mob_count": 10,
        "boss": {
            "name": "Chefe Goblin 'Gork'", "hp": 1000, "reward": 25, "media_key": "kd_chefe_gork",
            # 👇 ADICIONE ESTES ATRIBUTOS 👇
            "attack": 40, "defense": 15, "initiative": 10, "luck": 15
        },
    },
    # ... adicione também para a onda 2 e as seguintes ...
}