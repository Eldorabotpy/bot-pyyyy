# modules/recipes/guerreiro_t1.py
# -*- coding: utf-8 -*-
# ======================================================
# TIER 1: RECEITAS DO CONJUNTO DE FERRO DO GUERREIRO (Profissão 5+)
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
    # ---------- Arma ----------
    "work_espada_ferro_guerreiro": {
        "display_name": "Espada de Ferro do Guerreiro",
        "emoji": "🗡️",
        "profession": "armeiro",
        "level_req": 5,
        "time_seconds": 480,  # 8 minutos
        "xp_gain": 25,
        "inputs": {"barra_de_ferro": 8, "couro_curtido": 2, "nucleo_forja_fraco": 1},
        "result_base_id": "espada_ferro_guerreiro",
        "unique": True,
        "class_req": ["guerreiro"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["guerreiro", "geral"],
        "damage_info": {"type": "cortante", "min_damage": 12, "max_damage": 18},
    },

    # ---------- Armaduras ----------
    "work_elmo_ferro_guerreiro": {
        "display_name": "Elmo de Ferro do Guerreiro",
        "emoji": "🪖",
        "profession": "ferreiro",
        "level_req": 5,
        "time_seconds": 300,
        "xp_gain": 20,
        "inputs": {"barra_de_ferro": 5, "couro_curtido": 1, "nucleo_forja_fraco": 1},
        "result_base_id": "elmo_ferro_guerreiro",
        "unique": True,
        "class_req": ["guerreiro"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["guerreiro", "geral"],
    },
    "work_peitoral_ferro_guerreiro": {
        "display_name": "Peitoral de Ferro do Guerreiro",
        "emoji": "👕",
        "profession": "ferreiro",
        "level_req": 7,
        "time_seconds": 600,
        "xp_gain": 35,
        "inputs": {"barra_de_ferro": 12, "couro_curtido": 4, "nucleo_forja_fraco": 1},
        "result_base_id": "peitoral_ferro_guerreiro",
        "unique": True,
        "class_req": ["guerreiro"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["guerreiro", "geral"],
    },
    "work_calcas_ferro_guerreiro": {
        "display_name": "Calças de Ferro do Guerreiro",
        "emoji": "👖",
        "profession": "ferreiro",
        "level_req": 6,
        "time_seconds": 420,
        "xp_gain": 30,
        "inputs": {"barra_de_ferro": 8, "couro_curtido": 3, "nucleo_forja_fraco": 1},
        "result_base_id": "calcas_ferro_guerreiro",
        "unique": True,
        "class_req": ["guerreiro"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["guerreiro", "geral"],
    },
    "work_botas_ferro_guerreiro": {
        "display_name": "Botas de Ferro do Guerreiro",
        "emoji": "🥾",
        "profession": "ferreiro",
        "level_req": 5,
        "time_seconds": 240,
        "xp_gain": 15,
        "inputs": {"barra_de_ferro": 4, "couro_curtido": 2, "nucleo_forja_fraco": 1},
        "result_base_id": "botas_ferro_guerreiro",
        "unique": True,
        "class_req": ["guerreiro"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["guerreiro", "geral"],
    },
    "work_luvas_ferro_guerreiro": {
        "display_name": "Luvas de Ferro do Guerreiro",
        "emoji": "🧤",
        "profession": "ferreiro",
        "level_req": 5,
        "time_seconds": 240,
        "xp_gain": 15,
        "inputs": {"barra_de_ferro": 4, "couro_curtido": 2, "nucleo_forja_fraco": 1},
        "result_base_id": "luvas_ferro_guerreiro",
        "unique": True,
        "class_req": ["guerreiro"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["guerreiro", "geral"],
    },

    # ---------- Acessórios (Joalheiro) ----------
    "work_anel_ferro_guerreiro": {
        "display_name": "Anel de Ferro do Guerreiro",
        "emoji": "💍",
        "profession": "joalheiro",
        "level_req": 5,
        "time_seconds": 360,
        "xp_gain": 40,
        "inputs": {"barra_de_ferro": 3, "gema_bruta": 1, "nucleo_forja_fraco": 1},
        "result_base_id": "anel_ferro_guerreiro",
        "unique": True,
        "class_req": ["guerreiro"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["guerreiro", "geral"],
    },
    "work_colar_ferro_guerreiro": {
        "display_name": "Colar de Ferro do Guerreiro",
        "emoji": "📿",
        "profession": "joalheiro",
        "level_req": 9,
        "time_seconds": 400,
        "xp_gain": 50,
        "inputs": {"barra_de_ferro": 3, "gema_polida": 2, "nucleo_forja_fraco": 1}, 
        "result_base_id": "colar_ferro_guerreiro",
        "unique": True,
        "class_req": ["guerreiro"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["guerreiro", "geral"],
    },
    "work_brinco_ferro_guerreiro": {
        "display_name": "Brinco de Ferro do Guerreiro",
        "emoji": "🧿",
        "profession": "joalheiro",
        "level_req": 9,
        "time_seconds": 300,
        "xp_gain": 35,
        "inputs": {"barra_de_ferro": 2, "gema_polida": 1, "nucleo_forja_fraco": 1},
        "result_base_id": "brinco_ferro_guerreiro",
        "unique": True,
        "class_req": ["guerreiro"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["guerreiro", "geral"],
    },
}
