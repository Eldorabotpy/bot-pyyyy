# modules/class_evolution_service.py
# (VERSÃO NOVA - LÊ O SISTEMA "CAMINHO DA ASCENSÃO")

from __future__ import annotations
from typing import Dict, Tuple, Optional, List, Any
from modules import player_manager
from modules.game_data import class_evolution as evo_data # Importa o ficheiro de DADOS

# ================================================
# Funções Auxiliares (Não mudaram)
# ================================================
def _inventory_has(pdata: Dict, required_items: Dict[str, int]) -> bool:
    """Verifica se o jogador tem os itens."""
    for item_id, qty in required_items.items():
        if not player_manager.has_item(pdata, item_id, qty):
            return False
    return True

def _consume_items(pdata: Dict, required_items: Dict[str, int]) -> bool:
    """Consome os itens do inventário."""
    # (Verifica de novo por segurança, caso seja chamado diretamente)
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
# NOVAS FUNÇÕES DE LÓGICA
# ================================================

# Em modules/class_evolution_service.py

def get_player_evolution_status(pdata: dict) -> Dict[str, Any]:
    """
    Verifica o estado da próxima evolução do jogador, incluindo o progresso
    no "Caminho da Ascensão" (a árvore).
    """
    current_class = (pdata.get("class") or "").lower()
    current_level = int(pdata.get("level") or 1)
    
    # --- CORREÇÃO AQUI ---
    # 1. Passamos o current_level que a função exige.
    # 2. Pegamos o primeiro item da lista (pois a função retorna uma lista).
    evo_options_list = evo_data.get_evolution_options(current_class, current_level)
    evo_opt = evo_options_list[0] if evo_options_list else None
    
    if not evo_opt:
        return {"status": "max_tier", "message": "Você atingiu o auge da sua classe."}

    min_lvl = evo_opt.get("min_level", 999)
    
    # 2. Verifica se o nível mínimo foi atingido
    if current_level < min_lvl:
        return {
            "status": "locked", 
            "message": f"Requer Nível {min_lvl} para iniciar este caminho.",
            "option": evo_opt
        }

    # 3. Processa a "Árvore" (Ascension Path)
    ascension_path = evo_opt.get("ascension_path", [])
    if not ascension_path:
        # (Fallback para 'required_items' se a árvore não foi definida)
        return _check_legacy_evolution(pdata, evo_opt)

    player_progress = pdata.get("evolution_progress", {})
    path_nodes = [] # A lista de tarefas para mostrar ao jogador
    all_nodes_complete = True
    next_node_unlocked = True # O primeiro nó está sempre desbloqueado

    for node in ascension_path:
        node_id = node["id"]
        is_complete = player_progress.get(node_id, False)
        
        node_status = "locked" # (Status padrão: 🔒)
        
        if is_complete:
            node_status = "complete" # (Status: ✅)
        elif next_node_unlocked:
            # Este é o próximo nó disponível
            node_status = "available" # (Status: 🔘)
            all_nodes_complete = False
            next_node_unlocked = False # Bloqueia os próximos até este ser feito
        else:
            # Este é um nó futuro, mas não o próximo
            all_nodes_complete = False
            
        path_nodes.append({
            "id": node_id,
            "desc": node["desc"],
            "cost": node.get("cost", {}),
            "status": node_status
        })

    # 4. Retorna o status completo
    return {
        "status": "path_available",
        "message": f"Siga o Caminho da Ascensão para se tornar um {evo_opt['to'].title()}.",
        "option": evo_opt,
        "path_nodes": path_nodes,
        "all_nodes_complete": all_nodes_complete
    }

def _check_legacy_evolution(pdata: dict, evo_opt: dict) -> Dict[str, Any]:
    """Função de fallback para evoluções que ainda usam 'required_items'."""
    req_items = evo_opt.get("required_items", {})
    if _inventory_has(pdata, req_items):
        return {
            "status": "trial_ready", # Pronto para o teste (sistema antigo)
            "message": "Você tem os itens. Pronto para o teste!",
            "option": evo_opt,
            "all_nodes_complete": True # (Considerado completo)
        }
    else:
        return {
            "status": "path_available", # Mostra os itens em falta
            "message": "Reúna os itens necessários.",
            "option": evo_opt,
            "path_nodes": [], # Sem árvore, o handler deve mostrar 'required_items'
            "all_nodes_complete": False
        }

