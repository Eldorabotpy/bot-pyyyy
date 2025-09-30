# modules/dungeon_definitions.py (VERSÃO CORRIGIDA)

DUNGEONS = {
    'catacumba_reino': {
        'display_name': 'Catacumba do Reino',
        'description': 'Corredores úmidos onde os primeiros reis descansam... e não sozinhos.',
        'entry_location': 'reino_eldora',
        'required_key': 'chave_da_catacumba',
        'max_players': 4,
        # A ESTRUTURA ABAIXO FOI CORRIGIDA DE LISTA PARA DICIONÁRIO
        'floors': {
            '1': {
                "monsters": [
                    {"base_id": "morcego_gigante", "quantity": 1}
                ],
                "boss": None
            },
            '2': {
                "monsters": [
                    {"base_id": "dragao_negro", "quantity": 1}
                    
                ],
                "boss": None
            },
            '3': {
                "monsters": [
                    {"base_id": "trol_escavador", "quantity": 1}
                ],
                "boss": None
            },
            '4': {
                "monsters": [
                    {"base_id": "golen_de_larva", "quantity": 1}
                
                ],
                "boss": None
            },
            '5': {
                "monsters": [
                    {"base_id": "golen_de_palha", "quantity": 1}
                    
                ],
                "boss": None
            },
            '6': {
                "monsters": [], # Andar do chefe
                "boss": {"base_id": "rei_lagarto"}
            }
        }
    },
    'mina_abandonada': {
        'display_name': 'Mina Abandonada',
        'description': 'Túneis escuros e perigosos, abandonados por um motivo.',
        'entry_location': 'pedreira_granito',
        'required_key': 'mapa_da_mina',
        'max_players': 4,
        'floors': {} # Adicionar andares aqui no futuro no formato de dicionário
    }
}
DUNGEONS.update({
    "floresta_sombria_raizes_negras": {
        "name": "Raízes Negras",
        "region_label": "Floresta Sombria",
        "difficulties": {
            "normal": {
                "label": "Normal",
                "gold_reward": 60,
                "energy_cost": 0,  # ignorado porque o handler não consome energia
                "other_drops": [
                    {"item_id": "seiva_escura", "chance": 0.45, "min": 1, "max": 2},
                ],
                "set_piece_drop_chance": 0.10,
                "rarity_weights": {"comum": 70, "bom": 25, "raro": 5}
            },
            "calamidade": {
                "label": "Calamidade",
                "gold_reward": 120, "energy_cost": 0,
                "other_drops": [
                    {"item_id": "seiva_escura", "chance": 0.60, "min": 1, "max": 3},
                ],
                "set_piece_drop_chance": 0.14,
                "rarity_weights": {"comum": 55, "bom": 30, "raro": 12, "epico": 3}
            },
            "inferno": {
                "label": "Inferno",
                "gold_reward": 220, "energy_cost": 0,
                "other_drops": [
                    {"item_id": "seiva_escura", "chance": 0.70, "min": 2, "max": 4},
                ],
                "set_piece_drop_chance": 0.18,
                "rarity_weights": {"comum": 40, "bom": 30, "raro": 20, "epico": 9, "lendario": 1}
            },
        },
        "set_piece": {  # opcional, já suportado no seu handler
            "default": "peitoral_coracao_umbrio",
            "mage": "manto_coracao_umbrio",
            "mage_classes": ["mago", "bardo"],
            "hp_by_rarity": {"comum": 8, "bom": 16, "raro": 28, "epico": 45, "lendario": 70}
        }
    }
})
