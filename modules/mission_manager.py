# Ficheiro: modules/mission_manager.py

import random
from datetime import datetime
from modules import player_manager, clan_manager
from modules.game_data.missions import MISSION_CATALOG
from modules import mission_manager
def _generate_new_daily_missions(user_id: int) -> dict:
    """Sorteia 5 missões únicas do catálogo e prepara a estrutura para o jogador."""
    
    # Garante que não sorteamos mais missões do que as que existem
    sample_size = min(5, len(MISSION_CATALOG))
    
    # Sorteia 5 modelos de missão aleatórios e únicos
    mission_templates = random.sample(MISSION_CATALOG, k=sample_size)
    
    active_missions = []
    for template in mission_templates:
        active_missions.append({
            "mission_id": template["id"],
            "progress": 0,
            "is_complete": False,
            "is_claimed": False, # Para saber se a recompensa já foi entregue
        })

    return {
        "daily_rerolls_left": 2,
        "last_refresh_date": datetime.now().date().isoformat(),
        "active_missions": active_missions
    }

def get_player_missions(user_id: int) -> dict:
    """
    Obtém as missões diárias de um jogador.
    Se for um novo dia, gera uma nova lista de missões.
    """
    player_data = player_manager.get_player_data(user_id)
    missions_data = player_data.get("missions", {})
    today = datetime.now().date().isoformat()
    
    # Se a data do último refresh for diferente de hoje, gera novas missões
    if missions_data.get("last_refresh_date") != today:
        missions_data = _generate_new_daily_missions(user_id)
        player_data["missions"] = missions_data
        player_manager.save_player_data(user_id, player_data)
        
    return missions_data


# Em modules/mission_manager.py
# Substitua a sua função 'update_mission_progress' por esta versão final

def update_mission_progress(player_data: dict, event_type: str, details: dict) -> bool:
    user_id = player_data.get("user_id")
    if not user_id:
        return False

    missions_data = player_data.get("missions")
    if not missions_data:
        return False

    something_changed = False
    for mission in missions_data.get("active_missions", []):
        if mission.get("is_complete"):
            continue

        template = next((m for m in MISSION_CATALOG if m["id"] == mission["mission_id"]), None)
        if not template:
            continue

        if template.get("type") == event_type:
            match = False
            increment = 1
            
            if event_type == "HUNT":
                target_region = template.get("target_region")
                details_region = details.get("region")
                region_ok = not target_region or target_region == details_region
                
                target_mob = template.get("target_id")
                details_mob = details.get("monster_id")
                mob_ok = not target_mob or target_mob == details_mob
                
                if region_ok and mob_ok:
                    match = True

            # --- LÓGICA PARA ELITE ---
            elif event_type == "HUNT_ELITE":
                # Missões de elite geralmente não precisam de mais verificações
                match = True
            
            elif event_type in ("REFINE", "CRAFT", "MARKET_SELL"):
                # ... (outras lógicas que já implementámos) ...
                match = True
            
            elif event_type == "ENHANCE_SUCCESS":
                match = True

            if match:
                mission["progress"] = mission.get("progress", 0) + increment
                something_changed = True
                target_count = template.get("target_count", 1)
                if mission["progress"] >= target_count:
                    mission["is_complete"] = True

    return something_changed

def reroll_mission(user_id: int, mission_index: int) -> bool:
    """Substitui uma missão por uma nova do catálogo, se houver rerolls."""
    player_data = player_manager.get_player_data(user_id)
    missions_data = player_data.get("missions", {})
    
    if missions_data.get("daily_rerolls_left", 0) <= 0:
        return False # Sem rerolls

    active_missions = missions_data.get("active_missions", [])
    if not (0 <= mission_index < len(active_missions)):
        return False # Índice inválido

    # Pega IDs das missões atuais para não sortear uma repetida
    current_mission_ids = {m["mission_id"] for m in active_missions}
    
    # Filtra o catálogo para encontrar missões que o jogador ainda não tem
    available_pool = [m for m in MISSION_CATALOG if m["id"] not in current_mission_ids]
    if not available_pool:
        return False # Não há mais missões únicas para sortear

    # Sorteia uma nova missão
    new_template = random.choice(available_pool)
    
    # Substitui a missão antiga pela nova
    active_missions[mission_index] = {
        "mission_id": new_template["id"],
        "progress": 0,
        "is_complete": False,
        "is_claimed": False,
    }

    missions_data["daily_rerolls_left"] -= 1
    player_data["missions"] = missions_data
    player_manager.save_player_data(user_id, player_data)
    return True

# Adicione esta nova função no final do ficheiro modules/mission_manager.py

