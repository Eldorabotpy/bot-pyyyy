# modules/game_data/world.py

WORLD_MAP = {
    'reino_eldora': ['floresta_sombria', 'campos_linho'],
    'floresta_sombria': ['reino_eldora', 'pedreira_granito'],
    'pedreira_granito': ['floresta_sombria', 'mina_ferro'],
    'campos_linho': ['reino_eldora', 'pico_grifo'],
    'pico_grifo': ['campos_linho', 'pantano_maldito'],
    'mina_ferro': ['pedreira_granito', 'forja_abandonada'],
    'forja_abandonada': ['mina_ferro'],
    'pantano_maldito': ['pico_grifo'],
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
    'pico_grifo': {'display_name': 'Pico do Grifo', 'resource': 'pena', 'emoji': '🦅', 'file_id_name': 'regiao_pico_grifo', 'ambush_chance': 0.25},
    'mina_ferro':       {'display_name': 'Mina de Ferro',        'resource': 'ferro', 'emoji': '⛏️', 'file_id_name': 'regiao_mina_ferro'},
    'forja_abandonada': {'display_name': 'Forja Abandonada',     'resource': None,    'emoji': '🔥', 'file_id_name': 'regiao_forja_abandonada'},
    'pantano_maldito':  {'display_name': 'Pântano Maldito',      'resource': 'sangue','emoji': '🩸', 'file_id_name': 'regiao_pantano_maldito', 'ambush_chance': 0.30},
}
