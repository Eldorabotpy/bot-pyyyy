# modules/recipes/ferramentas_curtidor.py

RECIPES = {

    "craft_ferramentas_curtidor_t1": {
        "display_name": "Montar Raspador do Curtidor Iniciante",
        "profession_req": "ferreiro",
        "required_tool_type": "ferreiro",
        "required_tool_tier": 1,
        "level_req": 9,
        "materials": {"barra_de_ferro": 6, "madeira": 6, "nucleo_forja_fraco": 1},
        "result_base_id": "ferramentas_curtidor_t1",
        "xp_gain": 15
    },

    "craft_ferramentas_curtidor_t2": {
        "display_name": "Montar Conjunto de Curtimento de Ferro",
        "profession_req": "ferreiro",
        "required_tool_type": "ferreiro",
        "required_tool_tier": 1,
        "level_req": 21,
        "materials": {"barra_de_ferro": 14, "madeira": 8, "nucleo_forja_fraco": 1},
        "result_base_id": "ferramentas_curtidor_t2",
        "xp_gain": 26
    },

    "craft_ferramentas_curtidor_t3": {
        "display_name": "Montar Ferramentas do Curtidor Artesão",
        "profession_req": "ferreiro",
        "required_tool_type": "ferreiro",
        "required_tool_tier": 2,
        "level_req": 42,
        "materials": {"barra_de_aco": 14, "madeira": 10, "nucleo_forja_fraco": 1},
        "result_base_id": "ferramentas_curtidor_t3",
        "xp_gain": 44
    },

    "craft_ferramentas_curtidor_t4": {
        "display_name": "Montar Conjunto de Mithril para Couro Raro",
        "profession_req": "ferreiro",
        "required_tool_type": "ferreiro",
        "required_tool_tier": 3,
        "level_req": 63,
        "materials": {"mithril": 18, "madeira": 12, "nucleo_forja_fraco": 1},
        "result_base_id": "ferramentas_curtidor_t4",
        "xp_gain": 64
    },

    "craft_ferramentas_curtidor_t5": {
        "display_name": "Montar Ferramentas do Curtidor das Bestas Antigas",
        "profession_req": "ferreiro",
        "required_tool_type": "ferreiro",
        "required_tool_tier": 4,
        "level_req": 88,
        "materials": {"adamantio": 20, "madeira": 14, "nucleo_forja_fraco": 1},
        "result_base_id": "ferramentas_curtidor_t5",
        "xp_gain": 90
    },
}
