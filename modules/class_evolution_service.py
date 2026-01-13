# modules/class_evolution_service.py
# (MIGRAÇÃO: ObjectId)

from __future__ import annotations

from typing import Dict, Tuple, Any, Union

from bson import ObjectId

from modules import player_manager
from modules.game_data import class_evolution as evo_data

PlayerId = Union[ObjectId, str]


def _normalize_player_id(user_id: PlayerId) -> ObjectId:
    """
    Normaliza para ObjectId.
    Aceita ObjectId ou string válida de ObjectId. Caso inválido, levanta ValueError.
    """
    if isinstance(user_id, ObjectId):
        return user_id
    if isinstance(user_id, str) and ObjectId.is_valid(user_id.strip()):
        return ObjectId(user_id.strip())
    raise ValueError("user_id inválido (esperado ObjectId ou string de ObjectId).")


def _inventory_has(pdata: Dict, required_items: Dict[str, int]) -> bool:
    for item_id, qty in required_items.items():
        if not player_manager.has_item(pdata, item_id, qty):
            return False
    return True


def _consume_items(pdata: Dict, required_items: Dict[str, int]) -> bool:
    if not _inventory_has(pdata, required_items):
        return False
    for item_id, qty in required_items.items():
        player_manager.remove_item_from_inventory(pdata, item_id, qty)
    return True


def _consume_gold(pdata: Dict, amount: int) -> bool:
    current_gold = int(pdata.get("gold", 0))
    if current_gold < amount:
        return False
    pdata["gold"] = current_gold - amount
    return True


def get_player_evolution_status(pdata: dict) -> Dict[str, Any]:
    current_class = (pdata.get("class") or "").lower()
    current_level = int(pdata.get("level") or 1)

    evo_options_list = evo_data.get_evolution_options(current_class, current_level)
    evo_opt = evo_options_list[0] if evo_options_list else None

    if not evo_opt:
        return {"status": "max_tier", "message": "Você atingiu o auge da sua classe."}

    min_lvl = int(evo_opt.get("min_level", 999))
    if current_level < min_lvl:
        return {"status": "locked", "message": f"Requer Nível {min_lvl}.", "option": evo_opt}

    ascension_path = evo_opt.get("ascension_path", [])

    # Fallback legado: evolução sem árvore
    if not ascension_path:
        req_items = evo_opt.get("required_items", {}) or {}
        if _inventory_has(pdata, req_items):
            return {"status": "trial_ready", "option": evo_opt, "all_nodes_complete": True}
        return {
            "status": "path_available",
            "path_nodes": [],
            "option": evo_opt,
            "all_nodes_complete": False
        }

    player_progress = pdata.get("evolution_progress", {}) or {}
    path_nodes = []
    all_nodes_complete = True
    next_node_unlocked = True

    for node in ascension_path:
        nid = node["id"]
        is_complete = bool(player_progress.get(nid, False))
        status = "locked"

        if is_complete:
            status = "complete"
        elif next_node_unlocked:
            status = "available"
            all_nodes_complete = False
            next_node_unlocked = False
        else:
            all_nodes_complete = False

        path_nodes.append({
            "id": nid,
            "desc": node.get("desc", ""),
            "cost": node.get("cost", {}) or {},
            "status": status
        })

    return {
        "status": "path_available",
        "option": evo_opt,
        "path_nodes": path_nodes,
        "all_nodes_complete": all_nodes_complete
    }


async def attempt_ascension_node(user_id: PlayerId, node_id: str) -> Tuple[bool, str]:
    try:
        oid = _normalize_player_id(user_id)
    except ValueError:
        return False, "ID do jogador inválido."

    pdata = await player_manager.get_player_data(oid)
    if not pdata:
        return False, "Jogador não encontrado."

    status = get_player_evolution_status(pdata)
    node_to_complete = next(
        (n for n in status.get("path_nodes", []) if n["id"] == node_id and n["status"] == "available"),
        None
    )
    if not node_to_complete:
        return False, "Tarefa indisponível."

    cost = node_to_complete.get("cost", {}) or {}
    req_items = {k: v for k, v in cost.items() if k != "gold"}
    req_gold = int(cost.get("gold", 0))

    if int(pdata.get("gold", 0)) < req_gold:
        return False, f"Falta Ouro ({req_gold})."
    if not _inventory_has(pdata, req_items):
        return False, "Faltam itens."

    _consume_gold(pdata, req_gold)
    _consume_items(pdata, req_items)

    pdata.setdefault("evolution_progress", {})
    pdata["evolution_progress"][node_id] = True

    await player_manager.save_player_data(oid, pdata)
    return True, "Tarefa concluída!"


