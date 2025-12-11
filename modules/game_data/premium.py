# modules/game_data/premium.py

PREMIUM_TIERS = {
    "free": {
        "display_name": "Aventureiro Comum",
        "perks": {
            "auto_hunt": False,
            "xp_multiplier": 1.0,
            "gold_multiplier": 1.0,
            "refine_speed_multiplier": 1.0, # Normal
            "max_energy_bonus": 0,
            "energy_regen_seconds": 420, # 7 min
            "travel_time_multiplier": 1.0,
            "gather_speed_multiplier": 1.0,
            "gather_energy_cost": 1,
        }
    },
    "premium": {
        "display_name": "Aventureiro Premium",
        "perks": {
            "auto_hunt": True,
            "xp_multiplier": 1.25,      # 1.25x XP
            "gold_multiplier": 1.25,    # 1.25x Ouro
            "refine_speed_multiplier": 1.25, # 25% mais rápido
            "max_energy_bonus": 5,      # Total 25
            "energy_regen_seconds": 300, # 5 min
            "travel_time_multiplier": 0.0,
            "gather_speed_multiplier": 1.5, # 1.5x Coleta
            "gather_energy_cost": 1,
        }
    },
    "vip": {
        "display_name": "Aventureiro VIP",
        "perks": {
            "auto_hunt": True,
            "xp_multiplier": 1.5,       # 1.5x XP
            "gold_multiplier": 1.5,     # 1.5x Ouro
            "refine_speed_multiplier": 1.5, # 50% mais rápido
            "max_energy_bonus": 10,     # Total 30
            "energy_regen_seconds": 180, # 3 min
            "travel_time_multiplier": 0.0,
            "gather_speed_multiplier": 2.0, # 2x Coleta
            "gather_energy_cost": 0,    # Coleta grátis? (No texto dizia custo 0)
        }
    },
    "lenda": {
        "display_name": "Aventureiro Lenda",
        "perks": {
            "auto_hunt": True,
            "xp_multiplier": 1.75,      # 1.75x XP
            "gold_multiplier": 1.5,     # 1.5x Ouro
            "refine_speed_multiplier": 2.0, # 2x mais rápido (100%)
            "max_energy_bonus": 15,     # Total 35 (Base 20 + 15)
            "energy_regen_seconds": 120, # 2 min
            "travel_time_multiplier": 0.0,
            "gather_speed_multiplier": 2.5, # 2.5x Coleta
            "gather_energy_cost": 0,    # Coleta sem gastar energia
        }
    }
}

# =================================================================
# PLANOS E PREÇOS (AJUSTADOS PARA A ECONOMIA DO JOGO)
# =================================================================
PREMIUM_PLANS_FOR_SALE = {
    # --- PREMIUM (~R$ 20,00) ---
    "premium_30d": {
        "name": "Premium (30 Dias)", 
        "price": 120, # Exatamente o pacote Básico
        "tier": "premium", 
        "days": 30
    },
    "premium_15d": {
        "name": "Premium (15 Dias)", 
        "price": 70, 
        "tier": "premium", 
        "days": 15
    },
    "premium_7d":  {
        "name": "Premium (7 Dias)",  
        "price": 35, 
        "tier": "premium", 
        "days": 7
    },
    
    # --- VIP (~R$ 40,00) ---
    "vip_30d": {
        "name": "VIP (30 Dias)",     
        "price": 300, # Aprox R$ 40~42
        "tier": "vip", 
        "days": 30
    },
    "vip_15d": {
        "name": "VIP (15 Dias)",     
        "price": 160, 
        "tier": "vip", 
        "days": 15
    },
    "vip_7d": {
        "name": "VIP (7 Dias)",      
        "price": 80,  
        "tier": "vip", 
        "days": 7
    },

    # --- LENDA (~R$ 65,00) ---
    "lenda_30d": {
        "name": "Lenda (30 Dias)",   
        "price": 500, # Aprox R$ 65,00
        "tier": "lenda", 
        "days": 30
    },
    "lenda_15d": {
        "name": "Lenda (15 Dias)",   
        "price": 270, 
        "tier": "lenda", 
        "days": 15
    },
    "lenda_7d": {
        "name": "Lenda (7 Dias)",    
        "price": 140, 
        "tier": "lenda", 
        "days": 7
    },
}

def get_benefits_text(tier_key: str) -> str:
    """Gera um texto bonito com as vantagens do tier."""
    data = PREMIUM_TIERS.get(tier_key, {}).get("perks", {})
    if not data: return "Sem benefícios."

    lines = []
    
    # Auto Caça
    if data.get("auto_hunt"):
        lines.append("🤖 <b>Auto Caça:</b> Liberado")
    
    # Coleta
    gather_speed = data.get("gather_speed_multiplier", 1.0)
    gather_cost = data.get("gather_energy_cost", 1)
    if gather_speed > 1.0:
        lines.append(f"⚡️ <b>Coleta:</b> {gather_speed}x mais rápida")
    if gather_cost == 0:
        lines.append("💥 <b>Coleta:</b> Energia ZERO")

    # Multiplicadores
    xp = int((data.get("xp_multiplier", 1.0) - 1) * 100)
    gold = int((data.get("gold_multiplier", 1.0) - 1) * 100)
    refine = int((data.get("refine_speed_multiplier", 1.0) - 1) * 100)
    
    if xp > 0: lines.append(f"📈 <b>XP:</b> +{xp}%")
    if gold > 0: lines.append(f"💰 <b>Ouro:</b> +{gold}%")
    if refine > 0: lines.append(f"⚒ <b>Refino:</b> +{refine}% Vel.")
    
    # Energia
    bonus_e = data.get("max_energy_bonus", 0)
    
    if bonus_e > 0: 
        base = 20
        lines.append(f"💚 <b>Energia Máx:</b> +{bonus_e} ({base}→{base+bonus_e})")

    return "\n".join(lines)