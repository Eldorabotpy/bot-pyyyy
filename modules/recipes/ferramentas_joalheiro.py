# modules/recipes/ferramentas_joalheiro.py

RECIPES = {

    "craft_ferramentas_joalheiro_t1": {
        "display_name": "Montar Ferramentas do Lapidador Iniciante",
        "profession_req": "ferreiro",
        "required_tool_type": "ferreiro",
        "required_tool_tier": 1,
        "level_req": 10,
        "materials": {"barra_de_ferro": 8, "pedra": 10, "nucleo_forja_fraco": 1},
        "result_base_id": "ferramentas_joalheiro_t1",
        "xp_gain": 16
    },

    "craft_ferramentas_joalheiro_t2": {
        "display_name": "Montar Kit de Polimento Refinado",
        "profession_req": "ferreiro",
        "required_tool_type": "ferreiro",
        "required_tool_tier": 1,
        "level_req": 22,
        "materials": {"barra_de_ferro": 14, "linho": 8, "nucleo_forja_fraco": 1},
        "result_base_id": "ferramentas_joalheiro_t2",
        "xp_gain": 26
    },

    "craft_ferramentas_joalheiro_t3": {
        "display_name": "Montar Ferramentas do Ourives Experiente",
        "profession_req": "ferreiro",
        "required_tool_type": "ferreiro",
        "required_tool_tier": 2,
        "level_req": 45,
        "materials": {"barra_de_aco": 14, "linho": 12, "nucleo_forja_fraco": 1},
        "result_base_id": "ferramentas_joalheiro_t3",
        "xp_gain": 44
    },

    "craft_ferramentas_joalheiro_t4": {
        "display_name": "Montar Conjunto de Mithril do Mestre Ourives",
        "profession_req": "ferreiro",
        "required_tool_type": "ferreiro",
        "required_tool_tier": 3,
        "level_req": 65,
        "materials": {"barra_de_mithril": 18, "linho": 16, "nucleo_forja_fraco": 1},
        "result_base_id": "ferramentas_joalheiro_t4",
        "xp_gain": 66
    },

    "craft_ferramentas_joalheiro_t5": {
        "display_name": "Montar Ferramentas Rúnicas do Joalheiro Arcano",
        "profession_req": "ferreiro",
        "required_tool_type": "ferreiro",
        "required_tool_tier": 4,
        "level_req": 90,
        "materials": {"barra_de_adamantio": 20, "linho": 20, "nucleo_forja_fraco": 1},
        "result_base_id": "ferramentas_joalheiro_t5",
        "xp_gain": 92
    },
}
