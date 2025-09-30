# Em pvp/pvp_config.py

# Dicionário com os limites de pontos para cada Elo
ELO_THRESHOLDS = {
    "Bronze": 0,
    "Prata": 500,
    "Ouro": 1000,
    "Diamante": 2000,
    "Mestre da Arena": 4000,
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
    "Mestre da Arena": {"ouro": 250000, "cristal_de_abertura": 10, "gems": 100, "sigilo_protecao": 1},
}