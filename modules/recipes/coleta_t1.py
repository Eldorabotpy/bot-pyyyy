# modules/recipes/coleta_t1.py
from __future__ import annotations
from typing import Dict, Any

# TIER 1: RECEITAS 
# ============================================================================

RECIPES: Dict[str, Dict[str, Any]] = {
    # ==========================
    # 🪓 LENHADOR TIER 1 (Pedra)
    # ==========================
    "machado_pedra": {
        "display_name": "Machado de Pedra",
        "description": "Ferramenta primitiva. Quebra rápido.",
        "type": "tool",
        "sub_type": "lenhador",
        "tier": 1,
        "profession_req": "ferreiro",     # Qualquer um pode fazer
        "level_req": 1,
        "ingredients": {
            "pedra": 3,             # Cabeça do machado
            "madeira": 2,           # Cabo
            "linho": 1,              # Amarra (dropa de plantas ou monstros iniciais)
            "nucleo_de_forja": 1
        },
        "gold_cost": 50,
        "craft_time": 20,           # Rápido
        "xp_reward": 10
    },

    # ==========================
    # ⛏️ MINERADOR TIER 1 (Pedra)
    # ==========================
    "picareta_pedra": {
        "display_name": "Picareta de Pedra",
        "description": "Pedra amarrada num graveto. Funciona... por enquanto.",
        "type": "tool",
        "sub_type": "minerador",
        "tier": 1,
        "profession_req": "ferreiro",
        "level_req": 1,
        "ingredients": {
            "pedra": 4,
            "madeira": 2,
            "linho": 1,
            "nucleo_de_forja": 1
        },
        "gold_cost": 50,
        "craft_time": 20,
        "xp_reward": 10
    },

    # ==========================
    # 🌾 COLHEDOR TIER 1 (Pedra Lascada)
    # ==========================
    "foice_pedra": {
        "display_name": "Foice de Pedra Lascada",
        "description": "Corte irregular, mas colhe plantas.",
        "type": "tool",
        "sub_type": "colhedor",
        "tier": 1,
        "profession_req": "ferreiro",
        "level_req": 1,
        "ingredients": {
            "pedra": 2,             # Lâmina lascada
            "madeira": 3,            # Cabo longo
            "nucleo_de_forja": 1
        },
        "gold_cost": 40,
        "craft_time": 15,
        "xp_reward": 8
    },

    # ==========================
    # 🗡️ ESFOLADOR TIER 1 (Pederneira)
    # ==========================
    "faca_pedra": {
        "display_name": "Faca de Pederneira",
        "description": "Afiada o suficiente para tirar peles.",
        "type": "tool",
        "sub_type": "esfolador",
        "tier": 1,
        "profession_req": "ferreiro",
        "level_req": 1,
        "ingredients": {
            "pedra": 1,
            "madeira": 1,
            "pano_simples": 1,       # Dropa de monstros T1 (Ex: Goblins/Bandidos)
            "nucleo_de_forja": 1
        },
        "gold_cost": 40,
        "craft_time": 15,
        "xp_reward": 8
    },

    # ==========================
    # 🧪 ALQUIMISTA TIER 1 (Vidro Rústico)
    # ==========================
    "frasco_vidro": {
        "display_name": "Frasco de Vidro",
        "description": "Vidro simples feito de areia derretida.",
        "type": "tool",
        "sub_type": "alquimista",
        "tier": 1,
        "profession_req": "joalheiro",
        "level_req": 1,
        "ingredients": {
            "pedra": 3,             # Simbolizando areia/sílica
            "carvao": 1,
            "nucleo_de_forja": 1                          # Combustível para derreter
        },
        "gold_cost": 30,
        "craft_time": 30,
        "xp_reward": 15
    }
}