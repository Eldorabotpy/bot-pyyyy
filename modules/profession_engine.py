# modules/profession_engine.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Tuple
import random
from datetime import datetime, timezone, timedelta

from modules import player_manager, game_data, crafting_registry

# =========================
# Config / Defaults
# =========================

# Fallbacks caso não estejam definidos nas tabelas
RARITY_CAPS_FALLBACK = {
    "comum": 5,
    "bom": 7,
    "raro": 9,
    "epico": 11,
    "lendario": 13,
}

# Itens de aprimoramento
JOIA_FORJA_ID    = "joia_da_forja"        # obrigatória em toda tentativa
SIGILO_ID        = "sigilo_protecao"      # opcional (protege contra queda)
PARCHMENT_ID     = "pergaminho_durabilidade"  # restaura durabilidade (20/20)

# =========================
# Regras de chance (ajustadas)
# =========================
# Chance base por nível de destino (target = up_atual + 1).
# +1 e +2 garantidos (100%).
BASE_SUCCESS_BY_TARGET = {
    1: 1.00,  # indo p/ +1
    2: 1.00,  # indo p/ +2
    3: 1.00,
    4: 1.00,
    5: 1.00,
    6: 1.00,
    7: 0.58,
    8: 0.57,
    9: 0.40,
    10: 0.45,
    11: 0.30,
    12: 0.36,
    13: 0.20,
    14: 0.22,
    15: 0.15,
    16: 0.10,
    17: 0.08,
    18: 0.05,
    19: 0.02,
    20: 0.01
}

# Modificadores por raridade (somados à base)
RARITY_SUCCESS_MOD = {
    "comum":    +0.10,
    "bom":      +0.05,
    "raro":      0.00,
    "epico":    -0.05,
    "lendario": -0.10,
}

# Failstack: +3% por falha, até +30% (reinicia ao sucesso)
FAILSTACK_STEP = 0.03
FAILSTACK_MAX  = 0.30

# Limites gerais de chance
MIN_CHANCE = 0.05
MAX_CHANCE = 0.95

# =========================
# Tempo com perks
# =========================
def _seconds_with_perks_for_work(player_data: dict, base_seconds: int) -> int:
    mult = float(player_manager.get_player_perk_value(player_data, "refine_speed_multiplier", 1.0))
    mult = max(0.25, min(4.0, mult))
    return int(base_seconds / mult)

# =========================
# Inventário util
# =========================
def _has_materials(player_data: dict, inputs: dict) -> bool:
    inv = player_data.get('inventory', {}) or {}
    return all(int(inv.get(k, 0)) >= int(v) for k, v in (inputs or {}).items())

def _consume_materials(player_data: dict, inputs: dict) -> None:
    for item_id, qty in (inputs or {}).items():
        player_manager.remove_item_from_inventory(player_data, item_id, int(qty))

def _inv_qty(pdata: dict, item_id: str) -> int:
    inv = (pdata or {}).get("inventory", {}) or {}
    val = inv.get(item_id, 0)
    if isinstance(val, dict):  # itens únicos não contam como pilha de material
        return 0
    try:
        return int(val)
    except Exception:
        return 0

# =========================
# Tabelas de raridade (cap)
# =========================
def _get_caps_table() -> Dict[str, int]:
    try:
        from modules.game_data import rarity as rarity_tables
        # aceitamos UPGRADE_CAP_BY_RARITY ou MAX_UPGRADE_BY_RARITY
        for attr in ("UPGRADE_CAP_BY_RARITY", "MAX_UPGRADE_BY_RARITY"):
            tb = getattr(rarity_tables, attr, None)
            if isinstance(tb, dict) and tb:
                return {str(k).lower(): int(v) for k, v in tb.items()}
    except Exception:
        pass
    return dict(RARITY_CAPS_FALLBACK)

# =========================
# Metadados de itens
# =========================
def _get_item_info(base_id: str) -> dict:
    try:
        info = game_data.get_item_info(base_id)
        if info:
            return dict(info)
    except Exception:
        pass
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

