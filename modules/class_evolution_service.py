# modules/class_evolution_service.py
# (VERSÃO CORRIGIDA E FINAL: ÁRVORE + SKILLS LEVEL SYSTEM)

from __future__ import annotations
from typing import Dict, Tuple, Optional, List, Any
from modules import player_manager
from modules.game_data import class_evolution as evo_data 

# ================================================
# FUNÇÕES AUXILIARES DE INVENTÁRIO
# ================================================

def _inventory_has(pdata: Dict, required_items: Dict[str, int]) -> bool:
    """Verifica se o jogador tem os itens (Wrapper)."""
    for item_id, qty in required_items.items():
        if not player_manager.has_item(pdata, item_id, qty):
            return False
    return True

def _consume_items(pdata: Dict, required_items: Dict[str, int]) -> bool:
    """Consome os itens do inventário."""
    if not _inventory_has(pdata, required_items):
        return False
        
    for item_id, qty in required_items.items():
        player_manager.remove_item_from_inventory(pdata, item_id, qty)
    return True

def _consume_gold(pdata: Dict, amount: int) -> bool:
    """Consome ouro do jogador."""
    current_gold = pdata.get("gold", 0)
    if current_gold < amount:
        return False
    pdata["gold"] = current_gold - amount
    return True

# ================================================
# SISTEMA 1: ÁRVORE DE ASCENSÃO (CLASSE)
# ================================================

def get_player_evolution_status(pdata: dict) -> Dict[str, Any]:
    """Retorna o estado da evolução (Árvore) baseada no nível/classe."""
    current_class = (pdata.get("class") or "").lower()
    current_level = int(pdata.get("level") or 1)
    
    evo_options_list = evo_data.get_evolution_options(current_class, current_level)
    evo_opt = evo_options_list[0] if evo_options_list else None
    
    if not evo_opt:
        return {"status": "max_tier", "message": "Você atingiu o auge da sua classe."}

    min_lvl = evo_opt.get("min_level", 999)
    if current_level < min_lvl:
        return {"status": "locked", "message": f"Requer Nível {min_lvl}.", "option": evo_opt}

    ascension_path = evo_opt.get("ascension_path", [])
    
    # Fallback para sistema legado (required_items sem árvore)
    if not ascension_path:
        req_items = evo_opt.get("required_items", {})
        if _inventory_has(pdata, req_items):
            return {"status": "trial_ready", "option": evo_opt, "all_nodes_complete": True}
        return {"status": "path_available", "path_nodes": [], "option": evo_opt, "all_nodes_complete": False}

    player_progress = pdata.get("evolution_progress", {})
    path_nodes = []
    all_nodes_complete = True
    next_node_unlocked = True

    for node in ascension_path:
        nid = node["id"]
        is_complete = player_progress.get(nid, False)
        status = "locked"
        
        if is_complete:
            status = "complete"
        elif next_node_unlocked:
            status = "available"
            all_nodes_complete = False
            next_node_unlocked = False
        else:
            all_nodes_complete = False
            
        path_nodes.append({"id": nid, "desc": node["desc"], "cost": node.get("cost", {}), "status": status})

    return {
        "status": "path_available",
        "option": evo_opt,
        "path_nodes": path_nodes,
        "all_nodes_complete": all_nodes_complete
    }

async def attempt_ascension_node(user_id: int, node_id: str) -> Tuple[bool, str]:
    """Tenta completar um nó da árvore."""
    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return False, "Jogador não encontrado."
        
    status = get_player_evolution_status(pdata)
    node_to_complete = next((n for n in status.get("path_nodes", []) if n["id"] == node_id and n["status"] == "available"), None)
    
    if not node_to_complete: return False, "Tarefa indisponível."
        
    cost = node_to_complete.get("cost", {})
    req_items = {k:v for k,v in cost.items() if k!="gold"}
    req_gold = cost.get("gold", 0)
    
    if pdata.get("gold", 0) < req_gold: return False, f"Falta Ouro ({req_gold})."
    if not _inventory_has(pdata, req_items): return False, "Faltam itens."

    _consume_gold(pdata, req_gold)
    _consume_items(pdata, req_items)
    
    if "evolution_progress" not in pdata: pdata["evolution_progress"] = {}
    pdata["evolution_progress"][node_id] = True
    
    await player_manager.save_player_data(user_id, pdata)
    return True, "Tarefa concluída!"

