# modules/game_data/runes_data.py

# ==============================================================================
# BANCO DE DADOS DE RUNAS DE ELDORA
# ==============================================================================
# Estrutura:
# Chave única -> { Nome, Emoji, Tier (1-3), Tipo de Efeito, Valor, Descrição }

RUNES_DB = {
    # ------------------------------------------------------------------
    # FAMÍLIA DA OFENSIVA (Vermelho) - Foco: Assassino, Berserker, Caçador
    # ------------------------------------------------------------------
    "runa_crueldade_menor": {
        "name": "Runa da Crueldade Menor", "emoji": "☠️", "tier": 1,
        "stat_key": "crit_damage_mult", "value": 5, "type": "percent",
        "desc": "+5% de Dano Crítico"
    },
    "runa_crueldade_maior": {
        "name": "Runa da Crueldade Maior", "emoji": "☠️", "tier": 2,
        "stat_key": "crit_damage_mult", "value": 10, "type": "percent",
        "desc": "+10% de Dano Crítico"
    },
    "runa_crueldade_ancestral": {
        "name": "Runa da Crueldade Ancestral", "emoji": "🏴‍☠️", "tier": 3,
        "stat_key": "crit_damage_mult", "value": 20, "type": "percent",
        "desc": "+20% de Dano Crítico"
    },

    "runa_precisao_menor": {
        "name": "Runa da Precisão Menor", "emoji": "🎯", "tier": 1,
        "stat_key": "crit_chance_flat", "value": 2, "type": "flat",
        "desc": "+2% de Chance Crítica"
    },
    "runa_precisao_ancestral": {
        "name": "Runa da Precisão Ancestral", "emoji": "🎯", "tier": 3,
        "stat_key": "crit_chance_flat", "value": 6, "type": "flat",
        "desc": "+6% de Chance Crítica"
    },

    # ------------------------------------------------------------------
    # FAMÍLIA DA SUSTENTAÇÃO (Verde) - Foco: Guerreiro, Monge, Berserker
    # ------------------------------------------------------------------
    "runa_vampiro_menor": {
        "name": "Runa do Vampiro Menor", "emoji": "🩸", "tier": 1,
        "stat_key": "lifesteal", "value": 1, "type": "percent",
        "desc": "Rouba 1% do dano causado como Vida"
    },
    "runa_vampiro_maior": {
        "name": "Runa do Vampiro Maior", "emoji": "🩸", "tier": 2,
        "stat_key": "lifesteal", "value": 3, "type": "percent",
        "desc": "Rouba 3% do dano causado como Vida"
    },
    "runa_vampiro_ancestral": {
        "name": "Runa do Vampiro Ancestral", "emoji": "🧛", "tier": 3,
        "stat_key": "lifesteal", "value": 5, "type": "percent",
        "desc": "Rouba 5% do dano causado como Vida"
    },

    "runa_rocha_menor": {
        "name": "Runa da Rocha Menor", "emoji": "🛡️", "tier": 1,
        "stat_key": "defesa_fisica", "value": 3, "type": "flat",
        "desc": "+3 de Defesa Física Base"
    },
    
    # ------------------------------------------------------------------
    # FAMÍLIA MÍSTICA (Azul) - Foco: Mago, Bardo, Curandeiro
    # ------------------------------------------------------------------
    "runa_mente_menor": {
        "name": "Runa da Mente Menor", "emoji": "🧠", "tier": 1,
        "stat_key": "max_mana", "value": 10, "type": "flat",
        "desc": "+10 de Mana Máxima"
    },
    "runa_eco_menor": {
        "name": "Runa do Eco Menor", "emoji": "🔊", "tier": 1,
        "stat_key": "magic_attack", "value": 2, "type": "flat",
        "desc": "+2 de Poder Mágico"
    },
    "runa_eco_ancestral": {
        "name": "Runa do Eco Ancestral", "emoji": "🔮", "tier": 3,
        "stat_key": "magic_attack", "value": 8, "type": "flat",
        "desc": "+8 de Poder Mágico"
    },

    # ------------------------------------------------------------------
    # FAMÍLIA DA PROSPERIDADE (Amarelo) - Farm
    # ------------------------------------------------------------------
    "runa_midas_menor": {
        "name": "Runa de Midas Menor", "emoji": "💰", "tier": 1,
        "stat_key": "gold_multiplier", "value": 5, "type": "percent",
        "desc": "+5% de Ouro obtido"
    },
    "runa_sabio_menor": {
        "name": "Runa do Sábio Menor", "emoji": "📜", "tier": 1,
        "stat_key": "xp_multiplier", "value": 3, "type": "percent",
        "desc": "+3% de XP obtido"
    },
}

def get_rune_info(rune_id: str) -> dict:
    return RUNES_DB.get(rune_id, {})

def get_runes_by_tier(tier: int) -> list:
    return [rid for rid, data in RUNES_DB.items() if data.get("tier") == tier]
from modules.game_data.rune_rules import complete_catalog
complete_catalog(RUNES_DB)
