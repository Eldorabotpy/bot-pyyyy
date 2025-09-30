# modules/game_data/attributes.py

ATTRIBUTE_ICONS = {
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

    "dmg": "⚔️",  # se algum lugar exibir diretamente a chave dmg
}

# O dicionário AFFIXES conterá os valores e o escalonamento, 
# mas primeiro listamos todos para referência.
ALL_ATTRIBUTES = {
    "vida": {"display_name": "Vida"},
    "defesa": {"display_name": "Defesa"},
    "sorte": {"display_name": "Sorte"},
    "agilidade": {"display_name": "Agilidade"},
    "forca": {"display_name": "Força"},
    "inteligencia": {"display_name": "Inteligência"},
    "furia": {"display_name": "Fúria"},
    "precisao": {"display_name": "Precisão"},
    "letalidade": {"display_name": "Letalidade"},
    "carisma": {"display_name": "Carisma"},
    "foco": {"display_name": "Foco"},
    "bushido": {"display_name": "Bushido"}
}

# ============================================================================
# PARTE 2: POOLS DE AFIXOS PARA GERAÇÃO ALEATÓRIA
# ============================================================================
# Define quais atributos podem ser sorteados como bônus secundários para cada classe.

AFFIX_POOLS = {
    # A pool "geral" contém atributos úteis para qualquer classe.
    "geral": ["sorte", "defesa", "agilidade", "vida"],
    
    # As pools de classe contêm seu atributo principal, garantindo que ele
    # possa aparecer como um bônus secundário em itens que não o têm como primário.
    "guerreiro": ["forca"],
    "mago": ["inteligencia"],
    "berserker": ["furia"],
    "cacador": ["precisao"],
    "assassino": ["letalidade"],
    "bardo": ["carisma"],
    "monge": ["foco"],
    "samurai": ["bushido"]
}


# Afixos secundários com seus ranges por raridade
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
