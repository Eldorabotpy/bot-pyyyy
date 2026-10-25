# modules/class_evolution_service.py
# (MIGRAÇÃO: ObjectId)

from __future__ import annotations

from typing import Dict, Tuple, Any, Union

from bson import ObjectId

from modules import player_manager
from modules.game_data import class_evolution as evo_data
from modules.game_data.skills import SKILL_DATA
from modules.skill_progression import skill_is_available_to_class

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
    current_class = str(pdata.get("class") or pdata.get("class_key") or pdata.get("classe") or "").lower()
    current_level = int(pdata.get("level") or 1)

    evo_options_list = evo_data.get_evolution_options(current_class, current_level)
    evo_opt = evo_options_list[0] if evo_options_list else None

    if not evo_opt:
        return {"status": "max_tier", "message": "Você atingiu o auge da sua classe."}

    min_lvl = int(evo_opt.get("min_level", 999))
    if current_level < min_lvl:
        return {
            "status": "locked",
            "message": f"Requer Nível {min_lvl}.",
            "level": current_level,
            "required_level": min_lvl,
            "option": evo_opt,
            "path_nodes": [],
            "all_nodes_complete": False,
            "trial": pdata.get("evolution_trial") or None,
        }

    ascension_path = evo_opt.get("ascension_path", [])

    # Fallback legado: evolução sem árvore
    if not ascension_path:
        req_items = evo_opt.get("required_items", {}) or {}
        if _inventory_has(pdata, req_items):
            return {
                "status": "trial_ready", "option": evo_opt,
                "all_nodes_complete": True, "path_nodes": [],
                "trial": pdata.get("evolution_trial") or None,
                "level": current_level, "required_level": min_lvl,
            }
        return {
            "status": "path_available",
            "path_nodes": [],
            "option": evo_opt,
            "all_nodes_complete": False,
            "trial": pdata.get("evolution_trial") or None,
            "level": current_level, "required_level": min_lvl,
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
        "all_nodes_complete": all_nodes_complete,
        "trial": pdata.get("evolution_trial") or None,
        "level": current_level, "required_level": min_lvl,
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

    target_class = str(target_class or "").strip().lower()
    status = get_player_evolution_status(pdata)

    if (status.get("option", {}) or {}).get("to") != target_class:
        return {"success": False, "message": "Evolução incorreta."}

    if not status.get("all_nodes_complete", False):
        return {"success": False, "message": "Complete a árvore primeiro."}

    opt = status.get("option", {}) or {}
    if not opt.get("trial_monster_id"):
        return {"success": False, "message": "Esta evolução ainda não possui uma prova configurada."}
    current_trial = pdata.get("evolution_trial") or {}
    if (
        isinstance(current_trial, dict)
        and current_trial.get("target_class") == target_class
        and current_trial.get("status") == "won"
    ):
        return {"success": True, "trial_monster_id": opt["trial_monster_id"], "already_won": True}

    if "ascension_path" not in opt:
        req_items = opt.get("required_items", {}) or {}
        if not _consume_items(pdata, req_items):
            return {"success": False, "message": "Erro ao consumir itens."}

    pdata["evolution_trial"] = {
        "target_class": target_class,
        "monster_id": opt["trial_monster_id"],
        "status": "started",
        "path_complete": True,
    }
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

    status = get_player_evolution_status(pdata)
    trial = pdata.get("evolution_trial") or {}
    target_class = str(target_class or "").strip().lower()
    if (status.get("option", {}) or {}).get("to") != target_class:
        return False, "Essa não é a próxima evolução da sua classe."
    if int(pdata.get("level") or 1) < int(opt.get("min_level") or 999):
        return False, f"Você precisa do nível {opt.get('min_level')} para evoluir."
    if not isinstance(trial, dict) or trial.get("target_class") != target_class:
        return False, "Inicie a prova de evolução antes de concluir."
    if not trial.get("path_complete") or trial.get("status") != "won":
        return False, "Derrote o guardião da evolução para concluir."
    if (status.get("all_nodes_complete") is not True) and opt.get("ascension_path"):
        return False, "Complete todas as etapas da evolução primeiro."

    pdata["class"] = target_class
    pdata["class_key"] = target_class
    pdata["evolution_progress"] = {}

    for field in ("skills", "skills_desbloqueadas", "database_skills"):
        if not isinstance(pdata.get(field), dict):
            pdata[field] = {}

    learned = 0
    for sid in (opt.get("unlocks_skills", []) or []):
        if sid and sid not in pdata["skills"]:
            learned_skill = {"unlocked": True, "rarity": "comum", "level": 1, "progress": 0}
            pdata["skills"][sid] = learned_skill.copy()
            pdata["skills_desbloqueadas"][sid] = learned_skill.copy()
            pdata["database_skills"][sid] = learned_skill.copy()
            learned += 1
        elif sid:
            for field in ("skills_desbloqueadas", "database_skills"):
                pdata[field].setdefault(sid, dict(pdata["skills"][sid]))

    pdata["evolution_trial"] = None

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

    if skill_id not in SKILL_DATA:
        return False, "Habilidade não encontrada.", {}

    skill_entry = (pdata.get("skills", {}) or {}).get(skill_id)
    if not skill_entry:
        return False, "Skill não aprendida.", {}
    if not isinstance(skill_entry, dict):
        skill_entry = {"level": 1, "rarity": "comum"}
        pdata["skills"][skill_id] = skill_entry

    player_class = str(pdata.get("class") or pdata.get("class_key") or pdata.get("classe") or "")
    if not skill_is_available_to_class(player_class, skill_id):
        return False, "Essa habilidade ainda não foi liberada para sua classe.", {}

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

    try:
        from modules.game_data.items import ITEMS_DATA
        tome = ITEMS_DATA.get(f"tomo_{skill_id}") or {}
        if tome.get("type") != "skill_book" or tome.get("skill_tome_purpose") != "upgrade":
            return False, "O tomo desta habilidade não está configurado para aprimoramento.", {}
    except Exception:
        return False, "Não foi possível validar o tomo de aprimoramento.", {}

    _consume_gold(pdata, req_gold)
    _consume_items(pdata, req_items)

    new_lvl = lvl + 1
    pdata.setdefault("skills", {})
    pdata["skills"].setdefault(skill_id, {})
    pdata["skills"][skill_id]["level"] = new_lvl
    for field in ("skills_desbloqueadas", "database_skills"):
        if not isinstance(pdata.get(field), dict):
            pdata[field] = {}
        pdata[field][skill_id] = dict(pdata["skills"][skill_id])

    await player_manager.save_player_data(oid, pdata)
    return True, f"Skill evoluída para Nível {new_lvl}!", pdata["skills"][skill_id]


def record_evolution_trial_victory(player_data: dict, mob: dict, player_id: str) -> bool:
    """Mark a trial complete only after its private, owner-checked mob is defeated."""
    trial = player_data.get("evolution_trial") or {}
    if not isinstance(trial, dict) or trial.get("status") != "started":
        return False
    if not mob or not mob.get("evolution_trial"):
        return False
    if str(mob.get("evolution_trial_owner_id") or "") != str(player_id or ""):
        return False
    if str(mob.get("monster_id") or "") != str(trial.get("monster_id") or ""):
        return False
    trial["status"] = "won"
    player_data["evolution_trial"] = trial
    return True
