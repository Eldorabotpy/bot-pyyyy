# Em pvp/pvp_config.py

ELO_THRESHOLDS = {
    "Bronze": 0,
    "Prata": 1500,
    "Ouro": 4000,
    "Diamante": 8000,
    "Mestre da Arena": 10000,
}

# Dicionário com os nomes de exibição e emojis
ELO_DISPLAY = {
    "Bronze": "🥉 Bronze",
    "Prata": "🥈 Prata",
    "Ouro": "🥇 Ouro",
    "Diamante": "💎 Diamante",
    "Mestre da Arena": "👑 Mestre da Arena",
}

# Dicionário com as recompensas semanais para cada Elo
# A chave é o nome do Elo, o valor é um dicionário de recompensas {item_id: quantidade}
WEEKLY_REWARDS = {
    "Bronze": {"ouro": 5000},
    "Prata": {"ouro": 15000, "cristal_de_abertura": 1},
    "Ouro": {"ouro": 50000, "cristal_de_abertura": 3, "gems": 10},
    "Diamante": {"ouro": 100000, "cristal_de_abertura": 5, "gems": 50},
    "Mestre da Arena": {"ouro": 250000, "cristal_de_abertura": 10, "gems": 150, "sigilo_protecao": 1},
}

ARENA_MODIFIERS = {
    # Segunda-feira (weekday() == 0)
    0: {
        "name": "Dia da Fúria 😡",
        "effect": "fury_day",
        "description": "Todos os jogadores recebem +20% de Ataque, mas -10% de Defesa."
    },
    # Terça-feira (weekday() == 1)
    1: {
        "name": "Dia da Agilidade ⚡️",
        "effect": "agility_day",
        "description": "A chance de Esquiva e Ataque Duplo de todos os jogadores é aumentada em 15%."
    },
    # =========================================================
    # 👇 [CORREÇÃO DE BALANCEAMENTO] 👇
    # =========================================================
    # Quarta-feira (weekday() == 2)
    2: {
        "name": "Dia da Muralha 🛡️",
        "effect": "wall_day",
        # Alterado de "Defesa dobrada / Ataque -25%"
        "description": "A Defesa de todos os jogadores aumenta em 50%, mas o Ataque é reduzido em 20%."
    },
    # =========================================================
    # 👆 [FIM DA CORREÇÃO] 👆
    # =========================================================
    # Quinta-feira (weekday() == 3)
    3: {
        "name": "Dia da Sorte Crítica 🍀",
        "effect": "critical_day",
        "description": "A chance de Acerto Crítico de todos os jogadores é aumentada em 20%."
    },
    # Sexta-feira (weekday() == 4)
    4: {
        "name": "Dia da Ganância 💰",
        "effect": "greed_day",
        "description": "As recompensas em Ouro por vitória na arena são dobradas!"
    },
    # Sábado (weekday() == 5)
    5: {
        "name": "Dia do Prestígio 🏆",
        "effect": "prestige_day",
        "description": "Os pontos de Elo ganhos ou perdidos são aumentados em 50%."
    },
    # Domingo (weekday() == 6)
    6: {
        "name": "Arena de Vidro 💥",
        "effect": "glass_cannon_day",
        "description": "O Ataque de todos é dobrado, mas a Defesa é zerada. Lutas rápidas e mortais!"
    }
}