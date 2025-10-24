# modules/game_data/items.py
"""
Tabela base de itens de inventário (materiais, consumíveis, insumos, etc).
Mantenha IDs canônicos — outros módulos referenciam esses IDs diretamente.
"""


ITEMS_DATA = {
    # Em modules/game_data/items.py, dentro do dicionário ITEMS_DATA

    # --- NOVOS INGREDIENTES DE ALQUIMIA ---
    "frasco_com_agua": {
        "display_name": "Frasco com Água",
        "emoji": "💧",
        "type": "reagent",
        "description": "A base para a maioria das poções."
    },
    "folha_sombria": {
        "display_name": "Folha Sombria",
        "emoji": "🌿",
        "type": "reagent",
        "description": "Uma erva com propriedades curativas que cresce na Floresta Sombria."
    },
    "geleia_slime": {
        "display_name": "Geleia de Slime",
        "emoji": "🟢",
        "type": "reagent",
        "description": "Uma substância viscosa com uma energia vital peculiar."
    },

    # --- NOVAS POÇÕES ---
    "pocao_cura_leve": {
        "display_name": "Poção de Cura Leve",
        "emoji": "❤️",
        "type": "potion",
        "description": "Recupera 50 pontos de vida instantaneamente.",
        "effects": {
            "heal": 50
        }
    },
    "pocao_cura_media": {
        "display_name": "Poção de Cura Média", # <--- ESTA LINHA FALTAVA
        "emoji": "❤️‍🩹",
        "type": "potion",
        "description": "Recupera 150 pontos de vida instantaneamente.",
        "effects": {
            "heal": 150
        }
    },
    "pocao_energia_fraca": {
        "display_name": "Poção de Energia Fraca",
        "emoji": "⚡️",
        "type": "potion",
        "description": "Recupera 10 pontos de energia instantaneamente.",
        "effects": {
            "add_energy": 10
        }
    },
    "frasco_sabedoria": {
        "display_name": "Frasco de Sabedoria",
        "emoji": "🧠",
        "type": "potion",
        "description": "Concede 100 pontos de experiência de combate.",
        "effects": {
            "add_xp": 100
        }
    },
    "fragmento_bravura": {
        "display_name": "Fʀᴀɢᴍᴇɴᴛᴏ ᴅᴇ Bʀᴀᴠᴜʀᴀ",
        "emoji": "🏅",
        "type": "especial",
        "category": "evento",
        "description": "Um fragmento obtido ao defender o reino. Junte 100 para forjar uma recompensa.",
        "stackable": True,
        "media_key": "item_fragmento_bravura" # Podemos criar um file_id para ele depois
    },
    "ticket_defesa_reino": {
        "display_name": "Tɪᴄᴋᴇᴛ ᴅᴇ Dᴇғᴇsᴀ ᴅᴏ Rᴇɪɴᴏ",
        "emoji": "🎟️",
        "type": "event_ticket",
        "category": "evento",
        "description": "Garante uma entrada no evento de Defesa do Reino. Válido até o fim do evento ou até você ser derrotado.",
        "stackable": True,
        "media_key": "item_ticket_defesa_reino" # Podemos criar um file_id para ele depois
    },

    "ticket_arena": {
    "display_name": "Entrada da Arena",
    "emoji": "🎟️",
    "description": "Um ticket que concede uma entrada extra para as batalhas ranqueadas da Arena de Eldora. Pode ser usado a qualquer momento.",
    "type": "event_ticke",
    "category": "evento",        # É um item consumível
    "stackable": True,      # O jogador pode ter vários
    
    # Efeito especial ao usar o item do inventário
    "on_use": {
        "effect": "add_pvp_entries",
        "value": 1
    }
    },

        "nucleo_forja_comum": {
        "display_name": "Núcleo de Forja Comum",
        "emoji": "🔥",
        "type": "material",
        "description": "Fonte de energia básica utilizada na forja de itens de Tier 2."
    },

     "joia_da_forja": {
        "display_name": "Joia de Aprimoramento",
        "emoji": "💎",
    },

     "sigilo_protecao": {
        "display_name": "Sigilo de Proteção",
        "emoji": "✨",
        "type": "especial",
     },
     
    "gems": {
        "display_name": "Diamante",
        "emoji": "💎",
        "description": "Uma gema rara e valiosa, usada para transações especiais na loja.",
        "type": "currency",     # Sugestão: bom para organizar seus itens
        "stackable": True,      # Moedas são sempre empilháveis
    
    },
    "pergaminho_durabilidade": {
        "display_name": "Pergaminho de Durabilidade",
        "emoji": "📜",
    },

    # ================================
    # COLETA BÁSICA
    # ================================
    "madeira": {
        "display_name": "Mᴀᴅᴇɪʀᴀ", "emoji": "🪵",
        "type": "material_bruto", "category": "coletavel",
        "description": "Madeira comum para várias criações.",
        "stackable": True,  
        "media_key":"imagem_madeira_coletada",
        
    },
    "pedra": {
        "display_name": "Pᴇᴅʀᴀ", "emoji": "🪨",
        "type": "material_bruto", "category": "coletavel",
        "description": "Rocha comum, serve para construções e refino.",
        "stackable": True,
        "media_key": "imagem_pedra",
        
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

    
    # ================================
    # MATERIAIS DE MONSTROS (ABA: CAÇA)
    # ================================
    
    "minerio_estanho": {
        "display_name": "Mɪɴᴇ́ʀɪᴏ ᴅᴇ Esᴛᴀɴʜᴏ", "emoji": "🪙",
        "type": "material_bruto", "category": "cacada",
        "description": "Metal macio, excelente para ligas (ex.: bronze).",
        "stackable": True,
        "media_key": "item_minerio_stanho"
    },
    
    "gema_bruta": {
        "display_name": "Gᴇᴍᴀ Bʀᴜᴛᴀ", "emoji": "💎",
        "type": "material_bruto", "category": "cacada",
        "description": "Pedra preciosa sem lapidação, com potencial mágico.",
        "stackable": True,
        "media_key": "item_gema_bruta"
    },

    "madeira_rara": {
        "display_name": "Mᴀᴅᴇɪʀᴀ Rᴀʀᴀ", "emoji": "🪵☦️",
        "type": "material_bruto", "category": "cacada",
        "description": "Madeira de árvore antiga, resistente e flexível.",
        "stackable": True,
        "media_key": "item_madeira_rara",
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
        "description": "Presas afiadas, úteis em talismãs e reforços.",
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
        "media_key": "item_martelo_enfrrujado"
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
    "barra_de_aco": {
        "display_name": "Bᴀʀʀᴀ ᴅᴇ Aᴄ̧ᴏ", "emoji": "⛓️🧱",
        "type": "material_refinado", "category": "coletavel",
        "description": "Liga metálica superior ao ferro, essencial em equipamentos T2.",
        "stackable": True,
        "value": 60,
        "media_key": "item_barra_de_aco"
    },
    "dente_afiado_superior": {
        "display_name": "Dᴇɴᴛᴇ Aғɪᴀᴅᴏ Sᴜᴘᴇʀɪᴏʀ", "emoji": "🦷",
        "type": "material_monstro", "category": "cacada",
        "description": "Dente robusto e extremamente afiado, usado em forjas avançadas.",
        "stackable": True,
        "media_key": "item_dente_afiado_superior"
        
    },
    "ponta_de_osso_afiada": {
        "display_name": "Pᴏɴᴛᴀ ᴅᴇ Ossᴏ Aғɪᴀᴅᴀ", "emoji": "🦴",
        "type": "material_monstro", "category": "coletavel",
        "description": "Dente robusto e extremamente afiado, usado em forjas avançadas.",
        "stackable": True,
        "media_key": "item_ponta_de_osso_afiada"
        
    },
    "veludo_runico": {
        "display_name": "Vᴇʟᴜᴅᴏ Rᴜ́ɴɪᴄᴏ", "emoji": "🧵",
        "type": "material_refinado", "category": "coletavel",
        "description": "Tecido mágico e luxuoso usado em trajes avançados.",
        "stackable": True,
        "media_key": "item_veludo_runico"
    },
    "couro_reforcado": {
        "display_name": "Cᴏᴜʀᴏ Rᴇғᴏʀᴄ̧ᴀᴅᴏ", "emoji": "🐂",
        "type": "material_refinado", "category": "coletavel",
        "description": "Couro tratado com técnicas especiais para maior durabilidade.",
        "stackable": True,
        "media_key": "item_couro_reforcado"
    },    
    "pele_troll_regenerativa": {
        "display_name": "Pᴇʟᴇ ᴅᴇ Tʀᴏʟʟ Rᴇɢᴇɴᴇʀᴀᴛɪᴠᴀ", "emoji": "🧌✨🩸",
        "type": "material_refinado", "category": "coletavel",
        "description": "Couro tratado com técnicas especiais para maior durabilidade.",
        "stackable": True,
        "media_key": "item_pele_troll_regenerativa"    
     },    
    "membrana_de_couro_fino": {
        "display_name": "Mᴇᴍʙʀᴀɴᴀ ᴅᴇ Cᴏᴜʀᴏ Fɪɴᴏ", "emoji": "🦇",
        "type": "material_refinado", "category": "coletavel",
        "description": "Couro tratado com técnicas especiais para maior durabilidade.",
        "stackable": True,
        "media_key": "item_membrana_de_couro_fino"        
    },
    "barra_de_prata": {
        "display_name": "Bᴀʀʀᴀ ᴅᴇ Pʀᴀᴛᴀ", "emoji": "🥈",
        "type": "material_refinado", "category": "coletavel",
        "description": "Metal precioso usado em joias e ornamentos.",
        "stackable": True,
        "media_key": "item_barra_de_prata" 
    },
    # ================================
    # PRODUTOS DE REFINO & TECELAGEM (ABA: COLETÁVEL)
    # ================================
    "barra_de_ferro": {
        "display_name": "Bᴀʀʀᴀ ᴅᴇ Fᴇʀʀᴏ", "emoji": "🧱",
        "type": "material_refinado", "category": "coletavel",
        "description": "Barra metálica básica, resultado de refino.",
        "stackable": True,
        "media_key": "item_barra_de_ferro"
    },
    "barra_bronze": {
        "display_name": "Bᴀʀʀᴀ ᴅᴇ Bʀᴏɴᴢᴇ", "emoji": "🟤",
        "type": "material_refinado", "category": "coletavel",
        "description": "Liga de ferro+estanho (neste jogo).",
        "stackable": True,
        "media_key": "item_barra_de_bronze"
    },
    "couro_curtido": {
        "display_name": "Cᴏᴜʀᴏ Cᴜʀᴛɪᴅᴏ", "emoji": "🐑",
        "type": "material_refinado", "category": "coletavel",
        "description": "Couro tratado, base para várias criações.",
        "stackable": True,
        "media_key": "item_couro_curtido"
    },
    "rolo_de_pano_simples": {
        "display_name": "Rᴏʟᴏ ᴅᴇ Pᴀɴᴏ Sɪᴍᴘʟᴇs", "emoji": "🪢",
        "type": "material_refinado", "category": "coletavel",
        "description": "Tecido básico preparado para costura.",
        "stackable": True,
        "media_key": "item_rolo_de_pano_simples"
    },
       "gema_polida": { 
        "display_name": "Gᴇᴍᴀ Pᴏʟɪᴅᴀ", "emoji": "🔷",
        "type": "material_refinado", "category": "coletavel",
        "description": "Gema lapidada, pronta para engaste em joias.",
        "stackable": True,
        "media_key": "item_gema_polida"
        
    },
    "dente_afiado": {
        "display_name": "Dᴇɴᴛᴇ Aғɪᴀᴅᴏ", "emoji": "🦷",
        "type": "material_monstro", "category": "cacada",
        "description": "Dente afiado coletado de criaturas selvagens.",
        "stackable": True,
        "media_key": "item_dente_afiado"
    },
    "fragmento_gargula": {
        "display_name": "Fʀᴀɢᴍᴇɴᴛᴏ ᴅᴇ Gᴀ́ʀɢᴜʟᴀ", "emoji": "🪨",
        "type": "material_monstro", "category": "cacada",
        "description": "Estilhaço pétreo imbuído de energia sombria.",
        "stackable": True,
        "media_key": "item_fragmento_gargula"
    },
    "fio_de_prata": {
        "display_name": "Fɪᴏ ᴅᴇ Pʀᴀᴛᴀ", "emoji": "🪡",
        "type": "material_refinado", "category": "coletavel",
        "description": "Fio de prata maleável, ótimo para joias finas.",
        "stackable": True,
        "media_key": "item_fio_de_prata"
    },
        "pedra_do_aprimoramento": {
        "display_name": "Pᴇᴅʀᴀ ᴅᴏ Aᴘʀɪᴍᴏʀᴀᴍᴇɴᴛᴏ", "emoji": "✨",
        "type": "consumivel", "category": "consumivel",
        "description": "Melhora a qualidade de equipamentos.",
        "stackable": True,
        "value": 300,

    },
    "pergaminho_durabilidade": {
        "display_name": "Pᴇʀɢᴀᴍɪɴʜᴏ ᴅᴇ Dᴜʀᴀʙɪʟɪᴅᴀᴅᴇ", "emoji": "📜",
        "type": "consumivel", "category": "consumivel",
        "description": "Restaura a durabilidade máxima de um item.",
        "stackable": True,
        "value": 150,
    },
    "nucleo_forja_fraco": {
        "display_name": "Nᴜ́ᴄʟᴇᴏ ᴅᴇ Fᴏʀᴊᴀ Fʀᴀᴄᴏ", "emoji": "🔥",
        "type": "material_magico", "category": "consumivel",
        "description": "Fonte de poder modesta para a forja.",
        "stackable": True,
        "value": 40,
    },
    "nucleo_forja_comum": {
        "display_name": "Nᴜ́ᴄʟᴇᴏ ᴅᴇ Fᴏʀᴊᴀ Cᴏᴍᴜᴍ", "emoji": "💥",
        "type": "material_magico", "category": "consumivel",
        "description": "Fonte de poder estável para a forja.",
        "stackable": True,
        "value": 150,
    },

    # ================================
    # ESPECIAIS
    # ================================
    # --- Chaves de dungeon ---

    "cristal_de_abertura": {
        "display_name": "Cʀɪsᴛᴀʟ ᴅᴇ Aʙᴇʀᴛᴜʀᴀ", "emoji": "🔹",
        "type": "especial", "category": "especial",
        "description": "Chave arcana para abrir portais de dungeons.",
        "stackable": True,
    },
    # use ID diferente para coop:
    "cristal_de_abertura_coop": {
        "display_name": "Cʀɪsᴛᴀʟ ᴅᴇ Aʙᴇʀᴛᴜʀᴀ (Cᴏᴏᴘ)", "emoji": "🪯",
        "type": "especial", "category": "consumivel",
        "description": "Chave arcana para abrir portais de dungeon em grupo.",
        "stackable": True,
    },

# --- Drop regional da Floresta (buff de vida ao usar) ---

    "seiva_escura": {
        "display_name": "Sᴇɪᴠᴀ Esᴄᴜʀᴀ", "emoji": "🩸",
        "type": "consumivel", "category": "buff",
        "description": "Essência vital da floresta sombria. Ao usar: +10 Vida máxima por 60 min.",
        "stackable": True,
        "on_use": {
            "effect_id": "buff_hp_flat",
            "value": 10,
            "duration_sec": 3600    
        }
        
    },
    "chave_da_catacumba": {
        "display_name": "Cʜᴀᴠᴇ ᴅᴀ Cᴀᴛᴀᴄᴜᴍʙᴀ", "emoji": "🗝",
        "typr": "especial", "category": "especial",
        "description": "Chave da Catatumba do Reino.",
        "stackable": True, 
    },
    # ================================
    # ITENS RESULTANTES - ASSASSINO T1
    # ================================
    "adaga_sorrateira_assassino": {
        "display_name": "Adaga Sorrateira", "emoji": "🔪",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "description": "Arma letal do Conjunto Sorrateiro do Assassino.",
        "media_key": "item_adaga_sorrateira_assassino",
        "class_req": ["assassino"]
    },
    "mascara_sorrateira_assassino": {
        "display_name": "Máscara Sorrateira", "emoji": "🪖",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "description": "Máscara leve e intimidadora do Conjunto Sorrateiro.",
        "media_key": "item_mascara_sorrateira_assassino",
        "class_req": ["assassino"]
    },
    "couraca_sorrateira_assassino": {
        "display_name": "Couraça Sorrateira", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "description": "Proteção ágil feita para furtividade.",
        "media_key": "item_couraca_sorrateira_assassino",
        "class_req": ["assassino"] 
    },
    "calcas_sorrateiras_assassino": {
        "display_name": "Calças Sorrateiras", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "description": "Calças leves que permitem movimentos rápidos.",
        "media_key": "item_calcas_sorrateira_assassino",
        "class_req": ["assassino"]
    },
    "botas_sorrateiras_assassino": {
        "display_name": "Botas Sorrateiras", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "description": "Botas reforçadas para movimentação silenciosa.",
        "media_key": "item_bota_sorrateira_assassino",
        "class_req": ["assassino"]
    },
    "luvas_sorrateiras_assassino": {
        "display_name": "Luvas Sorrateiras", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "description": "Luvas leves que aumentam a destreza do assassino.",
        "media_key": "item_luvas_sorrateiras_assassino",
        "class_req": ["assassino"]
    },
    "anel_sorrateiro_assassino": {
        "display_name": "Anel Sorrateiro", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "description": "Anel sombrio que amplifica a furtividade.",
        "media_key": "item_anel_sorrateiro_assassino",
        "class_req": ["assassino"]
    },
    "colar_sorrateiro_assassino": {
        "display_name": "Colar Sorrateiro", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "description": "Colar que envolve o portador em uma aura de sombras.",
        "media_key": "item_colar_sorrateiro_assassino",
        "class_req": ["assassino"]
    },
    "brinco_sorrateiro_assassino": {
        "display_name": "Brinco Sorrateiro", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "description": "Brinco que protege contra olhares indiscretos.",
        "media_key": "item_brinco_sorrateiro_assassino",
        "class_req": ["assassino"]
    },

    # ================================
    # ITENS RESULTANTES — Assassino T2
    # ================================
    "adaga_sombra_assassino": {
        "display_name": "Adaga da Sombra", "emoji": "🔪",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "description": "Lâmina leve e mortal, envolta em brumas etéreas.",
        "media_key": "item_adaga_sombra_assassino",
        "class_req": ["assassino"]
    },
    "mascara_sombra_assassino": {
        "display_name": "Máscara da Sombra", "emoji": "🪖",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "description": "Máscara de couro escuro, oculta intenções.",
        "media_key": "item_mascara_sombra_assassino",
        "class_req": ["assassino"]
    },
    "couraca_sombra_assassino": {
        "display_name": "Couraça da Sombra", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "description": "Proteção flexível adequada ao silêncio mortal.",
        "media_key": "item_couraca_sombra_assassino",
        "class_req": ["assassino"]
    },
    "calcas_sombra_assassino": {
        "display_name": "Calças da Sombra", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "description": "Tecidos silenciosos que não traem seus passos.",
        "media_key": "item_calcas_sombra_assassino",
        "class_req": ["assassino"]
    },
    "botas_sombra_assassino": {
        "display_name": "Botas da Sombra", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "description": "Passos que desaparecem no escuro.",
        "media_key": "item_botas_sombra_assassino",
        "class_req": ["assassino"]
    },
    "luvas_sombra_assassino": {
        "display_name": "Luvas da Sombra", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "description": "Empunhadura firme sem um ruído.",
        "media_key": "item_luvas_sombra_assassino",
        "class_req": ["assassino"]
    },
    "anel_sombra_assassino": {
        "display_name": "Anel da Sombra", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "description": "Eco espectral preso em metal frio.",
        "media_key": "item_anel_sombra_assassino",
        "class_req": ["assassino"]
    },
    "colar_sombra_assassino": {
        "display_name": "Colar da Sombra", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "description": "Sussurros que guiam o golpe perfeito.",
        "media_key": "item_colar_sombra_assassino",
        "class_req": ["assassino"]
    },
    "brinco_sombra_assassino": {
        "display_name": "Brinco da Sombra", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "description": "Lâmina na escuridão, sinal na penumbra.",
        "media_key": "item_brinco_sombra_assassino",
        "class_req": ["assassino"]
    },
    # ================================
    # ITENS RESULTANTES — Bardo T1
    # ================================
    "alaude_simples_bardo": {
        "display_name": "Alaúde Simples do Bardo", "emoji": "🎻",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "description": "Instrumento encantado que ecoa notas de coragem.",
        "media_key": "item_alaude_simples_bardo",
        "class_req": ["bardo"]
    },
    "chapeu_elegante_bardo": {
        "display_name": "Chapéu Elegante do Bardo", "emoji": "🎩",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "description": "Chapéu com pena vistosa, marca de um verdadeiro trovador.",
        "media_key": "item_chapeu_elegante_bardo",
        "class_req": ["bardo"]
    },
    "colete_viajante_bardo": {
        "display_name": "Colete de Viajante do Bardo", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "description": "Colete leve para longas jornadas de espetáculo.",
        "media_key": "item_colete_viajante_bardo",
        "class_req": ["bardo"]
    },
    "calcas_linho_bardo": {
        "display_name": "Calças de Linho do Bardo", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "description": "Linho confortável para passos inspirados.",
        "media_key": "item_calcas_linho_bardo",
        "class_req": ["bardo"]
    },
    "botas_macias_bardo": {
        "display_name": "Botas Macias do Bardo", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "description": "Botas silenciosas para palcos e tavernas.",
        "media_key": "item_botas_macias_bardo",
        "class_req": ["bardo"]
    },
    "luvas_sem_dedos_bardo": {
        "display_name": "Luvas sem Dedos do Bardo", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "description": "Luvas que não atrapalham a performance.",
        "media_key": "item_luvas_sem_dedos_bardo",
        "class_req": ["bardo"]
    },
    "anel_melodico_bardo": {
        "display_name": "Anel Melódico do Bardo", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "description": "Anel que ressoa com harmonias arcanas.",
        "media_key": "item_anel_melodico_bardo",
        "class_req": ["bardo"]
    },
    "colar_melodico_bardo": {
        "display_name": "Colar Melódico do Bardo", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "description": "Colar que amplia a projeção da voz.",
        "media_key": "item_colar_melodico_bardo",
        "class_req": ["bardo"]
    },
    "brinco_melodico_bardo": {
        "display_name": "Brinco Melódico do Bardo", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "description": "Brinco que harmoniza frequências sônicas.",
        "media_key": "item_brinco_melodico_bardo",
        "class_req": ["bardo"]
    },

    
    # ================================
    # RESULTADOS — BARDO T2
    # ================================
    "alaude_ornamentado_bardo": {
        "display_name": "Alaúde Ornamentado do Bardo", "emoji": "🎻",
        "type": "equipment_base", "slot": "arma",
        "description": "Instrumento magistral de madeira rúnica e prata, ressoa magia melódica.",
        "stackable": False,
        "media_key": "item_alaude_ornamentado_bardo",
        "class_req": ["bardo"]
    },
    "chapeu_emplumado_bardo": {
        "display_name": "Chapéu Emplumado do Bardo", "emoji": "🎩",
        "type": "equipment_base", "slot": "elmo",
        "description": "Chapéu elegante adornado com plumas, favorito dos virtuoses itinerantes.",
        "stackable": False,
        "media_key": "item_chapeu_emplumado_bardo",
        "class_req": ["bardo"]
    },
    "casaco_veludo_bardo": {
        "display_name": "Casaco de Veludo do Bardo", "emoji": "👕",
        "type": "equipment_base", "slot": "armadura",
        "description": "Casaco de veludo rúnico com costuras em prata, feito para grandes palcos.",
        "stackable": False,
        "media_key": "item_casaco_veludo_bardo",
        "class_req": ["bardo"]
    },
    "calcas_veludo_bardo": {
        "display_name": "Calças de Veludo do Bardo", "emoji": "👖",
        "type": "equipment_base", "slot": "calca",
        "description": "Calças confortáveis de veludo rúnico, leves para performances ágeis.",
        "stackable": False,
        "media_key": "item_calca_veludo_bardo",
        "class_req": ["bardo"]
    },
    "botas_veludo_bardo": {
        "display_name": "Botas de Veludo do Bardo", "emoji": "🥾",
        "type": "equipment_base", "slot": "botas",
        "description": "Botas macias com reforço discreto, perfeitas para longas turnês.",
        "stackable": False,
        "media_key": "item_botas_veludo_bardo",
        "class_req": ["bardo"]
    },
    "luvas_veludo_bardo": {
        "display_name": "Luvas de Veludo do Bardo", "emoji": "🧤",
        "type": "equipment_base", "slot": "luvas",
        "description": "Luvas finas que preservam a destreza dos dedilhados mais intrincados.",
        "stackable": False,
        "media_key": "item_luvas_veludo_bardo",
        "class_req": ["bardo"]
    },
    "anel_prata_bardo": {
        "display_name": "Anel de Prata do Bardo", "emoji": "💍",
        "type": "equipment_base", "slot": "anel",
        "description": "Anel de prata lapidado, amplifica a presença cênica do músico.",
        "stackable": False,
        "media_key": "item_anel_prata_bardo",
        "class_req": ["bardo"]
    },
    "colar_prata_bardo": {
        "display_name": "Colar de Prata do Bardo", "emoji": "📿",
        "type": "equipment_base", "slot": "colar",
        "description": "Colar de prata com gemas, vibra em harmonia com canções arcanas.",
        "stackable": False,
        "media_key": "item_colar_prata_bardo",
        "class_req": ["bardo"]
    },
    "brinco_prata_bardo": {
        "display_name": "Brinco de Prata do Bardo", "emoji": "🧿",
        "type": "equipment_base", "slot": "brinco",
        "description": "Brincos de prata finamente trabalhados, sussurram notas inspiradoras.",
        "stackable": False,
        "media_key": "item_brinco_prata_bardo",
        "class_req": ["bardo"]
    },

    # ================================
    # ITENS RESULTANTES — Berserker T1
    # ================================
    "machado_rustico_berserker": {
        "display_name": "Machado Rústico do Berserker", "emoji": "🪓",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "description": "Machado pesado que canaliza a fúria do guerreiro.",
        "media_key": "item_machado_rustico_berserker",
        "class_req": ["berserker"]
    },
    "elmo_chifres_berserker": {
        "display_name": "Elmo de Chifres do Berserker", "emoji": "🪖",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "description": "Elmo intimidador adornado com chifres.",
        "media_key": "item_elmo_chifres_berserker",
        "class_req": ["berserker"]
    },
    "peitoral_placas_berserker": {
        "display_name": "Peitoral de Placas do Berserker", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "description": "Placas robustas para aguentar a linha de frente.",
        "media_key": "item_peitoral_placas_berserker",
        "class_req": ["berserker"]
    },
    "calcas_placas_berserker": {
        "display_name": "Calças de Placas do Berserker", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "description": "Proteção de pernas reforçada para combate cerrado.",
        "media_key": "item_calcas_placas_berserker",
        "class_req": ["berserker"]
    },
    "botas_couro_berserker": {
        "display_name": "Botas de Couro do Berserker", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "description": "Botas resistentes para avançar sem medo.",
        "media_key": "item_botas_couro_berserker",
        "class_req": ["berserker"]
    },
    "luvas_couro_berserker": {
        "display_name": "Luvas de Couro do Berserker", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "description": "Luvas firmes para golpes devastadores.",
        "media_key": "item_luvas_couro_berserker",
        "class_req": ["berserker"]
    },
    "anel_osso_berserker": {
        "display_name": "Anel de Osso do Berserker", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "description": "Anel tribal feito de ossos de caça.",
        "media_key": "item_anel_osso_berserker",
        "class_req": ["berserker"]
    },
    "colar_presas_berserker": {
        "display_name": "Colar de Presas do Berserker", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "description": "Colar adornado com presas de feras.",
        "media_key": "item_colar_presas_berserker",
        "class_req": ["berserker"]
    },
    "brinco_osso_berserker": {
        "display_name": "Brinco de Osso do Berserker", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "description": "Brinco que simboliza ferocidade em batalha.",
        "media_key": "item_brinco_osso_berserker",
        "class_req": ["berserker"]
    },

    # ================================
    # RESULTADOS — BERSERKER T2
    # ================================
    "machado_aco_berserker": {
        "display_name": "Machado de Aço do Berserker", "emoji": "🪓",
        "type": "equipment_base", "slot": "arma",
        "description": "Machado brutal de aço, banhado em sangue regenerativo.",
        "stackable": False,
        "media_key": "item_machado_aco_berserker",
        "class_req": ["berserker"]
    },
    "elmo_troll_berserker": {
        "display_name": "Elmo de Pele de Troll", "emoji": "🪖",
        "type": "equipment_base", "slot": "elmo",
        "description": "Elmo reforçado com pele de troll, transmite ferocidade.",
        "stackable": False,
        "media_key": "item_elmo_troll_berserker",
        "class_req": ["berserker"]
    },
    "peitoral_troll_berserker": {
        "display_name": "Peitoral de Pele de Troll", "emoji": "👕",
        "type": "equipment_base", "slot": "armadura",
        "description": "Placas de aço e pele de troll que regeneram lentamente.",
        "stackable": False,
        "media_key": "item_peitoral_troll_berserker",
        "class_req": ["berserker"]
    },
    "calcas_troll_berserker": {
        "display_name": "Calças de Pele de Troll", "emoji": "👖",
        "type": "equipment_base", "slot": "calca",
        "description": "Proteção robusta, dá vigor nas batalhas prolongadas.",
        "stackable": False,
        "media_key": "item_calcas_troll_berserker",
        "class_req": ["berserker"]
    },
    "botas_troll_berserker": {
        "display_name": "Botas de Pele de Troll", "emoji": "🥾",
        "type": "equipment_base", "slot": "botas",
        "description": "Botas pesadas com couro regenerativo de troll.",
        "stackable": False,
        "media_key": "item_botas_troll_berserker",
        "class_req": ["berserker"]
    },
    "luvas_troll_berserker": {
        "display_name": "Luvas de Pele de Troll", "emoji": "🧤",
        "type": "equipment_base", "slot": "luvas",
        "description": "Luvas reforçadas que aumentam o impacto dos golpes.",
        "stackable": False,
        "media_key": "item_luvas_troll_berserker",
        "class_req": ["berserker"]
    },
    "anel_troll_berserker": {
        "display_name": "Anel de Garra de Troll", "emoji": "💍",
        "type": "equipment_base", "slot": "anel",
        "description": "Forjado com garras de troll, vibra com fúria selvagem.",
        "stackable": False,
        "media_key": "item_anel_troll_berserker",
        "class_req": ["berserker"]
    },
    "colar_troll_berserker": {
        "display_name": "Colar de Garra de Troll", "emoji": "📿",
        "type": "equipment_base", "slot": "colar",
        "description": "Colar tribal, pulsando com energia sanguínea.",
        "stackable": False,
        "media_key": "item_colar_troll_berserker",
        "class_req": ["berserker"]
    },
    "brinco_troll_berserker": {
        "display_name": "Brinco de Garra de Troll", "emoji": "🧿",
        "type": "equipment_base", "slot": "brinco",
        "description": "Brinco artesanal, ecoa a fúria dos trolls.",
        "stackable": False,
        "media_key": "item_brinco_troll_berserker",
        "class_req": ["berserker"]

    },
# ================================
# EQUIPAMENTOS T2 — CAÇADOR continua 
# ================================
"arco_patrulheiro_cacador": {
    "display_name": "Arco de Patrulheiro",
    "emoji": "🏹",
    "type": "arma",
    "category": "equipamento",
    "description": "Arco de alta precisão usado por patrulheiros experientes.",
    "stackable": False,
    "media_key": "item_arco_patrulheiro_cacador",
    "class_req": ["cacador"]
},
"capuz_patrulheiro_cacador": {
    "display_name": "Capuz de Patrulheiro",
    "emoji": "🪖",
    "type": "elmo",
    "category": "equipamento",
    "description": "Capuz reforçado para proteger caçadores nas emboscadas.",
    "stackable": False,
    "media_key": "item_capuz_patrulheiro_cacador",
    "class_req": ["cacador"]
},
"peitoral_patrulheiro_cacador": {
    "display_name": "Peitoral de Patrulheiro",
    "emoji": "👕",
    "type": "armadura",
    "category": "equipamento",
    "description": "Proteção robusta de couro reforçado para longas caçadas.",
    "stackable": False,
    "media_key": "item_peitoral_patrulheiro_cacador",
    "class_req": ["cacador"]
},
"calcas_patrulheiro_cacador": {
    "display_name": "Calças de Patrulheiro",
    "emoji": "👖",
    "type": "calca",
    "category": "equipamento",
    "description": "Calças resistentes, ideais para movimentação rápida na floresta.",
    "stackable": False,
    "media_key": "item_calcas_patrulheiro_cacador",
    "class_req": ["cacador"]
},
"botas_patrulheiro_cacador": {
    "display_name": "Botas de Patrulheiro",
    "emoji": "🥾",
    "type": "botas",
    "category": "equipamento",
    "description": "Botas firmes que garantem passos silenciosos e estáveis.",
    "stackable": False,
    "media_key": "item_botas_patrulheiro_cacador",
    "class_req": ["cacador"]
},
"luvas_patrulheiro_cacador": {
    "display_name": "Luvas de Patrulheiro",
    "emoji": "🧤",
    "type": "luvas",
    "category": "equipamento",
    "description": "Luvas reforçadas para melhor precisão e agilidade no arco.",
    "stackable": False,
    "media_key": "item_luvas_patrulheiro_cacador",
    "class_req": ["cacador"]
},
"anel_patrulheiro_cacador": {
    "display_name": "Anel de Patrulheiro",
    "emoji": "💍",
    "type": "anel",
    "category": "equipamento",
    "description": "Anel mágico que aprimora a mira e a percepção do caçador.",
    "stackable": False,
    "media_key": "item_anel_patrulheiro_cacador",
    "class_req": ["cacador"]
},
"colar_patrulheiro_cacador": {
    "display_name": "Colar de Patrulheiro",
    "emoji": "📿",
    "type": "colar",
    "category": "equipamento",
    "description": "Colar encantado que conecta o caçador aos instintos da natureza.",
    "stackable": False,
    "media_key": "item_colar_patrulheiro_cacador",
    "class_req": ["cacador"]
},
"brinco_patrulheiro_cacador": {
    "display_name": "Brinco de Patrulheiro",
    "emoji": "🧿",
    "type": "brinco",
    "category": "equipamento",
    "description": "Brinco talismânico que aumenta a atenção e reflexos do caçador.",
    "stackable": False,
    "media_key": "item_brinco_patrulheiro_cacador",
    "class_req": ["cacador"]
},

    # ================================
    # ITENS RESULTANTES — Caçador T1
    # ================================
    "arco_batedor_cacador": {
        "display_name": "Arco de Batedor", "emoji": "🏹",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "description": "Arco leve e preciso usado pelos batedores.",
        "media_key": "item_arco_batedor_cacador",
        "class_req": ["cacador"]
    },
    "capuz_batedor_cacador": {
        "display_name": "Capuz de Batedor", "emoji": "🪖",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "description": "Capuz de couro para camuflagem e proteção.",
        "media_key": "item_capuz_batedor_cacador",
        "class_req": ["cacador"]
    },
    "peitoral_batedor_cacador": {
        "display_name": "Peitoral de Batedor", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "description": "Peitoral leve que não restringe os movimentos.",
        "media_key": "item_peitoral_batedor_cacador",
        "class_req": ["cacador"]
    },
    "calcas_batedor_cacador": {
        "display_name": "Calças de Batedor", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "description": "Calças reforçadas para longas perseguições.",
        "media_key": "item_caulcas_batedor_cacador",
        "class_req": ["cacador"]
    },
    "botas_batedor_cacador": {
        "display_name": "Botas de Batedor", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "description": "Botas leves que favorecem a mobilidade.",
        "media_key": "item_botas_batedor_cacador",
        "class_req": ["cacador"]
    },
    "luvas_batedor_cacador": {
        "display_name": "Luvas de Batedor", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "description": "Luvas que garantem firmeza ao empunhar o arco.",
        "media_key": "item_luvas_batedor_cacador",
        "class_req": ["cacador"]
    },
    "anel_batedor_cacador": {
        "display_name": "Anel de Batedor", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "description": "Anel que inspira foco na caçada.",
        "media_key": "item_anel_batedor_cacador",
        "class_req": ["cacador"]
    },
    "colar_batedor_cacador": {
        "display_name": "Colar de Batedor", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "description": "Colar adornado com lembranças de grandes caçadas.",
        "media_key": "item_colar_batedor_cacador",
        "class_req": ["cacador"]
    },
    "brinco_batedor_cacador": {
        "display_name": "Brinco de Batedor", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "description": "Brinco que aguça os sentidos durante a vigia.",
        "media_key": "item_brinco_batedor_cacador",
        "class_req": ["cacador"]
    },

    # ================================
    # ITENS RESULTANTES — Guerreiro T1
    # ================================
    "espada_ferro_guerreiro": {
        "display_name": "Espada de Ferro do Guerreiro", "emoji": "🗡️",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "description": "Espada confiável forjada em ferro temperado.",
        "media_key": "item_espada_ferro_guerreiro",
        "class_req": ["guerreiro"]
    },
    "elmo_ferro_guerreiro": {
        "display_name": "Elmo de Ferro do Guerreiro", "emoji": "🪖",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "description": "Proteção robusta para a cabeça.",
        "media_key": "item_elmo_ferro_guerreiro",
        "class_req": ["guerreiro"]
    },
    "peitoral_ferro_guerreiro": {
        "display_name": "Peitoral de Ferro do Guerreiro", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "description": "Peitoral de placas para combates intensos.",
        "media_key": "item_peitoral_ferro_guerreiro",
        "class_req": ["guerreiro"]
    },
    "calcas_ferro_guerreiro": {
        "display_name": "Calças de Ferro do Guerreiro", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "description": "Calças reforçadas para proteção das pernas.",
        "media_key": "item_calcas_ferro_guerreiro",
        "class_req": ["guerreiro"]
    },
    "botas_ferro_guerreiro": {
        "display_name": "Botas de Ferro do Guerreiro", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "description": "Botas que suportam marchas e batalha.",
        "media_key": "item_botas_ferro_guerreiro",
        "class_req": ["guerreiro"]
    },
    "luvas_ferro_guerreiro": {
        "display_name": "Luvas de Ferro do Guerreiro", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "description": "Luvas que firmam o golpe.",
        "media_key": "item_luvas_ferro_guerreiro",
        "class_req": ["guerreiro"]
    },
    "anel_ferro_guerreiro": {
        "display_name": "Anel de Ferro do Guerreiro", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "description": "Anel simples que inspira bravura.",
        "media_key": "item_anel_ferro_guerreiro",
        "class_req": ["guerreiro"]
    },
    "colar_ferro_guerreiro": {
        "display_name": "Colar de Ferro do Guerreiro", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "description": "Colar que simboliza determinação.",
        "media_key": "item_colar_ferro_guerreiro",
        "class_req": ["guerreiro"]
    },
    "brinco_ferro_guerreiro": {
        "display_name": "Brinco de Ferro do Guerreiro", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "description": "Brinco que reforça o espírito combativo.",
        "media_key": "item_brinco_ferro_guerreiro",
        "class_req": ["guerreiro"]
    },

# ---------- RESULTADOS DE CRAFT — GUERREIRO T2 ----------
    "espada_aco_guerreiro": {
        "display_name": "Espada de Aço do Guerreiro",
        "emoji": "🗡️",
        "type": "arma",
        "category": "equipamento",
        "description": "Lâmina de aço balanceada para combate pesado.",
        "stackable": False,
        "media_key": "item_espada_aco_guerreiro",
        "class_req": ["guerreiro"]
    },
    "elmo_aco_guerreiro": {
        "display_name": "Elmo de Aço do Guerreiro",
        "emoji": "🪖",
        "type": "elmo",
        "category": "equipamento",
        "description": "Elmo robusto forjado em aço.",
        "stackable": False,
        "media_key": "item_elmo_aco_guerreiro",
        "class_req": ["guerreiro"]
    },
    "peitoral_aco_guerreiro": {
        "display_name": "Peitoral de Aço do Guerreiro",
        "emoji": "👕",
        "type": "armadura",
        "category": "equipamento",
        "description": "Armadura de aço que protege o torso.",
        "stackable": False,
        "media_key": "item_peitoral_aco_guerreiro",
        "class_req": ["guerreiro"]
    },
    "calcas_aco_guerreiro": {
        "display_name": "Calças de Aço do Guerreiro",
        "emoji": "👖",
        "type": "calca",
        "category": "equipamento",
        "description": "Calças reforçadas com placas metálicas.",
        "stackable": False,
        "media_key": "item_calcas_aco_guerreiro",
        "class_req": ["guerreiro"]
    },
    "botas_aco_guerreiro": {
        "display_name": "Botas de Aço do Guerreiro",
        "emoji": "🥾",
        "type": "botas",
        "category": "equipamento",
        "description": "Botas pesadas que garantem firmeza no combate.",
        "stackable": False,
        "media_key": "item_botas_aco_guerreiro",
        "class_req": ["guerreiro"]
    },
        
    "luvas_aco_guerreiro": {
        "display_name": "Luvas de Aço do Guerreiro",
        "emoji": "🧤",
        "type": "luvas",
        "category": "equipamento",
        "description": "Luvas protegidas para golpes e empunhadura segura.",
        "stackable": False,
        "media_key": "item_luvas_aco_guerreiro",
        "class_req": ["guerreiro"]
    },
    "anel_aco_guerreiro": {
        "display_name": "Anel de Aço do Guerreiro",
        "emoji": "💍",
        "type": "anel",
        "category": "equipamento",
        "description": "Anel de aço imbuído de poder marcial.",
        "stackable": False,
        "media_key": "item_anel_aco_guerreiro",
        "class_req": ["guerreiro"]
    },
    "colar_aco_guerreiro": {
        "display_name": "Colar de Aço do Guerreiro",
        "emoji": "📿",
        "type": "colar",
        "category": "equipamento",
        "description": "Colar robusto que inspira coragem.",
        "stackable": False,
        "media_key": "item_colar_aco_guerreiro",
        "class_req": ["guerreiro"]
    },
    "brinco_aco_guerreiro": {
        "display_name": "Brinco de Aço do Guerreiro",
        "emoji": "🧿",
        "type": "brinco",
        "category": "equipamento",
        "description": "Brinco que simboliza honra em batalha.",
        "stackable": False,
        "media_key": "item_brinco_aco_guerreiro",
        "class_req": ["guerreiro"]

    },

    # ================================
    # ITENS RESULTANTES — Mago T1
    # ================================
    "cajado_aprendiz_mago": {
        "display_name": "Cajado de Aprendiz", "emoji": "🪄",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "description": "Cajado básico que canaliza energias arcanas.",
        "media_key": "item_cajado_aprendiz_mago",
        "class_req": ["mago"]
    },
    "chapeu_seda_mago": {
        "display_name": "Chapéu de Seda do Mago", "emoji": "🎩",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "description": "Chapéu leve, tradicional entre aprendizes.",
        "media_key": "item_chapel_seda_mago",
        "class_req": ["mago"]
    },
    "tunica_seda_mago": {
        "display_name": "Túnica de Seda do Mago", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "description": "Veste encantada para estudos arcanos.",
        "media_key": "item_tunica_seda_mago",
        "class_req": ["mago"]
    },
    "calcas_seda_mago": {
        "display_name": "Calças de Seda do Mago", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "description": "Calças confortáveis que não restringem movimentos.",
        "media_key": "item_calcas_seda_mago",
        "class_req": ["mago"]
    },
    "botas_seda_mago": {
        "display_name": "Botas de Seda do Mago", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "description": "Botas leves feitas para longas jornadas.",
        "media_key": "item_botas_seda_mago",
        "class_req": ["mago"]
    },
    "luvas_seda_mago": {
        "display_name": "Luvas de Seda do Mago", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "description": "Luvas que ajudam no controle dos feitiços.",
        "media_key": "item_luvas_seda_mago",
        "class_req": ["mago"]
    },
    "anel_gema_mago": {
        "display_name": "Anel de Gema do Mago", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "description": "Anel engastado que amplifica o foco arcano.",
        "media_key": "item_anel_gema_mago",
        "class_req": ["mago"]
    },
    "colar_gema_mago": {
        "display_name": "Colar de Gema do Mago", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "description": "Colar que pulsa com energia latente.",
        "media_key": "item_colar_gema_mago",
        "class_req": ["mago"]
    },
    "brinco_gema_mago": {
        "display_name": "Brinco de Gema do Mago", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "description": "Brinco que sussurra segredos arcanos.",
        "media_key": "item_brinco_gema_mago",
        "class_req": ["mago"]
    },

# --- Conjunto do Mago T2 ---
    "cajado_arcano_mago": {
        "display_name": "Cajado Arcano",
        "emoji": "🪄",
        "type": "arma",
        "slot": "arma",
        "class_req": ["mago"],
        "media_key": "item_cajado_arcano_mago",
        "class_req": ["mago"]
},
"chapeu_veludo_mago": {
    "display_name": "Chapéu de Veludo do Mago",
    "emoji": "🎩",
    "type": "equipamento",
    "slot": "elmo",
    "media_key": "item_chapel_veludo_mago",
    "class_req": ["mago"]
},
"tunica_veludo_mago": {
    "display_name": "Túnica de Veludo do Mago",
    "emoji": "👕",
    "type": "equipamento",
    "slot": "armadura",
    "media_key": "item_tunica_veludo_mago",
    "class_req": ["mago"]
},
"calcas_veludo_mago": {
    "display_name": "Calças de Veludo do Mago",
    "emoji": "👖",
    "type": "equipamento",
    "slot": "calca",
    "media_key": "item_calca_veludo_mago",
    "class_req": ["mago"]
},
"botas_veludo_mago": {
    "display_name": "Botas de Veludo do Mago",
    "emoji": "🥾",
    "type": "equipamento",
    "slot": "botas",
    "media_key": "item_botas_veludo_mago",
    "class_req": ["mago"]
},
"luvas_veludo_mago": {
    "display_name": "Luvas de Veludo do Mago",
    "emoji": "🧤",
    "type": "equipamento",
    "slot": "luvas",
    "media_key": "item_luvas_veludo_mago",
    "class_req": ["mago"]
},
"anel_runico_mago": {
    "display_name": "Anel Rúnico do Mago",
    "emoji": "💍",
    "type": "equipamento",
    "slot": "anel",
    "media_key": "item_anel_runico_mago",
    "class_req": ["mago"]
},
"colar_runico_mago": {
    "display_name": "Colar Rúnico do Mago",
    "emoji": "📿",
    "type": "equipamento",
    "slot": "colar",
    "media_key": "item_colar_runico_mago",
    "class_req": ["mago"]
},
"brinco_runico_mago": {
    "display_name": "Brinco Rúnico do Mago",
    "emoji": "🧿",
    "type": "equipamento",
    "slot": "brinco",
    "class_req": ["mago"],
    "media_key": "item_brinco_runico_mago",
    
},

    # ================================
    # ITENS RESULTANTES — Monge T1
    # ================================
    "manoplas_iniciado_monge": {
        "display_name": "Manoplas de Iniciado", "emoji": "🤜",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "description": "Manoplas simples usadas por monges em treinamento.",
        "media_key": "item_manoplas_iniciado_monge",
        "class_req": ["mago"]
    },
    "bandana_iniciado_monge": {
        "display_name": "Bandana de Iniciado", "emoji": "🪖",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "description": "Bandana leve que ajuda na concentração.",
        "media_key": "item_bandana_iniciado_monge",
        "class_req": ["mago"]

    },
    "gi_iniciado_monge": {
        "display_name": "Gi de Iniciado", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "description": "Roupa tradicional de treinamento monástico.",
        "media_key": "item_gi_iniciado_monge",
        "class_req": ["mago"]
    },
    "calcas_iniciado_monge": {
        "display_name": "Calças de Iniciado", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "description": "Calças leves para liberdade de movimento.",
        "media_key": "item_calcas_iniciado_monge",
        "class_req": ["mago"]
    },
    "sandalias_iniciado_monge": {
        "display_name": "Sandálias de Iniciado", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "description": "Sandálias tradicionais, leves e práticas.",
        "media_key": "item_sandalias_iniciado_monge",
        "class_req": ["mago"]
    },
    "faixas_iniciado_monge": {
        "display_name": "Faixas de Mão de Iniciado", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "description": "Faixas de tecido usadas para proteger as mãos.",
        "media_key": "item_faixas_iniciado_monge",
        "class_req": ["mago"]
    },
    "anel_iniciado_monge": {
        "display_name": "Anel de Iniciado", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "description": "Anel simples usado em rituais de foco espiritual.",
        "media_key": "item_anel_iniciado_monge",
        "class_req": ["mago"]
    },
    "colar_iniciado_monge": {
        "display_name": "Colar de Iniciado", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "description": "Colar com contas que auxiliam na meditação.",
        "media_key": "item_colar_iniciado_monge",
        "class_req": ["mago"]
    },
    "brinco_iniciado_monge": {
        "display_name": "Brinco de Iniciado", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "description": "Brinco que simboliza disciplina e equilíbrio.",
        "media_key": "item_brinco_iniciado_monge",
        "class_req": ["mago"]
    },

# --- EQUIPAMENTOS DO MONGE T2 (MESTRE) ---

    "manoplas_mestre_monge": {
        "display_name": "Manoplas de Mestre", "emoji": "🤜",
        "slot": "arma", "type": "arma",
        "description": "Manoplas reforçadas que concentram a força física e espiritual do mestre monge.",
        "media_key": "item_manoplas_mestre_monge",
        "class_req": ["monge"]
        
    },
    "bandana_mestre_monge": {
        "display_name": "Bandana de Mestre", "emoji": "🪖",
        "slot": "elmo", "type": "armadura",
        "description": "Faixa sagrada que auxilia na clareza mental durante as batalhas.",
        "media_key": "item_manoplas_mestre_monge",
        "class_req": ["monge"]  
        
    },
    "gi_mestre_monge": {
        "display_name": "Gi de Mestre", "emoji": "👕",
        "slot": "armadura", "type": "armadura",
        "description": "Traje cerimonial que amplia a resistência e a conexão espiritual do monge.",
        "media_key": "item_gi_mestre_monge",
        "class_req": ["monge"]
        
    },
    "calcas_mestre_monge": {
        "display_name": "Calças de Mestre", "emoji": "👖",
        "slot": "calca", "type": "armadura",
        "description": "Calças leves que permitem movimentos ágeis sem perder a proteção.",
        "media_key": "item_calcas_mestre_monge",
        "class_req": ["monge"]
        
    },
    "sandalias_mestre_monge": {
        "display_name": "Sandálias de Mestre", "emoji": "🥾",
        "slot": "botas", "type": "armadura",
        "description": "Sandálias ritualísticas que mantêm o equilíbrio do corpo e da mente.",
        "media_key": "item_sandalias_mestre_monge",
        "class_req": ["monge"]
        
    },
    "faixas_mestre_monge": {
        "display_name": "Faixas de Mão de Mestre", "emoji": "🧤",
        "slot": "luvas", "type": "armadura",
        "description": "Faixas encantadas que potencializam os golpes de punho.",
        "media_key": "item_faixas_mestre_monge",
        "class_req": ["monge"]
        
    },
    "anel_mestre_monge": {
        "display_name": "Anel de Mestre", "emoji": "💍",
        "slot": "anel", "type": "acessorio",
        "description": "Anel sagrado que simboliza a disciplina e aumenta o foco espiritual.",
        "media_key": "item_anel_mestre_monge",
        "class_req": ["monge"]
        
    },
    "colar_mestre_monge": {
        "display_name": "Colar de Mestre", "emoji": "📿",
        "slot": "colar", "type": "acessorio",
        "description": "Colar de contas antigas, usado em meditações profundas para canalizar energia.",
        "media_key": "item_colar_mestre_monge",
        "class_req": ["monge"]
        
    },
    "brinco_mestre_monge": {
        "display_name": "Brinco de Mestre", "emoji": "🧿",
        "slot": "brinco", "type": "acessorio",
        "description": "Brinco talismânico que protege contra más influências espirituais.",
        "media_key": "item_brincos_mestre_monge",
        "class_req": ["monge"]
        
    },

    # ================================
    # ITENS RESULTANTES — Samurai T1
    # ================================
    "katana_laminada_samurai": {
        "display_name": "Katana Laminada", "emoji": "⚔️",
        "slot": "arma", "type": "equipamento", "category": "arma",
        "description": "Lâmina laminada e flexível, símbolo do clã.",
        "media_key": "item_katana_laminada_samurai",
        "class_req": ["samurai"]

    },
    "kabuto_laminado_samurai": {
        "display_name": "Kabuto Laminado", "emoji": "🪖",
        "slot": "elmo", "type": "equipamento", "category": "armadura",
        "description": "Elmo tradicional com placas sobrepostas.",
        "media_key": "item_kabuto_laminada_samurai",
        "class_req": ["samurai"]

    },
    "do_laminado_samurai": {
        "display_name": "Do Laminado", "emoji": "👕",
        "slot": "armadura", "type": "equipamento", "category": "armadura",
        "description": "Peitoral em múltiplas lamelas de metal.",
        "media_key": "item_do_laminada_samurai",
        "class_req": ["samurai"]

    },
    "haidate_laminado_samurai": {
        "display_name": "Haidate Laminado", "emoji": "👖",
        "slot": "calca", "type": "equipamento", "category": "armadura",
        "description": "Proteções de coxa em placas flexíveis.",
        "media_key": "item_haidate_laminada_samurai",
        "class_req": ["samurai"]

    },
    "suneate_laminado_samurai": {
        "display_name": "Suneate Laminado", "emoji": "🥾",
        "slot": "botas", "type": "equipamento", "category": "armadura",
        "description": "Grevas laminadas para mobilidade e defesa.",
        "media_key": "item_suneate_laminada_samurai",
        "class_req": ["samurai"]
    },
    "kote_laminado_samurai": {
        "display_name": "Kote Laminado", "emoji": "🧤",
        "slot": "luvas", "type": "equipamento", "category": "armadura",
        "description": "Braçais com placas entrelaçadas.",
        "media_key": "item_kote_laminada_samurai",
        "class_req": ["samurai"]
    },
    "anel_laminado_samurai": {
        "display_name": "Anel Laminado", "emoji": "💍",
        "slot": "anel", "type": "equipamento", "category": "acessorio",
        "description": "Símbolo de lealdade ao clã.",
        "media_key": "item_anel_laminada_samurai",
        "class_req": ["samurai"]
    },
    "colar_laminado_samurai": {
        "display_name": "Colar Laminado", "emoji": "📿",
        "slot": "colar", "type": "equipamento", "category": "acessorio",
        "description": "Contas e placas representando honra.",
        "media_key": "item_colar_laminada_samurai",
        "class_req": ["samurai"]
    },
    "brinco_laminado_samurai": {
        "display_name": "Brinco Laminado", "emoji": "🧿",
        "slot": "brinco", "type": "equipamento", "category": "acessorio",
        "description": "Peça discreta, mas cheia de tradição.",
        "media_key": "item_brinco_laminada_samurai",
        "class_req": ["samurai"]
    },
# --- RESULTADOS DE CRAFT: SAMURAI T2 (display no inventário/market) ---
    
 
    "katana_damasco_samurai": {
        "display_name": "Katana de Aço Damasco", "emoji": "⚔️",
        "type": "equipamento", "category": "equipamento",
        "description": "Uma lâmina de aço damasco, forjada para a perfeição.",
        "stackable": False,
        "media_key": "item_katana_damasco_samurai",
        "class_req": ["samurai"]
    },

    "kabuto_damasco_samurai": {
        "display_name": "Kabuto de Aço Damasco", "emoji": "🪖",
        "type": "equipamento", "category": "equipamento",
        "description": "Elmo laminado de aço damasco.",
        "stackable": False,
        "media_key": "item_kabuto_damasco_samurai",
        "class_req": ["samurai"]
    },
    "do_damasco_samurai": {
        "display_name": "Do de Aço Damasco", "emoji": "👕",
        "type": "equipamento", "category": "equipamento",
        "description": "Peitoral laminado de aço damasco.",
        "stackable": False,
        "media_key": "item_do_damasco_samurai",
        "class_req": ["samurai"]
    },
    "haidate_damasco_samurai": {
        "display_name": "Haidate de Aço Damasco", "emoji": "👖",
        "type": "equipamento", "category": "equipamento",
        "description": "Grevas laminadas para proteção das pernas.",
        "stackable": False,
        "media_key": "item_haidate_damasco_samurai",
        "class_req": ["samurai"]
    },
    "suneate_damasco_samurai": {
        "display_name": "Suneate de Aço Damasco", "emoji": "🥾",
        "type": "equipamento", "category": "equipamento",
        "description": "Proteções das canelas em aço damasco.",
        "stackable": False,
        "media_key": "item_suneate_damasco_samurai",
        "class_req": ["samurai"]
    },
    "kote_damasco_samurai": {
        "display_name": "Kote de Aço Damasco", "emoji": "🧤",
        "type": "equipamento", "category": "equipamento",
        "description": "Braçadeiras/luvas reforçadas para o samurai.",
        "stackable": False,
        "media_key": "item_kote_damasco_samurai",
        "class_req": ["samurai"]
    },
    
    "anel_damasco_samurai": {
        "display_name": "Anel de Aço Damasco", "emoji": "💍",
        "type": "equipamento", "category": "equipamento",
        "description": "Anel de honra forjado em aço damasco.",
        "stackable": False,
        "media_key": "item_anel_damasco_samurai",
        "class_req": ["samurai"]
    },
    "colar_damasco_samurai": {
        "display_name": "Colar de Aço Damasco", "emoji": "📿",
        "type": "equipamento", "category": "equipamento",
        "description": "Colar que simboliza a disciplina do clã.",
        "stackable": False,
        "media_key": "item_colar_damasco_samurai",
        "class_req": ["samurai"]
    },
    "brinco_damasco_samurai": {
        "display_name": "Brinco de Aço Damasco", "emoji": "🧿",
        "type": "equipamento", "category": "equipamento",
        "description": "Brinco forjado com laminações delicadas.",
        "stackable": False,
        "media_key": "item_brinco_damasco_samurai",
        "class_req": ["samurai"]
    },

}

ITEMS_DATA["ferro"] = ITEMS_DATA["minerio_de_ferro"]

# Alguns módulos antigos ainda esperam ITEM_BASES apontando para uma tabela de itens.
ITEM_BASES = ITEMS_DATA
MARKET_ITEMS = list(ITEMS_DATA.keys())
ITEMS = ITEMS_DATA

def get_item(item_id: str):
    return ITEMS_DATA.get(item_id)

def is_stackable(item_id: str) -> bool:
    meta = ITEMS_DATA.get(item_id) or {}
    return bool(meta.get("stackable", True))

def get_display_name(item_id: str) -> str:
    meta = ITEMS_DATA.get(item_id) or {}
    return meta.get("display_name", item_id)


# 2) Nomes das peças citadas no set da dungeon (apenas display)
ITEMS_DATA.update({
    "peitoral_coracao_umbrio": {
        "display_name": "Peitoral do Coração Umbrio", "emoji": "🛡️",
        "type": "equipamento", "category": "armadura",
        "description": "Uma couraça pulsante com ecos da floresta sombria.",
        "stackable": False,
    },
    "manto_coracao_umbrio": {
        "display_name": "Manto do Coração Umbrio", "emoji": "🧥",
        "type": "equipamento", "category": "armadura",
        "description": "Tecidos enfeitiçados que latejam como raízes vivas.",
        "stackable": False,
    },
})

# 3) Corrige tipo/descrição da chave da catacumba (se existir com erro)
if "chave_da_catacumba" in ITEMS_DATA:
    ITEMS_DATA["chave_da_catacumba"]["type"] = "especial"
    ITEMS_DATA["chave_da_catacumba"]["category"] = "especial"
    ITEMS_DATA["chave_da_catacumba"]["description"] = "Chave da Catacumba do Reino."

# ============================================================
# Itens de Evolução de Classe (Tier 2 e Tier 3)
# - Compatível com o schema deste arquivo
# - Merge seguro: não sobrescreve se o ID já existir
# - Atualiza MARKET_ITEMS se for dict (com preço) ou list (apenas exibição)
# ============================================================

def _register_item_safe(item_id: str, data: dict, market_price: int | None = None):
    """Adiciona o item se ainda não existir. Opcionalmente registra no MARKET_ITEMS."""
    if item_id not in ITEMS_DATA:
        ITEMS_DATA[item_id] = data

    # Ajusta MARKET_ITEMS (há projetos que usam dict e outros que usam list)
    try:
        # se for dict de catálogo fixo
        if isinstance(MARKET_ITEMS, dict) and market_price is not None:
            MARKET_ITEMS[item_id] = {"price": int(market_price), "currency": "gold", "tradeable": bool(data.get("tradable", True))}
        # se for list (seu arquivo atual faz MARKET_ITEMS = list(ITEMS_DATA.keys()))
        elif isinstance(MARKET_ITEMS, list) and item_id not in MARKET_ITEMS:
            MARKET_ITEMS.append(item_id)
    except NameError:
        # se MARKET_ITEMS ainda não existe aqui, ignore
        pass

# -----------------------------
# Emblemas (Tier 2 – chave por classe)
# -----------------------------
_EVOLUTION_EMBLEMS = {
    "emblema_guerreiro": {"display_name": "Emblema do Guerreiro", "emoji": "⚔️", "desc": "Requisito para evoluções do Guerreiro."},
    "emblema_berserker": {"display_name": "Emblema do Berserker", "emoji": "🪓", "desc": "Requisito para evoluções do Berserker."},
    "emblema_cacador":   {"display_name": "Emblema do Caçador",   "emoji": "🏹", "desc": "Requisito para evoluções do Caçador."},
    "emblema_monge":     {"display_name": "Emblema do Monge",     "emoji": "🧘", "desc": "Requisito para evoluções do Monge."},
    "emblema_mago":      {"display_name": "Emblema do Mago",      "emoji": "🪄", "desc": "Requisito para evoluções do Mago."},
    "emblema_bardo":     {"display_name": "Emblema do Bardo",     "emoji": "🎶", "desc": "Requisito para evoluções do Bardo."},
    "emblema_assassino": {"display_name": "Emblema do Assassino", "emoji": "🔪", "desc": "Requisito para evoluções do Assassino."},
    "emblema_samurai":   {"display_name": "Emblema do Samurai",   "emoji": "🥷", "desc": "Requisito para evoluções do Samurai."},
}
for _id, _v in _EVOLUTION_EMBLEMS.items():
    _register_item_safe(_id, {
        "display_name": _v["display_name"], "emoji": _v["emoji"],
        "type": "especial", "category": "evolucao",
        "description": _v["desc"],
        "stackable": True, "tradable": True,
    }, market_price=500)

# -----------------------------
# Essências (consumíveis para T2/T3)
# -----------------------------
_EVOLUTION_ESSENCES = {
    "essencia_guardia":    ("Essência da Guarda",     "🛡️", "Energia protetora usada em evoluções defensivas."),
    "essencia_furia":      ("Essência da Fúria",      "💢", "Energia bruta para evoluções ofensivas."),
    "essencia_luz":        ("Essência da Luz",        "✨", "Luz sagrada para evoluções de ordem/templárias."),
    "essencia_sombra":     ("Essência das Sombras",   "🌑", "Sombras condensadas para evoluções furtivas."),
    "essencia_precisao":   ("Essência da Precisão",   "🎯", "Foco absoluto para tiros certeiros."),
    "essencia_fera":       ("Essência da Fera",       "🐾", "Instintos selvagens canalizados."),
    "essencia_ki":         ("Essência do Ki",         "🌀", "Força vital do corpo e da mente."),
    "essencia_arcana":     ("Essência Arcana",        "🔮", "Poder arcano concentrado."),
    "essencia_elemental":  ("Essência Elemental",     "🌩️", "Sinergia de fogo, gelo e raio."),
    "essencia_harmonia":   ("Essência da Harmonia",   "🎵", "Ressonância musical que fortalece aliados."),
    "essencia_encanto":    ("Essência do Encanto",    "🧿", "Magia sutil que influencia mentes."),
    "essencia_letal":      ("Essência Letal",         "☠️", "Venenos e precisão cirúrgica."),
    "essencia_corte":      ("Essência do Corte",      "🗡️", "Afiamento de lâminas e técnicas de espada."),
    "essencia_disciplina": ("Essência da Disciplina", "📏", "Controle técnico e foco do samurai."),
}
for _id, (_name, _emoji, _desc) in _EVOLUTION_ESSENCES.items():
    _register_item_safe(_id, {
        "display_name": _name, "emoji": _emoji,
        "type": "material_magico", "category": "evolucao",
        "description": _desc,
        "stackable": True, "tradable": True,
    }, market_price=220)

# -----------------------------
# Relíquias / Chaves (Tier 3)
# -----------------------------
_EVOLUTION_RELICS = {
    "selo_sagrado":     ("Selo Sagrado",        "🕊️", "Símbolo de devoção. Necessário para Templário."),
    "totem_ancestral":  ("Totem Ancestral",     "🪵", "Canaliza a fúria antiga. Necessário para Ira Primordial."),
    "marca_predador":   ("Marca do Predador",   "🐺", "Selo do caçador supremo. Necessário para Mestre Caçador."),
    "reliquia_mistica": ("Relíquia Mística",    "🔱", "Artefato de ki e luz. Necessário para Santo Asceta."),
    "grimorio_arcano":  ("Grimório Arcano",     "📘", "Tomo proibido. Necessário para Arquimago."),
    "batuta_maestria":  ("Batuta da Maestria",  "🎼", "Domínio absoluto da sinfonia. Necessário para Maestro."),
    "manto_eterno":     ("Manto Eterno",        "🕯️", "Tecidos da noite. Necessário para Sombra Inexorável."),
    "lamina_sagrada":   ("Lâmina Sagrada",      "⚔️", "Katana abençoada. Necessária para Iaijutsu."),
}
for _id, (_name, _emoji, _desc) in _EVOLUTION_RELICS.items():
    _register_item_safe(_id, {
        "display_name": _name, "emoji": _emoji,
        "type": "especial", "category": "evolucao",
        "description": _desc,
        "stackable": False, "tradable": False,
    }, market_price=None)  # geralmente não vendáveis; mude para um preço se quiser

# === Itens de evolução: só negociam por GEMAS ===
EVOLUTION_GEMS_ONLY = {
    "emblema_guerreiro",
    "essencia_guardia",
    "essencia_furia",
    "selo_sagrado",
    "essencia_luz",
    "emblema_berserker",
    "totem_ancestral",
    "emblema_cacador",
    "essencia_precisao",
    "marca_predador",
    "essencia_fera",
    "emblema_monge",
    "reliquia_mistica",
    "essencia_ki",
    "emblema_mago",
    "essencia_arcana",
    "essencia_elemental",
    "grimorio_arcano",
    "emblema_bardo",
    "essencia_harmonia",
    "essencia_encanto",
    "batuta_maestria",
    "emblema_assassino",
    "essencia_sombra",
    "essencia_letal",
    "manto_eterno",
    "emblema_samurai",
    "essencia_corte",
    "essencia_disciplina",
    "lamina_sagrada",
}

def apply_evolution_gem_flags():
    global ITEMS_DATA
    items = ITEMS_DATA or {}
    for iid in EVOLUTION_GEMS_ONLY:
        meta = items.get(iid) or {}
        meta["evolution_item"] = True
        meta["market_currency"] = "gems"
        items[iid] = meta
    ITEMS_DATA = items

# chamar na importação
try:
    apply_evolution_gem_flags()
except Exception:
    pass

# -----------------------------
# Pequeno fix em item existente com typo (se houver)
# -----------------------------
if "chave_da_catacumba" in ITEMS_DATA:
    ITEMS_DATA["chave_da_catacumba"]["type"] = "especial"
    ITEMS_DATA["chave_da_catacumba"]["category"] = "especial"
    ITEMS_DATA["chave_da_catacumba"]["description"] = "Chave da Catacumba do Reino."
