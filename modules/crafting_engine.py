# modules/crafting_engine.py

from __future__ import annotations
from datetime import datetime, timezone, timedelta
import uuid
import random
from typing import Any, Dict, Tuple, List

# Módulos do projeto (Removemos game_data daqui de cima para evitar o ciclo)
from modules import player_manager
# Importamos apenas o essencial aqui
from modules.crafting_registry import get_recipe
# Classes raramente causam ciclo, mas se causar, moveremos também.
try:
    from modules.game_data.classes import get_primary_damage_profile
except ImportError:
    # Fallback caso classes também esteja no ciclo
    def get_primary_damage_profile(_): return {"stat_key": "dmg"}

try:
    from modules.game_data import rarity as rarity_tables
except ImportError:
    rarity_tables = None

# =========================
# Utilitários básicos
# =========================

def _get_game_data():
    """
    Importação 'preguiçosa' (Lazy Import) para quebrar o Ciclo de Importação.
    Só chama o game_data quando a função for executada, não no início do arquivo.
    """
    try:
        from modules import game_data
        return game_data
    except ImportError:
        return None

def _as_dict(obj: Any, default: Dict | None = None) -> Dict:
    if isinstance(obj, dict):
        return obj
    return {} if default is None else default

def _as_tuple_2(val: Any, fallback: Tuple[int, int] = (1, 1)) -> Tuple[int, int]:
    try:
        if isinstance(val, (list, tuple)) and len(val) >= 2:
            return int(val[0]), int(val[1])
        if isinstance(val, dict):
            if "min" in val and "max" in val:
                return int(val["min"]), int(val["max"])
            for k in ("lendario", "epico", "raro", "bom", "comum"):
                v = val.get(k)
                if isinstance(v, (list, tuple)) and len(v) >= 2:
                    return int(v[0]), int(v[1])
    except Exception:
        pass
    return fallback

async def _seconds_with_perks(player_data: dict, base_seconds: int) -> int:
    craft_mult_raw = player_manager.get_perk_value(player_data, "craft_speed_multiplier", None)
    
    if craft_mult_raw is None:
        mult = float(player_manager.get_perk_value(player_data, "refine_speed_multiplier", 1.0))
    else:
        mult = float(craft_mult_raw)  
    mult = max(0.25, min(4.0, mult))
    
    return max(1, int(base_seconds / mult))

def _has_materials(player_data: dict, inputs: dict) -> bool:
    inv = _as_dict(player_data.get("inventory"))
    for k, v in _as_dict(inputs).items():
        have = inv.get(k, 0)
        if isinstance(have, dict):
            have = int(have.get("quantity", 0))
        if int(have) < int(v):
            return False
    return True

def _consume_materials(player_data: dict, inputs: dict) -> None:
    for item_id, qty in _as_dict(inputs).items():
        player_manager.remove_item_from_inventory(player_data, item_id, int(qty))

def _get_item_info(base_id: str) -> dict:
    # Usa o Lazy Import
    gd = _get_game_data()
    try:
        if gd:
            info = gd.get_item_info(base_id)
            if info:
                return dict(info)
            # Tenta acessar ITEMS_DATA direto se get_item_info falhar
            return _as_dict(getattr(gd, "ITEMS_DATA", {})).get(base_id, {}) or {}
    except Exception:
        pass
    return {}

def _get_player_class_key(player_data: dict) -> str | None:
    candidates = [
        _as_dict(player_data.get("class")).get("type"),
        _as_dict(player_data.get("classe")).get("type"),
        player_data.get("class_type"),
        player_data.get("classe_tipo"),
        player_data.get("class_key"),
        player_data.get("classe"),
        player_data.get("class"),
    ]
    for c in candidates:
        if isinstance(c, str) and c.strip():
            return c.strip().lower()
    return None

def _is_weapon_slot(slot: str | None) -> bool:
    s = (slot or "").lower()
    return s in {"arma", "weapon", "weap", "primary_weapon"}

# =========================
# Preview / Start
# =========================

