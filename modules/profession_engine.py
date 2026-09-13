# modules/profession_engine.py
# (VERSÃO CORRIGIDA: Lógica Original Restaurada + Funções de Reparo Incluídas)

from __future__ import annotations
from typing import Dict, Tuple, Any
import random
from modules import player_manager, game_data, crafting_registry



# ==================================================================
# 2. SUA ENGINE ORIGINAL (Enhance, Atributos, Failstacks, Tabelas)
# ==================================================================

# Fallbacks caso não estejam definidos nas tabelas
RARITY_CAPS_FALLBACK = {
    "comum": 5, "bom": 7, "raro": 9, "epico": 11, "lendario": 13,
}

# Itens de aprimoramento
JOIA_FORJA_ID    = "pedra_de_aprimoramento"
SIGILO_ID        = "sigilo_de_protecao"
PARCHMENT_ID     = "pergaminho_de_reparo"

# Regras de chance (ajustadas)
BASE_SUCCESS_BY_TARGET = {
    1: 1.00, 2: 1.00, 3: 1.00, 4: 1.00, 5: 1.00,
    6: 1.00, 7: 1.00, 8: 1.00, 9: 1.00, 10: 1.00,
    11: 0.30, 12: 0.20, 13: 0.18, 14: 0.16, 15: 0.15,
    16: 0.10, 17: 0.08, 18: 0.05, 19: 0.02, 20: 0.01
}

RARITY_SUCCESS_MOD = {
    "comum": +0.10, "bom": +0.05, "raro": 0.00, "epico": -0.05, "lendario": -0.10,
}

FAILSTACK_STEP = 0.03
FAILSTACK_MAX  = 0.30
MIN_CHANCE = 0.05
MAX_CHANCE = 0.95

# =========================
# Inventário util
# =========================
def _inv_qty(pdata: dict, item_id: str) -> int:
    """
    Conta item no inventário por:
    - chave direta: inventory["pergaminho_durabilidade"] = 3
    - item empilhado por UID: inventory["uuid"] = {"base_id": "pergaminho_durabilidade", "quantity": 3}
    """
    inv = (pdata or {}).get("inventory", {}) or {}
    total = 0

    if not isinstance(inv, dict):
        return 0

    for uid, val in inv.items():
        if isinstance(val, dict):
            base = val.get("base_id", uid)

            if base == item_id:
                try:
                    total += int(val.get("quantity", val.get("qtd", 1)) or 0)
                except Exception:
                    total += 1

        else:
            if uid == item_id:
                try:
                    total += int(val or 0)
                except Exception:
                    pass

    return total

def _consume_costs(pdata: dict, costs: Dict[str, int]) -> None:
    for k, need in (costs or {}).items():
        player_manager.remove_item_from_inventory(pdata, k, int(need))

# =========================
# Tabelas e Metadados
# =========================
def _get_caps_table() -> Dict[str, int]:
    try:
        from modules.game_data import rarity as rarity_tables
        for attr in ("UPGRADE_CAP_BY_RARITY", "MAX_UPGRADE_BY_RARITY"):
            tb = getattr(rarity_tables, attr, None)
            if isinstance(tb, dict) and tb:
                return {str(k).lower(): int(v) for k, v in tb.items()}
    except Exception: pass
    return dict(RARITY_CAPS_FALLBACK)

def _get_item_info(base_id: str) -> dict:
    try:
        info = game_data.get_item_info(base_id)
        if info: return dict(info)
    except Exception: pass
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

# =========================
# Ferramentas de Coleta
# =========================
def _norm_tool_key(value) -> str:
    txt = str(value or "").strip().lower()
    txt = (
        txt.replace("á", "a")
           .replace("à", "a")
           .replace("ã", "a")
           .replace("â", "a")
           .replace("é", "e")
           .replace("ê", "e")
           .replace("í", "i")
           .replace("ó", "o")
           .replace("ô", "o")
           .replace("õ", "o")
           .replace("ú", "u")
           .replace("ç", "c")
    )
    return txt

