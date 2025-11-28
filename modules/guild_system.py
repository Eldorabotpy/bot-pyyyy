# modules/guild_system.py
# (VERSÃO FINAL: COM EMOJIS NOS RANKS)

import random
from datetime import datetime, timezone

# Configuração dos Ranks (AGORA COM EMOJIS)
ADVENTURER_RANKS = {
    "F": {"title": "Novato",      "next": "E", "req_points": 100,   "emoji": "🌱"},
    "E": {"title": "Iniciado",    "next": "D", "req_points": 300,   "emoji": "🪵"},
    "D": {"title": "Aventureiro", "next": "C", "req_points": 800,   "emoji": "🥉"},
    "C": {"title": "Veterano",    "next": "B", "req_points": 2000,  "emoji": "🥈"},
    "B": {"title": "Elite",       "next": "A", "req_points": 5000,  "emoji": "🥇"},
    "A": {"title": "Herói",       "next": "S", "req_points": 10000, "emoji": "🎗️"},
    "S": {"title": "Lenda",       "next": None, "req_points": 0,    "emoji": "👑"}
}

# Missões Diárias (Templates)
MISSION_TEMPLATES = [
    {"type": "hunt", "target": "slime", "qty": 10, "name": "Praga Gosmenta", "desc": "Elimine 10 Slimes.", "xp": 50, "pts": 10},
    {"type": "hunt", "target": "lobo", "qty": 5, "name": "Uivos na Noite", "desc": "Cace 5 Lobos.", "xp": 80, "pts": 15},
    {"type": "collect", "target": "madeira", "qty": 10, "name": "Reforma da Guilda", "desc": "Entregue 10 Madeiras.", "xp": 40, "pts": 10},
    {"type": "collect", "target": "ferro", "qty": 5, "name": "Armas para Novatos", "desc": "Doe 5 Minérios de Ferro.", "xp": 60, "pts": 15},
]

def get_rank_info(rank: str) -> dict:
    """Retorna os dados do rank. Se não existir, retorna o rank F."""
    return ADVENTURER_RANKS.get(rank, ADVENTURER_RANKS["F"])

def generate_daily_missions(pdata: dict):
    """Gera 3 missões novas se o dia mudou."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    gdata = pdata.get("adventurer_guild", {})
    
    # Se já tem missões de hoje, retorna as existentes
    if gdata.get("last_mission_date") == today:
        return gdata.get("active_missions", [])

    new_missions = []
    # Seleciona 3 missões aleatórias
    templates = random.sample(MISSION_TEMPLATES, k=min(3, len(MISSION_TEMPLATES)))
    
    for t in templates:
        m = t.copy()
        m["id"] = f"ms_{random.randint(10000,99999)}"
        m["status"] = "active"
        # Variação de recompensa baseada no nível do jogador (simples)
        lvl = pdata.get("level", 1)
        m["reward_gold"] = int(random.randint(50, 100) * (1 + (lvl * 0.1)))
        m["reward_points"] = m.get("pts", 10)
        new_missions.append(m)
    
    gdata["last_mission_date"] = today
    gdata["active_missions"] = new_missions
    pdata["adventurer_guild"] = gdata
    return new_missions