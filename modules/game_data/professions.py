# modules/game_data/professions.py
# (VERSÃO CORRIGIDA)

from __future__ import annotations
from typing import Dict, Any

# ===================================================================
# <<< INÍCIO DA CORREÇÃO >>>
# ===================================================================
# As chaves dentro de 'resources' devem ser o ID do RECURSO (item),
# não o ID da REGIÃO.

PROFESSIONS_DATA = {
    # Coleta
    'lenhador':  {
        'display_name': 'Lenhador',
        'category': 'gathering',
        'resources': {
            # O recurso 'madeira' (o nó) dá o item 'madeira'
            'madeira': 'madeira' 
        }
    },
    'minerador': {
        'display_name': 'Minerador',
        'category': 'gathering',
        'resources': {
            'pedra': 'pedra', # O recurso 'pedra' dá o item 'pedra'
            'ferro': 'ferro'  # O recurso 'ferro' dá o item 'ferro'
        }
    },
    'colhedor': {
        'display_name': 'Colhedor',
        'category': 'gathering',
        'resources': {
            'linho': 'linho' # O recurso 'linho' dá o item 'linho'
        }
    },
    'esfolador': { 
        'display_name': 'Esfolador',
        'category': 'gathering',
        'resources': {
            'pena': 'pena' # O recurso 'pena' dá o item 'pena'
        }
    },
    'alquimista': {
        'display_name': 'Alquimista',
        'category': 'gathering',
        'resources': {
            'sangue': 'sangue' # O recurso 'sangue' dá o item 'sangue'
        }
    },

    # Produção (sem alterações)
    'ferreiro':  {'display_name': 'Ferreiro',  'category': 'crafting'},
    'armeiro':   {'display_name': 'Armeiro',   'category': 'crafting'},
    'alfaiate':  {'display_name': 'Alfaiate',  'category': 'crafting'},
    'joalheiro': {'display_name': 'Joalheiro', 'category': 'crafting'},
    'curtidor':  {'display_name': 'Curtidor',  'category': 'crafting'},
    'fundidor':  {'display_name': 'Fundidor',  'category': 'crafting'},
}
# ===================================================================
# <<< FIM DA CORREÇÃO >>>
# ===================================================================

def get_profession_for_resource(resource_id: str) -> str | None:
    """
    Profissão de COLETA necessária para obter 'resource_id'.
    (Esta função agora funciona, pois 'resource_id' será encontrado nas chaves)
    """
    for prof_key, prof_info in PROFESSIONS_DATA.items():
        # Agora procuramos se o resource_id é uma chave no dicionário de resources
        if prof_info.get('category') == 'gathering' and resource_id in prof_info.get('resources', {}):
            return prof_key
    return None