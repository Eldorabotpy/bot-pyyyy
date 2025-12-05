# modules/game_data/items_evolution.py

EVOLUTION_ITEMS_DATA = {}

# 1. Emblemas S
_EVOLUTION_EMBLEMS = {
    "emblema_guerreiro": "⚔️", "emblema_berserker": "🪓", "emblema_cacador": "🏹",
    "emblema_monge": "🧘", "emblema_mago": "🪄", "emblema_bardo": "🎶",
    "emblema_assassino": "🔪", "emblema_samurai": "🥷", 
    "emblema_cura": "⚕️"
}
for cls, emo in _EVOLUTION_EMBLEMS.items():
    EVOLUTION_ITEMS_DATA[cls] = {
        "display_name": f"Emblema: {cls.split('_')[1].title()}", "emoji": emo,
        "type": "especial", "category": "evolucao", "description": "Item de Evolução.",
        "stackable": True, "tradable": True, "evolution_item": True, "market_currency": "gems"
    }

# 2. Essências
_ESSENCES = [
    ("essencia_guardia", "🛡️"), ("essencia_furia", "💢"), ("essencia_luz", "✨"),
    ("essencia_sombra", "🌑"), ("essencia_precisao", "🎯"), ("essencia_fera", "🐾"),
    ("essencia_ki", "🌀"), ("essencia_arcana", "🔮"), ("essencia_elemental", "🌩️"),
    ("essencia_harmonia", "🎵"), ("essencia_encanto", "🧿"), ("essencia_letal", "☠️"),
    ("essencia_corte", "🗡️"), ("essencia_disciplina", "📏"),
    ("essencia_fe", "🙏"), ("essencia_fe_pura", "🌟")
]
for eid, emo in _ESSENCES:
    EVOLUTION_ITEMS_DATA[eid] = {
        "display_name": eid.replace("_", " ").title(), "emoji": emo,
        "type": "material_magico", "category": "evolucao", "description": "Essência de poder.",
        "stackable": True, "evolution_item": True, "market_currency": "gems"
    }

# 3. Relíquias
_RELICS = [
    "selo_sagrado", "totem_ancestral", "marca_predador", "reliquia_mistica",
    "grimorio_arcano", "batuta_maestria", "manto_eterno", "lamina_sagrada",
    "pergaminho_sagrado", "calice_da_luz", "alma_da_fe"
]
for rid in _RELICS:
    EVOLUTION_ITEMS_DATA[rid] = {
        "display_name": rid.replace("_", " ").title(), "emoji": "🔱",
        "type": "especial", "category": "evolucao", "description": "Relíquia antiga.",
        "stackable": False
    }