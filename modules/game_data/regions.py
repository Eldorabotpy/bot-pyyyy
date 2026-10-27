# modules/game_data/regions.py
# modules/game_data/regions.py

from __future__ import annotations
from typing import Dict, Any

# Presets globais (podem ser usados por várias regiões)
DIFFICULTY_PRESETS: Dict[str, dict] = {
    "facil":     {"hp": 0.90, "attack": 0.90, "defense": 0.90, "initiative": 1.00, "luck": 1.00, "xp": 0.9, "gold": 0.9, "drop": 0.95, "flee_bias": +0.05},
    "normal":    {"hp": 1.00, "attack": 1.00, "defense": 1.00, "initiative": 1.00, "luck": 1.00, "xp": 1.0, "gold": 1.0, "drop": 1.00, "flee_bias": 0.00},
    "dificil":   {"hp": 1.25, "attack": 1.25, "defense": 1.15, "initiative": 1.05, "luck": 1.05, "xp": 1.2, "gold": 1.2, "drop": 1.10, "flee_bias": -0.05},
    "pesadelo":  {"hp": 1.55, "attack": 1.45, "defense": 1.30, "initiative": 1.10, "luck": 1.10, "xp": 1.4, "gold": 1.35, "drop": 1.15, "flee_bias": -0.08},
    "lenda":     {"hp": 1.95, "attack": 1.70, "defense": 1.45, "initiative": 1.15, "luck": 1.15, "xp": 1.7, "gold": 1.6,  "drop": 1.20, "flee_bias": -0.12},
}

# Definição de regiões
REGIONS: Dict[str, dict] = {
    # id_da_regiao: {nivel_base (faixa), dificuldade, preset opcional, mods extras por região}
    "pradaria_inicial": {
        "display": "Pradaria Inicial",
        "level_range": (1, 10),        # pensado pra jogadores 1–10
        "difficulty": "normal",        # usa DIFFICULTY_PRESETS["normal"]
        "mods": {"xp": 0.95, "gold": 0.95},  # “sabor” da região
        "encounter_tier": 1,           # usado no scaling (opcional)
    },
    "floresta_sombria": {
        "display": "Floresta Sombria",
        "level_range": (6, 20),
        "difficulty": "dificil",
        "mods": {"drop": 1.08},
        "encounter_tier": 2,
    },
    "picos_gelados": {
        "display": "Picos Gelados",
        "level_range": (15, 35),
        "difficulty": "pesadelo",
        "mods": {"initiative": 1.05},
        "encounter_tier": 3,
    },
    "deserto_ancestral": {
        "display": "Deserto Ancestral",
        "level_range": (30, 60),
        "difficulty": "lenda",
        "mods": {},
        "encounter_tier": 4,
    },
}

def get_region_profile(region_id: str) -> dict:
    r = REGIONS.get(region_id, {})
    preset = DIFFICULTY_PRESETS.get(r.get("difficulty", "normal"), DIFFICULTY_PRESETS["normal"])
    mods = dict(preset)
    # aplica pequenos ajustes específicos da região
    for k, v in (r.get("mods") or {}).items():
        # multiplicadores “stackáveis” (numéricos)
        if isinstance(v, (int, float)) and isinstance(mods.get(k), (int, float)):
            mods[k] = float(mods[k]) * float(v)
        else:
            mods[k] = v
    # metadata útil
    mods["_display"] = r.get("display", region_id)
    mods["_range"] = r.get("level_range", (1, 999))
    mods["_tier"] = int(r.get("encounter_tier", 1))
    mods["_difficulty"] = r.get("difficulty", "normal")
    return mods

# modules/game_data/regions.py (VERSÃO UNIFICADA E CORRIGIDA)

