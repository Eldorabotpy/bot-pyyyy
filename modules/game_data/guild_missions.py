# Ficheiro: modules/game_data/guild_missions.py

# Ficheiro: modules/game_data/guild_missions.py
# VERSÃO ATUALIZADA COM LORE (HISTÓRIA)

"""
Este ficheiro serve como um catálogo central para todas as possíveis
missões que uma guilda pode receber. A estrutura é um dicionário para
facilitar a busca de uma missão pelo seu ID.

Novos Campos:
- story: A narrativa ou "lore" que dá contexto à missão.
- objective: A instrução clara do que a guilda precisa fazer.

Estrutura da Recompensa:
  - guild_xp: Pontos de prestígio que são adicionados ao clã.
  - gold_per_member: Ouro que cada membro do clã recebe individualmente.
  - item_per_member: Um item que cada membro recebe.
"""

GUILD_MISSIONS_CATALOG = {
    # --- Missões Semanais de Caça (Escala Grande) ---
    
    "weekly_hunt_goblins_batedores": {
        "title": "Guerra aos Goblins",
        "story": (
            "O Capitão da Guarda, Valerius, bate com o punho na mesa. \"Outra caravana... "
            "perdida! A Floresta Sombria está infestada de Goblins Batedores. Eles estão "
            "mais ousados, atacando à luz do dia! Precisamos de uma guilda forte para "
            "dar um basta nisso. Limpem a floresta, em nome de Eldora!\""
        ),
        "objective": "A sua guilda foi contratada para erradicar 500 Goblins Batedores da Floresta Sombria.",
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
        "story": (
            "\"Eles estão por toda parte!\" grita o Mestre Mineiro Durin. \"Esses malditos Kobolds "
            "Escavadores estão a sabotar nossos túneis na Pedreira de Granito, roubando "
            "ferramentas e causando desmoronamentos. Se não os pararmos, a produção de "
            "pedra para a capital vai parar!\""
        ),
        "objective": "Os Kobolds Escavadores estão a sabotar as operações na Pedreira de Granito. Acabem com 400 deles.",
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
        "story": (
            "Um caçador local chega à guilda, pálido e ofegante. \"Não é uma alcateia comum... "
            "os olhos deles... brilham com uma malícia sombria. Os Lobos Alfa estão "
            "maiores, mais rápidos e anormalmente agressivos. Eles não estão caçando "
            "por comida, estão caçando por esporte. Os viajantes não têm chance.\""
        ),
        "objective": "Uma alcateia de Lobos Alfa agressiva está a aterrorizar os viajantes. Cace 100 dos líderes da alcateia.",
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
        "title": "Desafio do Dia: Olhar Petrificante",
        "story": (
            "Um erudito da Torre de Marfim enviou um pedido urgente. \"Um Basilisco Jovem "
            "foi avistado na Pedreira! Precisamos de espécimes antes que ele amadureça "
            "e se torne uma ameaça de nível 'catástrofe'. Uma guilda rápida e "
            "coordenada pode dar conta do recado. Mas cuidado com seus olhos!\""
        ),
        "objective": "Um Basilisco Jovem foi avistado na Pedreira. Derrotem 10 deles como um esforço de equipa antes que cresçam.",
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