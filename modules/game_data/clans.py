# modules/game_data/clans.py

CLAN_CONFIG = {
    "creation_cost": {"gold": 30000, "dimas": 100},
    "mission_board_cost": {"gold": 5000}
}

CLAN_PRESTIGE_LEVELS = {
    1: {
        "title": "Iniciante",
        "max_members": 5,
        "points_to_next_level": 5000,  # Do 1 para o 2: Precisa de 5.000
        "upgrade_cost": {"gold": 0, "dimas": 0},
        "buffs": {} 
    },
    2: {
        "title": "Reconhecido",
        "max_members": 10,
        "points_to_next_level": 30000, # Do 2 para o 3: Precisa de 30.000
        "upgrade_cost": {"gold": 150000, "dimas": 500},
        "buffs": {
            "xp_bonus": 5,
            "gold_bonus": 3
        }
    },
    3: {
        "title": "Renomado",
        "max_members": 15,
        "points_to_next_level": 60000, # Do 3 para o 4: Precisa de 60.000
        "upgrade_cost": {"gold": 300000, "dimas": 1000},
        "buffs": {
            "xp_bonus": 10,
            "gold_bonus": 5,
            "drop_rate": 2
        }
    },
    4: {
        "title": "Lendário",
        "max_members": 20,
        "points_to_next_level": 120000, # Do 4 para o 5: Precisa de 120.000
        "upgrade_cost": {"gold": 500000, "dimas": 1500},
        "buffs": {
            "xp_bonus": 15,
            "gold_bonus": 8,
            "drop_rate": 5,
            "damage": 2
        }
    },
    5: {
        "title": "Mítico",
        "max_members": 25,
        "points_to_next_level": 250000, # Do 5 para o 6: Precisa de 250.000
        "upgrade_cost": {"gold": 1000000, "dimas": 3000},
        "buffs": {
            "xp_bonus": 20,
            "gold_bonus": 10,
            "drop_rate": 8,
            "damage": 5
        }
    },
    6: {
        "title": "Divino",
        "max_members": 30,
        "points_to_next_level": 999999999, # Nível Máximo (Fim)
        "upgrade_cost": {"gold": 2000000, "dimas": 5000},
        "buffs": {
            "xp_bonus": 25,
            "gold_bonus": 15,
            "drop_rate": 10,
            "damage": 8,
            "crafting_speed": 5
        }
    }
}