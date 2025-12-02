# -*- coding: utf-8 -*-
# =========================================
# TIER 2 — Conjunto do Mestre do Monge (Profissão 20+)
# =========================================

RARITY_T2 = {
    "comum": 0.90,     # Aumentei para 90% (mais lixo)
    "bom": 0.09,       # Diminuí para 9%
    "raro": 0.009,     # 0.9%
    "epico": 0.0009,   # 0.09%
    "lendario": 0.0001 # 0.01% (Extremamente raro)
}

RECIPES = {
    # --- Arma Focada (Armeiro) ---
    "work_manoplas_mestre_monge": {
        "display_name": "Manoplas de Mestre",
        "emoji": "🤜",
        "profession": "armeiro",
        "level_req": 20,
        "time_seconds": 1800,  # 30 minutos
        "xp_gain": 100,
        "inputs": {"couro_reforcado": 10, "madeira_rara": 5, "seiva_de_ent": 2, "nucleo_forja_comum": 1},
        "result_base_id": "manoplas_mestre_monge",
        "unique": True,
        "class_req": ["monge"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["monge", "geral"],
        "damage_info": {"type": "esmagamento", "min_damage": 35, "max_damage": 45},
    },

    # --- Vestes Iluminadas (Alfaiate / Curtidor) ---
    "work_bandana_mestre_monge": {
        "display_name": "Bandana de Mestre",
        "emoji": "🪖",
        "profession": "alfaiate",
        "level_req": 20,
        "time_seconds": 1200,  # 20 minutos
        "xp_gain": 80,
        "inputs": {"veludo_runico": 10, "fio_de_prata": 4, "nucleo_forja_comum": 1},
        "result_base_id": "bandana_mestre_monge",
        "unique": True,
        "class_req": ["monge"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["monge", "geral"],
    },
    "work_gi_mestre_monge": {
        "display_name": "Gi de Mestre",
        "emoji": "👕",
        "profession": "alfaiate",
        "level_req": 22,
        "time_seconds": 2400,  # 40 minutos
        "xp_gain": 150,
        "inputs": {"veludo_runico": 20, "fio_de_prata": 8, "ectoplasma": 3, "nucleo_forja_comum": 1},
        "result_base_id": "gi_mestre_monge",
        "unique": True,
        "class_req": ["monge"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["monge", "geral"],
    },
    "work_calcas_mestre_monge": {
        "display_name": "Calças de Mestre",
        "emoji": "👖",
        "profession": "alfaiate",
        "level_req": 21,
        "time_seconds": 1500,  # 25 minutos
        "xp_gain": 120,
        "inputs": {"veludo_runico": 15, "fio_de_prata": 6, "nucleo_forja_comum": 1},
        "result_base_id": "calcas_mestre_monge",
        "unique": True,
        "class_req": ["monge"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["monge", "geral"],
    },
    "work_sandalias_mestre_monge": {
        "display_name": "Sandálias de Mestre",
        "emoji": "🥾",
        "profession": "curtidor",
        "level_req": 20,
        "time_seconds": 900,  # 15 minutos
        "xp_gain": 70,
        "inputs": {"couro_reforcado": 8, "seiva_de_ent": 1, "nucleo_forja_comum": 1},
        "result_base_id": "sandalias_mestre_monge",
        "unique": True,
        "class_req": ["monge"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["monge", "geral"],
    },
    "work_faixas_mestre_monge": {
        "display_name": "Faixas de Mão de Mestre",
        "emoji": "🧤",
        "profession": "alfaiate",
        "level_req": 20,
        "time_seconds": 900,  # 15 minutos
        "xp_gain": 70,
        "inputs": {"veludo_runico": 8, "ectoplasma": 1, "nucleo_forja_comum": 1},
        "result_base_id": "faixas_mestre_monge",
        "unique": True,
        "class_req": ["monge"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["monge", "geral"],
    },

    # --- Acessórios de Iluminação (Joalheiro) ---
    "work_anel_mestre_monge": {
        "display_name": "Anel de Mestre",
        "emoji": "💍",
        "profession": "joalheiro",
        "level_req": 23,
        "time_seconds": 1380,  # ~23 minutos
        "xp_gain": 115,
        "inputs": {"madeira_rara": 2, "gema_polida": 1, "ectoplasma": 2, "nucleo_forja_comum": 1},
        "result_base_id": "anel_mestre_monge",
        "unique": True,
        "class_req": ["monge"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["monge", "geral"],
    },
    "work_colar_mestre_monge": {
        "display_name": "Colar de Mestre",
        "emoji": "📿",
        "profession": "joalheiro",
        "level_req": 24,
        "time_seconds": 1560,  # 26 minutos
        "xp_gain": 140,
        "inputs": {"madeira_rara": 3, "gema_polida": 2, "seiva_de_ent": 1, "nucleo_forja_comum": 1},
        "result_base_id": "colar_mestre_monge",
        "unique": True,
        "class_req": ["monge"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["monge", "geral"],
    },
    "work_brinco_mestre_monge": {
        "display_name": "Brinco de Mestre",
        "emoji": "🧿",
        "profession": "joalheiro",
        "level_req": 23,
        "time_seconds": 1200,  # 20 minutos
        "xp_gain": 100,
        "inputs": {"madeira_rara": 1, "gema_polida": 1, "ectoplasma": 1, "nucleo_forja_comum": 1},
        "result_base_id": "brinco_mestre_monge",
        "unique": True,
        "class_req": ["monge"],
        "rarity_chances": dict(RARITY_T2),
        "affix_pools_to_use": ["monge", "geral"],
    },
}
