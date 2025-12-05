# modules/game_data/attributes.py

# ============================================================================
# 1. EMOJIS DOS ATRIBUTOS (STAT_EMOJI)
# ============================================================================
# O sistema procura por "STAT_EMOJI", então renomeamos para corresponder.
STAT_EMOJI = {
    "vida": "❤️‍🩹",
    "hp": "❤️‍🩹",
    "defesa": "🛡️",
    "defense": "🛡️",
    "sorte": "🍀",
    "luck": "🍀",
    "agilidade": "🏃",
    "initiative": "🏃",

    "forca": "💪",
    "inteligencia": "🧠",
    "furia": "🔥",
    "precisao": "🎯",
    "letalidade": "☠️",
    "carisma": "😎",
    "foco": "🧘",
    "bushido": "🥷",

    "dmg": "⚔️",
    "attack": "⚔️", # Adicionado alias comum
    "energy": "⚡",  # Adicionado alias comum
    "xp": "✨",      # Adicionado alias comum
    "gold": "💰"     # Adicionado alias comum
}

# Alias para compatibilidade se algum módulo antigo usar ATTRIBUTE_ICONS
ATTRIBUTE_ICONS = STAT_EMOJI

# ============================================================================
# 2. POOLS DE AFIXOS PARA GERAÇÃO ALEATÓRIA
# ============================================================================
AFFIX_POOLS = {
    # A pool "geral" contém atributos úteis para qualquer classe.
    "geral": ["sorte", "defesa", "agilidade", "vida"],
    
    # Pools de classe
    "guerreiro": ["forca"],
    "mago": ["inteligencia"],
    "berserker": ["furia"],
    "cacador": ["precisao"],
    "assassino": ["letalidade"],
    "bardo": ["carisma"],
    "monge": ["foco"],
    "samurai": ["bushido"]
}

# ============================================================================
# 3. VALORES DOS AFIXOS (RANGES)
# ============================================================================
AFFIXES = {
    "vida":         {"values": {"comum":[1,2], "bom":[2,3], "raro":[3,5], "epico":[5,7],  "lendario":[7,10]}},
    "defesa":       {"values": {"comum":[1,2], "bom":[2,4], "raro":[4,6], "epico":[6,9],  "lendario":[9,12]}},
    "sorte":        {"values": {"comum":[1,1], "bom":[1,2], "raro":[2,3], "epico":[3,4],  "lendario":[4,6]}},
    "agilidade":    {"values": {"comum":[1,1], "bom":[1,2], "raro":[2,3], "epico":[3,4],  "lendario":[4,6]}},
    
    "forca":        {"values": {"comum":[1,2], "bom":[2,3], "raro":[3,5], "epico":[5,7],  "lendario":[7,10]}},
    "inteligencia": {"values": {"comum":[1,2], "bom":[2,3], "raro":[3,5], "epico":[5,7],  "lendario":[7,10]}},
    "furia":        {"values": {"comum":[1,2], "bom":[2,3], "raro":[3,5], "epico":[5,7],  "lendario":[7,10]}},
    "precisao":     {"values": {"comum":[1,2], "bom":[2,3], "raro":[3,5], "epico":[5,7],  "lendario":[7,10]}},
    "letalidade":   {"values": {"comum":[1,2], "bom":[2,3], "raro":[3,5], "epico":[5,7],  "lendario":[7,10]}},
    "carisma":      {"values": {"comum":[1,2], "bom":[2,3], "raro":[3,5], "epico":[5,7],  "lendario":[7,10]}},
    "foco":         {"values": {"comum":[1,2], "bom":[2,3], "raro":[3,5], "epico":[5,7],  "lendario":[7,10]}},
    "bushido":      {"values": {"comum":[1,2], "bom":[2,3], "raro":[3,5], "epico":[5,7],  "lendario":[7,10]}},
}