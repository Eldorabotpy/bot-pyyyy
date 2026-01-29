# modules/player/premium.py
# (VERSÃO FINAL: Tiers, Planos e Lógica de Expiração)

from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# =================================================================
# 1. CONFIGURAÇÕES GERAIS
# =================================================================
HUNT_ENERGY_COST = 1
COLLECTION_TIME_MINUTES = 10   # ⏳ BASE REAL DA COLETA
ELITE_CHANCE = 0.20

# =================================================================
# 2. TIERS (BENEFÍCIOS)
# =================================================================
PREMIUM_TIERS = {
    "free": {
        "display_name": "Aventureiro Comum",
        "perks": {
            "auto_hunt": False,
            "xp_multiplier": 1.0,
            "gold_multiplier": 1.0,
            "refine_speed_multiplier": 1.0,
            "craft_speed_multiplier": 1.0,
            "max_energy_bonus": 0,
            "energy_regen_seconds": 420,
            "travel_time_multiplier": 1.0,
            "gather_speed_multiplier": 1.0,
            "gather_energy_cost": 1,
            "hunt_energy_cost": 1,
            "all_stats_percent": 0,
            "bonus_luck": 0
        }
    },
    "premium": {
        "display_name": "Aventureiro Premium",
        "perks": {
            "auto_hunt": True,
            "xp_multiplier": 1.25,
            "gold_multiplier": 1.25,
            "refine_speed_multiplier": 1.25,
            "craft_speed_multiplier": 1.25,
            "max_energy_bonus": 5,
            "energy_regen_seconds": 300,
            "travel_time_multiplier": 0.0,
            "gather_speed_multiplier": 1.5,
            "gather_energy_cost": 1,
            "hunt_energy_cost": 1,
            "all_stats_percent": 2,
            "bonus_luck": 2
        }
    },
    "vip": {
        "display_name": "Aventureiro VIP",
        "perks": {
            "auto_hunt": True,
            "xp_multiplier": 1.5,
            "gold_multiplier": 1.5,
            "refine_speed_multiplier": 1.5,
            "craft_speed_multiplier": 1.5,
            "max_energy_bonus": 10,
            "energy_regen_seconds": 180,
            "travel_time_multiplier": 0.0,
            "gather_speed_multiplier": 2.0,
            "gather_energy_cost": 1,
            "hunt_energy_cost": 1,
            "all_stats_percent": 5,
            "bonus_luck": 5
        }
    },
    "lenda": {
        "display_name": "Aventureiro Lenda",
        "perks": {
            "auto_hunt": True,
            "xp_multiplier": 1.75,
            "gold_multiplier": 1.75,
            "refine_speed_multiplier": 2.0,
            "craft_speed_multiplier": 2.0,
            "max_energy_bonus": 20,
            "energy_regen_seconds": 120,
            "travel_time_multiplier": 0.0,
            "gather_speed_multiplier": 3.0,
            "gather_energy_cost": 0,  # 🌿 coleta grátis
            "hunt_energy_cost": 1,
            "all_stats_percent": 10,
            "bonus_luck": 10
        }
    }
}

# =================================================================
# 3. FUNÇÕES DE TEXTO (UI)
# =================================================================
def get_benefits_text(tier_key: str) -> str:
    data = PREMIUM_TIERS.get(tier_key, {}).get("perks", {})
    if not data:
        return "Sem benefícios."

    lines = []

    if data.get("auto_hunt"):
        lines.append("🤖 <b>Auto Caça:</b> Liberado")

    if data.get("travel_time_multiplier") == 0.0:
        lines.append("🚀 <b>Viagem:</b> Instantânea")

    g_speed = data.get("gather_speed_multiplier", 1.0)
    g_cost = data.get("gather_energy_cost", 1)
    if g_speed > 1.0:
        lines.append(f"⚡ <b>Coleta:</b> {g_speed}x mais rápida")
    if g_cost == 0:
        lines.append("🌿 <b>Coleta:</b> Energia ZERO")

    xp = int((data.get("xp_multiplier", 1.0) - 1) * 100)
    if xp > 0:
        lines.append(f"📈 <b>XP:</b> +{xp}%")

    gold = int((data.get("gold_multiplier", 1.0) - 1) * 100)
    if gold > 0:
        lines.append(f"💰 <b>Ouro:</b> +{gold}%")

    stats = data.get("all_stats_percent", 0)
    if stats > 0:
        lines.append(f"💪 <b>Status Base:</b> +{stats}%")

    max_e = data.get("max_energy_bonus", 0)
    if max_e > 0:
        lines.append(f"💚 <b>Energia Máx:</b> +{max_e}")

    regen = data.get("energy_regen_seconds", 420)
    if regen < 420:
        lines.append(f"🔋 <b>Regen:</b> 1 a cada {regen/60:.1f} min")

    return "\n".join(lines)

# =================================================================
# 4. CLASSE GERENCIADORA
# =================================================================
class PremiumManager:
    def __init__(self, player_data: dict):
        self.player_data = player_data
        self.tier_key = player_data.get("premium_tier", "free")
        self.tier_data = PREMIUM_TIERS.get(self.tier_key, PREMIUM_TIERS["free"])
        self.perks = self.tier_data.get("perks", {})

    @property
    def expiration_date(self):
        exp_str = self.player_data.get("premium_expires_at")
        if not exp_str:
            return None
        try:
            # aceita "...Z"
            dt = datetime.fromisoformat(str(exp_str).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None

    def is_premium(self) -> bool:
        if self.tier_key == "free":
            return False

        exp = self.expiration_date
        if not exp:
            return False

        return datetime.now(timezone.utc) < exp

    def get_perk_value(self, perk_key: str, default=0):
        return self.perks.get(perk_key, default)

    def revoke(self):
        self.player_data["premium_tier"] = "free"
        self.player_data["premium_expires_at"] = None

# =================================================================
# 5. ⏳ TEMPO DE COLETA (USADO PELO collect_callback)
# =================================================================
def get_collection_duration_seconds(player_data: dict) -> int:
    """
    Calcula a duração da coleta em segundos.
    Base: COLLECTION_TIME_MINUTES (10 min)
    Redução via perk: gather_speed_multiplier
    """
    try:
        base_minutes = int(COLLECTION_TIME_MINUTES)
    except Exception:
        base_minutes = 10

    base_seconds = max(60, base_minutes * 60)

    prem = PremiumManager(player_data)
    mult = prem.get_perk_value("gather_speed_multiplier", 1.0)

    try:
        mult = float(mult)
    except Exception:
        mult = 1.0

    if mult <= 0:
        mult = 1.0

    duration = int(base_seconds / mult)

    # piso de segurança
    return max(10, duration)
