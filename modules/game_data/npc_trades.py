# Em modules/game_data/npc_trades.py (VERSÃO COM CUSTO DE OURO)

NPC_TRADES = {
    'alquimista_floresta': {
        'display_name': 'Alquimista da Floresta',
        'intro_message': "'Olá, aventureiro. Vê o que podes obter em troca dos teus materiais.'",
        'trades': {
            'pocao_cura_leve': {
                'items': { 'fragmento_bravura': 10, 'presa_de_javali': 5, 'esporo_de_cogumelo': 2 },
                'gold': 50
            },
            'pocao_energia_fraca': {
                'items': { 'fragmento_bravura': 100, 'asa_de_morcego': 4, 'poeira_magica': 1 },
                'gold': 1000
            },
            'frasco_sabedoria': {
                'items': { 'fragmento_bravura': 30, 'ectoplasma': 3, 'pena': 10 },
                'gold': 200
            },
            'pocao_cura_media': {
                'items': { 'fragmento_bravura': 50, 'sangue_regenerativo': 2, 'seiva_de_ent': 1 },
                'gold': 250
            },
        }
    }
}