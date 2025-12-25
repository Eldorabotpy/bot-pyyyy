# modules/game_data/monsters.py

MONSTERS_DATA = {

    # --- MONSTROS ESPECIAIS DE EVOLUÇÃO ---
    "_evolution_trials": [
        
        # ==================== GUARDÕES DO GUERREIRO ====================
        {"id": "guardian_of_the_aegis", "name": "Guardião do Égide", 
         "hp": 800, "attack": 40, "defense": 70, "initiative": 20, "luck": 10, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_guardian_aegis_media"}, # T2

        {"id": "aspect_of_the_divine", "name": "Aspecto do Divino", 
         "hp": 2500, "attack": 120, "defense": 200, "initiative": 50, "luck": 30, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_aspect_divine_media"}, # T3
        
        {"id": "divine_sentinel", "name": "Sentinela Divina", 
         "hp": 3500, "attack": 180, "defense": 250, "initiative": 70, "luck": 40, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_divine_sentinel_media"}, # T4
        
        {"id": "celestial_bastion", "name": "Bastião Celestial", 
         "hp": 5000, "attack": 250, "defense": 350, "initiative": 90, "luck": 50, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_celestial_bastion_media"}, # T5
        
        {"id": "eldora_legend_guard", "name": "Guardião da Lenda", 
         "hp": 7500, "attack": 400, "defense": 500, "initiative": 120, "luck": 60, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_eldora_legend_media"}, # T6
        
        # ==================== GUARDÕES DO BERSERKER ====================
        {"id": "primal_spirit_of_rage", 
         "name": "Espírito Primordial da Fúria", 
         "hp": 700, "attack": 85, 
         "defense": 20, "initiative": 40, "luck": 15, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_spirit_rage_media"}, # T2

        {"id": "avatar_of_primal_wrath", 
         "name": "Avatar da Ira Primordial", 
         "hp": 2200, "attack": 250, "defense": 80, "initiative": 80, "luck": 25,
        "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_avatar_wrath_media"}, # T3

        {"id": "primal_rage_incarnate", "name": "Encarnação da Raiva", 
         "hp": 3000, "attack": 350, "defense": 120, "initiative": 100, "luck": 35, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_rage_incarnate_media"}, # T4
        
        {"id": "calamity_bringer", "name": "Portador da Calamidade", 
         "hp": 4800, "attack": 450, "defense": 150, "initiative": 130, "luck": 45, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_calamity_bringer_media"}, # T5
        
        {"id": "wrath_god_incarnate", "name": "Encarnação do Deus da Ira", 
         "hp": 7000, "attack": 650, "defense": 200, "initiative": 160, "luck": 60, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_wrath_god_media"}, # T6

        # ==================== GUARDÕES DO CAÇADOR ====================
        {"id": "phantom_of_the_watchtower", "name": "Fantasma da Atalaia", 
         "hp": 550, "attack": 70, "defense": 25, "initiative": 65, "luck": 40, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_phantom_watchtower_media"}, # T2
        
        {"id": "sky_piercer_hawk", "name": "Falcão Perfurador", 
         "hp": 1800, "attack": 150, "defense": 50, "initiative": 100, "luck": 55, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_sky_piercer_hawk_media"}, # T3
        
        {"id": "spectral_marksman", "name": "Atirador Espectral", 
         "hp": 2800, "attack": 250, "defense": 80, "initiative": 130, "luck": 70, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_spectral_marksman_media"}, # T4
        
        {"id": "horizon_walker", "name": "Caminhante do Horizonte", 
         "hp": 4000, "attack": 350, "defense": 110, "initiative": 160, "luck": 85, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_horizon_walker_media"}, # T5
        
        {"id": "legend_of_the_bow", "name": "Lenda do Arco", 
         "hp": 6000, "attack": 550, "defense": 150, "initiative": 200, "luck": 100, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_legend_bow_media"}, # T6
        
        # ==================== GUARDÕES DO MONGE ====================
        {"id": "avatar_of_the_four_elements", "name": "Avatar dos Quatro Elementos", 
         "hp": 680, "attack": 70, "defense": 45, "initiative": 55, "luck": 20, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_avatar_elements_media"}, # T2
        
        {"id": "echo_of_the_grandmaster", "name": "Eco do Grão-Mestre", 
         "hp": 2300, "attack": 140, "defense": 180, "initiative": 150, "luck": 40, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_echo_grandmaster_media"}, # T3
        
        {"id": "divine_hand", "name": "Mão Divina", 
         "hp": 3300, "attack": 220, "defense": 220, "initiative": 180, "luck": 55, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_divine_hand_media"}, # T4
        
        {"id": "inner_dragon_spirit", "name": "Espírito do Dragão", 
         "hp": 4500, "attack": 300, "defense": 280, "initiative": 220, "luck": 70, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_inner_dragon_media"}, # T5
        
        {"id": "legend_of_the_fist", "name": "Lenda do Punho", 
         "hp": 6800, "attack": 450, "defense": 350, "initiative": 250, "luck": 85, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_legend_fist_media"}, # T6

        # ==================== GUARDÕES DO MAGO ====================
        {"id": "raging_elemental_vortex", "name": "Vórtice Elemental Furioso", 
         "hp": 600, "attack": 90, "defense": 30, "initiative": 45, "luck": 15, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_raging_vortex_media"}, # T2
        
        {"id": "essence_of_pure_magic", "name": "Essência da Magia Pura", 
         "hp": 2000, "attack": 280, "defense": 90, "initiative": 100, "luck": 35, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_essence_magic_media"}, # T3
        
        {"id": "battlemage_prime", "name": "Mago de Batalha Prime", 
         "hp": 3000, "attack": 350, "defense": 150, "initiative": 130, "luck": 50, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_battlemage_prime_media"}, # T4
        
        {"id": "supreme_arcanist", "name": "Arcanista Supremo", 
         "hp": 4200, "attack": 450, "defense": 180, "initiative": 160, "luck": 65, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_supreme_arcanist_media"}, # T5
        
        {"id": "arcane_aspect", "name": "Aspecto Arcano", 
         "hp": 6500, "attack": 600, "defense": 220, "initiative": 190, "luck": 80, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_arcane_aspect_media"}, # T6
        
        # ==================== GUARDÕES DO BARDO ====================
        {"id": "silencing_critics", "name": "Críticos Silenciadores", 
         "hp": 750, "attack": 40, "defense": 50, "initiative": 50, "luck": 45, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_silencing_critics_media"}, # T2
        
        {"id": "deafening_silence", "name": "Silêncio Ensurdecedor", 
         "hp": 1900, "attack": 80, "defense": 100, "initiative": 120, "luck": 65, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_deafening_silence_media"}, # T3
        
        {"id": "unruly_orchestra", "name": "Orquestra Descontrolada", 
         "hp": 3000, "attack": 120, "defense": 150, "initiative": 150, "luck": 80, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_unruly_orchestra_media"}, # T4
        
        {"id": "chaotic_harmony", "name": "Harmonia Caótica", 
         "hp": 4500, "attack": 180, "defense": 200, "initiative": 180, "luck": 95, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_chaotic_harmony_media"}, # T5
        
        {"id": "primordial_symphony", "name": "Sinfonia Primordial", 
         "hp": 7000, "attack": 250, "defense": 280, "initiative": 220, "luck": 110, 
         "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_primordial_symphony_media"}, # T6

        # ==================== GUARDÕES DO ASSASSINO ====================
        {"id": "doppelganger_of_the_throne", "name": "Doppelgänger do Trono", 
         "hp": 600, "attack": 70, "defense": 35, "initiative": 80, "luck": 35, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_doppelganger_throne_media"}, # T2
        
        {"id": "quick_phantom", "name": "Fantasma Rápido", 
         "hp": 1700, "attack": 160, "defense": 60, "initiative": 140, "luck": 50, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_quick_phantom_media"}, # T3
        
        {"id": "dual_wielding_ronin", "name": "Ronin de Duas Lâminas", 
         "hp": 2800, "attack": 280, "defense": 90, "initiative": 180, "luck": 65, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_dual_wielding_ronin_media"}, # T4
        
        {"id": "shadow_of_fate", "name": "Sombra do Destino", 
         "hp": 4000, "attack": 380, "defense": 120, "initiative": 220, "luck": 80, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_shadow_fate_media"}, # T5
        
        {"id": "avatar_of_the_void", "name": "Avatar do Vazio", 
         "hp": 6000, "attack": 550, "defense": 160, "initiative": 250, "luck": 95, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_avatar_void_media"}, # T6

        # ==================== GUARDÕES DO SAMURAI ====================
        {"id": "phantom_of_the_dojo", "name": "Fantasma do Dojo", 
         "hp": 720, "attack": 75, "defense": 45, "initiative": 50, "luck": 20, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_phantom_dojo_media"}, # T2
        
        {"id": "master_swordsman_phantom", "name": "Fantasma Mestre Espadachim", 
         "hp": 1900, "attack": 130, "defense": 100, "initiative": 80, "luck": 30, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_master_swordsman_media"}, # T3
        
        {"id": "heavy_armored_general", "name": "General de Armadura Pesada", 
         "hp": 3200, "attack": 180, "defense": 200, "initiative": 110, "luck": 45, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_heavy_armored_general_media"}, # T4
        
        {"id": "spirit_of_honor", "name": "Espírito da Honra", 
         "hp": 4800, "attack": 250, "defense": 280, "initiative": 140, "luck": 60, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_spirit_honor_media"}, # T5
        
        {"id": "divine_blade_incarnate", "name": "Encarnação da Lâmina Divina", 
         "hp": 7200, "attack": 380, "defense": 380, "initiative": 180, "luck": 80, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_divine_blade_media"}, # T6

        # ==================== GUARDÕES DO CURANDEIRO (NOVO) ====================
        {"id": "plague_carrier_specter", "name": "Espectro Portador da Peste", 
         "hp": 700, "attack": 60, "defense": 35, "initiative": 40, "luck": 50, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_specter_plague_media"}, # T2
        
        {"id": "unholy_inquisitor", "name": "Inquisidor Profano", 
         "hp": 1800, "attack": 120, "defense": 100, "initiative": 70, "luck": 60, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_unholy_inquisitor_media"}, # T3
        
        {"id": "avatar_of_restoration", "name": "Avatar da Restauração", 
         "hp": 3000, "attack": 150, "defense": 180, "initiative": 100, "luck": 70, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_avatar_restoration_media"}, # T4
        
        {"id": "void_prophet", "name": "Profeta do Vazio", 
         "hp": 4500, "attack": 200, "defense": 250, "initiative": 130, "luck": 90, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_void_prophet_media"}, # T5
        
        {"id": "divine_healer_legend", "name": "Lenda da Cura Divina", 
         "hp": 7000, "attack": 350, "defense": 350, "initiative": 170, "luck": 110, "xp_reward": 0, "gold_drop": 0, "loot_table": [], 
         "media_key": "trial_healer_legend_media"}, # T6
    ],


    "defesa_reino": [
        {
            "id": "ond1_pequeno_slime",
            "name": "Pequeno Slime",
            "min_level": 1, "max_level": 5,
            "skills": ["gosma_pegajosa", "investida_brutal"],
            "hp": 10, "attack": 2, "defense": 1, "initiative": 5, "luck": 1,
            "media_key": "ond1_slime_pequeno_media"
        },
        {
            "id": "ond1_slime_verde",
            "name": "Slime Verde",
            "min_level": 1, "max_level": 5,
            "skills": ["gosma_pegajosa", "investida_brutal"],
            "hp": 20, "attack": 3, "defense": 2, "initiative": 3, "luck": 2,
            "media_key": "ond1_slime_verde_media"
        },
        {
            "id": "ond1_slime_azul",
            "name": "Slime Azul",
            "min_level": 1, "max_level": 5,
            "skills": ["gosma_pegajosa", "investida_brutal"],
            "hp": 30, "attack": 2, "defense": 4, "initiative": 2, "luck": 2,
            "media_key": "ond1_slime_azul_media"
        },
        {
            "id": "ond1_slime_magma",
            "name": "Slime de Magma",
            "min_level": 1, "max_level": 5,
            "skills": ["gosma_pegajosa", "investida_brutal"],
            "hp": 40, "attack": 5, "defense": 1, "initiative": 4, "luck": 2,
            "media_key": "ond1_slime_magma_media"
        },
        {
            "id": "ond1_slime_terra",
            "name": "Slime Terra",
            "min_level": 1, "max_level": 5,
            "skills": ["gosma_pegajosa", "investida_brutal"],
            "hp": 50, "attack": 4, "defense": 3, "initiative": 1, "luck": 3,
            "media_key": "ond1_slime_terra_media"
        },
        {
            "id": "ond1_slime_venenoso",
            "name": "Slime Venenoso", 
            "min_level": 1, "max_level": 5,
            "skills": ["gosma_pegajosa", "investida_brutal"],
            "hp": 60, "attack": 3, "defense": 2, "initiative": 12, "luck": 5,
            "media_key": "ond1_slime_venenoso_media"
        },
        {
            "id": "ond1_slime_eletrico",
            "name": "Slime Eeletrico", # Causa um pouco de dano extra
            "min_level": 1, "max_level": 5,
            "skills": ["gosma_pegajosa", "investida_brutal"], 
            "hp": 70, "attack": 4, "defense": 3, "initiative": 4, "luck": 4,
            "media_key": "ond1_slime_eletrico_media"
        },
        {
            "id": "ond1_slime_brilhante",
            "name": "Slime Brilhante", # Raro, dá mais ouro
            "min_level": 1, "max_level": 3,
            "skills": ["gosma_pegajosa", "investida_brutal"],
            "hp": 75, "attack": 1, "defense": 1, "initiative": 20, "luck": 10,
            "media_key": "ond1_slime_brilhante_media"
        },
        {
            "id": "ond1_slime_escuridao",
            "name": "Slime da Escuridão", # Raro, muito defensivo
            "min_level": 1, "max_level": 3,
            "skills": ["gosma_pegajosa", "investida_brutal"],
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
            "min_level": 1, "max_level": 5,
            "skills": ["gosma_pegajosa", "investida_brutal"],
            "hp": 15, "attack": 2, "defense": 1, "initiative": 5, "luck": 1,
            "xp_reward": 10, "gold_drop": 2,
            "loot_table": [{"item_id": "frasco_com_agua", "drop_chance": 10}],           
            "media_key": "slime_pequeno_media"
        },
        {
            "id": "slime_verde",
            "name": "Slime Verde",
            "hp": 25, "attack": 3, "defense": 2, "initiative": 3, "luck": 2,
            "min_level": 1, "max_level": 5,
            "skills": ["gosma_pegajosa", "investida_brutal"],
            "xp_reward": 10, "gold_drop": 3,
            "loot_table": [{"item_id": "geleia_slime", "drop_chance": 10}],
            "media_key": "slime_verde_media"
        },
        {
            "id": "slime_azul",
            "name": "Slime Azul", 
            "min_level": 1, "max_level": 5,
            "skills": ["gosma_pegajosa", "investida_brutal"],
            "hp": 35, "attack": 2, "defense": 4, "initiative": 2, "luck": 2,
            "xp_reward": 10, "gold_drop": 4,
            "loot_table": [{"item_id": "cristal_mana_bruto", "drop_chance": 10}],
            "media_key": "slime_azul_media"
        },
        {
            "id": "slime_magma",
            "name": "Slime de Magma", 
            "min_level": 1, "max_level": 5,
            "skills": ["bola_de_fogo_menor", "investida_brutal"],
            "hp": 20, "attack": 5, "defense": 1, "initiative": 4, "luck": 2,
            "xp_reward": 10, "gold_drop": 4,
            "loot_table": [{"item_id": "pocao_cura_leve", "drop_chance": 2}],
            "media_key": "slime_magma_media"
        },
        
        # --- Incomuns ---
        {
            "id": "slime_terra",
            "name": "Slime Terra",
            "min_level": 1, "max_level": 5,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 50, "attack": 4, "defense": 3, "initiative": 1, "luck": 3,
            "xp_reward": 10, "gold_drop": 8,
            "loot_table": [{"item_id": "raiz_da_fortuna", "drop_chance": 10}],
            "media_key": "slime_terra_media"
        },
        {
            "id": "slime_venenoso",
            "name": "Slime Venenoso",
            "min_level": 1, "max_level": 5,
            "skills": ["ferrao_toxico", "investida_brutal"], 
            "hp": 25, "attack": 3, "defense": 2, "initiative": 12, "luck": 5,
            "xp_reward": 10, "gold_drop": 5,
            "loot_table": [{"item_id": "folha_sombria", "drop_chance": 10}],
            "media_key": "slime_venenoso_media"
        },
        {
            "id": "slime_eletrico",
            "name": "Slime Eeletrico", 
            "min_level": 1, "max_level": 5,
            "skills": ["gosma_pegajosa", "investida_brutal"],
            "hp": 30, "attack": 4, "defense": 3, "initiative": 4, "luck": 4,
            "xp_reward": 10, "gold_drop": 6,
            "loot_table": [{"item_id": "essencia_purificadora", "drop_chance": 10}],
            "media_key": "slime_eletrico_media"
        },

        # --- Raros ---
        {
            "id": "slime_brilhante",
            "name": "Slime Brilhante", # Raro, dá mais ouro
            "min_level": 1, "max_level": 5,
            "skills": ["gosma_pegajosa", "investida_brutal"],
            "hp": 20, "attack": 1, "defense": 1, "initiative": 20, "luck": 10,
            "xp_reward": 10, "gold_drop": 5,
            "loot_table": [{"item_id": "essencia_purificadora", "drop_chance": 10}],
            "media_key": "slime_brilhante_media"
        },
        {
            "id": "slime_escuridao",
            "name": "Slime da Escuridão", # Raro, muito defensivo
            "min_level": 1, "max_level": 5,
            "skills": ["gosma_pegajosa", "investida_brutal"],
            "hp": 60, "attack": 3, "defense": 15, "initiative": 1, "luck": 5,
            "xp_reward": 10, "gold_drop": 1,
            "loot_table": [{"item_id": "folha_sombria", "drop_chance": 10}],
            "media_key": "slime_escuridao_media"
        },

        # --- Mini-Chefe (Muito Raro) ---
        {
            "id": "rei_slime",
            "name": "Rei Slime",
            "min_level": 1, "max_level": 5,
            "skills": ["esmagar", "investida_brutal"],
            "hp": 150, "attack": 10, "defense": 8, "initiative": 5, "luck": 10,
            "xp_reward": 10, "gold_drop": 1,
            "loot_table": [{"item_id": "po_de_iniciativa", "drop_chance": 5}],
            "media_key": "rei_slime_media"
        }
    ],

    "floresta_sombria": [
        {
            "id": "goblin_batedor",
            "name": "Goblin Batedor",
            "min_level": 5, "max_level": 10,
            "skills": ["golpe_sujo", "golpe_de_escudo"],
            "hp": 40, "attack": 5, "defense": 1, "initiative": 8, "luck": 5,
            "xp_reward": 13, "ambush_chance": 1.25,
            "file_id_name": "goblin_batedor_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "pano_simples", "drop_chance": 30}
            ],
        },
        {
            "id": "lobo_magro",
            "name": "Lobo Magro",
            "min_level": 5, "max_level": 10,
            "skills": ["mordida_feroz", "garras_dilacerantes"],
            "hp": 25, "attack": 4, "defense": 2, "initiative": 7, "luck": 3,
            "xp_reward": 13, "ambush_chance": 0.0,
            "file_id_name": "lobo_magro_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "couro_de_lobo", "drop_chance": 30}
            ],
        },
        {
            "id": "cogumelo_gigante",
            "name": "Cogumelo Gigante",
            "min_level": 5, "max_level": 10,
            "skills": ["drenar_vida", "gosma_pegajosa"],
            "hp": 30, "attack": 4, "defense": 4, "initiative": 2, "luck": 1,
            "xp_reward": 13, "ambush_chance": 0.0,
            "file_id_name": "cogumelo_gigante_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "esporo_de_cogumelo", "drop_chance": 30}
            ],
        },
        {
            "id": "javali_com_presas",
            "name": "Javali com Presas",
            "min_level": 5, "max_level": 10,
            "skills": ["investida_brutal", "mordida_feroz"],
            "hp": 35, "attack": 6, "defense": 3, "initiative": 5, "luck": 4,
            "xp_reward": 13, "ambush_chance": 0.0,
            "file_id_name": "javali_com_presas_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "presa_de_javali", "drop_chance": 30}
            ],
        },
        {
            "id": "ent_jovem",
            "name": "Ent Jovem",
            "min_level": 5, "max_level": 10,
            "skills": ["terremoto_local", "regeneracao_natural"],
            "hp": 40, "attack": 5, "defense": 5, "initiative": 3, "luck": 2,
            "xp_reward": 13, "ambush_chance": 0.0,
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
            "min_level": 5, "max_level": 10,
            "skills": ["grito_amedrontador", "toque_frio"],
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
            "min_level": 5, "max_level": 10,
            "skills": ["regeneracao_natural", "laminas_de_vento"],
            "hp": 55, "attack": 10, "defense": 3, "initiative": 7, "luck": 6,
            "xp_reward": 13, "ambush_chance": 0.0,
            "file_id_name": "xama_goblin_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "fio_de_prata", "drop_chance": 35}
            ],
        },
        {
            "id": "lobo_alfa",
            "name": "Lobo Alfa",
            "min_level": 5, "max_level": 10,
            "skills": ["garras_dilacerantes", "mordida_feroz"],
            "hp": 70, "attack": 15, "defense": 7, "initiative": 10, "luck": 15,
            "xp_reward": 13, "ambush_chance": 0.0,
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
            "min_level": 15, "max_level": 25,
            "skills": ["golpe_sujo", "terremoto_local"],
            "hp": 125, "attack": 18, "defense": 24, "initiative": 15, "luck": 15,
            "xp_reward":15, "ambush_chance": 0.20,
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
            "min_level": 15, "max_level": 25,
            "skills": ["golpe_sujo", "terremoto_local"],
            "hp": 240, "attack": 7, "defense": 30, "initiative": 16, "luck": 5,
            "xp_reward": 15, "ambush_chance": 0.0,
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
            "min_level": 15, "max_level": 25,
            "skills": ["golpe_sujo", "terremoto_local"],
            "hp": 360, "attack": 20, "defense": 22, "initiative": 10, "luck": 2,
            "xp_reward": 15, "ambush_chance": 0.0,
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
            "min_level": 15, "max_level": 25,
            "skills": ["golpe_sujo", "terremoto_local"],
            "hp": 345, "attack": 24, "defense": 38, "initiative": 19, "luck": 8,
            "xp_reward": 15, "ambush_chance": 0.0,
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
            "min_level": 15, "max_level": 25,
            "skills": ["golpe_sujo", "terremoto_local"],
            "hp": 435, "attack": 36, "defense": 36, "initiative": 20, "luck": 10,
            "xp_reward": 15, "ambush_chance": 0.30,
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
            "min_level": 15, "max_level": 25,
            "skills": ["golpe_sujo", "terremoto_local"],
            "hp": 280, "attack": 28, "defense": 20, "initiative": 38, "luck": 7,
            "xp_reward": 15, "ambush_chance": 6.60,
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
            "min_level": 25, "max_level": 35,
            "skills": ["grito_amedrontador", "drenar_vida"],
            "hp": 252, "attack": 19, "defense": 14, "initiative": 16, "luck": 5,
            "xp_reward": 18, "ambush_chance": 0.0,
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
            "min_level": 25, "max_level": 35,
            "skills": ["laminas_de_vento", "laminas_de_vento"],
            "hp": 178, "attack": 39, "defense": 16, "initiative": 18, "luck": 8,
            "xp_reward": 18, "ambush_chance": 0.0,
            "file_id_name": "passaro_roc_gigante_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "pano_simples", "drop_chance": 35},
                
            ],
        },
        {
            "id": "verme_de_seda",
            "name": "Verme de Seda",
            "min_level": 25, "max_level": 35,
            "skills": ["gosma_pegajosa", "teia_apris"],
            "hp": 160, "attack": 25, "defense": 20, "initiative": 14, "luck": 9,
            "xp_reward": 18, "ambush_chance": 0.0,
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
            "min_level": 25, "max_level": 35,
            "skills": ["mordida_feroz", "garras_dilacerantes"],
            "hp": 384, "attack": 26, "defense": 16, "initiative": 18, "luck": 6,
            "xp_reward": 18, "ambush_chance": 0.0,
            "file_id_name": "lobisomem_campones_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "couro_de_lobo", "drop_chance": 37},
                
            ],
        },
        {
            "id": "gnomo_de_jardim_travesso",
            "name": "Gnomo de Jardim Travesso",
            "min_level": 25, "max_level": 35,
            "skills": ["golpe_sujo", "golpe_sujo"],
            "hp": 348, "attack": 41, "defense": 13, "initiative": 12, "luck": 12,
            "xp_reward": 18, "ambush_chance": 0.0,
            "file_id_name": "gnomo_de_jardim_travesso_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "gema_bruta", "drop_chance": 35},
              
            ],
        },
        {
            "id": "banshee_dos_campos",
            "name": "Banshee dos Campos",
            "min_level": 25, "max_level": 35,
            "skills": ["grito_amedrontador", "drenar_vida"],
            "hp": 372, "attack": 47, "defense": 14, "initiative": 19, "luck": 10,
            "xp_reward": 18, "ambush_chance": 0.0,
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
            "min_level": 35, "max_level": 45,
            "skills": ["laminas_de_vento", "garras_dilacerantes"],
            "hp": 142, "attack": 34, "defense": 16, "initiative": 44, "luck": 30,
            "xp_reward": 20, "ambush_chance": 0.0,
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
            "min_level": 35, "max_level": 45,
            "skills": ["bola_de_fogo_menor", "garras_dilacerantes"],
            "hp": 165, "attack": 28, "defense": 19, "initiative": 23, "luck": 8,
            "xp_reward": 20, "ambush_chance": 0.0,
            "gold_drop": 1,
            "file_id_name": "grifo_jovem_media",
            "loot_table": [
                {"item_id": "pena", "drop_chance": 39},
            
            ],
        },
        {
            "id": "elemental_do_ar_menor",
            "name": "Elemental do Ar Menor",
            "min_level": 35, "max_level": 45,
            "skills": ["laminas_de_vento", "investida_brutal"],
            "hp": 255, "attack": 26, "defense": 18, "initiative": 36, "luck": 12,
            "xp_reward": 20, "ambush_chance": 0.0,
            "file_id_name": "elemental_ar_menor_media",
            "gold_drop": 1,
            "loot_table": [
                {"item_id": "gema_bruta", "drop_chance": 22},
                
            ],
        },
        {
            "id": "corvo_carniceiro_gigante",
            "name": "Corvo Carniceiro Gigante",
            "min_level": 35, "max_level": 45,
            "skills": ["laminas_de_vento", "garras_dilacerantes"],
            "hp": 348, "attack": 35, "defense": 17, "initiative": 37, "luck": 10,
            "xp_reward": 20, "ambush_chance": 0.0,
            "gold_drop": 1,
            "file_id_name": "corvo_gigante_media",
            "loot_table": [
                {"item_id": "pena", "drop_chance": 28}
            ],
        },
        {
            "id": "wyvern_filhote",
            "name": "Wyvern Filhote",
            "min_level": 35, "max_level": 45,
            "skills": ["bola_de_fogo_menor", "investida_brutal"],
            "hp": 288, "attack": 31, "defense": 21, "initiative": 32, "luck": 7,
            "xp_reward": 20, "ambush_chance": 0.0,
            "gold_drop": 1,
            "file_id_name": "wyvern_filhote_media",
            "loot_table": [
              
                {"item_id": "gema_bruta", "drop_chance": 20}
            ],
        },
        {
            "id": "abelha_gigante_rainha",
            "name": "Abelha Gigante Rainha",
            "min_level": 35, "max_level": 45,
            "skills": ["laminas_de_vento", "ferrao_toxico"],
            "hp": 272, "attack": 39, "defense": 20, "initiative": 50, "luck": 69,
            "xp_reward": 20, "ambush_chance": 0.0,
            "gold_drop": 1,
            "file_id_name": "abelha_gigante_rainha_media",
            "loot_table": [
                {"item_id": "cera_de_abelha", "drop_chance": 28},
            ],
        },
    ],

    "mina_ferro": [
        {
            "id": "morcego_das_minas",
            "name": "Morcego das Minas",
            "min_level": 45, "max_level": 55,
            "skills": ["laminas_de_vento", "ferrao_toxico"],
            "hp": 258, "attack": 27, "defense": 28, "initiative": 38, "luck": 19,
            "xp_reward": 22, "gold_drop": 1, "ambush_chance": 0.20,
            "file_id_name": "morcego_minas_media",
            "loot_table": [
                {"item_id": "asa_de_morcego", "drop_chance": 27},
                {"item_id": "gema_bruta", "drop_chance": 26}
            ],
        },
        {
            "id": "kobold_capataz",
            "name": "Kobold Capataz",
            "min_level": 45, "max_level": 55,
            "skills": ["terremoto_local", "golpe_sujo"],
            "hp": 376, "attack": 52, "defense": 22, "initiative": 32, "luck": 32,
            "xp_reward": 22, "gold_drop": 1, "ambush_chance": 0.18,
            "file_id_name": "kobold_capataz_media",
            "loot_table": [
                {"item_id": "minerio_de_ferro", "drop_chance": 40},
                {"item_id": "gema_bruta", "drop_chance": 28}
            ],
        },
        {
            "id": "slime_de_ferrugem",
            "name": "Slime de Ferrugem",
            "min_level": 45, "max_level": 55,
            "skills": ["gosma_pegajosa", "investida_brutal"],
            "hp": 390, "attack": 26, "defense": 16, "initiative": 36, "luck": 26,
            "xp_reward": 22, "gold_drop": 1, "ambush_chance": 0.0,
            "file_id_name": "slime_ferrugem_media",
            "loot_table": [
                {"item_id": "minerio_estanho", "drop_chance": 6},
                
            ],
        },
        {
            "id": "troll_da_caverna",
            "name": "Troll da Caverna",
            "min_level": 45, "max_level": 55,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 440, "attack": 48, "defense": 42, "initiative": 27, "luck": 25,
            "xp_reward": 22, "gold_drop": 1, "ambush_chance": 0.0,
            "file_id_name": "troll_caverna_media",
            "loot_table": [
                {"item_id": "pele_de_troll", "drop_chance": 27},
                {"item_id": "sangue_regenerativo", "drop_chance": 18}
            ],
        },
        {
            "id": "caranguejo_de_rocha",
            "name": "Caranguejo de Rocha",
            "min_level": 45, "max_level": 55,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 310, "attack": 30, "defense": 40, "initiative": 15, "luck": 26,
            "xp_reward": 22, "gold_drop": 1, "ambush_chance": 0.0,
            "file_id_name": "caranguejo_rocha_media",
            "loot_table": [
                {"item_id": "carapaca_de_pedra", "drop_chance": 65},
                {"item_id": "pedra", "drop_chance": 100}
            ],
        },
        {
            "id": "fantasma_de_mineiro",
            "name": "Fantasma de Mineiro",
            "min_level": 45, "max_level": 55,
            "skills": ["toque_frio", "grito_amedrontador"],
            "hp": 464, "attack": 33, "defense": 29, "initiative": 36, "luck": 14,
            "xp_reward": 22, "gold_drop": 1, "ambush_chance": 0.25,
            "file_id_name": "fantasma_mineiro_media",
            "loot_table": [
                {"item_id": "ectoplasma", "drop_chance": 25},
            ],
        },
    ],
# falta arruuma lvl e skil
    "forja_abandonada": [
        {
            "id": "golem_de_ferro_incompleto",
            "name": "Golem de Ferro Incompleto",
            "min_level": 55, "max_level": 65,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 495, "attack": 32, "defense": 44, "initiative": 28, "luck": 16,
            "xp_reward": 24, "gold_drop": 1, "ambush_chance": 0.0,
            "loot_table": [
                {"item_id": "martelo_enferrujado", "drop_chance": 25},
            ],
            "file_id_name": "golem_ferro_incompleto_media",
        },
        {
            "id": "elemental_de_fogo",
            "name": "Elemental de Fogo",
            "min_level": 55, "max_level": 65,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 480, "attack": 35, "defense": 30, "initiative": 26, "luck": 19,
            "xp_reward": 24, "gold_drop": 1, "ambush_chance": 0.5,
            "loot_table": [
                {"item_id": "essencia_de_fogo", "drop_chance": 25},
            ],
            "file_id_name": "elemental_fogo_media",
        },
        {
            "id": "cao_de_caca_de_metal",
            "name": "Cão de Caça de Metal",
            "min_level": 55, "max_level": 65,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 288, "attack": 23, "defense": 22, "initiative": 44, "luck": 8,
            "xp_reward": 24, "gold_drop": 1, "ambush_chance": 0.5,
            "loot_table": [
                {"item_id": "engrenagem_usada", "drop_chance": 25},
                {"item_id": "martelo_enferrujado", "drop_chance": 25}
            ],
            "file_id_name": "cao_caca_metal_media",
        },
        {
            "id": "anao_ferreiro_fantasma",
            "name": "Anão Ferreiro Fantasma",
            "min_level": 55, "max_level": 65,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 382, "attack": 31, "defense": 21, "initiative": 22, "luck": 10,
            "xp_reward": 24, "gold_drop": 1, "ambush_chance": 0.6,
            "loot_table": [
                {"item_id": "martelo_enferrujado", "drop_chance": 27},
               
            ],
            "file_id_name": "anao_ferreiro_fantasma_media",
        },
        {
            "id": "salamandra_de_fogo",
            "name": "Salamandra de Fogo",
            "min_level": 55, "max_level": 65,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 378, "attack": 44, "defense": 30, "initiative": 38, "luck": 9,
            "xp_reward": 24, "gold_drop": 1, "ambush_chance": 0.9,
            "loot_table": [
                {"item_id": "escama_incandescente", "drop_chance": 28},
                {"item_id": "essencia_de_fogo", "drop_chance": 30}
            ],
            "file_id_name": "salamandra_fogo_media",
        },
        {
            "id": "automato_com_defeito",
            "name": "Autômato com Defeito",
            "min_level": 55, "max_level": 65,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 490, "attack": 42, "defense": 33, "initiative": 20, "luck": 7,
            "xp_reward": 24, "gold_drop": 1, "ambush_chance": 0.20,
            "loot_table": [
                {"item_id": "engrenagem_usada", "drop_chance": 35},
                #{"item_id": "barra_de_ferro", "drop_chance": 32}
            ],
            "file_id_name": "automato_defeito_media",
        },
    ],
    "pantano_maldito": [
        {
            "id": "carnic_faminto",
            "name": "Carniçal Faminto",
            "min_level": 75, "max_level": 85,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 500, "attack": 40, "defense": 33, "initiative": 37, "luck": 55,
            "xp_reward": 26, "gold_drop": 5,
            "loot_table": [{"item_id": "pedra_vulcanica", "drop_chance": 10 }],
            "media_key": "carnical_faminto_media"
        },
        {
            "id": "verme_carcaca",
            "name": "Verme de Carcaça",
            "min_level": 75, "max_level": 85,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 535, "attack": 44, "defense": 46, "initiative": 39, "luck": 54,
            "xp_reward": 26, "gold_drop": 6,
            "loot_table": [{"item_id": "semente_encantada", "drop_chance": 10 }],
            "media_key": "verme_carcaca_media"
        },
        {
            "id": "abom_lodo",
            "name": "Abominação de Lodo",
            "min_level": 75, "max_level": 85,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 540, "attack": 46, "defense": 50, "initiative": 52, "luck": 53,
            "xp_reward": 26, "gold_drop": 8,
            "loot_table": [{"item_id": "nucleo_de_magma", "drop_chance": 10 }],
            "media_key": "abominacao_lodo_media"
        },
        {
            "id": "espectro_pantano",
            "name": "Espectro do Pântano",
            "min_level": 75, "max_level": 85,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 545, "attack": 44, "defense": 55, "initiative": 58, "luck": 60,
            "xp_reward": 26, "gold_drop": 10,
            "loot_table": [{"item_id": "", "drop_chance": 10 }],
            "media_key": "espectro_pantano_media"
        },
        {
            "id": "sanguessuga_gigante",
            "name": "Sanguessuga Gigante",
            "min_level": 75, "max_level": 85,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 550, "attack": 46, "defense": 48, "initiative": 56, "luck": 67,
            "xp_reward": 26, "gold_drop": 12,
            "loot_table": [{"item_id": "oleo_mineral", "drop_chance": 6}],
            "media_key": "sanguessuga_gigante_media"
        },
        {
            "id": "crocodilo_mutante",
            "name": "Crocodilo Mutante",
            "min_level": 75, "max_level": 85,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 555, "attack": 48, "defense": 55, "initiative": 54, "luck": 66,
            "xp_reward": 26, "gold_drop": 15,
            "loot_table": [
                {"item_id": "oleo_mineral"},
                #{"item_id": "", "drop_chance": 6}
            ],
            "media_key": "crocodilo_mutante_media"
        }
    ],
    "picos_gelados": [
        {
            "id": "lebre_neve",
            "name": "Lebre da Neve",
            "min_level": 85, "max_level": 95,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 560, "attack": 50, "defense": 52, "initiative": 42, "luck": 68,
            "xp_reward": 28, "gold_drop": 8,
            #"loot_table": [{"item_id": , "drop_chance": 32}],
            "media_key": "lebre_neve_media"
        },
        {
            "id": "urso_polar_jovem",
             "name": "Urso Polar Jovem",
             "min_level": 85, "max_level": 95,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 565, "attack": 56, "defense": 50, "initiative": 46, "luck": 57,
            "xp_reward": 28, "gold_drop": 12,
            #"loot_table": [{"item_id": ,"drop_chance": 32}],
            "media_key": "urso_polar_jovem_media"
        },
        {
            "id": "golem_de_gelo",
            "name": "Golem de Gelo",
            "min_level": 85, "max_level": 95,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 570, "attack": 64, "defense": 50, "initiative": 53, "luck": 45,
            "xp_reward": 28, "gold_drop": 15,
            #"loot_table": [{"item_id": ,"drop_chance": 32}],
            "media_key": "golem_de_gelo_media"
        },
        {
            "id": "elemental_vento",
            "name": "Elemental do Vento Gélido",
            "min_level": 85, "max_level": 95,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 575, "attack": 52, "defense": 58, "initiative": 50, "luck": 42,
            "xp_reward": 28, "gold_drop": 18,
            #"loot_table": [{"item_id": ,"drop_chance": 32}],
            "media_key": "elemental_vento_gelido_media"
        },
        {
            "id": "urso_polar_alpha",
            "name": "Urso Polar Alfa",
            "min_level": 85, "max_level": 95,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 580, "attack": 65, "defense": 55, "initiative": 57, "luck": 49,
            "xp_reward": 28, "gold_drop": 25,
            #"loot_table": [{"item_id": ,"drop_chance": 32}],
            "media_key": "urso_polar_alfa_media"
        },
        {
            "id": "gigante_congelado",
            "name": "Gigante Congelado",
            "min_level": 85, "max_level": 95,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 585, "attack": 70, "defense": 65, "initiative": 42, "luck": 55,
            "xp_reward": 28, "gold_drop": 30,
            "loot_table": [
            #{"item_id": , "drop_chance": 32},
            #{"item_id": }
            ],
            "media_key": "gigante_congelado_media"
        }
    ],
    "deserto_ancestral": [
        {
            "id": "escorp_venenoso",
            "name": "Escorpião Venenoso",
            "min_level": 95, "max_level": 105,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 590, "attack": 58, "defense": 48, "initiative": 65, "luck": 50,
            "xp_reward": 30, "gold_drop": 20,
            #"loot_table": [{"item_id": , "drop_chance": 32"}],
            "media_key": "escorpiao_venenoso_media"
        },
        {
            "id": "cobra_hieroglifica",
            "name": "Cobra Hieroglífica",
            "min_level": 95, "max_level": 105,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 595, "attack": 60, "defense": 30, "initiative": 58, "luck": 52,
            "xp_reward": 30, "gold_drop": 25,
            #"loot_table": [{"item_id": ,"drop_chance": 32"}],
            "media_key": "cobra_hieroglifica_media"
        },
        {
            "id": "guardiao_mumificado",
            "name": "Guardião Mumificado",
            "min_level": 95, "max_level": 105,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 600, "attack": 60, "defense": 50, "initiative": 45, "luck": 48,
            "xp_reward": 30, "gold_drop": 30,
            #"loot_table": [{"item_id": ,"drop_chance": 32}],
            "media_key": "guardiao_mumificado_media"
        },
        {
            "id": "elemental_areia",
            "name": "Elemental de Areia",
            "min_level": 95, "max_level": 105,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 610, "attack": 70, "defense": 55, "initiative": 40, "luck": 45,
            "xp_reward": 30, "gold_drop": 35,
            #"loot_table": [{"item_id": ,"drop_chance": 32}],
            "media_key": "elemental_areia_media"
        },
        {
            "id": "chacal_fantasma",
            "name": "Chacal Fantasma",
            "min_level": 95, "max_level": 105,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 615, "attack": 75, "defense": 50, "initiative": 44, "luck": 40,
            "xp_reward": 30, "gold_drop": 40,
            #"loot_table": [{"item_id": ,"drop_chance": 32}],
            "media_key": "chacal_fantasma_media"
        },
        {
            "id": "farao_maldito",
            "name": "Faraó Maldito",
            "min_level": 95, "max_level": 105,
            "skills": ["terremoto_local", "investida_brutal"],
            "hp": 620, "attack": 80, "defense": 60, "initiative": 46, "luck": 55,
            "xp_reward": 30, "gold_drop": 50,
            "loot_table": [
                #{"item_id": ,"drop_chance": 32},
                #{"item_id": }
            ],
            "media_key": "farao_maldito_media"
        }
    ]
}

# ==============================================================================
# 🧠 BANCO DE DADOS DE SKILLS DOS MONSTROS (EXPANDIDO)
# ==============================================================================
MONSTER_SKILLS_DB = {
    # --- 🐺 BESTIAL / FÍSICO (Lobos, Ursos, Javalis) ---
    "mordida_feroz": {
        "name": "Mordida Feroz", "chance": 0.30, 
        "damage_mult": 1.3, 
        "log": "{mob} crava as presas em você, rasgando sua armadura!"
    },
    "esmagar": {
        "name": "Esmagar", "chance": 0.25, 
        "damage_mult": 1.5, 
        "log": "{mob} levanta seus braços e ESMAGA você com força bruta!"
    },
    "investida_brutal": {
        "name": "Investida Brutal", "chance": 0.20,
        "damage_mult": 1.6,
        "log": "{mob} corre em sua direção como um trem, te jogando longe!"
    },
    "garras_dilacerantes": {
        "name": "Garras Dilacerantes", "chance": 0.35,
        "damage_mult": 1.2,
        "log": "{mob} desfere uma sequência rápida de arranhões profundos!"
    },

    # --- 🗡️ HUMANOIDE / ARMAS (Goblins, Bandidos, Orcs) ---
    "golpe_sujo": {
        "name": "Golpe Sujo", "chance": 0.25,
        "damage_mult": 1.4,
        "log": "{mob} joga areia nos seus olhos e acerta um golpe traiçoeiro!"
    },
    "chuva_de_flechas": {
        "name": "Disparo Preciso", "chance": 0.30,
        "damage_mult": 1.3,
        "log": "{mob} mira com calma e dispara um projétil direto em seu ponto fraco!"
    },
    "golpe_de_escudo": {
        "name": "Golpe de Escudo", "chance": 0.20,
        "damage_mult": 1.1,
        "log": "{mob} bate o escudo em seu rosto, te deixando tonto!"
    },

    # --- 🕷️ VENENOSO / INSIDIOSO (Aranhas, Cobras, Plantas) ---
    "gosma_pegajosa": {
        "name": "Gosma Pegajosa", "chance": 0.20, 
        "damage_mult": 0.8, 
        "log": "{mob} cospe uma gosma verde que dificulta seus movimentos!" 
    },
    "ferrao_toxico": {
        "name": "Ferrão Tóxico", "chance": 0.30,
        "damage_mult": 1.2, # Simula dano extra do veneno
        "log": "{mob} perfura sua pele injetando um veneno doloroso!"
    },
    "teia_apris": {
        "name": "Teia Aprisionadora", "chance": 0.15,
        "damage_mult": 0.5,
        "log": "{mob} te envolve em teias, impedindo que você se defenda direito!"
    },

    # --- 💀 MORTOS-VIVOS / TREVAS (Esqueletos, Zumbis, Fantasmas) ---
    "grito_amedrontador": {
        "name": "Grito Amedrontador", "chance": 0.15,
        "damage_mult": 0.5,
        "log": "{mob} solta um grito que gela sua espinha, diminuindo sua moral!"
    },
    "drenar_vida": {
        "name": "Drenar Vida", "chance": 0.20,
        "damage_mult": 1.0, 
        "heal_pct": 0.10, # Cura 10% do monstro ao atacar
        "magic": True,
        "log": "{mob} sugou sua energia vital para se curar!"
    },
    "toque_frio": {
        "name": "Toque da Morte", "chance": 0.25,
        "damage_mult": 1.5, "magic": True,
        "log": "A mão gélida de {mob} atravessa sua armadura, congelando sua alma!"
    },

    # --- 🔥 ELEMENTAL / MAGIA (Magos, Elementais) ---
    "bola_de_fogo_menor": {
        "name": "Bola de Fogo", "chance": 0.25,
        "damage_mult": 1.8, "magic": True,
        "log": "{mob} conjura uma esfera de chamas e a lança em você!"
    },
    "laminas_de_vento": {
        "name": "Lâminas de Vento", "chance": 0.20,
        "damage_mult": 1.4, "magic": True,
        "log": "O ar gira ao redor de {mob}, cortando você com lâminas invisíveis!"
    },
    "terremoto_local": {
        "name": "Tremor de Terra", "chance": 0.20,
        "damage_mult": 1.6, "magic": True,
        "log": "{mob} golpeia o chão, fazendo pedras voarem em sua direção!"
    },
    "raio_congelante": {
        "name": "Raio Congelante", "chance": 0.20,
        "damage_mult": 1.3, "magic": True,
        "log": "{mob} dispara um raio de gelo que enrijece seus músculos!"
    },

    # --- ❤️ CURA / SUPORTE (Xamãs, Druidas, Mobs Sagrados) ---
    "regeneracao_natural": {
        "name": "Regeneração", "chance": 0.15,
        "heal_pct": 0.20, # Cura 20%
        "log": "{mob} brilha com uma luz verde e suas feridas começam a fechar!"
    }
}

# ==============================================================================
# 🎄 SISTEMA DE EVENTO DE NATAL (INJEÇÃO AUTOMÁTICA) 🎄
# Coloque isso no FINAL do arquivo monsters.py
# ==============================================================================

ENABLE_CHRISTMAS_EVENT = True 

if ENABLE_CHRISTMAS_EVENT:
    print("🎅 HO HO HO! Injetando Presentes de Natal nos Monstros...")
    
    # Configuração dos Drops (Aumentei um pouco para teste)
    DROP_COMUM = {"item_id": "presente_perdido", "drop_chance": 40.0}  # A cada 4 monstros 1 cai
    DROP_RARO =  {"item_id": "presente_dourado", "drop_chance": 20.0}   # Difícil (Skins)

    count_updated = 0

    for region_key, monster_list in MONSTERS_DATA.items():
        # Pula listas que não são de monstros comuns (ex: bosses de evolução)
        if region_key.startswith("_"): 
            continue

        for monster in monster_list:
            # 1. Garante que existe uma lista de loot
            if "loot_table" not in monster:
                monster["loot_table"] = []
            
            # 2. Verifica quais itens esse monstro JÁ tem (para não duplicar)
            existing_ids = [item.get("item_id") for item in monster["loot_table"]]

            # 3. Adiciona Presente Perdido se não tiver
            if DROP_COMUM["item_id"] not in existing_ids:
                monster["loot_table"].append(DROP_COMUM.copy())
            
            # 4. Adiciona Presente Dourado se não tiver
            if DROP_RARO["item_id"] not in existing_ids:
                monster["loot_table"].append(DROP_RARO.copy())
            
            # 5. Bônus para Bosses (Garante drop e aumenta chance do raro)
            if monster.get("is_boss"):
                # Removemos a versão normal para por a versão 'turbinada' do boss
                monster["loot_table"] = [x for x in monster["loot_table"] 
                                       if x["item_id"] not in [DROP_COMUM["item_id"], DROP_RARO["item_id"]]]
                
                monster["loot_table"].append({"item_id": "presente_perdido", "drop_chance": 100.0})
                monster["loot_table"].append({"item_id": "presente_dourado", "drop_chance": 60.0})

            count_updated += 1

    print(f"🎅 Natal Ativo: {count_updated} monstros receberam presentes no bolso!")