def _get_equipped_tool(player_data: dict, required_tool_type: str | None = None) -> tuple[str | None, dict | None, dict | None]:
    """
    Retorna (unique_id, instância, item_base) da ferramenta equipada.

    Novo sistema:
        player_data["equipment_tools"]["ferreiro"] = uid_do_martelo

    Compatibilidade antiga:
        player_data["equipment"]["tool"] = uid_da_ferramenta
    """
    equip = player_data.get("equipment", {}) or {}
    equip_tools = player_data.get("equipment_tools", {}) or {}
    inv = player_data.get("inventory", {}) or {}

    if not isinstance(equip, dict):
        equip = {}

    if not isinstance(equip_tools, dict):
        equip_tools = {}

    required_tool_type = _norm_tool_key(required_tool_type)

    # 1. Novo sistema: busca direto pela profissão/ferramenta necessária
    if required_tool_type:
        uid = equip_tools.get(required_tool_type)
        if uid:
            inst = inv.get(uid)
            if isinstance(inst, dict):
                base_id = inst.get("base_id")
                info = _get_item_info(base_id)
                if info:
                    return uid, inst, info

    # 2. Fallback antigo: slot único "tool"
    uid = equip.get("tool")
    if uid:
        inst = inv.get(uid)
        if isinstance(inst, dict):
            base_id = inst.get("base_id")
            info = _get_item_info(base_id)

            if info:
                if required_tool_type:
                    tool_type = _norm_tool_key(info.get("tool_type"))
                    if tool_type == required_tool_type:
                        return uid, inst, info
                else:
                    return uid, inst, info

    # 3. Se não pediu tipo específico, pega qualquer ferramenta nova equipada
    if not required_tool_type:
        for uid in equip_tools.values():
            inst = inv.get(uid)
            if isinstance(inst, dict):
                base_id = inst.get("base_id")
                info = _get_item_info(base_id)
                if info:
                    return uid, inst, info

    return None, None, None

def _consume_tool_durability(tool_inst: dict, amount: int = 1) -> bool:
    """
    Consome durabilidade da ferramenta.
    Retorna False se quebrar.
    """
    cur, mx = _dur_tuple(tool_inst.get("durability"))
    cur -= amount
    if cur <= 0:
        _set_dur(tool_inst, 0, mx)
        return False

    _set_dur(tool_inst, cur, mx)
    return True

def _norm_prof_speed_key(value) -> str:
    txt = str(value or "").strip().lower()
    txt = (
        txt.replace("á", "a")
           .replace("à", "a")
           .replace("ã", "a")
           .replace("â", "a")
           .replace("é", "e")
           .replace("ê", "e")
           .replace("í", "i")
           .replace("ó", "o")
           .replace("ô", "o")
           .replace("õ", "o")
           .replace("ú", "u")
           .replace("ç", "c")
    )
    return txt


def get_profession_level_for_speed(player_data: dict, profession_key: str) -> int:
    """
    Pega o nível da profissão, considerando:
    - learned_professions novo
    - profession antigo
    """
    prof_key = _norm_prof_speed_key(profession_key)
    if not prof_key:
        return 1

    learned = player_data.get("learned_professions", {}) or {}

    if isinstance(learned, dict):
        prof_data = learned.get(prof_key)
        if isinstance(prof_data, dict):
            try:
                return max(1, int(prof_data.get("level", 1) or 1))
            except Exception:
                return 1

    elif isinstance(learned, list):
        if prof_key in [_norm_prof_speed_key(p) for p in learned]:
            return 1

    legacy = player_data.get("profession", {}) or {}
    if isinstance(legacy, dict):
        legacy_key = _norm_prof_speed_key(legacy.get("key") or legacy.get("type"))
        if legacy_key == prof_key:
            try:
                return max(1, int(legacy.get("level", 1) or 1))
            except Exception:
                return 1

    return 1


def get_equipped_tool_for_speed(player_data: dict, profession_key: str):
    """
    Procura a ferramenta equipada para a profissão.

    Novo sistema:
        equipment_tools["ferreiro"]

    Compatibilidade:
        equipment["tool"]
    """
    prof_key = _norm_prof_speed_key(profession_key)

    inv = player_data.get("inventory", {}) or {}
    equip = player_data.get("equipment", {}) or {}
    equip_tools = player_data.get("equipment_tools", {}) or {}

    if not isinstance(inv, dict):
        inv = {}
    if not isinstance(equip, dict):
        equip = {}
    if not isinstance(equip_tools, dict):
        equip_tools = {}

    # 1. Novo sistema: ferramenta por profissão
    uid = equip_tools.get(prof_key)
    if uid:
        inst = inv.get(uid)
        if isinstance(inst, dict):
            info = _get_item_info(inst.get("base_id"))
            if info:
                return uid, inst, info

    # 2. Compatibilidade: slot antigo único
    uid = equip.get("tool")
    if uid:
        inst = inv.get(uid)
        if isinstance(inst, dict):
            info = _get_item_info(inst.get("base_id"))
            tool_type = _norm_prof_speed_key(info.get("tool_type") or inst.get("tool_type"))

            if not prof_key or tool_type == prof_key:
                return uid, inst, info

    return None, None, None


