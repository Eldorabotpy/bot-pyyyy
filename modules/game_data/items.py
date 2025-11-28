# modules/game_data/items.py
import logging

logger = logging.getLogger(__name__)

ITEMS_DATA = {}
MARKET_ITEMS = {} 

ITEMS_DATA.update({
    
    # --- CONSUMÍVEIS BÁSICOS ---
    "frasco_com_agua": {
        "display_name": "Frasco com Água", "emoji": "💧", "type": "reagent",
        "description": "A base para a maioria das poções.", "stackable": True
    },
    "folha_sombria": {
        "display_name": "Folha Sombria", "emoji": "🌿", "type": "reagent",
        "description": "Erva curativa da Floresta Sombria.", "stackable": True
    },
    "geleia_slime": {
        "display_name": "Geleia de Slime", "emoji": "🟢", "type": "reagent",
        "description": "Substância viscosa vital.", "stackable": True
    },
    "pocao_cura_leve": {
        "display_name": "Poção de Cura Leve", "emoji": "❤️", "type": "potion",
        "category": "consumivel", "description": "Recupera 50 HP.",
        "stackable": True, "effects": {"heal": 50}
    },
    "pocao_cura_media": {
        "display_name": "Poção de Cura Média", "emoji": "❤️‍🩹", "type": "potion",
        "category": "consumivel", "description": "Recupera 150 HP.",
        "stackable": True, "effects": {"heal": 150}
    },
    "pocao_energia_fraca": {
        "display_name": "Poção de Energia Fraca", "emoji": "⚡️", "type": "potion",
        "category": "consumivel", "description": "Recupera 10 Energia.",
        "stackable": True, "effects": {"add_energy": 10}
    },
    "frasco_sabedoria": {
        "display_name": "Frasco de Sabedoria", "emoji": "🧠", "type": "potion",
        "category": "consumivel", "description": "Concede 500 XP.",
        "stackable": True, "effects": {"add_xp": 500}
    },
    "cristal_mana_bruto": {
        "display_name": "Cristal de Mana Bruto", "emoji": "💎",
        "type": "reagent", "category": "consumivel",
        "description": "Fragmento cristalino, essencial para poções de Mana.",
        "stackable": True
    },
    "raiz_da_fortuna": {
        "display_name": "Raiz da Fortuna", "emoji": "🍀",
        "type": "reagent", "category": "consumivel",
        "description": "Raiz rara que concentra a energia da sorte.",
        "stackable": True
    },
    "po_de_iniciativa": {
        "display_name": "Pó de Iniciativa", "emoji": "💨",
        "type": "reagent", "category": "consumivel",
        "description": "Pó cintilante que confere agilidade e rapidez.",
        "stackable": True
    },
    "essencia_purificadora": {
        "display_name": "Essência Purificadora", "emoji": "✨",
        "type": "reagent", "category": "consumivel",
        "description": "Líquido etéreo, usado em poções de resistência e purificação.",
        "stackable": True
    },

    # --- EVENTOS E CHAVES ---
    "fragmento_bravura": {
        "display_name": "Fragmento de Bravura", "emoji": "🏅", 
        "type": "especial", "category": "evento", 
        "description": "Obtido ao defender o reino.", 
        "stackable": True
    },
    "ticket_defesa_reino": {
        "display_name": "Ticket de Defesa", "emoji": "🎟️", 
        "type": "event_ticket", "category": "evento", 
        "description": "Entrada para Defesa do Reino.", 
        "stackable": True
    },
    "ticket_arena": {
        "display_name": "Entrada da Arena", "emoji": "🎟️", 
        "type": "event_ticket", "category": "evento", 
        "description": "Entrada extra para Arena PvP.", 
        "stackable": True,
        "on_use": {"effect": "add_pvp_entries", "value": 1}
    },
    "chave_da_catacumba": {
        "display_name": "Chave da Catacumba", "emoji": "🗝", 
        "type": "especial", "category": "especial", 
        "description": "Abre a Catacumba do Reino.", 
        "stackable": True
    },
    "cristal_de_abertura": {
        "display_name": "Cristal de Abertura", "emoji": "🔹", 
        "type": "especial", "category": "especial", 
        "description": "Chave arcana para Dungeons.", 
        "stackable": True
    },

    # --- MATERIAIS BÁSICOS ---
    "madeira": {
        "display_name": "Madeira", "emoji": "🪵", 
        "type": "material_bruto", "category": "coletavel", 
        "stackable": True
    },
    "pedra": {
        "display_name": "Pedra", "emoji": "🪨", 
        "type": "material_bruto", "category": "coletavel", 
        "stackable": True
    },
    "minerio_de_ferro": {
        "display_name": "Mɪɴᴇ́ʀɪᴏ ᴅᴇ Fᴇʀʀᴏ", "emoji": "⛏️",
        "type": "material_bruto", "category": "coletavel",
        "description": "Minério metálico que pode ser fundido.",
        "stackable": True,
        "media_key": "imagem_minerio_de_ferro",
    },
    "linho": {
        "display_name": "Lɪɴʜᴏ", "emoji": "🌿",
        "type": "material_bruto", "category": "coletavel",
        "description": "Fibras vegetais base para tecelagem.",
        "stackable": True,
        "media_key": "imagem_linho",
    },
    "pena": {
        "display_name": "Pᴇɴᴀ", "emoji": "🪶",
        "type": "material_monstro", "category": "coletavel",
        "description": "Pena leve, útil para flechas e ornamentos.",
        "stackable": True,
        "media_key": "imagem_pena",
    },
    "sangue": {
        "display_name": "Sᴀɴɢᴜᴇ", "emoji": "🩸",
        "type": "material_monstro", "category": "coletavel",
        "description": "Amostra de sangue para poções e rituais.",
        "stackable": True,
        "media_key": "imagem_sangue",
    },
    "minerio_estanho": {
        "display_name": "Mɪɴᴇ́ʀɪᴏ ᴅᴇ Esᴛᴀɴʜᴏ", "emoji": "🪙",
        "type": "material_bruto", "category": "cacada",
        "description": "Metal macio, excelente para ligas (ex.: bronze).",
        "stackable": True,
        "media_key": "item_minerio_stanho"
    },
    "minerio_de_prata": {
        "display_name": "Minerio de Prata", "emoji": "⛏️🪙",
        "type": "material_bruto", "category": "coletavel",
        "description": "Minério metálico que pode ser fundido.",
        "stackable": True,
        "media_key": "imagem_minerio_de_prata",
    },
    
    # --- CAÇADA & DROPS ---
    "madeira_rara": {
        "display_name": "Mᴀᴅᴇɪʀᴀ Rᴀʀᴀ", "emoji": "🪵☦️",
        "type": "material_bruto", "category": "cacada",
        "description": "Madeira de árvore antiga, resistente e flexível.",
        "stackable": True,
        "media_key": "item_madeira_rara",
    },
    "cera_de_abelha": {
        "display_name": "Cera de Abelha", "emoji": "🍯",
        "type": "material_bruto", "category": "coletavel",
        "description": "Cera natural, usada para selar pergaminhos.",
        "stackable": True,
        "media_key": "item_cera_de_abelha"
    },
    "oleo_mineral": {
        "display_name": "Óleo Mineral", "emoji": "🧪",
        "type": "reagent", "category": "consumivel",
        "description": "Óleo base inerte, essencial em alquimia.",
        "stackable": True,
        "media_key": "item_oleo_mineral"
    },
    "gema_bruta": {
        "display_name": "Gᴇᴍᴀ Bʀᴜᴛᴀ", "emoji": "💎",
        "type": "material_bruto", "category": "cacada",
        "description": "Pedra preciosa sem lapidação.",
        "stackable": True,
        "media_key": "item_gema_bruta"
    },
    "pano_simples": {
        "display_name": "Pᴇᴅᴀᴄ̧ᴏ ᴅᴇ Pᴀɴᴏ", "emoji": "🧣",
        "type": "material_monstro", "category": "cacada",
        "description": "Retalho comum, cai de criaturas humanoides.",
        "stackable": True,
        "media_key": "item_pano_simples"
    },
    "esporo_de_cogumelo": {
        "display_name": "Esᴘᴏʀᴏ ᴅᴇ Cᴏɢᴜᴍᴇʟᴏ", "emoji": "🍄",
        "type": "material_monstro", "category": "cacada",
        "description": "Base alquímica vinda de cogumelos gigantes.",
        "stackable": True,
        "media_key": "item_esporo_de_cogumelo"
    },
    "couro_de_lobo": {
        "display_name": "Cᴏᴜʀᴏ ᴅᴇ Lᴏʙᴏ", "emoji": "🐺",
        "type": "material_monstro", "category": "cacada",
        "description": "Pele de lobo comum para armaduras leves.",
        "stackable": True,
        "media_key": "item_couro_de_lobo"
    },
    "couro_de_lobo_alfa": {
        "display_name": "Cᴏᴜʀᴏ ᴅᴇ Lᴏʙᴏ Aʟғᴀ", "emoji": "🟤🐺",
        "type": "material_monstro", "category": "cacada",
        "description": "Pele espessa e rara de um lobo alfa.",
        "stackable": True,
        "media_key": "item_couro_de_lobo_alfa"
    },
    "seiva_de_ent": {
        "display_name": "Sᴇɪᴠᴀ ᴅᴇ Eɴᴛ", "emoji": "🌳",
        "type": "material_monstro", "category": "cacada",
        "description": "Seiva dourada de uma criatura ancestral.",
        "stackable": True,
        "media_key": "item_seiva_de_ent"
    },
    "ectoplasma": {
        "display_name": "Eᴄᴛᴏᴘʟᴀsᴍᴀ", "emoji": "👻",
        "type": "material_monstro", "category": "cacada",
        "description": "Resíduo etéreo de aparições.",
        "stackable": True,
        "media_key": "item_ectoplasma"
    },
    "joia_da_criacao": {
        "display_name": "Jᴏɪᴀ ᴅᴀ Cʀɪᴀᴄ̧ᴀ̃ᴏ", "emoji": "🔷",
        "type": "material_magico", "category": "consumivel",
        "description": "Gema rara com energia criadora.",
        "stackable": True,
        "media_key": "item_joia_da_criacao"
    },
    "presa_de_javali": {
        "display_name": "Pʀᴇsᴀ ᴅᴇ Jᴀᴠᴀʟɪ", "emoji": "🦷",
        "type": "material_monstro", "category": "cacada",
        "description": "Presas afiadas, úteis em talismãs.",
        "stackable": True,
        "media_key": "item_presa_de_javali"
    },
    "carapaca_de_pedra": {
        "display_name": "Cᴀʀᴀᴘᴀᴄ̧ᴀ ᴅᴇ Pᴇᴅʀᴀ", "emoji": "🪨",
        "type": "material_monstro", "category": "cacada",
        "description": "Placas pétreas de criaturas rochosas.",
        "stackable": True,
        "media_key": "item_carapaca_de_pedra"
    },
    "nucleo_de_golem": {
        "display_name": "Nᴜ́ᴄʟᴇᴏ ᴅᴇ Gᴏʟᴇᴍ", "emoji": "🧿",
        "type": "material_magico", "category": "cacada",
        "description": "Coração animado que dá vida a um golem.",
        "stackable": True,
        "media_key": "item_nucleo_de_golem"
    },
    "escama_de_salamandra": {
        "display_name": "Esᴄᴀᴍᴀ ᴅᴇ Sᴀʟᴀᴍᴀɴᴅʀᴀ", "emoji": "🦎",
        "type": "material_monstro", "category": "cacada",
        "description": "Escamas resistentes ao calor intenso.",
        "stackable": True,
        "media_key": "item_escama_de_salamandra"
    },
    "coracao_de_magma": {
        "display_name": "Cᴏʀᴀᴄ̧ᴀ̃ᴏ ᴅᴇ Mᴀɢᴍᴀ", "emoji": "❤️‍🔥",
        "type": "material_magico", "category": "cacada",
        "description": "Núcleo ígneo que pulsa calor.",
        "stackable": True,
        "media_key": "item_coracao_de_magma"
    },
    "poeira_magica": {
        "display_name": "Pᴏᴇɪʀᴀ Mᴀ́ɢɪᴄᴀ", "emoji": "✨",
        "type": "material_magico", "category": "cacada",
        "description": "Resíduo arcano com usos variados.",
        "stackable": True,
        "media_key": "item_poeira_magica"
    },
    "olho_de_basilisco": {
        "display_name": "Oʟʜᴏ ᴅᴇ Bᴀsɪʟɪsᴄᴏ", "emoji": "👁️",
        "type": "material_magico", "category": "cacada",
        "description": "Olho petrificante, raro e perigoso.",
        "stackable": True,
        "media_key": "item_olho_de_basilisco"
    },
    "asa_de_morcego": {
        "display_name": "Asᴀ ᴅᴇ Mᴏʀᴄᴇɢᴏ", "emoji": "🦇",
        "type": "material_monstro", "category": "cacada",
        "description": "Asas membranosas, úteis em alquimia.",
        "stackable": True,
        "media_key": "item_asa_de_morcego"
    },
    "pele_de_troll": {
        "display_name": "Pᴇʟᴇ ᴅᴇ Tʀᴏʟʟ", "emoji": "🧌",
        "type": "material_monstro", "category": "cacada",
        "description": "Couro grosso com traços regenerativos.",
        "stackable": True,
        "media_key": "item_pele_de_troll"
    },
    "sangue_regenerativo": {
        "display_name": "Sᴀɴɢᴜᴇ Rᴇɢᴇɴᴇʀᴀᴛɪᴠᴏ", "emoji": "✨🩸",
        "type": "material_magico", "category": "cacada",
        "description": "Líquido denso com poder de cura.",
        "stackable": True,
        "media_key": "item_sangue_regenerativo"
    },
    "nucleo_de_magma": {
        "display_name": "Nᴜ́ᴄʟᴇᴏ ᴅᴇ Mᴀɢᴍᴀ", "emoji": "🪔",
        "type": "material_magico", "category": "cacada",
        "description": "Fragmento ardente retirado de elementais.",
        "stackable": True,
        "media_key": "item_nucleo_de_magma"
    },
    "pedra_vulcanica": {
        "display_name": "Pᴇᴅʀᴀ Vᴜʟᴄᴀ̂ɴɪᴄᴀ", "emoji": "🪨🌋",
        "type": "material_monstro", "category": "cacada",
        "description": "Rochas formadas por magma resfriado.",
        "stackable": True,
        "media_key": "item_pedra_vulcanica"
    },
    "semente_encantada": {
        "display_name": "Sᴇᴍᴇɴᴛᴇ Eɴᴄᴀɴᴛᴀᴅᴀ", "emoji": "🌱✨",
        "type": "material_magico", "category": "cacada",
        "description": "Semente viva com magia natural.",
        "stackable": True,
        "media_key": "item_semente_encantada"
    },
    "engrenagem_usada": {
        "display_name": "Eɴɢʀᴇɴᴀɢᴇᴍ Usᴀᴅᴀ", "emoji": "⚙️",
        "type": "material_monstro", "category": "cacada",
        "description": "Peça mecânica recuperada de autômatos.",
        "stackable": True,
        "media_key": "item_engrenagem_usada"
    },
    "martelo_enferrujado": {
        "display_name": "Mᴀʀᴛᴇʟᴏ Eɴғᴇʀʀᴜᴊᴀᴅᴏ", "emoji": "🔨🔸",
        "type": "sucata", "category": "cacada",
        "description": "Velho martelo, mais lembrança do que ferramenta.",
        "stackable": True,
        "media_key": "item_martelo_enferrujado"
    },
    "escama_incandescente": {
        "display_name": "Esᴄᴀᴍᴀ Iɴᴄᴀɴᴅᴇsᴄᴇɴᴛᴇ", "emoji": "🔥",
        "type": "material_monstro", "category": "cacada",
        "description": "Escama que retém calor sobrenatural.",
        "stackable": True,
        "media_key": "item_escama_incandescente"
    },
    "essencia_de_fogo": {
        "display_name": "Essᴇ̂ɴᴄɪᴀ ᴅᴇ Fᴏɢᴏ", "emoji": "♨️",
        "type": "material_magico", "category": "cacada",
        "description": "Essência elementar ardente.",
        "stackable": True,
        "media_key": "item_essencia_de_fogo"
    },
    
    # --- REFINARIA & COLETÁVEIS ---
    "barra_de_aco": {
        "display_name": "Bᴀʀʀᴀ ᴅᴇ Aᴄ̧ᴏ", "emoji": "⛓️🧱",
        "type": "material_refinado", "category": "coletavel",
        "description": "Liga metálica superior ao ferro.",
        "stackable": True,
        "value": 60,
        "media_key": "item_barra_de_aco"
    },
    "dente_afiado_superior": {
        "display_name": "Dᴇɴᴛᴇ Aғɪᴀᴅᴏ Sᴜᴘᴇʀɪᴏʀ", "emoji": "🦷",
        "type": "material_monstro", "category": "cacada",
        "description": "Dente robusto usado em forjas avançadas.",
        "stackable": True,
        "media_key": "item_dente_afiado_superior"
    },
    "ponta_de_osso_afiada": {
        "display_name": "Pᴏɴᴛᴀ ᴅᴇ Ossᴏ Aғɪᴀᴅᴀ", "emoji": "🦴",
        "type": "material_monstro", "category": "coletavel",
        "description": "Ponta de osso afiada, usada em flechas e armas.",
        "stackable": True,
        "media_key": "item_ponta_de_osso_afiada"
    },
    "veludo_runico": {
        "display_name": "Vᴇʟᴜᴅᴏ Rᴜ́ɴɪᴄᴏ", "emoji": "🧵",
        "type": "material_refinado", "category": "coletavel",
        "description": "Tecido mágico usado em trajes avançados.",
        "stackable": True,
        "media_key": "item_veludo_runico"
    },
    "rolo_seda_sombria": {
        "display_name": "Rolo de Seda Sombria", "emoji": "🌑🧵",
        "type": "material_refinado", "category": "coletavel",
        "description": "Tecido escuro e silencioso que absorve a luz.",
        "stackable": True,
        "value": 60,
        "media_key": "item_rolo_seda_sombria"
    },
    "couro_escamoso": {
        "display_name": "Couro Escamoso", "emoji": "🐊",
        "type": "material_refinado", "category": "coletavel",
        "description": "Couro com escamas, alta resistência.",
        "stackable": True,
        "value": 55,
        "media_key": "item_couro_escamoso"
    },
    "tabua_ancestral": {
        "display_name": "Tábua Ancestral", "emoji": "🌳✨",
        "type": "material_refinado", "category": "coletavel",
        "description": "Madeira infundida com magia antiga.",
        "stackable": True,
        "value": 80,
        "media_key": "item_tabua_ancestral"
    },
    "couro_reforcado": {
        "display_name": "Cᴏᴜʀᴏ Rᴇғᴏʀᴄ̧ᴀᴅᴏ", "emoji": "🐂",
        "type": "material_refinado", "category": "coletavel",
        "description": "Couro tratado para maior durabilidade.",
        "stackable": True,
        "media_key": "item_couro_reforcado"
    },    
    "pele_troll_regenerativa": {
        "display_name": "Pᴇʟᴇ ᴅᴇ Tʀᴏʟʟ Rᴇɢᴇɴᴇʀᴀᴛɪᴠᴀ", "emoji": "🧌✨🩸",
        "type": "material_refinado", "category": "coletavel",
        "description": "Pele que retém propriedades de cura.",
        "stackable": True,
        "media_key": "item_pele_troll_regenerativa"    
     },    
    "membrana_de_couro_fino": {
        "display_name": "Mᴇᴍʙʀᴀɴᴀ ᴅᴇ Cᴏᴜʀᴏ Fɪɴᴏ", "emoji": "🦇",
        "type": "material_refinado", "category": "coletavel",
        "description": "Couro finíssimo para trabalhos delicados.",
        "stackable": True,
        "media_key": "item_membrana_de_couro_fino"        
    },
    "barra_de_ferro": {
        "display_name": "Bᴀʀʀᴀ ᴅᴇ Fᴇʀʀᴏ", "emoji": "🧱",
        "type": "material_refinado", "category": "coletavel",
        "description": "Barra metálica básica.",
        "stackable": True,
        "media_key": "item_barra_de_ferro"
    },
    "barra_de_prata": {
        "display_name": "Bᴀʀʀᴀ ᴅᴇ Pʀᴀᴛᴀ", "emoji": "🥈",
        "type": "material_refinado", "category": "coletavel",
        "description": "Metal precioso usado em joias.",
        "stackable": True,
        "media_key": "item_barra_de_prata" 
    },
    "barra_bronze": {
        "display_name": "Bᴀʀʀᴀ ᴅᴇ Bʀᴏɴᴢᴇ", "emoji": "🟤",
        "type": "material_refinado", "category": "coletavel",
        "description": "Liga de ferro e estanho.",
        "stackable": True,
        "media_key": "item_barra_de_bronze"
    },
    "placa_de_pedra_polida": {
        "display_name": "Placa de Pedra Polida", "emoji": "🪨✨",
        "type": "material_refinado", "category": "coletavel",
        "description": "Placa de pedra lisa para construções.",
        "stackable": True,
        "media_key": "item_placa_de_pedra_polida"
    },
    "nucleo_de_energia_instavel": {
        "display_name": "Núcleo de Energia Instável", "emoji": "💥",
        "type": "material_magico", "category": "especial",
        "description": "Fonte de energia bruta e volátil.",
        "stackable": True,
        "media_key": "item_nucleo_de_energia_instavel"
    },
    "placa_draconica_negra": {
        "display_name": "Placa Dracônica Negra", "emoji": "🐉🌑",
        "type": "material_monstro", "category": "cacada",
        "description": "Escama de dragão sombrio.",
        "stackable": True,
        "value": 500,
        "media_key": "item_placa_draconica_negra"
    },
    "essencia_espiritual": {
        "display_name": "Essência Espiritual", "emoji": "🕊️✨",
        "type": "material_magico", "category": "evolucao",
        "description": "Substância etérea de pureza.",
        "stackable": True,
        "value": 300,
        "media_key": "item_essencia_espiritual"
    },
    "couro_curtido": {
        "display_name": "Cᴏᴜʀᴏ Cᴜʀᴛɪᴅᴏ", "emoji": "🐑",
        "type": "material_refinado", "category": "coletavel",
        "description": "Couro tratado básico.",
        "stackable": True,
        "media_key": "item_couro_curtido"
    },
    "rolo_de_pano_simples": {
        "display_name": "Rᴏʟᴏ ᴅᴇ Pᴀɴᴏ Sɪᴍᴘʟᴇs", "emoji": "🪢",
        "type": "material_refinado", "category": "coletavel",
        "description": "Tecido básico preparado.",
        "stackable": True,
        "media_key": "item_rolo_de_pano_simples"
    },
    "gema_polida": { 
        "display_name": "Gᴇᴍᴀ Pᴏʟɪᴅᴀ", "emoji": "🔷",
        "type": "material_refinado", "category": "coletavel",
        "description": "Gema lapidada para joias.",
        "stackable": True,
        "media_key": "item_gema_polida"
    },
    "gema_lapidada_comum": {
       "display_name": "Gema lapidada comum", "emoji": "🔷⚒️",
        "type": "material_refinado", "category": "coletavel",
        "description": "Gema lapidada comum.",
        "stackable": True,
        "media_key": "item_gema_polida"  
    },
    "dente_afiado": {
        "display_name": "Dᴇɴᴛᴇ Aғɪᴀᴅᴏ", "emoji": "🦷",
        "type": "material_monstro", "category": "cacada",
        "description": "Dente afiado comum.",
        "stackable": True,
        "media_key": "item_dente_afiado"
    },
    "fragmento_gargula": {
        "display_name": "Fʀᴀɢᴍᴇɴᴛᴏ ᴅᴇ Gᴀ́ʀɢᴜʟᴀ", "emoji": "🪨",
        "type": "material_monstro", "category": "cacada",
        "description": "Estilhaço pétreo sombrio.",
        "stackable": True,
        "media_key": "item_fragmento_gargula"
    },
    "fio_de_prata": {
        "display_name": "Fɪᴏ ᴅᴇ Pʀᴀᴛᴀ", "emoji": "🪡",
        "type": "material_refinado", "category": "coletavel",
        "description": "Fio de prata maleável.",
        "stackable": True,
        "media_key": "item_fio_de_prata"
    },
    "lente_petrificante": {
        "display_name": "Lente Petrificante", "emoji": "👁️🐍",
        "type": "material_refinado", "category": "coletavel",
        "description": "Joia petrificada de basilisco.",
        "stackable": True,
        "media_key": "item_fio_de_prata" # Atenção aqui: chave repetida no original, mantida mas cuidado
    },
    "essencia_fungica": {
        "display_name": "Essência Fúngica", "emoji": "🍄🧪",
        "type": "material_monstro", "category": "cacada",
        "description": "Líquido viscoso de fungos.",
        "stackable": True,
        "value": 150,
        "media_key": "item_essencia_fungica"
    },
    "essencia_draconica_pura": {
        "display_name": "Essência Dracônica Pura", "emoji": "🐉✨",
        "type": "material_magico", "category": "especial",
        "description": "Forma pura de energia dracônica.",
        "stackable": True,
        "value": 1500,
        "media_key": "item_essencia_draconica_pura"
    },
    "tabua_de_madeira_rara": {
        "display_name": "Tábua de Madeira Rara", "emoji": "🪵✨",
        "type": "material_refinado", "category": "coletavel",
        "description": "Madeira rara tratada.",
        "stackable": True,
        "value": 50,
        "media_key": "item_tabua_de_madeira_rara"
    },

    # --- ESPECIAIS / CONSUMÍVEIS ---
    "pedra_do_aprimoramento": {
        "display_name": "Pedra de Aprimoramento", "emoji": "✨", 
        "type": "consumivel", "category": "consumivel", 
        "stackable": True, "value": 300
    },
    "pergaminho_durabilidade": {
        "display_name": "Pergaminho de Durabilidade", "emoji": "📜", 
        "type": "consumivel", "category": "consumivel", 
        "stackable": True, "value": 150
    },
    "nucleo_forja_comum": {
        "display_name": "Núcleo de Forja Comum", "emoji": "🔥", 
        "type": "material", "category": "consumivel", 
        "stackable": True, "value": 150
    },
    "nucleo_forja_fraco": {
        "display_name": "Núcleo de Forja Fraco", "emoji": "🔥", 
        "type": "material", "category": "consumivel", 
        "stackable": True, "value": 40
    },
    "gems": {
        "display_name": "Diamante", "emoji": "💎", 
        "type": "currency", "stackable": True, 
        "description": "Moeda premium."
    },
    "seiva_escura": {
        "display_name": "Seiva Escura", "emoji": "🩸", 
        "type": "consumivel", "category": "buff",
        "description": "+10 Vida Máxima por 60 min.", "stackable": True,
        "on_use": {"effect_id": "buff_hp_flat", "value": 10, "duration_sec": 3600}
    }
})

