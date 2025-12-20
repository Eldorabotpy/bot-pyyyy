# modules/game_data/items_evolution.py
# (VERSÃO COMPLETA: Contém TODOS os itens da árvore class_evolution.py)

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
# 2. ESSÊNCIAS MÁGICAS (Tier 2 -> Tier 3)
# ==============================================================================
_ESSENCES = [
    ("essencia_guardia", "🛡️"), ("essencia_furia", "💢"), ("essencia_luz", "✨"),
    ("essencia_sombra", "🌑"), ("essencia_precisao", "🎯"), ("essencia_fera", "🐾"),
    ("essencia_ki", "🌀"), ("essencia_arcana", "🔮"), ("essencia_elemental", "🌩️"),
    ("essencia_harmonia", "🎵"), ("essencia_encanto", "🧿"), ("essencia_letal", "☠️"),
    ("essencia_corte", "🗡️"), ("essencia_disciplina", "📏"),
    ("essencia_fe", "🙏"), ("essencia_fe_pura", "🌟"),
    ("essencia_venenosa", "🧪") # Adicionado (Assassino)
]
for eid, emo in _ESSENCES:
    EVOLUTION_ITEMS_DATA[eid] = {
        "display_name": eid.replace("_", " ").title(), 
        "emoji": emo,
        "type": "material_magico", "category": "evolucao", 
        "description": "Essência concentrada de poder puro.",
        "stackable": True, "evolution_item": True, "market_currency": "gems"
    }

# ==============================================================================
# 3. RELÍQUIAS ANTIGAS (Tier 3 -> Tier 4)
# ==============================================================================
_RELICS = [
    "selo_sagrado", "totem_ancestral", "marca_predador", "reliquia_mistica",
    "grimorio_arcano", "batuta_maestria", "manto_eterno", "lamina_sagrada",
    "pergaminho_sagrado", "calice_da_luz", "alma_da_fe"
]
for rid in _RELICS:
    EVOLUTION_ITEMS_DATA[rid] = {
        "display_name": rid.replace("_", " ").title(), 
        "emoji": "🔱",
        "type": "especial", "category": "evolucao", 
        "description": "Uma relíquia antiga vibrando com energia.",
        "stackable": False
    }

# ==============================================================================
# 4. MATERIAIS ESPECÍFICOS DE CLASSE (Tier 2, 3 e 4)
# (Itens usados em nós específicos das árvores)
# ==============================================================================
_SPECIFIC_MATS = [
    # -- Assassino --
    ("lâmina_afiada", "Lâmina Afiada", "🗡️", "Lâmina perfeitamente balanceada."),
    ("lamina_afiada", "Lâmina Afiada", "🗡️", "Alias sem acento."),
    ("poeira_sombria", "Poeira Sombria", "🌫️", "Restos de uma sombra materializada."),
    ("aço_sombrio", "Aço Sombrio", "⚫", "Metal que não reflete luz."),
    
    # -- Bardo --
    ("corda_encantada", "Corda Encantada", "🪕", "Corda de instrumento que nunca quebra."),
    ("partitura_antiga", "Partitura Antiga", "🎼", "Músicas de uma era esquecida."),
    ("cristal_sonoro", "Cristal Sonoro", "💎", "Ressoa com magia musical."),
    
    # -- Samurai --
    ("aco_tamahagane", "Aço Tamahagane", "⚔️", "Aço lendário dobrado mil vezes."),
    ("tomo_bushido", "Tomo do Bushido", "📜", "Ensinamentos sobre honra e espada."),
    ("placa_forjada", "Placa Forjada", "🛡️", "Metal reforçado para armaduras pesadas."),
    
    # -- Caçador --
    ("lente_infalivel", "Lente Infalível", "🧐", "Permite ver detalhes a quilômetros."),
    ("arco_fantasma", "Arco Fantasma", "🏹", "Um arco translúcido e etéreo."),
    
    # -- Monge/Mago/Outros --
    ("pergaminho_celestial", "Pergaminho Celestial", "📜", "Escrituras divinas."),
    ("foco_cristalino", "Foco Cristalino", "🔮", "Amplifica magia elemental."),
    ("coracao_do_colosso", "Coração do Colosso", "🗿", "Núcleo de pedra pulsante."),
    ("coracao_da_furia", "Coração da Fúria", "❤️‍🔥", "Órgão que queima eternamente.")
]

for mid, mname, memo, mdesc in _SPECIFIC_MATS:
    EVOLUTION_ITEMS_DATA[mid] = {
        "display_name": mname,
        "emoji": memo,
        "type": "material", "category": "consumivel",
        "description": mdesc,
        "stackable": True
    }

# ==============================================================================
# 5. ALMAS E ESSÊNCIAS PURAS (Tier 5 - Nível 80)
# ==============================================================================
_TIER5_MATS = [
    # Warrior/Tank
    ("alma_do_guardiao", "🛡️"), ("essencia_luz_pura", "✨"),
    # Berserker
    ("alma_da_furia", "💢"), ("essencia_furia_pura", "🩸"),
    # Hunter
    ("alma_da_precisao", "🎯"), ("essencia_precisao_pura", "🦅"),
    # Monk
    ("alma_do_ki", "🧘"), ("essencia_ki_pura", "🌀"),
    # Mage
    ("alma_elemental", "🌋"), ("essencia_elemental_pura", "⚛️"),
    # Bard
    ("espirito_musica", "🎼"), ("frequencia_pura", "🔊"),
    # Assassin
    ("energia_karmica", "☯️"), ("nevoa_da_morte", "💀"),
    # Samurai
    ("alma_katana", "🗡️"), ("aura_bushido", "👹"),
    # Healer
    ("alma_da_fe", "🙏"), # (Já existe em relics, mas reforçando)
]

for tid, temo in _TIER5_MATS:
    if tid not in EVOLUTION_ITEMS_DATA: # Evita duplicata
        EVOLUTION_ITEMS_DATA[tid] = {
            "display_name": tid.replace("_", " ").title(),
            "emoji": temo,
            "type": "material_lendario", "category": "evolucao",
            "description": "Material de ascensão lendário (Tier 5).",
            "stackable": True
        }

# ==============================================================================
# 6. FRAGMENTOS DIVINOS (Tier 6 - Nível 100)
# ==============================================================================
_GODLY_MATS = [
    ("essencia_divina_eldora", "🌟"), # Usado por todos
    ("fragmento_celestial", "🌤️"),    # Warrior, Monk, Healer, Hunter
    ("fragmento_caos", "🔥"),         # Berserker
    ("fragmento_arcano", "🌌"),       # Mage
    ("fragmento_melodia", "🎶"),      # Bard
    ("fragmento_escuridao", "🌑"),    # Assassin
    ("fragmento_espada_original", "⚔️") # Samurai
]

for gid, gemo in _GODLY_MATS:
    EVOLUTION_ITEMS_DATA[gid] = {
        "display_name": gid.replace("_", " ").title(),
        "emoji": gemo,
        "type": "material_divino", "category": "evolucao",
        "description": "Fragmento do poder de um Deus (Tier 6).",
        "stackable": True
    }