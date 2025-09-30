# modules/game_data/regions.py
# modules/game_data/regions.py

from __future__ import annotations
from typing import Dict, Any

# Presets globais (podem ser usados por várias regiões)
DIFFICULTY_PRESETS: Dict[str, dict] = {
    "facil":     {"hp": 0.90, "attack": 0.90, "defense": 0.90, "initiative": 1.00, "luck": 1.00, "xp": 0.9, "gold": 0.9, "drop": 0.95, "flee_bias": +0.05},
    "normal":    {"hp": 1.00, "attack": 1.00, "defense": 1.00, "initiative": 1.00, "luck": 1.00, "xp": 1.0, "gold": 1.0, "drop": 1.00, "flee_bias": 0.00},
    "dificil":   {"hp": 1.25, "attack": 1.25, "defense": 1.15, "initiative": 1.05, "luck": 1.05, "xp": 1.2, "gold": 1.2, "drop": 1.10, "flee_bias": -0.05},
    "pesadelo":  {"hp": 1.55, "attack": 1.45, "defense": 1.30, "initiative": 1.10, "luck": 1.10, "xp": 1.4, "gold": 1.35, "drop": 1.15, "flee_bias": -0.08},
    "lenda":     {"hp": 1.95, "attack": 1.70, "defense": 1.45, "initiative": 1.15, "luck": 1.15, "xp": 1.7, "gold": 1.6,  "drop": 1.20, "flee_bias": -0.12},
}

# Definição de regiões
REGIONS: Dict[str, dict] = {
    # id_da_regiao: {nivel_base (faixa), dificuldade, preset opcional, mods extras por região}
    "pradaria_inicial": {
        "display": "Pradaria Inicial",
        "level_range": (1, 10),        # pensado pra jogadores 1–10
        "difficulty": "normal",        # usa DIFFICULTY_PRESETS["normal"]
        "mods": {"xp": 0.95, "gold": 0.95},  # “sabor” da região
        "encounter_tier": 1,           # usado no scaling (opcional)
    },
    "floresta_sombria": {
        "display": "Floresta Sombria",
        "level_range": (6, 20),
        "difficulty": "dificil",
        "mods": {"drop": 1.08},
        "encounter_tier": 2,
    },
    "picos_gelados": {
        "display": "Picos Gelados",
        "level_range": (15, 35),
        "difficulty": "pesadelo",
        "mods": {"initiative": 1.05},
        "encounter_tier": 3,
    },
    "deserto_ancestral": {
        "display": "Deserto Ancestral",
        "level_range": (30, 60),
        "difficulty": "lenda",
        "mods": {},
        "encounter_tier": 4,
    },
}

def get_region_profile(region_id: str) -> dict:
    r = REGIONS.get(region_id, {})
    preset = DIFFICULTY_PRESETS.get(r.get("difficulty", "normal"), DIFFICULTY_PRESETS["normal"])
    mods = dict(preset)
    # aplica pequenos ajustes específicos da região
    for k, v in (r.get("mods") or {}).items():
        # multiplicadores “stackáveis” (numéricos)
        if isinstance(v, (int, float)) and isinstance(mods.get(k), (int, float)):
            mods[k] = float(mods[k]) * float(v)
        else:
            mods[k] = v
    # metadata útil
    mods["_display"] = r.get("display", region_id)
    mods["_range"] = r.get("level_range", (1, 999))
    mods["_tier"] = int(r.get("encounter_tier", 1))
    mods["_difficulty"] = r.get("difficulty", "normal")
    return mods

REGIONS_DATA = {
    'reino_eldora':     {'display_name': 'Reino de Eldora',      'resource': None,     'emoji': '🏰', 'file_id_name': 'regiao_reino_eldora'},
    'floresta_sombria': {'display_name': 'Floresta Sombria',     'resource': 'madeira','emoji': '🌳', 'file_id_name': 'regiao_floresta_sombria', 'ambush_chance': 0.20},
    'pedreira_granito': {'display_name': 'Pedreira de Granito',  'resource': 'pedra',  'emoji': '🪨', 'file_id_name': 'regiao_pedreira_granito'},
    'campos_linho':     {'display_name': 'Campos de Linho',      'resource': 'linho',  'emoji': '🌾', 'file_id_name': 'regiao_campos_linho'},
    'pico_grifo':       {'display_name': 'Pico do Grifo',        'resource': 'pena',   'emoji': '🦅', 'file_id_name': 'regiao_pico_grifo', 'ambush_chance': 0.25},
    'mina_ferro':       {'display_name': 'Mina de Ferro',        'resource': 'ferro',  'emoji': '⛏️', 'file_id_name': 'regiao_mina_ferro'},
    'forja_abandonada': {'display_name': 'Forja Abandonada',     'resource': None,     'emoji': '🔥', 'file_id_name': 'regiao_forja_abandonada'},
    'pantano_maldito':  {'display_name': 'Pântano Maldito',      'resource': 'sangue', 'emoji': '🩸', 'file_id_name': 'regiao_pantano_maldito', 'ambush_chance': 0.30},
}

REGION_TARGET_POWER = {
    "floresta_sombria": 80,
    "pedreira_granito": 130,
    "campos_linho": 180,
    "pico_grifo": 240,
    "mina_ferro": 260,
    "forja_abandonada": 300,
    "pantano_maldito": 330,
}

REGION_SCALING_ENABLED = {
    "floresta_sombria": True,
    "pedreira_granito": True,
    "campos_linho": True,
    "pico_grifo": True,
    "mina_ferro": True,
    "forja_abandonada": True,
    "pantano_maldito": True,
}
