# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict
from modules import crafting_registry

# RARIDADE TIER 1
RARITY_T1 = {
    "comum": 0.90,     # Aumentei para 90% (mais lixo)
    "bom": 0.09,       # Diminuí para 9%
    "raro": 0.009,     # 0.9%
    "epico": 0.0009,   # 0.09%
    "lendario": 0.0001 # 0.01% (Extremamente raro)
}

# TIER 1: CONJUNTO SIMPLES DO BARDO (Profissão 5+)
# ============================================================

RECIPES: Dict[str, Dict] = {
    "work_alaude_simples_bardo": {
        "display_name": "Alaúde Simples do Bardo",
        "emoji": "🎻",
        "profession": "armeiro",
        "level_req": 5,
        "time_seconds": 600,
        "xp_gain": 30,
        "inputs": {"madeira": 12, "linho": 8, "nucleo_forja_fraco": 1},
        "result_base_id": "alaude_simples_bardo",
        "unique": True,
        "class_req": ["bardo"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["bardo", "geral"],
        "damage_info": {"type": "sonico", "min_damage": 10, "max_damage": 15},
    },

    # Vestes de Viajante (Curtidor/Alfaiate)
    "work_chapeu_elegante_bardo": {
        "display_name": "Chapéu Elegante do Bardo",
        "emoji": "🎩",
        "profession": "curtidor",
        "level_req": 5,
        "time_seconds": 300,
        "xp_gain": 20,
        "inputs": {"couro_curtido": 4, "pano_simples": 4, "pena": 3, "nucleo_forja_fraco": 1},
        "result_base_id": "chapeu_elegante_bardo",
        "unique": True,
        "class_req": ["bardo"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["bardo", "geral"],
    },
    "work_colete_viajante_bardo": {
        "display_name": "Colete de Viajante do Bardo",
        "emoji": "👕",
        "profession": "curtidor",
        "level_req": 7,
        "time_seconds": 600,
        "xp_gain": 35,
        "inputs": {"couro_curtido": 8, "pano_simples": 6, "nucleo_forja_fraco": 1},
        "result_base_id": "colete_viajante_bardo",
        "unique": True,
        "class_req": ["bardo"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["bardo", "geral"],
    },
    "work_calcas_linho_bardo": {
        "display_name": "Calças de Linho do Bardo",
        "emoji": "👖",
        "profession": "alfaiate",
        "level_req": 6,
        "time_seconds": 420,
        "xp_gain": 30,
        "inputs": {"linho": 10, "pano_simples": 6, "nucleo_forja_fraco": 1},
        "result_base_id": "calcas_linho_bardo",
        "unique": True,
        "class_req": ["bardo"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["bardo", "geral"],
    },
    "work_botas_macias_bardo": {
        "display_name": "Botas Macias do Bardo",
        "emoji": "🥾",
        "profession": "curtidor",
        "level_req": 5,
        "time_seconds": 240,
        "xp_gain": 15,
        "inputs": {"couro_curtido": 5, "pano_simples": 2, "nucleo_forja_fraco": 1},
        "result_base_id": "botas_macias_bardo",
        "unique": True,
        "class_req": ["bardo"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["bardo", "geral"],
    },
    "work_luvas_sem_dedos_bardo": {
        "display_name": "Luvas sem Dedos do Bardo",
        "emoji": "🧤",
        "profession": "curtidor",
        "level_req": 5,
        "time_seconds": 240,
        "xp_gain": 15,
        "inputs": {"couro_curtido": 5, "pano_simples": 2, "nucleo_forja_fraco": 1},
        "result_base_id": "luvas_sem_dedos_bardo",
        "unique": True,
        "class_req": ["bardo"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["bardo", "geral"],
    },

    # Acessórios Melódicos (Joalheiro)
    "work_anel_melodico_bardo": {
        "display_name": "Anel Melódico do Bardo",
        "emoji": "💍",
        "profession": "joalheiro",
        "level_req": 8,
        "time_seconds": 360,
        "xp_gain": 40,
        "inputs": {"fio_de_prata": 3, "gema_bruta": 1, "nucleo_forja_fraco": 1},
        "result_base_id": "anel_melodico_bardo",
        "unique": True,
        "class_req": ["bardo"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["bardo", "geral"],
    },
    "work_colar_melodico_bardo": {
        "display_name": "Colar Melódico do Bardo",
        "emoji": "📿",
        "profession": "joalheiro",
        "level_req": 6,
        "time_seconds": 450,
        "xp_gain": 50,
        "inputs": {"fio_de_prata": 4, "gema_bruta": 2, "pena": 2, "nucleo_forja_fraco": 1},
        "result_base_id": "colar_melodico_bardo",
        "unique": True,
        "class_req": ["bardo"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["bardo", "geral"],
    },
    "work_brinco_melodico_bardo": {
        "display_name": "Brinco Melódico do Bardo",
        "emoji": "🧿",
        "profession": "joalheiro",
        "level_req": 8,
        "time_seconds": 300,
        "xp_gain": 35,
        "inputs": {"fio_de_prata": 2, "gema_bruta": 1, "nucleo_forja_fraco": 1},
        "result_base_id": "brinco_melodico_bardo",
        "unique": True,
        "class_req": ["bardo"],
        "rarity_chances": dict(RARITY_T1),
        "affix_pools_to_use": ["bardo", "geral"],
    },
}

def register_all() -> None:
    """Registra todas as receitas deste pacote no registry central."""
    for rid, data in RECIPES.items():
        crafting_registry.register_recipe(rid, data)
