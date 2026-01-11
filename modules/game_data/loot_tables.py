# modules/game_data/loot_tables.py

GATHERING_LOOT_TABLE = {
    # ==========================================
    # 🪓 LENHADOR (Madeira)
    # ==========================================
    "lenhador": {
        # Tier 1: Machado de Pedra
        1: {
            "drops": [
                {"item_key": "madeira", "chance": 90, "min_qty": 1, "max_qty": 3},
            ],
            "xp_reward": 10
        },
        # Tier 2: Machado de Ferro
        2: {
            "drops": [
                {"item_key": "madeira_de_carvalho", "chance": 60, "min_qty": 1, "max_qty": 2},
                {"item_key": "casca_rigida", "chance": 20, "min_qty": 1, "max_qty": 1},
                {"item_key": "madeira", "chance": 20, "min_qty": 2, "max_qty": 4}
            ],
            "xp_reward": 25
        },
        # Tier 3: Machado de Aço
        3: {
            "drops": [
                {"item_key": "madeira_mogno", "chance": 50, "min_qty": 1, "max_qty": 2},
                {"item_key": "ambar_seiva", "chance": 20, "min_qty": 1, "max_qty": 1},
                {"item_key": "madeira_rara", "chance": 30, "min_qty": 1, "max_qty": 1}
            ],
            "xp_reward": 60
        },
        # Tier 4: Machado de Mithril
        4: {
            "drops": [
                {"item_key": "madeira_elfica", "chance": 40, "min_qty": 1, "max_qty": 1},
                {"item_key": "semente_encantada", "chance": 10, "min_qty": 1, "max_qty": 1}
            ],
            "xp_reward": 150
        },
        # Tier 5: Machado de Adamantio
        5: {
            "drops": [
                {"item_key": "raiz_do_mundo", "chance": 15, "min_qty": 1, "max_qty": 1}
            ],
            "xp_reward": 500
        }
    },

    # ==========================================
    # ⛏️ MINERADOR (Minérios e Pedras)
    # ==========================================
    "minerador": {
        # Tier 1
        1: {
            "drops": [
                {"item_key": "pedra", "chance": 50, "min_qty": 1, "max_qty": 3},
                {"item_key": "minerio_de_cobre", "chance": 30, "min_qty": 1, "max_qty": 2},
                {"item_key": "minerio_de_estanho", "chance": 20, "min_qty": 1, "max_qty": 2}
            ],
            "xp_reward": 12
        },
        # Tier 2
        2: {
            "drops": [
                {"item_key": "minerio_de_ferro", "chance": 50, "min_qty": 1, "max_qty": 3},
                {"item_key": "carvao", "chance": 40, "min_qty": 2, "max_qty": 5},
                {"item_key": "gema_bruta", "chance": 10, "min_qty": 1, "max_qty": 1}
            ],
            "xp_reward": 30
        },
        # Tier 3
        3: {
            "drops": [
                {"item_key": "minerio_de_prata", "chance": 40, "min_qty": 1, "max_qty": 2},
                {"item_key": "minerio_de_ouro", "chance": 20, "min_qty": 1, "max_qty": 1},
                {"item_key": "cristal_bruto", "chance": 20, "min_qty": 1, "max_qty": 2}
            ],
            "xp_reward": 70
        },
        # Tier 4
        4: {
            "drops": [
                {"item_key": "cristal_mana", "chance": 40, "min_qty": 1, "max_qty": 2},
                {"item_key": "nucleo_de_energia_instavel", "chance": 5, "min_qty": 1, "max_qty": 1}
            ],
            "xp_reward": 180
        },
        # Tier 5
        5: {
            "drops": [
                {"item_key": "obsidiana_ancestral", "chance": 20, "min_qty": 1, "max_qty": 1}
            ],
            "xp_reward": 600
        }
    },

    # ==========================================
    # 🌿 COLHEDOR (Plantas)
    # ==========================================
    "colhedor": {
        # Tier 1
        1: {
            "drops": [
                {"item_key": "linho", "chance": 80, "min_qty": 1, "max_qty": 3},
                {"item_key": "fibra_vegetal", "chance": 20, "min_qty": 1, "max_qty": 2} # Assumindo que existe fibra ou usa-se linho
            ],
            "xp_reward": 8
        },
        # Tier 2
        2: {
            "drops": [
                {"item_key": "erva_cura", "chance": 50, "min_qty": 1, "max_qty": 3},
                {"item_key": "cogumelo_azul", "chance": 30, "min_qty": 1, "max_qty": 2},
                {"item_key": "raiz_sangrenta", "chance": 20, "min_qty": 1, "max_qty": 1}
            ],
            "xp_reward": 20
        },
        # Tier 3
        3: {
            "drops": [
                {"item_key": "flor_da_lua", "chance": 60, "min_qty": 1, "max_qty": 2},
                {"item_key": "semente_encantada", "chance": 10, "min_qty": 1, "max_qty": 1}
            ],
            "xp_reward": 50
        },
        # Tier 4
        4: {
            "drops": [
                {"item_key": "raiz_solar", "chance": 40, "min_qty": 1, "max_qty": 1}
            ],
            "xp_reward": 120
        },
        # Tier 5
        5: {
            "drops": [
                {"item_key": "fruta_imortalidade", "chance": 5, "min_qty": 1, "max_qty": 1}
            ],
            "xp_reward": 1000
        }
    },

    # ==========================================
    # 🗡️ ESFOLADOR (Monstros)
    # ==========================================
    "esfolador": {
        # Tier 1
        1: {
            "drops": [
                {"item_key": "pele_rasgada", "chance": 40, "min_qty": 1, "max_qty": 2}, # Se adicionado
                {"item_key": "pena", "chance": 30, "min_qty": 2, "max_qty": 4},
                {"item_key": "pano_simples", "chance": 30, "min_qty": 1, "max_qty": 2}
            ],
            "xp_reward": 15
        },
        # Tier 2
        2: {
            "drops": [
                {"item_key": "couro_de_lobo", "chance": 50, "min_qty": 1, "max_qty": 1},
                {"item_key": "presa_de_javali", "chance": 30, "min_qty": 1, "max_qty": 2},
                {"item_key": "sangue", "chance": 20, "min_qty": 1, "max_qty": 3}
            ],
            "xp_reward": 35
        },
        # Tier 3
        3: {
            "drops": [
                {"item_key": "escama_serpente", "chance": 40, "min_qty": 1, "max_qty": 2},
                {"item_key": "couro_de_lobo_alfa", "chance": 30, "min_qty": 1, "max_qty": 1},
                {"item_key": "asa_de_morcego", "chance": 30, "min_qty": 1, "max_qty": 2}
            ],
            "xp_reward": 80
        },
        # Tier 4
        4: {
            "drops": [
                {"item_key": "couro_dragao", "chance": 30, "min_qty": 1, "max_qty": 1},
                {"item_key": "olho_de_basilisco", "chance": 10, "min_qty": 1, "max_qty": 1}
            ],
            "xp_reward": 200
        },
        # Tier 5
        5: {
            "drops": [
                {"item_key": "essencia_vital", "chance": 15, "min_qty": 1, "max_qty": 1}
            ],
            "xp_reward": 800
        }
    },

    # ==========================================
    # 🧪 ALQUIMISTA (Essências)
    # ==========================================
    "alquimista": {
        # Tier 1
        1: {
            "drops": [
                {"item_key": "agua_pura", "chance": 80, "min_qty": 1, "max_qty": 3},
                {"item_key": "poeira_magica", "chance": 20, "min_qty": 1, "max_qty": 1}
            ],
            "xp_reward": 10
        },
        # Tier 2
        2: {
            "drops": [
                {"item_key": "esporo_de_cogumelo", "chance": 50, "min_qty": 1, "max_qty": 3},
                {"item_key": "seiva_de_ent", "chance": 50, "min_qty": 1, "max_qty": 2}
            ],
            "xp_reward": 25
        },
        # Tier 3
        3: {
            "drops": [
                {"item_key": "gas_venenoso", "chance": 40, "min_qty": 1, "max_qty": 1},
                {"item_key": "essencia_de_fogo", "chance": 20, "min_qty": 1, "max_qty": 1},
                {"item_key": "nucleo_de_golem", "chance": 10, "min_qty": 1, "max_qty": 1}
            ],
            "xp_reward": 60
        },
        # Tier 4
        4: {
            "drops": [
                {"item_key": "ectoplasma", "chance": 50, "min_qty": 1, "max_qty": 2},
                {"item_key": "coracao_de_magma", "chance": 10, "min_qty": 1, "max_qty": 1}
            ],
            "xp_reward": 150
        },
        # Tier 5
        5: {
            "drops": [
                {"item_key": "luz_estelar", "chance": 15, "min_qty": 1, "max_qty": 1}
            ],
            "xp_reward": 600
        }
    }
}