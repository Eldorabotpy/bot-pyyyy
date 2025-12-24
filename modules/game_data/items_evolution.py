# modules/game_data/items_evolution.py
# ARQUIVO COMPLETO: Emblemas, Materiais, Essências, Almas e Divinos.

# 1. CRIA O DICIONÁRIO VAZIO (Essencial para não dar erro de 'not defined')
EVOLUTION_ITEMS_DATA = {}

# ==============================================================================
# 1. EMBLEMAS DE CLASSE (Tier 1 -> Tier 2)
# ==============================================================================
_EVOLUTION_EMBLEMS = {
    "emblema_guerreiro": "⚔️", "emblema_berserker": "🪓", "emblema_cacador": "🏹",
    "emblema_monge": "🧘", "emblema_mago": "🪄", "emblema_bardo": "🎶",
    "emblema_assassino": "🔪", "emblema_samurai": "🥷", "emblema_cura": "⚕️"
}
for cls, emo in _EVOLUTION_EMBLEMS.items():
    EVOLUTION_ITEMS_DATA[cls] = {
        "display_name": f"Emblema: {cls.split('_')[1].title()}", 
        "emoji": emo,
        "type": "especial", "category": "evolucao", 
        "description": "Símbolo de maestria básica da classe.",
        "stackable": True, "tradable": True, 
        "evolution_item": True, "market_currency": "gems"
    }

# ==============================================================================
# 2. MATERIAIS ESPECÍFICOS DE CLASSE (BÁSICOS)
# ==============================================================================
_SPECIFIC_MATS = [
    ("lamina_afiada", "Lâmina Afiada", "🗡️", "Lâmina perfeitamente balanceada."),
    ("poeira_sombria", "Poeira Sombria", "🌫️", "Restos de uma sombra materializada."),
    ("aco_sombrio", "Aço Sombrio", "⚫", "Metal que não reflete luz."),
    ("corda_encantada", "Corda Encantada", "🪕", "Corda de instrumento que nunca quebra."),
    ("partitura_antiga", "Partitura Antiga", "🎼", "Músicas de uma era esquecida."),
    ("cristal_sonoro", "Cristal Sonoro", "💎", "Ressoa com magia musical."),
    ("aco_tamahagane", "Aço Tamahagane", "⚔️", "Aço lendário dobrado mil vezes."),
    ("tomo_bushido", "Tomo do Bushido", "📜", "Ensinamentos sobre honra e espada."),
    ("placa_forjada", "Placa Forjada", "🛡️", "Metal reforçado para armaduras pesadas."),
    ("lente_infalivel", "Lente Infalível", "🧐", "Permite ver detalhes a quilômetros."),
    ("arco_fantasma", "Arco Fantasma", "🏹", "Um arco translúcido e etéreo."),
    ("pergaminho_celestial", "Pergaminho Celestial", "📜", "Escrituras divinas."),
    ("foco_cristalino", "Foco Cristalino", "🔮", "Amplifica magia elemental."),
    ("coracao_do_colosso", "Coração do Colosso", "🗿", "Núcleo de pedra pulsante."),
    ("coracao_da_furia", "Coração da Fúria", "❤️‍🔥", "Órgão que queima eternamente.")
]

for mid, mname, memo, mdesc in _SPECIFIC_MATS:
    EVOLUTION_ITEMS_DATA[mid] = {
        "display_name": mname,
        "emoji": memo,
        "type": "material_especial", 
        "category": "evolucao", 
        "description": mdesc,
        "stackable": True,
        "evolution_item": True 
    }

# ==============================================================================
# 3. ESSÊNCIAS DE CLASSE (Tier 2 e 3)
# ==============================================================================
_ESSENCES_DATA = [
    # Guerreiro / Paladino
    ("essencia_guardia", "Essência do Guardião", "🛡️", "Energia condensada de proteção inabalável."),
    ("essencia_luz", "Essência da Luz", "✨", "Brilho sagrado usado por paladinos e clérigos."),
    # Berserker
    ("essencia_furia", "Essência da Fúria", "🔥", "A manifestação física da raiva incontrolável."),
    # Caçador
    ("essencia_precisao", "Essência da Precisão", "🎯", "Foco absoluto cristalizado em forma mágica."),
    # Monge
    ("essencia_ki", "Essência de Ki", "🧘", "Energia vital pura extraída através de meditação."),
    # Mago
    ("essencia_elemental", "Essência Elemental", "🌀", "Um vórtice instável de fogo, gelo e raio."),
    # Assassino
    ("essencia_venenosa", "Essência Venenosa", "☠️", "Toxina mágica letal concentrada."),
    # Curandeiro
    ("essencia_fe", "Essência da Fé", "🙏", "O poder da crença materializado."),
]

for eid, ename, emoji, edesc in _ESSENCES_DATA:
    EVOLUTION_ITEMS_DATA[eid] = {
        "display_name": ename,
        "emoji": emoji,
        "type": "essencia",
        "category": "evolucao",
        "description": edesc,
        "stackable": True,
        "evolution_item": True
    }