def _is_weapon(item_inst: dict) -> bool:
    base_id = (item_inst or {}).get("base_id")
    info = _get_item_info(base_id)
    slot = (info.get("slot") or "").lower()
    return slot in {"arma", "weapon", "weap", "primary_weapon"}

def _find_primary_key(item_inst: dict) -> str | None:
    ench = (item_inst or {}).get("enchantments") or {}
    if isinstance(ench, dict):
        for k, v in ench.items():
            if k == "dmg":
                continue
            if isinstance(v, dict) and str(v.get("source", "")).startswith("primary"):
                return k
    return None

# =========================
# Sincronização de atributos com upgrade_level
# =========================
def _sync_attrs_to_upgrade(item_inst: dict) -> None:
    if not isinstance(item_inst, dict):
        return
    ench = item_inst.setdefault("enchantments", {}) or {}
    up = int(item_inst.get("upgrade_level", 1))

    for k, v in list(ench.items()):
        if k == "dmg":
            continue
        if isinstance(v, dict):
            v["value"] = up
            ench[k] = v

    if _is_weapon(item_inst):
        prim = _find_primary_key(item_inst)
        if prim and prim != "dmg":
            ench["dmg"] = {"value": up, "source": "primary_mirror"}

# =========================
# Localizar receita do item (para custo de upgrade)
# =========================
def _resolve_recipe_for_inst(inst: dict) -> dict | None:
    if not isinstance(inst, dict):
        return None
    rid = inst.get("crafted_recipe_id")
    if rid:
        rec = crafting_registry.get_recipe(rid)
        if rec:
            return rec
    base_id = inst.get("base_id")
    if not base_id:
        return None
    try:
        all_rec = crafting_registry.all_recipes()
        for _, rec in (all_rec.items() if isinstance(all_rec, dict) else []):
            if rec.get("result_base_id") == base_id:
                return rec
    except Exception:
        pass
    return None

def _compute_costs_from_recipe(item_inst: dict, include_protection: bool) -> Dict[str, int]:
    """
    Custo do upgrade = insumos da receita original (mesmas quantidades)
                      + 1x joia_da_forja (obrigatória)
                      + (se include_protection=True) 1x sigilo_protecao
    """
    rec = _resolve_recipe_for_inst(item_inst)
    if not rec:
        return {}
    costs = {k: int(v) for k, v in (rec.get("inputs") or {}).items()}
    costs[JOIA_FORJA_ID] = costs.get(JOIA_FORJA_ID, 0) + 1
    if include_protection:
        costs[SIGILO_ID] = costs.get(SIGILO_ID, 0) + 1
    return costs

def _can_pay_costs(pdata: dict, costs: Dict[str, int]) -> bool:
    return all(_inv_qty(pdata, k) >= int(v) for k, v in (costs or {}).items())

def _consume_costs(pdata: dict, costs: Dict[str, int]) -> None:
    for k, need in (costs or {}).items():
        player_manager.remove_item_from_inventory(pdata, k, int(need))

# =========================
# Prévia do work (refino/forja simples)
# =========================
def preview_work(recipe_id: str, player_data: dict) -> dict | None:
    rec = crafting_registry.get_recipe(recipe_id)
    if not rec:
        return None

    prof = player_data.get("profession", {}) or {}
    ok_prof = (prof.get("type") == rec.get("profession")) and (int(prof.get("level", 1)) >= int(rec.get("level_req", 1)))
    duration = _seconds_with_perks_for_work(player_data, int(rec.get("time_seconds", 60)))
    can_pay = _has_materials(player_data, rec.get("inputs", {}))

    return {
        "can_work": ok_prof and can_pay,
        "can_profession": ok_prof,
        "has_materials": can_pay,
        "duration_seconds": duration,
        "inputs": rec.get("inputs", {}),
        "result_base_id": rec.get("result_base_id"),
        "unique": bool(rec.get("unique")),
    }

