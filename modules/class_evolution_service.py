# modules/class_evolution_service.py
from __future__ import annotations
from typing import Dict, Tuple, Optional

from modules.game_data.class_evolution import EVOLUTIONS

# === TODO: adapte estes helpers para o seu projeto ===
def _get_player(user_id: int) -> Dict:
    """
    Carrega o player dict. Troque para suas funções reais.
    """
    from modules.player_manager import load_player_data  # se existir; senão adapte
    return load_player_data(user_id)

def _save_player(user_id: int, pdata: Dict) -> None:
    from modules.player_manager import save_player_data
    save_player_data(user_id, pdata)

def _inventory_has_and_consume(pdata: Dict, required_items: Dict[str, int]) -> bool:
    """
    Verifica e consome itens do inventário do player.
    Adapte para suas APIs de inventário (ex.: modules.inventory).
    """
    inv = pdata.get("inventory") or {}
    # checar
    for item_id, qty in required_items.items():
        if inv.get(item_id, 0) < qty:
            return False
    # consumir
    for item_id, qty in required_items.items():
        inv[item_id] = inv.get(item_id, 0) - qty
        if inv[item_id] <= 0:
            inv.pop(item_id, None)
    pdata["inventory"] = inv
    return True
# ================================================


def _find_evolution_option(current_class: str, target_class: str) -> Optional[Dict]:
    curr = (current_class or "").lower()
    data = EVOLUTIONS.get(curr)
    if not data:
        return None
    for tier in ("tier2", "tier3"):
        for opt in data.get(tier, []):
            if opt.get("to") == target_class:
                return {"tier": tier, **opt}
    return None


def can_evolve_to(user_id: int, target_class: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    Checa se o jogador pode evoluir para 'target_class'.
    Retorna (ok, msg, opt_dict).
    """
    pdata = _get_player(user_id)
    current_class = (pdata.get("class") or "").lower()
    level = int(pdata.get("level") or 1)

    opt = _find_evolution_option(current_class, target_class)
    if not opt:
        return False, "Evolução inválida para sua classe atual.", None

    # se exigir 'from_any_of', precisa já ser uma dessas classes
    req_from = opt.get("from_any_of")
    if isinstance(req_from, list) and current_class not in req_from:
        return False, "Essa evolução requer que você tenha feito uma especialização anterior específica.", opt

    min_lvl = int(opt.get("min_level") or 0)
    if level < min_lvl:
        return False, f"Requer nível {min_lvl}.", opt

    # checagem de itens (sem consumir aqui)
    inv = (pdata.get("inventory") or {})
    req = (opt.get("required_items") or {})
    for item_id, qty in req.items():
        if inv.get(item_id, 0) < qty:
            return False, f"Faltam itens: {item_id} x{qty}.", opt

    return True, "Requisitos atendidos.", opt


def apply_evolution(user_id: int, target_class: str) -> Tuple[bool, str]:
    """
    Consome itens e altera a classe do jogador.
    """
    pdata = _get_player(user_id)
    current_class = (pdata.get("class") or "").lower()

    ok, msg, opt = can_evolve_to(user_id, target_class)
    if not ok or not opt:
        return False, msg

    # consumir itens
    req = opt.get("required_items") or {}
    if not _inventory_has_and_consume(pdata, req):
        return False, "Itens insuficientes no momento da evolução."

    # aplicar classe
    pdata["class"] = target_class
    # (opcional) marcar tier/caminho percorrido
    evo_path = pdata.get("evolution_path") or []
    evo_path.append({"from": current_class, "to": target_class})
    pdata["evolution_path"] = evo_path

    _save_player(user_id, pdata)
    return True, f"Parabéns! Você evoluiu para {target_class}."