# ==============================================================================
# 4. MATERIAIS ESPECÍFICOS FALTANTES (Tier 3 e 4)
# ==============================================================================
_MISSING_MATS = [
    # Guerreiro
    ("selo_sagrado", "Selo Sagrado", "🔱", "Um selo abençoado por antigas divindades da guerra."),
    # Berserker
    ("totem_ancestral", "Totem Ancestral", "🗿", "Um totem tribal que pulsa com tambores de guerra."),
    # Monge
    ("reliquia_mistica", "Relíquia Mística", "📿", "Contas de oração de um antigo mestre."),
    # Mago
    ("grimorio_arcano", "Grimório Arcano", "📘", "Livro flutuante contendo segredos proibidos."),
    # Curandeiro
    ("pergaminho_sagrado", "Pergaminho Sagrado", "📜", "Escrituras antigas de cura e ressurreição."),
    ("calice_da_luz", "Cálice da Luz", "🏆", "Um cálice que transborda água sagrada infinita.")
]

for mid, mname, memo, mdesc in _MISSING_MATS:
    EVOLUTION_ITEMS_DATA[mid] = {
        "display_name": mname,
        "emoji": memo,
        "type": "material_especial",
        "category": "evolucao",
        "description": mdesc,
        "stackable": True,
        "evolution_item": True
    }

# ==============================================================================
# 5. ITENS DE ALTA EVOLUÇÃO (Tier 5 - Nível 80 - Almas e Puros)
# ==============================================================================
_HIGH_TIER_DATA = [
    # Guerreiro
    ("alma_do_guardiao", "Alma do Guardião", "👻", "O espírito de um herói que morreu protegendo outros."),
    ("essencia_luz_pura", "Luz Pura Condensada", "🌟", "Luz tão forte que cega os indignos."),
    # Berserker
    ("alma_da_furia", "Alma da Fúria", "👹", "Um espírito consumido pela raiva eterna."),
    ("essencia_furia_pura", "Fúria Líquida", "🩸", "O sangue fervente de um deus da guerra."),
    # Caçador
    ("alma_da_precisao", "Alma da Precisão", "👁️", "O olho de uma entidade que tudo vê."),
    ("essencia_precisao_pura", "Foco Divino", "🔭", "Permite enxergar além da realidade."),
    # Monge
    ("alma_do_ki", "Alma do Ki", "🐉", "A manifestação espiritual de um dragão interior."),
    ("essencia_ki_pura", "Ki Celestial", "🌥️", "Energia vital refinada ao nível dos deuses."),
    # Mago
    ("alma_elemental", "Alma Elemental", "🌋", "O núcleo vivo de um planeta."),
    ("essencia_elemental_pura", "Éter Puro", "🌌", "A matéria-prima da criação mágica."),
    # Bardo
    ("espirito_musica", "Espírito da Música", "🎼", "Uma melodia viva que nunca termina."),
    ("frequencia_pura", "Frequência Pura", "🔊", "O som primordial que criou o universo."),
    # Assassino
    ("energia_karmica", "Energia Kármica", "☯️", "O equilíbrio entre a vida e a morte."),
    ("nevoa_da_morte", "Névoa da Morte", "🌫️", "Fumaça fria colhida do submundo."),
    # Samurai
    ("alma_katana", "Alma da Katana", "🗡️", "O espírito que habita uma lâmina lendária."),
    ("aura_bushido", "Aura do Bushido", "💮", "A honra materializada em luz espiritual."),
    # Curandeiro
    ("alma_da_fe", "Alma da Fé", "🛐", "A devoção absoluta de um santo."),
    ("essencia_fe_pura", "Milagre Engarrafado", "🧪", "Líquido dourado capaz de reverter a morte.")
]

for hid, hname, hemo, hdesc in _HIGH_TIER_DATA:
    EVOLUTION_ITEMS_DATA[hid] = {
        "display_name": hname,
        "emoji": hemo,
        "type": "material_lendario",
        "category": "evolucao",
        "description": hdesc,
        "stackable": True,
        "evolution_item": True,
        "rarity": "lendario"
    }

# ==============================================================================
# 6. FRAGMENTOS DIVINOS (Tier 6 - Nível 100 - Lendas)
# ==============================================================================

# Item Global (Todos usam)
EVOLUTION_ITEMS_DATA["essencia_divina_eldora"] = {
    "display_name": "Essência Divina de Eldora",
    "emoji": "🌍",
    "type": "divino",
    "category": "evolucao",
    "description": "O poder bruto do próprio mundo de Eldora. A chave para a divindade.",
    "stackable": True,
    "evolution_item": True,
    "rarity": "mitico",
    "market_currency": "gems"
}

_FRAGMENTS_DATA = [
    ("fragmento_celestial", "Fragmento Celestial", "👼", "Pedaço da armadura de um anjo."),
    ("fragmento_caos", "Fragmento do Caos", "🌀", "Um pedaço da entropia que destrói mundos."),
    ("fragmento_arcano", "Fragmento Arcano", "🔮", "Um pedaço da runa original da magia."),
    ("fragmento_melodia", "Fragmento da Melodia", "🎵", "A primeira nota cantada na criação."),
    ("fragmento_escuridao", "Fragmento da Escuridão", "🌑", "Um pedaço da noite eterna."),
    ("fragmento_espada_original", "Fragmento da Espada Original", "⚔️", "Aço da primeira espada forjada pelos deuses.")
]

for fid, fname, femo, fdesc in _FRAGMENTS_DATA:
    EVOLUTION_ITEMS_DATA[fid] = {
        "display_name": fname,
        "emoji": femo,
        "type": "fragmento_divino",
        "category": "evolucao",
        "description": fdesc,
        "stackable": True,
        "evolution_item": True,
        "rarity": "mitico"
    }