# modules/recipes/coleta_t4.py

from __future__ import annotations
from typing import Dict, Any

# TIER 4: RECEITAS 
# ============================================================================

RECIPES: Dict[str, Dict[str, Any]] = {
    # ==========================
    # 🪓 LENHADOR TIER 4 (Mithril/Élfico)
    # ==========================
    "machado_mithril": {
        "display_name": "Machado de Mithril",
        "description": "Leve como pluma, corta aço como papel.",
        "type": "tool",
        "sub_type": "lenhador",
        "tier": 4,
        "profession_req": "ferreiro",
        "level_req": 25,
        "ingredients": {
            "barra_de_prata": 5,        # Base metálica condutora
            "cristal_mana": 2,          # Infusão mágica (transforma em Mithril)
            "madeira_elfica": 2,        # Cabo raro
            "veludo_runico": 1,          # Empunhadura mágica
            "nucleo_de_forja": 1
        },
        "gold_cost": 5000,
        "craft_time": 300,              # 5 minutos
        "xp_reward": 500
    },

    # ==========================
    # ⛏️ MINERADOR TIER 4 (Mithril)
    # ==========================
    "picareta_mithril": {
        "display_name": "Picareta de Mithril",
        "description": "Ressoa com a magia da terra.",
        "type": "tool",
        "sub_type": "minerador",
        "tier": 4,
        "profession_req": "ferreiro",
        "level_req": 25,
        "ingredients": {
            "barra_de_prata": 6,
            "cristal_mana": 3,
            "madeira_elfica": 2,
            "nucleo_de_energia_instavel": 1,
            "barra_de_mithril": 3,
            "nucleo_de_forja": 1
        },
        "gold_cost": 5500,
        "craft_time": 300,
        "xp_reward": 550
    },

    # ==========================
    # 🌾 COLHEDOR TIER 4 (Mithril)
    # ==========================
    "foice_mithril": {
        "display_name": "Foice de Mithril",
        "description": "Colhe a essência da planta, não apenas o corpo.",
        "type": "tool",
        "sub_type": "colhedor",
        "tier": 4,
        "profession_req": "ferreiro",
        "level_req": 25,
        "ingredients": {
            "barra_de_prata": 4,
            "cristal_mana": 2,
            "madeira_elfica": 3,
            "essencia_fungica": 2,       # Item refinado de alquimia
            "barra_de_mithril": 3,
            "nucleo_de_forja": 1
        },
        "gold_cost": 4800,
        "craft_time": 280,
        "xp_reward": 480
    },

    # ==========================
    # 🗡️ ESFOLADOR TIER 4 (Obsidiana)
    # ==========================
    "faca_obsidiana": {
        "display_name": "Lâmina de Obsidiana",
        "description": "Mais afiada que qualquer metal. Extremamente frágil se não for mágica.",
        "type": "tool",
        "sub_type": "esfolador",
        "tier": 4,
        "profession_req": "ferreiro",  # Requer precisão de joalheiro
        "level_req": 25,
        "ingredients": {
            "obsidiana_ancestral": 3,   # Drop raro de mineração
            "couro_dragao": 1,          # Drop de esfolamento T3+
            "fio_de_prata": 4,           # Para amarrar a lâmina
            "barra_de_mithril": 3,
            "nucleo_de_forja": 1
        },
        "gold_cost": 4500,
        "craft_time": 250,
        "xp_reward": 450
    },

    # ==========================
    # 🧪 ALQUIMISTA TIER 4 (Rúnico)
    # ==========================
    "coletor_runico": {
        "display_name": "Coletor Rúnico",
        "description": "Atrai espíritos e energias instáveis.",
        "type": "tool",
        "sub_type": "alquimista",
        "tier": 4,
        "profession_req": "joalheiro",   # Foco em tecidos mágicos e runas
        "level_req": 25,
        "ingredients": {
            "veludo_runico": 4,         # Bolsa de contenção
            "cristal_mana": 2,
            "essencia_espiritual": 2,    # Ectoplasma refinado
            "barra_de_mithril": 3,
            "nucleo_de_forja": 1
        },
        "gold_cost": 4200,
        "craft_time": 240,
        "xp_reward": 420
    }
}