# modules/mission_manager.py

import random
from datetime import datetime, timezone
from modules import player_manager, clan_manager, guild_system
from modules.game_data.missions import MISSION_CATALOG
from modules.game_data.guild_missions import GUILD_MISSIONS_CATALOG

# ==============================================================================
# MISSÕES PESSOAIS (GUILDA DE AVENTUREIROS)
# ==============================================================================

def get_player_missions(user_id: int) -> dict:
    """
    Obtém as missões diárias de um jogador (lógica síncrona de leitura).
    Nota: Quem chamar deve ter o player_data carregado ou gerenciar o save.
    """
    # Esta função é um helper de leitura. A geração real é feita no guild_system.py
    # e chamada pelo menu handler.
    # Se precisar ler do banco aqui, teria que ser async.
    # Para compatibilidade com handlers síncronos antigos, mantemos a lógica simples
    # de retornar estrutura vazia se não tiver dados.
    return {} 

async def update_mission_progress(user_id: int, action_type: str, target_id: str, quantity: int = 1):
    """
    Chamado sempre que algo acontece no jogo (combate, coleta, craft).
    Verifica e atualiza missões PESSOAIS e de CLÃ.
    """
    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return

    # 1. MISSÕES PESSOAIS (Guilda de Aventureiros)
    gdata = player_data.get("adventurer_guild", {})
    missions = gdata.get("active_missions", [])
    updated = False

    for m in missions:
        if m.get("status") == "active":
            # Verifica tipo e alvo
            # Ex: type='hunt', target='slime'
            if m.get("type") == action_type and m.get("target") == target_id:
                current = m.get("progress", 0)
                req = m.get("qty", 1)
                
                if current < req:
                    m["progress"] = min(current + quantity, req)
                    updated = True
                    
                    if m["progress"] >= req:
                        m["status"] = "completed"
                        # Opcional: Notificar jogador aqui se tiver context

    if updated:
        player_data["adventurer_guild"] = gdata
        await player_manager.save_player_data(user_id, player_data)

    # 2. MISSÕES DE CLÃ (Coletivas)
    clan_id = player_data.get("clan_id")
    if clan_id:
        # Busca missão ativa do clã
        active_mission = await clan_manager.get_active_guild_mission(clan_id)
        
        if active_mission:
            c_type = active_mission.get("type")
            c_target = active_mission.get("target_monster_id") # ou target_item_id dependendo da missão
            
            # Mapeamento de tipos (ajuste conforme seu catalogo)
            # Se no catalogo for MONSTER_HUNT e a ação for 'hunt'
            match = False
            if c_type == "MONSTER_HUNT" and action_type == "hunt":
                if c_target == target_id: match = True
            elif c_type == "COLLECT" and action_type == "collect":
                # Assumindo que missões de coleta usem target_item_id ou similar
                if active_mission.get("target_item_id") == target_id: match = True
            
            if match:
                # Atualiza o clã atomicamente (banco de dados)
                # Como o clan_manager.update_guild_mission_progress não existe no código final do clan_manager,
                # vamos implementar a lógica de incremento direto aqui.
                
                # Nota: Idealmente, isso estaria no clan_manager para encapsulamento.
                # Mas como estamos unificando, faremos a chamada direta ao banco do clã aqui
                # ou usamos uma função helper se existir.
                
                # Vamos assumir que precisamos incrementar 'active_mission.current_progress'
                from modules.clan_manager import clans_col
                if clans_col is not None:
                    clans_col.update_one(
                        {"_id": clan_id},
                        {"$inc": {"active_mission.current_progress": quantity}}
                    )
                    
                    # Verifica conclusão (precisa ler o valor atualizado)
                    # Para performance, podemos não verificar a cada kill, 
                    # ou fazer uma verificação leve.
                    # O menu do clã já checa isso visualmente.
                    # A conclusão real é feita pelo líder no botão "Concluir" ou automática
                    # se implementarmos um check periódico.


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
    
    # Dá recompensas
    gold = mission.get("reward_gold", 0)
    pts = mission.get("reward_points", 0)
    
    if gold > 0: player_manager.add_gold(player_data, gold)
    
    # Adiciona pontos de rank
    gdata["points"] = gdata.get("points", 0) + pts
    
    # Remove a missão da lista (ou marca como claimada/arquivada)
    # Para missões diárias, geralmente removemos ou substituímos.
    # Aqui vamos remover para simples rotação, ou marcar 'claimed'.
    mission["status"] = "claimed" # Marca como feito para não sumir até o reset
    # Se quiser substituir imediatamente por outra (ciclo infinito):
    # new_mission = ... (logica de gerar nova)
    # missions[mission_index] = new_mission
    
    player_data["adventurer_guild"] = gdata
    
    # Verifica Rank Up
    rank_up, new_rank = guild_system.check_rank_up(player_data)
    
    await player_manager.save_player_data(user_id, player_data)
    
    return {
        "gold": gold,
        "points": pts,
        "rank_up": new_rank if rank_up else None
    }

# Mantivemos reroll_mission para compatibilidade se usado em handlers antigos,
# mas a lógica principal agora é via guild_system e reset diário.
def reroll_mission(user_id, index):
    return False