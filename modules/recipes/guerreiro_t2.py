# modules/recipes/guerreiro_t2.py
# -*- coding: utf-8 -*-
# ======================================================
# TIER 2: CONJUNTO DE AÇO DO GUERREIRO (Profissão 20+)
# ======================================================

from typing import Dict, Any
from modules.crafting_registry import register_recipe

# Padrão de raridade T2 (comum, bom, raro, épico, lendário)
RARITY_T2 = {
    "comum": 0.72,
    "bom": 0.25,
    "raro": 0.025,
    "epico": 0.004,
    "lendario": 0.001,
}

RECIPES: Dict[str, Dict[str, Any]] = {
    # ---------- Arma ----------
    "work_espada_aco_guerreiro": {
        "display_name": "Espada de Aço do Guerreiro",
        "emoji": "🗡️",
        "profession": "armeiro",
        "level_req": 20,
        "time_seconds": 1800,  # 30 minutos
        "xp_gain": 100,
        "inputs": {"barra_de_aco": 10, "couro_reforcado": 4, "nucleo_forja_comum": 1},
        "result_base_id": "espada_aco_guerreiro",
        "unique": True,
        "class_req": ["guerreiro"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["guerreiro", "geral"],
        "damage_info": {"type": "cortante", "min_damage": 35, "max_damage": 50},
    },

    # ---------- Armaduras ----------
    "work_elmo_aco_guerreiro": {
        "display_name": "Elmo de Aço do Guerreiro",
        "emoji": "🪖",
        "profession": "ferreiro",
        "level_req": 20,
        "time_seconds": 1200,  # 20 minutos
        "xp_gain": 80,
        "inputs": {"barra_de_aco": 7, "couro_reforcado": 2, "nucleo_forja_comum": 1},
        "result_base_id": "elmo_aco_guerreiro",
        "unique": True,
        "class_req": ["guerreiro"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["guerreiro", "geral"],
    },
    "work_peitoral_aco_guerreiro": {
        "display_name": "Peitoral de Aço do Guerreiro",
        "emoji": "👕",
        "profession": "ferreiro",
        "level_req": 22,  # peça principal
        "time_seconds": 2400,  # 40 minutos
        "xp_gain": 150,
        "inputs": {"barra_de_aco": 15, "couro_reforcado": 6, "nucleo_forja_comum": 1},
        "result_base_id": "peitoral_aco_guerreiro",
        "unique": True,
        "class_req": ["guerreiro"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["guerreiro", "geral"],
    },
    "work_calcas_aco_guerreiro": {
        "display_name": "Calças de Aço do Guerreiro",
        "emoji": "👖",
        "profession": "ferreiro",
        "level_req": 21,
        "time_seconds": 1500,  # 25 minutos
        "xp_gain": 120,
        "inputs": {"barra_de_aco": 10, "couro_reforcado": 4, "nucleo_forja_comum": 1},
        "result_base_id": "calcas_aco_guerreiro",
        "unique": True,
        "class_req": ["guerreiro"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["guerreiro", "geral"],
    },
    "work_botas_aco_guerreiro": {
        "display_name": "Botas de Aço do Guerreiro",
        "emoji": "🥾",
        "profession": "ferreiro",
        "level_req": 20,
        "time_seconds": 900,  # 15 minutos
        "xp_gain": 70,
        "inputs": {"barra_de_aco": 5, "couro_reforcado": 3, "nucleo_forja_comum": 1},
        "result_base_id": "botas_aco_guerreiro",
        "unique": True,
        "class_req": ["guerreiro"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["guerreiro", "geral"],
    },
    "work_luvas_aco_guerreiro": {
        "display_name": "Luvas de Aço do Guerreiro",
        "emoji": "🧤",
        "profession": "ferreiro",
        "level_req": 20,
        "time_seconds": 900,  # 15 minutos
        "xp_gain": 70,
        "inputs": {"barra_de_aco": 5, "couro_reforcado": 3, "nucleo_forja_comum": 1},
        "result_base_id": "luvas_aco_guerreiro",
        "unique": True,
        "class_req": ["guerreiro"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["guerreiro", "geral"],
    },

    # ---------- Acessórios (Joalheiro) ----------
    "work_anel_aco_guerreiro": {
        "display_name": "Anel de Aço do Guerreiro",
        "emoji": "💍",
        "profession": "joalheiro",
        "level_req": 23,
        "time_seconds": 1380,  # ~23 minutos
        "xp_gain": 115,
        "inputs": {"barra_de_aco": 4, "gema_polida": 1, "nucleo_forja_comum": 1},
        "result_base_id": "anel_aco_guerreiro",
        "unique": True,
        "class_req": ["guerreiro"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["guerreiro", "geral"],
    },
    "work_colar_aco_guerreiro": {
        "display_name": "Colar de Aço do Guerreiro",
        "emoji": "📿",
        "profession": "joalheiro",
        "level_req": 24,
        "time_seconds": 1560,  # 26 minutos
        "xp_gain": 140,
        "inputs": {"barra_de_aco": 3, "gema_polida": 2, "nucleo_forja_comum": 1},
        "result_base_id": "colar_aco_guerreiro",
        "unique": True,
        "class_req": ["guerreiro"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["guerreiro", "geral"],
    },
    "work_brinco_aco_guerreiro": {
        "display_name": "Brinco de Aço do Guerreiro",
        "emoji": "🧿",
        "profession": "joalheiro",
        "level_req": 23,
        "time_seconds": 1200,  # 20 minutos
        "xp_gain": 100,
        "inputs": {"barra_de_aco": 2, "gema_polida": 1, "nucleo_forja_comum": 1},
        "result_base_id": "brinco_aco_guerreiro",
        "unique": True,
        "class_req": ["guerreiro"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["guerreiro", "geral"],
    },
}

def register() -> None:
    """Registra todas as receitas deste módulo no registry central."""
    for rid, data in RECIPES.items():
        register_recipe(rid, data)