# ============================================================
# 3. EQUIPAMENTOS (T1 e T2)
# ============================================================
ITEMS_DATA.update({
    # --- GUERREIRO ---
    "espada_ferro_guerreiro": {
        "display_name": "Espada de Ferro", "emoji": "🗡️",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "description": "Espada confiável de ferro.",
        "media_key": "item_espada_ferro_guerreiro", "class_req": ["guerreiro"]
    },
    "elmo_ferro_guerreiro": {
        "display_name": "Elmo de Ferro", "emoji": "🪖",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "media_key": "item_elmo_ferro_guerreiro", "class_req": ["guerreiro"]
    },
    "peitoral_ferro_guerreiro": {
        "display_name": "Peitoral de Ferro", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "media_key": "item_peitoral_ferro_guerreiro", "class_req": ["guerreiro"]
    },
    "calcas_ferro_guerreiro": {
        "display_name": "Calças de Ferro", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "media_key": "item_calcas_ferro_guerreiro", "class_req": ["guerreiro"]
    },
    "botas_ferro_guerreiro": {
        "display_name": "Botas de Ferro", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "media_key": "item_botas_ferro_guerreiro", "class_req": ["guerreiro"]
    },
    "luvas_ferro_guerreiro": {
        "display_name": "Luvas de Ferro", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "media_key": "item_luvas_ferro_guerreiro", "class_req": ["guerreiro"]
    },
    "anel_ferro_guerreiro": {
        "display_name": "Anel de Ferro", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "media_key": "item_anel_ferro_guerreiro", "class_req": ["guerreiro"]
    },
    "colar_ferro_guerreiro": {
        "display_name": "Colar de Ferro", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "media_key": "item_colar_ferro_guerreiro", "class_req": ["guerreiro"]
    },
    "brinco_ferro_guerreiro": {
        "display_name": "Brinco de Ferro", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "media_key": "item_brinco_ferro_guerreiro", "class_req": ["guerreiro"]
    },

    # Guerreiro T2
    "espada_aco_guerreiro": {
        "display_name": "Espada de Aço", "emoji": "🗡️",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "media_key": "item_espada_aco_guerreiro", "class_req": ["guerreiro"]
    },
    "elmo_aco_guerreiro": {
        "display_name": "Elmo de Aço", "emoji": "🪖",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "media_key": "item_elmo_aco_guerreiro", "class_req": ["guerreiro"]
    },
    "peitoral_aco_guerreiro": {
        "display_name": "Peitoral de Aço", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "media_key": "item_peitoral_aco_guerreiro", "class_req": ["guerreiro"]
    },
    "calcas_aco_guerreiro": {
        "display_name": "Calças de Aço", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "media_key": "item_calcas_aco_guerreiro", "class_req": ["guerreiro"]
    },
    "botas_aco_guerreiro": {
        "display_name": "Botas de Aço", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "media_key": "item_botas_aco_guerreiro", "class_req": ["guerreiro"]
    },
    "luvas_aco_guerreiro": {
        "display_name": "Luvas de Aço", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "media_key": "item_luvas_aco_guerreiro", "class_req": ["guerreiro"]
    },
    "anel_aco_guerreiro": {
        "display_name": "Anel de Aço", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "media_key": "item_anel_aco_guerreiro", "class_req": ["guerreiro"]
    },
    "colar_aco_guerreiro": {
        "display_name": "Colar de Aço", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "media_key": "item_colar_aco_guerreiro", "class_req": ["guerreiro"]
    },
    "brinco_aco_guerreiro": {
        "display_name": "Brinco de Aço", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "media_key": "item_brinco_aco_guerreiro", "class_req": ["guerreiro"]
    },

    # --- MAGO ---
    "cajado_aprendiz_mago": {
        "display_name": "Cajado de Aprendiz", "emoji": "🪄",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "media_key": "item_cajado_aprendiz_mago", "class_req": ["mago"]
    },
    "chapeu_seda_mago": {
        "display_name": "Chapéu de Seda", "emoji": "🎩",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "media_key": "item_chapeu_seda_mago", "class_req": ["mago"]
    },
    "tunica_seda_mago": {
        "display_name": "Túnica de Seda", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "media_key": "item_tunica_seda_mago", "class_req": ["mago"]
    },
    "calcas_seda_mago": {
        "display_name": "Calças de Seda", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "media_key": "item_calcas_seda_mago", "class_req": ["mago"]
    },
    "botas_seda_mago": {
        "display_name": "Botas de Seda", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "media_key": "item_botas_seda_mago", "class_req": ["mago"]
    },
    "luvas_seda_mago": {
        "display_name": "Luvas de Seda", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "media_key": "item_luvas_seda_mago", "class_req": ["mago"]
    },
    "anel_gema_mago": {
        "display_name": "Anel de Gema", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "media_key": "item_anel_gema_mago", "class_req": ["mago"]
    },
    "colar_gema_mago": {
        "display_name": "Colar de Gema", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "media_key": "item_colar_gema_mago", "class_req": ["mago"]
    },
    "brinco_gema_mago": {
        "display_name": "Brinco de Gema", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "media_key": "item_brinco_gema_mago", "class_req": ["mago"]
    },
    # Mago T2
    "cajado_arcano_mago": {
        "display_name": "Cajado Arcano", "emoji": "🪄",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "media_key": "item_cajado_arcano_mago", "class_req": ["mago"]
    },
    "chapeu_veludo_mago": {
        "display_name": "Chapéu de Veludo", "emoji": "🎩",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "media_key": "item_chapeu_veludo_mago", "class_req": ["mago"]
    },
    "tunica_veludo_mago": {
        "display_name": "Túnica de Veludo", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "media_key": "item_tunica_veludo_mago", "class_req": ["mago"]
    },
    "calcas_veludo_mago": {
        "display_name": "Calças de Veludo", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "media_key": "item_calca_veludo_mago", "class_req": ["mago"]
    },
    "botas_veludo_mago": {
        "display_name": "Botas de Veludo", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "media_key": "item_botas_veludo_mago", "class_req": ["mago"]
    },
    "luvas_veludo_mago": {
        "display_name": "Luvas de Veludo", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "media_key": "item_luvas_veludo_mago", "class_req": ["mago"]
    },
    "anel_runico_mago": {
        "display_name": "Anel Rúnico", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "media_key": "item_anel_runico_mago", "class_req": ["mago"]
    },
    "colar_runico_mago": {
        "display_name": "Colar Rúnico", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "media_key": "item_colar_runico_mago", "class_req": ["mago"]
    },
    "brinco_runico_mago": {
        "display_name": "Brinco Rúnico", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "media_key": "item_brinco_runico_mago", "class_req": ["mago"]
    },

    # --- BERSERKER ---
    "machado_rustico_berserker": {
        "display_name": "Machado Rústico", "emoji": "🪓",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "media_key": "item_machado_rustico_berserker", "class_req": ["berserker"]
    },
    "elmo_chifres_berserker": {
        "display_name": "Elmo de Chifres", "emoji": "🪖",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "media_key": "item_elmo_chifres_berserker", "class_req": ["berserker"]
    },
    "peitoral_placas_berserker": {
        "display_name": "Peitoral de Placas", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "media_key": "item_peitoral_placas_berserker", "class_req": ["berserker"]
    },
    "calcas_placas_berserker": {
        "display_name": "Calças de Placas", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "media_key": "item_calcas_placas_berserker", "class_req": ["berserker"]
    },
    "botas_couro_berserker": {
        "display_name": "Botas de Couro", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "media_key": "item_botas_couro_berserker", "class_req": ["berserker"]
    },
    "luvas_couro_berserker": {
        "display_name": "Luvas de Couro", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "media_key": "item_luvas_couro_berserker", "class_req": ["berserker"]
    },
    "anel_osso_berserker": {
        "display_name": "Anel de Osso", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "media_key": "item_anel_osso_berserker", "class_req": ["berserker"]
    },
    "colar_presas_berserker": {
        "display_name": "Colar de Presas", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "media_key": "item_colar_presas_berserker", "class_req": ["berserker"]
    },
    "brinco_osso_berserker": {
        "display_name": "Brinco de Osso", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "media_key": "item_brinco_osso_berserker", "class_req": ["berserker"]
    },
    # Berserker T2
    "machado_aco_berserker": {
        "display_name": "Machado de Aço", "emoji": "🪓",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "media_key": "item_machado_aco_berserker", "class_req": ["berserker"]
    },
    "elmo_troll_berserker": {
        "display_name": "Elmo de Pele de Troll", "emoji": "🪖",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "media_key": "item_elmo_troll_berserker", "class_req": ["berserker"]
    },
    "peitoral_troll_berserker": {
        "display_name": "Peitoral de Pele de Troll", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "media_key": "item_peitoral_troll_berserker", "class_req": ["berserker"]
    },
    "calcas_troll_berserker": {
        "display_name": "Calças de Pele de Troll", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "media_key": "item_calcas_troll_berserker", "class_req": ["berserker"]
    },
    "botas_troll_berserker": {
        "display_name": "Botas de Pele de Troll", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "media_key": "item_botas_troll_berserker", "class_req": ["berserker"]
    },
    "luvas_troll_berserker": {
        "display_name": "Luvas de Pele de Troll", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "media_key": "item_luvas_troll_berserker", "class_req": ["berserker"]
    },
    "anel_troll_berserker": {
        "display_name": "Anel de Troll", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "media_key": "item_anel_troll_berserker", "class_req": ["berserker"]
    },
    "colar_troll_berserker": {
        "display_name": "Colar de Troll", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "media_key": "item_colar_troll_berserker", "class_req": ["berserker"]
    },
    "brinco_troll_berserker": {
        "display_name": "Brinco de Troll", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "media_key": "item_brinco_troll_berserker", "class_req": ["berserker"]
    },

    # --- CAÇADOR ---
    "arco_batedor_cacador": {
        "display_name": "Arco de Batedor", "emoji": "🏹",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "media_key": "item_arco_batedor_cacador", "class_req": ["cacador"]
    },
    "capuz_batedor_cacador": {
        "display_name": "Capuz de Batedor", "emoji": "🪖",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "media_key": "item_capuz_batedor_cacador", "class_req": ["cacador"]
    },
    "peitoral_batedor_cacador": {
        "display_name": "Peitoral de Batedor", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "media_key": "item_peitoral_batedor_cacador", "class_req": ["cacador"]
    },
    "calcas_batedor_cacador": {
        "display_name": "Calças de Batedor", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "media_key": "item_calcas_batedor_cacador", "class_req": ["cacador"]
    },
    "botas_batedor_cacador": {
        "display_name": "Botas de Batedor", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "media_key": "item_botas_batedor_cacador", "class_req": ["cacador"]
    },
    "luvas_batedor_cacador": {
        "display_name": "Luvas de Batedor", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "media_key": "item_luvas_batedor_cacador", "class_req": ["cacador"]
    },
    "anel_batedor_cacador": {
        "display_name": "Anel de Batedor", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "media_key": "item_anel_batedor_cacador", "class_req": ["cacador"]
    },
    "colar_batedor_cacador": {
        "display_name": "Colar de Batedor", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "media_key": "item_colar_batedor_cacador", "class_req": ["cacador"]
    },
    "brinco_batedor_cacador": {
        "display_name": "Brinco de Batedor", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "media_key": "item_brinco_batedor_cacador", "class_req": ["cacador"]
    },
    # Caçador T2
    "arco_patrulheiro_cacador": {
        "display_name": "Arco de Patrulheiro", "emoji": "🏹",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "media_key": "item_arco_patrulheiro_cacador", "class_req": ["cacador"]
    },
    "capuz_patrulheiro_cacador": {
        "display_name": "Capuz de Patrulheiro", "emoji": "🪖",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "media_key": "item_capuz_patrulheiro_cacador", "class_req": ["cacador"]
    },
    "peitoral_patrulheiro_cacador": {
        "display_name": "Peitoral de Patrulheiro", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "media_key": "item_peitoral_patrulheiro_cacador", "class_req": ["cacador"]
    },
    "calcas_patrulheiro_cacador": {
        "display_name": "Calças de Patrulheiro", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "media_key": "item_calcas_patrulheiro_cacador", "class_req": ["cacador"]
    },
    "botas_patrulheiro_cacador": {
        "display_name": "Botas de Patrulheiro", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "media_key": "item_botas_patrulheiro_cacador", "class_req": ["cacador"]
    },
    "luvas_patrulheiro_cacador": {
        "display_name": "Luvas de Patrulheiro", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "media_key": "item_luvas_patrulheiro_cacador", "class_req": ["cacador"]
    },
    "anel_patrulheiro_cacador": {
        "display_name": "Anel de Patrulheiro", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "media_key": "item_anel_patrulheiro_cacador", "class_req": ["cacador"]
    },
    "colar_patrulheiro_cacador": {
        "display_name": "Colar de Patrulheiro", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "media_key": "item_colar_patrulheiro_cacador", "class_req": ["cacador"]
    },
    "brinco_patrulheiro_cacador": {
        "display_name": "Brinco de Patrulheiro", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "media_key": "item_brinco_patrulheiro_cacador", "class_req": ["cacador"]
    },

    # --- ASSASSINO ---
    "adaga_sorrateira_assassino": {
        "display_name": "Adaga Sorrateira", "emoji": "🔪",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "media_key": "item_adaga_sorrateira_assassino", "class_req": ["assassino"]
    },
    "mascara_sorrateira_assassino": {
        "display_name": "Máscara Sorrateira", "emoji": "🪖",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "media_key": "item_mascara_sorrateira_assassino", "class_req": ["assassino"]
    },
    "couraca_sorrateira_assassino": {
        "display_name": "Couraça Sorrateira", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "media_key": "item_couraca_sorrateira_assassino", "class_req": ["assassino"]
    },
    "calcas_sorrateiras_assassino": {
        "display_name": "Calças Sorrateiras", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "media_key": "item_calcas_sorrateira_assassino", "class_req": ["assassino"]
    },
    "botas_sorrateiras_assassino": {
        "display_name": "Botas Sorrateiras", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "media_key": "item_bota_sorrateira_assassino", "class_req": ["assassino"]
    },
    "luvas_sorrateiras_assassino": {
        "display_name": "Luvas Sorrateiras", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "media_key": "item_luvas_sorrateiras_assassino", "class_req": ["assassino"]
    },
    "anel_sorrateiro_assassino": {
        "display_name": "Anel Sorrateiro", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "media_key": "item_anel_sorrateiro_assassino", "class_req": ["assassino"]
    },
    "colar_sorrateiro_assassino": {
        "display_name": "Colar Sorrateiro", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "media_key": "item_colar_sorrateiro_assassino", "class_req": ["assassino"]
    },
    "brinco_sorrateiro_assassino": {
        "display_name": "Brinco Sorrateiro", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "media_key": "item_brinco_sorrateiro_assassino", "class_req": ["assassino"]
    },
    # Assassino T2
    "adaga_sombra_assassino": {
        "display_name": "Adaga da Sombra", "emoji": "🔪",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "media_key": "item_adaga_sombra_assassino", "class_req": ["assassino"]
    },
    "mascara_sombra_assassino": {
        "display_name": "Máscara da Sombra", "emoji": "🪖",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "media_key": "item_mascara_sombra_assassino", "class_req": ["assassino"]
    },
    "couraca_sombra_assassino": {
        "display_name": "Couraça da Sombra", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "media_key": "item_couraca_sombra_assassino", "class_req": ["assassino"]
    },
    "calcas_sombra_assassino": {
        "display_name": "Calças da Sombra", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "media_key": "item_calcas_sombra_assassino", "class_req": ["assassino"]
    },
    "botas_sombra_assassino": {
        "display_name": "Botas da Sombra", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "media_key": "item_botas_sombra_assassino", "class_req": ["assassino"]
    },
    "luvas_sombra_assassino": {
        "display_name": "Luvas da Sombra", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "media_key": "item_luvas_sombra_assassino", "class_req": ["assassino"]
    },
    "anel_sombra_assassino": {
        "display_name": "Anel da Sombra", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "media_key": "item_anel_sombra_assassino", "class_req": ["assassino"]
    },
    "colar_sombra_assassino": {
        "display_name": "Colar da Sombra", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "media_key": "item_colar_sombra_assassino", "class_req": ["assassino"]
    },
    "brinco_sombra_assassino": {
        "display_name": "Brinco da Sombra", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "media_key": "item_brinco_sombra_assassino", "class_req": ["assassino"]
    },

    # --- MONGE ---
    "manoplas_iniciado_monge": {
        "display_name": "Manoplas de Iniciado", "emoji": "🤜",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "media_key": "item_manoplas_iniciado_monge", "class_req": ["monge"]
    },
    "bandana_iniciado_monge": {
        "display_name": "Bandana de Iniciado", "emoji": "🪖",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "media_key": "item_bandana_iniciado_monge", "class_req": ["monge"]
    },
    "gi_iniciado_monge": {
        "display_name": "Gi de Iniciado", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "media_key": "item_gi_iniciado_monge", "class_req": ["monge"]
    },
    "calcas_iniciado_monge": {
        "display_name": "Calças de Iniciado", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "media_key": "item_calcas_iniciado_monge", "class_req": ["monge"]
    },
    "sandalias_iniciado_monge": {
        "display_name": "Sandálias de Iniciado", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "media_key": "item_sandalias_iniciado_monge", "class_req": ["monge"]
    },
    "faixas_iniciado_monge": {
        "display_name": "Faixas de Iniciado", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "media_key": "item_faixas_iniciado_monge", "class_req": ["monge"]
    },
    "anel_iniciado_monge": {
        "display_name": "Anel de Iniciado", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "media_key": "item_anel_iniciado_monge", "class_req": ["monge"]
    },
    "colar_iniciado_monge": {
        "display_name": "Colar de Iniciado", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "media_key": "item_colar_iniciado_monge", "class_req": ["monge"]
    },
    "brinco_iniciado_monge": {
        "display_name": "Brinco de Iniciado", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "media_key": "item_brinco_iniciado_monge", "class_req": ["monge"]
    },
    # Monge T2
    "manoplas_mestre_monge": {
        "display_name": "Manoplas de Mestre", "emoji": "🤜",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "media_key": "item_manoplas_mestre_monge", "class_req": ["monge"]
    },
    "bandana_mestre_monge": {
        "display_name": "Bandana de Mestre", "emoji": "🪖",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "media_key": "item_bandana_mestre_monge", "class_req": ["monge"]
    },
    "gi_mestre_monge": {
        "display_name": "Gi de Mestre", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "media_key": "item_gi_mestre_monge", "class_req": ["monge"]
    },
    "calcas_mestre_monge": {
        "display_name": "Calças de Mestre", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "media_key": "item_calcas_mestre_monge", "class_req": ["monge"]
    },
    "sandalias_mestre_monge": {
        "display_name": "Sandálias de Mestre", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "media_key": "item_sandalias_mestre_monge", "class_req": ["monge"]
    },
    "faixas_mestre_monge": {
        "display_name": "Faixas de Mão de Mestre", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "media_key": "item_faixas_mestre_monge", "class_req": ["monge"]
    },
    "anel_mestre_monge": {
        "display_name": "Anel de Mestre", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "media_key": "item_anel_mestre_monge", "class_req": ["monge"]
    },
    "colar_mestre_monge": {
        "display_name": "Colar de Mestre", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "media_key": "item_colar_mestre_monge", "class_req": ["monge"]
    },
    "brinco_mestre_monge": {
        "display_name": "Brinco de Mestre", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "media_key": "item_brincos_mestre_monge", "class_req": ["monge"]
    },

    # --- BARDO ---
    "alaude_simples_bardo": {
        "display_name": "Alaúde Simples", "emoji": "🎻",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "media_key": "item_alaude_simples_bardo", "class_req": ["bardo"]
    },
    "chapeu_elegante_bardo": {
        "display_name": "Chapéu Elegante", "emoji": "🎩",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "media_key": "item_chapeu_elegante_bardo", "class_req": ["bardo"]
    },
    "colete_viajante_bardo": {
        "display_name": "Colete de Viajante", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "media_key": "item_colete_viajante_bardo", "class_req": ["bardo"]
    },
    "calcas_linho_bardo": {
        "display_name": "Calças de Linho", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "media_key": "item_calcas_linho_bardo", "class_req": ["bardo"]
    },
    "botas_macias_bardo": {
        "display_name": "Botas Macias", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "media_key": "item_botas_macias_bardo", "class_req": ["bardo"]
    },
    "luvas_sem_dedos_bardo": {
        "display_name": "Luvas sem Dedos", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "media_key": "item_luvas_sem_dedos_bardo", "class_req": ["bardo"]
    },
    "anel_melodico_bardo": {
        "display_name": "Anel Melódico", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "media_key": "item_anel_melodico_bardo", "class_req": ["bardo"]
    },
    "colar_melodico_bardo": {
        "display_name": "Colar Melódico", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "media_key": "item_colar_melodico_bardo", "class_req": ["bardo"]
    },
    "brinco_melodico_bardo": {
        "display_name": "Brinco Melódico", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "media_key": "item_brinco_melodico_bardo", "class_req": ["bardo"]
    },
    # Bardo T2
    "alaude_ornamentado_bardo": {
        "display_name": "Alaúde Ornamentado", "emoji": "🎻",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "media_key": "item_alaude_ornamentado_bardo", "class_req": ["bardo"]
    },
    "chapeu_emplumado_bardo": {
        "display_name": "Chapéu Emplumado", "emoji": "🎩",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "media_key": "item_chapeu_emplumado_bardo", "class_req": ["bardo"]
    },
    "casaco_veludo_bardo": {
        "display_name": "Casaco de Veludo", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "media_key": "item_casaco_veludo_bardo", "class_req": ["bardo"]
    },
    "calcas_veludo_bardo": {
        "display_name": "Calças de Veludo", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "media_key": "item_calca_veludo_bardo", "class_req": ["bardo"]
    },
    "botas_veludo_bardo": {
        "display_name": "Botas de Veludo", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "media_key": "item_botas_veludo_bardo", "class_req": ["bardo"]
    },
    "luvas_veludo_bardo": {
        "display_name": "Luvas de Veludo", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "media_key": "item_luvas_veludo_bardo", "class_req": ["bardo"]
    },
    "anel_prata_bardo": {
        "display_name": "Anel de Prata", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "media_key": "item_anel_prata_bardo", "class_req": ["bardo"]
    },
    "colar_prata_bardo": {
        "display_name": "Colar de Prata", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "media_key": "item_colar_prata_bardo", "class_req": ["bardo"]
    },
    "brinco_prata_bardo": {
        "display_name": "Brinco de Prata", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "media_key": "item_brinco_prata_bardo", "class_req": ["bardo"]
    },

    # --- SAMURAI ---
    "katana_laminada_samurai": {
        "display_name": "Katana Laminada", "emoji": "⚔️",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "media_key": "item_katana_laminada_samurai", "class_req": ["samurai"]
    },
    "kabuto_laminado_samurai": {
        "display_name": "Kabuto Laminado", "emoji": "🪖",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "media_key": "item_kabuto_laminado_samurai", "class_req": ["samurai"]
    },
    "do_laminado_samurai": {
        "display_name": "Do Laminado", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "media_key": "item_do_laminado_samurai", "class_req": ["samurai"]
    },
    "haidate_laminado_samurai": {
        "display_name": "Haidate Laminado", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "media_key": "item_haidate_laminado_samurai", "class_req": ["samurai"]
    },
    "suneate_laminado_samurai": {
        "display_name": "Suneate Laminado", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "media_key": "item_suneate_laminado_samurai", "class_req": ["samurai"]
    },
    "kote_laminado_samurai": {
        "display_name": "Kote Laminado", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "media_key": "item_kote_laminado_samurai", "class_req": ["samurai"]
    },
    "anel_laminado_samurai": {
        "display_name": "Anel Laminado", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "media_key": "item_anel_laminado_samurai", "class_req": ["samurai"]
    },
    "colar_laminado_samurai": {
        "display_name": "Colar Laminado", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "media_key": "item_colar_laminado_samurai", "class_req": ["samurai"]
    },
    "brinco_laminado_samurai": {
        "display_name": "Brinco Laminado", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "media_key": "item_brinco_laminado_samurai", "class_req": ["samurai"]
    },
    # Samurai T2
    "katana_damasco_samurai": {
        "display_name": "Katana de Aço Damasco", "emoji": "⚔️",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "media_key": "item_katana_damasco_samurai", "class_req": ["samurai"]
    },
    "kabuto_damasco_samurai": {
        "display_name": "Kabuto de Aço Damasco", "emoji": "🪖",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "media_key": "item_kabuto_damasco_samurai", "class_req": ["samurai"]
    },
    "do_damasco_samurai": {
        "display_name": "Do de Aço Damasco", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "media_key": "item_do_damasco_samurai", "class_req": ["samurai"]
    },
    "haidate_damasco_samurai": {
        "display_name": "Haidate de Aço Damasco", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "media_key": "item_haidate_damasco_samurai", "class_req": ["samurai"]
    },
    "suneate_damasco_samurai": {
        "display_name": "Suneate de Aço Damasco", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "media_key": "item_suneate_damasco_samurai", "class_req": ["samurai"]
    },
    "kote_damasco_samurai": {
        "display_name": "Kote de Aço Damasco", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "media_key": "item_kote_damasco_samurai", "class_req": ["samurai"]
    },
    "anel_damasco_samurai": {
        "display_name": "Anel de Aço Damasco", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "media_key": "item_anel_damasco_samurai", "class_req": ["samurai"]
    },
    "colar_damasco_samurai": {
        "display_name": "Colar de Aço Damasco", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "media_key": "item_colar_damasco_samurai", "class_req": ["samurai"]
    },
    "brinco_damasco_samurai": {
        "display_name": "Brinco de Aço Damasco", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "media_key": "item_brinco_damasco_samurai", "class_req": ["samurai"]
    },

    # --- CURANDEIRO ---
    "bastao_carvalho_curandeiro": {
        "display_name": "Bastão de Carvalho", "emoji": "🦯",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "media_key": "item_bastao_carvalho_curandeiro", "class_req": ["curandeiro"]
    },
    "capuz_linho_curandeiro": {
        "display_name": "Capuz de Linho", "emoji": "🧢",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "media_key": "item_capuz_linho_curandeiro", "class_req": ["curandeiro"]
    },
    "tunica_linho_curandeiro": {
        "display_name": "Túnica de Linho", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "media_key": "item_tunica_linho_curandeiro", "class_req": ["curandeiro"]
    },
    "calcas_linho_curandeiro": {
        "display_name": "Calças de Linho", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "media_key": "item_calcas_linho_curandeiro", "class_req": ["curandeiro"]
    },
    "sapatos_simples_curandeiro": {
        "display_name": "Sapatos Simples", "emoji": "👞",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "media_key": "item_sapatos_simples_curandeiro", "class_req": ["curandeiro"]
    },
    "faixas_linho_curandeiro": {
        "display_name": "Faixas de Linho", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "media_key": "item_faixas_linho_curandeiro", "class_req": ["curandeiro"]
    },
    "anel_cobre_curandeiro": {
        "display_name": "Anel de Cobre", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "media_key": "item_anel_cobre_curandeiro", "class_req": ["curandeiro"]
    },
    "colar_contas_curandeiro": {
        "display_name": "Colar de Contas", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "media_key": "item_colar_contas_curandeiro", "class_req": ["curandeiro"]
    },
    "brinco_cobre_curandeiro": {
        "display_name": "Brinco de Cobre", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "media_key": "item_brinco_cobre_curandeiro", "class_req": ["curandeiro"]
    },
    # Curandeiro T2
    "cetro_prata_curandeiro": {
        "display_name": "Cetro de Prata", "emoji": "⚕️",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "media_key": "item_cetro_prata_curandeiro", "class_req": ["curandeiro"]
    },
    "mitra_seda_curandeiro": {
        "display_name": "Mitra de Seda", "emoji": "👑",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "media_key": "item_mitra_seda_curandeiro", "class_req": ["curandeiro"]
    },
    "vestes_sagradas_curandeiro": {
        "display_name": "Vestes Sagradas", "emoji": "👘",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "media_key": "item_vestes_sagradas_curandeiro", "class_req": ["curandeiro"]
    },
    "calcas_seda_curandeiro": {
        "display_name": "Calças de Seda", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "media_key": "item_calcas_seda_curandeiro", "class_req": ["curandeiro"]
    },
    "botas_sagradas_curandeiro": {
        "display_name": "Botas Sagradas", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "media_key": "item_botas_sagradas_curandeiro", "class_req": ["curandeiro"]
    },
    "luvas_seda_curandeiro": {
        "display_name": "Luvas de Seda", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "media_key": "item_luvas_seda_curandeiro", "class_req": ["curandeiro"]
    },
    "anel_luz_curandeiro": {
        "display_name": "Anel da Luz", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "media_key": "item_anel_luz_curandeiro", "class_req": ["curandeiro"]
    },
    "amuleto_sagrado_curandeiro": {
        "display_name": "Amuleto Sagrado", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "media_key": "item_amuleto_sagrado_curandeiro", "class_req": ["curandeiro"]
    },
    "brinco_fe_curandeiro": {
        "display_name": "Brinco da Fé", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "media_key": "item_brinco_fe_curandeiro", "class_req": ["curandeiro"]
    },
})

