# modules/game_data/constants.py
TRAVEL_TIME_MINUTES = 15
COLLECTION_TIME_MINUTES = 10

PREMIUM_TIERS = {
    "free": {
        "display_name": "Aventureiro Comum",
        "color": "#AAAAAA",
        "perks": {
            "gather_speed_multiplier": 1.0,
            "gather_xp_multiplier": 1.0,
            "gather_energy_cost": 1,
            "xp_multiplier": 1.0,
            "gold_multiplier": 1.0,
            "refine_speed_multiplier": 1.0,
            "max_energy_bonus": 0,
            "energy_regen_seconds": 420,  # 7 min por energia
        }
    },
    "premium": {
        "display_name": "Aventureiro Premium",
        "color": "#FFD700",
        "perks": {
            "gather_speed_multiplier": 1.5,
            "gather_xp_multiplier": 1.5,
            "gather_energy_cost": 1,
            "xp_multiplier": 1.25,
            "gold_multiplier": 1.25,
            "refine_speed_multiplier": 1.25,
            "max_energy_bonus": 5,
            "energy_regen_seconds": 300,  # 5 min
        }
    },
    "vip": {
        "display_name": "Aventureiro VIP",
        "color": "#FF4500",
        "perks": {
            "gather_speed_multiplier": 2.0,
            "gather_xp_multiplier": 2.0,
            "gather_energy_cost": 0,
            "xp_multiplier": 1.5,
            "gold_multiplier": 1.5,
            "refine_speed_multiplier": 1.5,
            "max_energy_bonus": 10,
            "energy_regen_seconds": 180,  # 3 min
        }
    },
    "lenda": {
        "display_name": "Aventureiro Lenda",
        "color": "#B300FF",
        "perks": {
            "gather_speed_multiplier": 2.5,
            "gather_xp_multiplier": 2.5,
            "gather_energy_cost": 0,
            "xp_multiplier": 1.75,
            "gold_multiplier": 1.5,
            "refine_speed_multiplier": 2.0,
            "max_energy_bonus": 15,
            "energy_regen_seconds": 120,  # 2 min
        }
    }
}
