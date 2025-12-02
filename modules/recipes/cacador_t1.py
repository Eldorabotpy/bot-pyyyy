# modules/recipes/cacador_t1.py
# -*- coding: utf-8 -*-
# ============================================================
# TIER 1: RECEITAS DO CONJUNTO DE BATEDOR DO CAÇADOR (Profissão 5+)
# ============================================================

# RARIDADE TIER 1 (comum, bom, raro, epico, lendario)
RARITY_T1 = {
    "comum": 0.90,     # Aumentei para 90% (mais lixo)
    "bom": 0.09,       # Diminuí para 9%
    "raro": 0.009,     # 0.9%
    "epico": 0.0009,   # 0.09%
    "lendario": 0.0001 # 0.01% (Extremamente raro)
}

RECIPES = {
    # --- Arma (Armeiro) ---
    "work_arco_batedor_cacador": {
        "display_name": "Arco de Batedor",
        "emoji": "🏹",
        "profession": "armeiro",
        "level_req": 5,
        "time_seconds": 540,  # 9 minutos
        "xp_gain": 28,
        "inputs": {"madeira": 10, "linho": 5, "nucleo_forja_fraco": 1},
        "result_base_id": "arco_batedor_cacador",
        "unique": True,
        "class_req": ["cacador"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["cacador", "geral"],
        "damage_info": {"type": "perfurante", "min_damage": 14, "max_damage": 19},
    },

    # --- Armaduras (Curtidor) ---
    "work_capuz_batedor_cacador": {
        "display_name": "Capuz de Batedor",
        "emoji": "🪖",
        "profession": "curtidor",
        "level_req": 5,
        "time_seconds": 300,  # 5 minutos
        "xp_gain": 20,
        "inputs": {"couro_curtido": 6, "pano_simples": 3, "nucleo_forja_fraco": 1},
        "result_base_id": "capuz_batedor_cacador",
        "unique": True,
        "class_req": ["cacador"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["cacador", "geral"],
    },
    "work_peitoral_batedor_cacador": {
        "display_name": "Peitoral de Batedor",
        "emoji": "👕",
        "profession": "curtidor",
        "level_req": 7,
        "time_seconds": 600,  # 10 minutos
        "xp_gain": 35,
        "inputs": {"couro_curtido": 10, "pano_simples": 4, "nucleo_forja_fraco": 1},
        "result_base_id": "peitoral_batedor_cacador",
        "unique": True,
        "class_req": ["cacador"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["cacador", "geral"],
    },
    "work_calcas_batedor_cacador": {
        "display_name": "Calças de Batedor",
        "emoji": "👖",
        "profession": "curtidor",
        "level_req": 6,
        "time_seconds": 420,  # 7 minutos
        "xp_gain": 30,
        "inputs": {"couro_curtido": 8, "pano_simples": 5, "nucleo_forja_fraco": 1},
        "result_base_id": "calcas_batedor_cacador",
        "unique": True,
        "class_req": ["cacador"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["cacador", "geral"],
    },
    "work_botas_batedor_cacador": {
        "display_name": "Botas de Batedor",
        "emoji": "🥾",
        "profession": "curtidor",
        "level_req": 5,
        "time_seconds": 240,  # 4 minutos
        "xp_gain": 15,
        "inputs": {"couro_curtido": 5, "pano_simples": 2, "nucleo_forja_fraco": 1},
        "result_base_id": "botas_batedor_cacador",
        "unique": True,
        "class_req": ["cacador"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["cacador", "geral"],
    },
    "work_luvas_batedor_cacador": {
        "display_name": "Luvas de Batedor",
        "emoji": "🧤",
        "profession": "curtidor",
        "level_req": 5,
        "time_seconds": 240,  # 4 minutos
        "xp_gain": 15,
        "inputs": {"couro_curtido": 5, "pano_simples": 2, "nucleo_forja_fraco": 1},
        "result_base_id": "luvas_batedor_cacador",
        "unique": True,
        "class_req": ["cacador"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["cacador", "geral"],
    },

    # --- Acessórios de Caça (Joalheiro) ---
    "work_anel_batedor_cacador": {
        "display_name": "Anel de Batedor",
        "emoji": "💍",
        "profession": "joalheiro",
        "level_req": 8,
        "time_seconds": 360,  # 6 minutos
        "xp_gain": 40,
        "inputs": {"couro_curtido": 2, "pena": 5, "nucleo_forja_fraco": 1},
        "result_base_id": "anel_batedor_cacador",
        "unique": True,
        "class_req": ["cacador"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["cacador", "geral"],
    },
    "work_colar_batedor_cacador": {
        "display_name": "Colar de Batedor",
        "emoji": "📿",
        "profession": "joalheiro",
        "level_req": 9,
        "time_seconds": 450,  # 7.5 minutos
        "xp_gain": 50,
        "inputs": {"couro_curtido": 3, "pena": 8, "dente_afiado": 1, "nucleo_forja_fraco": 1},
        "result_base_id": "colar_batedor_cacador",
        "unique": True,
        "class_req": ["cacador"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["cacador", "geral"],
    },
    "work_brinco_batedor_cacador": {
        "display_name": "Brinco de Batedor",
        "emoji": "🧿",
        "profession": "joalheiro",
        "level_req": 8,
        "time_seconds": 300,  # 5 minutos
        "xp_gain": 35,
        "inputs": {"couro_curtido": 1, "pena": 10, "nucleo_forja_fraco": 1},
        "result_base_id": "brinco_batedor_cacador",
        "unique": True,
        "class_req": ["cacador"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["cacador", "geral"],
    },
}