async def attempt_ascension_node(user_id: int, node_id: str) -> Tuple[bool, str]:
    """
    Tenta completar um "nó" (tarefa) da árvore de ascensão.
    Consome os itens/ouro se o jogador os tiver.
    """
    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        return False, "Erro: Jogador não encontrado."
        
    status = get_player_evolution_status(pdata)
    
    # Encontra o nó que o jogador está a tentar ativar
    node_to_complete = None
    if status.get("status") == "path_available":
        for node in status.get("path_nodes", []):
            if node["id"] == node_id and node["status"] == "available":
                node_to_complete = node
                break
    
    if not node_to_complete:
        return False, "Esta tarefa não está disponível ou já foi completada."
        
    # Verifica o custo (Itens e Ouro)
    cost = node_to_complete.get("cost", {})
    required_items = {k: v for k, v in cost.items() if k != "gold"}
    required_gold = cost.get("gold", 0)
    
    # 1. Verifica Ouro
    if pdata.get("gold", 0) < required_gold:
        return False, f"Ouro insuficiente. Requer {required_gold} 🪙."
    
    # 2. Verifica Itens
    if not _inventory_has(pdata, required_items):
        return False, "Itens insuficientes."

    # 3. SUCESSO! Consome tudo e salva o progresso.
    _consume_gold(pdata, required_gold)
    _consume_items(pdata, required_items)
    
    # Salva o progresso
    if "evolution_progress" not in pdata:
        pdata["evolution_progress"] = {}
    pdata["evolution_progress"][node_id] = True
    
    await player_manager.save_player_data(user_id, pdata)
    
    return True, f"Tarefa '{node_to_complete['desc']}' concluída!"


async def start_evolution_trial(user_id: int, target_class: str) -> dict:
    """
    Verifica se o Caminho da Ascensão está completo e retorna os dados
    para a Batalha de Provação.
    """
    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        return {'success': False, 'message': "Erro: Jogador não encontrado."}
        
    status = get_player_evolution_status(pdata)
    
    # Verifica se a evolução alvo é a correta
    if status.get("option", {}).get("to") != target_class:
        return {'success': False, 'message': "Esta não é a sua próxima evolução."}
        
    # Verifica se o caminho (árvore) está completo
    if not status.get("all_nodes_complete", False):
        return {'success': False, 'message': "Você deve completar todo o Caminho da Ascensão primeiro."}

    # (Lógica de 'required_items' do sistema antigo é movida para cá, como fallback)
    # Se o sistema for antigo E usa 'required_items'
    if "ascension_path" not in status.get("option", {}):
        req_items = status["option"].get("required_items", {})
        if not _consume_items(pdata, req_items):
            return {'success': False, 'message': "Erro ao consumir itens (fallback)."}
        await player_manager.save_player_data(user_id, pdata)
    
    # Sucesso!
    return {
        'success': True,
        'message': 'Você completou o Caminho e está pronto para a sua provação!',
        'trial_monster_id': status["option"].get('trial_monster_id')
    }


async def finalize_evolution(user_id: int, target_class: str) -> Tuple[bool, str]:
    """
    Esta função é chamada APÓS o jogador vencer a batalha de provação.
    Ela efetivamente muda a classe e adiciona as novas habilidades.
    """
    pdata = await player_manager.get_player_data(user_id)
    
    # Usa a nova função 'find_evolution_by_target' do ficheiro de DADOS
    opt = evo_data.find_evolution_by_target(target_class)
    
    if not pdata or not opt:
        return False, "Erro ao finalizar a evolução. Dados não encontrados."
        
    # Verifica se a classe atual é a correta para esta evolução
    current_class = (pdata.get("class") or "").lower()
    if opt.get("from") != current_class:
        return False, f"Erro de lógica: Sua classe atual ({current_class}) não pode evoluir para {target_class}."

    # 1. Altera a classe do jogador
    pdata["class"] = target_class
    
    # 2. LIMPA o progresso da árvore antiga
    # (Para que o jogador não tenha 'cav_node_1' quando for T3)
    pdata["evolution_progress"] = {}
    
    # 3. Adiciona as novas habilidades (agora um dicionário com progress)
    if "skills" not in pdata or not isinstance(pdata["skills"], dict):
        # Se a migração do core.py falhou ou é um player novo, garante que é um dict
        pdata["skills"] = {} 

    new_skill_ids = opt.get("unlocks_skills", [])
    skills_adicionadas = 0

    if new_skill_ids:
        for skill_id in new_skill_ids:
            # Verifica se a CHAVE da skill não está no dicionário
            if skill_id and skill_id not in pdata["skills"]:
                # Adiciona a skill no novo formato de dicionário (com progress)
                pdata["skills"][skill_id] = {"rarity": "comum", "progress": 0}
                skills_adicionadas += 1
                
    await player_manager.save_player_data(user_id, pdata)
    
    msg_final = f"Parabéns! Você provou o seu valor e evoluiu para {target_class.title()}!"
    if skills_adicionadas > 0:
        s = "s" if skills_adicionadas > 1 else ""
        msg_final += f"\nVocê aprendeu {skills_adicionadas} nova{s} habilidade{s}!"
        
    return True, msg_final