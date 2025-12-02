# modules/game_data/world.py

WORLD_MAP = {
    # Ponto de Partida
    "reino_eldora": [
        "pradaria_inicial"
    ],
    
    # Caminho Principal
    "pradaria_inicial": [
        "reino_eldora", 
        "floresta_sombria"
    ],
    "floresta_sombria": [
        "pradaria_inicial",
        "campos_linho"
    ],
    "campos_linho": [
        "floresta_sombria",
        "pedreira_granito"
    ],
    "pedreira_granito": [
        "campos_linho",
        "pico_grifo"
    ],
    "pico_grifo": [
        "pedreira_granito",
        "mina_ferro"
    ],
    "mina_ferro": [
        "pico_grifo",
        "forja_abandonada"
    ],
    "forja_abandonada": [
        "mina_ferro",
        "pantano_maldito"
    ],
    "pantano_maldito": [
        "forja_abandonada",
        "picos_gelados"
    ],
    "picos_gelados": [
        "pantano_maldito",
        "deserto_ancestral"
    ],
    "deserto_ancestral": [
        "picos_gelados" 
    ],
}
# Pontos de poder “alvo” por região (para calibrar a dificuldade)
REGION_TARGET_POWER = {
    "floresta_sombria": 80,     # Tier 1
    "pedreira_granito": 130,    # Tier 2
    "campos_linho": 180,        # Tier 3  ← Campos de Linho
    "pico_grifo": 240,          # Tier 4 (ex.)
    "mina_ferro": 260,
    "forja_abandonada": 300,
    "pantano_maldito": 330,
    
}

# Regiões com “scaling” dinâmico ativado
REGION_SCALING_ENABLED = {
    "floresta_sombria": True,
    "pedreira_granito": True,
    "campos_linho": True,
    "pico_grifo": True,
    "mina_ferro": True,
    "forja_abandonada":True,
    "pantano_maldito":True,
    }


# --- REGIÕES ---

REGIONS_DATA = {
    'reino_eldora':     {'display_name': 'Reino de Eldora',      'resource': None,    'emoji': '🏰', 'file_id_name': 'regiao_reino_eldora'},
    'floresta_sombria': {'display_name': 'Floresta Sombria',     'resource': 'madeira','emoji': '🌳', 'file_id_name': 'regiao_floresta_sombria', 'ambush_chance': 0.20},
    'pedreira_granito': {'display_name': 'Pedreira de Granito',  'resource': 'pedra', 'emoji': '🪨', 'file_id_name': 'regiao_pedreira_granito'},
    'campos_linho':     {'display_name': 'Campos de Linho',      'resource': 'linho', 'emoji': '🌾', 'file_id_name': 'regiao_campos_linho'},
    'pico_grifo':       {'display_name': 'Pico do Grifo',        'resource': 'pena',  'emoji': '🦅', 'file_id_name': 'regiao_pico_grifo', 'ambush_chance': 0.25},
    'mina_ferro':       {'display_name': 'Mina de Ferro',        'resource': 'ferro', 'emoji': '⛏️', 'file_id_name': 'regiao_mina_ferro'},
    'forja_abandonada': {'display_name': 'Forja Abandonada',     'resource': None,    'emoji': '🔥', 'file_id_name': 'regiao_forja_abandonada'},
    'pantano_maldito':  {'display_name': 'Pântano Maldito',      'resource': 'sangue','emoji': '🩸', 'file_id_name': 'regiao_pantano_maldito', 'ambush_chance': 0.30},
    
    # --- NOVAS REGIÕES ADICIONADAS ---
    'pradaria_inicial': {'display_name': 'Pradaria Inicial',     'resource': 'trigo', 'emoji': '🌱', 'file_id_name': 'regiao_pradaria_inicial'},
    'picos_gelados':    {'display_name': 'Picos Gelados',        'resource': 'gelo',  'emoji': '❄️', 'file_id_name': 'regiao_picos_gelados', 'travel_cost': 2},
    
    # AQUI FICA O SEU NPC DE RUNAS:
    'deserto_ancestral':{
        'display_name': 'Deserto Ancestral', 
        'resource': 'poeira_magica',  # Combina com a temática mística
        'emoji': '🏜️', 
        'file_id_name': 'regiao_deserto_ancestral',
        'description': 'Dunas infinitas onde o tempo parece não passar. O lar do Místico Rúnico.',
        'travel_cost': 5 # Custa mais energia chegar aqui
    },
}