def get_profession_key_from_recipe_for_speed(recipe: dict, fallback: str = "ferreiro") -> str:
    if not isinstance(recipe, dict):
        return _norm_prof_speed_key(fallback)

    raw = (
        recipe.get("profession")
        or recipe.get("profession_req")
        or recipe.get("required_tool_type")
        or recipe.get("tool_type")
        or fallback
    )

    if isinstance(raw, (list, tuple)) and raw:
        raw = raw[0]

    return _norm_prof_speed_key(raw)


def get_profession_key_from_item_for_speed(item_inst: dict, fallback: str = "ferreiro") -> str:
    """
    Descobre a profissão do item pela receita original.
    Serve para melhorar e desmontar.
    """
    if not isinstance(item_inst, dict):
        return _norm_prof_speed_key(fallback)

    recipe = None

    recipe_id = item_inst.get("crafted_recipe_id")
    base_id = item_inst.get("base_id")

    if recipe_id:
        recipe = crafting_registry.get_recipe(recipe_id)

    if not recipe and base_id:
        recipe = crafting_registry.get_recipe_by_item_id(base_id)

    if recipe:
        return get_profession_key_from_recipe_for_speed(recipe, fallback)

    return _norm_prof_speed_key(fallback)


def calculate_profession_work_duration(
    player_data: dict,
    base_seconds: int,
    profession_key: str,
    apply_perks: bool = True
) -> dict:
    """
    Calcula tempo final de trabalho.

    Fórmula:
    - profissão: 0.5% por nível, máximo 25%
    - tier ferramenta: T1 0%, T2 5%, T3 10%, T4 15%, T5 20%
    - upgrade ferramenta: 1% por upgrade_level, máximo 10%
    - redução total máxima: 50%
    """
    base_seconds = max(1, int(base_seconds or 1))
    prof_key = _norm_prof_speed_key(profession_key)

    prof_level = get_profession_level_for_speed(player_data, prof_key)

    # Profissão: 0.5% por nível, máximo 25%
    profession_bonus = min(0.25, prof_level * 0.005)

    tool_uid, tool_inst, tool_info = get_equipped_tool_for_speed(player_data, prof_key)

    tool_tier = 1
    tool_upgrade = 0
    tier_bonus = 0.0
    upgrade_bonus = 0.0

    if isinstance(tool_info, dict) and isinstance(tool_inst, dict):
        try:
            tool_tier = max(1, int(tool_info.get("tier", tool_inst.get("tier", 1)) or 1))
        except Exception:
            tool_tier = 1

        try:
            tool_upgrade = max(0, int(tool_inst.get("upgrade_level", tool_inst.get("refino", 0)) or 0))
        except Exception:
            tool_upgrade = 0

        # T1 0%, T2 5%, T3 10%, T4 15%, T5 20%
        tier_bonus = min(0.20, max(0, tool_tier - 1) * 0.05)

        # +1% por melhoria, máximo 10%
        upgrade_bonus = min(0.10, tool_upgrade * 0.01)

    total_reduction = min(0.50, profession_bonus + tier_bonus + upgrade_bonus)

    after_reduction = max(1, int(base_seconds * (1.0 - total_reduction)))

    perk_multiplier = 1.0

    if apply_perks:
        try:
            craft_mult_raw = player_manager.get_perk_value(player_data, "craft_speed_multiplier", None)

            if craft_mult_raw is None:
                perk_multiplier = float(player_manager.get_perk_value(player_data, "refine_speed_multiplier", 1.0))
            else:
                perk_multiplier = float(craft_mult_raw)

            perk_multiplier = max(0.25, min(4.0, perk_multiplier))
        except Exception:
            perk_multiplier = 1.0

    final_seconds = max(1, int(after_reduction / perk_multiplier))

    return {
        "duration_seconds": final_seconds,
        "base_seconds": base_seconds,
        "profession_key": prof_key,
        "profession_level": prof_level,
        "profession_bonus": round(profession_bonus, 4),
        "tool_uid": tool_uid,
        "tool_tier": tool_tier,
        "tool_upgrade": tool_upgrade,
        "tier_bonus": round(tier_bonus, 4),
        "upgrade_bonus": round(upgrade_bonus, 4),
        "total_reduction": round(total_reduction, 4),
        "perk_multiplier": round(perk_multiplier, 4)
    }

