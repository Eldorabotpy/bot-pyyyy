# modules/recipes/coleta_t3.py

RECIPES = {
    # ==========================
    # 🪓 LENHADOR TIER 3 (Aço)
    # ==========================
    "machado_aco": {
        "display_name": "Machado de Aço",
        "description": "Aço temperado, capaz de cortar madeiras nobres.",
        "type": "tool",
        "sub_type": "lenhador",
        "tier": 3,
        "profession_req": "ferreiro",
        "level_req": 15,
        "ingredients": {
            "barra_de_aco": 4,          # Requer refino de Ferro + Carvão
            "tabua_de_mogno": 2,        # Requer Madeira Mogno + Óleo
            "couro_reforcado": 2,        # Requer Couro Curtido + Cera/Lobo Alfa
            "nucleo_forja_fraco": 1
        },
        "gold_cost": 1500,
        "craft_time": 120,              # 2 minutos
        "xp_reward": 150
    },

    # ==========================
    # ⛏️ MINERADOR TIER 3 (Aço)
    # ==========================
    "picareta_aco": {
        "display_name": "Picareta de Aço",
        "description": "Ponta endurecida para extrair metais preciosos.",
        "type": "tool",
        "sub_type": "minerador",
        "tier": 3,
        "profession_req": "ferreiro",
        "level_req": 15,
        "ingredients": {
            "barra_de_aco": 5,
            "tabua_de_mogno": 2,
            "couro_reforcado": 1,
            "nucleo_forja_fraco": 1
        },
        "gold_cost": 1600,
        "craft_time": 120,
        "xp_reward": 160
    },

    # ==========================
    # 🌾 COLHEDOR TIER 3 (Aço Fino)
    # ==========================
    "foice_aco": {
        "display_name": "Foice de Aço Fino",
        "description": "Corte cirúrgico para não danificar flores raras.",
        "type": "tool",
        "sub_type": "colhedor",
        "tier": 3,
        "profession_req": "ferreiro",
        "level_req": 15,
        "ingredients": {
            "barra_de_aco": 3,
            "tabua_de_mogno": 3,
            "fio_de_prata": 2,           # Item de joalheria para reforço
            "nucleo_forja_fraco": 1
        },
        "gold_cost": 1400,
        "craft_time": 100,
        "xp_reward": 140
    },

    # ==========================
    # 🗡️ ESFOLADOR TIER 3 (Aço Cirúrgico)
    # ==========================
    "faca_aco": {
        "display_name": "Faca de Esfolar",
        "description": "Lâmina perfeita para separar couro de escamas.",
        "type": "tool",
        "sub_type": "esfolador",
        "tier": 3,
        "profession_req": "ferreiro",
        "level_req": 15,
        "ingredients": {
            "barra_de_aco": 2,
            "couro_escamoso": 2,        # Drop processado de répteis
            "gema_polida": 1,            # Detalhe no cabo
            "nucleo_forja_fraco": 1
        },
        "gold_cost": 1300,
        "craft_time": 90,
        "xp_reward": 130
    },

    # ==========================
    # 🧪 ALQUIMISTA TIER 3 (Cristal)
    # ==========================
    "extrator_cristal": {
        "display_name": "Extrator de Cristal",
        "description": "Vidro reforçado com pó de gema para conter gases.",
        "type": "tool",
        "sub_type": "alquimista",
        "tier": 3,
        "profession_req": "joalheiro",
        "level_req": 15,
        "ingredients": {
            "gema_lapidada_comum": 2,
            "barra_de_prata": 2,        # Suporte de prata (antibacteriano)
            "frasco_ceramica": 1,        # Base
            "nucleo_forja_fraco": 1
        },
        "gold_cost": 1200,
        "craft_time": 100,
        "xp_reward": 120
    }
}