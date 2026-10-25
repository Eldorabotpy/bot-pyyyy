# modules/class_evolution_service.py
# (MIGRAÇÃO: ObjectId)

from __future__ import annotations

from copy import deepcopy
import unicodedata
from typing import Dict, Tuple, Any, Union

from bson import ObjectId

from modules import player_manager
from modules.game_data import class_evolution as evo_data
from modules.game_data.skills import SKILL_DATA
from modules.skill_progression import (
    SKILL_MAX_LEVEL,
    SKILL_POWER_BONUS_PER_LEVEL,
    is_evolution_skill,
    skill_is_available_to_class,
)

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


SKILL_UPGRADE_MAX_LEVEL = SKILL_MAX_LEVEL
SKILL_UPGRADE_BONUS_PER_LEVEL_PCT = int(SKILL_POWER_BONUS_PER_LEVEL * 100)
SKILL_UPGRADE_RARITY_MULTIPLIERS = {
    "comum": 1,
    "incomum": 2,
    "rara": 5,
    "epica": 10,
    "lendaria": 20,
}


def _get_skill_upgrade_cost(current_level: int, rarity: str, skill_id: str) -> Dict[str, Any]:
    base_gold = 150
    rarity_key = "".join(
        char for char in unicodedata.normalize("NFKD", str(rarity or "comum").lower())
        if not unicodedata.combining(char)
    )
    mult = SKILL_UPGRADE_RARITY_MULTIPLIERS.get(rarity_key, 1)

    lvl = max(1, int(current_level or 1))
    gold_cost = int(base_gold * lvl * mult)

    skill_book_item_id = f"tomo_{skill_id}"
    return {
        "gold": gold_cost,
        "rarity_multiplier": mult,
        "items": {
            skill_book_item_id: 1,
            "pedra_de_aprimoramento": max(1, (lvl + 1) // 2),
            "cristal_mana_bruto": max(1, (lvl + 2) // 3),
            "essencia_purificadora": 1 + max(0, (lvl - 1) // 4),
        },
    }


def _skill_entry_from_collection(collection: Any, skill_id: str):
    if isinstance(collection, dict):
        return collection.get(skill_id)
    if isinstance(collection, list):
        for entry in collection:
            if isinstance(entry, dict) and str(entry.get("skill_id") or entry.get("id") or "") == skill_id:
                return entry
            if str(entry or "") == skill_id:
                return {"unlocked": True}
    return None


def _item_quantity(pdata: dict, item_id: str) -> int:
    inventory = pdata.get("inventory") or {}
    if not isinstance(inventory, dict):
        return 0
    item = inventory.get(item_id)
    if isinstance(item, dict):
        for field in ("quantity", "qty", "qtd", "quantidade"):
            if field in item:
                try:
                    return max(0, int(item.get(field) or 0))
                except (TypeError, ValueError):
                    return 0
        return 1
    try:
        return max(0, int(item or 0))
    except (TypeError, ValueError):
        return 0


def _normalize_upgrade_inventory_entries(pdata: dict, item_ids) -> None:
    inventory = pdata.get("inventory")
    if not isinstance(inventory, dict):
        return
    for item_id in item_ids:
        item = inventory.get(item_id)
        if not isinstance(item, dict):
            continue
        if "quantity" not in item:
            for alias in ("qty", "qtd", "quantidade"):
                if alias in item:
                    item["quantity"] = item[alias]
                    break
            else:
                # Legacy stack entries sometimes stored only the item metadata.
                item["quantity"] = 1
        for alias in ("qty", "qtd", "quantidade"):
            item.pop(alias, None)


def get_skill_upgrade_quote(pdata: dict, skill_id: str) -> Dict[str, Any]:
    """Build the authoritative preview for an ordinary learned skill upgrade."""
    from modules.game_data.items import ITEMS_DATA, get_display_name

    skill_id = str(skill_id or "").strip()
    quote = {
        "skill_id": skill_id,
        "eligible": False,
        "can_upgrade": False,
        "max_level": SKILL_UPGRADE_MAX_LEVEL,
        "bonus_per_level_pct": SKILL_UPGRADE_BONUS_PER_LEVEL_PCT,
        "current_level": 1,
        "next_level": None,
        "current_power_pct": 0,
        "next_power_pct": None,
        "gold": {"required": 0, "owned": 0, "enough": False},
        "items": [],
        "reason": "Habilidade não encontrada.",
    }
    try:
        quote["gold"]["owned"] = max(0, int(pdata.get("gold", 0) or 0))
    except (TypeError, ValueError):
        quote["gold"]["owned"] = 0
    if skill_id not in SKILL_DATA:
        return quote
    if is_evolution_skill(skill_id):
        quote["reason"] = "Habilidades de evolução de classe terão uma progressão própria."
        return quote

    player_skills = pdata.get("skills")
    unlocked_skills = pdata.get("skills_desbloqueadas")
    skill_entry = _skill_entry_from_collection(player_skills, skill_id)
    if skill_entry is None:
        skill_entry = _skill_entry_from_collection(unlocked_skills, skill_id)
    if skill_entry is None or (isinstance(skill_entry, dict) and skill_entry.get("unlocked") is False):
        quote["reason"] = "Esta habilidade ainda não foi aprendida."
        return quote
    if not isinstance(skill_entry, dict):
        skill_entry = {}

    player_class = str(pdata.get("class") or pdata.get("class_key") or pdata.get("classe") or "")
    if not skill_is_available_to_class(player_class, skill_id):
        quote["reason"] = "Esta habilidade ainda não foi liberada para sua classe."
        return quote

    tome_id = f"tomo_{skill_id}"
    tome = ITEMS_DATA.get(tome_id) or {}
    tome_purpose = tome.get("skill_tome_purpose")
    tome_skill = str((tome.get("effects") or {}).get("learn_skill") or "")
    if (
        tome.get("type") != "skill_book"
        or tome_skill != skill_id
        or tome_purpose not in {"learn", "upgrade"}
    ):
        quote["reason"] = "O tomo desta habilidade ainda não está configurado para aprimoramento."
        return quote

    try:
        level = max(1, min(SKILL_UPGRADE_MAX_LEVEL, int(skill_entry.get("level", 1) or 1)))
    except (TypeError, ValueError):
        level = 1
    quote.update({
        "eligible": True,
        "current_level": level,
        "current_power_pct": (level - 1) * SKILL_UPGRADE_BONUS_PER_LEVEL_PCT,
        "rarity": str(skill_entry.get("rarity") or "comum"),
    })

    costs = _get_skill_upgrade_cost(level, quote["rarity"], skill_id)
    quote["rarity_multiplier"] = int(costs["rarity_multiplier"])

    if level >= SKILL_UPGRADE_MAX_LEVEL:
        quote["reason"] = "Esta habilidade já alcançou o nível máximo."
        return quote

    gold_owned = quote["gold"]["owned"]
    quote["gold"] = {
        "required": int(costs["gold"]),
        "owned": gold_owned,
        "enough": gold_owned >= int(costs["gold"]),
    }
    quote["next_level"] = level + 1
    quote["next_power_pct"] = level * SKILL_UPGRADE_BONUS_PER_LEVEL_PCT

    requirements_met = quote["gold"]["enough"]
    for item_id, required in costs["items"].items():
        item_info = ITEMS_DATA.get(item_id) or {}
        owned = _item_quantity(pdata, item_id)
        enough = owned >= int(required)
        quote["items"].append({
            "id": item_id,
            "name": get_display_name(item_id),
            "emoji": item_info.get("emoji") or "📦",
            "icon_url": item_info.get("icon_url") or "",
            "required": int(required),
            "owned": owned,
            "enough": enough,
        })
        requirements_met = requirements_met and enough

    quote["can_upgrade"] = requirements_met
    if requirements_met:
        quote["reason"] = "Você tem todos os materiais para aprimorar esta habilidade."
    else:
        quote["reason"] = "Reúna os materiais e o ouro indicados para continuar."
    return quote


def apply_skill_upgrade_to_player_data(pdata: dict, skill_id: str) -> Tuple[bool, str, dict]:
    """Consume the quoted costs and update all player skill snapshots in memory."""
    quote = get_skill_upgrade_quote(pdata, skill_id)
    if not quote.get("eligible") or not quote.get("can_upgrade"):
        return False, str(quote.get("reason") or "Não foi possível aprimorar a habilidade."), {}

    costs = _get_skill_upgrade_cost(quote["current_level"], quote.get("rarity", "comum"), skill_id)
    _normalize_upgrade_inventory_entries(pdata, costs["items"])
    if not _consume_gold(pdata, int(costs["gold"])) or not _consume_items(pdata, costs["items"]):
        return False, "Os materiais mudaram. Atualize a mochila e tente novamente.", {}

    source = _skill_entry_from_collection(pdata.get("skills"), skill_id)
    if source is None:
        source = _skill_entry_from_collection(pdata.get("skills_desbloqueadas"), skill_id)
    updated_skill = dict(source) if isinstance(source, dict) else {"unlocked": True, "rarity": "comum"}
    updated_skill["unlocked"] = True
    updated_skill["level"] = int(quote["next_level"])

    for field in ("skills", "skills_desbloqueadas", "database_skills"):
        skill_map = pdata.get(field)
        if not isinstance(skill_map, dict):
            skill_map = {}
        else:
            skill_map = dict(skill_map)
        skill_map[skill_id] = dict(updated_skill)
        pdata[field] = skill_map

    return True, f"Habilidade aprimorada para o nível {quote['next_level']}!", updated_skill


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

    pdata = deepcopy(pdata)
    sucesso, mensagem, habilidade = apply_skill_upgrade_to_player_data(pdata, skill_id)
    if not sucesso:
        return False, mensagem, {}

    await player_manager.save_player_data(oid, pdata)
    return True, mensagem, habilidade


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
