# modules/mission_manager.py
# (VERSÃO FINAL COMPATÍVEL COM SEU MONSTERS.PY)

import logging
from modules import player_manager, clan_manager, guild_system, game_data
# Importamos a coleção do DB para updates atômicos de clã (se usar MongoDB)
# Se não usar, a parte de clã precisará ser adaptada.
from modules.database import db 

logger = logging.getLogger(__name__)

# ==============================================================================
# MISSÕES PESSOAIS
# ==============================================================================

def get_player_missions(user_id: int) -> dict:
    """
    Retorna missões apenas para leitura visual.
    A geração real ocorre no guild_system.py.
    """
    return {} 

async def update_mission_progress(user_id: int, action_type: str, target_id: str, quantity: int = 1):
    """
    Central de processamento de missões.
    
    Args:
        user_id: ID do jogador
        action_type: "hunt", "collect", "craft", etc.
        target_id: ID do monstro (ex: 'goblin_batedor') ou item (ex: 'madeira')
        quantity: Quantidade a incrementar
    """
    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return []

    logs = []

    # --- 0. ENRIQUECIMENTO DE DADOS (LOOKUP INTELIGENTE) ---
    # Aqui adaptamos para ler o seu MONSTERS_DATA
    target_info = {}
    target_region = None
    is_elite = False
    is_boss = False

    if action_type == "hunt":
        # 1. Tenta pegar o dicionário global de monstros
        # (Assume que game_data.MONSTERS_DATA é o dict do seu arquivo)
        monsters_db = getattr(game_data, "MONSTERS_DATA", {})
        
        # 2. Varre as regiões para encontrar o monstro e definir a região
        for region_key, monster_list in monsters_db.items():
            if not isinstance(monster_list, list): continue # Pula _evolution_trials se não for lista de dicts padrão
            
            for m in monster_list:
                if m.get("id") == target_id:
                    target_info = m
                    target_region = region_key # "floresta_sombria", "pradaria_inicial", etc.
                    break
            if target_region: break
        
        # 3. Define propriedades especiais
        # Verifica se é Elite OU Boss (para missões de desafio)
        is_elite = target_info.get("is_elite", False)
        is_boss = target_info.get("is_boss", False)
        
        # Se for Boss, conta como Elite também para facilitar missões
        if is_boss: is_elite = True

    # ====================================================
    # 1. MISSÕES PESSOAIS (Guilda de Aventureiros)
    # ====================================================
    gdata = player_data.get("adventurer_guild", {})
    missions = gdata.get("active_missions", [])
    updated = False

    for m in missions:
        if m.get("status") != "active": continue
        
        mission_type = m.get("type", "").upper()
        req_action = action_type.upper()

        match = False
        
        # --- CAÇA (HUNT) ---
        if req_action == "HUNT":
            # 1.1 Caça Específica (ID Exato)
            if mission_type == "HUNT" and m.get("target_id") == target_id:
                match = True
            
            # 1.2 Caça Regional (Qualquer monstro da região)
            # Ex: "Derrote 5 monstros na Floresta Sombria"
            elif mission_type == "HUNT" and m.get("target_region") == target_region and not m.get("target_id"):
                match = True
                
            # 1.3 Caça Global (Qualquer monstro)
            elif mission_type == "HUNT" and not m.get("target_region") and not m.get("target_id"):
                match = True

            # 1.4 Caça de Elite/Boss
            elif mission_type == "HUNT_ELITE" and is_elite:
                match = True

        # --- COLETA (COLLECT) ---
        elif req_action == "COLLECT" and mission_type == "COLLECT":
            if m.get("target_id") == target_id:
                match = True

        # --- OUTROS (Craft, Spend Energy) ---
        elif mission_type == req_action and m.get("target_id") == target_id:
            match = True

        # --- APLICA PROGRESSO ---
        if match:
            current = m.get("progress", 0)
            req = m.get("target_count", m.get("qty", 1))
            
            if current < req:
                increment = min(quantity, req - current)
                m["progress"] = current + increment
                updated = True
                
                if m["progress"] >= req:
                    m["status"] = "completed"
                    # logs.append(f"✅ Missão Concluída: <b>{m.get('title', 'Missão')}</b>!")

    if updated:
        player_data["adventurer_guild"] = gdata
        await player_manager.save_player_data(user_id, player_data)

    # ====================================================
    # 2. MISSÕES DE CLÃ (Coletivas)
    # ====================================================
    clan_id = player_data.get("clan_id")
    if clan_id:
        try:
            # Busca missão ativa do clã no DB
            clan = await db.clans.find_one({"_id": clan_id}, {"active_mission": 1})
            active_mission = clan.get("active_mission") if clan else None

            if active_mission and not active_mission.get("completed", False):
                c_type = active_mission.get("type")
                c_target = active_mission.get("target_monster_id") or active_mission.get("target_id")
                
                match_clan = False
                
                if action_type == "hunt":
                    # Caça exata
                    if c_type == "HUNT" and c_target == target_id:
                        match_clan = True
                    # Caça Elite Global
                    elif c_type == "HUNT_ELITE" and is_elite:
                        match_clan = True
                        
                elif action_type == "collect" and c_type == "COLLECT":
                    if active_mission.get("target_item_id") == target_id:
                        match_clan = True

                if match_clan:
                    # Update atômico e seguro no DB
                    await db.clans.update_one(
                        {"_id": clan_id},
                        {"$inc": {"active_mission.current_progress": quantity}}
                    )
        except Exception as e:
            logger.error(f"Erro ao atualizar missão de clã: {e}")

    return logs

async def claim_personal_reward(user_id: int, mission_index: int):
    """
    Reclama a recompensa e aplica (Gold, XP, Pontos de Guilda).
    """
    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return None
    
    gdata = player_data.get("adventurer_guild", {})
    missions = gdata.get("active_missions", [])
    
    if mission_index < 0 or mission_index >= len(missions): return None
    
    mission = missions[mission_index]
    if mission.get("status") != "completed": return None
    
    # Processa Recompensas
    rewards = mission.get("rewards", {})
    gold = rewards.get("gold", 0)
    xp = rewards.get("xp", 0)
    points = rewards.get("prestige_points", 0)
    
    if gold > 0: player_manager.add_gold(player_data, gold)
    if xp > 0: player_data["xp"] = player_data.get("xp", 0) + xp
    
    # Pontos de Rank
    gdata["points"] = gdata.get("points", 0) + points
    
    # Marca como coletada
    mission["status"] = "claimed"
    
    player_data["adventurer_guild"] = gdata
    
    # Verifica Rank Up
    rank_up_info = await guild_system.check_rank_up(player_data)
    
    await player_manager.save_player_data(user_id, player_data)
    
    return {
        "gold": gold,
        "xp": xp,
        "points": points,
        "rank_up": rank_up_info
    }

def reroll_mission(user_id, index):
    return False