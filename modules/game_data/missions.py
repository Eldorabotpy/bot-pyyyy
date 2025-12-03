# Ficheiro: modules/game_data/missions.py
# (VERSÃO FINAL: Sem missões de Craft/Refino para não travar profissões)

MISSION_CATALOG = [
    # --- Missões de Caça Genéricas (Por Região) ---
    {
        "id": "hunt_generic_forest",
        "title": "Limpeza Florestal",
        "description": "Derrote 5 monstros na Floresta Sombria.",
        "type": "HUNT",
        "target_region": "floresta_sombria",
        "target_count": 5,
        "rewards": {"xp": 100, "gold": 50, "prestige_points": 5}
    },
    {
        "id": "hunt_specific_swamp",
        "title": "Defesa da Pedreira",
        "description": "Derrote 8 criaturas na Pedreira Granito.",
        "type": "HUNT",
        "target_region": "pedreira_granito",
        "target_count": 8,
        "rewards": {"xp": 180, "gold": 120, "prestige_points": 9}
    },

    # --- Missões de Caça Específicas (Por ID do Monstro) ---
    {
        "id": "goblin_batedor_mission",
        "title": "Caça aos Goblins",
        "description": "Derrote 5 Goblins na Floresta Sombria.",
        "type": "HUNT",
        "target_region": "floresta_sombria",
        "target_id": "goblin_batedor",
        "target_count": 5,
        "rewards": {"xp": 100, "gold": 50, "prestige_points": 5}
    },
    # ===============================================================
    # = MISSÕES DE CAÇADA ESPECÍFICAS (FLORESTA SOMBRIA) =
    # ===============================================================
    {
        "id": "hunt_goblin_batedor_contract",
        "title": "Contrato: Goblins Batedores",
        "description": "Derrote 10 Goblin(s) Batedor(es) na região de Floresta Sombria.",
        "type": "HUNT",
        "target_count": 10,
        "target_region": "floresta_sombria",
        "target_id": "goblin_batedor",
        "rewards": {"xp": 60, "gold": 30, "prestige_points": 2}
    },
    {
        "id": "hunt_lobo_magro",
        "title": "Contrato: Lobos Magros",
        "description": "Derrote 12 Lobo(s) Magro(s) na região de Floresta Sombria.",
        "type": "HUNT",
        "target_count": 12,
        "target_region": "floresta_sombria",
        "target_id": "lobo_magro",
        "rewards": {"xp": 90, "gold": 90, "prestige_points": 2}
    },
    {
        "id": "hunt_cogumelo_gigante",
        "title": "Contrato: Cogumelos Gigantes",
        "description": "Derrote 10 Cogumelo(s) Gigante(s) na região de Floresta Sombria.",
        "type": "HUNT",
        "target_count": 10,
        "target_region": "floresta_sombria",
        "target_id": "cogumelo_gigante",
        "rewards": {"xp": 120, "gold": 45, "prestige_points": 4}
    },
    {
        "id": "hunt_javali_com_presas",
        "title": "Contrato: Javalis com Presas",
        "description": "Derrote 8 Javali(s) com Presas na região de Floresta Sombria.",
        "type": "HUNT",
        "target_count": 8,
        "target_region": "floresta_sombria",
        "target_id": "javali_com_presas",
        "rewards": {"xp": 120, "gold": 120, "prestige_points": 5}
    },
    {
        "id": "hunt_ent_jovem",
        "title": "Contrato: Ents Jovens",
        "description": "Derrote 8 Ent(s) Jovem(s) na região de Floresta Sombria.",
        "type": "HUNT",
        "target_count": 8,
        "target_region": "floresta_sombria",
        "target_id": "ent_jovem",
        "rewards": {"xp": 180, "gold": 144, "prestige_points": 7}
    },
    {
        "id": "hunt_espectro_do_bosque",
        "title": "Contrato: Espectros do Bosque",
        "description": "Derrote 8 Espectro(s) do Bosque na região de Floresta Sombria.",
        "type": "HUNT",
        "target_count": 8,
        "target_region": "floresta_sombria",
        "target_id": "espectro_do_bosque",
        "rewards": {"xp": 216, "gold": 168, "prestige_points": 9}
    },
    {
        "id": "hunt_xama_goblin",
        "title": "Contrato: Xamãs Goblins",
        "description": "Derrote 5 Xamã(s) Goblin(s) na região de Floresta Sombria.",
        "type": "HUNT",
        "target_count": 5,
        "target_region": "floresta_sombria",
        "target_id": "xama_goblin",
        "rewards": {"xp": 187, "gold": 150, "prestige_points": 12}
    },
    {
        "id": "hunt_lobo_alfa",
        "title": "Contrato: Lobo Alfa",
        "description": "Derrote 5 Lobo(s) Alfa na região de Floresta Sombria.",
        "type": "HUNT",
        "target_count": 5,
        "target_region": "floresta_sombria",
        "target_id": "lobo_alfa",
        "rewards": {"xp": 225, "gold": 225, "prestige_points": 15}
    },

    # ===============================================================
    # = MISSÕES DE CAÇADA ESPECÍFICAS (PEDREIRA GRANITO) =
    # ===============================================================
    {
        "id": "hunt_kobold_escavador",
        "title": "Contrato: Kobolds Escavadores",
        "description": "Derrote 8 Kobold(s) Escavador(es) na região de Pedreira Granito.",
        "type": "HUNT",
        "target_count": 8,
        "target_region": "pedreira_granito",
        "target_id": "kobold_escavador",
        "rewards": {"xp": 144, "gold": 144, "prestige_points": 6}
    },
    {
        "id": "hunt_tatu_de_rocha",
        "title": "Contrato: Tatus de Rocha",
        "description": "Derrote 5 Tatu(s) de Rocha na região de Pedreira Granito.",
        "type": "HUNT",
        "target_count": 5,
        "target_region": "pedreira_granito",
        "target_id": "tatu_de_rocha",
        "rewards": {"xp": 112, "gold": 67, "prestige_points": 7}
    },
    {
        "id": "hunt_golem_de_pedra_pequeno",
        "title": "Contrato: Golems de Pedra",
        "description": "Derrote 3 Golem(s) de Pedra Pequeno(s) na região de Pedreira Granito.",
        "type": "HUNT",
        "target_count": 3,
        "target_region": "pedreira_granito",
        "target_id": "golem_de_pedra_pequeno",
        "rewards": {"xp": 90, "gold": 49, "prestige_points": 10}
    },
    {
        "id": "hunt_salamandra_de_pedra",
        "title": "Contrato: Salamandras de Pedra",
        "description": "Derrote 3 Salamandra(s) de Pedra na região de Pedreira Granito.",
        "type": "HUNT",
        "target_count": 3,
        "target_region": "pedreira_granito",
        "target_id": "salamandra_de_pedra",
        "rewards": {"xp": 112, "gold": 36, "prestige_points": 12}
    },
    {
        "id": "hunt_gargula_de_vigia",
        "title": "Contrato: Gárgulas de Vigia",
        "description": "Derrote 3 Gárgula(s) de Vigia na região de Pedreira Granito.",
        "type": "HUNT",
        "target_count": 3,
        "target_region": "pedreira_granito",
        "target_id": "gargula_de_vigia",
        "rewards": {"xp": 126, "gold": 63, "prestige_points": 14}
    },
    {
        "id": "hunt_basilisco_jovem",
        "title": "Contrato: Basilisco Jovem",
        "description": "Derrote 3 Basilisco(s) Jovem(s) na região de Pedreira Granito.",
        "type": "HUNT",
        "target_count": 3,
        "target_region": "pedreira_granito",
        "target_id": "basilisco_jovem",
        "rewards": {"xp": 225, "gold": 225, "prestige_points": 25}
    },

    # ===============================================================
    # = MISSÕES DE CAÇADA ESPECÍFICAS (CAMPOS LINHO) =
    # ===============================================================
    {
        "id": "hunt_espantalho_vivo",
        "title": "Contrato: Espantalhos Vivos",
        "description": "Derrote 5 Espantalho(s) Vivo(s) na região de Campos Linho.",
        "type": "HUNT",
        "target_count": 5,
        "target_region": "campos_linho",
        "target_id": "espantalho_vivo",
        "rewards": {"xp": 150, "gold": 60, "prestige_points": 10}
    },
    {
        "id": "hunt_passaro_roc_gigante",
        "title": "Contrato: Pássaros Roc",
        "description": "Derrote 5 Pássaro(s) Roc Gigante(s) na região de Campos Linho.",
        "type": "HUNT",
        "target_count": 5,
        "target_region": "campos_linho",
        "target_id": "passaro_roc_gigante",
        "rewards": {"xp": 240, "gold": 120, "prestige_points": 16}
    },
    {
        "id": "hunt_verme_de_seda",
        "title": "Contrato: Vermes de Seda",
        "description": "Derrote 5 Verme(s) de Seda na região de Campos Linho.",
        "type": "HUNT",
        "target_count": 5,
        "target_region": "campos_linho",
        "target_id": "verme_de_seda",
        "rewards": {"xp": 180, "gold": 45, "prestige_points": 12}
    },
    {
        "id": "hunt_lobisomem_campones",
        "title": "Contrato: Lobisomens Camponeses",
        "description": "Derrote 3 Lobisomem(ns) Camponês(es) na região de Campos Linho.",
        "type": "HUNT",
        "target_count": 3,
        "target_region": "campos_linho",
        "target_id": "lobisomem_campones",
        "rewards": {"xp": 180, "gold": 99, "prestige_points": 20}
    },
    {
        "id": "hunt_gnomo_de_jardim_travesso",
        "title": "Contrato: Gnomos Travessos",
        "description": "Derrote 3 Gnomo(s) de Jardim Travesso(s) na região de Campos Linho.",
        "type": "HUNT",
        "target_count": 3,
        "target_region": "campos_linho",
        "target_id": "gnomo_de_jardim_travesso",
        "rewards": {"xp": 117, "gold": 81, "prestige_points": 13}
    },
    {
        "id": "hunt_banshee_dos_campos",
        "title": "Contrato: Banshees dos Campos",
        "description": "Derrote 3 Banshee(s) dos Campos na região de Campos Linho.",
        "type": "HUNT",
        "target_count": 3,
        "target_region": "campos_linho",
        "target_id": "banshee_dos_campos",
        "rewards": {"xp": 202, "gold": 90, "prestige_points": 22}
    }
]

