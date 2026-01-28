# modules/recipes/coleta_t5.py

RECIPES = {
    # ==========================
    # 🪓 LENHADOR TIER 5 (Adamantio/Dragão)
    # ==========================
    "machado_adamantio": {
        "display_name": "Machado de Adamantio",
        "description": "Forjado com fogo de dragão. Corta a realidade.",
        "type": "tool",
        "sub_type": "lenhador",
        "tier": 5,
        "profession_req": "ferreiro",
        "level_req": 40,
        "ingredients": {
            "placa_draconica_negra": 2, # Refinado (Escama Dragão + Coração Magma)
            "raiz_do_mundo": 1,         # Madeira Lendária
            "essencia_draconica_pura": 1 # Refinado (Coração + Sangue)
        },
        "gold_cost": 20000,
        "craft_time": 600,              # 10 minutos
        "xp_reward": 2000
    },

    # ==========================
    # ⛏️ MINERADOR TIER 5 (Adamantio)
    # ==========================
    "picareta_adamantio": {
        "display_name": "Picareta de Adamantio",
        "description": "Pode quebrar as paredes do abismo.",
        "type": "tool",
        "sub_type": "minerador",
        "tier": 5,
        "profession_req": "ferreiro",
        "level_req": 40,
        "ingredients": {
            "placa_draconica_negra": 3,
            "raiz_do_mundo": 1,
            "nucleo_de_energia_instavel": 3
        },
        "gold_cost": 22000,
        "craft_time": 600,
        "xp_reward": 2200
    },

    # ==========================
    # 🌾 COLHEDOR TIER 5 (Druídica)
    # ==========================
    "foice_druidica": {
        "display_name": "Foice da Natureza",
        "description": "As plantas se entregam voluntariamente a esta lâmina.",
        "type": "tool",
        "sub_type": "colhedor",
        "tier": 5,
        "profession_req": "ferreiro",   # Ou Artesão Mestre
        "level_req": 40,
        "ingredients": {
            "raiz_do_mundo": 3,         # Feita quase inteira de madeira divina
            "essencia_vital": 2,        # Drop raro T5
            "lente_petrificante": 1     # Olho de Basilisco Refinado (para o gume eterno)
        },
        "gold_cost": 18000,
        "craft_time": 550,
        "xp_reward": 1800
    },

    # ==========================
    # 🗡️ ESFOLADOR TIER 5 (Vorpal)
    # ==========================
    "faca_vorpal": {
        "display_name": "A Estripadora",
        "description": "Uma lenda sanguinária.",
        "type": "tool",
        "sub_type": "esfolador",
        "tier": 5,
        "profession_req": "ferreiro",
        "level_req": 40,
        "ingredients": {
            "placa_draconica_negra": 1,
            "dente_afiado_superior": 5, # Refinado T4
            "essencia_draconica_pura": 2
        },
        "gold_cost": 19000,
        "craft_time": 500,
        "xp_reward": 1900
    },

    # ==========================
    # 🧪 ALQUIMISTA TIER 5 (Vazio)
    # ==========================
    "cubo_vazio": {
        "display_name": "Cubo de Contenção",
        "description": "Uma caixa que guarda o nada e o tudo.",
        "type": "tool",
        "sub_type": "alquimista",
        "tier": 5,
        "profession_req": "joalheiro",
        "level_req": 40,
        "ingredients": {
            "lente_petrificante": 4,    # Paredes de cristal indestrutível
            "essencia_sombra": 5,
            "luz_estelar": 1            # O núcleo
        },
        "gold_cost": 25000,
        "craft_time": 700,
        "xp_reward": 2500
    }
}