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

# =================================================================
# PLANOS PREMIUM À VENDA NA LOJA DE GEMAS (VERSÃO CORRIGIDA)
# =================================================================
# Agora, cada plano vende um TIER específico dos seus PREMIUM_TIERS.
PREMIUM_PLANS_FOR_SALE = {
    "premium_30d": {
        "name": "Aventureiro Premium (30 Dias)",
        "description": "Ativa todas as vantagens do tier Premium.",
        "price": 120, # Preço em gemas
        "tier": "premium", # <--- Mapeia diretamente para a chave em PREMIUM_TIERS
        "days": 30
    },
    "premium_15d": {
        "name": "Aventureiro Premium (15 Dias)",
        "description": "Ativa todas as vantagens do tier Premium.",
        "price": 90, # Preço em gemas
        "tier": "premium", # <--- Mapeia diretamente para a chave em PREMIUM_TIERS
        "days": 15
    },
    "premium_7d": {
        "name": "Aventureiro Premium (7 Dias)",
        "description": "Ativa todas as vantagens do tier Premium.",
        "price": 40, # Preço em gemas
        "tier": "premium", # <--- Mapeia diretamente para a chave em PREMIUM_TIERS
        "days": 7
    },
    "vip_30d": {
        "name": "Aventureiro VIP (30 Dias)",
        "description": "Ativa as vantagens incríveis do tier VIP.",
        "price": 240, # Preço em gemas
        "tier": "vip", # <--- Mapeia diretamente para a chave em PREMIUM_TIERS
        "days": 30
    },
    "vip_15d": {
        "name": "Aventureiro VIP (15 Dias)",
        "description": "Ativa as vantagens incríveis do tier VIP.",
        "price": 130, # Preço em gemas
        "tier": "vip", # <--- Mapeia diretamente para a chave em PREMIUM_TIERS
        "days": 15
    },
    "vip_7d": {
        "name": "Aventureiro VIP (7 Dias)",
        "description": "Ativa as vantagens incríveis do tier VIP.",
        "price": 70, # Preço em gemas
        "tier": "vip", # <--- Mapeia diretamente para a chave em PREMIUM_TIERS
        "days": 7
    },
    "lenda_30d": {
        "name": "Aventureiro Lenda (30 Dias)",
        "description": "Torne-se uma Lenda por um mês inteiro!",
        "price": 360, # Preço em gemas
        "tier": "lenda", # <--- Mapeia diretamente para a chave em PREMIUM_TIERS
        "days": 30
    },
    "lenda_15d": {
        "name": "Aventureiro Lenda (15 Dias)",
        "description": "Torne-se uma Lenda por um mês inteiro!",
        "price": 190, # Preço em gemas
        "tier": "lenda", # <--- Mapeia diretamente para a chave em PREMIUM_TIERS
        "days": 15
    },
    "lenda_7d": {
        "name": "Aventureiro Lenda (7 Dias)",
        "description": "Torne-se uma Lenda por um mês inteiro!",
        "price": 100, # Preço em gemas
        "tier": "lenda", # <--- Mapeia diretamente para a chave em PREMIUM_TIERS
        "days": 7
    },
}