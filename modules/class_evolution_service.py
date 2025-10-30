# modules/class_evolution_service.py (VERSÃO ATUALIZADA PARA O "PLANO MESTRE")
from __future__ import annotations
from typing import Dict, Tuple, Optional
from modules.game_data.class_evolution import EVOLUTIONS
from modules import player_manager

# ================================================
# Funções de acesso a dados (CORRIGIDAS)
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

def _find_evolution_option(current_class: str, target_class: str) -> Optional[Dict]:
    """Encontra a definição de uma evolução específica."""
    curr = (current_class or "").lower()
    data = EVOLUTIONS.get(curr)
    if not data:
        return None
    for tier in ("tier2", "tier3"):
        for opt in data.get(tier, []):
            if opt.get("to") == target_class:
                return {"tier": tier, **opt}
    return None


# Não precisa de 'async def' pois agora é síncrona
def can_evolve_to(pdata: dict, target_class: str) -> Tuple[bool, str, Optional[Dict]]:
    """Checa se o jogador pode evoluir para 'target_class' (versão síncrona)."""
    # pdata já foi carregado pela função que chamou esta
    if not pdata:
        return False, "Jogador não encontrado.", None
        
    current_class = (pdata.get("class") or "").lower()
    level = int(pdata.get("level") or 1)

    opt = _find_evolution_option(current_class, target_class) # Síncrono
    if not opt:
        return False, "Evolução inválida para sua classe atual.", None

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

# --- FUNÇÃO PRINCIPAL MODIFICADA ---
async def start_evolution_trial(user_id: int, target_class: str) -> dict:
    """
    Verifica os requisitos, consome os itens e retorna as informações
    para o handler iniciar a Batalha de Provação.
    """
    # 1. Carrega os dados (PRIMEIRA E ÚNICA VEZ)
    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        return {'success': False, 'message': "Erro: Jogador não encontrado."}
        
    # 2. Verifica os requisitos (CHAMADA SÍNCRONA CORRIGIDA)
    ok, msg, opt = can_evolve_to(pdata, target_class) # Remove 'await'
    
    if not ok or not opt:
        return {'success': False, 'message': msg}

    # 3. Consome os itens necessários (função síncrona)
    req_items = opt.get("required_items") or {}
    _consume_items(pdata, req_items)
    
    # 4. Salva o consumo de itens
    await player_manager.save_player_data(user_id, pdata) # Await já estava correto
    
    # 5. Retorna as instruções para o handler
    return {
        'success': True,
        'message': 'Você entregou os materiais e está pronto para a sua provação!',
        'trial_monster_id': opt.get('trial_monster_id')
    }

# --- NOVA FUNÇÃO PARA FINALIZAR A EVOLUÇÃO ---
async def finalize_evolution(user_id: int, target_class: str) -> Tuple[bool, str]:
    """
    Esta função é chamada APÓS o jogador vencer a batalha de provação.
    Ela efetivamente muda a classe e adiciona a nova habilidade.
    """
    pdata = await player_manager.get_player_data(user_id)
    opt = _find_evolution_option((pdata.get("class") or "").lower(), target_class)
    
    if not pdata or not opt:
        return False, "Erro ao finalizar a evolução. Dados não encontrados."

    # 1. Altera a classe do jogador
    pdata["class"] = target_class
    
    # 2. Adiciona a nova habilidade (se existir)
    new_skill_id = opt.get("unlocks_skill")
    if new_skill_id:
        if "skills" not in pdata:
            pdata["skills"] = []
        if new_skill_id not in pdata["skills"]:
            pdata["skills"].append(new_skill_id)
            
    await player_manager.save_player_data(user_id, pdata)
    return True, f"Parabéns! Você provou o seu valor e evoluiu para {target_class.title()}!"