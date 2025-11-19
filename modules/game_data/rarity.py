# modules/game_data/rarity.py

from typing import Dict, List

BASE_STATS_BY_RARITY = {
    # slots com primary fixo
    "elmo":      {"vida":      {"comum":[3,5],  "bom":[5,8],  "raro":[8,12],  "epico":[12,16], "lendario":[16,22]}},
    "armadura":  {"vida":      {"comum":[6,9],  "bom":[9,13], "raro":[13,18], "epico":[18,24], "lendario":[24,32]}},
    "calca":     {"vida":      {"comum":[4,6],  "bom":[6,9],  "raro":[9,13],  "epico":[13,18], "lendario":[18,24]}},
    "colar":     {"vida":      {"comum":[2,4],  "bom":[4,6],  "raro":[6,9],   "epico":[9,12],  "lendario":[12,16]}},
    "botas":     {"agilidade": {"comum":[1,2],  "bom":[2,3],  "raro":[3,5],   "epico":[5,7],   "lendario":[7,10]}},
    "luvas":     {"sorte":     {"comum":[1,2],  "bom":[2,3],  "raro":[3,4],   "epico":[4,6],   "lendario":[6,8]}},

    # slots com atributo primário de classe
    "arma":      {"__class_primary__": {"comum":[2,4], "bom":[4,6], "raro":[6,9], "epico":[9,12], "lendario":[12,16]}},
    "anel":      {"__class_primary__": {"comum":[1,2], "bom":[2,3], "raro":[3,5], "epico":[5,7],  "lendario":[7,10]}},
    "brinco":    {"__class_primary__": {"comum":[1,2], "bom":[2,3], "raro":[3,5], "epico":[5,7],  "lendario":[7,10]}},
}

RARITY_DATA = {
    "comum":    {"name": "Comum",    "emoji": "⚪", "tier": 1, "bonus_stats": 0},
    "bom":      {"name": "Bom",      "emoji": "🟢", "tier": 1, "bonus_stats": 1},
    "raro":     {"name": "Raro",     "emoji": "🔵", "tier": 1, "bonus_stats": 2},
    "epico":    {"name": "Épico",    "emoji": "🟣", "tier": 1, "bonus_stats": 3},
    "lendario": {"name": "Lendário", "emoji": "🟡", "tier": 1, "bonus_stats": 4},
}

# Quantos atributos cada raridade deve ter (inclui o primário)
ATTR_COUNT_BY_RARITY = {
    "comum": 1,
    "bom": 2,
    "raro": 3,
    "epico": 4,
    "lendario": 5,
}

# Teto de aprimoramento por raridade
UPGRADE_CAP_BY_RARITY = {
    "comum": 20,
    "bom": 25,
    "raro": 30,
    "epico": 35,
    "lendario": 40,
}

# modules/game_data/rarity.py

# =====================================================
# POOLS DE ATRIBUTOS SECUNDÁRIOS (AFFIXES)
# Usados pelo crafting_engine para sortear atributos secundários.
# =====================================================

AFFIX_POOLS: Dict[str, List[str]] = {
    # Pool Geral (Usado por todas as classes)
    "geral": [
        "vida", "defesa", "iniciativa", "sorte", "tenacidade", "agilidade"
    ],
    
    # Pool Mágico/Arcano (Para Mago, Bardo, Curandeiro)
    "magico_arcano": [
        "inteligencia", "mana", "magic_attack", "magic_penetration", "cooldown_reduction"
    ],
    
    # Pool Físico/Guerreiro (Para Guerreiro, Samurai)
    "fisico_defensivo": [
        "forca", "defesa_fisica", "max_hp", "tenacidade"
    ],
    
    # Pool Agilidade/Letalidade (Para Caçador, Assassino)
    "agilidade_letal": [
        "crit_chance_flat", "crit_damage_mult", "armor_penetration", "lifesteal"
    ],

    # --- Pools de Classes Específicas (Opcional) ---
    "guerreiro": ["vida", "defesa_fisica", "max_hp", "tenacidade", "block_chance"],
    "berserker": ["furia", "crit_damage_mult", "lifesteal", "attack_speed"],
    "mago":      ["inteligencia", "magic_attack", "max_mana", "magic_penetration"],
    "cacador":   ["crit_chance_flat", "armor_penetration", "agilidade"],
    "monge":     ["foco", "dodge_chance_flat", "tenacidade"],
    "assassino": ["letalidade", "crit_chance_flat", "armor_penetration"],
    "bardo":     ["carisma", "cooldown_reduction", "max_mana"],
    "samurai":   ["bushido", "block_chance", "parry_chance"],
    "curandeiro": ["fe", "heal_potency", "magic_resist"]
}
