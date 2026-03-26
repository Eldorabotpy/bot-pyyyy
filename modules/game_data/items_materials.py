# modules/game_data/items_materials.py

MATERIALS_DATA = {
    # --- MINÉRIO E PEDRAS ---
    "minerio_de_cobre": {
        "display_name": "Minério de Cobre", "emoji": "⛓️🟠",
        "type": "material_bruto", "category": "coletavel",
        "description": "Metal condutor básico.", 
        "stackable": True,
        "media_key": "imagem_minerio_de_cpbre",
    },
    "minerio_de_ouro": {
        "display_name": "Minério de Ouro", "emoji": "⛓️🟡",
        "type": "material_bruto", "category": "coletavel",
        "description": "Metal precioso e brilhante.", 
        "stackable": True,
        "media_key": "imagem_minerio_de_ouro",
    },
    "minerio_de_ferro": {
        "display_name": "Minério de Ferro", "emoji": "⛓️⚫️",
        "type": "material_bruto", "category": "coletavel",
        "description": "Minério metálico que pode ser fundido.",
        "stackable": True, 
        "media_key": "imagem_minerio_de_ferro",
        "icon_url": "https://github.com/user-attachments/assets/05750a8a-6804-47f6-b6fe-beddcaa20dff",
    },
    "minerio_de_estanho": {
        "display_name": "Minério de Estanho", "emoji": "⛓️⚪️",
        "type": "material_bruto", "category": "cacada",
        "description": "Metal macio, excelente para ligas.",
        "stackable": True, 
        "media_key": "item_minerio_de_stanho"
    },
    "minerio_de_prata": {
        "display_name": "Minério de Prata", "emoji": "⛓️🔘",
        "type": "material_bruto", "category": "coletavel",
        "description": "Minério metálico que pode ser fundido.",
        "stackable": True, "media_key": "imagem_minerio_de_prata",
    },
    "carvao": {
        "display_name": "Carvão Mineral", "emoji": "⚫",
        "type": "material_bruto", "category": "coletavel",
        "description": "Combustível essencial para forjas.", 
        "stackable": True,
        "media_key": "imagem_carvao",
    },
    "cristal_bruto": {
        "display_name": "Cristal Bruto", "emoji": "💎",
        "type": "material_bruto", "category": "coletavel",
        "description": "Cristal com potencial mágico não lapidado.", 
        "stackable": True,
        "media_key": "imagem_cristal_bruto",
    },
    "pedra": {
        "display_name": "Pedra", "emoji": "🪨", 
        "type": "material_bruto", "category": "coletavel", 
        "stackable": True, 
        "media_key": "item_pedra",
    },
    # --- MADEIRAS E PLANTAS ---
    "madeira": {
        "display_name": "Madeira", "emoji": "🪵", 
        "type": "material_bruto", "category": "coletavel", 
        "stackable": True, 
        "media_key": "item_madeira",
    },
    "madeira_de_carvalho": {
        "display_name": "Tora de Carvalho", "emoji": "🪵🟤",
        "type": "material_bruto", "category": "coletavel",
        "description": "Madeira dura e resistente.", 
        "stackable": True,
        "media_key": "imagem_madeira_de_carvalho",
    },
    "madeira_rara": {
        "display_name": "Madeira Rara", "emoji": "🪵☦️",
        "type": "material_bruto", "category": "cacada",
        "description": "Madeira de árvore antiga, resistente.",
        "stackable": True, 
        "media_key": "item_madeira_rara",
    },
    "casca_rigida": {
        "display_name": "Casca Rígida", "emoji": "🛡️",
        "type": "material_bruto", "category": "coletavel",
        "description": "Casca de árvore grossa para curtição.", 
        "stackable": True,
        "media_key": "imagem_minerio_de_ferro",
    },
    "raiz_sangrenta": {
        "display_name": "Raiz Sangrenta", "emoji": "🥕",
        "type": "reagent", "category": "coletavel",
        "description": "Raiz vermelha para poções.", 
        "stackable": True,
        "media_key": "imagem_minerio_de_ferro",
    },
    "linho": {
        "display_name": "Linho", "emoji": "🌿",
        "type": "material_bruto", "category": "coletavel",
        "description": "Fibras vegetais base para tecelagem.",
        "stackable": True, 
        "media_key": "imagem_linho",
    },
    "flor_da_lua": {
        "display_name": "Flor da Lua", "emoji": "🌷",
        "type": "reagent", "category": "coletavel",
        "description": "Brilha levemente à noite.", 
        "stackable": True,
        "media_key": "imagem_flor_da_lua",
    },
    "cogumelo_azul": {
        "display_name": "Cogumelo Azul", "emoji": "🍄🟦",
        "type": "reagent", "category": "coletavel",
        "description": "Fungo raro.", "stackable": True,
        "media_key": "imagem_cogumelo_azul",
    },
    # --- DROPS DE MONSTROS ---
    "pena": {
        "display_name": "Pena", "emoji": "🪶",
        "type": "material_monstro", "category": "coletavel",
        "description": "Pena leve.", 
        "stackable": True, 
        "media_key": "imagem_pena",
    },
    "sangue": {
        "display_name": "Sangue", "emoji": "🩸",
        "type": "material_monstro", "category": "coletavel",
        "description": "Amostra de sangue.", 
        "stackable": True, 
        "media_key": "imagem_sangue",
    },
    "pano_simples": {
        "display_name": "Pedaço de Pano", "emoji": "🧣",
        "type": "material_monstro", "category": "cacada",
        "description": "Retalho comum.", 
        "stackable": True, 
        "media_key": "item_pano_simples"
    },
    "couro_de_lobo": {
        "display_name": "Couro de Lobo", "emoji": "🐺",
        "type": "material_monstro", "category": "cacada",
        "description": "Pele de lobo comum.", 
        "stackable": True, 
        "media_key": "item_couro_de_lobo"
    },
    "couro_de_lobo_alfa": {
        "display_name": "Couro de Lobo Alfa", "emoji": "🟤🐺",
        "type": "material_monstro", "category": "cacada",
        "description": "Pele espessa e rara.", 
        "stackable": True, 
        "media_key": "item_couro_de_lobo_alfa"
    },
    "presa_de_javali": {
        "display_name": "Presa de Javali", "emoji": "🦷",
        "type": "material_monstro", "category": "cacada",
        "description": "Presas afiadas.", 
        "stackable": True, 
        "media_key": "item_presa_de_javali"
    },
    "asa_de_morcego": {
        "display_name": "Asa de Morcego", "emoji": "🦇",
        "type": "material_monstro", "category": "cacada",
        "description": "Asas membranosas.", 
        "stackable": True, 
        "media_key": "item_asa_de_morcego"
    },
    "pele_de_troll": {
        "display_name": "Pele de Troll", "emoji": "🧌",
        "type": "material_monstro", "category": "cacada",
        "description": "Couro grosso regenerativo.", 
        "stackable": True, 
        "media_key": "item_pele_de_troll"
    },
    "ectoplasma": {
        "display_name": "Ectoplasma", "emoji": "👻",
        "type": "material_monstro", "category": "cacada",
        "description": "Resíduo etéreo.", 
        "stackable": True, 
        "media_key": "item_ectoplasma"
    },
    "esporo_de_cogumelo": {
        "display_name": "Esporo de Cogumelo", "emoji": "🍄",
        "type": "material_monstro", "category": "cacada", 
        "stackable": True, 
        "media_key": "item_esporo_de_cogumelo"
    },
    "seiva_de_ent": {
        "display_name": "Seiva de Ent", "emoji": "🌳",
        "type": "material_monstro", "category": "cacada", 
        "stackable": True, 
        "media_key": "item_seiva_de_ent"
    },
    "carapaca_de_pedra": {
        "display_name": "Carapaça de Pedra", "emoji": "🪨",
        "type": "material_monstro", "category": "cacada", 
        "stackable": True, 
        "media_key": "item_carapaca_de_pedra"
    },
    "escama_de_salamandra": {
        "display_name": "Escama de Salamandra", "emoji": "🦎",
        "type": "material_monstro", "category": "cacada", 
        "stackable": True, 
        "media_key": "item_escama_de_salamandra"
    },
    "engrenagem_usada": {
        "display_name": "Engrenagem Usada", "emoji": "⚙️",
        "type": "material_monstro", "category": "cacada", 
        "stackable": True, 
        "media_key": "item_engrenagem_usada"
    },
    "martelo_enferrujado": {
        "display_name": "Martelo Enferrujado", "emoji": "🔨🔸",
        "type": "sucata", "category": "cacada", 
        "stackable": True, 
        "media_key": "item_martelo_enferrujado"
    },
    "dente_afiado": {
        "display_name": "Dente Afiado", "emoji": "🦷",
        "type": "material_monstro", "category": "cacada", 
        "stackable": True, 
        "media_key": "item_dente_afiado"
    },
    "dente_afiado_superior": {
        "display_name": "Dente Afiado Superior", "emoji": "🦷",
        "type": "material_monstro", "category": "cacada", 
        "stackable": True, 
        "media_key": "item_dente_afiado_superior"
    },
    "fragmento_gargula": {
        "display_name": "Fragmento de Gárgula", "emoji": "🪨",
        "type": "material_monstro", "category": "cacada", 
        "stackable": True, 
        "media_key": "item_fragmento_gargula"
    },
    # --- REAGENTE E MATERIAIS MÁGICOS ---
    "poeira_magica": {
        "display_name": "Poeira Mágica", "emoji": "✨",
        "type": "material_magico", "category": "cacada", 
        "stackable": True, 
        "media_key": "item_poeira_magica"
    },
    "ambar_seiva": {
        "display_name": "Âmbar Fossilizado", "emoji": "🔸",
        "type": "reagent", "category": "coletavel", 
        "stackable": True,
        "media_key": "imagem_ambar_seiva",
    },
    "nucleo_de_golem": {
        "display_name": "Núcleo de Golem", "emoji": "🧿",
        "type": "material_magico", "category": "cacada", 
        "stackable": True, 
        "media_key": "item_nucleo_de_golem"
    },
    "coracao_de_magma": {
        "display_name": "Coração de Magma", "emoji": "❤️‍🔥",
        "type": "material_magico", "category": "cacada", 
        "stackable": True, 
        "media_key": "item_coracao_de_magma"
    },
    "nucleo_de_magma": {
        "display_name": "Núcleo de Magma", "emoji": "🪔",
        "type": "material_magico", "category": "cacada", 
        "stackable": True, 
        "media_key": "item_nucleo_de_magma"
    },
    "olho_de_basilisco": {
        "display_name": "Olho de Basilisco", "emoji": "👁️",
        "type": "material_magico", 
        "category": "cacada", 
        "stackable": True, 
        "media_key": "item_olho_de_basilisco"
    },
    "essencia_de_fogo": {
        "display_name": "Essência de Fogo", "emoji": "♨️",
        "type": "material_magico", "category": "cacada", 
        "stackable": True, 
        "media_key": "item_essencia_de_fogo"
    },
    "semente_encantada": {
        "display_name": "Semente Encantada", "emoji": "🌱✨",
        "type": "material_magico", "category": "cacada", 
        "stackable": True, 
        "media_key": "item_semente_encantada"
    },
    "joia_da_criacao": {
        "display_name": "Joia da Criação", "emoji": "🔷",
        "type": "material_magico", "category": "consumivel", 
        "stackable": True, 
        "media_key": "item_joia_da_criacao"
    },
    "nucleo_de_energia_instavel": {
        "display_name": "Núcleo de Energia Instável", "emoji": "💥",
        "type": "material_magico", "category": "especial", 
        "stackable": True, 
        "media_key": "item_nucleo_de_energia_instavel"
    },

    # --- REFINADOS E MANUFATURADOS ---
    "barra_de_ferro": {
        "display_name": "Barra de Ferro", "emoji": "🧱",
        "type": "material_refinado", "category": "coletavel", 
        "stackable": True, "media_key": 
        "item_barra_de_ferro"
    },
    "barra_de_aco": {
        "display_name": "Barra de Aço", "emoji": "🧱⛓️",
        "type": "material_refinado", "category": "coletavel", 
        "stackable": True, 
        "media_key": "item_barra_de_aco"
    },
    "barra_de_prata": {
        "display_name": "Barra de Prata", "emoji": "🧱🥈",
        "type": "material_refinado", "category": "coletavel", 
        "stackable": True, 
        "media_key": "item_barra_de_prata" 
    },
    "barra_bronze": {
        "display_name": "Barra de Bronze", "emoji": "🧱🟤",
        "type": "material_refinado", "category": "coletavel", 
        "stackable": True, 
        "media_key": "item_barra_de_bronze"
    },
    "couro_curtido": {
        "display_name": "Couro Curtido", "emoji": "🐑",
        "type": "material_refinado", "category": "coletavel", 
        "stackable": True, 
        "media_key": "item_couro_curtido"
    },
    "couro_reforcado": {
        "display_name": "Couro Reforçado", "emoji": "🐂",
        "type": "material_refinado", "category": "coletavel", 
        "stackable": True, 
        "media_key": "item_couro_reforcado"
    },
    "couro_escamoso": {
        "display_name": "Couro Escamoso", "emoji": "🐊",
        "type": "material_refinado", "category": "coletavel", 
        "stackable": True, 
        "media_key": "item_couro_escamoso"
    },
    "rolo_de_pano_simples": {
        "display_name": "Rolo de Pano Simples", "emoji": "🪢",
        "type": "material_refinado", "category": "coletavel", 
        "stackable": True, 
        "media_key": "item_rolo_de_pano_simples"
    },
    "veludo_runico": {
        "display_name": "Veludo Rúnico", "emoji": "🧵",
        "type": "material_refinado", "category": "coletavel", 
        "stackable": True, 
        "media_key": "item_veludo_runico"
    },
    "rolo_seda_sombria": {
        "display_name": "Rolo de Seda Sombria", "emoji": "🌑🧵",
        "type": "material_refinado", "category": "coletavel", 
        "stackable": True, 
        "media_key": "item_rolo_seda_sombria"
    },
    "gema_bruta": {
        "display_name": "Gema Bruta", "emoji": "💎",
        "type": "material_bruto", "category": "cacada", 
        "stackable": True, 
        "media_key": "item_gema_bruta"
    },
    "gema_polida": { 
        "display_name": "Gema Polida", "emoji": "🔷",
        "type": "material_refinado", "category": "coletavel", 
        "stackable": True, 
        "media_key": "item_gema_polida"
    },
    "fio_de_prata": {
        "display_name": "Fio de Prata", "emoji": "🪡",
        "type": "material_refinado", "category": "coletavel", 
        "stackable": True, 
        "media_key": "item_fio_de_prata"
    },
    "membrana_de_couro_fino": {
        "display_name": "Membrana de couro fino", "emoji": "🟤🦇",
        "type": "material_refinado", "category": "coletavel", 
        "stackable": True, 
        "media_key": "item_membrana_de_couro_fino"
    },
    "gema_de_polimento": {
        "display_name": "Gema de Polimento", "emoji": "💎✨",
        "type": "consumivel", "category": "especial",
        "description": "Aplica um revestimento mágico. Adiciona +5 de Durabilidade Máxima a uma ferramenta.",
        "stackable": True,
        "value": 0, # Valor 0 (Premium/Gemas)
        "premium": True,
        "media_key": "item_gema_polimento"
    },

    # --- NOVOS RECURSOS DE LENHADOR (Madeiras Nobres) ---
    "madeira_mogno": {
        "display_name": "Mogno Real", "emoji": "🪵🔴",
        "type": "material_bruto", "category": "coletavel",
        "tier": 3, "profession": "lenhador",
        "description": "Madeira nobre de cor avermelhada.",
        "stackable": True, "value": 80,
        "media_key": "item_madeira_mogno"
    },
    "madeira_elfica": {
        "display_name": "Madeira Élfica", "emoji": "🪵🍃",
        "type": "material_bruto", "category": "coletavel",
        "tier": 4, "profession": "lenhador",
        "description": "Leve como pluma, dura como aço.",
        "stackable": True, "value": 350,
        "media_key": "item_madeira_elfica"
    },
    "raiz_do_mundo": {
        "display_name": "Fragmento de Yggdrasil", "emoji": "🪵🌌",
        "type": "material_bruto", "category": "coletavel",
        "tier": 5, "profession": "lenhador",
        "description": "Um pedaço da árvore que sustenta os mundos.",
        "stackable": True, "value": 1500,
        "media_key": "item_raiz_do_mundo"
    },

    # --- NOVOS RECURSOS DE MINERADOR (Minérios Raros) ---
    "cristal_mana": {
        "display_name": "Cristal de Mana", "emoji": "💎⚡",
        "type": "material_bruto", "category": "coletavel",
        "tier": 4, "profession": "minerador",
        "description": "Pedra pulsante de energia mágica.",
        "stackable": True, "value": 400,
        "media_key": "item_cristal_mana"
    },
    "obsidiana_ancestral": {
        "display_name": "Obsidiana Ancestral", "emoji": "⚫🔥",
        "type": "material_bruto", "category": "coletavel",
        "tier": 5, "profession": "minerador",
        "description": "Minério forjado no núcleo do planeta.",
        "stackable": True, "value": 1800,
        "media_key": "item_obsidiana_ancestral"
    },

    # --- NOVOS RECURSOS DE COLHEDOR (Plantas Exóticas) ---
    "erva_cura": {
        "display_name": "Erva Medicinal", "emoji": "🌿💚",
        "type": "reagent", "category": "coletavel",
        "tier": 2, "profession": "colhedor",
        "description": "Folha básica para poções de vida.",
        "stackable": True, "value": 15,
        "media_key": "item_erva_cura"
    },
    "raiz_solar": {
        "display_name": "Raiz Solar", "emoji": "🥕☀️",
        "type": "reagent", "category": "coletavel",
        "tier": 4, "profession": "colhedor",
        "description": "Quente ao toque, brilha no escuro.",
        "stackable": True, "value": 300,
        "media_key": "item_raiz_solar"
    },
    "fruta_imortalidade": {
        "display_name": "Pêssego Dourado", "emoji": "🍑✨",
        "type": "reagent", "category": "coletavel",
        "tier": 5, "profession": "colhedor",
        "description": "Diz a lenda que concede vida eterna.",
        "stackable": True, "value": 1200,
        "media_key": "item_fruta_imortalidade"
    },

    # --- NOVOS RECURSOS DE ESFOLADOR (Peles de Monstros) ---
    "escama_serpente": {
        "display_name": "Escama de Serpente", "emoji": "🐍🟢",
        "type": "material_monstro", "category": "cacada",
        "tier": 3, "profession": "esfolador",
        "description": "Material duro e flexível.",
        "stackable": True, "value": 90,
        "media_key": "item_escama_serpente"
    },
    "couro_dragao": {
        "display_name": "Couro de Dragão", "emoji": "🐉🔴",
        "type": "material_monstro", "category": "cacada",
        "tier": 4, "profession": "esfolador",
        "description": "Imune ao fogo comum.",
        "stackable": True, "value": 450,
        "media_key": "item_couro_dragao"
    },
    "essencia_vital": {
        "display_name": "Essência Vital", "emoji": "❤️💎",
        "type": "material_monstro", "category": "cacada",
        "tier": 5, "profession": "esfolador",
        "description": "A própria alma da criatura solidificada.",
        "stackable": True, "value": 2000,
        "media_key": "item_essencia_vital"
    },

    # --- NOVOS RECURSOS DE ALQUIMISTA (Fluidos e Energias) ---
    "agua_pura": {
        "display_name": "Água Pura", "emoji": "💧",
        "type": "reagent", "category": "coletavel",
        "tier": 1, "profession": "alquimista",
        "description": "Água cristalina de nascente.",
        "stackable": True, "value": 5,
        "media_key": "item_agua_pura"
    },
    "gas_venenoso": {
        "display_name": "Gás do Pântano", "emoji": "☁️🤢",
        "type": "reagent", "category": "coletavel",
        "tier": 3, "profession": "alquimista",
        "description": "Tóxico, coletado com extrator.",
        "stackable": True, "value": 85,
        "media_key": "item_gas_venenoso"
    },
    "luz_estelar": {
        "display_name": "Luz Estelar Líquida", "emoji": "🌟💧",
        "type": "reagent", "category": "coletavel",
        "tier": 5, "profession": "alquimista",
        "description": "Um pedaço do céu em um frasco.",
        "stackable": True, "value": 1600,
        "media_key": "item_luz_estelar"
    },    

    # =========================
# COLETA / REFINO (NOVOS)
# =========================

"tronco_antigo": {
    "display_name": "Tronco Antigo",
    "emoji": "🪵",
    "type": "material",
    "category": "madeira",
    "stackable": True,
    "tier": 4,
    "profession": "lenhador",
    "description": "Um tronco ancestral, denso e resistente. Usado em tábuas avançadas."
},

"pedra_vulcanica": {
    "display_name": "Pedra Vulcânica",
    "emoji": "🌋",
    "type": "material",
    "category": "mineral",
    "stackable": True,
    "tier": 3,
    "profession": "minerador",
    "description": "Rocha quente e rica em minerais. Usada em ligas especiais."
},

"linho_fino": {
    "display_name": "Linho Fino",
    "emoji": "🧵",
    "type": "material",
    "category": "fibra",
    "stackable": True,
    "tier": 2,
    "profession": "colhedor",
    "description": "Fibra de linho de alta qualidade. Ideal para tecidos superiores."
},

"fibra_resistente": {
    "display_name": "Fibra Resistente",
    "emoji": "🪢",
    "type": "material",
    "category": "fibra",
    "stackable": True,
    "tier": 3,
    "profession": "colhedor",
    "description": "Fibra robusta usada para reforçar tecidos e equipamentos leves."
},

"fibra_sedosa": {
    "display_name": "Fibra Sedosa",
    "emoji": "🕸️",
    "type": "material",
    "category": "fibra",
    "stackable": True,
    "tier": 4,
    "profession": "colhedor",
    "description": "Fibra rara e sedosa para tecidos avançados e especiais."
},

"pena_grande": {
    "display_name": "Pena Grande",
    "emoji": "🪶",
    "type": "material",
    "category": "caça",
    "stackable": True,
    "tier": 2,
    "profession": "esfolador",
    "description": "Pena grande e resistente, valorizada por artesãos."
},

"couro_de_grifo": {
    "display_name": "Couro de Grifo",
    "emoji": "🟫",
    "type": "material",
    "category": "couro",
    "stackable": True,
    "tier": 3,
    "profession": "esfolador",
    "description": "Couro raro de criatura alada, usado em armaduras leves superiores."
},

"garras_de_grifo": {
    "display_name": "Garras de Grifo",
    "emoji": "🦴",
    "type": "material",
    "category": "caça",
    "stackable": True,
    "tier": 4,
    "profession": "esfolador",
    "description": "Garras afiadas usadas em receitas especiais e itens raros."
},

"pluma_celestial": {
    "display_name": "Pluma Celestial",
    "emoji": "✨",
    "type": "material",
    "category": "caça",
    "stackable": True,
    "tier": 5,
    "profession": "esfolador",
    "description": "Uma pluma raríssima com energia mística. Material épico."
},

"lodo_toxico": {
    "display_name": "Lodo Tóxico",
    "emoji": "🧫",
    "type": "material",
    "category": "alquimia",
    "stackable": True,
    "tier": 2,
    "profession": "alquimista",
    "description": "Substância corrosiva do pântano, usada em venenos e reagentes."
},

"sangue_regenerativo": {
    "display_name": "Sangue Regenerativo",
    "emoji": "🩸",
    "type": "material",
    "category": "alquimia",
    "stackable": True,
    "tier": 3,
    "profession": "alquimista",
    "description": "Sangue raro com propriedades regenerativas. Muito valioso."
},

"essencia_sombra": {
    "display_name": "Essência da Sombra",
    "emoji": "🌑",
    "type": "material",
    "category": "alquimia",
    "stackable": True,
    "tier": 5,
    "profession": "alquimista",
    "description": "Essência sombria concentrada. Usada em receitas épicas."
},

"escoria_metalica": {
    "display_name": "Escória Metálica",
    "emoji": "⚙️",
    "type": "material",
    "category": "mineral",
    "stackable": True,
    "tier": 2,
    "profession": "minerador",
    "description": "Resíduo metálico de forjas antigas. Pode ser usado em ligas e refino."
},

"fragmento_de_magma": {
    "display_name": "Fragmento de Magma",
    "emoji": "🔥",
    "type": "material",
    "category": "mineral",
    "stackable": True,
    "tier": 4,
    "profession": "minerador",
    "description": "Fragmento incandescente usado em ligas e processos avançados."
},

"nucleo_igneo": {
    "display_name": "Núcleo Ígneo",
    "emoji": "💠",
    "type": "material",
    "category": "mineral",
    "stackable": True,
    "tier": 5,
    "profession": "minerador",
    "description": "Núcleo elemental extremamente raro. Material épico de refino."
},

"cinzas_elementais": {
    "display_name": "Cinzas Elementais",
    "emoji": "🌪️",
    "type": "material",
    "category": "alquimia",
    "stackable": True,
    "tier": 3,
    "profession": "alquimista",
    "description": "Cinzas carregadas de energia elemental. Reagente versátil."
},
    # --- MINÉRIOS RAROS (T4 / T5) ---
    "minerio_de_mithril": {
        "display_name": "Minério de Mithril", "emoji": "⛓️🔷",
        "type": "material_bruto", "category": "coletavel",
        "tier": 4, "profession": "minerador",
        "description": "Minério raro, leve e extremamente resistente.",
        "stackable": True,
        "media_key": "item_minerio_de_mithril"
    },
    "minerio_de_adamantio": {
        "display_name": "Minério de Adamantio", "emoji": "⛓️🔴",
        "type": "material_bruto", "category": "coletavel",
        "tier": 5, "profession": "minerador",
        "description": "Minério lendário quase indestrutível.",
        "stackable": True,
        "media_key": "item_minerio_de_adamantio"
    },

    # --- BARRAS REFINADAS (MITHRIL / ADAMANTIO) ---
    "barra_de_mithril": {
        "display_name": "Barra de Mithril", "emoji": "🧱🔷",
        "type": "material_refinado", "category": "coletavel",
        "tier": 4,
        "description": "Barra refinada de mithril, usada em equipamentos avançados.",
        "stackable": True,
        "media_key": "item_barra_de_mithril"
    },
    "barra_de_adamantio": {
        "display_name": "Barra de Adamantio", "emoji": "🧱🔴",
        "type": "material_refinado", "category": "coletavel",
        "tier": 5,
        "description": "Barra lendária de adamantio, base de itens épicos.",
        "stackable": True,
        "media_key": "item_barra_de_adamantio"
    },


}
