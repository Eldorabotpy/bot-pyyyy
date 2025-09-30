# modules/game_data/professions.py

# Em modules/game_data/professions.py
# SUBSTITUA o seu PROFESSIONS_DATA por este:

PROFESSIONS_DATA = {
    # Coleta
    'lenhador':   {
        'display_name': 'Lenhador',
        'category': 'gathering',
        'resources': {
            'floresta_sombria': 'madeira' # Região 'floresta_sombria' dá o item 'madeira'
        }
    },
    'minerador':  {
        'display_name': 'Minerador',
        'category': 'gathering',
        'resources': {
            'pedreira_granito': 'pedra', # Região 'pedreira_granito' dá o item 'pedra'
            'mina_ferro': 'ferro'       # Região 'mina_ferro' dá o item 'ferro'
        }
    },
    'colhedor':   {
        'display_name': 'Colhedor',
        'category': 'gathering',
        'resources': {
            'campos_linho': 'linho'     # Região 'campos_linho' dá o item 'linho'
        }
    },
    'esfolador':  { 
        'display_name': 'Esfolador',
        'category': 'gathering',
        'resources': {
            'pico_grifo': 'pena'        # Região 'pico_grifo' dá o item 'pena'
        }
    },
    'alquimista': {
        'display_name': 'Alquimista',
        'category': 'gathering',
        'resources': {
            'pantano_maldito': 'sangue' # Região 'pantano_maldito' dá o item 'sangue'
        }
    },

    # Produção (sem alterações)
    'ferreiro':   {'display_name': 'Ferreiro',   'category': 'crafting'},
    'armeiro':    {'display_name': 'Armeiro',    'category': 'crafting'},
    'alfaiate':   {'display_name': 'Alfaiate',   'category': 'crafting'},
    'joalheiro':  {'display_name': 'Joalheiro',  'category': 'crafting'},
    'curtidor':   {'display_name': 'Curtidor',   'category': 'crafting'},
    'fundidor':   {'display_name': 'Fundidor',   'category': 'crafting'},
}
def get_profession_for_resource(resource_id: str) -> str | None:
    """Profissão de COLETA necessária para obter 'resource_id'."""
    for prof_key, prof_info in PROFESSIONS_DATA.items():
        # Agora procuramos se o resource_id é uma chave no dicionário de resources
        if prof_info.get('category') == 'gathering' and resource_id in prof_info.get('resources', {}):
            return prof_key
    return None
