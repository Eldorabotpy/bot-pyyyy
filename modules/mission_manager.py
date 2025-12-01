# modules/mission_manager.py
# (VERSÃO LIMPA: Lógica de Coleta REMOVIDA)

import logging
from modules import player_manager, guild_system, game_data
# Importamos a coleção do DB
from modules.database import db 

logger = logging.getLogger(__name__)

# ==============================================================================
# MISSÕES PESSOAIS
# ==============================================================================

def get_player_missions(user_id: int) -> dict:
    """Retorna missões apenas para leitura."""
    return {} 

async def update_mission_progress(user_id: int, action_type: str, target_id: str, quantity: int = 1):
    """
    Central de processamento de missões com logs detalhados.
    """
    
    # [DEBUG]
    print(f"\n--- [MISSION DEBUG] Tentando atualizar: User={user_id}, Action={action_type}, Target={target_id}, Qty={quantity} ---")

    player_data = await player_manager.get_player_data(user_id)
    if not player_data: 
        print("[MISSION DEBUG] Player data não encontrado.")
        return []

    logs = []

    # --- 0. ENRIQUECIMENTO DE DADOS (LOOKUP) ---
    target_info = {}
    target_region = None
    is_elite = False
    is_boss = False

    if action_type == "hunt":
        monsters_db = getattr(game_data, "MONSTERS_DATA", {})
        
        # Varre as regiões para encontrar o monstro
        for region_key, monster_list in monsters_db.items():
            if not isinstance(monster_list, list): continue 
            
            for m in monster_list:
                # Compara ID como string para evitar erro de tipo
                if str(m.get("id")) == str(target_id):
                    target_info = m
                    target_region = region_key 
                    break
            if target_region: break
        
        # Define propriedades baseadas no que achou
        is_elite = target_info.get("is_elite", False)
        is_boss = target_info.get("is_boss", False)
        if is_boss: is_elite = True
        
        print(f"[MISSION DEBUG] Monster Info: Region={target_region}, Elite={is_elite}")

    # ====================================================
    # 1. MISSÕES PESSOAIS (Guilda de Aventureiros)
    # ====================================================
    gdata = player_data.get("adventurer_guild", {})
    missions = gdata.get("active_missions", [])
    updated = False

    for m in missions:
        if m.get("status") != "active": continue
        
        mission_type = m.get("type", "").upper() # No save pode estar lowercase
        req_action = action_type.upper() # Padroniza para UPPER

        match = False
        
        # --- Lógica de CAÇA (HUNT) ---
        if req_action == "HUNT":
            # 1.1 Caça Específica (Pelo ID exato)
            if mission_type == "HUNT" and str(m.get("target_id")) == str(target_id):
                match = True
            
            # 1.2 Caça Regional (Qualquer monstro da região)
            elif mission_type == "HUNT" and m.get("target_region") == target_region and not m.get("target_id"):
                match = True
                
            # 1.3 Caça Global (Qualquer monstro)
            elif mission_type == "HUNT" and not m.get("target_region") and not m.get("target_id"):
                match = True

            # 1.4 Caça de Elite
            elif mission_type == "HUNT_ELITE" and is_elite:
                match = True

        # [REMOVIDO] Lógica de COLETA (COLLECT) retirada daqui.

        # --- Lógica de OUTROS (Craft, Spend Energy, etc - genérico) ---
        elif mission_type == req_action and str(m.get("target_id")) == str(target_id):
            match = True

        # --- APLICA O PROGRESSO ---
        if match:
            current = m.get("progress", 0)
            req = m.get("target_count", m.get("qty", 1)) # Tenta pegar target_count, fallback para qty
            
            if current < req:
                increment = min(quantity, req - current)
                m["progress"] = current + increment
                updated = True
                
                # Verifica conclusão
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
            # Sem 'await' pois o driver é síncrono
            clan = db.clans.find_one({"_id": clan_id}, {"active_mission": 1})
            active_mission = clan.get("active_mission") if clan else None

            if active_mission:
                c_type = active_mission.get("type")
                c_target = active_mission.get("target_monster_id") or active_mission.get("target_id")
                completed = active_mission.get("completed", False)
                
                print(f"[MISSION DEBUG] Clã tem missão: Type={c_type}, Target={c_target}, Completed={completed}")

                if not completed:
                    match_clan = False
                    
                    if action_type == "hunt":
                        # Caça exata
                        if str(c_type).upper() == "HUNT" and str(c_target) == str(target_id):
                            match_clan = True
                            print("[MISSION DEBUG] MATCH! Missão de caça exata encontrada.")
                        # Caça Elite Global
                        elif str(c_type).upper() == "HUNT_ELITE" and is_elite:
                            match_clan = True
                            print("[MISSION DEBUG] MATCH! Missão de elite encontrada.")
                        
                    # [REMOVIDO] Lógica de coleta de Clã retirada.

                    if match_clan:
                        print(f"[MISSION DEBUG] Atualizando banco de dados (+{quantity})...")
                        # Update atômico no DB do Clã (seguro para concorrência)
                        db.clans.update_one(
                            {"_id": clan_id},
                            {"$inc": {"active_mission.current_progress": quantity}}
                        )
                    else:
                        print(f"[MISSION DEBUG] Sem match de Clã. Tipo ação: {action_type}")
            else:
                print("[MISSION DEBUG] Clã sem missão ativa.")

        except Exception as e:
            logger.error(f"Erro ao atualizar missão de clã: {e}")
            print(f"[MISSION DEBUG] Erro Exception: {e}")

    return logs

async def claim_personal_reward(user_id: int, mission_index: int):
    """
    Reclama a recompensa de uma missão pessoal concluída.
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
    
    # Pontos de Guilda (Rank)
    gdata["points"] = gdata.get("points", 0) + points
    
    # Marca como coletada ('claimed')
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