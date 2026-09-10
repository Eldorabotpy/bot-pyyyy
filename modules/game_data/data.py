# ==========================================
# ARQUIVO: data.py
# DEFINIÇÕES DAS ONDAS DE INVASÃO DO MAPA
# ==========================================

WAVE_DEFINITIONS = {
    # 🟢 ONDA 1: A Invasão Gosmenta
    1: {
        "boss_id": "ond1_rei_slime",
        "mob_pool": [
            "ond1_pequeno_slime", "ond1_slime_verde", "ond1_slime_azul", 
            "ond1_slime_magma", "ond1_slime_terra", "ond1_slime_venenoso", 
            "ond1_slime_eletrico", "ond1_slime_brilhante", "ond1_slime_escuridao"
        ],
        "special_attack": {
            "name": "Esmagamento Real",
            "damage_multiplier": 2.5,
            "log_text": "O Rei Slime se infla e salta, caindo com um impacto esmagador!"
        }
    },
    
    # 💀 ONDA 2: O Despertar do Sepulcro
    2: {
        "boss_id": "onda2_campeao_do_sepulcro",
        "mob_pool": [
            "onda2_soldado_esqueletico", "onda2_lacaio_reanimado", "onda2_arqueiro_esqueletico",
            "onda2_bruto_reanimado", "onda2_mago_esqueletico", "onda2_espadachim_ossudo",
            "onda2_legionario_caido", "onda2_lobo_esqueletico", "onda2_esqueleto_amaldicoado"
        ],
        "special_attack": {
            "name": "Golpe Sepulcral",
            "damage_multiplier": 3.0,
            "log_text": "O Campeão do Sepulcro ergue sua lâmina antiga, que brilha com uma energia fantasmagórica antes de desferir um golpe devastador!"
        }
    },
    
    # 👺 ONDA 3: A Horda Goblin
    3: {
        "boss_id": "onda3_rei_goblin",
        "mob_pool": [
            "onda3_goblin_catador", "onda3_goblin_fura_pe", "onda3_atirador_goblin",
            "onda3_brutamontes_goblin", "onda3_goblin_xama", "onda3_goblin_ardilheiro",
            "onda3_montador_de_lobo", "onda3_goblin_bombardeiro", "onda3_chefe_goblin"
        ],
        "special_attack": {
            "name": "Chamado da Horda!",
            "damage_multiplier": 3.5,
            "log_text": "O Rei Goblin aponta seu cetro e solta um grito de guerra estridente! Em resposta, uma onda de ataques de todos os lados chove sobre você!"
        }
    },
    
    # 🐉 ONDA 4: A Fúria Dracónica
    4: {
        "boss_id": "onda4_prole_de_dragao",
        "mob_pool": [
            "onda4_mineiro_kobold", "onda4_lanceiro_kobold", "onda4_atirador_de_dardo",
            "onda4_batedor_draconiano", "onda4_armadilheiro_kobold", "onda4_geomante_kobold",
            "onda4_guarda_da_ninhada", "onda4_guerreiro_escamadura", "onda4_porta_estandarte_kobold"
        ],
        "special_attack": {
            "name": "Sopro Dracônico",
            "damage_multiplier": 4.0,
            "log_text": "A Prole de Dragão inspira profundamente, e de suas mandíbulas irrompe uma torrente de fogo que engole tudo ao seu redor!"
        }
    }
}