def _norm_tool_key(value) -> str:
    txt = str(value or "").strip().lower()
    txt = (
        txt.replace("á", "a")
           .replace("à", "a")
           .replace("ã", "a")
           .replace("â", "a")
           .replace("é", "e")
           .replace("ê", "e")
           .replace("í", "i")
           .replace("ó", "o")
           .replace("ô", "o")
           .replace("õ", "o")
           .replace("ú", "u")
           .replace("ç", "c")
    )
    return txt


def _recipe_required_tool_type(recipe: dict, fallback: str = "ferreiro") -> str:
    """
    Descobre qual ferramenta a receita exige.

    Prioridade:
    1. required_tool_type
    2. tool_type
    3. profession
    4. profession_req
    5. fallback
    """
    if not isinstance(recipe, dict):
        return _norm_tool_key(fallback)

    raw = (
        recipe.get("required_tool_type")
        or recipe.get("tool_type")
        or recipe.get("profession")
        or recipe.get("profession_req")
        or fallback
    )

    if isinstance(raw, (list, tuple)) and raw:
        raw = raw[0]

    return _norm_tool_key(raw)


def _recipe_required_tool_tier(recipe: dict) -> int:
    """
    Descobre tier mínimo da ferramenta.

    Se a receita não informar tier, usa 1.
    """
    if not isinstance(recipe, dict):
        return 1

    for key in ("required_tool_tier", "tool_tier_req", "min_tool_tier"):
        if recipe.get(key) is not None:
            try:
                return max(1, int(recipe.get(key)))
            except Exception:
                return 1

    return 1


def validate_and_consume_profession_tool(
    player_data: dict,
    required_tool_type: str,
    min_tier: int = 1,
    durability_cost: int = 1,
    action_name: str = "ação"
) -> dict:
    """
    Valida e gasta durabilidade da ferramenta equipada.

    Usado por:
    - forjar
    - desmontar
    - melhorar

    Retorno:
    {
        "ok": True/False,
        "error": "...",
        "tool_uid": "...",
        "tool_broke": True/False,
        "message": "..."
    }
    """
    required_tool_type = _norm_tool_key(required_tool_type)
    min_tier = max(1, int(min_tier or 1))
    durability_cost = max(1, int(durability_cost or 1))

    uid, tool_inst, tool_info = _get_equipped_tool(player_data, required_tool_type)

    if not tool_inst or not tool_info:
        return {
            "ok": False,
            "error": f"Você precisa equipar uma ferramenta de {required_tool_type} para {action_name}."
        }

    tool_type = _norm_tool_key(tool_info.get("tool_type"))
    if tool_type != required_tool_type:
        return {
            "ok": False,
            "error": f"Ferramenta incompatível. Requer {required_tool_type}, mas você equipou {tool_type or 'desconhecida'}."
        }

    tool_tier = int(tool_info.get("tier", 1) or 1)
    if tool_tier < min_tier:
        return {
            "ok": False,
            "error": f"Ferramenta fraca demais. Requer tier {min_tier}."
        }

    cur, mx = _dur_tuple(tool_inst.get("durability"))
    if cur <= 0:
        return {
            "ok": False,
            "error": "Sua ferramenta está quebrada."
        }

    tool_broke = not _consume_tool_durability(tool_inst, durability_cost)

    msg = ""
    if tool_broke:
        msg = " Sua ferramenta quebrou."

    return {
        "ok": True,
        "tool_uid": uid,
        "tool_type": required_tool_type,
        "tool_tier": tool_tier,
        "tool_broke": tool_broke,
        "message": msg
    }


def validate_and_consume_tool_for_recipe(
    player_data: dict,
    recipe: dict,
    action_name: str = "forjar"
) -> dict:
    """
    Usa a receita para decidir qual ferramenta gastar.
    """
    required_tool_type = _recipe_required_tool_type(recipe, "ferreiro")
    min_tier = _recipe_required_tool_tier(recipe)

    try:
        durability_cost = int(recipe.get("tool_durability_cost", 1) or 1)
    except Exception:
        durability_cost = 1

    return validate_and_consume_profession_tool(
        player_data=player_data,
        required_tool_type=required_tool_type,
        min_tier=min_tier,
        durability_cost=durability_cost,
        action_name=action_name
    )


