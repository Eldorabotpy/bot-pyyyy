# modules/player/premium.py
# (VERSÃO FINAL: Tiers, Planos e Lógica de Expiração)

from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# =================================================================
# 1. CONFIGURAÇÕES GERAIS
# =================================================================
HUNT_ENERGY_COST = 1
COLLECTION_TIME_MINUTES = 1
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
            "energy_regen_seconds": 420,  # 7 Minutos
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
            "energy_regen_seconds": 300,  # 5 Minutos
            "travel_time_multiplier": 0.0,  # Viagem Instantânea
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
            "energy_regen_seconds": 180,  # 3 Minutos
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
            "energy_regen_seconds": 120,  # 2 Minutos
            "travel_time_multiplier": 0.0,
            "gather_speed_multiplier": 3.0,
            "gather_energy_cost": 0,       # Coleta Grátis
            "hunt_energy_cost": 1,
            "all_stats_percent": 10,
            "bonus_luck": 10
        }
    }
}

# =================================================================
# 3. PLANOS À VENDA (CONFIGURAÇÃO DA LOJA)
# =================================================================
# O sistema de loja usará este dicionário para listar opções.
PREMIUM_PLANS_FOR_SALE = {
    # --- PREMIUM ---
    "premium_30d": {
        "name": "Premium (30 Dias)", 
        "price": 1500,  # Preço em Gemas (exemplo)
        "tier": "premium", 
        "days": 30
    },
    "premium_7d": {
        "name": "Premium (7 Dias)", 
        "price": 400, 
        "tier": "premium", 
        "days": 7
    },
    
    # --- VIP ---
    "vip_30d": {
        "name": "VIP (30 Dias)", 
        "price": 3500, 
        "tier": "vip", 
        "days": 30
    },
    
    # --- LENDA ---
    "lenda_30d": {
        "name": "Lenda (30 Dias)", 
        "price": 7000, 
        "tier": "lenda", 
        "days": 30
    },
}

def get_benefits_text(tier_key: str) -> str:
    """Gera texto visual dos benefícios para menus."""
    data = PREMIUM_TIERS.get(tier_key, {}).get("perks", {})
    if not data: return "Sem benefícios."
    
    lines = []
    if data.get("auto_hunt"): lines.append("🤖 <b>Auto Caça:</b> Liberado")
    
    travel_mult = data.get("travel_time_multiplier", 1.0)
    if travel_mult == 0.0: lines.append("🚀 <b>Viagem:</b> Instantânea")
    
    gather_speed = data.get("gather_speed_multiplier", 1.0)
    gather_cost = data.get("gather_energy_cost", 1)
    if gather_speed > 1.0: lines.append(f"⚡️ <b>Coleta:</b> {gather_speed}x Veloz")
    if gather_cost == 0: lines.append("🌿 <b>Coleta:</b> Energia ZERO")
    
    xp = int((data.get("xp_multiplier", 1.0) - 1) * 100)
    if xp > 0: lines.append(f"📈 <b>XP:</b> +{xp}%")
    
    gold = int((data.get("gold_multiplier", 1.0) - 1) * 100)
    if gold > 0: lines.append(f"💰 <b>Ouro:</b> +{gold}%")

    stats = data.get("all_stats_percent", 0)
    if stats > 0: lines.append(f"💪 <b>Status Base:</b> +{stats}%")
    
    bonus_e = data.get("max_energy_bonus", 0)
    if bonus_e > 0: lines.append(f"💚 <b>Energia Máx:</b> +{bonus_e}")
    
    regen = data.get("energy_regen_seconds", 420)
    regen_min = regen / 60
    if regen < 420: lines.append(f"🔋 <b>Regen:</b> 1 a cada {regen_min:.1f} min")

    return "\n".join(lines)

# =================================================================
# 4. CLASSE GERENCIADORA
# =================================================================
class PremiumManager:
    """
    Gerencia a lógica de Premium sobre o dicionário de dados do jogador.
    Esta classe não acessa banco de dados, apenas processa o dicionário.
    """
    def __init__(self, player_data: dict):
        self.player_data = player_data
        self.tier_key = player_data.get("premium_tier", "free")
        # Fallback seguro se o tier salvo não existir mais na config
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
        """
        Verifica se é Premium e se a data ainda é válida.
        """
        if self.tier_key == "free": return False
        
        # Se tem tier mas não tem data, considera inválido/expirado
        if not self.player_data.get("premium_expires_at"):
            return False

        exp = self.expiration_date
        now = datetime.now(timezone.utc)
        
        # Verifica se ainda não venceu
        if exp and now < exp:
            return True
            
        return False

    def get_perk_value(self, perk_key: str, default=0):
        """Retorna o valor de um benefício específico do tier atual."""
        return self.perks.get(perk_key, default)

    def revoke(self):
        """
        Rebaixa o jogador para 'free' no dicionário local.
        Nota: O código que chamar isso deve salvar o pdata no banco.
        """
        self.player_data["premium_tier"] = "free"
        self.player_data["premium_expires_at"] = None