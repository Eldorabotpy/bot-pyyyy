# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any

# TIER 1: CONJUNTO DA VIGÍLIA — usa apenas materiais já existentes.
RECIPES: Dict[str, Dict[str, Any]] = {
    "work_cajado_vigilia_necromante": {
        "display_name": "Cajado da Vigília", "emoji": "🪄", "profession": "armeiro",
        "level_req": 5, "time_seconds": 480, "xp_gain": 25,
        "inputs": {"madeira": 12, "gema_bruta": 2, "nucleo_de_forja": 1, "ectoplasma": 1},
        "result_base_id": "cajado_vigilia_necromante", "unique": True,
        "class_req": ["necromante"], "affix_pools_to_use": ["necromante", "geral"],
        "damage_info": {"type": "arcano", "min_damage": 15, "max_damage": 20},
    },
    "work_capuz_vigilia_necromante": {
        "display_name": "Capuz da Vigília", "emoji": "🧢", "profession": "alfaiate",
        "level_req": 5, "time_seconds": 300, "xp_gain": 20,
        "inputs": {"linho": 10, "pano_simples": 5, "ectoplasma": 1},
        "result_base_id": "capuz_vigilia_necromante", "unique": True,
        "class_req": ["necromante"], "affix_pools_to_use": ["necromante", "geral"],
    },
    "work_veste_vigilia_necromante": {
        "display_name": "Veste da Vigília", "emoji": "🥼", "profession": "alfaiate",
        "level_req": 7, "time_seconds": 600, "xp_gain": 35,
        "inputs": {"linho": 20, "pano_simples": 10, "ectoplasma": 2},
        "result_base_id": "veste_vigilia_necromante", "unique": True,
        "class_req": ["necromante"], "affix_pools_to_use": ["necromante", "geral"],
    },
    "work_calcas_vigilia_necromante": {
        "display_name": "Calças da Vigília", "emoji": "👖", "profession": "alfaiate",
        "level_req": 6, "time_seconds": 420, "xp_gain": 30,
        "inputs": {"linho": 15, "pano_simples": 8, "ectoplasma": 1},
        "result_base_id": "calcas_vigilia_necromante", "unique": True,
        "class_req": ["necromante"], "affix_pools_to_use": ["necromante", "geral"],
    },
    "work_botas_vigilia_necromante": {
        "display_name": "Botas da Vigília", "emoji": "🥾", "profession": "alfaiate",
        "level_req": 5, "time_seconds": 240, "xp_gain": 15,
        "inputs": {"linho": 8, "pano_simples": 3, "ectoplasma": 1},
        "result_base_id": "botas_vigilia_necromante", "unique": True,
        "class_req": ["necromante"], "affix_pools_to_use": ["necromante", "geral"],
    },
    "work_luvas_vigilia_necromante": {
        "display_name": "Luvas da Vigília", "emoji": "🧤", "profession": "alfaiate",
        "level_req": 5, "time_seconds": 240, "xp_gain": 15,
        "inputs": {"linho": 8, "pano_simples": 3, "ectoplasma": 1},
        "result_base_id": "luvas_vigilia_necromante", "unique": True,
        "class_req": ["necromante"], "affix_pools_to_use": ["necromante", "geral"],
    },
    "work_anel_vigilia_necromante": {
        "display_name": "Anel da Vigília", "emoji": "💍", "profession": "joalheiro",
        "level_req": 5, "time_seconds": 360, "xp_gain": 40,
        "inputs": {"fio_de_prata": 3, "gema_bruta": 2, "ectoplasma": 1},
        "result_base_id": "anel_vigilia_necromante", "unique": True,
        "class_req": ["necromante"], "affix_pools_to_use": ["necromante", "geral"],
    },
    "work_colar_vigilia_necromante": {
        "display_name": "Colar da Vigília", "emoji": "📿", "profession": "joalheiro",
        "level_req": 9, "time_seconds": 450, "xp_gain": 50,
        "inputs": {"fio_de_prata": 4, "gema_bruta": 3, "ectoplasma": 2},
        "result_base_id": "colar_vigilia_necromante", "unique": True,
        "class_req": ["necromante"], "affix_pools_to_use": ["necromante", "geral"],
    },
    "work_brinco_vigilia_necromante": {
        "display_name": "Brinco da Vigília", "emoji": "🧿", "profession": "joalheiro",
        "level_req": 7, "time_seconds": 300, "xp_gain": 35,
        "inputs": {"fio_de_prata": 2, "gema_bruta": 1, "ectoplasma": 1},
        "result_base_id": "brinco_vigilia_necromante", "unique": True,
        "class_req": ["necromante"], "affix_pools_to_use": ["necromante", "geral"],
    },
}