# =========================
# Início/Conclusão de trabalhos (não relacionados a upgrade)
# =========================
def start_work(user_id: int, recipe_id: str):
    pdata = player_manager.get_player_data(user_id)
    rec = crafting_registry.get_recipe(recipe_id)
    if not pdata or not rec:
        return {"error": "Receita inválida."}

    prof = pdata.get("profession", {}) or {}
    if prof.get("type") != rec.get("profession") or int(prof.get("level", 1)) < int(rec.get("level_req", 1)):
        return {"error": "Você não atende aos requisitos da profissão/nível."}

    if not _has_materials(pdata, rec.get("inputs", {})):
        return {"error": "Materiais insuficientes."}

    _consume_materials(pdata, rec.get("inputs", {}))
    duration = _seconds_with_perks_for_work(pdata, int(rec.get("time_seconds", 60)))
    finish = datetime.now(timezone.utc) + timedelta(seconds=duration)
    pdata["player_state"] = {
        "action": "working",
        "finish_time": finish.isoformat(),
        "details": {"recipe_id": recipe_id}
    }
    player_manager.save_player_data(user_id, pdata)
    return {"duration_seconds": duration, "finish_time": finish.isoformat()}

def finish_work(user_id: int) -> dict:
    pdata = player_manager.get_player_data(user_id)
    if not pdata or pdata.get("player_state", {}).get("action") != "working":
        return {"error": "Nenhum trabalho em andamento."}

    rid = (pdata["player_state"].get("details") or {}).get("recipe_id")
    rec = crafting_registry.get_recipe(rid)
    if not rec:
        pdata["player_state"] = {"action": "idle"}
        player_manager.save_player_data(user_id, pdata)
        return {"error": "Receita não encontrada ao concluir."}

    base_id = rec["result_base_id"]
    if rec.get("unique"):
        unique_item = {
            "base_id": base_id,
            "rarity": "comum",
            "durability": [100, 100],
            "enchantments": {},
            "tier": 1,
            "upgrade_level": 1,  # já nascendo em +1 (coerente com a forja)
        }
        player_manager.add_unique_item(pdata, unique_item)
    else:
        player_manager.add_item_to_inventory(pdata, base_id, 1)

    # XP da profissão
    prof = pdata.get("profession", {}) or {}
    if prof.get("type") == rec.get("profession"):
        prof["xp"] = int(prof.get("xp", 0)) + int(rec.get("xp_gain", 1))
        cur = int(prof.get("level", 1))
        while True:
            try:
                need = int(game_data.get_xp_for_next_collection_level(cur))
            except Exception:
                need = 0
            if need <= 0 or prof["xp"] < need:
                break
            prof["xp"] -= need
            cur += 1
            prof["level"] = cur
        pdata["profession"] = prof

    pdata["player_state"] = {"action": "idle"}
    player_manager.save_player_data(user_id, pdata)
    return {"status": "success", "result_base_id": base_id, "unique": bool(rec.get("unique"))}

# =========================
# Helpers de durabilidade
# =========================
def _dur_tuple(raw) -> Tuple[int, int]:
    cur, mx = 20, 20
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        try:
            cur = int(raw[0]); mx = int(raw[1])
        except Exception:
            cur, mx = 20, 20
    elif isinstance(raw, dict):
        try:
            cur = int(raw.get("current", 20)); mx = int(raw.get("max", 20))
        except Exception:
            cur, mx = 20, 20
    cur = max(0, min(cur, mx))
    mx = max(1, mx)
    return cur, mx

def _set_dur(item: dict, cur: int, mx: int) -> None:
    # mantém o formato aceitando tanto lista quanto dict – aqui normalizamos para lista
    item["durability"] = [int(max(0, min(cur, mx))), int(mx)]

