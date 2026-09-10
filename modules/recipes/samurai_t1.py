# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any

# TIER 1: RECEITAS 
# ============================================================================

RECIPES: Dict[str, Dict[str, Any]] = {
    # --- Arma (Armeiro) ---
    "work_katana_laminada_samurai": {
        "display_name": "Katana Laminada",
        "emoji": "⚔️",
        "profession": "armeiro",
        "level_req": 5,  # Katanas exigem mais habilidade
        "time_seconds": 720,  # 12 minutos
        "xp_gain": 45,
        "inputs": {"barra_de_ferro": 5, "couro_curtido": 3, "pano_simples": 2, "nucleo_de_forja": 1},
        "result_base_id": "katana_laminada_samurai",
        "unique": True,
        "class_req": ["samurai"],
        "affix_pools_to_use": ["samurai", "geral"],
        "damage_info": {"type": "cortante", "min_damage": 15, "max_damage": 20},
    },

    # --- Armadura Laminada (Ferreiro) ---
    "work_kabuto_laminado_samurai": {
        "display_name": "Kabuto Laminado",
        "emoji": "🪖",
        "profession": "ferreiro",
        "level_req": 6,
        "time_seconds": 480,  # 8 minutos
        "xp_gain": 25,
        "inputs": {"barra_de_ferro": 6, "couro_curtido": 3, "pano_simples": 2, "nucleo_de_forja": 1},
        "result_base_id": "kabuto_laminado_samurai",
        "unique": True,
        "class_req": ["samurai"],
        "affix_pools_to_use": ["samurai", "geral"],
    },
    "work_do_laminado_samurai": {
        "display_name": "Do Laminado",
        "emoji": "👕",
        "profession": "ferreiro",
        "level_req": 7,
        "time_seconds": 600,  # 10 minutos
        "xp_gain": 35,
        "inputs": {"barra_de_ferro": 12, "couro_curtido": 6, "pano_simples": 4, "nucleo_de_forja": 1},
        "result_base_id": "do_laminado_samurai",
        "unique": True,
        "class_req": ["samurai"],
        "affix_pools_to_use": ["samurai", "geral"],
    },
    "work_haidate_laminado_samurai": {
        "display_name": "Haidate Laminado",
        "emoji": "👖",
        "profession": "ferreiro",
        "level_req": 7,
        "time_seconds": 540,  # 9 minutos
        "xp_gain": 30,
        "inputs": {"barra_de_ferro": 9, "couro_curtido": 5, "pano_simples": 3, "nucleo_de_forja": 1},
        "result_base_id": "haidate_laminado_samurai",
        "unique": True,
        "class_req": ["samurai"],
        "affix_pools_to_use": ["samurai", "geral"],
    },
    "work_suneate_laminado_samurai": {
        "display_name": "Suneate Laminado",
        "emoji": "🥾",
        "profession": "ferreiro",
        "level_req": 5,
        "time_seconds": 300,  # 5 minutos
        "xp_gain": 18,
        "inputs": {"barra_de_ferro": 4, "couro_curtido": 2, "pano_simples": 1, "nucleo_de_forja": 1},
        "result_base_id": "suneate_laminado_samurai",
        "unique": True,
        "class_req": ["samurai"],
        "affix_pools_to_use": ["samurai", "geral"],
    },
    "work_kote_laminado_samurai": {
        "display_name": "Kote Laminado",
        "emoji": "🧤",
        "profession": "ferreiro",
        "level_req": 5,
        "time_seconds": 300,  # 5 minutos
        "xp_gain": 18,
        "inputs": {"barra_de_ferro": 4, "couro_curtido": 2, "pano_simples": 1, "nucleo_de_forja": 1},
        "result_base_id": "kote_laminado_samurai",
        "unique": True,
        "class_req": ["samurai"],
        "affix_pools_to_use": ["samurai", "geral"],
    },

    # --- Acessórios do Clã (Ferreiro) ---
    "work_anel_laminado_samurai": {
        "display_name": "Anel Laminado",
        "emoji": "💍",
        "profession": "joalheiro",
        "level_req": 5,
        "time_seconds": 400,  # ~6.5 minutos
        "xp_gain": 40,
        "inputs": {"barra_de_ferro": 2, "gema_bruta": 1, "nucleo_de_forja": 1},
        "result_base_id": "anel_laminado_samurai",
        "unique": True,
        "class_req": ["samurai"],
        "affix_pools_to_use": ["samurai", "geral"],
    },
    "work_colar_laminado_samurai": {
        "display_name": "Colar Laminado",
        "emoji": "📿",
        "profession": "joalheiro",
        "level_req": 7,
        "time_seconds": 500,  # ~8 minutos
        "xp_gain": 50,
        "inputs": {"barra_de_ferro": 3, "gema_bruta": 2, "couro_curtido": 1, "nucleo_de_forja": 1},
        "result_base_id": "colar_laminado_samurai",
        "unique": True,
        "class_req": ["samurai"],
        "affix_pools_to_use": ["samurai", "geral"],
    },
    "work_brinco_laminado_samurai": {
        "display_name": "Brinco Laminado",
        "emoji": "🧿",
        "profession": "joalheiro",
        "level_req": 9,
        "time_seconds": 400,  # ~6.5 minutos
        "xp_gain": 40,
        "inputs": {"barra_de_ferro": 2, "gema_bruta": 1, "nucleo_de_forja": 1},
        "result_base_id": "brinco_laminado_samurai",
        "unique": True,
        "class_req": ["samurai"],
        "affix_pools_to_use": ["samurai", "geral"],
    },
}