def get_clan_mission_stats(clan_id: int) -> dict:
    """
    Calcula as estatísticas de missões para uma guilda inteira.
    Conta o total de missões concluídas por todos os membros.

    Args:
        clan_id (int): O ID da guilda a ser verificada.

    Returns:
        dict: Um dicionário contendo as estatísticas, como 'completed_missions_count'.
    """
    # 1. Obter a lista de IDs de todos os membros da guilda.
    #    (Estou a supor que existe uma função assim em clan_manager. Se o nome for
    #     diferente, basta ajustá-lo).
    try:
        member_ids = clan_manager.get_clan_member_ids(clan_id)
        if not member_ids:
            # Retorna zero se a guilda não tiver membros
            return {"completed_missions_count": 0}
    except Exception as e:
        # Se a função não existir ou der erro, retorna 0 para não quebrar o jogo.
        print(f"AVISO: Não foi possível obter membros do clã {clan_id}. Erro: {e}")
        return {"completed_missions_count": 0}

    # 2. Inicializar o contador total de missões concluídas.
    total_concluidas = 0

    # 3. Percorrer a lista de IDs de cada membro.
    for user_id in member_ids:
        # 4. Para cada membro, obter os seus dados de missão.
        #    A função get_player_missions já trata da lógica de criar missões se não existirem.
        player_missions_data = get_player_missions(user_id)
        
        active_missions = player_missions_data.get("active_missions", [])

        # 5. Percorrer as missões ativas do membro atual.
        for mission in active_missions:
            # 6. Verificar se a missão está completa.
            #    Usar .get() é mais seguro, pois evita erros se a chave não existir.
            if mission.get("is_complete"):
                # 7. Se estiver completa, incrementar o contador.
                total_concluidas += 1

    # 8. Retornar o resultado num dicionário para futura expansão (ex: total de progresso, etc.)
    return {"completed_missions_count": total_concluidas}

def show_clan_status(user_id):
    # ... obter os dados do jogador e do seu clã ...
    player_data = player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")

    if not clan_id:
        print("Você não está numa guilda!")
        return

    # Chama a nossa nova função!
    stats = mission_manager.get_clan_mission_stats(clan_id)
    
    # Extrai o valor do dicionário retornado
    missoes_concluidas = stats["completed_missions_count"]

    print(f"--- Status da Guilda ---")
    print(f"Missões Diárias Concluídas pela Guilda: {missoes_concluidas}")
    # ... mostrar outras informações da guilda ...

# Em modules/mission_manager.py
# SUBSTITUA a sua função claim_reward por esta nova versão:

# No arquivo: modules/mission_manager.py
# Substitua a sua função 'claim_reward' inteira por esta:

def claim_reward(player_data: dict, mission_index: int) -> dict | None:
    """
    Dá a recompensa e substitui a missão por uma nova, permitindo a repetição
    de missões já concluídas para um ciclo infinito.
    """
    missions_data = player_data.get("missions", {})
    active_missions = missions_data.get("active_missions", [])

    if not (0 <= mission_index < len(active_missions)):
        return None

    mission_to_claim = active_missions[mission_index]
    if not mission_to_claim.get("is_complete") or mission_to_claim.get("is_claimed"):
        return None

    template = next((m for m in MISSION_CATALOG if m["id"] == mission_to_claim["mission_id"]), None)
    if not template:
        return None

    # --- Parte 1: Dar a recompensa ---
    rewards = template.get("rewards", {})
    xp = rewards.get("xp", 0)
    gold = rewards.get("gold", 0)
    prestige = rewards.get("prestige_points", 0)

    player_data["xp"] = player_data.get("xp", 0) + xp
    player_data["gold"] = player_data.get("gold", 0) + gold

    clan_id = player_data.get("clan_id")
    if clan_id and prestige > 0:
        clan_manager.add_prestige_points(clan_id, prestige)
    
    # --- Parte 2: Substituir a missão por uma nova (com repetição) ---
    current_mission_ids = {m["mission_id"] for i, m in enumerate(active_missions) if i != mission_index}
    available_pool = [m for m in MISSION_CATALOG if m["id"] not in current_mission_ids]
    
    if not available_pool:
        mission_to_claim["is_claimed"] = True
        print("AVISO: Catálogo de missões muito pequeno. Não foi possível sortear uma nova missão.")
    else:
        new_template = random.choice(available_pool)
        active_missions[mission_index] = {
            "mission_id": new_template["id"],
            "progress": 0,
            "is_complete": False,
            "is_claimed": False,
        }
        
    player_data["missions"] = missions_data
    # A função modifica os dados, mas a responsabilidade de salvar é de quem a chamou.
    return rewards