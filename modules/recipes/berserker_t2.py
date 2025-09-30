# modules/recipes/berserker_t2.py
# =========================================
# TIER 2 — Conjunto de Pele de Troll do Berserker (Profissão 20+)
# =========================================

RARITY_T2 = {
    "comum": 0.72,
    "bom": 0.25,
    "raro": 0.025,
    "epico": 0.004,
    "lendario": 0.001,
}

RECIPES = {
    # ---------- Arma (Armeiro) ----------
    "work_machado_aco_berserker": {
        "display_name": "Machado de Aço do Berserker",
        "emoji": "🪓",
        "profession": "armeiro",
        "level_req": 20,
        "time_seconds": 2100,  # 35 minutos
        "xp_gain": 110,
        "inputs": {"barra_de_aco": 12, "pele_de_troll": 2, "sangue_regenerativo": 1, "nucleo_forja_comum": 1},
        "result_base_id": "machado_aco_berserker",
        "unique": True,
        "class_req": ["berserker"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["berserker", "geral"],
        "damage_info": {"type": "cortante", "min_damage": 30, "max_damage": 60},
    },

    # ---------- Armaduras (Ferreiro) ----------
    "work_elmo_troll_berserker": {
        "display_name": "Elmo de Pele de Troll",
        "emoji": "🪖",
        "profession": "ferreiro",
        "level_req": 20,
        "time_seconds": 1200,  # 20 minutos
        "xp_gain": 85,
        "inputs": {"barra_de_aco": 6, "pele_de_troll": 3, "nucleo_forja_comum": 1},
        "result_base_id": "elmo_troll_berserker",
        "unique": True,
        "class_req": ["berserker"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["berserker", "geral"],
    },
    "work_peitoral_troll_berserker": {
        "display_name": "Peitoral de Pele de Troll",
        "emoji": "👕",
        "profession": "ferreiro",
        "level_req": 22,
        "time_seconds": 2700,  # 45 minutos
        "xp_gain": 160,
        "inputs": {"barra_de_aco": 10, "pele_de_troll": 5, "sangue_regenerativo": 3, "nucleo_forja_comum": 1},
        "result_base_id": "peitoral_troll_berserker",
        "unique": True,
        "class_req": ["berserker"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["berserker", "geral"],
    },
    "work_calcas_troll_berserker": {
        "display_name": "Calças de Pele de Troll",
        "emoji": "👖",
        "profession": "ferreiro",
        "level_req": 21,
        "time_seconds": 1620,  # 27 minutos
        "xp_gain": 125,
        "inputs": {"barra_de_aco": 8, "pele_de_troll": 4, "sangue_regenerativo": 1, "nucleo_forja_comum": 1},
        "result_base_id": "calcas_troll_berserker",
        "unique": True,
        "class_req": ["berserker"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["berserker", "geral"],
    },
    "work_botas_troll_berserker": {
        "display_name": "Botas de Pele de Troll",
        "emoji": "🥾",
        "profession": "ferreiro",
        "level_req": 20,
        "time_seconds": 960,  # 16 minutos
        "xp_gain": 75,
        "inputs": {"barra_de_aco": 4, "pele_de_troll": 2, "nucleo_forja_comum": 1},
        "result_base_id": "botas_troll_berserker",
        "unique": True,
        "class_req": ["berserker"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["berserker", "geral"],
    },
    "work_luvas_troll_berserker": {
        "display_name": "Luvas de Pele de Troll",
        "emoji": "🧤",
        "profession": "ferreiro",
        "level_req": 20,
        "time_seconds": 960,  # 16 minutos
        "xp_gain": 75,
        "inputs": {"barra_de_aco": 4, "pele_de_troll": 2, "nucleo_forja_comum": 1},
        "result_base_id": "luvas_troll_berserker",
        "unique": True,
        "class_req": ["berserker"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["berserker", "geral"],
    },

    # ---------- Acessórios (Joalheiro) ----------
    "work_anel_troll_berserker": {
        "display_name": "Anel de Garra de Troll",
        "emoji": "💍",
        "profession": "joalheiro",
        "level_req": 23,
        "time_seconds": 1380,  # ~23 minutos
        "xp_gain": 115,
        "inputs": {"pele_de_troll": 1, "dente_afiado_superior": 1, "gema_polida": 1, "nucleo_forja_comum": 1},
        "result_base_id": "anel_troll_berserker",
        "unique": True,
        "class_req": ["berserker"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["berserker", "geral"],
    },
    "work_colar_troll_berserker": {
        "display_name": "Colar de Garra de Troll",
        "emoji": "📿",
        "profession": "joalheiro",
        "level_req": 24,
        "time_seconds": 1560,  # 26 minutos
        "xp_gain": 140,
        "inputs": {"pele_de_troll": 2, "sangue_regenerativo": 1, "gema_polida": 2, "nucleo_forja_comum": 1},
        "result_base_id": "colar_troll_berserker",
        "unique": True,
        "class_req": ["berserker"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["berserker", "geral"],
    },
    "work_brinco_troll_berserker": {
        "display_name": "Brinco de Garra de Troll",
        "emoji": "🧿",
        "profession": "joalheiro",
        "level_req": 23,
        "time_seconds": 1200,  # 20 minutos
        "xp_gain": 100,
        "inputs": {"pele_de_troll": 1, "dente_afiado_superior": 1, "nucleo_forja_comum": 1},
        "result_base_id": "brinco_troll_berserker",
        "unique": True,
        "class_req": ["berserker"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["berserker", "geral"],
    },
}