# ============================================================
# 4. REGISTRO E GERAÇÃO AUTOMÁTICA
# ============================================================

def _register_item_safe(item_id: str, data: dict, market_price: int | None = None):
    """Registra item no banco de dados e opcionalmente no mercado."""
    global ITEMS_DATA, MARKET_ITEMS
    
    if item_id not in ITEMS_DATA:
        ITEMS_DATA[item_id] = data

    if market_price is not None:
        if isinstance(MARKET_ITEMS, dict):
            MARKET_ITEMS[item_id] = {
                "price": int(market_price), 
                "currency": "gold", 
                "tradeable": bool(data.get("tradable", True))
            }

def _generate_auto_items():
    """Lê Skills e Skins e cria os itens 'Tomo' e 'Caixa'."""
    generated = 0
    
    # SKILLS -> TOMOS
    try:
        from modules.game_data.skills import SKILL_DATA
        for skill_id, info in SKILL_DATA.items():
            item_id = f"tomo_{skill_id}"
            if item_id not in ITEMS_DATA:
                ITEMS_DATA[item_id] = {
                    "display_name": f"Tomo: {info.get('display_name', skill_id)}",
                    "emoji": "📖",
                    "type": "consumable",
                    "category": "aprendizado", 
                    "description": f"Ensina a habilidade: {info.get('display_name', skill_id)}.",
                    "stackable": True, "tradable": True, "market_currency": "gems",
                    "on_use": {"effect": "grant_skill", "skill_id": skill_id}
                }
                generated += 1
    except Exception as e:
        logger.error(f"Auto-Items Skill Error: {e}")

    # SKINS -> CAIXAS
    try:
        from modules.game_data.skins import SKIN_CATALOG
        for skin_id, info in SKIN_CATALOG.items():
            item_id = f"caixa_{skin_id}"
            if item_id not in ITEMS_DATA:
                ITEMS_DATA[item_id] = {
                    "display_name": f"Cx. Skin: {info.get('display_name', skin_id)}",
                    "emoji": "🎨",
                    "type": "consumable",
                    "category": "aprendizado", 
                    "description": f"Desbloqueia skin: {info.get('display_name', skin_id)}.",
                    "stackable": True, "tradable": True, "market_currency": "gems",
                    "on_use": {"effect": "grant_skin", "skin_id": skin_id}
                }
                generated += 1
    except Exception as e:
        logger.error(f"Auto-Items Skin Error: {e}")
        
    print(f">>> ITEMS: {generated} itens automáticos gerados.")