async def start_evolution_trial(user_id: int, target_class: str) -> dict:
    """Prepara a batalha de provação."""
    pdata = await player_manager.get_player_data(user_id)
    status = get_player_evolution_status(pdata)
    
    if status.get("option", {}).get("to") != target_class:
        return {'success': False, 'message': "Evolução incorreta."}
        
    if not status.get("all_nodes_complete", False):
        return {'success': False, 'message': "Complete a árvore primeiro."}

    # Fallback para consumir itens do sistema legado se não houve árvore
    if "ascension_path" not in status.get("option", {}):
        req_items = status["option"].get("required_items", {})
        if not _consume_items(pdata, req_items):
            return {'success': False, 'message': "Erro ao consumir itens."}
        await player_manager.save_player_data(user_id, pdata)

    return {'success': True, 'trial_monster_id': status["option"].get('trial_monster_id')}

async def finalize_evolution(user_id: int, target_class: str) -> Tuple[bool, str]:
    """Finaliza a evolução após vitória."""
    pdata = await player_manager.get_player_data(user_id)
    opt = evo_data.find_evolution_by_target(target_class)
    
    if not pdata or not opt: return False, "Dados inválidos."
    
    pdata["class"] = target_class
    pdata["evolution_progress"] = {} # Reseta árvore para a próxima
    
    if "skills" not in pdata or not isinstance(pdata["skills"], dict):
        pdata["skills"] = {}
    
    count = 0
    for sid in opt.get("unlocks_skills", []):
        if sid and sid not in pdata["skills"]:
            # CORREÇÃO: Inicializa com level=1 (novo sistema), não progress=0
            pdata["skills"][sid] = {"rarity": "comum", "level": 1}
            count += 1
            
    await player_manager.save_player_data(user_id, pdata)
    return True, f"Você evoluiu para {target_class.title()} e aprendeu {count} skills!"

# ================================================
# SISTEMA 2: UPGRADE DE SKILLS (OURO + TOMOS)
# ================================================

def _get_skill_upgrade_cost(current_level: int, rarity: str, skill_id: str) -> Dict[str, Any]:
    """Calcula custo: Ouro + Tomo da Skill."""
    base_gold = 150
    rarity_mult = {"comum": 1, "incomum": 2, "rara": 5, "epica": 10, "lendaria": 20}
    mult = rarity_mult.get(rarity.lower(), 1)
    
    gold_cost = int(base_gold * (current_level if current_level > 0 else 1) * mult)
    
    # O item necessário é sempre "tomo_{skill_id}"
    skill_book_item_id = f"tomo_{skill_id}"
    
    return {"gold": gold_cost, "items": {skill_book_item_id: 1}}

async def process_skill_upgrade(user_id: int, skill_id: str) -> Tuple[bool, str, dict]:
    """Realiza o upgrade da skill se tiver recursos."""
    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return False, "Erro player.", {}
    
    skill_entry = pdata.get("skills", {}).get(skill_id)
    if not skill_entry: return False, "Skill não aprendida.", {}
    
    # Garante leitura correta do nível
    lvl = skill_entry.get("level", 1)
    if lvl >= 10: return False, "Nível máximo!", {}
    
    costs = _get_skill_upgrade_cost(lvl, skill_entry.get("rarity", "comum"), skill_id)
    req_gold = costs["gold"]
    req_items = costs["items"]
    
    if pdata.get("gold", 0) < req_gold: return False, f"Ouro insuficiente ({req_gold}).", {}
    
    if not _inventory_has(pdata, req_items):
        tomo_id = list(req_items.keys())[0]
        # Tenta pegar nome bonito
        try:
            from modules.game_data.items import get_display_name
            name = get_display_name(tomo_id)
        except:
            name = tomo_id.replace("_", " ").title()
        return False, f"Requer: 1x {name}", {}
        
    _consume_gold(pdata, req_gold)
    _consume_items(pdata, req_items)
    
    # Aplica o nível
    new_lvl = lvl + 1
    pdata["skills"][skill_id]["level"] = new_lvl
    
    await player_manager.save_player_data(user_id, pdata)
    
    return True, f"Skill evoluída para Nível {new_lvl}!", pdata["skills"][skill_id]