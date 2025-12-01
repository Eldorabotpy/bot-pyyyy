# modules/game_data/guild_missions.py

GUILD_MISSIONS_CATALOG = {

    # =========================================================================
    # DIFICULDADE: FÁCIL (Easy)
    # Mapas: Pradaria Inicial, Floresta Sombria
    # =========================================================================

    # --- PRADARIA INICIAL ---
    "hunt_pradaria_slime_verde": {
        "difficulty": "easy",
        "title": "Limpeza Viscosa",
        "description": "Slimes Verdes estão se multiplicando rápido demais na entrada do reino.",
        "type": "HUNT",
        "target_monster_id": "slime_verde",
        "target_count": 25,
        "rewards": {"clan_xp": 20, "clan_gold": 100}
    },
    "hunt_pradaria_slime_magma": {
        "difficulty": "easy",
        "title": "Perigo de Incêndio",
        "description": "Slimes de Magma ameaçam queimar a grama seca da pradaria.",
        "type": "HUNT",
        "target_monster_id": "slime_magma",
        "target_count": 15,
        "rewards": {"clan_xp": 20, "clan_gold": 100}
    },
    "hunt_pradaria_slime_brilhante": {
        "difficulty": "easy",
        "title": "Caça ao Tesouro Vivo",
        "description": "Slimes Brilhantes foram avistados! Eles carregam materiais valiosos.",
        "type": "HUNT",
        "target_monster_id": "slime_brilhante",
        "target_count": 10,
        "rewards": {"clan_xp": 15, "clan_gold": 100}
    },

    # --- FLORESTA SOMBRIA ---
    "hunt_floresta_goblin": {
        "difficulty": "easy",
        "title": "Patrulha Goblin",
        "description": "Batedores Goblins estão espionando nossas rotas comerciais.",
        "type": "HUNT",
        "target_monster_id": "goblin_batedor",
        "target_count": 20,
        "rewards": {"clan_xp": 13, "clan_gold": 200}
    },
    "hunt_floresta_lobo": {
        "difficulty": "easy",
        "title": "Alcateia Faminta",
        "description": "Lobos Magros estão atacando viajantes na orla da floresta.",
        "type": "HUNT",
        "target_monster_id": "lobo_magro",
        "target_count": 15,
        "rewards": {"clan_xp": 13, "clan_gold": 200}
    },
    "hunt_floresta_ent": {
        "difficulty": "easy",
        "title": "A Fúria da Natureza",
        "description": "Ents Jovens, perturbados pela magia negra, estão atacando lenhadores.",
        "type": "HUNT",
        "target_monster_id": "ent_jovem",
        "target_count": 10,
        "rewards": {"clan_xp": 15, "clan_gold": 200}
    },

    # =========================================================================
    # DIFICULDADE: MÉDIA (Medium)
    # Mapas: Pedreira, Campos de Linho, Pico do Grifo
    # =========================================================================

    # --- PEDREIRA DE GRANITO ---
    "hunt_pedreira_kobold": {
        "difficulty": "medium",
        "title": "Ladrões de Minério",
        "description": "Expulse os Kobolds Escavadores que tomaram a mina norte.",
        "type": "HUNT",
        "target_monster_id": "kobold_escavador",
        "target_count": 30,
        "rewards": {"clan_xp": 100, "clan_gold": 200}
    },
    "hunt_pedreira_tatu": {
        "difficulty": "medium",
        "title": "Casca Dura",
        "description": "Tatus de Rocha estão bloqueando as estradas de transporte.",
        "type": "HUNT",
        "target_monster_id": "tatu_de_rocha",
        "target_count": 20,
        "rewards": {"clan_xp": 15, "clan_gold": 200}
    },
    "hunt_pedreira_basilisco": {
        "difficulty": "medium",
        "title": "Olhar Petrificante",
        "description": "Cuidado com os olhos! Elimine os Basiliscos Jovens.",
        "type": "HUNT",
        "target_monster_id": "basilisco_jovem",
        "target_count": 15,
        "rewards": {"clan_xp": 20, "clan_gold": 200}
    },

    # --- CAMPOS DE LINHO ---
    "hunt_campos_espantalho": {
        "difficulty": "medium",
        "title": "A Colheita Maldita",
        "description": "Os Espantalhos Vivos ganharam consciência e atacam fazendeiros.",
        "type": "HUNT",
        "target_monster_id": "espantalho_vivo",
        "target_count": 25,
        "rewards": {"clan_xp": 20, "clan_gold": 200}
    },
    "hunt_campos_lobisomem": {
        "difficulty": "medium",
        "title": "Noite de Lua Cheia",
        "description": "Lobisomens Camponeses aterrorizam as vilas próximas.",
        "type": "HUNT",
        "target_monster_id": "lobisomem_campones",
        "target_count": 15,
        "rewards": {"clan_xp": 20, "clan_gold": 200}
    },
    "hunt_campos_banshee": {
        "difficulty": "medium",
        "title": "O Grito da Morte",
        "description": "Silencie as Banshees dos Campos antes que enlouqueçam a população.",
        "type": "HUNT",
        "target_monster_id": "banshee_dos_campos",
        "target_count": 10,
        "rewards": {"clan_xp": 20, "clan_gold": 200}
    },

    # --- PICO DO GRIFO ---
    "hunt_pico_harpia": {
        "difficulty": "medium",
        "title": "Céus Hostis",
        "description": "Harpias Saqueadoras estão roubando suprimentos da guilda.",
        "type": "HUNT",
        "target_monster_id": "harpia_saqueadora",
        "target_count": 25,
        "rewards": {"clan_xp": 30, "clan_gold": 200}
    },
    "hunt_pico_grifo": {
        "difficulty": "medium",
        "title": "Controle Aéreo",
        "description": "Grifos Jovens estão muito agressivos nesta temporada.",
        "type": "HUNT",
        "target_monster_id": "grifo_jovem",
        "target_count": 20,
        "rewards": {"clan_xp": 20, "clan_gold": 200}
    },
    "hunt_pico_corvo": {
        "difficulty": "medium",
        "title": "Sombra Alada",
        "description": "Corvos Carniceiros Gigantes estão descendo das montanhas.",
        "type": "HUNT",
        "target_monster_id": "corvo_carniceiro_gigante",
        "target_count": 15,
        "rewards": {"clan_xp": 20, "clan_gold": 200}
    },

    # =========================================================================
    # DIFICULDADE: DIFÍCIL (Hard)
    # Mapas: Mina, Forja, Pântano, Picos Gelados, Deserto
    # =========================================================================

    # --- MINA DE FERRO ---
    "hunt_mina_morcego": {
        "difficulty": "hard",
        "title": "Ecos na Escuridão",
        "description": "Morcegos das Minas infestaram os túneis principais.",
        "type": "HUNT",
        "target_monster_id": "morcego_das_minas",
        "target_count": 40,
        "rewards": {"clan_xp": 50, "clan_gold": 400}
    },
    "hunt_mina_capataz": {
        "difficulty": "hard",
        "title": "Revolta Subterrânea",
        "description": "Elimine os Kobolds Capatazes que lideram a revolta.",
        "type": "HUNT",
        "target_monster_id": "kobold_capataz",
        "target_count": 20,
        "rewards": {"clan_xp": 50, "clan_gold": 400}
    },
    "hunt_mina_troll": {
        "difficulty": "hard",
        "title": "O Gigante da Caverna",
        "description": "Um grupo de Trolls da Caverna bloqueia a extração de ferro.",
        "type": "HUNT",
        "target_monster_id": "troll_da_caverna",
        "target_count": 10,
        "rewards": {"clan_xp": 50, "clan_gold": 400}
    },

    # --- FORJA ABANDONADA ---
    "hunt_forja_elemental": {
        "difficulty": "hard",
        "title": "Fogo Vivo",
        "description": "Elementais de Fogo escaparam das fornalhas antigas.",
        "type": "HUNT",
        "target_monster_id": "elemental_de_fogo",
        "target_count": 20,
        "rewards": {"clan_xp": 50, "clan_gold": 400}
    },
    "hunt_forja_salamandra": {
        "difficulty": "hard",
        "title": "Sangue de Magma",
        "description": "Salamandras de Fogo estão superaquecendo o local.",
        "type": "HUNT",
        "target_monster_id": "salamandra_de_fogo",
        "target_count": 15,
        "rewards": {"clan_xp": 50, "clan_gold": 400}
    },
    "hunt_forja_automato": {
        "difficulty": "hard",
        "title": "Máquinas Loucas",
        "description": "Autômatos com Defeito atacam qualquer intruso na forja.",
        "type": "HUNT",
        "target_monster_id": "automato_com_defeito",
        "target_count": 15,
        "rewards": {"clan_xp": 50, "clan_gold": 400}
    },

    # --- PÂNTANO MALDITO ---
    "hunt_pantano_carnical": {
        "difficulty": "hard",
        "title": "Fome Eterna",
        "description": "Carniçais Famintos rondam as águas turvas.",
        "type": "HUNT",
        "target_monster_id": "carnic_faminto",
        "target_count": 25,
        "rewards": {"clan_xp": 50, "clan_gold": 200}
    },
    "hunt_pantano_lodo": {
        "difficulty": "hard",
        "title": "Poluição Mágica",
        "description": "Destrua as Abominações de Lodo que envenenam o pântano.",
        "type": "HUNT",
        "target_monster_id": "abom_lodo",
        "target_count": 20,
        "rewards": {"clan_xp": 50, "clan_gold": 400}
    },
    "hunt_pantano_crocodilo": {
        "difficulty": "hard",
        "title": "Predador Apex",
        "description": "Crocodilos Mutantes gigantescos estão caçando nossos guerreiros.",
        "type": "HUNT",
        "target_monster_id": "crocodilo_mutante",
        "target_count": 10,
        "rewards": {"clan_xp": 50, "clan_gold": 400}
    },

    # --- PICOS GELADOS ---
    "hunt_picos_urso": {
        "difficulty": "hard",
        "title": "Fera da Neve",
        "description": "Ursos Polares Jovens bloquearam a passagem da montanha.",
        "type": "HUNT",
        "target_monster_id": "urso_polar_jovem",
        "target_count": 20,
        "rewards": {"clan_xp": 50, "clan_gold": 400}
    },
    "hunt_picos_golem": {
        "difficulty": "hard",
        "title": "Coração de Gelo",
        "description": "Golems de Gelo impedem o avanço para o cume.",
        "type": "HUNT",
        "target_monster_id": "golem_de_gelo",
        "target_count": 15,
        "rewards": {"clan_xp": 50, "clan_gold": 400}
    },
    "hunt_picos_gigante": {
        "difficulty": "hard",
        "title": "O Titã Congelado",
        "description": "Gigantes Congelados desceram das alturas para destruir.",
        "type": "HUNT",
        "target_monster_id": "gigante_congelado",
        "target_count": 8,
        "rewards": {"clan_xp": 50, "clan_gold": 400}
    },

    # --- DESERTO ANCESTRAL ---
    "hunt_deserto_escorpiao": {
        "difficulty": "hard",
        "title": "Veneno das Dunas",
        "description": "Escorpiões Venenosos gigantes cercaram o oásis.",
        "type": "HUNT",
        "target_monster_id": "escorp_venenoso",
        "target_count": 25,
        "rewards": {"clan_xp": 50, "clan_gold": 400}
    },
    "hunt_deserto_guardiao": {
        "difficulty": "hard",
        "title": "Tumba Profanada",
        "description": "Guardiões Mumificados despertaram para proteger as ruínas.",
        "type": "HUNT",
        "target_monster_id": "guardiao_mumificado",
        "target_count": 20,
        "rewards": {"clan_xp": 50, "clan_gold": 400}
    },
    "hunt_deserto_farao": {
        "difficulty": "hard",
        "title": "A Maldição do Rei",
        "description": "Faraós Malditos tentam reconstruir seu império sombrio.",
        "type": "HUNT",
        "target_monster_id": "farao_maldito",
        "target_count": 8,
        "rewards": {"clan_xp": 50, "clan_gold": 500}
    }
}