# ------------------------------------------------------------------------

GUILD_MISSIONS_CATALOG = {
    "desafio_basiliscos": {
        "title": "Desafio do Dia: Basiliscos",
        "description": "Como um clã, derrotem 10 Basiliscos na Pedreira Granito.",
        "type": "HUNT",
        "target_monster_id": "basilisco_jovem",
        "target_count": 10,
        "duration_hours": 24,
        "rewards": {
            "guild_xp": 50,
            "gold_per_member": 1000,
        }
    },
    
    "contrato_goblins_guilda": {
        "title": "Contrato da Guilda: Goblins",
        "description": "Como um clã, derrotem 50 Goblins Batedores na Floresta Sombria.",
        "type": "HUNT",
        "target_monster_id": "goblin_batedor",
        "target_count": 50,
        "duration_hours": 48,
        "rewards": {
            "guild_xp": 100,
            "item_per_member": {
                "item_id": "joia_da_criacao",
                "quantity": 1
            }
        }
    },
    
    "guild_hunt_alfa_wolf": {
        "title": "Contrato: A Alcateia Alfa",
        "description": "Como um clã, derrotem 10 Lobos Alfa na Floresta Sombria.",
        "type": "HUNT",
        "target_monster_id": "lobo_alfa",
        "target_count": 10,
        "duration_hours": 24,
        "rewards": {
            "guild_xp": 200,
            "item_per_member": {
                "item_id": "fragmento_de_runa",
                "quantity": 1
            }
        }
    },

    "guild_hunt_basilisks": {
        "title": "Contrato: Ninho de Basiliscos",
        "description": "Como um clã, derrotem 20 Basiliscos Jovens na Pedreira Granito.",
        "type": "HUNT",
        "target_monster_id": "basilisco_jovem",
        "target_count": 20,
        "duration_hours": 48,
        "rewards": {
            "guild_xp": 250,
            "gold_per_member": 5000
        }
    },
    
    "guild_hunt_gargoyles": {
        "title": "Contrato: Vigias de Pedra",
        "description": "Como um clã, derrotem 25 Gárgulas de Vigia na Pedreira Granito.",
        "type": "HUNT",
        "target_monster_id": "gargula_de_vigia",
        "target_count": 25,
        "duration_hours": 48,
        "rewards": {
            "guild_xp": 180,
            "item_per_member": {
                "item_id": "fragmento_de_gargula",
                "quantity": 5
            }
        }
    },

    "guild_hunt_werewolves": {
        "title": "Contrato: A Maldição do Camponês",
        "description": "Como um clã, derrotem 15 Lobisomens Camponeses nos Campos de Linho.",
        "type": "HUNT",
        "target_monster_id": "lobisomem_campones",
        "target_count": 15,
        "duration_hours": 24,
        "rewards": {
            "guild_xp": 300,
            "gold_per_member": 6000
        }
    },
    
    "guild_hunt_elites_world": {
        "title": "Desafio dos Campeões da Guilda",
        "description": "Como um clã, derrotem 5 monstros de Elite em qualquer região do mundo.",
        "type": "HUNT_ELITE",
        "target_count": 5,
        "duration_hours": 72,
        "rewards": {
            "guild_xp": 500,
            "item_per_member": {
                "item_id": "bau_de_tesouro_epico",
                "quantity": 1
            }
        }
    }
}