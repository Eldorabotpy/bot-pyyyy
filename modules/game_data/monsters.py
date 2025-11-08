# modules/game_data/monsters.py

MONSTERS_DATA = {

    # --- MONSTROS ESPECIAIS DE EVOLUÇÃO ---
    "_evolution_trials": [
        # --- Guardiões do Guerreiro ---
        {"id": "guardian_of_the_aegis",
          "name": "Guardião do Égide", 
          "hp": 800, "attack": 40, "defense": 70, "initiative": 20, "luck": 10, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
          "media_key": "trial_guardian_aegis_media"},
        {"id": "phantom_of_the_arena",
          "name": "Fantasma da Arena", 
          "hp": 650, "attack": 75, "defense": 30, "initiative": 60, "luck": 20, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
          "media_key": "trial_phantom_arena_media"},
        {"id": "aspect_of_the_divine", 
         "name": "Aspecto do Divino", 
         "hp": 2500, "attack": 120, "defense": 200, "initiative": 50, "luck": 30, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_aspect_divine_media"},

        # --- Guardiões do Berserker ---
        {"id": "primal_spirit_of_rage", 
         "name": "Espírito Primordial da Fúria", 
         "hp": 700, "attack": 85, "defense": 20, "initiative": 40, "luck": 15, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_spirit_rage_media"},
        {"id": "guardian_of_the_mountain", 
         "name": "Guardião da Montanha", 
         "hp": 950, "attack": 60, "defense": 60, "initiative": 15, "luck": 5, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_guardian_mountain_media"},
        {"id": "avatar_of_primal_wrath", 
         "name": "Avatar da Ira Primordial", 
         "hp": 2200, "attack": 250, "defense": 80, "initiative": 80, "luck": 25, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_avatar_wrath_media"},

        # --- Guardiões do Caçador ---
        {"id": "spirit_of_the_alpha_wolf", 
         "name": "Espírito do Lobo Alfa", 
         "hp": 600, "attack": 65, "defense": 30, "initiative": 70, "luck": 30, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_spirit_wolf_media"},
        {"id": "phantom_of_the_watchtower", 
         "name": "Fantasma da Atalaia", 
         "hp": 550, "attack": 70, "defense": 25, "initiative": 65, "luck": 40, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_phantom_watchtower_media"},
        {"id": "aspect_of_the_world_tree", 
         "name": "Aspecto da Árvore-Mundo", 
         "hp": 2400, "attack": 150, "defense": 120, "initiative": 130, "luck": 50, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_aspect_tree_media"},

        # --- Guardiões do Monge ---
        {"id": "statue_of_the_serene_fist", 
         "name": "Estátua do Punho Sereno", 
         "hp": 900, "attack": 35, "defense": 80, "initiative": 30, "luck": 10, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_statue_fist_media"},
        {"id": "avatar_of_the_four_elements", 
         "name": "Avatar dos Quatro Elementos", 
         "hp": 680, "attack": 70, "defense": 45, "initiative": 55, "luck": 20, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_avatar_elements_media"},
        {"id": "echo_of_the_grandmaster", 
         "name": "Eco do Grão-Mestre", 
         "hp": 2300, "attack": 140, "defense": 180, "initiative": 150, "luck": 40, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_echo_grandmaster_media"},

        # --- Guardiões do Mago ---
        {"id": "shade_of_the_forbidden_library", 
         "name": "Sombra da Biblioteca Proibida", 
         "hp": 550, "attack": 80, "defense": 25, "initiative": 40, "luck": 25, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_shade_library_media"},
        {"id": "raging_elemental_vortex", 
         "name": "Vórtice Elemental Furioso", 
         "hp": 600, "attack": 90, "defense": 30, "initiative": 45, "luck": 15, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_raging_vortex_media"},
        {"id": "essence_of_pure_magic", 
         "name": "Essência da Magia Pura", 
         "hp": 2000, "attack": 280, "defense": 90, "initiative": 100, "luck": 35, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_essence_magic_media"},

        # --- Guardiões do Bardo ---
        {"id": "echo_of_the_first_ballad", 
         "name": "Eco da Primeira Balada", 
         "hp": 750, "attack": 40, "defense": 50, "initiative": 50, "luck": 45, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_echo_ballad_media"},
        {"id": "siren_of_the_lost_stage", 
         "name": "Sereia do Palco Perdido", 
         "hp": 650, "attack": 60, "defense": 40, "initiative": 60, "luck": 50, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_siren_stage_media"},
        {"id": "avatar_of_the_grand_orchestra", 
         "name": "Avatar da Grande Orquestra", 
         "hp": 2400, "attack": 110, "defense": 130, "initiative": 140, "luck": 80, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_avatar_orchestra_media"},

        # --- Guardiões do Assassino ---
        {"id": "doppelganger_of_the_throne", 
         "name": "Doppelgänger do Trono", 
         "hp": 600, "attack": 70, "defense": 35, "initiative": 80, "luck": 35, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_doppelganger_throne_media"},
        {"id": "spirit_of_the_swamp_adder", 
         "name": "Espírito da Víbora do Pântano", 
         "hp": 620, "attack": 65, "defense": 40, "initiative": 60, "luck": 40, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_spirit_adder_media"},
        {"id": "specter_of_the_silent_kill", 
         "name": "Espectro do Abate Silencioso", 
         "hp": 2100, "attack": 180, "defense": 100, "initiative": 200, "luck": 60, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_specter_kill_media"},

        # --- Guardiões do Samurai ---
        {"id": "phantom_of_the_dojo", 
         "name": "Fantasma do Dojo", 
         "hp": 720, "attack": 75, "defense": 45, "initiative": 50, "luck": 20, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_phantom_dojo_media"},
        {"id": "spirit_of_the_wandering_warrior", 
         "name": "Espírito do Guerreiro Errante", 
         "hp": 800, "attack": 65, "defense": 65, "initiative": 40, "luck": 25, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_spirit_warrior_media"},
        {"id": "avatar_of_the_first_emperor", 
         "name": "Avatar do Primeiro Imperador", 
         "hp": 2600, "attack": 160, "defense": 160, "initiative": 110, "luck": 40, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_avatar_emperor_media"},
    ],
    "defesa_reino": [
        {
            "id": "ond1_pequeno_slime",
            "name": "Pequeno Slime",
            "hp": 10, "attack": 2, "defense": 1, "initiative": 5, "luck": 1,
            "media_key": "ond1_slime_pequeno_media"
        },
        {
            "id": "ond1_slime_verde",
            "name": "Slime Verde",
            "hp": 20, "attack": 3, "defense": 2, "initiative": 3, "luck": 2,
            "media_key": "ond1_slime_verde_media"
        },
        {
            "id": "ond1_slime_azul",
            "name": "Slime Azul", # Mais defensivo
            "hp": 30, "attack": 2, "defense": 4, "initiative": 2, "luck": 2,
            "media_key": "ond1_slime_azul_media"
        },
        {
            "id": "ond1_slime_magma",
            "name": "Slime de Magma", # Mais agressivo
            "hp": 40, "attack": 5, "defense": 1, "initiative": 4, "luck": 2,
            "media_key": "ond1_slime_magma_media"
        },
        {
            "id": "ond1_slime_terra",
            "name": "Slime Terra",
            "hp": 50, "attack": 4, "defense": 3, "initiative": 1, "luck": 3,
            "media_key": "ond1_slime_terra_media"
        },
        {
            "id": "ond1_slime_venenoso",
            "name": "Slime Venenoso", 
            "hp": 60, "attack": 3, "defense": 2, "initiative": 12, "luck": 5,
            "media_key": "ond1_slime_venenoso_media"
        },
        {
            "id": "ond1_slime_eletrico",
            "name": "Slime Eeletrico", # Causa um pouco de dano extra
            "hp": 70, "attack": 4, "defense": 3, "initiative": 4, "luck": 4,
            "media_key": "ond1_slime_eletrico_media"
        },
        {
            "id": "ond1_slime_brilhante",
            "name": "Slime Brilhante", # Raro, dá mais ouro
            "hp": 75, "attack": 1, "defense": 1, "initiative": 20, "luck": 10,
            "media_key": "ond1_slime_brilhante_media"
        },
        {
            "id": "ond1_slime_escuridao",
            "name": "Slime da Escuridão", # Raro, muito defensivo
            "hp": 80, "attack": 3, "defense": 15, "initiative": 1, "luck": 5,
            "media_key": "ond1_slime_escuridao_media"
        },

        {
            "id": "ond1_rei_slime",
            "name": "Rei Slime",
            "is_boss": True,
            "hp": 1150, "attack": 20, "defense": 8, "initiative": 5, "luck": 10,
            "special_attack": {
                "name": "Esmagamento Real",
                "damage_multiplier": 2.5,
                "log_text": "O Rei Slime se infla e salta, caindo com um impacto esmagador!",
                "is_aoe": True
            },
            "xp_reward": 1, "gold_drop": 1,
            "media_key": "ond1_rei_slime_media"
        },
            #onda 2 ==== defesa
        {
            "id": "onda2_soldado_esqueletico",
            "name": "Soldado Esquelético",
            "hp": 60, "attack": 12, "defense": 8, "initiative": 10, "luck": 5,
            "media_key": "onda2_esqueleto_soldado_media"
        },
        {
            "id": "onda2_lacaio_reanimado",
            "name": "Lacaio Reanimado",
            "hp": 65, "attack": 14, "defense": 6, "initiative": 12, "luck": 5,
            "media_key": "onda2_esqueleto_lacaio_media"
        },
        {
            "id": "onda2_arqueiro_esqueletico",
            "name": "Arqueiro Esquelético",
            "hp": 70, "attack": 18, "defense": 4, "initiative": 15, "luck": 8,
            "media_key": "onda2_esqueleto_arqueiro_media"
        },
        {
            "id": "onda2_bruto_reanimado",
            "name": "Bruto Reanimado",
            "hp": 120, "attack": 15, "defense": 15, "initiative": 5, "luck": 3,
           "media_key": "onda2_bruto_reanimado_media"
        },
        {
            "id": "onda2_mago_esqueletico",
            "name": "Mago Esquelético",
            "hp": 140, "attack": 22, "defense": 3, "initiative": 12, "luck": 18,
            "media_key": "onda2_esqueleto_mago_media"
        },
        {
            "id": "onda2_espadachim_ossudo",
            "name": "Espadachim Ossudo",
            "hp": 150, "attack": 16, "defense": 6, "initiative": 25, "luck": 12,
            "media_key": "onda2_esqueleto_espadachim_media"
        },
        {
            "id": "onda2_legionario_caido",
            "name": "Legionário Caído",
            "hp": 160, "attack": 10, "defense": 25, "initiative": 2, "luck": 4,
            "media_key": "onda2_esqueleto_legionario_media"
        },
        
        {
            "id": "onda2_lobo_esqueletico",
            "name": "Lobo Esquelético",
            "hp": 180, "attack": 14, "defense": 4, "initiative": 35, "luck": 10,
            "media_key": "onda2_esqueleto_lobo_media"
        },
        {
            "id": "onda2_esqueleto_amaldicoado",
            "name": "Esqueleto Amaldiçoado",
            "hp": 200, "attack": 11, "defense": 9, "initiative": 9, "luck": 14,
            "media_key": "onda2_esqueleto_amaldicoado_media"
        },
        {
            "id": "onda2_campeao_do_sepulcro",
            "name": "Campeão do Sepulcro",
            "is_boss": True,
            "hp": 1300, "attack": 50, "defense": 20, "initiative": 20, "luck": 15,
            "special_attack": {
                "name": "Golpe Sepulcral",
                "damage_multiplier": 3.0,
                "log_text": "O Campeão do Sepulcro ergue sua lâmina antiga, que brilha com uma energia fantasmagórica antes de desferir um golpe devastador!",
                "is_aoe": True
            },
            "media_key": "onda2_esqueleto_campeao_media"
        },
        #0nda 3===================
        {
            "id": "onda3_goblin_catador",
            "name": "Goblin Catador",
            "hp": 135, "attack": 8, "defense": 4, "initiative": 12, "luck": 8,
            "media_key": "onda3_goblin_catador_media"
        },
        {
            "id": "onda3_goblin_fura_pe",
            "name": "Goblin Fura-Pé",
            "hp": 140, "attack": 10, "defense": 5, "initiative": 8, "luck": 5,
            "media_key": "onda3_goblin_fura_pe_media"
        },
        {
            "id": "onda3_atirador_goblin",
            "name": "Atirador Goblin",
            "hp": 150, "attack": 12, "defense": 3, "initiative": 15, "luck": 10,
            "media_key": "onda3_goblin_atirador_media"
        },
        
        # --- Incomuns ---
        {
            "id": "onda3_brutamontes_goblin",
            "name": "Brutamontes Goblin",
            "hp": 180, "attack": 15, "defense": 10, "initiative": 4, "luck": 3,
            "media_key": "onda3_goblin_brutamontes_media"
        },
        {
            "id": "onda3_goblin_xama",
            "name": "Goblin Xamã",
            "hp": 190, "attack": 18, "defense": 5, "initiative": 10, "luck": 15,
            "media_key": "onda3_goblin_xama_media"
        },
        {
            "id": "onda3_goblin_ardilheiro",
            "name": "Goblin Ardilheiro",
            "hp": 195, "attack": 9, "defense": 6, "initiative": 22, "luck": 20,
            "media_key": "onda3_goblin_ardilheiro_media"
        },

        # --- Raros ---
        {
            "id": "onda3_montador_de_lobo",
            "name": "Montador de Lobo Goblin",
            "hp": 200, "attack": 20, "defense": 12, "initiative": 30, "luck": 12,
            "media_key": "onda3_goblin_montador_lobo_media"
        },
        {
            "id": "onda3_goblin_bombardeiro",
            "name": "Goblin Bombardeiro",
            "hp": 240, "attack": 25, "defense": 4, "initiative": 18, "luck": 10,
            "media_key": "onda3_goblin_bombardeiro_media"
        },
        
        # --- Chefe / Elite ---
        {
            "id": "onda3_chefe_goblin",
            "name": "Chefe Goblin",
            "hp": 250, "attack": 22, "defense": 18, "initiative": 15, "luck": 15,
            "media_key": "onda3_goblin_chefe_media"
        },
        {
            "id": "onda3_rei_goblin",
            "name": "Rei Goblin",
            "is_boss": True,
            "hp": 1500, "attack": 60, "defense": 25, "initiative": 20, "luck": 20,
            "special_attack": {
                "name": "Chamado da Horda!",
                "damage_multiplier": 3.5,
                "log_text": "O Rei Goblin aponta seu cetro e solta um grito de guerra estridente! Em resposta, uma onda de ataques de todos os lados chove sobre você!",
                "is_aoe": True
            },
            "media_key": "goblin_rei_media"
        },
        # onda 4==============
        {
            "id": "onda4_mineiro_kobold",
            "name": "Mineiro Kobold",
            "hp": 150, "attack": 10, "defense": 8, "initiative": 8, "luck": 10,
            "media_key": "onda4_kobold_mineiro_media"
        },
        {
            "id": "onda4_lanceiro_kobold",
            "name": "Lanceiro Kobold",
            "hp": 160, "attack": 14, "defense": 7, "initiative": 10, "luck": 8,
            "media_key": "onda4_kobold_lanceiro_media"
        },
        {
            "id": "onda4_atirador_de_dardo",
            "name": "Atirador de Dardo Kobold",
            "hp": 175, "attack": 16, "defense": 5, "initiative": 14, "luck": 12,
            "media_key": "onda4_kobold_atirador_media"
        },
        
        # --- Incomuns ---
        {
            "id": "onda4_batedor_draconiano",
            "name": "Batedor Draconiano", # Mais rápido e sortudo
            "hp": 155, "attack": 15, "defense": 6, "initiative": 25, "luck": 20,
            "media_key": "onda4_kobold_batedor_media"
        },
        {
            "id": "onda4_armadilheiro_kobold",
            "name": "Armadilheiro Kobold",
            "hp": 165, "attack": 12, "defense": 10, "initiative": 18, "luck": 25,
            "media_key": "onda4_kobold_armadilheiro_media"
        },
        {
            "id": "onda4_geomante_kobold",
            "name": "Geomante Kobold", # Caster
            "hp": 150, "attack": 24, "defense": 7, "initiative": 15, "luck": 18,
            "media_key": "onda4_kobold_geomante_media"
        },

        # --- Raros ---
        {
            "id": "onda4_guarda_da_ninhada",
            "name": "Guarda da Ninhada Kobold", # Tanque
            "hp": 180, "attack": 18, "defense": 20, "initiative": 8, "luck": 10,
            "media_key": "onda4_kobold_guarda_ninhada_media"
        },
        {
            "id": "onda4_guerreiro_escamadura",
            "name": "Guerreiro Escamadura", # Elite
            "hp": 210, "attack": 22, "defense": 18, "initiative": 16, "luck": 15,
            "media_key": "onda4_kobold_guerreiro_escamadura_media"
        },
        
        # --- Chefe / Mini-Chefe ---
        {
            "id": "onda4_porta_estandarte_kobold",
            "name": "Porta-Estandarte Kobold",
            "hp": 220, "attack": 25, "defense": 22, "initiative": 20, "luck": 20,
            "media_key": "onda4_kobold_porta_estandarte_media"
        },
        {
            "id": "onda4_prole_de_dragao",
            "name": "Prole de Dragão",
            "is_boss": True,
            "hp": 2000, 
            "attack": 60, "defense": 28, "initiative": 25, "luck": 22,
            "special_attack": {
                "name": "Sopro Dracônico",
                "damage_multiplier": 4.0,
                "log_text": "A Prole de Dragão inspira profundamente, e de suas mandíbulas irrompe uma torrente de fogo que engole tudo ao seu redor!",
                "is_aoe": True
            },
            "media_key": "onda4_kobold_prole_dragao_media"
        },

    ],
    "pradaria_inicial": [
        # --- Comuns ---
        {
            "id": "pequeno_slime",
            "name": "Pequeno Slime",
            "hp": 15, "attack": 2, "defense": 1, "initiative": 5, "luck": 1,
            "xp_reward": 5, "gold_drop": 2,
           # "loot_table": [{"item_id": "geleia_comum", "drop_chance": 60.0}],
            "media_key": "slime_pequeno_media"
        },
        {
            "id": "slime_verde",
            "name": "Slime Verde",
            "hp": 25, "attack": 3, "defense": 2, "initiative": 3, "luck": 2,
            "xp_reward": 5, "gold_drop": 3,
            #"loot_table": [{"item_id": "geleia_verde", "drop_chance": 50.0}],
            "media_key": "slime_verde_media"
        },
        {
            "id": "slime_azul",
            "name": "Slime Azul", # Mais defensivo
            "hp": 35, "attack": 2, "defense": 4, "initiative": 2, "luck": 2,
            "xp_reward": 6, "gold_drop": 4,
            #"loot_table": [{"item_id": "geleia_azul", "drop_chance": 50.0}],
            "media_key": "slime_azul_media"
        },
        {
            "id": "slime_magma",
            "name": "Slime de Magma", # Mais agressivo
            "hp": 20, "attack": 5, "defense": 1, "initiative": 4, "luck": 2,
            "xp_reward": 6, "gold_drop": 4,
            #"loot_table": [{"item_id": "geleia_vermelha", "drop_chance": 50.0}],
            "media_key": "slime_magma_media"
        },
        
        # --- Incomuns ---
        {
            "id": "slime_terra",
            "name": "Slime Terra",
            "hp": 50, "attack": 4, "defense": 3, "initiative": 1, "luck": 3,
            "xp_reward": 10, "gold_drop": 8,
            "loot_table": [
                #{"item_id": "geleia_verde", "drop_chance": 70.0},
                #{"item_id": "geleia_grande", "drop_chance": 20.0}
            ],
            "media_key": "slime_terra_media"
        },
        {
            "id": "slime_venenoso",
            "name": "Slime Venenoso", 
            "hp": 25, "attack": 3, "defense": 2, "initiative": 12, "luck": 5,
            "xp_reward": 7, "gold_drop": 5,
            #"loot_table": [{"item_id": "geleia_pegajosa", "drop_chance": 40.0}],
            "media_key": "slime_venenoso_media"
        },
        {
            "id": "slime_eletrico",
            "name": "Slime Eeletrico", # Causa um pouco de dano extra
            "hp": 30, "attack": 4, "defense": 3, "initiative": 4, "luck": 4,
            "xp_reward": 10, "gold_drop": 6,
            #"loot_table": [{"item_id": "geleia_acida", "drop_chance": 40.0}],
            "media_key": "slime_eletrico_media"
        },

        # --- Raros ---
        {
            "id": "slime_brilhante",
            "name": "Slime Brilhante", # Raro, dá mais ouro
            "hp": 20, "attack": 1, "defense": 1, "initiative": 20, "luck": 10,
            "xp_reward": 1, "gold_drop": 5,
            #"loot_table": [{"item_id": "po_brilhante", "drop_chance": 100.0}],
            "media_key": "slime_brilhante_media"
        },
        {
            "id": "slime_escuridao",
            "name": "Slime da Escuridão", # Raro, muito defensivo
            "hp": 60, "attack": 3, "defense": 15, "initiative": 1, "luck": 5,
            "xp_reward": 2, "gold_drop": 1,
            #"loot_table": [{"item_id": "fragmento_metalico", "drop_chance": 30.0}],
            "media_key": "slime_escuridao_media"
        },

        # --- Mini-Chefe (Muito Raro) ---
        {
            "id": "rei_slime",
            "name": "Rei Slime",
            "hp": 150, "attack": 10, "defense": 8, "initiative": 5, "luck": 10,
            "xp_reward": 1, "gold_drop": 1,
            "loot_table": [
                #{"item_id": "coroa_de_geleia", "drop_chance": 10.0},
                #{"item_id": "nucleo_de_slime", "drop_chance": 100.0}
            ],
            "media_key": "rei_slime_media"
        }
    ],

    "floresta_sombria": [
        {
            "id": "goblin_batedor",
            "name": "Goblin Batedor",
            "hp": 40, "attack": 5, "defense": 1, "initiative": 8, "luck": 5,
            "xp_reward": 5, "ambush_chance": 1.25,
            "file_id_name": "goblin_batedor_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "pano_simples", "drop_chance": 30}
            ],
        },
        {
            "id": "lobo_magro",
            "name": "Lobo Magro",
            "hp": 25, "attack": 4, "defense": 2, "initiative": 7, "luck": 3,
            "xp_reward": 6, "ambush_chance": 0.0,
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
            "xp_reward": 5, "ambush_chance": 0.0,
            "file_id_name": "cogumelo_gigante_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "esporo_de_cogumelo", "drop_chance": 30}
            ],
        },
        {
            "id": "javali_com_presas",
            "name": "Javali com Presas",
            "hp": 35, "attack": 6, "defense": 3, "initiative": 5, "luck": 4,
            "xp_reward": 8, "ambush_chance": 0.0,
            "file_id_name": "javali_com_presas_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "presa_de_javali", "drop_chance": 30}
            ],
        },
        {
            "id": "ent_jovem",
            "name": "Ent Jovem",
            "hp": 40, "attack": 5, "defense": 5, "initiative": 3, "luck": 2,
            "xp_reward": 10, "ambush_chance": 0.0,
            "file_id_name": "ent_jovem_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "madeira_rara", "drop_chance": 30},
                {"item_id": "seiva_de_ent", "drop_chance": 30},
                {"item_id": "madeira", "drop_chance": 30}
            ],
        },
        {
            "id": "espectro_do_bosque",
            "name": "Espectro do Bosque",
            "hp": 45, "attack": 8, "defense": 2, "initiative": 6, "luck": 8,
            "xp_reward": 13, "ambush_chance": 0.0,
            "file_id_name": "espectro_bosque_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "ectoplasma", "drop_chance": 30},
                
            ],
        },
        {
            "id": "xama_goblin",
            "name": "Xamã Goblin",
            "hp": 55, "attack": 10, "defense": 3, "initiative": 7, "luck": 6,
            "xp_reward": 15, "ambush_chance": 0.0,
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
            "xp_reward": 26, "ambush_chance": 0.0,
            "file_id_name": "lobo_alfa_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "couro_de_lobo_alfa", "drop_chance": 30}
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
                {"item_id": "gema_bruta", "drop_chance": 30}
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
                {"item_id": "carapaca_de_pedra", "drop_chance": 30},
                {"item_id": "pedra", "drop_chance": 30}
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
                {"item_id": "pedra", "drop_chance": 30},
                {"item_id": "nucleo_de_golem", "drop_chance": 35}
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
                {"item_id": "escama_de_salamandra", "drop_chance": 30},
                {"item_id": "coracao_de_magma", "drop_chance": 30}
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
                {"item_id": "fragmento_gargula", "drop_chance": 30},
                {"item_id": "poeira_magica", "drop_chance": 30}
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
                {"item_id": "olho_de_basilisco", "drop_chance": 30},
              
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
                {"item_id": "palha_amaldicoada", "drop_chance": 30},
                {"item_id": "pano_simples", "drop_chance": 35}
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
                {"item_id": "pano_simples", "drop_chance": 35},
                
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
                {"item_id": "linho", "drop_chance": 35},
                {"item_id": "pano_simples", "drop_chance": 35}
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
                {"item_id": "couro_de_lobo", "drop_chance": 37},
                
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
                {"item_id": "gema_bruta", "drop_chance": 35},
              
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
                {"item_id": "ectoplasma", "drop_chance": 38},
                
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
                {"item_id": "pena", "drop_chance": 35},
                {"item_id": "gema_bruta", "drop_chance": 35}
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
                {"item_id": "pena", "drop_chance": 39},
            
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
                {"item_id": "gema_bruta", "drop_chance": 22},
                
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
                {"item_id": "pena", "drop_chance": 28}
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
              
                {"item_id": "gema_bruta", "drop_chance": 20}
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
                {"item_id": "gema_bruta", "drop_chance": 28},
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
                {"item_id": "asa_de_morcego", "drop_chance": 27},
                {"item_id": "gema_bruta", "drop_chance": 26}
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
                {"item_id": "gema_bruta", "drop_chance": 28}
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
                {"item_id": "barra_bronze", "drop_chance": 25}
            ],
        },
        {
            "id": "troll_da_caverna",
            "name": "Troll da Caverna",
            "hp": 440, "attack": 48, "defense": 42, "initiative": 27, "luck": 25,
            "xp_reward": 17, "gold_drop": 1, "ambush_chance": 0.0,
            "file_id_name": "troll_caverna_media",
            "loot_table": [
                {"item_id": "pele_de_troll", "drop_chance": 27},
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
                {"item_id": "ectoplasma", "drop_chance": 25},
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
                {"item_id": "barra_de_ferro", "drop_chance": 25},
            ],
            "file_id_name": "golem_ferro_incompleto_media",
        },
        {
            "id": "elemental_de_fogo",
            "name": "Elemental de Fogo",
            "hp": 480, "attack": 35, "defense": 30, "initiative": 26, "luck": 19,
            "xp_reward": 148, "gold_drop": 1, "ambush_chance": 0.5,
            "loot_table": [
                {"item_id": "essencia_de_fogo", "drop_chance": 25},
            ],
            "file_id_name": "elemental_fogo_media",
        },
        {
            "id": "cao_de_caca_de_metal",
            "name": "Cão de Caça de Metal",
            "hp": 288, "attack": 23, "defense": 22, "initiative": 44, "luck": 8,
            "xp_reward": 16, "gold_drop": 1, "ambush_chance": 0.5,
            "loot_table": [
                {"item_id": "engrenagem_usada", "drop_chance": 25},
                {"item_id": "barra_de_ferro", "drop_chance": 25}
            ],
            "file_id_name": "cao_caca_metal_media",
        },
        {
            "id": "anao_ferreiro_fantasma",
            "name": "Anão Ferreiro Fantasma",
            "hp": 382, "attack": 31, "defense": 21, "initiative": 22, "luck": 10,
            "xp_reward": 14, "gold_drop": 1, "ambush_chance": 0.6,
            "loot_table": [
                {"item_id": "martelo_enferrujado", "drop_chance": 27},
               
            ],
            "file_id_name": "anao_ferreiro_fantasma_media",
        },
        {
            "id": "salamandra_de_fogo",
            "name": "Salamandra de Fogo",
            "hp": 378, "attack": 44, "defense": 30, "initiative": 38, "luck": 9,
            "xp_reward": 14, "gold_drop": 1, "ambush_chance": 0.9,
            "loot_table": [
                {"item_id": "escama_incandescente", "drop_chance": 28},
                {"item_id": "essencia_de_fogo", "drop_chance": 30}
            ],
            "file_id_name": "salamandra_fogo_media",
        },
        {
            "id": "automato_com_defeito",
            "name": "Autômato com Defeito",
            "hp": 490, "attack": 42, "defense": 33, "initiative": 20, "luck": 7,
            "xp_reward": 27, "gold_drop": 1, "ambush_chance": 0.20,
            "loot_table": [
                {"item_id": "engrenagem_usada", "drop_chance": 35},
                {"item_id": "barra_de_ferro", "drop_chance": 32}
            ],
            "file_id_name": "automato_defeito_media",
        },
    ],

    "catacumba_reino": [
        {
            "id": "morcego_gigante",
            "name": "Morcego Gigante",
            "hp": 30, "attack": 10, "defense": 5, "initiative": 18, "luck": 5,
            "xp_reward": 15, "ambush_chance": 0.9,
            "file_id_name": "morcego_gigante_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "asa_de_morcego", "drop_chance": 37}
            ],
        },
        {
            "id": "dragao_negro",
            "name": "Dragão Negro",
            "hp": 100, "attack": 20, "defense": 12, "initiative": 9, "luck": 5,
            "xp_reward": 16, "ambush_chance": 0.10,
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
            "xp_reward": 15, "ambush_chance": 0.10,
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
            "xp_reward": 18, "ambush_chance": 0.10,
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
            "xp_reward": 27, "ambush_chance": 0.10,
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
            "xp_reward": 20, "gold_drop": 1, "ambush_chance": 0.10,
            "is_boss": True, "consume_energy": False,
            "file_id_name": "rei_lagarto_media",
            "loot_table": [
                {"item_id": "coroa_reptiliana", "drop_chance": 31},
                {"item_id": "cetro_dos_pantanos", "drop_chance": 32}
            ],
        },
    ],
}
