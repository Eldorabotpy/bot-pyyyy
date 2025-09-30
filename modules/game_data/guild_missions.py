# Ficheiro: modules/game_data/guild_missions.py

"""
Este ficheiro serve como um catálogo central para todas as possíveis
missões que uma guilda pode receber. A estrutura é um dicionário para
facilitar a busca de uma missão pelo seu ID.

Estrutura da Recompensa:
  - guild_xp: Pontos de prestígio que são adicionados ao clã.
  - gold_per_member: Ouro que cada membro do clã recebe individualmente.
  - item_per_member: Um item que cada membro recebe.
"""

GUILD_MISSIONS_CATALOG = {
    # --- Missões Semanais de Caça (Escala Grande) ---
    
    "weekly_hunt_goblins_batedores": {
        "title": "Guerra aos Goblins",
        "description": "Uma infestação de Goblins Batedores ameaça a Floresta Sombria. A sua guilda foi contratada para erradicar a ameaça.",
        "type": "HUNT",
        "target_monster_id": "goblin_batedor",
        "target_count": 500,
        "duration_hours": 168,  # 7 dias
        "rewards": {
            "guild_xp": 1000,
            "gold_per_member": 5000,
            "item_per_member": { "item_id": "bau_da_guilda_1", "quantity": 1 }
        }
    },
    
    "weekly_hunt_kobolds_escavadores": {
        "title": "Limpeza na Pedreira",
        "description": "Os Kobolds Escavadores estão a sabotar as operações na Pedreira de Granito. Acabem com eles.",
        "type": "HUNT",
        "target_monster_id": "kobold_escavador",
        "target_count": 400,
        "duration_hours": 168,
        "rewards": {
            "guild_xp": 1200,
            "gold_per_member": 6000
        }
    },

    "weekly_hunt_lobos_alfa": {
        "title": "A Alcateia Sombria",
        "description": "Uma alcateia de Lobos Alfa anormalmente agressiva está a aterrorizar os viajantes. Cace os líderes da alcateia.",
        "type": "HUNT",
        "target_monster_id": "lobo_alfa",
        "target_count": 100,
        "duration_hours": 168,
        "rewards": {
            "guild_xp": 1500,
            "gold_per_member": 8000,
            "item_per_member": { "item_id": "bau_da_guilda_2", "quantity": 1 }
        }
    },

    # --- Missões de Elite (Mais difíceis, mas mais rápidas) ---
    "daily_hunt_elite_basiliscos": {
        "title": "Desafio do Dia: Basiliscos",
        "description": "Um Basilisco Jovem foi avistado na Pedreira. Derrotem-no como um esforço de equipa antes que cresça.",
        "type": "HUNT",
        "target_monster_id": "basilisco_jovem", # Assumindo que este é um monstro de elite
        "target_count": 10,
        "duration_hours": 24, # 1 dia
        "rewards": {
            "guild_xp": 500,
            "gold_per_member": 2500,
        }
    }
}