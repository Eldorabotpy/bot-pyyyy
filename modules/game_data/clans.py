# Em modules/game_data/clans.py

CLAN_CONFIG = {
    "creation_cost": {
        "gold": 30000,
        "dimas": 100
    }
}

CLAN_PRESTIGE_LEVELS = {
    1: {"title": "Iniciante", "max_members": 5, "points_to_next_level": 1000, "upgrade_cost": {"prestige": 1000, "gold": 50000, "dimas": 200}},
    2: {"title": "Reconhecido", "max_members": 10, "points_to_next_level": 2500, "upgrade_cost": {"prestige": 2500, "gold": 150000, "dimas": 500}},
    3: {"title": "Renomado", "max_members": 15, "points_to_next_level": 5000, "upgrade_cost": {"prestige": 5000, "gold": 300000, "dimas": 1000}},
    4: {"title": "Lendário", "max_members": 20, "points_to_next_level": None}
}

# Em modules/game_data/clans.py

CLAN_PRESTIGE_LEVELS = {
    1: {
        "title": "Iniciante", "max_members": 5, "points_to_next_level": 1000, 
        "upgrade_cost": {"prestige": 1000, "gold": 50000, "dimas": 200},
        "buffs": {} # Nível 1 não tem buffs
    },
    2: {
        "title": "Reconhecido", "max_members": 10, "points_to_next_level": 2500, 
        "upgrade_cost": {"prestige": 2500, "gold": 150000, "dimas": 500},
        "buffs": {
            "xp_bonus_percent": 5,   # +5% de XP em todas as fontes
            "gold_bonus_percent": 3    # +3% de Ouro em todas as fontes
        }
    },
    3: {
        "title": "Renomado", "max_members": 15, "points_to_next_level": 5000, 
        "upgrade_cost": {"prestige": 5000, "gold": 300000, "dimas": 1000},
        "buffs": {
            "xp_bonus_percent": 10,
            "gold_bonus_percent": 5,
            "all_stats_percent": 1   # +1% em todos os atributos (força, defesa, etc.)
        }
    },
    4: {
        "title": "Lendário", "max_members": 20, "points_to_next_level": None,
        "buffs": {
            "xp_bonus_percent": 15,
            "gold_bonus_percent": 10,
            "all_stats_percent": 2,
            "crafting_speed_percent": 5 # -5% no tempo de forja/refino
        }
    }
}