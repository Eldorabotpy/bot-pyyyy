# modules/guild_system.py
# (VERSÃO CORRIGIDA: Filtra geração de missões de Coleta)

import random
from datetime import datetime, timezone
from modules.game_data.missions import MISSION_CATALOG 

# Configuração dos Ranks (Visual)
ADVENTURER_RANKS = {
    "F": {"title": "Novato",      "next": "E", "req_points": 100,   "emoji": "🌱"},
    "E": {"title": "Iniciado",    "next": "D", "req_points": 300,   "emoji": "🪵"},
    "D": {"title": "Aventureiro", "next": "C", "req_points": 800,   "emoji": "🥉"},
    "C": {"title": "Veterano",    "next": "B", "req_points": 2000,  "emoji": "🥈"},
    "B": {"title": "Elite",       "next": "A", "req_points": 5000,  "emoji": "🥇"},
    "A": {"title": "Herói",       "next": "S", "req_points": 10000, "emoji": "🎗️"},
    "S": {"title": "Lenda",       "next": None, "req_points": 0,    "emoji": "👑"}
}

def get_rank_info(rank: str) -> dict:
    """Retorna os dados do rank. Se não existir, retorna o rank F."""
    return ADVENTURER_RANKS.get(rank, ADVENTURER_RANKS["F"])

# [MANTIDO ASYNC] Compatível com o await no mission_manager
async def check_rank_up(player_data: dict) -> dict | None:
    """
    Verifica se o jogador pode subir de rank.
    Retorna dict com info do novo rank se subiu, ou None.
    """
    gdata = player_data.get("adventurer_guild", {})
    current_rank_id = gdata.get("rank", "F")
    points = gdata.get("points", 0)
    
    current_info = get_rank_info(current_rank_id)
    next_rank_id = current_info.get("next")
    
    if not next_rank_id: return None # Já é rank máximo
    
    req_points = current_info.get("req_points", 999999)
    
    if points >= req_points:
        # Subiu de rank!
        gdata["rank"] = next_rank_id
        # Reseta pontos excedentes ou acumula? Normalmente acumula.
        
        player_data["adventurer_guild"] = gdata
        
        new_rank_info = get_rank_info(next_rank_id)
        return {
            "old_rank": current_rank_id,
            "new_rank": next_rank_id,
            "title": new_rank_info["title"],
            "emoji": new_rank_info["emoji"]
        }
    return None

def generate_daily_missions(pdata: dict):
    """
    Gera 3 missões novas baseadas no MISSION_CATALOG se o dia mudou.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    gdata = pdata.get("adventurer_guild", {})
    
    # Se já tem missões de hoje, retorna as existentes
    if gdata.get("last_mission_date") == today and gdata.get("active_missions"):
        return gdata.get("active_missions", [])

    new_missions = []
    
    # [CORREÇÃO IMPORTANTE] Filtra missões de COLETA para não serem geradas
    all_templates = MISSION_CATALOG
    available_templates = [
        m for m in all_templates
        if str(m.get("type", "")).upper() != "COLLECT"
    ]
    
    # Se não sobrar nenhuma (ex: só tinha coleta), evita crash
    if not available_templates:
        return []

    count = min(3, len(available_templates))
    if count == 0: return []
    
    chosen_templates = random.sample(available_templates, k=count)
    
    player_lvl = pdata.get("level", 1)
    
    for t in chosen_templates:
        m = t.copy()
        
        m["status"] = "active"
        m["progress"] = 0
        
        base_rewards = m.get("rewards", {})
        gold = base_rewards.get("gold", 0)
        xp = base_rewards.get("xp", 0)
        
        # Bônus de nível
        bonus_mult = 1 + (player_lvl * 0.05)
        
        m["rewards"] = {
            "gold": int(gold * bonus_mult),
            "xp": int(xp * bonus_mult),
            "prestige_points": base_rewards.get("prestige_points", 5)
        }
        
        new_missions.append(m)
    
    gdata["last_mission_date"] = today
    gdata["active_missions"] = new_missions
    pdata["adventurer_guild"] = gdata
    
    return new_missions