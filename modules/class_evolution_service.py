# modules/class_evolution_service.py (VERSÃO CORRIGIDA PARA LISTA DE SKILLS)

from __future__ import annotations
from typing import Dict, Tuple, Optional, List
from modules.game_data.class_evolution import EVOLUTIONS
from modules import player_manager

# (As funções de acesso a dados _inventory_has e _consume_items estão corretas)
# ================================================
def _inventory_has(pdata: Dict, required_items: Dict[str, int]) -> bool:
    """Verifica se o jogador tem os itens, usando o player_manager."""
    for item_id, qty in required_items.items():
        if not player_manager.has_item(pdata, item_id, qty):
            return False
    return True

def _consume_items(pdata: Dict, required_items: Dict[str, int]) -> None:
    """Consome os itens do inventário, usando o player_manager."""
    for item_id, qty in required_items.items():
        player_manager.remove_item_from_inventory(pdata, item_id, qty)
# ================================================


# <<< MUDANÇA (INÍCIO): Função _find_evolution_option corrigida >>>
def _find_evolution_option(current_class: str, target_class: str) -> Optional[Dict]:
    """Encontra a definição de uma evolução específica, procurando em T2 e T3."""
    curr = (current_class or "").lower()
    
    # 1. Tenta encontrar como uma T2 (ex: guerreiro -> cavaleiro)
    # Procura na classe base 'current_class'
    base_data = EVOLUTIONS.get(curr)
    if base_data:
        for opt in base_data.get("tier2", []):
            if opt.get("to") == target_class:
                return {"tier": "tier2", **opt}

    # 2. Se não, procura em TODAS as T3 (ex: cavaleiro -> templario)
    # Itera por todas as classes base (guerreiro, mago, etc.)
    for base_class_key, base_class_data in EVOLUTIONS.items():
        # Procura nas T3 dessa classe
        for opt in base_class_data.get("tier3", []):
            if opt.get("to") == target_class:
                # Se encontrou, verifica se a classe atual é permitida
                req_from = opt.get("from_any_of")
                if isinstance(req_from, list) and curr in req_from:
                    return {"tier": "tier3", **opt}
    
    return None # Não encontrou
# <<< MUDANÇA (FIM): Função _find_evolution_option corrigida >>>


def can_evolve_to(pdata: dict, target_class: str) -> Tuple[bool, str, Optional[Dict]]:
    """Checa se o jogador pode evoluir para 'target_class' (versão síncrona)."""
    if not pdata:
        return False, "Jogador não encontrado.", None
        
    current_class = (pdata.get("class") or "").lower()
    level = int(pdata.get("level") or 1)

    opt = _find_evolution_option(current_class, target_class) # Síncrono
    if not opt:
        return False, "Evolução inválida para sua classe atual.", None

    # (Esta verificação 'from_any_of' é redundante pois _find_evolution_option já a faz, mas mantemos por segurança)
    req_from = opt.get("from_any_of")
    if isinstance(req_from, list) and current_class not in req_from:
        return False, "Essa evolução requer uma especialização anterior específica.", opt

    min_lvl = int(opt.get("min_level") or 0)
    if level < min_lvl:
        return False, f"Requer nível {min_lvl}.", opt

    req_items = opt.get("required_items") or {}
    if not _inventory_has(pdata, req_items): # Síncrono
        return False, "Faltam itens necessários.", opt

    return True, "Requisitos atendidos.", opt

async def start_evolution_trial(user_id: int, target_class: str) -> dict:
    """
    Verifica os requisitos, consome os itens e retorna as informações
    para o handler iniciar a Batalha de Provação.
    """
    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        return {'success': False, 'message': "Erro: Jogador não encontrado."}
        
    ok, msg, opt = can_evolve_to(pdata, target_class)
    
    if not ok or not opt:
        return {'success': False, 'message': msg}

    req_items = opt.get("required_items") or {}
    _consume_items(pdata, req_items)
    
    await player_manager.save_player_data(user_id, pdata)
    
    return {
        'success': True,
        'message': 'Você entregou os materiais e está pronto para a sua provação!',
        'trial_monster_id': opt.get('trial_monster_id')
    }


# <<< MUDANÇA (INÍCIO): Função finalize_evolution corrigida >>>
async def finalize_evolution(user_id: int, target_class: str) -> Tuple[bool, str]:
    """
    Esta função é chamada APÓS o jogador vencer a batalha de provação.
    Ela efetivamente muda a classe e adiciona as novas habilidades (plural).
    """
    pdata = await player_manager.get_player_data(user_id)
    # (Usa a função corrigida _find_evolution_option)
    opt = _find_evolution_option((pdata.get("class") or "").lower(), target_class)
    
    if not pdata or not opt:
        return False, "Erro ao finalizar a evolução. Dados não encontrados."

    # 1. Altera a classe do jogador
    pdata["class"] = target_class
    
    # 2. Adiciona as novas habilidades (agora uma lista)
    if "skills" not in pdata or not isinstance(pdata["skills"], list):
        pdata["skills"] = []

    # Pega a nova lista (plural)
    new_skill_ids = opt.get("unlocks_skills", [])
    
    # Fallback para a chave antiga (singular), caso tenhamos esquecido de atualizar
    if not new_skill_ids and opt.get("unlocks_skill"):
        new_skill_ids = [opt.get("unlocks_skill")]

    skills_adicionadas = 0
    if new_skill_ids:
        for skill_id in new_skill_ids:
            if skill_id and skill_id not in pdata["skills"]:
                pdata["skills"].append(skill_id)
                skills_adicionadas += 1
                
    await player_manager.save_player_data(user_id, pdata)
    
    msg_final = f"Parabéns! Você provou o seu valor e evoluiu para {target_class.title()}!"
    if skills_adicionadas > 0:
        s = "s" if skills_adicionadas > 1 else ""
        msg_final += f"\nVocê aprendeu {skills_adicionadas} nova{s} habilidade{s}!"
        
    return True, msg_final
# <<< MUDANÇA (FIM): Função finalize_evolution corrigida >>>