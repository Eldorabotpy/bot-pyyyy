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
    
}