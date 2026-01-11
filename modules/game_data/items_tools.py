TOOLS_DATA = {
    # ==========================================
    # 1. LENHADOR (Machados - Coleta Madeira)
    # ==========================================
    "machado_pedra": {
        "display_name": "Machado de Pedra", "emoji": "🪓",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "lenhador", 
        "tier": 1, "durability": [50, 50],
        "description": "Ferramenta primitiva. Coleta madeira básica.",
        "rarity": "comum", "stackable": False, "value": 50
    },
    "machado_ferro": {
        "display_name": "Machado de Ferro", "emoji": "🪓⛓️",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "lenhador", 
        "tier": 2, "durability": [100, 100],
        "description": "Lâmina de ferro robusta. Corta carvalho.",
        "rarity": "incomum", "stackable": False, "value": 200
    },
    "machado_aco": {
        "display_name": "Machado de Aço", "emoji": "🪓✨",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "lenhador", 
        "tier": 3, "durability": [250, 250],
        "description": "Aço temperado. Corta madeiras duras como Mogno.",
        "rarity": "raro", "stackable": False, "value": 600
    },
    "machado_mithril": {
        "display_name": "Machado de Mithril", "emoji": "🪓💠",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "lenhador", 
        "tier": 4, "durability": [600, 600],
        "description": "Leve e indestrutível. Corta árvores mágicas.",
        "rarity": "epico", "stackable": False, "value": 2500
    },
    "machado_adamantio": {
        "display_name": "Machado de Adamantio", "emoji": "🪓🐉",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "lenhador", 
        "tier": 5, "durability": [1500, 1500],
        "description": "Lâmina lendária. Corta a Raiz do Mundo.",
        "rarity": "lendario", "stackable": False, "value": 10000
    },

    # ==========================================
    # 2. MINERADOR (Picaretas - Coleta Minérios)
    # ==========================================
    "picareta_pedra": {
        "display_name": "Picareta de Pedra", "emoji": "⛏️",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "minerador", 
        "tier": 1, "durability": [50, 50],
        "description": "Quebra pedras comuns e cobre.",
        "rarity": "comum", "stackable": False, "value": 50
    },
    "picareta_ferro": {
        "display_name": "Picareta de Ferro", "emoji": "⛏️⛓️",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "minerador", 
        "tier": 2, "durability": [120, 120],
        "description": "Forte o suficiente para minerar Ferro.",
        "rarity": "incomum", "stackable": False, "value": 220
    },
    "picareta_aco": {
        "display_name": "Picareta de Aço", "emoji": "⛏️✨",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "minerador", 
        "tier": 3, "durability": [300, 300],
        "description": "Aço reforçado. Pode minerar Ouro e Prata.",
        "rarity": "raro", "stackable": False, "value": 650
    },
    "picareta_mithril": {
        "display_name": "Picareta de Mithril", "emoji": "⛏️💠",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "minerador", 
        "tier": 4, "durability": [700, 700],
        "description": "Brilha com luz própria. Minera Cristais de Mana.",
        "rarity": "epico", "stackable": False, "value": 2800
    },
    "picareta_adamantio": {
        "display_name": "Picareta de Adamantio", "emoji": "⛏️💎",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "minerador", 
        "tier": 5, "durability": [1800, 1800],
        "description": "Ponta de diamante negro. Quebra Obsidiana Ancestral.",
        "rarity": "lendario", "stackable": False, "value": 12000
    },

    # ==========================================
    # 3. COLHEDOR (Foices - Coleta Plantas/Ervas)
    # ==========================================
    "foice_pedra": {
        "display_name": "Foice de Pedra", "emoji": "🌾",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "colhedor", 
        "tier": 1, "durability": [40, 40],
        "description": "Corte irregular. Serve para fibras simples.",
        "rarity": "comum", "stackable": False, "value": 40
    },
    "foice_ferro": {
        "display_name": "Foice de Ferro", "emoji": "🌾⛓️",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "colhedor", 
        "tier": 2, "durability": [80, 80],
        "description": "Lâmina curva. Colhe ervas medicinais.",
        "rarity": "incomum", "stackable": False, "value": 150
    },
    "foice_aco": {
        "display_name": "Foice de Aço", "emoji": "🌾✨",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "colhedor", 
        "tier": 3, "durability": [200, 200],
        "description": "Corte preciso. Extrai flores raras intactas.",
        "rarity": "raro", "stackable": False, "value": 550
    },
    "foice_mithril": {
        "display_name": "Foice de Mithril", "emoji": "🌾💠",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "colhedor", 
        "tier": 4, "durability": [500, 500],
        "description": "Não enferruja. Colhe plantas lunares.",
        "rarity": "epico", "stackable": False, "value": 2200
    },
    "foice_druidica": {
        "display_name": "Foice da Natureza", "emoji": "🌾🍃",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "colhedor", 
        "tier": 5, "durability": [1200, 1200],
        "description": "Abençoada. Colhe a Vida Eterna.",
        "rarity": "lendario", "stackable": False, "value": 9000
    },

    # ==========================================
    # 4. ESFOLADOR (Facas - Coleta Couro/Peles)
    # ==========================================
    "faca_pedra": {
        "display_name": "Faca de Pederneira", "emoji": "🗡️",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "esfolador", 
        "tier": 1, "durability": [40, 40],
        "description": "Corte grosseiro. Coleta peles rasgadas.",
        "rarity": "comum", "stackable": False, "value": 45
    },
    "faca_ferro": {
        "display_name": "Faca de Caça", "emoji": "🗡️⛓️",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "esfolador", 
        "tier": 2, "durability": [90, 90],
        "description": "Afiada. Remove couro de animais médios.",
        "rarity": "incomum", "stackable": False, "value": 190
    },
    "faca_aco": {
        "display_name": "Faca de Esfolar", "emoji": "🗡️✨",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "esfolador", 
        "tier": 3, "durability": [220, 220],
        "description": "Lâmina cirúrgica. Obtém couro perfeito e escamas.",
        "rarity": "raro", "stackable": False, "value": 580
    },
    "faca_obsidiana": {
        "display_name": "Lâmina de Obsidiana", "emoji": "🗡️🌑",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "esfolador", 
        "tier": 4, "durability": [500, 500],
        "description": "Mais afiada que o aço. Corta couro de dragão.",
        "rarity": "epico", "stackable": False, "value": 2400
    },
    "faca_vorpal": {
        "display_name": "A Estripadora", "emoji": "🗡️🩸",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "esfolador", 
        "tier": 5, "durability": [1300, 1300],
        "description": "Separa a alma do corpo. Coleta essências vitais.",
        "rarity": "lendario", "stackable": False, "value": 10500
    },

    # ==========================================
    # 5. ALQUIMISTA (Frascos/Extratores - Coleta Fluidos/Essências)
    # ==========================================
    "frasco_vidro": {
        "display_name": "Frasco de Vidro", "emoji": "🧪",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "alquimista", 
        "tier": 1, "durability": [30, 30],
        "description": "Frágil. Coleta água pura e seiva simples.",
        "rarity": "comum", "stackable": True, "value": 25
    },
    "frasco_ceramica": {
        "display_name": "Recipiente de Cerâmica", "emoji": "🏺",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "alquimista", 
        "tier": 2, "durability": [60, 60],
        "description": "Resistente. Coleta ácidos fracos e óleos.",
        "rarity": "incomum", "stackable": True, "value": 100
    },
    "extrator_cristal": {
        "display_name": "Extrator de Cristal", "emoji": "⚗️",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "alquimista", 
        "tier": 3, "durability": [150, 150],
        "description": "Vidro reforçado com magia. Coleta venenos e névoas.",
        "rarity": "raro", "stackable": False, "value": 450
    },
    "coletor_runico": {
        "display_name": "Coletor Rúnico", "emoji": "🔮",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "alquimista", 
        "tier": 4, "durability": [400, 400],
        "description": "Atrai energia. Coleta Fogo Fátuo e Ectoplasma.",
        "rarity": "epico", "stackable": False, "value": 2000
    },
    "cubo_vazio": {
        "display_name": "Cubo de Contenção", "emoji": "◼️",
        "type": "ferramenta", "slot": "ferramenta", "tool_type": "alquimista", 
        "tier": 5, "durability": [1000, 1000],
        "description": "Desafia a física. Coleta Luz Estelar e Sombras.",
        "rarity": "lendario", "stackable": False, "value": 8500
    }
}