def validate_and_consume_tool_for_item(
    player_data: dict,
    item_obj: dict,
    fallback_tool_type: str = "ferreiro",
    action_name: str = "melhorar"
) -> dict:
    """
    Usa o item para achar a receita original e decidir qual ferramenta gastar.
    """
    recipe = None

    if isinstance(item_obj, dict):
        recipe_id = item_obj.get("crafted_recipe_id")
        base_id = item_obj.get("base_id")

        if recipe_id:
            recipe = crafting_registry.get_recipe(recipe_id)

        if not recipe and base_id:
            recipe = crafting_registry.get_recipe_by_item_id(base_id)

    if recipe:
        return validate_and_consume_tool_for_recipe(
            player_data=player_data,
            recipe=recipe,
            action_name=action_name
        )

    return validate_and_consume_profession_tool(
        player_data=player_data,
        required_tool_type=fallback_tool_type,
        min_tier=1,
        durability_cost=1,
        action_name=action_name
    )

def validate_and_prepare_gather(player_data: dict, recurso_tipo: str | None = None, required_tool_type: str | None = None) -> dict:
    """
    Valida se o jogador pode coletar.

    Corrigido para:
    - aceitar multi-profissões em learned_professions
    - aceitar profession.key ou profession.type
    - escolher profissão pela coleta clicada
    - usar ferramenta correta em equipment_tools
    """

    def _norm_prof(valor):
        return _norm_tool_key(valor)

    MAPA_RECURSO_PROFISSAO = {
        "madeira": "lenhador",
        "pedra": "minerador",
        "minerio_de_ferro": "minerador",
        "linho": "colhedor",
        "pena": "esfolador",
        "sangue": "alquimista",
    }

    prof_key = (
        required_tool_type
        or MAPA_RECURSO_PROFISSAO.get(_norm_prof(recurso_tipo))
    )

    prof_key = _norm_prof(prof_key)

    if not prof_key:
        prof = player_data.get("profession", {}) or {}

        if isinstance(prof, dict):
            prof_key = _norm_prof(prof.get("key") or prof.get("type"))
        elif isinstance(prof, str):
            prof_key = _norm_prof(prof)

    if not prof_key:
        return {"ok": False, "error": "Você não possui uma profissão válida para coletar."}

    profissoes = set()

    prof_atual = player_data.get("profession", {}) or {}

    if isinstance(prof_atual, dict):
        if prof_atual.get("key"):
            profissoes.add(_norm_prof(prof_atual.get("key")))
        if prof_atual.get("type"):
            profissoes.add(_norm_prof(prof_atual.get("type")))

        for k in prof_atual.keys():
            profissoes.add(_norm_prof(k))

    elif isinstance(prof_atual, str):
        profissoes.add(_norm_prof(prof_atual))

    learned = player_data.get("learned_professions", {}) or {}

    if isinstance(learned, dict):
        for k, v in learned.items():
            profissoes.add(_norm_prof(k))

            if isinstance(v, dict):
                if v.get("key"):
                    profissoes.add(_norm_prof(v.get("key")))
                if v.get("type"):
                    profissoes.add(_norm_prof(v.get("type")))
            elif isinstance(v, str):
                profissoes.add(_norm_prof(v))

    elif isinstance(learned, list):
        for p in learned:
            if isinstance(p, str):
                profissoes.add(_norm_prof(p))
            elif isinstance(p, dict):
                if p.get("key"):
                    profissoes.add(_norm_prof(p.get("key")))
                if p.get("type"):
                    profissoes.add(_norm_prof(p.get("type")))

    if prof_key not in profissoes:
        return {
            "ok": False,
            "error": f"Requer profissão: {prof_key.capitalize()}."
        }

    uid, tool_inst, tool_info = _get_equipped_tool(player_data, prof_key)

    if not tool_inst or not tool_info:
        return {
            "ok": False,
            "error": f"Você precisa equipar uma ferramenta de {prof_key}."
        }

    tool_type = _norm_tool_key(tool_info.get("tool_type") or tool_inst.get("tool_type"))

    if tool_type != prof_key:
        return {
            "ok": False,
            "error": f"Ferramenta incompatível. Requer {prof_key}, mas você equipou {tool_type or 'desconhecida'}."
        }

    cur, _ = _dur_tuple(tool_inst.get("durability"))

    if cur <= 0:
        return {"ok": False, "error": "Sua ferramenta está quebrada."}

    return {
        "ok": True,
        "tool_uid": uid,
        "tool_inst": tool_inst,
        "tool_info": tool_info,
        "profession": prof_key
    }

def _is_weapon(item_inst: dict) -> bool:
    base_id = (item_inst or {}).get("base_id")
    info = _get_item_info(base_id)
    slot = (info.get("slot") or "").lower()
    return slot in {"arma", "weapon", "weap", "primary_weapon"}