async def preview_craft(recipe_id: str, player_data: dict) -> dict | None:
    rec = get_recipe(recipe_id)
    if not rec:
        return None
    rec = dict(rec)
    inputs = _as_dict(rec.get("inputs"))
    prof = _as_dict(player_data.get("profession"))
    ok_prof = (prof.get("type") == rec.get("profession")) and \
              (int(prof.get("level", 1)) >= int(rec.get("level_req", 1)))
    duration = await _seconds_with_perks(player_data, int(rec.get("time_seconds", 60)))

    return {
        "can_craft": bool(ok_prof and _has_materials(player_data, inputs)),
        "duration_seconds": duration,
        "inputs": dict(inputs),
        "result_base_id": rec.get("result_base_id"),
        "display_name": rec.get("display_name", recipe_id),
        "emoji": rec.get("emoji", ""),
    }

async def start_craft(user_id: int, recipe_id: str):
    pdata = await player_manager.get_player_data(user_id)
    rec = get_recipe(recipe_id)
    if not pdata or not rec:
        return "Receita de forja inválida."
    rec = dict(rec)
    prof = _as_dict(pdata.get("profession"))
    if prof.get("type") != rec.get("profession") or int(prof.get("level", 1)) < int(rec.get("level_req", 1)):
        return "Nível ou tipo de profissão insuficiente para esta receita."
    inputs = _as_dict(rec.get("inputs"))
    if not _has_materials(pdata, inputs):
        return "Materiais insuficientes."
    duration = await _seconds_with_perks(pdata, int(rec.get("time_seconds", 60)))
    _consume_materials(pdata, inputs)

    finish = datetime.now(timezone.utc) + timedelta(seconds=duration)
    pdata["player_state"] = {
        "action": "crafting",
        "finish_time": finish.isoformat(),
        "details": {"recipe_id": recipe_id}
    }
    await player_manager.save_player_data(user_id, pdata)
    return {"duration_seconds": duration, "finish_time": finish.isoformat()}

# =========================
# Mapeamento/seleção de atributos
# =========================

def _attr_to_enchant_key(attr_name: str) -> str:
    a = str(attr_name or "").lower().strip()
    if not a: return "hp"
    
    if a in {"forca", "força", "ataque", "attack", "dano", "damage", "dmg", "poder", "ofensivo"}:
        return "dmg"
    if a in {"vida", "hp", "saude", "saúde", "health"}:
        return "hp"
    if a in {"defesa", "defense", "armor", "blindagem"}:
        return "defense"
    if a in {"iniciativa", "initiative", "velocidade", "agilidade", "speed"}:
        return "initiative"
    if a in {"sorte", "luck"}:
        return "luck"
    return a

def _class_primary_attr(player_class: str | None) -> str:
    profile = get_primary_damage_profile((player_class or "").lower()) or {}
    key = profile.get("stat_key") or "dmg"
    return key

def _rarity_target_attr_count(rarity: str) -> int:
    default_map = {"comum": 1, "bom": 2, "raro": 3, "epico": 4, "lendario": 5}
    table = getattr(rarity_tables, "ATTR_COUNT_BY_RARITY", None)
    
    r_key = (rarity or "").lower()
    
    if isinstance(table, dict) and table:
        val = table.get(r_key)
        if val is not None:
            return int(val)
            
    return int(default_map.get(r_key, 1))

def _secondary_attr_pool(recipe: dict, player_class: str | None) -> List[str]:
    """
    Tenta carregar AFFIX_POOLS do game_data. 
    Se falhar (por ciclo de importação ou erro), usa o BACKUP_POOL.
    """
    gd = _get_game_data() # Lazy Import
    AFFIX_POOLS = {}
    
    if gd:
        AFFIX_POOLS = getattr(gd, "AFFIX_POOLS", {}) or {}
    
    # Pool de segurança se o game_data falhar
    BACKUP_POOL = ["hp", "defense", "initiative", "luck"] 
    
    combined: List[str] = []

    for pool_name in (recipe.get("affix_pools_to_use") or []):
        pool = AFFIX_POOLS.get(pool_name) or []
        for entry in pool:
            if isinstance(entry, dict):
                stat_name = entry.get("stat") or entry.get("name") or entry.get("attr")
                if stat_name:
                    combined.append(str(stat_name))
            elif isinstance(entry, str):
                combined.append(entry)

    combined += (AFFIX_POOLS.get("geral") or [])
    if player_class:
        combined += (AFFIX_POOLS.get(player_class) or [])

    if len(combined) < 4:
        combined.extend(BACKUP_POOL)

    out: List[str] = []
    seen = {"dmg", "damage", "ataque"}
    
    for a in combined:
        key_norm = _attr_to_enchant_key(a)
        if not key_norm or key_norm in seen:
            continue
        if key_norm not in out:
            out.append(key_norm)
            
    if not out:
        out = ["hp", "defense", "initiative", "luck"]

    return out

