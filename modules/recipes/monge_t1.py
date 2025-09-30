# -*- coding: utf-8 -*-

# RARIDADE TIER 1 (comum, bom, raro, epico, lendario)
RARITY_T1 = {
    "comum": 0.80,
    "bom": 0.18,
    "raro": 0.018,
    "epico": 0.0018,
    "lendario": 0.0002,
}

# TIER 1: RECEITAS DO CONJUNTO DO INICIADO DO MONGE (Nível de Profissão 5+)
# ============================================================================

RECIPES = {
    "work_manoplas_iniciado_monge": {
        "display_name": "Manoplas de Iniciado",
        "emoji": "🤜",
        "profession": "armeiro",
        "level_req": 5,
        "time_seconds": 480,  # 8 minutos
        "xp_gain": 28,
        "inputs": {"couro_curtido": 6, "madeira": 4, "nucleo_forja_fraco": 1},
        "result_base_id": "manoplas_iniciado_monge",
        "unique": True,
        "class_req": ["monge"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["monge", "geral"],
        "damage_info": {"type": "esmagamento", "min_damage": 13, "max_damage": 17},
    },

    # --- Vestes de Treino (Alfaiate) ---
    "work_bandana_iniciado_monge": {
        "display_name": "Bandana de Iniciado",
        "emoji": "🪖",
        "profession": "alfaiate",
        "level_req": 5,
        "time_seconds": 300,  # 5 minutos
        "xp_gain": 20,
        "inputs": {"linho": 8, "pano_simples": 4, "nucleo_forja_fraco": 1},
        "result_base_id": "bandana_iniciado_monge",
        "unique": True,
        "class_req": ["monge"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["monge", "geral"],
    },
    "work_gi_iniciado_monge": {
        "display_name": "Gi de Iniciado",
        "emoji": "👕",
        "profession": "alfaiate",
        "level_req": 7,
        "time_seconds": 600,  # 10 minutos
        "xp_gain": 35,
        "inputs": {"linho": 15, "pano_simples": 8, "nucleo_forja_fraco": 1},
        "result_base_id": "gi_iniciado_monge",
        "unique": True,
        "class_req": ["monge"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["monge", "geral"],
    },
    "work_calcas_iniciado_monge": {
        "display_name": "Calças de Iniciado",
        "emoji": "👖",
        "profession": "alfaiate",
        "level_req": 6,
        "time_seconds": 420,  # 7 minutos
        "xp_gain": 30,
        "inputs": {"linho": 12, "pano_simples": 6, "nucleo_forja_fraco": 1},
        "result_base_id": "calcas_iniciado_monge",
        "unique": True,
        "class_req": ["monge"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["monge", "geral"],
    },
    "work_sandalias_iniciado_monge": {
        "display_name": "Sandálias de Iniciado",
        "emoji": "🥾",
        "profession": "curtidor",
        "level_req": 5,
        "time_seconds": 240,  # 4 minutos
        "xp_gain": 15,
        "inputs": {"couro_curtido": 4, "linho": 2, "nucleo_forja_fraco": 1},
        "result_base_id": "sandalias_iniciado_monge",
        "unique": True,
        "class_req": ["monge"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["monge", "geral"],
    },
    "work_faixas_iniciado_monge": {
        "display_name": "Faixas de Mão de Iniciado",
        "emoji": "🧤",
        "profession": "alfaiate",
        "level_req": 5,
        "time_seconds": 240,  # 4 minutos
        "xp_gain": 15,
        "inputs": {"linho": 6, "pano_simples": 3, "nucleo_forja_fraco": 1},
        "result_base_id": "faixas_iniciado_monge",
        "unique": True,
        "class_req": ["monge"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["monge", "geral"],
    },

    # --- Acessórios de Meditação (Artífice) ---
    "work_anel_iniciado_monge": {
        "display_name": "Anel de Iniciado",
        "emoji": "💍",
        "profession": "joalheiro",
        "level_req": 5,
        "time_seconds": 360,  # 6 minutos
        "xp_gain": 40,
        "inputs": {"madeira_rara": 1, "seiva_de_ent": 1, "nucleo_forja_fraco": 1},
        "result_base_id": "anel_iniciado_monge",
        "unique": True,
        "class_req": ["monge"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["monge", "geral"],
    },
    "work_colar_iniciado_monge": {
        "display_name": "Colar de Iniciado",
        "emoji": "📿",
        "profession": "joalheiro",
        "level_req": 7,
        "time_seconds": 450,  # 7.5 minutos
        "xp_gain": 50,
        "inputs": {"madeira_rara": 2, "gema_bruta": 1, "linho": 2, "nucleo_forja_fraco": 1},
        "result_base_id": "colar_iniciado_monge",
        "unique": True,
        "class_req": ["monge"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["monge", "geral"],
    },
    "work_brinco_iniciado_monge": {
        "display_name": "Brinco de Iniciado",
        "emoji": "🧿",
        "profession": "joalheiro",
        "level_req": 9,
        "time_seconds": 300,  # 5 minutos
        "xp_gain": 35,
        "inputs": {"madeira_rara": 1, "gema_bruta": 1, "nucleo_forja_fraco": 1},
        "result_base_id": "brinco_iniciado_monge",
        "unique": True,
        "class_req": ["monge"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["monge", "geral"],
    },
}
