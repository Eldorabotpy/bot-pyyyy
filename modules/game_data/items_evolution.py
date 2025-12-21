# modules/game_data/items_evolution.py

# 1. CRIA O DICIONÁRIO VAZIO PRIMEIRO (Isso corrige o seu erro)
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

# ... (O código das Essências e Relíquias vem aqui) ...

# ==============================================================================
# 4. MATERIAIS ESPECÍFICOS DE CLASSE (O bloco que você enviou)
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
    # AGORA VAI FUNCIONAR, POIS EVOLUTION_ITEMS_DATA JÁ EXISTE
    EVOLUTION_ITEMS_DATA[mid] = {
        "display_name": mname,
        "emoji": memo,
        "type": "material_especial", 
        "category": "evolucao", 
        "description": mdesc,
        "stackable": True,
        "evolution_item": True 
    }