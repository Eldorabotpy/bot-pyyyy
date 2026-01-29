# modules/recipes/ferramentas_fundidor.py

RECIPES = {

    "craft_ferramentas_fundidor_t1": {
        "display_name": "Montar Tenaz do Fundidor Iniciante",
        "profession_req": "ferreiro",
        "required_tool_type": "ferreiro",
        "required_tool_tier": 1,
        "level_req": 11,
        "materials": {"barra_de_ferro": 8, "pedra": 8, "nucleo_forja_fraco": 1},
        "result_base_id": "ferramentas_fundidor_t1",
        "xp_gain": 18
    },

    "craft_ferramentas_fundidor_t2": {
        "display_name": "Montar Moldes de Ferro do Fundidor",
        "profession_req": "ferreiro",
        "required_tool_type": "ferreiro",
        "required_tool_tier": 1,
        "level_req": 24,
        "materials": {"barra_de_ferro": 16, "pedra": 10, "nucleo_forja_fraco": 1},
        "result_base_id": "ferramentas_fundidor_t2",
        "xp_gain": 28
    },

    "craft_ferramentas_fundidor_t3": {
        "display_name": "Montar Conjunto de Fundição do Artesão",
        "profession_req": "ferreiro",
        "required_tool_type": "ferreiro",
        "required_tool_tier": 2,
        "level_req": 48,
        "materials": {"barra_de_aco": 16, "pedra": 12, "nucleo_forja_fraco": 1},
        "result_base_id": "ferramentas_fundidor_t3",
        "xp_gain": 46
    },

    "craft_ferramentas_fundidor_t4": {
        "display_name": "Montar Tenazes de Mithril e Moldes Finos",
        "profession_req": "ferreiro",
        "required_tool_type": "ferreiro",
        "required_tool_tier": 3,
        "level_req": 70,
        "materials": {"barra_de_mithril": 20, "pedra": 14, "nucleo_forja_fraco": 1},
        "result_base_id": "ferramentas_fundidor_t4",
        "xp_gain": 70
    },

    "craft_ferramentas_fundidor_t5": {
        "display_name": "Montar Instrumentos do Fundidor Vulcânico",
        "profession_req": "ferreiro",
        "required_tool_type": "ferreiro",
        "required_tool_tier": 4,
        "level_req": 95,
        "materials": {"barra_de_adamantio": 22, "pedra": 16, "nucleo_forja_fraco": 1},
        "result_base_id": "ferramentas_fundidor_t5",
        "xp_gain": 98
    },
}