def _sync_attrs_to_upgrade(item_inst: dict) -> None:
    """Sincroniza atributos com o nível de upgrade."""
    if not isinstance(item_inst, dict): return
    
    ench = item_inst.setdefault("enchantments", {}) or {}
    up = int(item_inst.get("upgrade_level", 1)) 
    primary_key_found = None

    for k, v in list(ench.items()):
        if not isinstance(v, dict): continue
        source = str(v.get("source", ""))
        if source == "primary_mirror": continue
        v["value"] = up
        ench[k] = v
        if source == "primary": primary_key_found = k

    if _is_weapon(item_inst):
        if primary_key_found and primary_key_found != "dmg":
            ench["dmg"] = {"value": up, "source": "primary_mirror"}

# =========================
# Custos baseados na receita original
# =========================
def _resolve_recipe_for_inst(inst: dict) -> dict | None:
    if not isinstance(inst, dict): return None
    rid = inst.get("crafted_recipe_id")
    if rid:
        rec = crafting_registry.get_recipe(rid)
        if rec: return rec
    base_id = inst.get("base_id")
    if not base_id: return None
    try:
        all_rec = crafting_registry.all_recipes()
        for _, rec in (all_rec.items() if isinstance(all_rec, dict) else []):
            if rec.get("result_base_id") == base_id: return rec
    except Exception: pass
    return None

def _compute_costs_from_recipe(item_inst: dict, include_protection: bool) -> Dict[str, int]:
    rec = _resolve_recipe_for_inst(item_inst)
    if not rec: return {} 
    costs = {k: int(v) for k, v in (rec.get("inputs") or {}).items()}
    costs[JOIA_FORJA_ID] = costs.get(JOIA_FORJA_ID, 0) + 1
    if include_protection:
        costs[SIGILO_ID] = costs.get(SIGILO_ID, 0) + 1
    return costs

def _can_pay_costs(pdata: dict, costs: Dict[str, int]) -> bool:
    return all(_inv_qty(pdata, k) >= int(v) for k, v in (costs or {}).items())

# =========================
# APRIMORAMENTO (ENHANCE)
# =========================
async def enhance_item(user_id: str, player_data: dict, unique_id: str, use_joia: bool = False) -> dict:
    inv = player_data.get('inventory', {}) or {}
    item = inv.get(unique_id)
    
    if not isinstance(item, dict) or not item.get('base_id'):
        return {"success": False, "error": "Item inválido."}

    rarity = str(item.get("rarity", "comum")).lower()
    up = int(item.get("upgrade_level", 1))
    caps = _get_caps_table()
    cap = int(caps.get(rarity, RARITY_CAPS_FALLBACK.get(rarity, 5)))

    if up >= cap:
        return {"success": False, "error": f"Item no limite (+{cap}) para {rarity}."}

    costs = _compute_costs_from_recipe(item, include_protection=use_joia)
    if not costs:
        costs = {JOIA_FORJA_ID: 1}
        if use_joia: costs[SIGILO_ID] = 1

    if not _can_pay_costs(player_data, costs):
        return {"success": False, "error": "Materiais insuficientes."}

    _consume_costs(player_data, costs)

    # Lógica de Chance
    target = up + 1
    if target <= 2: 
        new_level = target
        item['upgrade_level'] = new_level
        item['enh_failstacks'] = 0.0
        _sync_attrs_to_upgrade(item)
        await player_manager.save_player_data(user_id, player_data)
        return {"success": True, "new_level": new_level, "message": f"Sucesso garantido! +{new_level}"}

    base = BASE_SUCCESS_BY_TARGET.get(target, 0.10)
    base += RARITY_SUCCESS_MOD.get(rarity, 0.0)

    fs = float(item.get("enh_failstacks", 0.0) or 0.0)
    fs_bonus = min(FAILSTACK_MAX, fs * FAILSTACK_STEP)
    
    total_stats = await player_manager.get_player_total_stats(player_data)
    luck = int(total_stats.get('luck', 5))
    prof_lvl = int(player_data.get('profession', {}).get('level', 1))
    perk_bonus = (luck + prof_lvl) * 0.001

    chance = max(MIN_CHANCE, min(MAX_CHANCE, base + fs_bonus + perk_bonus))
    success = random.random() <= chance

    # Durabilidade na falha
    cur_d, max_d = _dur_tuple(item.get("durability"))
    if not success:
        cur_d = max(0, cur_d - 1)
    _set_dur(item, cur_d, max_d)

    msg = ""
    if success:
        new_level = up + 1
        item['upgrade_level'] = new_level
        item['enh_failstacks'] = 0.0
        _sync_attrs_to_upgrade(item)
        msg = f"✨ <b>SUCESSO!</b> Agora é +{new_level}!"
    else:
        protected = False
        if use_joia and costs.get(SIGILO_ID, 0) > 0:
            protected = True
            msg = "❌ Falhou! (Protegido pelo Sigilo)"
        else:
            if up >= 3:
                item['upgrade_level'] = max(1, up - 1)
                msg = f"❌ Falhou! Caiu para +{item['upgrade_level']}."
            else:
                msg = "❌ Falhou! (Nível mantido)."
        
        item['enh_failstacks'] = min(10.0, float(item.get('enh_failstacks', 0.0) or 0.0) + 1.0)
        _sync_attrs_to_upgrade(item)

    await player_manager.save_player_data(user_id, player_data)
    return {"success": success, "new_level": item.get("upgrade_level"), "message": msg}

