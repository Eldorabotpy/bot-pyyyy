# modules/recipes/guild_aventureiro.py
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Dict, Any


# ============================================================
# 🏅 CONJUNTO DO AVENTUREIRO
# GUILDA DOS AVENTUREIROS
# ============================================================
#
# Estas receitas NÃO são liberadas automaticamente.
#
# O jogador precisa comprar o desbloqueio permanente
# correspondente na Loja da Guilda.
#
# O crafting_engine valida:
#
# guild_missions.receitas_desbloqueadas
#
# ============================================================

RECIPES: Dict[str, Dict[str, Any]] = {

    # ========================================================
    # 🥾 FERRO — BOTAS
    # ========================================================

    "work_guild_aventureiro_botas": {

        "display_name":
            "Botas do Aventureiro",

        "emoji":
            "🥾",

        "profession":
            "ferreiro",

        "level_req":
            5,

        "time_seconds":
            240,

        "xp_gain":
            15,

        "inputs": {
            "barra_de_ferro": 4,
            "couro_curtido": 2,
            "nucleo_de_forja": 1,
        },

        "result_base_id":
            "botas_aventureiro_guilda",

        "unique":
            True,

        "unlock_id":
            "guild_aventureiro_botas",
    },


    # ========================================================
    # 🧤 BRONZE — LUVAS
    # ========================================================

    "work_guild_aventureiro_luvas": {

        "display_name":
            "Luvas do Aventureiro",

        "emoji":
            "🧤",

        "profession":
            "ferreiro",

        "level_req":
            10,

        "time_seconds":
            300,

        "xp_gain":
            20,

        "inputs": {
            "barra_de_ferro": 5,
            "couro_curtido": 2,
            "nucleo_de_forja": 1,
        },

        "result_base_id":
            "luvas_aventureiro_guilda",

        "unique":
            True,

        "unlock_id":
            "guild_aventureiro_luvas",
    },


    # ========================================================
    # 👖 PRATA — CALÇAS
    # ========================================================

    "work_guild_aventureiro_calcas": {

        "display_name":
            "Calças do Aventureiro",

        "emoji":
            "👖",

        "profession":
            "ferreiro",

        "level_req":
            15,

        "time_seconds":
            420,

        "xp_gain":
            30,

        "inputs": {
            "barra_de_ferro": 8,
            "couro_curtido": 3,
            "nucleo_de_forja": 1,
        },

        "result_base_id":
            "calcas_aventureiro_guilda",

        "unique":
            True,

        "unlock_id":
            "guild_aventureiro_calcas",
    },


    # ========================================================
    # 👕 OURO — COURAÇA
    # ========================================================

    "work_guild_aventureiro_couraca": {

        "display_name":
            "Couraça do Aventureiro",

        "emoji":
            "👕",

        "profession":
            "ferreiro",

        "level_req":
            20,

        "time_seconds":
            600,

        "xp_gain":
            40,

        "inputs": {
            "barra_de_ferro": 12,
            "couro_curtido": 4,
            "nucleo_de_forja": 1,
        },

        "result_base_id":
            "couraca_aventureiro_guilda",

        "unique":
            True,

        "unlock_id":
            "guild_aventureiro_couraca",
    },


    # ========================================================
    # 🪖 PLATINA — ELMO
    # ========================================================

    "work_guild_aventureiro_elmo": {

        "display_name":
            "Elmo do Aventureiro",

        "emoji":
            "🪖",

        "profession":
            "ferreiro",

        "level_req":
            25,

        "time_seconds":
            720,

        "xp_gain":
            50,

        "inputs": {
            "barra_de_ferro": 8,
            "couro_curtido": 3,
            "nucleo_de_forja": 2,
        },

        "result_base_id":
            "elmo_aventureiro_guilda",

        "unique":
            True,

        "unlock_id":
            "guild_aventureiro_elmo",
    },
}