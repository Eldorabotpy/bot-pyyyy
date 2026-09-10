# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any

RECIPES: Dict[str, Dict[str, Any]] = {
    # --- Arma de Precisão (Armeiro) ---
    "work_adaga_sorrateira_assassino": {
        "display_name": "Adaga Sorrateira",
        "emoji": "🔪",
        "profession": "armeiro",
        "level_req": 5,
        "time_seconds": 420,  # 7 minutos
        "xp_gain": 26,
        "inputs": {"barra_de_ferro": 5, "couro_curtido": 2, "asa_de_morcego": 2, "nucleo_de_forja": 1},
        "result_base_id": "adaga_sorrateira_assassino",
        "unique": True,
        "class_req": ["assassino"],
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
        "inputs": {"couro_curtido": 7, "pano_simples": 4, "nucleo_de_forja": 1},
        "result_base_id": "mascara_sorrateira_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "affix_pools_to_use": ["assassino", "geral"],
    },
    "work_couraça_sorrateira_assassino": {
        "display_name": "Couraça Sorrateira",
        "emoji": "👕",
        "profession": "curtidor",
        "level_req": 7,
        "time_seconds": 600,  # 10 minutos
        "xp_gain": 35,
        "inputs": {"couro_curtido": 12, "pano_simples": 5, "nucleo_de_forja": 1},
        "result_base_id": "couraca_sorrateira_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "affix_pools_to_use": ["assassino", "geral"],
    },
    "work_calcas_sorrateiras_assassino": {
        "display_name": "Calças Sorrateiras",
        "emoji": "👖",
        "profession": "curtidor",
        "level_req": 6,
        "time_seconds": 420,  # 7 minutos
        "xp_gain": 30,
        "inputs": {"couro_curtido": 9, "pano_simples": 6, "nucleo_de_forja": 1},
        "result_base_id": "calcas_sorrateiras_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "affix_pools_to_use": ["assassino", "geral"],
    },
    "work_botas_sorrateiras_assassino": {
        "display_name": "Botas Sorrateiras",
        "emoji": "🥾",
        "profession": "curtidor",
        "level_req": 5,
        "time_seconds": 240,  # 4 minutos
        "xp_gain": 15,
        "inputs": {"couro_curtido": 5, "pano_simples": 2, "asa_de_morcego": 1, "nucleo_de_forja": 1},
        "result_base_id": "botas_sorrateiras_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "affix_pools_to_use": ["assassino", "geral"],
    },
    "work_luvas_sorrateiras_assassino": {
        "display_name": "Luvas Sorrateiras",
        "emoji": "🧤",
        "profession": "curtidor",
        "level_req": 5,
        "time_seconds": 240,  # 4 minutos
        "xp_gain": 15,
        "inputs": {"couro_curtido": 5, "pano_simples": 2, "asa_de_morcego": 1, "nucleo_de_forja": 1},
        "result_base_id": "luvas_sorrateiras_assassino",
        "unique": True,
        "class_req": ["assassino"],
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
        "inputs": {"couro_curtido": 2, "ectoplasma": 1, "nucleo_de_forja": 1},
        "result_base_id": "anel_sorrateiro_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "affix_pools_to_use": ["assassino", "geral"],
    },
    "work_colar_sorrateiro_assassino": {
        "display_name": "Colar Sorrateiro",
        "emoji": "📿",
        "profession": "joalheiro",
        "level_req": 9,
        "time_seconds": 450,  # 7.5 minutos
        "xp_gain": 50,
        "inputs": {"couro_curtido": 3, "ectoplasma": 2, "dente_afiado": 1, "nucleo_de_forja": 1},
        "result_base_id": "colar_sorrateiro_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "affix_pools_to_use": ["assassino", "geral"],
    },
    "work_brinco_sorrateiro_assassino": {
        "display_name": "Brinco Sorrateiro",
        "emoji": "🧿",
        "profession": "joalheiro",
        "level_req": 8,
        "time_seconds": 300,  # 5 minutos
        "xp_gain": 35,
        "inputs": {"couro_curtido": 1, "ectoplasma": 1, "asa_de_morcego": 1, "nucleo_de_forja": 1},
        "result_base_id": "brinco_sorrateiro_assassino",
        "unique": True,
        "class_req": ["assassino"],
        "affix_pools_to_use": ["assassino", "geral"],
    },
}
