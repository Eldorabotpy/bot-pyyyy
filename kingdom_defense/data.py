# Em kingdom_defense/data.py

WAVE_DEFINITIONS = {
    # =================================================================
    # WAVE 1: 10 Mobs de Nível 0 (Tema: Goblins da Floresta)
    # =================================================================
    1: {
        "mobs": [
            {
                # Extraído de MONSTERS_DATA["floresta_sombria"][0]
                "name": "Goblin Batedor",
                "hp": 40,
                "attack": 5,
                "defense": 1,
                "initiative": 8,
                "luck": 5,
                "reward": 5,  # Recompensa em 'fragmento_bravura' (ou item do evento)
                "media_key": "goblin_batedor_media" 
            },
        ],
        "mob_count": 10,
        "boss": {
            "name": "Xamã Goblin",
            "hp": 550, # HP aumentado para o evento
            "attack": 18, # Atributos aumentados para o evento
            "defense": 8,
            "initiative": 7,
            "luck": 6,
            "reward": 50,
            "media_key": "xama_goblin_media"
        },
    },
    # =================================================================
    # WAVE 2: 15 Mobs de Nível 3 (Tema: Criaturas da Pedreira)
    # =================================================================
    2: {
        "mobs": [
            {
                # Extraído de MONSTERS_DATA["pedreira_granito"][0]
                "name": "Kobold Escavador",
                "hp": 125,
                "attack": 18,
                "defense": 24,
                "initiative": 15,
                "luck": 15,
                "reward": 10,
                "media_key": "kobold_escavador_media"
            },
        ],
        "mob_count": 15,
        "boss": {
            # Extraído de MONSTERS_DATA["pedreira_granito"][2]
            "name": "Golem de Pedra", # Nome adaptado
            "hp": 3200, # HP aumentado para o evento
            "attack": 50, # Atributos aumentados para o evento
            "defense": 45,
            "initiative": 10,
            "luck": 2,
            "reward": 100,
            "media_key": "golem_pedra_pequeno_media"
        },
    },
    # =================================================================
    # WAVE 3: 20 Mobs de Nível 6 (Tema: Horrores das Minas)
    # =================================================================
    3: {
        "mobs": [
            {
                # Extraído de MONSTERS_DATA["mina_ferro"][0]
                "name": "Morcego das Minas",
                "hp": 258,
                "attack": 27,
                "defense": 28,
                "initiative": 38,
                "luck": 19,
                "reward": 20,
                "media_key": "morcego_minas_media"
            },
        ],
        "mob_count": 20,
        "boss": {
            # Extraído de MONSTERS_DATA["mina_ferro"][3]
            "name": "Troll da Caverna Ancião", # Nome adaptado
            "hp": 7000, # HP aumentado para o evento
            "attack": 90, # Atributos aumentados para o evento
            "defense": 65,
            "initiative": 27,
            "luck": 25,
            "reward": 250,
            "media_key": "troll_caverna_media"
        },
    },
    # =================================================================
    # WAVE 4: 25 Mobs de Nível 9 (Tema: Guardiões da Forja)
    # =================================================================
    4: {
        "mobs": [
            {
                # Extraído de MONSTERS_DATA["forja_abandonada"][0]
                "name": "Golem de Ferro Incompleto",
                "hp": 495,
                "attack": 32,
                "defense": 44,
                "initiative": 28,
                "luck": 16,
                "reward": 35,
                "media_key": "golem_ferro_incompleto_media"
            },
        ],
        "mob_count": 25,
        "boss": {
            # Extraído de MONSTERS_DATA["catacumba_reino"][5]
            "name": "Rei Lagarto Soberano", # Nome adaptado
            "hp": 12500, # HP aumentado para o evento
            "attack": 150, # Atributos aumentados para o evento
            "defense": 100,
            "initiative": 14,
            "luck": 10,
            "reward": 500,
            "media_key": "rei_lagarto_media"
        },
        # =================================================================
    # WAVE 5: 30 Mobs de Nível 12 (Tema: Guardiões da Forja)
    # =================================================================
    4: {
        "mobs": [
            {
                # Extraído de MONSTERS_DATA["forja_abandonada"][0]
                "name": "Golem de Ferro Incompleto",
                "hp": 495,
                "attack": 32,
                "defense": 44,
                "initiative": 28,
                "luck": 16,
                "reward": 35,
                "media_key": "golem_ferro_incompleto_media"
            },
        ],
        "mob_count": 30,
        "boss": {
            # Extraído de MONSTERS_DATA["catacumba_reino"][5]
            "name": "Rei Lagarto Soberano", # Nome adaptado
            "hp": 12500, # HP aumentado para o evento
            "attack": 150, # Atributos aumentados para o evento
            "defense": 100,
            "initiative": 14,
            "luck": 10,
            "reward": 500,
            "media_key": "rei_lagarto_media"
        },
    },
    # =================================================================
    # WAVE 4: 25 Mobs de Nível 9 (Tema: Guardiões da Forja)
    # =================================================================
    4: {
        "mobs": [
            {
                # Extraído de MONSTERS_DATA["forja_abandonada"][0]
                "name": "Golem de Ferro Incompleto",
                "hp": 495,
                "attack": 32,
                "defense": 44,
                "initiative": 28,
                "luck": 16,
                "reward": 35,
                "media_key": "golem_ferro_incompleto_media"
            },
        ],
        "mob_count": 35,
        "boss": {
            # Extraído de MONSTERS_DATA["catacumba_reino"][5]
            "name": "Rei Lagarto Soberano", # Nome adaptado
            "hp": 12500, # HP aumentado para o evento
            "attack": 150, # Atributos aumentados para o evento
            "defense": 100,
            "initiative": 14,
            "luck": 10,
            "reward": 500,
            "media_key": "rei_lagarto_media"
        },# =================================================================
    # WAVE 4: 25 Mobs de Nível 9 (Tema: Guardiões da Forja)
    # =================================================================
    4: {
        "mobs": [
            {
                # Extraído de MONSTERS_DATA["forja_abandonada"][0]
                "name": "Golem de Ferro Incompleto",
                "hp": 495,
                "attack": 32,
                "defense": 44,
                "initiative": 28,
                "luck": 16,
                "reward": 35,
                "media_key": "golem_ferro_incompleto_media"
            },
        ],
        "mob_count": 40,
        "boss": {
            # Extraído de MONSTERS_DATA["catacumba_reino"][5]
            "name": "Rei Lagarto Soberano", # Nome adaptado
            "hp": 12500, # HP aumentado para o evento
            "attack": 150, # Atributos aumentados para o evento
            "defense": 100,
            "initiative": 14,
            "luck": 10,
            "reward": 500,
            "media_key": "rei_lagarto_media"
        },
     },
   },
 }
}