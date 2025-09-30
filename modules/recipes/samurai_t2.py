# modules/recipes/samurai_t2.py
# -*- coding: utf-8 -*-
# =========================================
# TIER 2 — Receitas do Samurai (Aço Damasco, nível prof. 20+)
# =========================================

from __future__ import annotations
from typing import Dict, Any

# Padrão de raridade (comum, bom, raro, épico, lendário)
RARITY_T2 = {
    "comum": 0.72,
    "bom": 0.25,
    "raro": 0.025,
    "epico": 0.004,
    "lendario": 0.001,
}

RECIPES: Dict[str, Dict[str, Any]] = {
    # --- Lâmina Magistral (Armeiro) ---
    "work_katana_damasco_samurai": {
        "display_name": "Katana de Aço Damasco",
        "emoji": "⚔️",
        "profession": "armeiro",
        "level_req": 25,  # Obra-prima do armeiro
        "time_seconds": 3600,  # 1 hora
        "xp_gain": 250,
        "inputs": {"barra_de_aco": 15, "couro_reforcado": 5, "fio_de_prata": 5, "nucleo_forja_comum": 1},
        "result_base_id": "katana_damasco_samurai",
        "unique": True,
        "class_req": ["samurai"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["samurai", "geral"],
        "damage_info": {"type": "cortante", "min_damage": 42, "max_damage": 55},
    },

    # --- Armadura de Aço Damasco (Ferreiro) ---
    "work_kabuto_damasco_samurai": {
        "display_name": "Kabuto de Aço Damasco",
        "emoji": "🪖",
        "profession": "ferreiro",
        "level_req": 21,
        "time_seconds": 1320,  # 22 minutos
        "xp_gain": 90,
        "inputs": {"barra_de_aco": 8, "couro_reforcado": 4, "fio_de_prata": 2, "nucleo_forja_comum": 1},
        "result_base_id": "kabuto_damasco_samurai",
        "unique": True,
        "class_req": ["samurai"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["samurai", "geral"],
    },
    "work_do_damasco_samurai": {
        "display_name": "Do de Aço Damasco",
        "emoji": "👕",
        "profession": "ferreiro",
        "level_req": 22,
        "time_seconds": 2400,  # 40 minutos
        "xp_gain": 150,
        "inputs": {"barra_de_aco": 18, "couro_reforcado": 8, "fragmento_gargula": 2, "nucleo_forja_comum": 1},
        "result_base_id": "do_damasco_samurai",
        "unique": True,
        "class_req": ["samurai"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["samurai", "geral"],
    },
    "work_haidate_damasco_samurai": {
        "display_name": "Haidate de Aço Damasco",
        "emoji": "👖",
        "profession": "ferreiro",
        "level_req": 22,
        "time_seconds": 1800,  # 30 minutos
        "xp_gain": 130,
        "inputs": {"barra_de_aco": 12, "couro_reforcado": 6, "fio_de_prata": 3, "nucleo_forja_comum": 1},
        "result_base_id": "haidate_damasco_samurai",
        "unique": True,
        "class_req": ["samurai"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["samurai", "geral"],
    },
    "work_suneate_damasco_samurai": {
        "display_name": "Suneate de Aço Damasco",
        "emoji": "🥾",
        "profession": "ferreiro",
        "level_req": 20,
        "time_seconds": 1020,  # 17 minutos
        "xp_gain": 75,
        "inputs": {"barra_de_aco": 6, "couro_reforcado": 3, "nucleo_forja_comum": 1},
        "result_base_id": "suneate_damasco_samurai",
        "unique": True,
        "class_req": ["samurai"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["samurai", "geral"],
    },
    "work_kote_damasco_samurai": {
        "display_name": "Kote de Aço Damasco",
        "emoji": "🧤",
        "profession": "ferreiro",
        "level_req": 20,
        "time_seconds": 1020,  # 17 minutos
        "xp_gain": 75,
        "inputs": {"barra_de_aco": 6, "couro_reforcado": 3, "nucleo_forja_comum": 1},
        "result_base_id": "kote_damasco_samurai",
        "unique": True,
        "class_req": ["samurai"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["samurai", "geral"],
    },

    # --- Acessórios de Honra (Joalheiro) ---
    "work_anel_damasco_samurai": {
        "display_name": "Anel de Aço Damasco",
        "emoji": "💍",
        "profession": "joalheiro",
        "level_req": 23,
        "time_seconds": 1500,  # 25 minutos
        "xp_gain": 120,
        "inputs": {"barra_de_aco": 3, "gema_polida": 1, "fragmento_gargula": 1, "nucleo_forja_comum": 1},
        "result_base_id": "anel_damasco_samurai",
        "unique": True,
        "class_req": ["samurai"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["samurai", "geral"],
    },
    "work_colar_damasco_samurai": {
        "display_name": "Colar de Aço Damasco",
        "emoji": "📿",
        "profession": "joalheiro",
        "level_req": 24,
        "time_seconds": 1680,  # 28 minutos
        "xp_gain": 145,
        "inputs": {"barra_de_aco": 4, "gema_polida": 2, "fio_de_prata": 2, "nucleo_forja_comum": 1},
        "result_base_id": "colar_damasco_samurai",
        "unique": True,
        "class_req": ["samurai"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["samurai", "geral"],
    },
    "work_brinco_damasco_samurai": {
        "display_name": "Brinco de Aço Damasco",
        "emoji": "🧿",
        "profession": "joalheiro",
        "level_req": 23,
        "time_seconds": 1320,  # 22 minutos
        "xp_gain": 110,
        "inputs": {"barra_de_aco": 2, "gema_polida": 1, "fio_de_prata": 1, "nucleo_forja_comum": 1},
        "result_base_id": "brinco_damasco_samurai",
        "unique": True,
        "class_req": ["samurai"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["samurai", "geral"],
    },

    
}
