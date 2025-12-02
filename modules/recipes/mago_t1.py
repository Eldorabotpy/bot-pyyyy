# modules/recipes/mago_t1.py
# -*- coding: utf-8 -*-
# =========================================
# TIER 1 — Receitas do Mago (nível prof. 5+)
# =========================================

# Padrão de raridade T1 (comum, bom, raro, épico, lendário)
RARITY_T1 = {
    "comum": 0.90,     # Aumentei para 90% (mais lixo)
    "bom": 0.09,       # Diminuí para 9%
    "raro": 0.009,     # 0.9%
    "epico": 0.0009,   # 0.09%
    "lendario": 0.0001 # 0.01% (Extremamente raro)
}

RECIPES = {
    # ---------- Arma (Armeiro) ----------
    "work_cajado_aprendiz_mago": {
        "display_name": "Cajado de Aprendiz",
        "emoji": "🪄",
        "profession": "armeiro",
        "level_req": 5,
        "time_seconds": 480,  # 8 minutos
        "xp_gain": 25,
        # T1 usa madeira comum (padronizado com outros T1)
        "inputs": {"madeira": 12, "gema_bruta": 2, "nucleo_forja_fraco": 1},
        "result_base_id": "cajado_aprendiz_mago",
        "unique": True,
        "class_req": ["mago"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["mago", "geral"],
        "damage_info": {"type": "arcano", "min_damage": 15, "max_damage": 20},
    },

    # ---------- Armaduras (Alfaiate) ----------
    "work_chapeu_seda_mago": {
        "display_name": "Chapéu de Seda do Mago",
        "emoji": "🎩",
        "profession": "alfaiate",
        "level_req": 5,
        "time_seconds": 300,  # 5 minutos
        "xp_gain": 20,
        "inputs": {"linho": 10, "pano_simples": 5, "nucleo_forja_fraco": 1},
        "result_base_id": "chapeu_seda_mago",
        "unique": True,
        "class_req": ["mago"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["mago", "geral"],
    },
    "work_tunica_seda_mago": {
        "display_name": "Túnica de Seda do Mago",
        "emoji": "👕",
        "profession": "alfaiate",
        "level_req": 7,
        "time_seconds": 600,  # 10 minutos
        "xp_gain": 35,
        "inputs": {"linho": 20, "pano_simples": 10, "nucleo_forja_fraco": 1},
        "result_base_id": "tunica_seda_mago",
        "unique": True,
        "class_req": ["mago"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["mago", "geral"],
    },
    "work_calcas_seda_mago": {
        "display_name": "Calças de Seda do Mago",
        "emoji": "👖",
        "profession": "alfaiate",
        "level_req": 6,
        "time_seconds": 420,  # 7 minutos
        "xp_gain": 30,
        "inputs": {"linho": 15, "pano_simples": 8, "nucleo_forja_fraco": 1},
        "result_base_id": "calcas_seda_mago",
        "unique": True,
        "class_req": ["mago"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["mago", "geral"],
    },
    "work_botas_seda_mago": {
        "display_name": "Botas de Seda do Mago",
        "emoji": "🥾",
        "profession": "alfaiate",
        "level_req": 5,
        "time_seconds": 240,  # 4 minutos
        "xp_gain": 15,
        "inputs": {"linho": 8, "pano_simples": 3, "nucleo_forja_fraco": 1},
        "result_base_id": "botas_seda_mago",
        "unique": True,
        "class_req": ["mago"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["mago", "geral"],
    },
    "work_luvas_seda_mago": {
        "display_name": "Luvas de Seda do Mago",
        "emoji": "🧤",
        "profession": "alfaiate",
        "level_req": 5,
        "time_seconds": 240,  # 4 minutos
        "xp_gain": 15,
        "inputs": {"linho": 8, "pano_simples": 3, "nucleo_forja_fraco": 1},
        "result_base_id": "luvas_seda_mago",
        "unique": True,
        "class_req": ["mago"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["mago", "geral"],
    },

    # ---------- Acessórios (Joalheiro) ----------
    "work_anel_gema_mago": {
        "display_name": "Anel de Gema do Mago",
        "emoji": "💍",
        "profession": "joalheiro",
        "level_req": 5,
        "time_seconds": 360,  # 6 minutos
        "xp_gain": 40,
        "inputs": {"fio_de_prata": 3, "gema_bruta": 2, "nucleo_forja_fraco": 1},
        "result_base_id": "anel_gema_mago",
        "unique": True,
        "class_req": ["mago"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["mago", "geral"],
    },
    "work_colar_gema_mago": {
        "display_name": "Colar de Gema do Mago",
        "emoji": "📿",
        "profession": "joalheiro",
        "level_req": 9,
        "time_seconds": 450,  # 7.5 minutos
        "xp_gain": 50,
        "inputs": {"fio_de_prata": 4, "gema_bruta": 3, "nucleo_forja_fraco": 1},
        "result_base_id": "colar_gema_mago",
        "unique": True,
        "class_req": ["mago"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["mago", "geral"],
    },
    "work_brinco_gema_mago": {
        "display_name": "Brinco de Gema do Mago",
        "emoji": "🧿",
        "profession": "joalheiro",
        "level_req": 7,
        "time_seconds": 300,  # 5 minutos
        "xp_gain": 35,
        "inputs": {"fio_de_prata": 2, "gema_bruta": 1, "nucleo_forja_fraco": 1},
        "result_base_id": "brinco_gema_mago",
        "unique": True,
        "class_req": ["mago"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["mago", "geral"],
    },
}
