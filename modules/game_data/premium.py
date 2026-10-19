# modules/game_data/premium.py
HUNT_ENERGY_COST = 1
COLLECTION_TIME_MINUTES = 10

PREMIUM_TIERS = {
    "free": {
        "display_name": "Aventureiro Comum",
        "perks": {
            "auto_hunt": False,
            "xp_multiplier": 1.0,
            "gold_multiplier": 1.0,
            "refine_speed_multiplier": 1.0,
            "max_energy_bonus": 0,
            "energy_regen_seconds": 420,  # 7 Minutos
            "travel_time_multiplier": 1.0,
            "gather_speed_multiplier": 1.0,
            "gather_energy_cost": 1,
            "hunt_energy_cost": 1,
        }
    },
    "premium": {
        "display_name": "Aventureiro Premium",
        "perks": {
            "auto_hunt": True,
            "xp_multiplier": 1.25,
            "gold_multiplier": 1.25,
            "refine_speed_multiplier": 1.25,
            "max_energy_bonus": 5,
            "energy_regen_seconds": 300,  # 5 Minutos
            "travel_time_multiplier": 0.0, # Viagem Instantânea
            "gather_speed_multiplier": 1.5,
            "gather_energy_cost": 1,
            "hunt_energy_cost": 1,
        }
    },
    "vip": {
        "display_name": "Aventureiro VIP",
        "perks": {
            "auto_hunt": True,
            "xp_multiplier": 1.5,
            "gold_multiplier": 1.5,
            "refine_speed_multiplier": 1.5,
            "max_energy_bonus": 10,
            "energy_regen_seconds": 180,  # 3 Minutos
            "travel_time_multiplier": 0.0, # Viagem Instantânea
            "gather_speed_multiplier": 2.0,
            "gather_energy_cost": 1,      # Coleta Grátis
            "hunt_energy_cost": 1,
        }
    },
    "lenda": {
        "display_name": "Aventureiro Lenda",
        "perks": {
            "auto_hunt": True,
            "xp_multiplier": 1.75,
            "gold_multiplier": 1.5,
            "refine_speed_multiplier": 2.0,
            "max_energy_bonus": 15,
            "energy_regen_seconds": 120,  # 2 Minutos
            "travel_time_multiplier": 0.0, # Viagem Instantânea
            "gather_speed_multiplier": 2.5,
            "gather_energy_cost": 0,      # Coleta Grátis
            "hunt_energy_cost": 1,        # Custa 1 (Regra Global)
        }
    }
}

# =================================================================
# PLANOS E PREÇOS
# =================================================================
PREMIUM_PLANS_FOR_SALE = {
    # --- PREMIUM ---
    "premium_30d": {"name": "Premium (30 Dias)", "price": 120, "tier": "premium", "days": 30},
    "premium_15d": {"name": "Premium (15 Dias)", "price": 70,  "tier": "premium", "days": 15},
    "premium_7d":  {"name": "Premium (7 Dias)",  "price": 35,  "tier": "premium", "days": 7},
    
    # --- VIP ---
    "vip_30d": {"name": "VIP (30 Dias)",     "price": 300, "tier": "vip", "days": 30},
    "vip_15d": {"name": "VIP (15 Dias)",     "price": 160, "tier": "vip", "days": 15},
    "vip_7d":  {"name": "VIP (7 Dias)",      "price": 80,  "tier": "vip", "days": 7},

    # --- LENDA ---
    "lenda_30d": {"name": "Lenda (30 Dias)",   "price": 500, "tier": "lenda", "days": 30},
    "lenda_15d": {"name": "Lenda (15 Dias)",   "price": 270, "tier": "lenda", "days": 15},
    "lenda_7d":  {"name": "Lenda (7 Dias)",    "price": 140, "tier": "lenda", "days": 7},
}

def get_benefits_text(tier_key: str) -> str:
    """Gera um texto bonito com as vantagens do tier."""
    data = PREMIUM_TIERS.get(tier_key, {}).get("perks", {})
    if not data: return "Sem benefícios."

    lines = []
    
    # Auto Caça
    if data.get("auto_hunt"):
        lines.append("🤖 <b>Auto Caça:</b> Liberado")
    
    # Viagem (Novo)
    travel_mult = data.get("travel_time_multiplier", 1.0)
    if travel_mult == 0.0:
        lines.append("🚀 <b>Viagem:</b> Instantânea")
    
    # Coleta
    gather_speed = data.get("gather_speed_multiplier", 1.0)
    gather_cost = data.get("gather_energy_cost", 1)
    
    if gather_speed > 1.0:
        lines.append(f"⚡️ <b>Coleta:</b> {gather_speed}x mais rápida")
    
    if gather_cost == 0:
        lines.append("🌿 <b>Coleta:</b> Energia ZERO") # Ícone diferenciado

    # Multiplicadores
    xp = int((data.get("xp_multiplier", 1.0) - 1) * 100)
    gold = int((data.get("gold_multiplier", 1.0) - 1) * 100)
    refine = int((data.get("refine_speed_multiplier", 1.0) - 1) * 100)
    
    if xp > 0: lines.append(f"📈 <b>XP:</b> +{xp}%")
    if gold > 0: lines.append(f"💰 <b>Ouro:</b> +{gold}%")
    if refine > 0: lines.append(f"⚒ <b>Refino:</b> +{refine}% Vel.")
    
    # Energia
    bonus_e = data.get("max_energy_bonus", 0)
    regen_s = data.get("energy_regen_seconds", 420)
    
    if bonus_e > 0: 
        base = 20
        lines.append(f"💚 <b>Energia Máx:</b> +{bonus_e} ({base}→{base+bonus_e})")
    
    # Exibir Regen de forma amigável
    if regen_s < 420:
        regen_min = regen_s // 60
        lines.append(f"⏳ <b>Regen:</b> 1 a cada {regen_min} min")

    return "\n".join(lines)
