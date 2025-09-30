# modules/game_data/monsters_data.py

# Templates “base” (equilíbrio geral)
WOLF = {"id":"wolf","name":"Lobo Cinzento","hp": 30,"attack": 9,"defense": 3,"initiative": 9,"luck": 5,"xp_reward": 22,"gold_drop": 1,
        "loot_table":[{"item_id":"pele_lobo","drop_chance": 35.0}]}

BANDIT = {"id":"bandit","name":"Bandido","hp": 38,"attack": 11,"defense": 4,"initiative": 7,"luck": 6,"xp_reward": 26,"gold_drop": 1,
          "loot_table":[{"item_id":"moeda_enferrujada","drop_chance": 40.0}]}

YETI = {"id":"yeti","name":"Yeti","hp": 90,"attack": 22,"defense": 10,"initiative": 6,"luck": 7,"xp_reward": 70,"gold_drop": 1,
        "loot_table":[{"item_id":"pelo_gelado","drop_chance": 30.0}]}

SCORPION = {"id":"scorpion","name":"Escorpião Ancestral","hp": 140,"attack": 33,"defense": 16,"initiative": 10,"luck": 8,"xp_reward": 1,"gold_drop": 60,
            "loot_table":[{"item_id":"aguilhao_ancestral","drop_chance": 22.0}]}

# Pools por região
REGION_POOLS = {
    "pradaria_inicial": [WOLF, BANDIT],
    "floresta_sombria": [WOLF, BANDIT],
    "picos_gelados": [YETI],
    "deserto_ancestral": [SCORPION],
    # fallback
    "default": [WOLF, BANDIT],
}

# caso precise
DEFAULT_POOL = [WOLF, BANDIT]
