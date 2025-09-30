# modules/recipes/mago_t2.py
# -*- coding: utf-8 -*-
# =========================================
# TIER 2 — Receitas do Mago (nível prof. 20+)
# =========================================

# Padrão de raridade (comum, bom, raro, épico, lendário)
RARITY_T2 = {
    "comum": 0.72,
    "bom": 0.25,
    "raro": 0.025,
    "epico": 0.004,
    "lendario": 0.001,
}

RECIPES = {
    # ---------- Arma (Armeiro) ----------
    "work_cajado_arcano_mago": {
        "display_name": "Cajado Arcano",
        "emoji": "🪄",
        "profession": "armeiro",
        "level_req": 20,
        "time_seconds": 1800,  # 30 minutos
        "xp_gain": 100,
        # Obs.: usando madeira_rara (já existe no items.py) + gemas polidas
        "inputs": {"madeira_rara": 10, "gema_polida": 4, "nucleo_forja_comum": 1},
        "result_base_id": "cajado_arcano_mago",
        "unique": True,
        "class_req": ["mago"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["mago", "geral"],
        "damage_info": {"type": "arcano", "min_damage": 40, "max_damage": 55},
    },

    # ---------- Armaduras (Alfaiate) ----------
    "work_chapeu_veludo_mago": {
        "display_name": "Chapéu de Veludo do Mago",
        "emoji": "🎩",
        "profession": "alfaiate",
        "level_req": 20,
        "time_seconds": 1200,  # 20 minutos
        "xp_gain": 80,
        "inputs": {"veludo_runico": 12, "fio_de_prata": 5, "nucleo_forja_comum": 1},
        "result_base_id": "chapeu_veludo_mago",
        "unique": True,
        "class_req": ["mago"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["mago", "geral"],
    },
    "work_tunica_veludo_mago": {
        "display_name": "Túnica de Veludo do Mago",
        "emoji": "👕",
        "profession": "alfaiate",
        "level_req": 22,
        "time_seconds": 2400,  # 40 minutos
        "xp_gain": 150,
        "inputs": {"veludo_runico": 25, "fio_de_prata": 10, "nucleo_forja_comum": 1},
        "result_base_id": "tunica_veludo_mago",
        "unique": True,
        "class_req": ["mago"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["mago", "geral"],
    },
    "work_calcas_veludo_mago": {
        "display_name": "Calças de Veludo do Mago",
        "emoji": "👖",
        "profession": "alfaiate",
        "level_req": 21,
        "time_seconds": 1500,  # 25 minutos
        "xp_gain": 120,
        "inputs": {"veludo_runico": 18, "fio_de_prata": 8, "nucleo_forja_comum": 1},
        "result_base_id": "calcas_veludo_mago",
        "unique": True,
        "class_req": ["mago"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["mago", "geral"],
    },
    "work_botas_veludo_mago": {
        "display_name": "Botas de Veludo do Mago",
        "emoji": "🥾",
        "profession": "alfaiate",
        "level_req": 20,
        "time_seconds": 900,  # 15 minutos
        "xp_gain": 70,
        "inputs": {"veludo_runico": 10, "fio_de_prata": 4, "nucleo_forja_comum": 1},
        "result_base_id": "botas_veludo_mago",
        "unique": True,
        "class_req": ["mago"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["mago", "geral"],
    },
    "work_luvas_veludo_mago": {
        "display_name": "Luvas de Veludo do Mago",
        "emoji": "🧤",
        "profession": "alfaiate",
        "level_req": 20,
        "time_seconds": 900,  # 15 minutos
        "xp_gain": 70,
        "inputs": {"veludo_runico": 10, "fio_de_prata": 4, "nucleo_forja_comum": 1},
        "result_base_id": "luvas_veludo_mago",
        "unique": True,
        "class_req": ["mago"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["mago", "geral"],
    },

    # ---------- Acessórios (Joalheiro) ----------
    "work_anel_runico_mago": {
        "display_name": "Anel Rúnico do Mago",
        "emoji": "💍",
        "profession": "joalheiro",
        "level_req": 23,
        "time_seconds": 1300,  # ~22 minutos
        "xp_gain": 110,
        "inputs": {"barra_de_prata": 4, "gema_polida": 2, "nucleo_forja_comum": 1},
        "result_base_id": "anel_runico_mago",
        "unique": True,
        "class_req": ["mago"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["mago", "geral"],
    },
    "work_colar_runico_mago": {
        "display_name": "Colar Rúnico do Mago",
        "emoji": "📿",
        "profession": "joalheiro",
        "level_req": 24,
        "time_seconds": 1400,  # ~23 minutos
        "xp_gain": 130,
        "inputs": {"barra_de_prata": 3, "gema_polida": 3, "nucleo_forja_comum": 1},
        "result_base_id": "colar_runico_mago",
        "unique": True,
        "class_req": ["mago"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["mago", "geral"],
    },
    "work_brinco_runico_mago": {
        "display_name": "Brinco Rúnico do Mago",
        "emoji": "🧿",
        "profession": "joalheiro",
        "level_req": 23,
        "time_seconds": 1300,  # ~22 minutos
        "xp_gain": 110,
        "inputs": {"barra_de_prata": 2, "gema_polida": 1, "nucleo_forja_comum": 1},
        "result_base_id": "brinco_runico_mago",
        "unique": True,
        "class_req": ["mago"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["mago", "geral"],
    },
}
