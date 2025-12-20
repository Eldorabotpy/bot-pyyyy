# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict
from modules import crafting_registry

RARITY_T2 = {
    "comum": 0.90,     # Aumentei para 90% (mais lixo)
    "bom": 0.09,       # Diminuí para 9%
    "raro": 0.009,     # 0.9%
    "epico": 0.0009,   # 0.09%
    "lendario": 0.0001 # 0.01% (Extremamente raro)
}

# TIER 2: RECEITAS DO CONJUNTO DA SOMBRA DO ASSASSINO (Nível de Profissão 20+)
# ============================================================================

RECIPES: Dict[str, Dict] = {
    # --- Arma Sombria (Armeiro) ---
    "work_adaga_sombra_assassino": {
        "display_name": "Adaga da Sombra",
        "emoji": "🔪",
        "profession": "armeiro",
        "level_req": 20,
        "time_seconds": 1500,  # 25 minutos
        "xp_gain": 95,
        "inputs": {"barra_de_aco": 8, "ectoplasma": 5, "olho_de_basilisco": 1, "nucleo_forja_comum": 1},
        "result_base_id": "adaga_sombra_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["assassino", "geral"],
        "damage_info": {"type": "perfurante", "min_damage": 45, "max_damage": 48},
    },

    # --- Armadura da Sombra (Curtidor) ---
    "work_mascara_sombra_assassino": {
        "display_name": "Máscara da Sombra",
        "emoji": "🪖",
        "profession": "curtidor",
        "level_req": 20,
        "time_seconds": 1200,
        "xp_gain": 80,
        "inputs": {"pele_de_troll": 4, "ectoplasma": 3, "nucleo_forja_comum": 1},
        "result_base_id": "mascara_sombra_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["assassino", "geral"],
    },
    "work_couraça_sombra_assassino": {
        "display_name": "Couraça da Sombra",
        "emoji": "👕",
        "profession": "curtidor",
        "level_req": 22,
        "time_seconds": 2400,
        "xp_gain": 150,
        "inputs": {"pele_de_troll": 8, "ectoplasma": 8, "nucleo_forja_comum": 1},
        "result_base_id": "couraça_sombra_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["assassino", "geral"],
    },
    "work_calcas_sombra_assassino": {
        "display_name": "Calças da Sombra",
        "emoji": "👖",
        "profession": "curtidor",
        "level_req": 21,
        "time_seconds": 1500,
        "xp_gain": 120,
        "inputs": {"pele_de_troll": 6, "ectoplasma": 5, "nucleo_forja_comum": 1},
        "result_base_id": "calcas_sombra_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["assassino", "geral"],
    },
    "work_botas_sombra_assassino": {
        "display_name": "Botas da Sombra",
        "emoji": "🥾",
        "profession": "curtidor",
        "level_req": 20,
        "time_seconds": 900,
        "xp_gain": 70,
        "inputs": {"pele_de_troll": 3, "ectoplasma": 2, "asa_de_morcego": 5, "nucleo_forja_comum": 1},
        "result_base_id": "botas_sombra_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["assassino", "geral"],
    },
    "work_luvas_sombra_assassino": {
        "display_name": "Luvas da Sombra",
        "emoji": "🧤",
        "profession": "curtidor",
        "level_req": 20,
        "time_seconds": 900,
        "xp_gain": 70,
        "inputs": {"pele_de_troll": 3, "ectoplasma": 2, "asa_de_morcego": 5, "nucleo_forja_comum": 1},
        "result_base_id": "luvas_sombra_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["assassino", "geral"],
    },

    # --- Acessórios Espectrais (Joalheiro) ---
    "work_anel_sombra_assassino": {
        "display_name": "Anel da Sombra",
        "emoji": "💍",
        "profession": "joalheiro",
        "level_req": 23,
        "time_seconds": 1380,
        "xp_gain": 115,
        "inputs": {"ectoplasma": 4, "gema_polida": 1, "fragmento_gargula": 1, "nucleo_forja_comum": 1},
        "result_base_id": "anel_sombra_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["assassino", "geral"],
    },
    "work_colar_sombra_assassino": {
        "display_name": "Colar da Sombra",
        "emoji": "📿",
        "profession": "joalheiro",
        "level_req": 24,
        "time_seconds": 1560,
        "xp_gain": 140,
        "inputs": {"ectoplasma": 5, "gema_polida": 2, "olho_de_basilisco": 1, "nucleo_forja_comum": 1},
        "result_base_id": "colar_sombra_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["assassino", "geral"],
    },
    "work_brinco_sombra_assassino": {
        "display_name": "Brinco da Sombra",
        "emoji": "🧿",
        "profession": "joalheiro",
        "level_req": 23,
        "time_seconds": 1200,
        "xp_gain": 100,
        "inputs": {"ectoplasma": 3, "gema_polida": 1, "fragmento_gargula": 2, "nucleo_forja_comum": 1},
        "result_base_id": "brinco_sombra_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["assassino", "geral"],
    },
}

def register_all() -> None:
    """Registra todas as receitas deste pacote no registry central."""
    for rid, data in RECIPES.items():
        crafting_registry.register_recipe(rid, data)
