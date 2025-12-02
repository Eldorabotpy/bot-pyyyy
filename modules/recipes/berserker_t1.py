# modules/recipes/berserker_t1.py
# ======================================================
# TIER 1: RECEITAS DO CONJUNTO RÚSTICO DO BERSERKER (Nível Profissão 5+)
# ======================================================

# Padrão de raridade (comum, bom, raro, épico, lendário)
RARITY_T1 = {
    "comum": 0.90,     # Aumentei para 90% (mais lixo)
    "bom": 0.09,       # Diminuí para 9%
    "raro": 0.009,     # 0.9%
    "epico": 0.0009,   # 0.09%
    "lendario": 0.0001 # 0.01% (Extremamente raro)
}

RECIPES = {
    # ---------- Arma (Armeiro) ----------
    "work_machado_rustico_berserker": {
        "display_name": "Machado Rústico do Berserker",
        "emoji": "🪓",
        "profession": "armeiro",
        "level_req": 5,
        "time_seconds": 540,  # 9 minutos
        "xp_gain": 28,
        "inputs": {"barra_de_ferro": 7, "couro_curtido": 3, "presa_de_javali": 2, "nucleo_forja_fraco": 1},
        "result_base_id": "machado_rustico_berserker",
        "unique": True,
        "class_req": ["berserker"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["berserker", "geral"],
        "damage_info": {"type": "cortante", "min_damage": 10, "max_damage": 22},
    },

    # ---------- Armaduras (Ferreiro/Curtidor) ----------
    "work_elmo_chifres_berserker": {
        "display_name": "Elmo de Chifres do Berserker",
        "emoji": "🪖",
        "profession": "ferreiro",
        "level_req": 5,
        "time_seconds": 360,  # 6 minutos
        "xp_gain": 22,
        "inputs": {"barra_de_ferro": 4, "couro_de_lobo_alfa": 2, "presa_de_javali": 1, "nucleo_forja_fraco": 1},
        "result_base_id": "elmo_chifres_berserker",
        "unique": True,
        "class_req": ["berserker"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["berserker", "geral"],
    },
    "work_peitoral_placas_berserker": {
        "display_name": "Peitoral de Placas do Berserker",
        "emoji": "👕",
        "profession": "ferreiro",
        "level_req": 7,
        "time_seconds": 660,  # 11 minutos
        "xp_gain": 40,
        "inputs": {"barra_de_ferro": 10, "couro_de_lobo_alfa": 5, "presa_de_javali": 2, "nucleo_forja_fraco": 1},
        "result_base_id": "peitoral_placas_berserker",
        "unique": True,
        "class_req": ["berserker"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["berserker", "geral"],
    },
    "work_calcas_placas_berserker": {
        "display_name": "Calças de Placas do Berserker",
        "emoji": "👖",
        "profession": "ferreiro",
        "level_req": 6,
        "time_seconds": 480,  # 8 minutos
        "xp_gain": 32,
        "inputs": {"barra_de_ferro": 7, "couro_de_lobo_alfa": 3, "nucleo_forja_fraco": 1},
        "result_base_id": "calcas_placas_berserker",
        "unique": True,
        "class_req": ["berserker"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["berserker", "geral"],
    },
    "work_botas_couro_berserker": {
        "display_name": "Botas de Couro do Berserker",
        "emoji": "🥾",
        "profession": "curtidor",
        "level_req": 5,
        "time_seconds": 300,  # 5 minutos
        "xp_gain": 18,
        "inputs": {"couro_de_lobo_alfa": 4, "couro_curtido": 2, "nucleo_forja_fraco": 1},
        "result_base_id": "botas_couro_berserker",
        "unique": True,
        "class_req": ["berserker"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["berserker", "geral"],
    },
    "work_luvas_couro_berserker": {
        "display_name": "Luvas de Couro do Berserker",
        "emoji": "🧤",
        "profession": "curtidor",
        "level_req": 5,
        "time_seconds": 300,  # 5 minutos
        "xp_gain": 18,
        "inputs": {"couro_de_lobo_alfa": 4, "couro_curtido": 2, "nucleo_forja_fraco": 1},
        "result_base_id": "luvas_couro_berserker",
        "unique": True,
        "class_req": ["berserker"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["berserker", "geral"],
    },

    # ---------- Acessórios Tribais (Joalheiro) ----------
    "work_anel_osso_berserker": {
        "display_name": "Anel de Osso do Berserker",
        "emoji": "💍",
        "profession": "joalheiro",
        "level_req": 8,
        "time_seconds": 420,  # 7 minutos
        "xp_gain": 45,
        "inputs": {"dente_afiado": 2, "couro_curtido": 1, "nucleo_forja_fraco": 1},
        "result_base_id": "anel_osso_berserker",
        "unique": True,
        "class_req": ["berserker"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["berserker", "geral"],
    },
    "work_colar_presas_berserker": {
        "display_name": "Colar de Presas do Berserker",
        "emoji": "📿",
        "profession": "joalheiro",
        "level_req": 9,
        "time_seconds": 500,  # ~8 minutos
        "xp_gain": 55,
        "inputs": {"presa_de_javali": 3, "dente_afiado": 1, "couro_curtido": 2, "nucleo_forja_fraco": 1},
        "result_base_id": "colar_presas_berserker",
        "unique": True,
        "class_req": ["berserker"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["berserker", "geral"],
    },
    "work_brinco_osso_berserker": {
        "display_name": "Brinco de Osso do Berserker",
        "emoji": "🧿",
        "profession": "joalheiro",
        "level_req": 8,
        "time_seconds": 400,  # ~6.5 minutos
        "xp_gain": 42,
        "inputs": {"dente_afiado": 1, "presa_de_javali": 1, "nucleo_forja_fraco": 1},
        "result_base_id": "brinco_osso_berserker",
        "unique": True,
        "class_req": ["berserker"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["berserker", "geral"],
    },
}
