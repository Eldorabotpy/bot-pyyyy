# modules/game_data/refining.py

REFINING_RECIPES = {
    # ======================
    # Couros e derivados
    # ======================
    #
    "ref_couro_curtido_rapido": {
        "display_name": " Curtição de Couro (Rápida)",
        "profession": ["curtidor", "ferreiro", "armeiro",],
        "level_req": 1,
        "time_seconds": 1 * 60,
        "inputs": {"couro_de_lobo": 2},
        "outputs": {"couro_curtido": 1},
        "xp_gain": 5
    },

    "ref_couro_reforcado": {
        "display_name": " Curtimento de Couro Reforçado",
        "profession": ["curtidor"],
        "level_req": 5,
        "time_seconds": 15 * 60,
        "inputs": {"couro_de_lobo_alfa": 1, "seiva_de_ent": 2},
        "outputs": {"couro_reforcado": 1},
        "xp_gain": 20
    },
    "ref_pele_troll_tratada": {
        "display_name": " Tratamento de Pele de Troll",
        "profession": ["curtidor"],
        "level_req": 10,
        "time_seconds": 30 * 60,
        "inputs": {"pele_de_troll": 1, "sangue_regenerativo": 1},
        "outputs": {"pele_troll_regenerativa": 1},
        "xp_gain": 50
    },
    "ref_membrana_fina": {
        "display_name": "Secagem de Asa de Morcego",
        "profession": ["curtidor"],
        "level_req": 8,
        "time_seconds": 10 * 60,
        "inputs": {"asa_de_morcego": 5},
        "outputs": {"membrana_de_couro_fino": 1},
        "xp_gain": 12
    },
    
    "ref_afiar_presas": {
        "display_name": "Afiação de Presas",
        "profession": ["curtidor"],
        "level_req": 5,
        "time_seconds": 8 * 60, # 8 minutos
        "inputs": {"presa_de_javali": 2, "pedra": 1}, # Usa pedra como lixa/amolação
        "outputs": {"dente_afiado": 1},
        "xp_gain": 15
    },

    "ref_dente_superior": {
        "display_name": " Polimento de Dente Superior",
        "profession": ["curtidor"],
        "level_req": 18,
        "time_seconds": 20 * 60, # 20 minutos
        "inputs": {"dente_afiado": 3, "oleo_mineral": 1}, # Requer o óleo que adicionamos no items.py
        "outputs": {"dente_afiado_superior": 1},
        "xp_gain": 45
    },

    # ======================
    # Joalheria / Lapidação
    # ======================
    "ref_gema_polida": {
        "display_name": " Gema Polida",
        "profession": ["joalheiro", ],
        "level_req": 10,
        "time_seconds": 25 * 60,
        "inputs": {"gema_bruta": 3, "fragmento_gargula": 3},
        "outputs": {"gema_polida": 1},
        "xp_gain": 40 
    },
    "ref_ponta_afiada": {
        "display_name": " Polimento de Presa",
        "profession": ["joalheiro", ],
        "level_req": 5,
        "time_seconds": 8 * 60,
        "inputs": {"presa_de_javali": 2},
        "outputs": {"ponta_de_osso_afiada": 1},
        "xp_gain": 8
    },
    "ref_lente_petrificante": {
        "display_name": " Cristalização de Olho de Basilisco",
        "profession": ["joalheiro", ],
        "level_req": 25,
        "time_seconds": 60 * 60,  # 1h
        "inputs": {"olho_de_basilisco": 1, "gema_bruta": 5},
        "outputs": {"lente_petrificante": 1},
        "xp_gain": 100
    },

    # ======================
    # Metalurgia / Mineralogia
    # ======================
    "ref_bronze": {
        "display_name": "Liga de Bronze",
        "profession": ["fundidor", "ferreiro", "armeiro"],
        "level_req": 1,
        "time_seconds": 8 * 60,
        "inputs": {"minerio_de_ferro": 1, "minerio_de_estanho": 1},
        "outputs": {"barra_bronze": 1},
        "xp_gain": 3
    },
    "ref_placa_de_pedra": {
        "display_name": "Polimento de Carapaça",
        "profession": ["fundidor", "ferreiro", "armeiro", ],
        "level_req": 18,
        "time_seconds": 22 * 60,
        "inputs": {"carapaca_de_pedra": 2},  # corrigido (sem emoji no id)
        "outputs": {"placa_de_pedra_polida": 1},
        "xp_gain": 35
    },
    "ref_nucleo_energia": {
        "display_name": " Ativação de Núcleo de Golem",
        "profession": ["fundidor", "ferreiro", "armeiro", ],        "level_req": 22,
        "time_seconds": 40 * 60,
        "inputs": {"nucleo_de_golem": 1, "pedra_vulcanica": 10},
        "outputs": {"nucleo_de_energia_instavel": 1},
        "xp_gain": 70
    },
    "ref_placa_draconica": {
        "display_name": " Forja de Escama de Dragão",
        "profession": ["fundidor", "ferreiro", "armeiro", ],        "level_req": 30,
        "time_seconds": 120 * 60,  # 2h
        "inputs": {"escama_de_dragao": 1, "coracao_de_magma": 1},
        "outputs": {"placa_draconica_negra": 1},
        "xp_gain": 250
    },

    # ======================
    # Alquimia / Essências
    # ======================
    "ref_essencia_espiritual": {
        "display_name": " Condensação de Ectoplasma",
        "profession": ["curtidor", "ferreiro", "armeiro", "alfaiate", "joalheiro", "fundidor"],
        "level_req": 13,
        "time_seconds": 18 * 60,
        "inputs": {"ectoplasma": 5},
        "outputs": {"essencia_espiritual": 1},
        "xp_gain": 25
    },
    "ref_essencia_fungica": {
        "display_name": " Cultivo de Esporos",
        "profession": ["curtidor", "ferreiro", "armeiro", "alfaiate", "joalheiro", "fundidor"],
        "level_req": 3,
        "time_seconds": 12 * 60,
        "inputs": {"esporo_de_cogumelo": 10},
        "outputs": {"essencia_fungica": 1},
        "xp_gain": 10
    },
    "ref_essencia_draconica_pura": {
        "display_name": " Purificação de Coração de Dragão",
        "profession": ["curtidor", "ferreiro", "armeiro", "alfaiate", "joalheiro", "fundidor"],
        "level_req": 30,
        "time_seconds": 18 * 60,
        "inputs": {"coracao_de_dragao": 1, "sangue_regenerativo": 10},
        "outputs": {"essencia_draconica_pura": 1},
        "xp_gain": 50
    },

    # ======================
    # Tecelagem / Madeira
    # ======================
        "ref_pano_simples": {
        "display_name": "Tecelagem de Pano Simples",
        "profession": ["alfaiate"],
        "level_req": 1,
        "time_seconds": 3 * 60,
        "inputs": {"linho": 2},
        "outputs": {"pano_simples": 1},
        "xp_gain": 5
    },

    "ref_rolo_pano": {
        "display_name": " Tecelagem de Pano",
        "profession": ["alfaiate", ],
        "level_req": 2,
        "time_seconds": 6 * 60,
        "inputs": {"pano_simples": 4},
        "outputs": {"rolo_de_pano_simples": 1},
        "xp_gain": 6
    },
    "ref_tabua_de_madeira_rara": {
        "display_name": " Serragem de Madeira Rara",
        "profession": ["curtidor", "ferreiro", "armeiro", "alfaiate", "joalheiro", "fundidor"],
        "level_req": 9,
        "time_seconds": 14 * 60,
        "inputs": {"madeira_rara": 3, "seiva_de_ent": 1},
        "outputs": {"tabua_de_madeira_rara": 1},
        "xp_gain": 18
    },
    "ref_barra_de_ferro": {
        "display_name": "Fundição de Ferro",
        "profession": ["ferreiro", "armeiro", "fundidor"],
        "level_req": 1,
        "time_seconds": 6 * 60,
        "inputs": {"minerio_de_ferro": 2}, 
        "outputs": {"barra_de_ferro": 1},
        "xp_gain": 3,
        "emoji": "⛏️",
    },

    
    # --- METALURGIA (Ferreiro / Fundidor / Joalheiro) ---
    #V
    "ref_aco_temperado": {
        "display_name": "Fundição de Aço",
        "profession": ["ferreiro", "armeiro", "fundidor"],
        "level_req": 12,
        "time_seconds": 15 * 60,
        "inputs": {"barra_de_ferro": 2, "carvao": 2},
        "outputs": {"barra_de_aco": 1},
        "xp_gain": 25
    },
    "ref_prata_pura": {
        "display_name": " Fundição de Prata",
        "profession": ["ferreiro", "armeiro", "fundidor"],
        "level_req": 10,
        "time_seconds": 12 * 60,
        "inputs": {"minerio_de_prata": 2},
        "outputs": {"barra_de_prata": 1},
        "xp_gain": 20
    },
    "ref_fio_de_prata": {
        "display_name": "Fio de Prata",
        "profession": ["ferreiro", "armeiro", "joalheiro", "fundidor"],
        "level_req": 11,
        "time_seconds": 10 * 60,
        "inputs": {"barra_de_prata": 1},
        "outputs": {"fio_de_prata": 2},
        "xp_gain": 15
    }, 

    # --- ALFAIATARIA (Tecidos Avançados) ---
    "ref_veludo_runico": {
        "display_name": " Tecelagem de Veludo Rúnico",
        "profession": ["alfaiate"],
        "level_req": 15,
        "time_seconds": 20 * 60,
        "inputs": {"rolo_de_pano_simples": 3, "poeira_magica": 1},
        "outputs": {"veludo_runico": 1},
        "xp_gain": 30
    },
    "ref_seda_sombria": {
        "display_name": " Tecelagem de Seda Sombria",
        "profession": ["alfaiate"],
        "level_req": 18,
        "time_seconds": 25 * 60,
        "inputs": {"teia_de_aranha_gigante": 4, "essencia_sombra": 1},
        "outputs": {"rolo_seda_sombria": 1},
        "xp_gain": 40
    },

    # --- CURTUME (Couros Especiais) ---
    "ref_couro_escamoso": {
        "display_name": "Tratamento de Couro Escamoso",
        "profession": ["curtidor"],
        "level_req": 14,
        "time_seconds": 18 * 60,
        "inputs": {"pele_de_lagarto": 3, "oleo_mineral": 1},
        "outputs": {"couro_escamoso": 1},
        "xp_gain": 35
    },
    # Receita alternativa para Couro Reforçado (mais acessível que a de Lobo Alfa)
    "ref_couro_reforcado_comum": {
        "display_name": "Couro Reforçado (Básico)",
        "profession": ["curtidor"],
        "level_req": 12,
        "time_seconds": 20 * 60,
        "inputs": {"couro_curtido": 3, "cera_de_abelha": 1},
        "outputs": {"couro_reforcado": 1},
        "xp_gain": 25
    },

    # --- CARPINTARIA (Madeiras Mágicas) ---
    "ref_tabua_ancestral": {
        "display_name": "Corte de Tábua Ancestral",
        "profession": ["curtidor", "ferreiro", "armeiro", "alfaiate", "joalheiro", "fundidor"],
        "level_req": 20,
        "time_seconds": 30 * 60,
        "inputs": {"tronco_antigo": 2, "oleo_mineral": 1},
        "outputs": {"tabua_ancestral": 1},
        "xp_gain": 50
    },
    "ref_tabua_carvalho": {
        "display_name": "Tábua de Carvalho",
        "profession": ["curtidor", "ferreiro", "armeiro"], # Profissões que usam madeira
        "level_req": 5,
        "time_seconds": 10 * 60,
        "inputs": {"madeira_de_carvalho": 2}, # Você já tem esse item no items.py
        "outputs": {"tabua_de_carvalho": 1},  # Novo item refinado
        "xp_gain": 12
    },
    "ref_tabua_mogno": {
        "display_name": "Tábua de Mogno",
        "profession": ["curtidor", "ferreiro", "armeiro"],
        "level_req": 15,
        "time_seconds": 25 * 60,
        "inputs": {"madeira_mogno": 2, "oleo_mineral": 1},
        "outputs": {"tabua_de_mogno": 1},
        "xp_gain": 35
    },

    # --- METAIS (Adicionais) ---
    # Você já tem Bronze, Ferro, Aço e Prata. Vamos adicionar Ouro se for usar.
    "ref_barra_ouro": {
        "display_name": "Fundição de Ouro",
        "profession": ["fundidor", "joalheiro", "ferreiro"],
        "level_req": 20,
        "time_seconds": 30 * 60,
        "inputs": {"minerio_de_ouro": 4, "carvao": 4},
        "outputs": {"barra_de_ouro": 1},
        "xp_gain": 60
    },

    # --- TECIDOS (Amarras) ---
    # Você já tem Rolo de Pano e Seda. Vamos adicionar Corda Resistente.
    "ref_corda_linho": {
        "display_name": "Corda de Linho",
        "profession": ["alfaiate", "curtidor"],
        "level_req": 3,
        "time_seconds": 5 * 60,
        "inputs": {"linho": 4, "fibra_vegetal": 2},
        "outputs": {"corda_de_linho": 1},
        "xp_gain": 8
    },

        # --- METAIS RAROS (MITHRIL / ADAMANTIO) ---

    "ref_barra_de_mithril": {
        "display_name": "Fundição de Mithril",
        "profession": ["fundidor", "ferreiro", "armeiro"],
        "level_req": 45,
        "time_seconds": 60 * 60,  # 1h
        "inputs": {
            "minerio_de_mithril": 4,
            "carvao": 3
        },
        "outputs": {
            "barra_de_mithril": 1
        },
        "xp_gain": 120
    },

    "ref_barra_de_adamantio": {
        "display_name": "Fundição de Adamantio",
        "profession": ["fundidor", "ferreiro", "armeiro"],
        "level_req": 70,
        "time_seconds": 120 * 60,  # 2h
        "inputs": {
            "minerio_de_adamantio": 5,
            "carvao": 5
        },
        "outputs": {
            "barra_de_adamantio": 1
        },
        "xp_gain": 220
    },

}