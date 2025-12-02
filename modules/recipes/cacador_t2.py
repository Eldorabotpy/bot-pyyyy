# -*- coding: utf-8 -*-
# ============================================================
# TIER 2: RECEITAS DO CONJUNTO DE PATRULHEIRO DO CAÇADOR (Profissão 20+)
# ============================================================

from __future__ import annotations
from typing import Dict
from modules import crafting_registry

# RARIDADE TIER 2 (comum, bom, raro, epico, lendario)
RARITY_T2 = {
    "comum": 0.90,     # Aumentei para 90% (mais lixo)
    "bom": 0.09,       # Diminuí para 9%
    "raro": 0.009,     # 0.9%
    "epico": 0.0009,   # 0.09%
    "lendario": 0.0001 # 0.01% (Extremamente raro)
}

RECIPES: Dict[str, Dict] = {
    # --- Arma de Precisão (Armeiro) ---
    "work_arco_patrulheiro_cacador": {
        "display_name": "Arco de Patrulheiro",
        "emoji": "🏹",
        "profession": "armeiro",
        "level_req": 20,
        "time_seconds": 1800,  # 30 minutos
        "xp_gain": 100,
        "inputs": {"madeira_rara": 12, "seiva_de_ent": 2, "linho": 10, "nucleo_forja_comum": 1},
        "result_base_id": "arco_patrulheiro_cacador",
        "unique": True,
        "class_req": ["cacador"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["cacador", "geral"],
        "damage_info": {"type": "perfurante", "min_damage": 38, "max_damage": 52},
    },

    # --- Armaduras de Couro Reforçado (Curtidor) ---
    "work_capuz_patrulheiro_cacador": {
        "display_name": "Capuz de Patrulheiro",
        "emoji": "🪖",
        "profession": "curtidor",
        "level_req": 20,
        "time_seconds": 1200,  # 20 minutos
        "xp_gain": 80,
        "inputs": {"couro_de_lobo_alfa": 8, "pele_de_troll": 2, "nucleo_forja_comum": 1},
        "result_base_id": "capuz_patrulheiro_cacador",
        "unique": True,
        "class_req": ["cacador"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["cacador", "geral"],
    },
    "work_peitoral_patrulheiro_cacador": {
        "display_name": "Peitoral de Patrulheiro",
        "emoji": "👕",
        "profession": "curtidor",
        "level_req": 22,
        "time_seconds": 2400,  # 40 minutos
        "xp_gain": 150,
        "inputs": {"couro_de_lobo_alfa": 15, "pele_de_troll": 5, "pena": 20, "nucleo_forja_comum": 1},
        "result_base_id": "peitoral_patrulheiro_cacador",
        "unique": True,
        "class_req": ["cacador"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["cacador", "geral"],
    },
    "work_calcas_patrulheiro_cacador": {
        "display_name": "Calças de Patrulheiro",
        "emoji": "👖",
        "profession": "curtidor",
        "level_req": 21,
        "time_seconds": 1500,  # 25 minutos
        "xp_gain": 120,
        "inputs": {"couro_de_lobo_alfa": 10, "pele_de_troll": 4, "nucleo_forja_comum": 1},
        "result_base_id": "calcas_patrulheiro_cacador",
        "unique": True,
        "class_req": ["cacador"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["cacador", "geral"],
    },
    "work_botas_patrulheiro_cacador": {
        "display_name": "Botas de Patrulheiro",
        "emoji": "🥾",
        "profession": "curtidor",
        "level_req": 20,
        "time_seconds": 900,  # 15 minutos
        "xp_gain": 70,
        "inputs": {"couro_de_lobo_alfa": 6, "pele_de_troll": 2, "nucleo_forja_comum": 1},
        "result_base_id": "botas_patrulheiro_cacador",
        "unique": True,
        "class_req": ["cacador"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["cacador", "geral"],
    },
    "work_luvas_patrulheiro_cacador": {
        "display_name": "Luvas de Patrulheiro",
        "emoji": "🧤",
        "profession": "curtidor",
        "level_req": 20,
        "time_seconds": 900,  # 15 minutos
        "xp_gain": 70,
        "inputs": {"couro_de_lobo_alfa": 6, "pele_de_troll": 2, "nucleo_forja_comum": 1},
        "result_base_id": "luvas_patrulheiro_cacador",
        "unique": True,
        "class_req": ["cacador"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["cacador", "geral"],
    },

    # --- Acessórios de Rastreio (Joalheiro) ---
    "work_anel_patrulheiro_cacador": {
        "display_name": "Anel de Patrulheiro",
        "emoji": "💍",
        "profession": "joalheiro",
        "level_req": 23,
        "time_seconds": 1380,  # ~23 minutos
        "xp_gain": 115,
        "inputs": {"couro_reforcado": 2, "gema_bruta": 1, "olho_de_basilisco": 1, "nucleo_forja_comum": 1},
        "result_base_id": "anel_patrulheiro_cacador",
        "unique": True,
        "class_req": ["cacador"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["cacador", "geral"],
    },
    "work_colar_patrulheiro_cacador": {
        "display_name": "Colar de Patrulheiro",
        "emoji": "📿",
        "profession": "joalheiro",
        "level_req": 24,
        "time_seconds": 1560,  # 26 minutos
        "xp_gain": 140,
        "inputs": {"couro_reforcado": 3, "gema_bruta": 2, "seiva_de_ent": 1, "nucleo_forja_comum": 1},
        "result_base_id": "colar_patrulheiro_cacador",
        "unique": True,
        "class_req": ["cacador"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["cacador", "geral"],
    },
    "work_brinco_patrulheiro_cacador": {
        "display_name": "Brinco de Patrulheiro",
        "emoji": "🧿",
        "profession": "joalheiro",
        "level_req": 23,
        "time_seconds": 1200,  # 20 minutos
        "xp_gain": 100,
        "inputs": {"couro_reforcado": 1, "gema_bruta": 1, "pena": 15, "nucleo_forja_comum": 1},
        "result_base_id": "brinco_patrulheiro_cacador",
        "unique": True,
        "class_req": ["cacador"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["cacador", "geral"],
    },
}

def register_all() -> None:
    """Registra todas as receitas deste pacote no registry central."""
    for rid, data in RECIPES.items():
        crafting_registry.register_recipe(rid, data)