# =========================
# Aprimoramento (+1 em TODOS os atributos visíveis)
# =========================
def enhance_item(player_data: dict, unique_id: str, use_joia: bool = False) -> dict:
    inv = player_data.get('inventory', {}) or {}

    item = inv.get(unique_id)
    if not isinstance(item, dict) or not item.get('base_id'):
        return {"error": "Item inválido para aprimorar."}

    rarity = str(item.get("rarity", "comum")).lower()
    up = int(item.get("upgrade_level", 1))
    caps = _get_caps_table()
    cap = int(caps.get(rarity, RARITY_CAPS_FALLBACK.get(rarity, 5)))

    if up >= cap:
        return {"error": f"Este item já está no limite (+{cap}) para a raridade {rarity}."}

    # Custos: MESMOS da receita + joia_da_forja (+ sigilo_protecao se proteção)
    costs = _compute_costs_from_recipe(item, include_protection=use_joia)
    if not costs:
        return {"error": "Não foi possível identificar a receita de origem deste item."}
    if not _can_pay_costs(player_data, costs):
        return {"error": "Materiais insuficientes para o aprimoramento."}

    # Consome custos (inclui Sigilo se use_joia=True)
    _consume_costs(player_data, costs)

    # ===== Chances com regras mais amigáveis =====
    target = up + 1
    # +1 e +2 garantidos
    if target <= 2:
        new_level = target
        item['upgrade_level'] = new_level
        item['enh_failstacks'] = 0.0
        _sync_attrs_to_upgrade(item)
        inv[unique_id] = item
        player_data['inventory'] = inv
        return {"success": True, "new_level": new_level}

    base = BASE_SUCCESS_BY_TARGET.get(target, 0.10)
    base += RARITY_SUCCESS_MOD.get(rarity, 0.0)

    # Failstack por item: armazena no próprio item
    fs = float(item.get("enh_failstacks", 0.0) or 0.0)
    fs_bonus = min(FAILSTACK_MAX, fs * FAILSTACK_STEP)

    # Perks: mantemos sua sorte/nível de profissão como bônus leve (+0.1% por ponto, opcional)
    total = player_manager.get_player_total_stats(player_data)
    luck = int(total.get('luck', 5))
    prof = player_data.get('profession', {}) or {}
    plevel = int(prof.get('level', 1))
    perk_bonus = (luck + plevel) * 0.001  # +0.1% por ponto combinado

    chance = max(MIN_CHANCE, min(MAX_CHANCE, base + fs_bonus + perk_bonus))

    roll = random.random()  # 0.0 ~ 1.0
    success = roll <= chance

    # Durabilidade: consome 1 na falha (opcional)
    cur_d, max_d = _dur_tuple(item.get("durability"))
    if not success:
        cur_d = max(0, cur_d - 1)
    _set_dur(item, cur_d, max_d)

    if success:
        new_level = up + 1
        item['upgrade_level'] = new_level
        item['enh_failstacks'] = 0.0
        _sync_attrs_to_upgrade(item)
        inv[unique_id] = item
        player_data['inventory'] = inv
        return {"success": True, "new_level": new_level}

    # Falha
    protected = False
    if use_joia and costs.get(SIGILO_ID, 0) > 0:
        # protegido: mantém nível
        protected = True
        # não altera upgrade_level
    else:
        # sem proteção: cai 1 nível apenas se já estava 3+ (evita punição pesada no começo)
        if up >= 3:
            item['upgrade_level'] = max(1, up - 1)

    # incrementa failstack
    item['enh_failstacks'] = min(10.0, float(item.get('enh_failstacks', 0.0) or 0.0) + 1.0)

    _sync_attrs_to_upgrade(item)
    inv[unique_id] = item
    player_data['inventory'] = inv
    return {"success": False, "new_level": int(item.get('upgrade_level', up)), "protected": protected}

# =========================
# Restaurar durabilidade
# =========================
def restore_durability(player_data: dict, unique_id: str) -> dict:
    inv = player_data.get('inventory', {}) or {}
    item = inv.get(unique_id)
    if not isinstance(item, dict) or not item.get('base_id'):
        return {"error": "Item inválido para restaurar."}
    if _inv_qty(player_data, PARCHMENT_ID) <= 0:
        return {"error": "Você precisa de 1x Pergaminho de Durabilidade."}

    # Consome 1 pergaminho e restaura totalmente (20/20)
    player_manager.remove_item_from_inventory(player_data, PARCHMENT_ID, 1)
    _set_dur(item, 20, 20)

    inv[unique_id] = item
    player_data['inventory'] = inv
    return {"status": "ok", "durability": item['durability']}
