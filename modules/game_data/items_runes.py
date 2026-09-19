# modules/game_data/items_runes.py

# Dicionário exclusivo para Runas e Fragmentos
RUNE_ITEMS_DATA = {
    
    # --- MATERIAIS DE CRAFTING DE RUNAS ---
    "fragmento_runa_ancestral": {
        "display_name": "Fragmento de Runa",
        "emoji": "🧩",
        "type": "material_runico",
        "category": "runas",
        "description": "Junte 7 destes para forjar uma Runa Aleatória.",
        "stackable": True,
        "media_key": "item_fragmento_runa",
        "rarity": "raro"
    },
    "po_runico": {
        "display_name": "Pó Rúnico",
        "emoji": "✨",
        "type": "material_runico",
        "category": "runas",
        "description": "Resíduo mágico obtido ao quebrar runas.",
        "stackable": True,
        "media_key": "item_po_runico"
    },

    # --- RUNAS TIER 1 (MENORES) ---
    "runa_crueldade_menor": {
        "display_name": "Runa da Crueldade Menor", "emoji": "☠️",
        "type": "runa", "category": "socketable",
        "description": "Aumenta levemente o Dano Crítico.",
        "stackable": True, "tier": 1, 
        "media_key": "item_runa_vermelha"
    },
    "runa_precisao_menor": {
        "display_name": "Runa da Precisão Menor", "emoji": "🎯",
        "type": "runa", "category": "socketable",
        "description": "Aumenta levemente a Chance Crítica.",
        "stackable": True, "tier": 1,
        "media_key": "item_runa_vermelha"
    },
    "runa_vampiro_menor": {
        "display_name": "Runa do Vampiro Menor", "emoji": "🩸",
        "type": "runa", "category": "socketable",
        "description": "Concede um pouco de Roubo de Vida.",
        "stackable": True, "tier": 1,
        "media_key": "item_runa_verde"
    },
    "runa_rocha_menor": {
        "display_name": "Runa da Rocha Menor", "emoji": "🛡️",
        "type": "runa", "category": "socketable",
        "description": "Aumenta a Defesa Física.",
        "stackable": True, "tier": 1,
        "media_key": "item_runa_verde"
    },
    "runa_mente_menor": {
        "display_name": "Runa da Mente Menor", "emoji": "🧠",
        "type": "runa", "category": "socketable",
        "description": "Aumenta a Mana Máxima.",
        "stackable": True, "tier": 1,
        "media_key": "item_runa_azul"
    },
    "runa_eco_menor": {
        "display_name": "Runa do Eco Menor", "emoji": "🔊",
        "type": "runa", "category": "socketable",
        "description": "Aumenta o Poder Mágico.",
        "stackable": True, "tier": 1,
        "media_key": "item_runa_azul"
    },
    "runa_midas_menor": {
        "display_name": "Runa de Midas Menor", "emoji": "💰",
        "type": "runa", "category": "socketable",
        "description": "Aumenta o ganho de Ouro.",
        "stackable": True, "tier": 1,
        "media_key": "item_runa_dourada"
    },
    "runa_sabio_menor": {
        "display_name": "Runa do Sábio Menor", "emoji": "📜",
        "type": "runa", "category": "socketable",
        "description": "Aumenta o ganho de XP.",
        "stackable": True, "tier": 1,
        "media_key": "item_runa_dourada"
    },

    # --- RUNAS TIER 2 (MAIORES) ---
    "runa_crueldade_maior": {
        "display_name": "Runa da Crueldade Maior", "emoji": "☠️",
        "type": "runa", "category": "socketable",
        "description": "Aumenta consideravelmente o Dano Crítico.",
        "stackable": True, "tier": 2,
        "media_key": "item_runa_vermelha_brilhante"
    },
    "runa_vampiro_maior": {
        "display_name": "Runa do Vampiro Maior", "emoji": "🩸",
        "type": "runa", "category": "socketable",
        "description": "Concede bom Roubo de Vida.",
        "stackable": True, "tier": 2,
        "media_key": "item_runa_verde_brilhante"
    },

    # --- RUNAS TIER 3 (ANCESTRAIS) ---
    "runa_crueldade_ancestral": {
        "display_name": "Runa da Crueldade Ancestral", "emoji": "🏴‍☠️",
        "type": "runa", "category": "socketable",
        "description": "Poder imenso de Dano Crítico.",
        "stackable": True, "tier": 3,
        "rarity": "lendario",
        "media_key": "item_runa_ancestral"
    },
    "runa_precisao_ancestral": {
        "display_name": "Runa da Precisão Ancestral", "emoji": "🎯",
        "type": "runa", "category": "socketable",
        "description": "Precisão cirúrgica lendária.",
        "stackable": True, "tier": 3,
        "rarity": "lendario",
        "media_key": "item_runa_ancestral"
    },
    "runa_vampiro_ancestral": {
        "display_name": "Runa do Vampiro Ancestral", "emoji": "🧛",
        "type": "runa", "category": "socketable",
        "description": "Vampirismo lendário.",
        "stackable": True, "tier": 3,
        "rarity": "lendario",
        "media_key": "item_runa_ancestral"
    },
    "runa_eco_ancestral": {
        "display_name": "Runa do Eco Ancestral", "emoji": "🔮",
        "type": "runa", "category": "socketable",
        "description": "Poder Mágico avassalador.",
        "stackable": True, "tier": 3,
        "rarity": "lendario",
        "media_key": "item_runa_ancestral"
    },
}
# Mesmo catálogo para identificação, inventário e evolução.
from modules.game_data.runes_data import RUNES_DB
for _rid, _rune in RUNES_DB.items():
    RUNE_ITEMS_DATA.setdefault(_rid, {"display_name": _rune["name"], "type": "runa", "category": "socketable", "stackable": True, "rarity": {1:"raro",2:"epico",3:"lendario"}[_rune["tier"]]})
    RUNE_ITEMS_DATA[_rid]["description"] = _rune["desc"]
