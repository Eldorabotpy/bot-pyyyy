# modules/recipes/coleta_t2.py

RECIPES = {
    # ==========================
    # 🪓 FERRAMENTAS DE LENHADOR (Tier 2 - Ferro)
    # ==========================
    "machado_ferro": {
        "display_name": "Machado de Ferro",
        "description": "Lâmina pesada. Requer força para manusear.",
        "type": "ferramenta",
        "sub_type": "lenhador",
        "tier": 2,
        "profession_req": "ferreiro",
        "level_req": 5,
        "ingredients": {
            "barra_de_ferro": 4,        # Exige muito minério processado
            "tabua_de_carvalho": 2,     # Madeira refinada (não bruta)
            "couro_curtido": 2          # Para a empunhadura
        },
        "gold_cost": 450,
        "craft_time": 60,               # 1 minuto
        "xp_reward": 50
    },

    # ==========================
    # ⛏️ FERRAMENTAS DE MINERADOR (Tier 2 - Ferro)
    # ==========================
    "picareta_ferro": {
        "display_name": "Picareta de Ferro",
        "description": "Ponta reforçada para quebrar rochas duras.",
        "type": "ferramenta",
        "sub_type": "minerador",
        "tier": 2,
        "profession_req": "ferreiro",
        "level_req": 5,
        "ingredients": {
            "barra_de_ferro": 5,
            "tabua_de_carvalho": 2,
            "corda_de_linho": 1         # Para fixar a cabeça ao cabo
        },
        "gold_cost": 500,
        "craft_time": 60,
        "xp_reward": 55
    },

    # ==========================
    # 🌾 FERRAMENTAS DE COLHEDOR (Tier 2 - Ferro)
    # ==========================
    "foice_ferro": {
        "display_name": "Foice de Ferro",
        "description": "Lâmina curva e afiada para corte preciso.",
        "type": "ferramenta",
        "sub_type": "colhedor",
        "tier": 2,
        "profession_req": "ferreiro",
        "level_req": 5,
        "ingredients": {
            "barra_de_ferro": 3,
            "tabua_de_carvalho": 3,     # Cabo longo gasta mais madeira
            "corda_de_linho": 2
        },
        "gold_cost": 400,
        "craft_time": 50,
        "xp_reward": 45
    },

    # ==========================
    # 🗡️ FERRAMENTAS DE ESFOLADOR (Tier 2 - Ferro)
    # ==========================
    "faca_ferro": {
        "display_name": "Faca de Caça",
        "description": "Curta e extremamente afiada.",
        "type": "ferramenta",
        "sub_type": "esfolador",
        "tier": 2,
        "profession_req": "ferreiro",
        "level_req": 5,
        "ingredients": {
            "barra_de_ferro": 2,
            "couro_curtido": 3,         # Bainha e cabo de couro
            "dente_afiado": 2           # Uso criativo de drop de monstro
        },
        "gold_cost": 350,
        "craft_time": 45,
        "xp_reward": 40
    },

    # ==========================
    # 🧪 FERRAMENTAS DE ALQUIMISTA (Tier 2 - Cerâmica)
    # ==========================
    "frasco_ceramica": {
        "display_name": "Recipiente de Cerâmica",
        "description": "Resistente a corrosão básica.",
        "type": "ferramenta",
        "sub_type": "alquimista",
        "tier": 2,
        "profession_req": "artesao", # Ou oleiro, se tiver
        "level_req": 5,
        "ingredients": {
            "placa_de_pedra_polida": 2, # Requer processar pedra
            "oleo_mineral": 1,          # Para impermeabilizar
            "carvao": 2                 # Para queimar a cerâmica
        },
        "gold_cost": 300,
        "craft_time": 40,
        "xp_reward": 35
    }
}