# Executa geração
_generate_auto_items()

# ============================================================
# 5. ITENS DE EVOLUÇÃO
# ============================================================

# Emblemas
_EVOLUTION_EMBLEMS = {
    "emblema_guerreiro": "⚔️", "emblema_berserker": "🪓", "emblema_cacador": "🏹",
    "emblema_monge": "🧘", "emblema_mago": "🪄", "emblema_bardo": "🎶",
    "emblema_assassino": "🔪", "emblema_samurai": "🥷", 
    "emblema_cura": "⚕️" # Adicionado Curandeiro
}
for cls, emo in _EVOLUTION_EMBLEMS.items():
    _register_item_safe(cls, {
        "display_name": f"Emblema: {cls.split('_')[1].title()}", "emoji": emo,
        "type": "especial", "category": "evolucao", "description": "Item de Evolução.",
        "stackable": True, "tradable": True
    }, market_price=500)

# Essências
_ESSENCES = [
    ("essencia_guardia", "🛡️"), ("essencia_furia", "💢"), ("essencia_luz", "✨"),
    ("essencia_sombra", "🌑"), ("essencia_precisao", "🎯"), ("essencia_fera", "🐾"),
    ("essencia_ki", "🌀"), ("essencia_arcana", "🔮"), ("essencia_elemental", "🌩️"),
    ("essencia_harmonia", "🎵"), ("essencia_encanto", "🧿"), ("essencia_letal", "☠️"),
    ("essencia_corte", "🗡️"), ("essencia_disciplina", "📏"),
    ("essencia_fe", "🙏"), ("essencia_fe_pura", "🌟") # Adicionado Curandeiro
]
for eid, emo in _ESSENCES:
    name = eid.replace("_", " ").title()
    _register_item_safe(eid, {
        "display_name": name, "emoji": emo, "type": "material_magico", 
        "category": "evolucao", "description": "Essência de poder.", "stackable": True
    }, market_price=220)

