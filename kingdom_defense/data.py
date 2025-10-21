# Em kingdom_defense/data.py

# Em kingdom_defense/data.py (VERSÃO "BARALHO DE MONSTROS")

WAVE_DEFINITIONS = {
    # --- ONDA 1 (Total: 9 Mobs + 1 Chefe) ---
    1: {
        'display_name': "Onda 1",
        # Define exatamente quais e quantos monstros compõem a onda
        'mob_pool': [
            'ond1_pequeno_slime', 'ond1_slime_verde', 'ond1_slime_azul',
            'ond1_slime_magma', 'ond1_slime_terra',                     
            'ond1_slime_venenoso', 'ond1_slime_eletrico', 'ond1_slime_brilhante',   
            'ond1_slime_escuridao',                                     
        ],
        'boss_id': 'ond1_rei_slime'
    },
    # --- ONDA 2 (Total: 14 Mobs + 1 Chefe) ---
    2: {
        'display_name': "Onda 2",
        'mob_pool': [
            'onda2_soldado_esqueletico', 'onda2_lacaio_reanimado', 
            'onda2_arqueiro_esqueletico', 'onda2_bruto_reanimado',
            'onda2_mago_esqueletico', 'onda2_espadachim_ossudo', 
            'onda2_legionario_caido', 'onda2_lobo_esqueletico',
            'onda2_esqueleto_amaldicoado', 'onda2_soldado_esqueletico',                
            'onda2_legionario_caido', 'onda2_espadachim_ossudo',
            'onda2_mago_esqueletico', 'onda2_lobo_esqueletico',         # 2x
        ],
        'boss_id': 'onda2_campeao_do_sepulcro'
    },
    3: {
        'display_name': "Onda 3",
        'mob_pool': [
            'onda3_goblin_catador', 'onda3_goblin_fura_pe', 
            'onda3_atirador_goblin', 'onda3_brutamontes_goblin',
            'onda3_goblin_ardilheiro', 'onda3_goblin_xama', 
            'onda3_montador_de_lobo', 'onda3_goblin_bombardeiro',
            'onda3_chefe_goblin', 'onda3_goblin_fura_pe',                
            'onda3_goblin_catador', 'onda3_atirador_goblin',
            'onda3_goblin_ardilheiro', 'onda3_brutamontes_goblin',
            'onda3_montador_de_lobo', 'onda3_goblin_xama',
            'onda3_chefe_goblin', 'onda3_atirador_goblin',
            'onda3_goblin_bombardeiro', 'onda3_goblin_bombardeiro',
        ],
        'boss_id': 'onda3_rei_goblin'
    },
    4: {
        'display_name': "Onda 4",
        'mob_pool': [
            'onda4_mineiro_kobold', 'onda4_lanceiro_kobold', 
            'onda4_atirador_de_dardo', 'onda4_batedor_draconiano',
            'onda4_armadilheiro_kobold', 'onda4_geomante_kobold', 
            'onda4_guarda_da_ninhada', 'onda4_guerreiro_escamadura',
            'onda4_porta_estandarte_kobold', 'onda4_mineiro_kobold',                
            'onda4_atirador_de_dardo', 'onda4_lanceiro_kobold',
            'onda4_armadilheiro_kobold', 'onda4_geomante_kobold',
            'onda4_porta_estandarte_kobold', 'onda4_guerreiro_escamadura',
            'onda4_atirador_de_dardo', 'onda4_lanceiro_kobold',
            'onda4_porta_estandarte_kobold', 'onda4_geomante_kobold',
            'onda4_armadilheiro_kobold', 'onda4_geomante_kobold', 
            'onda4_guarda_da_ninhada', 'onda4_guerreiro_escamadura',
            'onda4_porta_estandarte_kobold',
        ],
        'boss_id': 'onda4_prole_de_dragao'
    },
    
    # Adiciona a Onda 3, 4, etc. aqui...
}

SCORE_PER_WAVE = { 1: 10, 2: 15, 3:20, 4:25, } # Ajusta como quiseres



