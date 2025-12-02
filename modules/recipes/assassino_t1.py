# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict
from modules import crafting_registry

RARITY_T1 = {

    "comum": 0.90,     # Aumentei para 90% (mais lixo)
    "bom": 0.09,       # Diminuí para 9%
    "raro": 0.009,     # 0.9%
    "epico": 0.0009,   # 0.09%
    "lendario": 0.0001 # 0.01% (Extremamente raro)
}

# TIER 1: RECEITAS DO CONJUNTO SORRATEIRO DO ASSASSINO (Nível de Profissão 5+)
# ============================================================================

RECIPES: Dict[str, Dict] = {
    # --- Arma de Precisão (Armeiro) ---
    "work_adaga_sorrateira_assassino": {
        "display_name": "Adaga Sorrateira",
        "emoji": "🔪",
        "profession": "armeiro",
        "level_req": 5,
        "time_seconds": 420,  # 7 minutos
        "xp_gain": 26,
        "inputs": {"barra_de_ferro": 5, "couro_curtido": 2, "asa_de_morcego": 2, "nucleo_forja_fraco": 1},
        "result_base_id": "adaga_sorrateira_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["assassino", "geral"],
        "damage_info": {"type": "perfurante", "min_damage": 16, "max_damage": 18},
    },

    # --- Armadura de Couro (Curtidor) ---
    "work_mascara_sorrateira_assassino": {
        "display_name": "Máscara Sorrateira",
        "emoji": "🪖",
        "profession": "curtidor",
        "level_req": 5,
        "time_seconds": 300,  # 5 minutos
        "xp_gain": 20,
        "inputs": {"couro_curtido": 7, "pano_simples": 4, "nucleo_forja_fraco": 1},
        "result_base_id": "mascara_sorrateira_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["assassino", "geral"],
    },
    "work_couraça_sorrateira_assassino": {
        "display_name": "Couraça Sorrateira",
        "emoji": "👕",
        "profession": "curtidor",
        "level_req": 7,
        "time_seconds": 600,  # 10 minutos
        "xp_gain": 35,
        "inputs": {"couro_curtido": 12, "pano_simples": 5, "nucleo_forja_fraco": 1},
        "result_base_id": "couraça_sorrateira_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["assassino", "geral"],
    },
    "work_calcas_sorrateiras_assassino": {
        "display_name": "Calças Sorrateiras",
        "emoji": "👖",
        "profession": "curtidor",
        "level_req": 6,
        "time_seconds": 420,  # 7 minutos
        "xp_gain": 30,
        "inputs": {"couro_curtido": 9, "pano_simples": 6, "nucleo_forja_fraco": 1},
        "result_base_id": "calcas_sorrateiras_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["assassino", "geral"],
    },
    "work_botas_sorrateiras_assassino": {
        "display_name": "Botas Sorrateiras",
        "emoji": "🥾",
        "profession": "curtidor",
        "level_req": 5,
        "time_seconds": 240,  # 4 minutos
        "xp_gain": 15,
        "inputs": {"couro_curtido": 5, "pano_simples": 2, "asa_de_morcego": 1, "nucleo_forja_fraco": 1},
        "result_base_id": "botas_sorrateiras_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["assassino", "geral"],
    },
    "work_luvas_sorrateiras_assassino": {
        "display_name": "Luvas Sorrateiras",
        "emoji": "🧤",
        "profession": "curtidor",
        "level_req": 5,
        "time_seconds": 240,  # 4 minutos
        "xp_gain": 15,
        "inputs": {"couro_curtido": 5, "pano_simples": 2, "asa_de_morcego": 1, "nucleo_forja_fraco": 1},
        "result_base_id": "luvas_sorrateiras_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["assassino", "geral"],
    },

    # --- Acessórios Sombrios (Joalheiro) ---
    "work_anel_sorrateiro_assassino": {
        "display_name": "Anel Sorrateiro",
        "emoji": "💍",
        "profession": "joalheiro",
        "level_req": 5,
        "time_seconds": 360,  # 6 minutos
        "xp_gain": 40,
        "inputs": {"couro_curtido": 2, "ectoplasma": 1, "nucleo_forja_fraco": 1},
        "result_base_id": "anel_sorrateiro_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["assassino", "geral"],
    },
    "work_colar_sorrateiro_assassino": {
        "display_name": "Colar Sorrateiro",
        "emoji": "📿",
        "profession": "joalheiro",
        "level_req": 9,
        "time_seconds": 450,  # 7.5 minutos
        "xp_gain": 50,
        "inputs": {"couro_curtido": 3, "ectoplasma": 2, "dente_afiado": 1, "nucleo_forja_fraco": 1},
        "result_base_id": "colar_sorrateiro_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["assassino", "geral"],
    },
    "work_brinco_sorrateiro_assassino": {
        "display_name": "Brinco Sorrateiro",
        "emoji": "🧿",
        "profession": "joalheiro",
        "level_req": 8,
        "time_seconds": 300,  # 5 minutos
        "xp_gain": 35,
        "inputs": {"couro_curtido": 1, "ectoplasma": 1, "asa_de_morcego": 1, "nucleo_forja_fraco": 1},
        "result_base_id": "brinco_sorrateiro_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["assassino", "geral"],
    },
}

def register_all() -> None:
    """Registra todas as receitas deste pacote no registry central."""
    for rid, data in RECIPES.items():
        crafting_registry.register_recipe(rid, data)