# Relíquias (T3/T4)
_RELICS = [
    "selo_sagrado", "totem_ancestral", "marca_predador", "reliquia_mistica",
    "grimorio_arcano", "batuta_maestria", "manto_eterno", "lamina_sagrada",
    "pergaminho_sagrado", "calice_da_luz", "alma_da_fe" # Adicionado Curandeiro
]
for rid in _RELICS:
    _register_item_safe(rid, {
        "display_name": rid.replace("_", " ").title(), "emoji": "🔱",
        "type": "especial", "category": "evolucao", "description": "Relíquia antiga.",
        "stackable": False
    }, market_price=None)

# ============================================================
# 6. FINALIZAÇÃO
# ============================================================

# Configuração Premium (Gemas)
EVOLUTION_GEMS_ONLY = {
    "emblema_guerreiro", "essencia_guardia", "essencia_furia", "essencia_luz",
    "emblema_berserker", "emblema_cacador", "essencia_precisao", "essencia_fera",
    "emblema_monge", "essencia_ki", "emblema_mago", "essencia_arcana",
    "essencia_elemental", "emblema_bardo", "essencia_harmonia", "essencia_encanto",
    "emblema_assassino", "essencia_sombra", "essencia_letal", "emblema_samurai",
    "essencia_corte", "essencia_disciplina", "emblema_cura", "essencia_fe", "essencia_fe_pura"
}

def apply_gem_flags():
    for iid in EVOLUTION_GEMS_ONLY:
        if iid in ITEMS_DATA:
            ITEMS_DATA[iid]["evolution_item"] = True
            ITEMS_DATA[iid]["market_currency"] = "gems"

apply_gem_flags()

# Alias e Helpers
ITEMS_DATA["ferro"] = ITEMS_DATA.get("minerio_de_ferro")
ITEM_BASES = ITEMS_DATA
ITEMS = ITEMS_DATA

def get_item(item_id: str):
    return ITEMS_DATA.get(item_id)

def is_stackable(item_id: str) -> bool:
    meta = ITEMS_DATA.get(item_id) or {}
    return bool(meta.get("stackable", True))

def get_display_name(item_id: str) -> str:
    meta = ITEMS_DATA.get(item_id) or {}
    return meta.get("display_name", item_id)