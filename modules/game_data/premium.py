# modules/game_data/premium.py

PREMIUM_TIERS = {
    "free": {
        "display_name": "Aventureiro Comum",
        "color": "#AAAAAA",
        "perks": {
            # Profissões / Coleta
            "gather_speed_multiplier": 1.0,
            "gather_xp_multiplier": 1.0,
            "gather_energy_cost": 1,

            # Progressão / Recompensas
            "xp_multiplier": 1.0,
            "gold_multiplier": 1.0,

            # Refino
            "refine_speed_multiplier": 1.0,

            # Energia
            "max_energy_bonus": 0,
            "energy_regen_seconds": 420,

            # Viagem (opcional; se quiser viagem instantânea para pagos)
            "travel_time_multiplier": 1.0,  # free = normal
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
            "energy_regen_seconds": 300,

            "travel_time_multiplier": 0.0,  # viagem instantânea
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
            "energy_regen_seconds": 180,

            "travel_time_multiplier": 0.0,
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
            "energy_regen_seconds": 120,

            "travel_time_multiplier": 0.0,
        }
    }
}