# Em gather_table, weight é peso relativo entre os materiais liberados pelo
# nível da profissão e tier da ferramenta; a coleta sorteia um resultado.
REGIONS_DATA = {
    'reino_eldora': {
        'display_name': '𝐑𝐞𝐢𝐧𝐨 𝐝𝐞 𝐄𝐥𝐝𝐨𝐫𝐚',
        'emoji': '🏰',
        'description': "O coração pulsante do mundo, um refúgio seguro para todos os aventureiros. Aqui podes descansar, comerciar e preparar-te para a tua próxima jornada.",
        'resource': None,
        'file_id_name': 'regiao_reino_eldora',
    },
    "pradaria_inicial": {
        "display_name": "𝐏𝐫𝐚𝐝𝐚𝐫𝐢𝐚 𝐈𝐧𝐢𝐜𝐢𝐚𝐥",
        "emoji": '🌱', 
        'description': "Campos verdes e tranquilos que rodeiam o Reino. É o local perfeito para novos aventureiros darem os seus primeiros passos e enfrentarem criaturas mais fracas.",
        'resource': None,
        "level_range": (1, 10),
    },

    'floresta_sombria': {
    'display_name': '𝐅𝐥𝐨𝐫𝐞𝐬𝐭𝐚 𝐒𝐨𝐦𝐛𝐫𝐢𝐚',
    'emoji': '🌳',
    'description': "Uma floresta densa e antiga, envolta em mistério. As suas árvores retorcidas são uma fonte valiosa de madeira, mas cuidado com as criaturas que se escondem nas sombras.",
    'resource': 'madeira',
    'file_id_name': 'regiao_floresta_sombria',
    'ambush_chance': 0.20,
    'level_range': (6, 20),

    'gather_table': {
        'lenhador': [
            {'item': 'madeira',             'min_level': 1,  'min_tool_tier': 1, 'weight': 70, 'min_qty': 1, 'max_qty': 3},
            {'item': 'madeira_de_carvalho', 'min_level': 5,  'min_tool_tier': 2, 'weight': 20, 'min_qty': 1, 'max_qty': 2},
            {'item': 'casca_rigida',        'min_level': 5,  'min_tool_tier': 2, 'weight': 10, 'min_qty': 1, 'max_qty': 1},
            {'item': 'seiva_de_ent',        'min_level': 5,  'min_tool_tier': 2, 'weight': 6,  'min_qty': 1, 'max_qty': 2},
            {'item': 'madeira_rara',        'min_level': 9,  'min_tool_tier': 3, 'weight': 8,  'min_qty': 1, 'max_qty': 1},
            {'item': 'ambar_seiva',         'min_level': 10, 'min_tool_tier': 3, 'weight': 4,  'min_qty': 1, 'max_qty': 1},
            {'item': 'madeira_mogno',       'min_level': 15, 'min_tool_tier': 3, 'weight': 2,  'min_qty': 1, 'max_qty': 2},
            {'item': 'madeira_elfica',      'min_level': 20, 'min_tool_tier': 4, 'weight': 3,  'min_qty': 1, 'max_qty': 1},
            {'item': 'semente_encantada',   'min_level': 20, 'min_tool_tier': 4, 'weight': 2,  'min_qty': 1, 'max_qty': 1},
            {'item': 'tronco_antigo',       'min_level': 20, 'min_tool_tier': 5, 'weight': 1,  'min_qty': 1, 'max_qty': 1},
            {'item': 'raiz_do_mundo',       'min_level': 50, 'min_tool_tier': 5, 'weight': 0.5, 'min_qty': 1, 'max_qty': 1},

        ]
    },
},

    'pedreira_granito': {
    'display_name': '𝐏𝐞𝐝𝐫𝐞𝐢𝐫𝐚 𝐝𝐞 𝐆𝐫𝐚𝐧𝐢𝐭𝐨',
    'emoji': '🪨',
    'description': "Uma enorme pedreira a céu aberto, rica em pedra de alta qualidade. O som de picaretas ecoa durante o dia, mas à noite, criaturas rochosas vagueiam livremente.",
    'resource': 'pedra',
    'file_id_name': 'regiao_pedreira_granito',

    'gather_table': {
        'minerador': [
            {'item': 'pedra',               'min_level': 1,  'min_tool_tier': 1, 'weight': 65, 'min_qty': 1, 'max_qty': 3},
            {'item': 'minerio_de_cobre',    'min_level': 1,  'min_tool_tier': 1, 'weight': 15, 'min_qty': 1, 'max_qty': 2},
            {'item': 'minerio_de_estanho',  'min_level': 5,  'min_tool_tier': 1, 'weight': 10, 'min_qty': 1, 'max_qty': 2},
            {'item': 'carvao',              'min_level': 10, 'min_tool_tier': 2, 'weight': 15, 'min_qty': 2, 'max_qty': 5},
            {'item': 'gema_bruta',          'min_level': 10, 'min_tool_tier': 2, 'weight': 10, 'min_qty': 1, 'max_qty': 1},
            {'item': 'pedra_vulcanica',     'min_level': 30, 'min_tool_tier': 3, 'weight': 3,  'min_qty': 1, 'max_qty': 1},
        ]
    },
},

    'campos_linho': {
    'display_name': '𝐂𝐚𝐦𝐩𝐨𝐬 𝐝𝐞 𝐋𝐢𝐧𝐡𝐨',
    'emoji': '🌾',
    'description': "Vastas planícies cobertas por linho dourado. É um local relativamente pacífico, ideal para colhedores experientes reunirem fibras para tecelagem.",
    'resource': 'linho',
    'file_id_name': 'regiao_campos_linho',

    'gather_table': {
        'colhedor': [
            {'item': 'linho',               'min_level': 1,  'min_tool_tier': 1, 'weight': 70, 'min_qty': 1, 'max_qty': 3},
            {'item': 'linho_fino',          'min_level': 10, 'min_tool_tier': 2, 'weight': 20, 'min_qty': 1, 'max_qty': 2},
            {'item': 'erva_cura',           'min_level': 10, 'min_tool_tier': 2, 'weight': 15, 'min_qty': 1, 'max_qty': 3},
            {'item': 'cogumelo_azul',       'min_level': 10, 'min_tool_tier': 2, 'weight': 10, 'min_qty': 1, 'max_qty': 2},
            {'item': 'raiz_sangrenta',      'min_level': 15, 'min_tool_tier': 2, 'weight': 5,  'min_qty': 1, 'max_qty': 1},
            {'item': 'fibra_resistente',    'min_level': 20, 'min_tool_tier': 2, 'weight': 8,  'min_qty': 1, 'max_qty': 2},
            {'item': 'flor_da_lua',         'min_level': 20, 'min_tool_tier': 3, 'weight': 12, 'min_qty': 1, 'max_qty': 2},
            {'item': 'semente_encantada',   'min_level': 25, 'min_tool_tier': 3, 'weight': 3,  'min_qty': 1, 'max_qty': 1},
            {'item': 'fibra_sedosa',        'min_level': 30, 'min_tool_tier': 3, 'weight': 2,  'min_qty': 1, 'max_qty': 1},
            {'item': 'raiz_solar',          'min_level': 35, 'min_tool_tier': 4, 'weight': 2,  'min_qty': 1, 'max_qty': 1},
            {'item': 'fruta_imortalidade',  'min_level': 50, 'min_tool_tier': 5, 'weight': 1,  'min_qty': 1, 'max_qty': 1},
        ]
    },
},

    'pico_grifo': {
    'display_name': '𝐏𝐢𝐜𝐨 𝐝𝐨 𝐆𝐫𝐢𝐟𝐨',
    'emoji': '🦅',
    'description': "Uma montanha alta e ventosa, cujo cume está acima das nuvens. É o lar de grifos majestosos e outras feras aladas, cujas penas são muito cobiçadas.",
    'resource': 'pena',
    'file_id_name': 'regiao_pico_grifo',
    'ambush_chance': 0.25,

    'gather_table': {
        'esfolador': [
            # Base absoluta
            {'item': 'pena',               'min_level': 1,  'min_tool_tier': 1, 'weight': 55, 'min_qty': 2, 'max_qty': 4},
            {'item': 'pano_simples',       'min_level': 1,  'min_tool_tier': 1, 'weight': 10, 'min_qty': 1, 'max_qty': 2},

            # Partes comuns de criaturas aéreas
            {'item': 'pena_grande',        'min_level': 10, 'min_tool_tier': 2, 'weight': 20, 'min_qty': 1, 'max_qty': 2},
            {'item': 'asa_de_morcego',     'min_level': 20, 'min_tool_tier': 3, 'weight': 15, 'min_qty': 1, 'max_qty': 2},

            # Couros e partes mais valiosas
            {'item': 'couro_de_grifo',     'min_level': 30, 'min_tool_tier': 4, 'weight': 7, 'min_qty': 1, 'max_qty': 1},
            {'item': 'garras_de_grifo',    'min_level': 40, 'min_tool_tier': 4, 'weight': 2, 'min_qty': 1, 'max_qty': 1},
            {'item': 'couro_dragao',       'min_level': 45, 'min_tool_tier': 5, 'weight': 2, 'min_qty': 1, 'max_qty': 1},

            # Raro / épico
            {'item': 'pluma_celestial',    'min_level': 50, 'min_tool_tier': 5, 'weight': 1, 'min_qty': 1, 'max_qty': 1},
        ]
    },
},

    'mina_ferro': {
    'display_name': '𝐌𝐢𝐧𝐚 𝐝𝐞 𝐅𝐞𝐫𝐫𝐨',
    'emoji': '⛏️',
    'description': "Uma rede de túneis escuros e profundos, rica em veios de minério de ferro. O perigo espreita em cada sombra, mas a recompensa para os mineiros corajosos é grande.",
    'resource': 'minerio_de_ferro',
    'file_id_name': 'regiao_mina_ferro',

    'gather_table': {
        'minerador': [
            {'item': 'minerio_de_ferro',   'min_level': 1,  'min_tool_tier': 2, 'weight': 60, 'min_qty': 1, 'max_qty': 3},
            {'item': 'minerio_de_estanho', 'min_level': 10, 'min_tool_tier': 1, 'weight': 12, 'min_qty': 1, 'max_qty': 2},
            {'item': 'gema_bruta',         'min_level': 10, 'min_tool_tier': 2, 'weight': 10, 'min_qty': 1, 'max_qty': 1},
            {'item': 'minerio_de_prata',   'min_level': 20, 'min_tool_tier': 3, 'weight': 7,  'min_qty': 1, 'max_qty': 2},
            {'item': 'minerio_de_ouro',    'min_level': 38, 'min_tool_tier': 3, 'weight': 2,  'min_qty': 1, 'max_qty': 1},
            {'item': 'cristal_bruto',      'min_level': 25, 'min_tool_tier': 3, 'weight': 20, 'min_qty': 1, 'max_qty': 2},
            {'item': 'cristal_mana',       'min_level': 40, 'min_tool_tier': 4, 'weight': 15, 'min_qty': 1, 'max_qty': 2},
            {'item': 'nucleo_de_energia_instavel', 'min_level': 45, 'min_tool_tier': 4, 'weight': 5, 'min_qty': 1, 'max_qty': 1},
            {'item': 'minerio_de_mithril', 'min_level': 45, 'min_tool_tier': 4, 'weight': 5, 'min_qty': 1, 'max_qty': 2},
            {'item': 'pedra_vulcanica',    'min_level': 50, 'min_tool_tier': 4, 'weight': 3,  'min_qty': 1, 'max_qty': 1},
            {'item': 'obsidiana_ancestral','min_level': 50, 'min_tool_tier': 5, 'weight': 20, 'min_qty': 1, 'max_qty': 1},
            {'item': 'minerio_de_adamantio','min_level': 50, 'min_tool_tier': 5, 'weight': 2, 'min_qty': 1, 'max_qty': 1},
        ]
    },
},

    'forja_abandonada': {
    'display_name': '𝐅𝐨𝐫𝐣𝐚 𝐀𝐛𝐚𝐧𝐝𝐨𝐧𝐚𝐝𝐚',
    'emoji': '🔥',
    'description': "As ruínas de uma antiga forja elemental. O calor ainda emana das suas bigornas esquecidas, e diz-se que espíritos de fogo e golens de ferro ainda guardam o local.",
    'resource': None,
    'file_id_name': 'regiao_forja_abandonada',
    'ambush_chance': 0.55,

    # Região especial: coleta avançada (sem resource base)
    'gather_table': {
        # ⛏️ Minerador / Fundição avançada
        'minerador': [
            {'item': 'pedra_vulcanica',     'min_level': 15, 'min_tool_tier': 3, 'weight': 40, 'min_qty': 1, 'max_qty': 1},
            {'item': 'escoria_metalica',    'min_level': 12, 'min_tool_tier': 2, 'weight': 25, 'min_qty': 1, 'max_qty': 2},
            {'item': 'fragmento_de_magma',  'min_level': 18, 'min_tool_tier': 4, 'weight': 20, 'min_qty': 1, 'max_qty': 1},
            {'item': 'nucleo_igneo',        'min_level': 25, 'min_tool_tier': 5, 'weight': 5,  'min_qty': 1, 'max_qty': 1},
        ],

        # 🧪 Alquimista (essências ígneas)
        'alquimista': [
            {'item': 'essencia_de_fogo',    'min_level': 12, 'min_tool_tier': 3, 'weight': 35, 'min_qty': 1, 'max_qty': 1},
            {'item': 'cinzas_elementais',   'min_level': 10, 'min_tool_tier': 2, 'weight': 30, 'min_qty': 1, 'max_qty': 2},
        ],
    },
},

    'pantano_maldito': {
    'display_name': '𝐏𝐚̂𝐧𝐭𝐚𝐧𝐨 𝐌𝐚𝐥𝐝𝐢𝐭𝐨',
    'emoji': '🩸',
    'description': "Um pântano sombrio e enevoado, onde o ar é pesado e a água tem uma cor estranha. É um local perigoso, mas rico em ingredientes alquímicos raros, como o sangue de criaturas do pântano.",
    'resource': 'sangue',
    'file_id_name': 'regiao_pantano_maldito',
    'ambush_chance': 0.30,

    'gather_table': {
        'alquimista': [
            # Base (sempre cai algo útil)
            {'item': 'sangue',              'min_level': 1,  'min_tool_tier': 1, 'weight': 55, 'min_qty': 1, 'max_qty': 3},

            # Componentes comuns de alquimia
            {'item': 'esporo_de_cogumelo',  'min_level': 10, 'min_tool_tier': 2, 'weight': 18, 'min_qty': 1, 'max_qty': 3},
            {'item': 'lodo_toxico',         'min_level': 20, 'min_tool_tier': 3, 'weight': 15, 'min_qty': 1, 'max_qty': 1},

            # Componentes de refino / avançados
            {'item': 'ectoplasma',          'min_level': 30, 'min_tool_tier': 4, 'weight': 8, 'min_qty': 1, 'max_qty': 2},
            {'item': 'sangue_regenerativo', 'min_level': 40, 'min_tool_tier': 4, 'weight': 3, 'min_qty': 1, 'max_qty': 1},

            # Raro / épico (pântano maldito tem que ter “pico”)
            {'item': 'essencia_sombra',     'min_level': 50, 'min_tool_tier': 5, 'weight': 1, 'min_qty': 1, 'max_qty': 1},
        ]
    },
},

    # Adicionei as regiões que faltavam da tua outra lista
    
    "picos_gelados": {
        "display_name": "𝐏𝐢𝐜𝐨𝐬 𝐆𝐞𝐥𝐚𝐝𝐨𝐬",
        "emoji": '🏔️', 
        'description': "Montanhas cobertas de neve eterna, onde o frio corta até aos ossos. Apenas os aventureiros mais bem preparados ousam enfrentar as feras de gelo que habitam aqui.",
        'resource': None,
        "level_range": (15, 35),
    },
    "deserto_ancestral": {
        "display_name": "𝐃𝐞𝐬𝐞𝐫𝐭𝐨 𝐀𝐧𝐜𝐞𝐬𝐭𝐫𝐚𝐥",
        "emoji": '🏜️',
        'description': "Um vasto deserto de areias douradas, pontilhado por ruínas de uma civilização há muito esquecida. Segredos e perigos ancestrais aguardam sob o sol escaldante.",
        'resource': 'poeira_magica',
        'gather_table': {
            'alquimista': [
                {'item': 'agua_pura',     'min_level': 1,  'min_tool_tier': 1, 'weight': 80, 'min_qty': 1, 'max_qty': 3},
                {'item': 'poeira_magica', 'min_level': 1,  'min_tool_tier': 1, 'weight': 20, 'min_qty': 1, 'max_qty': 1},
                {'item': 'luz_estelar',   'min_level': 50, 'min_tool_tier': 5, 'weight': 5,  'min_qty': 1, 'max_qty': 1},
            ]
        },
        "level_range": (30, 60),
    },
}

REGION_TARGET_POWER = {
    "floresta_sombria": 80,
    "pedreira_granito": 130,
    "campos_linho": 180,
    "pico_grifo": 240,
    "mina_ferro": 260,
    "forja_abandonada": 300,
    "pantano_maldito": 330,
}

REGION_SCALING_ENABLED = {
    "floresta_sombria": True,
    "pedreira_granito": True,
    "campos_linho": True,
    "pico_grifo": True,
    "mina_ferro": True,
    "forja_abandonada": True,
    "pantano_maldito": True,
}
