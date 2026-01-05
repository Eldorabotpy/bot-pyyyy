# modules/player/premium.py
# (VERSÃO COMPLETA: Config + Classe Manager)

from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# =================================================================
# CONFIGURAÇÕES (PREMIUM TIERS)
# =================================================================
HUNT_ENERGY_COST = 1
COLLECTION_TIME_MINUTES = 1
ELITE_CHANCE = 0.20

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
            "travel_time_multiplier": 0.0,
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
            "travel_time_multiplier": 0.0,
            "gather_speed_multiplier": 2.0,
            "gather_energy_cost": 1,
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
            "travel_time_multiplier": 0.0,
            "gather_speed_multiplier": 2.5,
            "gather_energy_cost": 0,
            "hunt_energy_cost": 1,
        }
    }
}

PREMIUM_PLANS_FOR_SALE = {
    "premium_30d": {"name": "Premium (30 Dias)", "price": 120, "tier": "premium", "days": 30},
    "premium_15d": {"name": "Premium (15 Dias)", "price": 70,  "tier": "premium", "days": 15},
    "premium_7d":  {"name": "Premium (7 Dias)",  "price": 35,  "tier": "premium", "days": 7},
    "vip_30d":     {"name": "VIP (30 Dias)",     "price": 300, "tier": "vip", "days": 30},
    "vip_15d":     {"name": "VIP (15 Dias)",     "price": 160, "tier": "vip", "days": 15},
    "vip_7d":      {"name": "VIP (7 Dias)",      "price": 80,  "tier": "vip", "days": 7},
    "lenda_30d":   {"name": "Lenda (30 Dias)",   "price": 500, "tier": "lenda", "days": 30},
    "lenda_15d":   {"name": "Lenda (15 Dias)",   "price": 270, "tier": "lenda", "days": 15},
    "lenda_7d":    {"name": "Lenda (7 Dias)",    "price": 140, "tier": "lenda", "days": 7},
}

def get_benefits_text(tier_key: str) -> str:
    data = PREMIUM_TIERS.get(tier_key, {}).get("perks", {})
    if not data: return "Sem benefícios."
    lines = []
    if data.get("auto_hunt"): lines.append("🤖 <b>Auto Caça:</b> Liberado")
    travel_mult = data.get("travel_time_multiplier", 1.0)
    if travel_mult == 0.0: lines.append("🚀 <b>Viagem:</b> Instantânea")
    gather_speed = data.get("gather_speed_multiplier", 1.0)
    gather_cost = data.get("gather_energy_cost", 1)
    if gather_speed > 1.0: lines.append(f"⚡️ <b>Coleta:</b> {gather_speed}x mais rápida")
    if gather_cost == 0: lines.append("🌿 <b>Coleta:</b> Energia ZERO")
    xp = int((data.get("xp_multiplier", 1.0) - 1) * 100)
    if xp > 0: lines.append(f"📈 <b>XP:</b> +{xp}%")
    bonus_e = data.get("max_energy_bonus", 0)
    if bonus_e > 0: lines.append(f"💚 <b>Energia Máx:</b> +{bonus_e}")
    return "\n".join(lines)

# =================================================================
# CLASSE DE GERENCIAMENTO (CRÍTICO PARA JOBS.PY)
# =================================================================
class PremiumManager:
    def __init__(self, player_data: dict):
        self.player_data = player_data
        self.tier_key = player_data.get("premium_tier", "free")
        self.tier_data = PREMIUM_TIERS.get(self.tier_key, PREMIUM_TIERS["free"])
        self.perks = self.tier_data.get("perks", {})

    @property
    def expiration_date(self):
        """Retorna objeto datetime (UTC) ou None."""
        exp_str = self.player_data.get("premium_expires_at")
        if not exp_str: return None
        try:
            dt = datetime.fromisoformat(exp_str)
            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except: return None

    def is_premium(self) -> bool:
        """Verifica se é Premium e se a data ainda é válida."""
        if self.tier_key == "free": return False
        
        # Se não tem data, mas tem tier definido => Estado Inválido (downgrade seguro)
        if not self.player_data.get("premium_expires_at"):
            return False

        exp = self.expiration_date
        now = datetime.now(timezone.utc)
        
        if exp and now < exp:
            return True
        return False

    def get_perk_value(self, perk_key: str, default=0):
        return self.perks.get(perk_key, default)

    def revoke(self):
        """Remove o status premium do dicionário local."""
        self.player_data["premium_tier"] = "free"
        self.player_data["premium_expires_at"] = None