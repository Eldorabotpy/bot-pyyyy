TOOLS_DATA = {
    # ==========================================
    # 1. LENHADOR (Machados - Coleta Madeira)
    # ==========================================
    "machado_pedra": {
        "display_name": "Machado de Pedra", "emoji": "🪓",
        "type": "tool", "slot": "tool", "tool_type": "lenhador", 
        "tier": 1, "durability": [10, 10],
        "description": "Ferramenta primitiva. Coleta madeira básica.",
        "rarity": "comum", "stackable": False, "value": 50
    },
    "machado_ferro": {
        "display_name": "Machado de Ferro", "emoji": "🪓⛓️",
        "type": "tool", "slot": "tool", "tool_type": "lenhador", 
        "tier": 2, "durability": [30, 30],
        "description": "Lâmina de ferro robusta. Corta carvalho.",
        "rarity": "incomum", "stackable": False, "value": 200
    },
    "machado_aco": {
        "display_name": "Machado de Aço", "emoji": "🪓✨",
        "type": "tool", "slot": "tool", "tool_type": "lenhador", 
        "tier": 3, "durability": [50, 50],
        "description": "Aço temperado. Corta madeiras duras como Mogno.",
        "rarity": "raro", "stackable": False, "value": 600
    },
    "machado_mithril": {
        "display_name": "Machado de Mithril", "emoji": "🪓💠",
        "type": "tool", "slot": "tool", "tool_type": "lenhador", 
        "tier": 4, "durability": [70, 70],
        "description": "Leve e indestrutível. Corta árvores mágicas.",
        "rarity": "epico", "stackable": False, "value": 2500
    },
    "machado_adamantio": {
        "display_name": "Machado de Adamantio", "emoji": "🪓🐉",
        "type": "tool", "slot": "tool", "tool_type": "lenhador", 
        "tier": 5, "durability": [90, 90],
        "description": "Lâmina lendária. Corta a Raiz do Mundo.",
        "rarity": "lendario", "stackable": False, "value": 10000
    },

    # ==========================================
    # 2. MINERADOR (Picaretas - Coleta Minérios)
    # ==========================================
    "picareta_pedra": {
        "display_name": "Picareta de Pedra", "emoji": "⛏️",
        "type": "tool", "slot": "tool", "tool_type": "minerador", 
        "tier": 1, "durability": [10, 10],
        "description": "Quebra pedras comuns e cobre.",
        "rarity": "comum", "stackable": False, "value": 50
    },
    "picareta_ferro": {
        "display_name": "Picareta de Ferro", "emoji": "⛏️⛓️",
        "type": "tool", "slot": "tool", "tool_type": "minerador", 
        "tier": 2, "durability": [30, 30],
        "description": "Forte o suficiente para minerar Ferro.",
        "rarity": "incomum", "stackable": False, "value": 220
    },
    "picareta_aco": {
        "display_name": "Picareta de Aço", "emoji": "⛏️✨",
        "type": "tool", "slot": "tool", "tool_type": "minerador", 
        "tier": 3, "durability": [50, 50],
        "description": "Aço reforçado. Pode minerar Ouro e Prata.",
        "rarity": "raro", "stackable": False, "value": 650
    },
    "picareta_mithril": {
        "display_name": "Picareta de Mithril", "emoji": "⛏️💠",
        "type": "tool", "slot": "tool", "tool_type": "minerador", 
        "tier": 4, "durability": [70, 70],
        "description": "Brilha com luz própria. Minera Cristais de Mana.",
        "rarity": "epico", "stackable": False, "value": 2800
    },
    "picareta_adamantio": {
        "display_name": "Picareta de Adamantio", "emoji": "⛏️💎",
        "type": "tool", "slot": "tool", "tool_type": "minerador", 
        "tier": 5, "durability": [90, 90],
        "description": "Ponta de diamante negro. Quebra Obsidiana Ancestral.",
        "rarity": "lendario", "stackable": False, "value": 12000
    },

    # ==========================================
    # 3. COLHEDOR (Foices - Coleta Plantas/Ervas)
    # ==========================================
    "foice_pedra": {
        "display_name": "Foice de Pedra", "emoji": "🌾",
        "type": "tool", "slot": "tool", "tool_type": "colhedor", 
        "tier": 1, "durability": [10, 10],
        "description": "Corte irregular. Serve para fibras simples.",
        "rarity": "comum", "stackable": False, "value": 50
    },
    "foice_ferro": {
        "display_name": "Foice de Ferro", "emoji": "🌾⛓️",
        "type": "tool", "slot": "tool", "tool_type": "colhedor", 
        "tier": 2, "durability": [30, 30],
        "description": "Lâmina curva. Colhe ervas medicinais.",
        "rarity": "incomum", "stackable": False, "value": 150
    },
    "foice_aco": {
        "display_name": "Foice de Aço", "emoji": "🌾✨",
        "type": "tool", "slot": "tool", "tool_type": "colhedor", 
        "tier": 3, "durability": [50, 50],
        "description": "Corte preciso. Extrai flores raras intactas.",
        "rarity": "raro", "stackable": False, "value": 550
    },
    "foice_mithril": {
        "display_name": "Foice de Mithril", "emoji": "🌾💠",
        "type": "tool", "slot": "tool", "tool_type": "colhedor", 
        "tier": 4, "durability": [70, 70],
        "description": "Não enferruja. Colhe plantas lunares.",
        "rarity": "epico", "stackable": False, "value": 2200
    },
    "foice_druidica": {
        "display_name": "Foice da Natureza", "emoji": "🌾🍃",
        "type": "tool", "slot": "tool", "tool_type": "colhedor", 
        "tier": 5, "durability": [90, 90],
        "description": "Abençoada. Colhe a Vida Eterna.",
        "rarity": "lendario", "stackable": False, "value": 9000
    },

    # ==========================================
    # 4. ESFOLADOR (Facas - Coleta Couro/Peles)
    # ==========================================
    "faca_pedra": {
        "display_name": "Faca de Pederneira", "emoji": "🗡️",
        "type": "tool", "slot": "tool", "tool_type": "esfolador", 
        "tier": 1, "durability": [10, 10],
        "description": "Corte grosseiro. Coleta peles rasgadas.",
        "rarity": "comum", "stackable": False, "value": 50
    },
    "faca_ferro": {
        "display_name": "Faca de Caça", "emoji": "🗡️⛓️",
        "type": "tool", "slot": "tool", "tool_type": "esfolador", 
        "tier": 2, "durability": [30, 30],
        "description": "Afiada. Remove couro de animais médios.",
        "rarity": "incomum", "stackable": False, "value": 190
    },
    "faca_aco": {
        "display_name": "Faca de Esfolar", "emoji": "🗡️✨",
        "type": "tool", "slot": "tool", "tool_type": "esfolador", 
        "tier": 3, "durability": [50, 50],
        "description": "Lâmina cirúrgica. Obtém couro perfeito e escamas.",
        "rarity": "raro", "stackable": False, "value": 580
    },
    "faca_obsidiana": {
        "display_name": "Lâmina de Obsidiana", "emoji": "🗡️🌑",
        "type": "tool", "slot": "tool", "tool_type": "esfolador", 
        "tier": 4, "durability": [70, 70],
        "description": "Mais afiada que o aço. Corta couro de dragão.",
        "rarity": "epico", "stackable": False, "value": 2400
    },
    "faca_vorpal": {
        "display_name": "A Estripadora", "emoji": "🗡️🩸",
        "type": "tool", "slot": "tool", "tool_type": "esfolador", 
        "tier": 5, "durability": [90, 90],
        "description": "Separa a alma do corpo. Coleta essências vitais.",
        "rarity": "lendario", "stackable": False, "value": 10500
    },

    # ==========================================
    # 5. ALQUIMISTA (Frascos/Extratores - Coleta Fluidos/Essências)
    # ==========================================
    "frasco_vidro": {
        "display_name": "Frasco de Vidro", "emoji": "🧪",
        "type": "tool", "slot": "tool", "tool_type": "alquimista", 
        "tier": 1, "durability": [10, 10],
        "description": "Frágil. Coleta água pura e seiva simples.",
        "rarity": "comum", "stackable": False, "value": 50
    },
    "frasco_ceramica": {
        "display_name": "Recipiente de Cerâmica", "emoji": "🏺",
        "type": "tool", "slot": "tool", "tool_type": "alquimista", 
        "tier": 2, "durability": [30, 30],
        "description": "Resistente. Coleta ácidos fracos e óleos.",
        "rarity": "incomum", "stackable": False, "value": 100
    },
    "extrator_cristal": {
        "display_name": "Extrator de Cristal", "emoji": "⚗️",
        "type": "tool", "slot": "tool", "tool_type": "alquimista", 
        "tier": 3, "durability": [50, 50],
        "description": "Vidro reforçado com magia. Coleta venenos e névoas.",
        "rarity": "raro", "stackable": False, "value": 450
    },
    "coletor_runico": {
        "display_name": "Coletor Rúnico", "emoji": "🔮",
        "type": "tool", "slot": "tool", "tool_type": "alquimista", 
        "tier": 4, "durability": [70, 70],
        "description": "Atrai energia. Coleta Fogo Fátuo e Ectoplasma.",
        "rarity": "epico", "stackable": False, "value": 2000
    },
    "cubo_vazio": {
        "display_name": "Cubo de Contenção", "emoji": "◼️",
        "type": "tool", "slot": "tool", "tool_type": "alquimista", 
        "tier": 5, "durability": [90, 90],
        "description": "Desafia a física. Coleta Luz Estelar e Sombras.",
        "rarity": "lendario", "stackable": False, "value": 8500
    },

    # ==========================================
    # 6. CRIAÇÃO (Ferramentas de Crafting) — RPG
    # ==========================================

    # --------------------------
    # FERREIRO (Martelos)
    # --------------------------
    "martelo_ferreiro_t1": {
        "display_name": "Martelo do Aprendiz Ferreiro", "emoji": "🔨",
        "type": "tool", "slot": "tool", "tool_type": "ferreiro",
        "tier": 1, "durability": [25, 25],
        "description": "Um martelo simples, mas confiável. Permite forjas básicas.",
        "rarity": "comum", "stackable": False, "value": 160
    },
    "martelo_ferreiro_t2": {
        "display_name": "Martelo de Ferro do Ferreiro", "emoji": "🔨",
        "type": "tool", "slot": "tool", "tool_type": "ferreiro",
        "tier": 2, "durability": [40, 40],
        "description": "Cabeça de ferro bem balanceada. Forja com mais precisão.",
        "rarity": "incomum", "stackable": False, "value": 320
    },
    "martelo_ferreiro_t3": {
        "display_name": "Martelo de Aço Temperado", "emoji": "🔨",
        "type": "tool", "slot": "tool", "tool_type": "ferreiro",
        "tier": 3, "durability": [60, 60],
        "description": "Aço temperado que mantém o fio e a forma. Ideal para trabalho pesado.",
        "rarity": "raro", "stackable": False, "value": 620
    },
    "martelo_ferreiro_t4": {
        "display_name": "Martelo de Mithril do Mestre Ferreiro", "emoji": "🔨",
        "type": "tool", "slot": "tool", "tool_type": "ferreiro",
        "tier": 4, "durability": [85, 85],
        "description": "Leve e resistente. A bigorna canta quando ele toca o metal.",
        "rarity": "épico", "stackable": False, "value": 1200
    },
    "martelo_ferreiro_t5": {
        "display_name": "Martelo Adamantino do Forjador Ancestral", "emoji": "🔨",
        "type": "tool", "slot": "tool", "tool_type": "ferreiro",
        "tier": 5, "durability": [120, 120],
        "description": "Dizem que cada golpe grava runas invisíveis no aço. Forja lendária.",
        "rarity": "lendário", "stackable": False, "value": 2400
    },

    # --------------------------
    # ARMEIRO (Martelos de Armas / Cinzel)
    # --------------------------
    "martelo_armeiro_t1": {
        "display_name": "Martelo do Armeiro Iniciante", "emoji": "⚒️",
        "type": "tool", "slot": "tool", "tool_type": "armeiro",
        "tier": 1, "durability": [25, 25],
        "description": "Ferramenta básica para moldar lâminas e guardas simples.",
        "rarity": "comum", "stackable": False, "value": 170
    },
    "martelo_armeiro_t2": {
        "display_name": "Martelo de Rebite do Armeiro", "emoji": "⚒️",
        "type": "tool", "slot": "tool", "tool_type": "armeiro",
        "tier": 2, "durability": [40, 40],
        "description": "Excelente para encaixes e rebites. Reduz erros de montagem.",
        "rarity": "incomum", "stackable": False, "value": 340
    },
    "martelo_armeiro_t3": {
        "display_name": "Martelo de Aço do Artesão Bélico", "emoji": "⚒️",
        "type": "tool", "slot": "tool", "tool_type": "armeiro",
        "tier": 3, "durability": [60, 60],
        "description": "Golpes firmes e exatos. Indispensável para armas de qualidade.",
        "rarity": "raro", "stackable": False, "value": 660
    },
    "martelo_armeiro_t4": {
        "display_name": "Martelo de Mithril do Forjador de Guerra", "emoji": "⚒️",
        "type": "tool", "slot": "tool", "tool_type": "armeiro",
        "tier": 4, "durability": [85, 85],
        "description": "O equilíbrio perfeito entre força e precisão. Armas de elite nascem aqui.",
        "rarity": "épico", "stackable": False, "value": 1280
    },
    "martelo_armeiro_t5": {
        "display_name": "Martelo Adamantino do Arsenal Real", "emoji": "⚒️",
        "type": "tool", "slot": "tool", "tool_type": "armeiro",
        "tier": 5, "durability": [120, 120],
        "description": "Forja armas dignas de reis. Um golpe, uma obra-prima.",
        "rarity": "lendário", "stackable": False, "value": 2550
    },

    # --------------------------
    # ALFAIATE (Ferramentas de Costura)
    # --------------------------
    "ferramentas_alfaiate_t1": {
        "display_name": "Estojo de Costura do Aprendiz", "emoji": "🧵",
        "type": "tool", "slot": "tool", "tool_type": "alfaiate",
        "tier": 1, "durability": [25, 25],
        "description": "Agulhas simples e linha comum. Permite costura básica.",
        "rarity": "comum", "stackable": False, "value": 150
    },
    "ferramentas_alfaiate_t2": {
        "display_name": "Conjunto de Agulhas Reforçadas", "emoji": "🧵",
        "type": "tool", "slot": "tool", "tool_type": "alfaiate",
        "tier": 2, "durability": [40, 40],
        "description": "Agulhas resistentes e tesoura afiada. Acabamento superior.",
        "rarity": "incomum", "stackable": False, "value": 300
    },
    "ferramentas_alfaiate_t3": {
        "display_name": "Kit do Alfaiate Artesão", "emoji": "🧵",
        "type": "tool", "slot": "tool", "tool_type": "alfaiate",
        "tier": 3, "durability": [60, 60],
        "description": "Linha firme e cortes precisos. Ideal para peças de couro e tecido grosso.",
        "rarity": "raro", "stackable": False, "value": 590
    },
    "ferramentas_alfaiate_t4": {
        "display_name": "Tesouras de Mithril e Bobinas Finas", "emoji": "🧵",
        "type": "tool", "slot": "tool", "tool_type": "alfaiate",
        "tier": 4, "durability": [85, 85],
        "description": "Corta como vento e costura como seda. Vestes raras ganham forma.",
        "rarity": "épico", "stackable": False, "value": 1150
    },
    "ferramentas_alfaiate_t5": {
        "display_name": "Instrumentos do Alfaiate das Cortes", "emoji": "🧵",
        "type": "tool", "slot": "tool", "tool_type": "alfaiate",
        "tier": 5, "durability": [120, 120],
        "description": "Tecidos obedecem suas mãos. Dizem que cada ponto sela proteção antiga.",
        "rarity": "lendário", "stackable": False, "value": 2300
    },

    # --------------------------
    # JOALHEIRO (Lapidação e Montagem)
    # --------------------------
    "ferramentas_joalheiro_t1": {
        "display_name": "Ferramentas do Lapidador Iniciante", "emoji": "💎",
        "type": "tool", "slot": "tool", "tool_type": "joalheiro",
        "tier": 1, "durability": [25, 25],
        "description": "Limas e pinças simples. Monta joias básicas.",
        "rarity": "comum", "stackable": False, "value": 190
    },
    "ferramentas_joalheiro_t2": {
        "display_name": "Kit de Polimento Refinado", "emoji": "💎",
        "type": "tool", "slot": "tool", "tool_type": "joalheiro",
        "tier": 2, "durability": [40, 40],
        "description": "Melhora brilho e precisão. Ótimo para engastes mais firmes.",
        "rarity": "incomum", "stackable": False, "value": 380
    },
    "ferramentas_joalheiro_t3": {
        "display_name": "Ferramentas do Ourives Experiente", "emoji": "💎",
        "type": "tool", "slot": "tool", "tool_type": "joalheiro",
        "tier": 3, "durability": [60, 60],
        "description": "Cinzel e lupa de precisão. Ideal para runas e detalhes finos.",
        "rarity": "raro", "stackable": False, "value": 720
    },
    "ferramentas_joalheiro_t4": {
        "display_name": "Conjunto de Mithril do Mestre Ourives", "emoji": "💎",
        "type": "tool", "slot": "tool", "tool_type": "joalheiro",
        "tier": 4, "durability": [85, 85],
        "description": "Engastes perfeitos. Gema e metal se unem sem falhas.",
        "rarity": "épico", "stackable": False, "value": 1380
    },
    "ferramentas_joalheiro_t5": {
        "display_name": "Ferramentas Rúnicas do Joalheiro Arcano", "emoji": "💎",
        "type": "tool", "slot": "tool", "tool_type": "joalheiro",
        "tier": 5, "durability": [120, 120],
        "description": "Lapida essência além da pedra. Joias lendárias nascem deste conjunto.",
        "rarity": "lendário", "stackable": False, "value": 2750
    },

    # --------------------------
    # CURTIDOR (Tratamento de Couro)
    # --------------------------
    "ferramentas_curtidor_t1": {
        "display_name": "Raspador do Curtidor Iniciante", "emoji": "🧴",
        "type": "tool", "slot": "tool", "tool_type": "curtidor",
        "tier": 1, "durability": [25, 25],
        "description": "Ferramenta simples para raspar e preparar peles.",
        "rarity": "comum", "stackable": False, "value": 160
    },
    "ferramentas_curtidor_t2": {
        "display_name": "Conjunto de Curtimento de Ferro", "emoji": "🧴",
        "type": "tool", "slot": "tool", "tool_type": "curtidor",
        "tier": 2, "durability": [40, 40],
        "description": "Melhora a remoção de impurezas e o acabamento do couro.",
        "rarity": "incomum", "stackable": False, "value": 330
    },
    "ferramentas_curtidor_t3": {
        "display_name": "Ferramentas do Curtidor Artesão", "emoji": "🧴",
    "type": "tool", "slot": "tool", "tool_type": "curtidor",
    "tier": 3, "durability": [60, 60],
    "description": "Preparação mais uniforme. Couro mais resistente e flexível.",
    "rarity": "raro", "stackable": False, "value": 640
    },
    "ferramentas_curtidor_t4": {
        "display_name": "Conjunto de Mithril para Couro Raro", "emoji": "🧴",
        "type": "tool", "slot": "tool", "tool_type": "curtidor",
        "tier": 4, "durability": [85, 85],
        "description": "Corta e trata sem agredir a fibra. Ideal para peles exóticas.",
        "rarity": "épico", "stackable": False, "value": 1250
    },
    "ferramentas_curtidor_t5": {
        "display_name": "Ferramentas do Curtidor das Bestas Antigas", "emoji": "🧴",
        "type": "tool", "slot": "tool", "tool_type": "curtidor",
        "tier": 5, "durability": [120, 120],
        "description": "Transforma peles lendárias em armaduras dignas de heróis.",
        "rarity": "lendário", "stackable": False, "value": 2500
    },

    # --------------------------
    # FUNDIDOR (Moldes e Tenazes)
    # --------------------------
    "ferramentas_fundidor_t1": {
        "display_name": "Tenaz do Fundidor Iniciante", "emoji": "🔥",
        "type": "tool", "slot": "tool", "tool_type": "fundidor",
        "tier": 1, "durability": [25, 25],
        "description": "Segura metal quente e auxilia na fundição básica.",
        "rarity": "comum", "stackable": False, "value": 170
    },
    "ferramentas_fundidor_t2": {
        "display_name": "Moldes de Ferro do Fundidor", "emoji": "🔥",
        "type": "tool", "slot": "tool", "tool_type": "fundidor",
        "tier": 2, "durability": [40, 40],
        "description": "Moldagem mais estável. Menos falhas na fundição.",
        "rarity": "incomum", "stackable": False, "value": 350
    },
    "ferramentas_fundidor_t3": {
        "display_name": "Conjunto de Fundição do Artesão", "emoji": "🔥",
        "type": "tool", "slot": "tool", "tool_type": "fundidor",
        "tier": 3, "durability": [60, 60],
        "description": "Controle de temperatura e moldes precisos. Lingotes superiores.",
        "rarity": "raro", "stackable": False, "value": 690
    },
    "ferramentas_fundidor_t4": {
        "display_name": "Tenazes de Mithril e Moldes Finos", "emoji": "🔥",
        "type": "tool", "slot": "tool", "tool_type": "fundidor",
        "tier": 4, "durability": [85, 85],
        "description": "Metal flui como água. Fundição avançada para ligas raras.",
        "rarity": "épico", "stackable": False, "value": 1320
    },
    "ferramentas_fundidor_t5": {
        "display_name": "Instrumentos do Fundidor Vulcânico", "emoji": "🔥",
        "type": "tool", "slot": "tool", "tool_type": "fundidor",
        "tier": 5, "durability": [120, 120],
        "description": "Forjado em calor ancestral. Permite fundir ligas lendárias.",
        "rarity": "lendário", "stackable": False, "value": 2650
},

}