# =========================
# Helpers Durabilidade (Seu código original)
# =========================
def _dur_tuple(raw) -> Tuple[int, int]:
    cur, mx = 20, 20
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        try: cur = int(raw[0]); mx = int(raw[1])
        except: pass
    elif isinstance(raw, dict):
        try: cur = int(raw.get("current", 20)); mx = int(raw.get("max", 20))
        except: pass
    return max(0, min(cur, mx)), max(1, mx)

def _set_dur(item: dict, cur: int, mx: int) -> None:
    item["durability"] = [int(max(0, min(cur, mx))), int(mx)]

# ==================================================================
# 3. REPARO E REPARO EM MASSA
# ==================================================================

async def restore_durability(player_data: dict, unique_id: str) -> dict:
    inv = player_data.get('inventory', {}) or {}
    item = inv.get(unique_id)
    
    if not isinstance(item, dict) or not item.get('base_id'):
        return {"error": "Item inválido para restaurar."}
        
    # 👇 MÁGICA AQUI: O código agora aceita os dois IDs!
    pergaminho_usado = None
    if _inv_qty(player_data, "pergaminho_de_reparo") > 0:
        pergaminho_usado = "pergaminho_de_reparo"
    elif _inv_qty(player_data, "pergaminho_durabilidade") > 0:
        pergaminho_usado = "pergaminho_durabilidade"
        
    if not pergaminho_usado:
        return {"error": "Você precisa de 1x Pergaminho de Reparo."}

    # Consome 1 pergaminho e restaura totalmente
    player_manager.remove_item_from_inventory(player_data, pergaminho_usado, 1)
    
    # Pega durabilidade máxima real
    info = _get_item_info(item.get("base_id"))
    max_d = 20
    raw_dur = info.get("durability")
    if isinstance(raw_dur, list): max_d = raw_dur[1]
    elif isinstance(raw_dur, int): max_d = raw_dur

    _set_dur(item, max_d, max_d)
    
    return {"status": "ok", "durability": item['durability']}

