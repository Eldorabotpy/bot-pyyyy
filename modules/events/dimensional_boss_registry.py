# modules/events/dimensional_boss_registry.py

BOSS_DIMENSIONAL_CONFIG = {
    "template_id": "arauto_do_vazio",
    "nome_evento": "Fenda Dimensional",
    "nome_boss": "Arauto do Vazio",
    "max_jogadores": 20,

    "mapas_permitidos": [
        "capital_eldora",
        "pradaria_inicial",
        "floresta_sombria",
        "pedreira_granito",
    ],

    "tempo_entrada_segundos": 600,
    "assets": {
        "portal": "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/mob/fenda_dimencional/portal%20da%20fenda.png",
        "boss": "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/mob/fenda_dimencional/Arauto%20do%20Vazio.png",
        "lacaio_guardiao": "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/mob/fenda_dimencional/Guardi%C3%A3o%20da%20Fenda.png",
        "lacaio_sacerdote": "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/mob/fenda_dimencional/Sacerdote%20da%20Fenda.png",
        # Imagens estáticas da tela de combate
        "boss_combate": "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/mob/combate/fenda/Arauto%20do%20Vazio%20st.png",
        "lacaio_guardiao_combate": "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/mob/combate/fenda/Guardi%C3%A3o%20da%20Fenda%20st.png",
        "lacaio_sacerdote_combate": "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/mob/combate/fenda/Sacerdote%20da%20Fenda%20st.png",
    },

    "spritesheet": {
        "portal": {
            "frame_width": 128,
            "frame_height": 128,
            "cols": 4,
            "rows": 2
        },
        "mobs": {
            "frame_width": 128,
            "frame_height": 128,
            "cols": 3,
            "rows": 4
        }
    },

    "posicoes_mapa": {
        "capital_eldora": {
            "portal": {"tile_x": 29, "tile_y": 36},
            "boss": {"tile_x": 29, "tile_y": 38},
            "lacaio_guardiao": {"tile_x": 27, "tile_y": 37},
            "lacaio_sacerdote": {"tile_x": 31, "tile_y": 37}
        },
        "pradaria_inicial": {
            "portal": {"tile_x": 27, "tile_y": 7},
            "boss": {"tile_x": 27, "tile_y": 9},
            "lacaio_guardiao": {"tile_x": 25, "tile_y": 8},
            "lacaio_sacerdote": {"tile_x": 29, "tile_y": 8}
        },
        "floresta_sombria": {
            "portal": {"tile_x": 47, "tile_y": 23},
            "boss": {"tile_x": 47, "tile_y": 25},
            "lacaio_guardiao": {"tile_x": 45, "tile_y": 24},
            "lacaio_sacerdote": {"tile_x": 49, "tile_y": 24}
        },
        "pedreira_granito": {
            "portal": {"tile_x": 6, "tile_y": 11},
            "boss": {"tile_x": 6, "tile_y": 13},
            "lacaio_guardiao": {"tile_x": 4, "tile_y": 12},
            "lacaio_sacerdote": {"tile_x": 8, "tile_y": 12}
        }
    },    
    # 🌌 Spawn automático da Fenda por abates de mobs normais no mapa.
    # TESTE:
    # ----------------------------------------------------------
    # 🌌 FENDA DIMENSIONAL POR ABATES
    # ----------------------------------------------------------
    # Contador GLOBAL entre os mapas permitidos.
    # A cada 500 mobs derrotados, a Fenda Dimensional surge
    # no mapa onde ocorreu o 500º abate.
    # ----------------------------------------------------------
    "spawn_por_abates": {
        "ativo": True,

        "default": {
            "limite_abates": 500,
            "chance_percent": 100
        },

        "capital_eldora": {
            "limite_abates": 500,
            "chance_percent": 100
        },

        "pradaria_inicial": {
            "limite_abates": 500,
            "chance_percent": 100
        },

        "floresta_sombria": {
            "limite_abates": 500,
            "chance_percent": 100
        },

        "pedreira_granito": {
            "limite_abates": 500,
            "chance_percent": 100
        }
    },

    "boss": {
        "id": "boss_arauto_vazio",
        "tipo": "boss",
        "nome": "Arauto do Vazio",
        "hp": 120000,
        "hp_max": 120000,
        "attack": 800,
        "magic_attack": 700,
        "defense": 300,
        "initiative": 60,
        "vivo": True,
        "protegido": True,
        "skills": [
            "rasgo_dimensional",
            "explosao_do_vazio",
            "marca_do_vazio"
        ]
    },

    "lacaios": [
        {
            "id": "lacaio_guardiao_fenda",
            "tipo": "lacaio",
            "nome": "Guardião da Fenda",
            "hp": 35000,
            "hp_max": 35000,
            "attack": 450,
            "magic_attack": 100,
            "defense": 260,
            "initiative": 45,
            "vivo": True,
            "skills": [
                "golpe_dimensional",
                "muralha_da_fenda"
            ]
        },
        {
            "id": "lacaio_sacerdote_fenda",
            "tipo": "lacaio",
            "nome": "Sacerdote da Fenda",
            "hp": 26000,
            "hp_max": 26000,
            "attack": 150,
            "magic_attack": 520,
            "defense": 140,
            "initiative": 55,
            "vivo": True,
            "skills": [
                "cura_sombria",
                "rajada_arcana"
            ]
        }
    ]
}