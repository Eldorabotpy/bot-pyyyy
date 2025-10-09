# modules/game_data/monsters.py

MONSTERS_DATA = {
    "floresta_sombria": [
        {
            "id": "goblin_batedor",
            "name": "Goblin Batedor",
            "hp": 40, "attack": 5, "defense": 1, "initiative": 8, "luck": 5,
            "xp_reward": 1, "ambush_chance": 0.25,
            "file_id_name": "goblin_batedor_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "pano_simples", "drop_chance": 10}
            ],
        },
        {
            "id": "lobo_magro",
            "name": "Lobo Magro",
            "hp": 25, "attack": 4, "defense": 2, "initiative": 7, "luck": 3,
            "xp_reward": 1, "ambush_chance": 0.0,
            "file_id_name": "lobo_magro_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "couro_de_lobo", "drop_chance": 30}
            ],
        },
        {
            "id": "cogumelo_gigante",
            "name": "Cogumelo Gigante",
            "hp": 30, "attack": 4, "defense": 4, "initiative": 2, "luck": 1,
            "xp_reward": 2, "ambush_chance": 0.0,
            "file_id_name": "cogumelo_gigante_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "esporo_de_cogumelo", "drop_chance": 10}
            ],
        },
        {
            "id": "javali_com_presas",
            "name": "Javali com Presas",
            "hp": 35, "attack": 6, "defense": 3, "initiative": 5, "luck": 4,
            "xp_reward": 1, "ambush_chance": 0.0,
            "file_id_name": "javali_com_presas_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "presa_de_javali", "drop_chance": 10}
            ],
        },
        {
            "id": "ent_jovem",
            "name": "Ent Jovem",
            "hp": 40, "attack": 5, "defense": 5, "initiative": 3, "luck": 2,
            "xp_reward": 3, "ambush_chance": 0.0,
            "file_id_name": "ent_jovem_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "madeira_rara", "drop_chance": 10},
                {"item_id": "seiva_de_ent", "drop_chance": 10},
                {"item_id": "madeira", "drop_chance": 10}
            ],
        },
        {
            "id": "espectro_do_bosque",
            "name": "Espectro do Bosque",
            "hp": 45, "attack": 8, "defense": 2, "initiative": 6, "luck": 8,
            "xp_reward": 3, "ambush_chance": 0.0,
            "file_id_name": "espectro_bosque_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "ectoplasma", "drop_chance": 10},
                
            ],
        },
        {
            "id": "xama_goblin",
            "name": "Xamã Goblin",
            "hp": 55, "attack": 10, "defense": 3, "initiative": 7, "luck": 6,
            "xp_reward": 5, "ambush_chance": 0.0,
            "file_id_name": "xama_goblin_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "fio_de_prata", "drop_chance": 35}
            ],
        },
        {
            "id": "lobo_alfa",
            "name": "Lobo Alfa",
            "hp": 70, "attack": 15, "defense": 7, "initiative": 10, "luck": 15,
            "xp_reward": 6, "ambush_chance": 0.0,
            "file_id_name": "lobo_alfa_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "couro_de_lobo_alfa", "drop_chance": 10}
            ],
        },
    ],

    "pedreira_granito": [
        {
            "id": "kobold_escavador",
            "name": "Kobold Escavador",
            "hp": 125, "attack": 18, "defense": 24, "initiative": 15, "luck": 15,
            "xp_reward": 6, "ambush_chance": 0.20,
            "file_id_name": "kobold_escavador_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "minerio_de_ferro", "drop_chance": 10},
                {"item_id": "gema_bruta", "drop_chance": 3}
            ],
            
        },
        {
            "id": "tatu_de_rocha",
            "name": "Tatu de Rocha",
            "hp": 240, "attack": 7, "defense": 30, "initiative": 16, "luck": 5,
            "xp_reward": 5, "ambush_chance": 0.0,
            "file_id_name": "tatu_rocha_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "carapaca_de_pedra", "drop_chance": 10},
                {"item_id": "pedra", "drop_chance": 10}
            ],
        },
        {
            "id": "golem_de_pedra_pequeno",
            "name": "Golem de Pedra Pequeno",
            "hp": 360, "attack": 20, "defense": 22, "initiative": 10, "luck": 2,
            "xp_reward": 6, "ambush_chance": 0.0,
            "file_id_name": "golem_pedra_pequeno_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "pedra", "drop_chance": 10},
                {"item_id": "nucleo_de_golem", "drop_chance": 0.5}
            ],
        },
        {
            "id": "salamandra_de_pedra",
            "name": "Salamandra de Pedra",
            "hp": 345, "attack": 24, "defense": 38, "initiative": 19, "luck": 8,
            "xp_reward": 5, "ambush_chance": 0.0,
            "file_id_name": "salamandra_pedra_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "escama_de_salamandra", "drop_chance": 10},
                {"item_id": "coracao_de_magma", "drop_chance": 10}
            ],
        },
        {
            "id": "gargula_de_vigia",
            "name": "Gárgula de Vigia",
            "hp": 435, "attack": 36, "defense": 36, "initiative": 20, "luck": 10,
            "xp_reward": 8, "ambush_chance": 0.30,
            "file_id_name": "gargula_vigia_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "fragmento_gargula", "drop_chance": 10},
                {"item_id": "poeira_magica", "drop_chance": 10}
            ],
        },
        {
            "id": "basilisco_jovem",
            "name": "Basilisco Jovem",
            "hp": 280, "attack": 28, "defense": 20, "initiative": 38, "luck": 7,
            "xp_reward": 5, "ambush_chance": 0.0,
            "file_id_name": "basilisco_jovem_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "olho_de_basilisco", "drop_chance": 10},
              
            ],
        },
    ],

    "campos_linho": [
        {
            "id": "espantalho_vivo",
            "name": "Espantalho Vivo",
            "hp": 252, "attack": 19, "defense": 14, "initiative": 16, "luck": 5,
            "xp_reward": 2, "ambush_chance": 0.0,
            "file_id_name": "espantalho_vivo_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "palha_amaldicoada", "drop_chance": 10},
                {"item_id": "pano_simples", "drop_chance": 15}
            ],
        },
        {
            "id": "passaro_roc_gigante",
            "name": "Pássaro Roc Gigante",
            "hp": 178, "attack": 39, "defense": 16, "initiative": 18, "luck": 8,
            "xp_reward": 3, "ambush_chance": 0.0,
            "file_id_name": "passaro_roc_gigante_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "pano_simples", "drop_chance": 5},
                
            ],
        },
        {
            "id": "verme_de_seda",
            "name": "Verme de Seda",
            "hp": 160, "attack": 25, "defense": 20, "initiative": 14, "luck": 9,
            "xp_reward": 4, "ambush_chance": 0.0,
            "file_id_name": "verme_de_seda_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "linho", "drop_chance": 5},
                {"item_id": "pano_simples", "drop_chance": 5}
            ],
        },
        {
            "id": "lobisomem_campones",
            "name": "Lobisomem Camponês",
            "hp": 384, "attack": 26, "defense": 16, "initiative": 18, "luck": 6,
            "xp_reward": 4, "ambush_chance": 0.0,
            "file_id_name": "lobisomem_campones_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "couro_de_lobo", "drop_chance": 7},
                
            ],
        },
        {
            "id": "gnomo_de_jardim_travesso",
            "name": "Gnomo de Jardim Travesso",
            "hp": 348, "attack": 41, "defense": 13, "initiative": 12, "luck": 12,
            "xp_reward": 6, "ambush_chance": 0.0,
            "file_id_name": "gnomo_de_jardim_travesso_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "gema_bruta", "drop_chance": 5},
              
            ],
        },
        {
            "id": "banshee_dos_campos",
            "name": "Banshee dos Campos",
            "hp": 372, "attack": 47, "defense": 14, "initiative": 19, "luck": 10,
            "xp_reward": 5, "ambush_chance": 0.0,
            "file_id_name": "banshee_dos_campos_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "ectoplasma", "drop_chance": 8},
                
            ],
        },
    ],

    "pico_grifo": [
        {
            "id": "harpia_saqueadora",
            "name": "Harpia Saqueadora",
            "hp": 142, "attack": 34, "defense": 16, "initiative": 44, "luck": 30,
            "xp_reward": 4, "ambush_chance": 0.0,
            "gold_drop": 1,
            "file_id_name": "harpia_saqueadora_media",
            "loot_table": [
                {"item_id": "pena", "drop_chance": 5},
                {"item_id": "gema_bruta", "drop_chance": 5}
            ],
        },
        {
            "id": "grifo_jovem",
            "name": "Grifo Jovem",
            "hp": 165, "attack": 28, "defense": 19, "initiative": 23, "luck": 8,
            "xp_reward": 5, "ambush_chance": 0.0,
            "gold_drop": 1,
            "file_id_name": "grifo_jovem_media",
            "loot_table": [
                {"item_id": "pena", "drop_chance": 9},
            
            ],
        },
        {
            "id": "elemental_do_ar_menor",
            "name": "Elemental do Ar Menor",
            "hp": 255, "attack": 26, "defense": 18, "initiative": 36, "luck": 12,
            "xp_reward": 8, "ambush_chance": 0.0,
            "file_id_name": "elemental_ar_menor_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "gema_bruta", "drop_chance": 2},
                
            ],
        },
        {
            "id": "corvo_carniceiro_gigante",
            "name": "Corvo Carniceiro Gigante",
            "hp": 348, "attack": 35, "defense": 17, "initiative": 37, "luck": 10,
            "xp_reward": 5, "ambush_chance": 0.0,
            "gold_drop": 1,
            "file_id_name": "corvo_gigante_media",
            "loot_table": [
                {"item_id": "pena", "drop_chance": 8}
            ],
        },
        {
            "id": "wyvern_filhote",
            "name": "Wyvern Filhote",
            "hp": 288, "attack": 31, "defense": 21, "initiative": 32, "luck": 7,
            "xp_reward": 4, "ambush_chance": 0.0,
            "gold_drop": 1,
            "file_id_name": "wyvern_filhote_media",
            "loot_table": [
              
                {"item_id": "gema_bruta", "drop_chance": 10}
            ],
        },
        {
            "id": "abelha_gigante_rainha",
            "name": "Abelha Gigante Rainha",
            "hp": 272, "attack": 39, "defense": 20, "initiative": 50, "luck": 69,
            "xp_reward": 13, "ambush_chance": 0.0,
            "gold_drop": 1,
            "file_id_name": "abelha_gigante_rainha_media",
            "loot_table": [
                {"item_id": "gema_bruta", "drop_chance": 8},
            ],
        },
    ],

    "mina_ferro": [
        {
            "id": "morcego_das_minas",
            "name": "Morcego das Minas",
            "hp": 258, "attack": 27, "defense": 28, "initiative": 38, "luck": 19,
            "xp_reward": 4, "gold_drop": 1, "ambush_chance": 0.20,
            "file_id_name": "morcego_minas_media",
            "loot_table": [
                {"item_id": "asa_de_morcego", "drop_chance": 7},
                {"item_id": "gema_bruta", "drop_chance": 6}
            ],
        },
        {
            "id": "kobold_capataz",
            "name": "Kobold Capataz",
            "hp": 376, "attack": 52, "defense": 22, "initiative": 32, "luck": 32,
            "xp_reward": 4, "gold_drop": 1, "ambush_chance": 0.18,
            "file_id_name": "kobold_capataz_media",
            "loot_table": [
                {"item_id": "minerio_de_ferro", "drop_chance": 40},
                {"item_id": "gema_bruta", "drop_chance": 8}
            ],
        },
        {
            "id": "slime_de_ferrugem",
            "name": "Slime de Ferrugem",
            "hp": 390, "attack": 26, "defense": 16, "initiative": 36, "luck": 26,
            "xp_reward": 8, "gold_drop": 1, "ambush_chance": 0.0,
            "file_id_name": "slime_ferrugem_media",
            "loot_table": [
                {"item_id": "pedra", "drop_chance": 60},
                {"item_id": "barra_bronze", "drop_chance": 5}
            ],
        },
        {
            "id": "troll_da_caverna",
            "name": "Troll da Caverna",
            "hp": 440, "attack": 48, "defense": 42, "initiative": 27, "luck": 25,
            "xp_reward": 17, "gold_drop": 1, "ambush_chance": 0.0,
            "file_id_name": "troll_caverna_media",
            "loot_table": [
                {"item_id": "pele_de_troll", "drop_chance": 7},
                {"item_id": "sangue_regenerativo", "drop_chance": 18}
            ],
        },
        {
            "id": "caranguejo_de_rocha",
            "name": "Caranguejo de Rocha",
            "hp": 310, "attack": 30, "defense": 40, "initiative": 15, "luck": 26,
            "xp_reward": 12, "gold_drop": 1, "ambush_chance": 0.0,
            "file_id_name": "caranguejo_rocha_media",
            "loot_table": [
                {"item_id": "carapaca_de_pedra", "drop_chance": 65},
                {"item_id": "pedra", "drop_chance": 100}
            ],
        },
        {
            "id": "fantasma_de_mineiro",
            "name": "Fantasma de Mineiro",
            "hp": 464, "attack": 33, "defense": 29, "initiative": 36, "luck": 14,
            "xp_reward": 15, "gold_drop": 1, "ambush_chance": 0.25,
            "file_id_name": "fantasma_mineiro_media",
            "loot_table": [
                {"item_id": "ectoplasma", "drop_chance": 5},
            ],
        },
    ],

    "forja_abandonada": [
        {
            "id": "golem_de_ferro_incompleto",
            "name": "Golem de Ferro Incompleto",
            "hp": 495, "attack": 32, "defense": 44, "initiative": 28, "luck": 16,
            "xp_reward": 15, "gold_drop": 1, "ambush_chance": 0.0,
            "loot_table": [
                {"item_id": "barra_de_ferro", "drop_chance": 5},
            ],
            "file_id_name": "golem_ferro_incompleto_media",
        },
        {
            "id": "elemental_de_fogo",
            "name": "Elemental de Fogo",
            "hp": 480, "attack": 35, "defense": 30, "initiative": 26, "luck": 19,
            "xp_reward": 148, "gold_drop": 1, "ambush_chance": 0.0,
            "loot_table": [
                {"item_id": "essencia_de_fogo", "drop_chance": 0.5},
            ],
            "file_id_name": "elemental_fogo_media",
        },
        {
            "id": "cao_de_caca_de_metal",
            "name": "Cão de Caça de Metal",
            "hp": 288, "attack": 23, "defense": 22, "initiative": 44, "luck": 8,
            "xp_reward": 16, "gold_drop": 1, "ambush_chance": 0.0,
            "loot_table": [
                {"item_id": "engrenagem_usada", "drop_chance": 5},
                {"item_id": "barra_de_ferro", "drop_chance": 15}
            ],
            "file_id_name": "cao_caca_metal_media",
        },
        {
            "id": "anao_ferreiro_fantasma",
            "name": "Anão Ferreiro Fantasma",
            "hp": 382, "attack": 31, "defense": 21, "initiative": 22, "luck": 10,
            "xp_reward": 14, "gold_drop": 1, "ambush_chance": 0.0,
            "loot_table": [
                {"item_id": "martelo_enferrujado", "drop_chance": 7},
               
            ],
            "file_id_name": "anao_ferreiro_fantasma_media",
        },
        {
            "id": "salamandra_de_fogo",
            "name": "Salamandra de Fogo",
            "hp": 378, "attack": 44, "defense": 30, "initiative": 38, "luck": 9,
            "xp_reward": 14, "gold_drop": 1, "ambush_chance": 0.0,
            "loot_table": [
                {"item_id": "escama_incandescente", "drop_chance": 8},
                {"item_id": "essencia_de_fogo", "drop_chance": 10}
            ],
            "file_id_name": "salamandra_fogo_media",
        },
        {
            "id": "automato_com_defeito",
            "name": "Autômato com Defeito",
            "hp": 490, "attack": 42, "defense": 33, "initiative": 20, "luck": 7,
            "xp_reward": 27, "gold_drop": 1, "ambush_chance": 0.0,
            "loot_table": [
                {"item_id": "engrenagem_usada", "drop_chance": 5},
                {"item_id": "barra_de_ferro", "drop_chance": 12}
            ],
            "file_id_name": "automato_defeito_media",
        },
    ],

    "catacumba_reino": [
        {
            "id": "morcego_gigante",
            "name": "Morcego Gigante",
            "hp": 30, "attack": 10, "defense": 5, "initiative": 18, "luck": 5,
            "xp_reward": 15, "ambush_chance": 0.0,
            "file_id_name": "morcego_gigante_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "asa_de_morcego", "drop_chance": 7}
            ],
        },
        {
            "id": "dragao_negro",
            "name": "Dragão Negro",
            "hp": 100, "attack": 20, "defense": 12, "initiative": 9, "luck": 5,
            "xp_reward": 16, "ambush_chance": 0.0,
            "file_id_name": "dragao_negro_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "escama_de_dragao", "drop_chance": 80},
                {"item_id": "coracao_de_dragao", "drop_chance": 15}
            ],
        },
        {
            "id": "trol_escavador",
            "name": "Trol Escavador",
            "hp": 120, "attack": 25, "defense": 8, "initiative": 5, "luck": 2,
            "xp_reward": 15, "ambush_chance": 0.0,
            "file_id_name": "trol_escavador_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "pele_de_troll", "drop_chance": 70},
                {"item_id": "sangue_regenerativo", "drop_chance": 20}
            ],
        },
        {
            "id": "golem_de_lava",
            "name": "Golem de Lava",
            "hp": 90, "attack": 22, "defense": 20, "initiative": 3, "luck": 1,
            "xp_reward": 18, "ambush_chance": 0.0,
            "file_id_name": "golem_de_lava_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "nucleo_de_magma", "drop_chance": 40},
                {"item_id": "pedra_vulcanica", "drop_chance": 60}
            ],
        },
        {
            "id": "golem_de_palha",
            "name": "Golem de Palha",
            "hp": 70, "attack": 18, "defense": 10, "initiative": 15, "luck": 10,
            "xp_reward": 27, "ambush_chance": 0.0,
            "file_id_name": "golem_de_palha_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "palha_amaldicoada", "drop_chance": 80},
                {"item_id": "semente_encantada", "drop_chance": 25}
            ],
        },
        {
            "id": "rei_lagarto",
            "name": "Rei Lagarto",
            "hp": 400, "attack": 35, "defense": 22, "initiative": 14, "luck": 10,
            "xp_reward": 20, "gold_drop": 1, "ambush_chance": 0.0,
            "is_boss": True, "consume_energy": False,
            "file_id_name": "rei_lagarto_media",
            "loot_table": [
                {"item_id": "coroa_reptiliana", "drop_chance": 1},
                {"item_id": "cetro_dos_pantanos", "drop_chance": 2}
            ],
        },
    ],
}