def _pick_attribute_keys_for_item(rarity: str, primary_key: str, recipe: dict, player_class: str | None) -> List[str]:
    target = max(1, _rarity_target_attr_count(rarity))
    prim_norm = _attr_to_enchant_key(primary_key)
    
    if target == 1:
        return [primary_key]

    candidates = _secondary_attr_pool(recipe, player_class)
    random.shuffle(candidates)

    out = [primary_key]
    seen = {prim_norm, "dmg"}
    
    for c in candidates:
        ck = _attr_to_enchant_key(c)
        if ck in seen:
            continue
        seen.add(ck)
        out.append(ck)
        if len(out) >= target:
            break
            
    if len(out) < target:
        fallback_stats = ["hp", "defense", "initiative", "luck"]
        for fb in fallback_stats:
            if fb not in seen:
                seen.add(fb)
                out.append(fb)
                if len(out) >= target:
                    break

    return out[:target]


# =========================
# Raridade / meta de dano
# =========================

def _roll_rarity(player_data: dict, recipe: dict) -> str:
    prof = _as_dict(player_data.get("profession"))
    prof_level = int(prof.get("level", 1))
    level_req = int(recipe.get("level_req", 1))
    level_diff = max(0, prof_level - level_req)

    base_chances = dict(recipe.get("rarity_chances", {"comum": 1.0}))
    bonus_per_level = 0.005

    def _add_bonus(k: str, v: float) -> float:
        return max(0.0, v + (level_diff * bonus_per_level)) if k in ("bom", "raro", "epico", "lendario") else max(0.0, v)

    adjusted = {k: _add_bonus(k, float(v)) for k, v in base_chances.items()}
    total = sum(adjusted.values()) or 1.0
    norm = {k: v / total for k, v in adjusted.items()}

    order = ["lendario", "epico", "raro", "bom", "comum"]
    roll = random.random()
    acc = 0.0
    for r in order:
        acc += norm.get(r, 0.0)
        if roll < acc:
            return r
    return "comum"

# =========================
# Aplicação de atributos (= upgrade_level)
# =========================

def _apply_attr_with_upgrade(item: dict, attr_key: str, upgrade_level: int, source: str) -> None:
    ench = item.setdefault("enchantments", {})
    ench[attr_key] = {"value": int(upgrade_level), "source": source}


# =========================
# Criação do item
# =========================

