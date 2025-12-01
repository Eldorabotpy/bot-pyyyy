# modules/game_data/clans.py

CLAN_CONFIG = {
    # Custo para criar um clã novo
    "creation_cost": {
        "gold": 30000,
        "dimas": 100
    },
    # Custo para comprar o quadro de missões
    "mission_board_cost": {
        "gold": 5000
    }
}

CLAN_PRESTIGE_LEVELS = {
    1: {
        "title": "Iniciante",
        "max_members": 5,
        "points_to_next_level": 5000, # Precisa de 5k XP para ir pro 2
        "upgrade_cost": {"gold": 0, "dimas": 0}, # Nível inicial é grátis (paga na criação)
        "buffs": {} # Sem buffs no nível 1
    },
    2: {
        "title": "Reconhecido",
        "max_members": 10,
        "points_to_next_level": 15000,
        "upgrade_cost": {"gold": 150000, "dimas": 500}, # Custo para virar Nível 2
        "buffs": {
            "xp_bonus": 5,        # +5% XP
            "gold_bonus": 3       # +3% Ouro
        }
    },
    3: {
        "title": "Renomado",
        "max_members": 15,
        "points_to_next_level": 30000,
        "upgrade_cost": {"gold": 300000, "dimas": 1000}, # Custo para virar Nível 3
        "buffs": {
            "xp_bonus": 10,
            "gold_bonus": 5,
            "drop_rate": 2        # +2% Sorte
        }
    },
    4: {
        "title": "Lendário",
        "max_members": 20,
        "points_to_next_level": 50000,
        "upgrade_cost": {"gold": 500000, "dimas": 1500}, # Custo para virar Nível 4
        "buffs": {
            "xp_bonus": 15,
            "gold_bonus": 8,
            "drop_rate": 5,
            "damage": 2           # +2% Dano
        }
    },
    5: {
        "title": "Mítico",
        "max_members": 25,
        "points_to_next_level": 80000,
        "upgrade_cost": {"gold": 1000000, "dimas": 3000}, # Custo para virar Nível 5
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
        "points_to_next_level": 999999999, # Nível Máximo
        "upgrade_cost": {"gold": 2000000, "dimas": 5000}, # Custo para virar Nível 6
        "buffs": {
            "xp_bonus": 25,
            "gold_bonus": 15,
            "drop_rate": 10,
            "damage": 8,
            "crafting_speed": 5   # -5% tempo de craft
        }
    }
}