async def start_evolution_trial(user_id: PlayerId, target_class: str) -> dict:
    try:
        oid = _normalize_player_id(user_id)
    except ValueError:
        return {"success": False, "message": "ID do jogador inválido."}

    pdata = await player_manager.get_player_data(oid)
    if not pdata:
        return {"success": False, "message": "Jogador não encontrado."}

    status = get_player_evolution_status(pdata)

    if (status.get("option", {}) or {}).get("to") != target_class:
        return {"success": False, "message": "Evolução incorreta."}

    if not status.get("all_nodes_complete", False):
        return {"success": False, "message": "Complete a árvore primeiro."}

    opt = status.get("option", {}) or {}
    if "ascension_path" not in opt:
        req_items = opt.get("required_items", {}) or {}
        if not _consume_items(pdata, req_items):
            return {"success": False, "message": "Erro ao consumir itens."}
        await player_manager.save_player_data(oid, pdata)

    return {"success": True, "trial_monster_id": opt.get("trial_monster_id")}


async def finalize_evolution(user_id: PlayerId, target_class: str) -> Tuple[bool, str]:
    try:
        oid = _normalize_player_id(user_id)
    except ValueError:
        return False, "ID do jogador inválido."

    pdata = await player_manager.get_player_data(oid)
    opt = evo_data.find_evolution_by_target(target_class)

    if not pdata or not opt:
        return False, "Dados inválidos."

    pdata["class"] = target_class
    pdata["evolution_progress"] = {}

    if "skills" not in pdata or not isinstance(pdata["skills"], dict):
        pdata["skills"] = {}

    learned = 0
    for sid in (opt.get("unlocks_skills", []) or []):
        if sid and sid not in pdata["skills"]:
            pdata["skills"][sid] = {"rarity": "comum", "level": 1}
            learned += 1

    await player_manager.save_player_data(oid, pdata)
    return True, f"Você evoluiu para {target_class.title()} e aprendeu {learned} skills!"


def _get_skill_upgrade_cost(current_level: int, rarity: str, skill_id: str) -> Dict[str, Any]:
    base_gold = 150
    rarity_mult = {"comum": 1, "incomum": 2, "rara": 5, "epica": 10, "lendaria": 20}
    mult = rarity_mult.get((rarity or "comum").lower(), 1)

    lvl = current_level if current_level > 0 else 1
    gold_cost = int(base_gold * lvl * mult)

    skill_book_item_id = f"tomo_{skill_id}"
    return {"gold": gold_cost, "items": {skill_book_item_id: 1}}


async def process_skill_upgrade(user_id: PlayerId, skill_id: str) -> Tuple[bool, str, dict]:
    try:
        oid = _normalize_player_id(user_id)
    except ValueError:
        return False, "ID do jogador inválido.", {}

    pdata = await player_manager.get_player_data(oid)
    if not pdata:
        return False, "Erro player.", {}

    skill_entry = (pdata.get("skills", {}) or {}).get(skill_id)
    if not skill_entry:
        return False, "Skill não aprendida.", {}

    lvl = int(skill_entry.get("level", 1))
    if lvl >= 10:
        return False, "Nível máximo!", {}

    costs = _get_skill_upgrade_cost(lvl, skill_entry.get("rarity", "comum"), skill_id)
    req_gold = int(costs["gold"])
    req_items = costs["items"]

    if int(pdata.get("gold", 0)) < req_gold:
        return False, f"Ouro insuficiente ({req_gold}).", {}

    if not _inventory_has(pdata, req_items):
        tomo_id = list(req_items.keys())[0]
        try:
            from modules.game_data.items import get_display_name
            name = get_display_name(tomo_id)
        except Exception:
            name = tomo_id.replace("_", " ").title()
        return False, f"Requer: 1x {name}", {}

    _consume_gold(pdata, req_gold)
    _consume_items(pdata, req_items)

    new_lvl = lvl + 1
    pdata.setdefault("skills", {})
    pdata["skills"].setdefault(skill_id, {})
    pdata["skills"][skill_id]["level"] = new_lvl

    await player_manager.save_player_data(oid, pdata)
    return True, f"Skill evoluída para Nível {new_lvl}!", pdata["skills"][skill_id]