def _create_dynamic_unique_item(player_data: dict, recipe: dict) -> dict:
    final_rarity = _roll_rarity(player_data, recipe)
    base_id = recipe["result_base_id"]

    SOCKETS_MAP = {
        "comum": 0, "bom": 0, 
        "raro": 1, "epico": 2, "lendario": 3
    }
    num_sockets = SOCKETS_MAP.get(final_rarity, 0)
    initial_sockets = [None] * num_sockets

    new_item = {
        "uuid": str(uuid.uuid4()),
        "base_id": base_id,
        "rarity": final_rarity,
        "upgrade_level": 1,
        "durability": [20, 20],
        "sockets": initial_sockets, 
        "enchantments": {},
    }

    info = _get_item_info(base_id)
    slot = (info.get("slot") or "").lower()

    if isinstance(recipe.get("class_req"), (list, tuple)) and recipe["class_req"]:
        target_class = str(recipe["class_req"][0]).strip().lower()
    else:
        target_class = _get_player_class_key(player_data)

    CLASS_VISIBLE_PRIMARY_ATTR = {
        "guerreiro": "forca", "berserker": "forca", "samurai": "forca",
        "cacador": "agilidade", "assassino": "agilidade", "monge": "agilidade",
        "mago": "inteligencia", "bardo": "inteligencia", "curandeiro": "inteligencia"
    }

    if _is_weapon_slot(slot):
        primary_attr = CLASS_VISIBLE_PRIMARY_ATTR.get((target_class or ""), "forca")
        mirror_dmg = True

        dmg_info = _as_dict(recipe.get("damage_info"))
        dmin, dmax = _as_tuple_2(dmg_info, (10, 20))
        class_profile = get_primary_damage_profile(target_class or "")
        scales_with = str(dmg_info.get("scales_with", class_profile.get("scales_with", "for")))
        
        new_item["damage"] = {
            "type": str(dmg_info.get("type", class_profile.get("type", "fisico"))),
            "min": int(dmg_info.get("min_damage", dmin)),
            "max": int(dmg_info.get("max_damage", dmax)),
            "scales_with": scales_with,
        }
    else:
        # CORREÇÃO: Acessa BASE_STATS_BY_RARITY diretamente via 'rarity_tables' 
        # (importado no topo), resolvendo o AttributeError.
        slot_stats = _as_dict(getattr(rarity_tables, "BASE_STATS_BY_RARITY", {})).get(slot)
        
        if slot_stats:
            # Pega o primeiro (e esperado único) atributo primário do slot na tabela
            primary_attr = next(iter(slot_stats.keys()), "hp")
        else:
            # Fallback seguro
            primary_attr = "hp"
            
        mirror_dmg = False

    attr_keys = _pick_attribute_keys_for_item(final_rarity, primary_attr, recipe, target_class)

    upg = int(new_item["upgrade_level"])
    for idx, ak in enumerate(attr_keys):
        source = "primary" if idx == 0 else "affix"
        _apply_attr_with_upgrade(new_item, _attr_to_enchant_key(ak), upg, source)

    if mirror_dmg:
        has_dmg = False
        for k in new_item["enchantments"]:
            if k == "dmg": has_dmg = True
        
        if not has_dmg:
             new_item["enchantments"]["dmg"] = {"value": upg, "source": "primary_mirror"}

    dn = info.get("display_name") or info.get("nome_exibicao") or info.get("name") or base_id.replace("_", " ").title()
    if dn:
        new_item["display_name"] = str(dn)
    
    emoji_found = info.get("emoji") or recipe.get("emoji")
    if emoji_found:
        new_item["emoji"] = emoji_found

    class_req = recipe.get("class_req")
    if isinstance(class_req, (list, tuple)):
        new_item["class_req"] = [str(x).strip().lower() for x in class_req if str(x).strip()]
    elif isinstance(class_req, str) and class_req.strip():
        new_item["class_req"] = [class_req.strip().lower()]

    return new_item

# =========================
# Finish / XP
# =========================

async def finish_craft(user_id: int):
    # Usa Lazy Import para xp curve se precisar no futuro, mas aqui usa player_manager
    # Importante: game_data é usado aqui para curva de XP
    gd = _get_game_data()

    pdata = await player_manager.get_player_data(user_id)
    pstate = _as_dict(pdata.get("player_state")) if pdata else {}
    if not pdata or pstate.get("action") != "crafting":
        return "Nenhuma forja em andamento."

    rid = _as_dict(pstate.get("details")).get("recipe_id")
    rec = get_recipe(rid)
    if not rec:
        pdata["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(user_id, pdata)
        return "Receita não encontrada ao concluir."

    rec = dict(rec)

    novo_item_criado = _create_dynamic_unique_item(pdata, rec)
    player_manager.add_unique_item(pdata, novo_item_criado)

    prof = _as_dict(pdata.get("profession"))
    if prof.get("type") == rec.get("profession"):
        prof["xp"] = int(prof.get("xp", 0)) + int(rec.get("xp_gain", 1))
        cur = int(prof.get("level", 1))
        
        # Lógica de XP segura
        if gd:
            while True:
                try: need = int(gd.get_xp_for_next_collection_level(cur))
                except Exception: need = 0
                if need <= 0 or prof["xp"] < need: break
                prof["xp"] -= need; cur += 1; prof["level"] = cur
        
        pdata["profession"] = prof

    pdata["player_state"] = {"action": "idle"}
    await player_manager.save_player_data(user_id, pdata)

    return {"status": "success", "item_criado": novo_item_criado}