async def restore_all_equipped_durability(player_data: dict) -> dict:
    """
    Restaura TODOS os itens equipados consumindo APENAS 1 Pergaminho.

    Corrige ferramentas de:
    - combate/equipamentos normais em equipment
    - crafting/coleta em equipment_tools
    - referências salvas como UID
    - referências salvas como base_id
    - referências salvas como objeto
    """
    inv = player_data.get("inventory", {}) or {}
    equip = player_data.get("equipment", {}) or {}
    equip_tools = player_data.get("equipment_tools", {}) or {}

    if not isinstance(inv, dict):
        inv = {}

    if not isinstance(equip, dict):
        equip = {}

    if not isinstance(equip_tools, dict):
        equip_tools = {}

    def _dur_tuple_local(raw):
        cur, mx = 0, 0

        if isinstance(raw, (list, tuple)) and len(raw) >= 2:
            try:
                cur, mx = int(raw[0]), int(raw[1])
            except Exception:
                cur, mx = 0, 0

        elif isinstance(raw, dict):
            try:
                cur = int(raw.get("current", raw.get("cur", 0)))
                mx = int(raw.get("max", raw.get("mx", 0)))
            except Exception:
                cur, mx = 0, 0

        mx = max(0, mx)
        cur = max(0, min(cur, mx)) if mx > 0 else max(0, cur)

        return cur, mx

    def _max_from_info_local(info: dict, fallback_max: int) -> int:
        if not isinstance(info, dict):
            return int(fallback_max or 0)

        raw = info.get("durability")

        if isinstance(raw, (list, tuple)) and len(raw) >= 2:
            try:
                return int(raw[1])
            except Exception:
                return int(fallback_max or 0)

        if isinstance(raw, int):
            return int(raw)

        if isinstance(raw, dict):
            try:
                return int(raw.get("max", fallback_max or 0))
            except Exception:
                return int(fallback_max or 0)

        return int(fallback_max or 0)

    def _set_dur_local(item: dict, cur: int, mx: int) -> None:
        item["durability"] = [int(max(0, min(cur, mx))), int(max(0, mx))]

    def _get_item_info_local(base_id: str) -> dict:
        try:
            return _get_item_info(base_id) or {}
        except Exception:
            return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

    def _extrair_ids_equipados(valor, saida: set):
        """
        Aceita:
        - string UID
        - string base_id
        - dict com uid/id/item_id/unique_id/base_id
        - dict aninhado
        """
        if not valor:
            return

        if isinstance(valor, str):
            saida.add(valor)
            return

        if isinstance(valor, dict):
            for chave in ("uid", "id", "item_id", "unique_id", "base_id"):
                if valor.get(chave):
                    saida.add(str(valor.get(chave)))

            for subvalor in valor.values():
                if isinstance(subvalor, (dict, str)):
                    _extrair_ids_equipados(subvalor, saida)

    def _resolver_instancia_por_id(possivel_id: str):
        """
        Tenta achar no inventário:
        1. por UID direto
        2. por base_id
        """
        if not possivel_id:
            return None, None

        # 1. UID direto
        inst = inv.get(possivel_id)
        if isinstance(inst, dict):
            return possivel_id, inst

        # 2. Busca por base_id
        for uid_real, obj in inv.items():
            if not isinstance(obj, dict):
                continue

            base = str(obj.get("base_id", uid_real))
            if base == str(possivel_id):
                return uid_real, obj

        return None, None

    # 1. Verifica pergaminho.
    pergaminho_usado = None

    if _inv_qty(player_data, "pergaminho_de_reparo") > 0:
        pergaminho_usado = "pergaminho_de_reparo"
    elif _inv_qty(player_data, "pergaminho_durabilidade") > 0:
        pergaminho_usado = "pergaminho_durabilidade"

    if not pergaminho_usado:
        return {"error": "Você precisa de 1x Pergaminho de Reparo."}

    # 2. Junta referências equipadas.
    ids_equipados = set()

    for valor in equip.values():
        _extrair_ids_equipados(valor, ids_equipados)

    for valor in equip_tools.values():
        _extrair_ids_equipados(valor, ids_equipados)

    if not ids_equipados:
        return {"error": "Nenhum equipamento equipado para restaurar."}

    # 3. Resolve para itens reais no inventário.
    itens_equipados = {}

    for possivel_id in ids_equipados:
        uid_real, inst = _resolver_instancia_por_id(possivel_id)

        if uid_real and isinstance(inst, dict):
            itens_equipados[uid_real] = inst

    if not itens_equipados:
        return {"error": "Nenhum equipamento equipado foi encontrado no inventário."}

    # 4. Descobre quais precisam reparo.
    need_repair = []

    for uid, inst in itens_equipados.items():
        cur, mx = _dur_tuple_local(inst.get("durability"))

        base_id = inst.get("base_id")
        info = _get_item_info_local(base_id)
        real_max = _max_from_info_local(info, mx)

        if real_max <= 0 and mx > 0:
            real_max = mx

        if real_max <= 0:
            continue

        if cur < real_max:
            need_repair.append((uid, real_max))

    if not need_repair:
        return {"error": "Todos os equipamentos equipados já estão com durabilidade máxima."}

    # 5. Consome 1 pergaminho.
    player_manager.remove_item_from_inventory(player_data, pergaminho_usado, 1)

    # 6. Repara todos.
    count = 0

    for uid, real_max in need_repair:
        inst = inv.get(uid)

        if not isinstance(inst, dict):
            continue

        _set_dur_local(inst, real_max, real_max)
        count += 1

    player_data["inventory"] = inv

    return {
        "success": True,
        "count": count,
        "message": f"Uma luz dourada restaurou {count} equipamentos e ferramentas perfeitamente!"
    }

# =========================
# Util XP
# =========================
def _add_xp(player_data, amount):
    p = player_data.setdefault("profession", {})
    if "level" not in p: p["level"] = 1
    if "xp" not in p: p["xp"] = 0
    p["xp"] += amount
    req = p["level"] * 100
    if p["xp"] >= req:
        p["xp"] -= req
        p["level"] += 1