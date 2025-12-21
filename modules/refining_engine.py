# modules/refining_engine.py
# (VERSÃO FINAL: Soma itens no menu + Corrige bug de Nível 0)

from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from modules import player_manager, game_data

# ==============================================================================
# SISTEMA DE COMPATIBILIDADE (ALIASES)
# ==============================================================================
MATERIAL_ALIASES = {
    "minerio_de_ferro": ["minerio_ferro", "iron_ore", "pedra_ferro"],
    "minerio_de_estanho": ["minerio_estanho", "tin_ore"],
    "minerio_de_cobre": ["minerio_cobre", "copper_ore"],
    "madeira": ["wood", "tora_madeira"],
    "couro_de_lobo": ["wolf_leather", "pele_lobo"],
}

def get_total_material_quantity(player_data: dict, item_id: str) -> int:
    """
    Função PÚBLICA que soma o item principal + todos os seus itens antigos.
    O Handler vai usar isso para mostrar o valor correto na tela.
    """
    inv = player_data.get("inventory", {}) or {}
    
    # 1. Quantidade do item principal (novo)
    val_main = inv.get(item_id)
    total = int(val_main.get("quantity", 0)) if isinstance(val_main, dict) else int(val_main or 0)
    
    # 2. Soma os aliases (itens antigos)
    aliases = MATERIAL_ALIASES.get(item_id, [])
    for alias in aliases:
        if alias in inv:
            val_alias = inv[alias]
            qty = int(val_alias.get("quantity", 0)) if isinstance(val_alias, dict) else int(val_alias or 0)
            total += qty
            
    return total

# ----------------------- helpers -----------------------

def _seconds_with_perks(player_data: dict, base_seconds: int) -> int:
    mult_raw = player_manager.get_perk_value(player_data, 'refine_speed_multiplier', None)
    if mult_raw is None:
        mult_raw = player_manager.get_perk_value(player_data, 'craft_speed_multiplier', 1.0)
    try: mult = float(mult_raw)
    except: mult = 1.0
    if mult <= 0: mult = 0.1
    mult = max(0.25, min(4.0, mult))
    return max(1, int(base_seconds / mult))

def _norm_profession(pdata: dict) -> Tuple[Optional[str], int]:
    """Normaliza profissão e CORRIGE O NÍVEL 0."""
    raw = (pdata or {}).get("profession")
    if not raw: return (None, 0)
    if isinstance(raw, str): return (raw, 1)
    if isinstance(raw, dict):
        lvl = int(raw.get("level", 1))
        # CORREÇÃO CRÍTICA: Se tem profissão mas está nível 0, conta como nível 1
        final_lvl = max(1, lvl)
        
        if "type" in raw:
            return (raw.get("type") or None, final_lvl)
        for k, v in raw.items():
            if isinstance(v, dict): return (k, final_lvl)
            return (k, 1)
    return (None, 0)

def _is_crafting_profession(prof_type: Optional[str]) -> bool:
    if not prof_type: return False
    meta = game_data.PROFESSIONS_DATA.get(prof_type, {})
    return (meta.get("category") == "crafting")

def _has_materials(player_data: dict, inputs: dict, multiplier: int = 1) -> bool:
    # Agora usa a função pública de soma
    for k, v in (inputs or {}).items():
        needed = int(v) * multiplier
        if get_total_material_quantity(player_data, k) < needed:
            return False
    return True

def _consume_materials(player_data: dict, inputs: dict, multiplier: int = 1) -> None:
    """Consome materiais, PRIORIZANDO OS ANTIGOS."""
    inv = player_data.get("inventory", {})
    
    for item_id, qty in (inputs or {}).items():
        needed_total = int(qty) * multiplier
        
        # 1. Remove dos ANTIGOS primeiro (limpeza)
        aliases = MATERIAL_ALIASES.get(item_id, [])
        for alias in aliases:
            if needed_total <= 0: break
            if alias in inv:
                val_alias = inv[alias]
                qty_alias = int(val_alias.get("quantity", 0)) if isinstance(val_alias, dict) else int(val_alias)
                to_take = min(qty_alias, needed_total)
                if to_take > 0:
                    player_manager.remove_item_from_inventory(player_data, alias, to_take)
                    needed_total -= to_take

        # 2. Remove do NOVO se faltar
        if needed_total > 0:
            player_manager.remove_item_from_inventory(player_data, item_id, needed_total)

# ------------------- Lógica de Lote (Batch) -------------------

def get_max_refine_quantity(player_data: dict, recipe: dict) -> int:
    inputs = recipe.get("inputs", {})
    max_by_mats = 99999
    
    if not inputs: return 1

    for item_id, req_qty in inputs.items():
        if req_qty > 0:
            total_has = get_total_material_quantity(player_data, item_id)
            can_make = total_has // int(req_qty)
            if can_make < max_by_mats:
                max_by_mats = can_make

    # Limite por Nível
    prof_name = recipe.get("profession")
    prof_data = player_data.get("profession", {})
    
    # Normaliza nível usando a correção
    _, prof_lvl = _norm_profession(player_data)
    
    return min(max_by_mats, prof_lvl)

# ------------------- API principal -------------------

def preview_refine(recipe_id: str, player_data: dict) -> dict | None:
    rec = game_data.REFINING_RECIPES.get(recipe_id)
    if not rec: return None

    prof_type, prof_lvl = _norm_profession(player_data)
    
    allowed = rec.get("profession", [])
    if isinstance(allowed, str): allowed = [allowed]
    
    meets_prof = (prof_type in allowed) or _is_crafting_profession(prof_type)
    meets_lvl = prof_lvl >= int(rec.get("level_req", 1))
    
    has_mats = _has_materials(player_data, rec.get("inputs", {}), 1)
    duration = _seconds_with_perks(player_data, int(rec.get("time_seconds", 60)))

    return {
        "can_refine": bool(meets_prof and meets_lvl and has_mats),
        "meets_prof": meets_prof and meets_lvl,
        "duration_seconds": duration,
        "inputs": dict(rec.get("inputs", {})),
        "outputs": dict(rec.get("outputs", {})),
    }

async def start_batch_refine(pdata: dict, recipe_id: str, quantity: int) -> dict | str:
    rec = game_data.REFINING_RECIPES.get(recipe_id)
    if not pdata or not rec: return "Receita inválida."

    prof_type, prof_lvl = _norm_profession(pdata)
    allowed = rec.get("profession", [])
    if isinstance(allowed, str): allowed = [allowed]

    if (prof_type not in allowed) and not _is_crafting_profession(prof_type):
        return f"Sua profissão ({prof_type}) não sabe fazer isso."
    
    if prof_lvl < int(rec.get("level_req", 1)):
        return f"Nível insuficiente."

    inputs = rec.get("inputs", {})
    if not _has_materials(pdata, inputs, quantity):
         return "Falta material (verifique o total)."

    _consume_materials(pdata, inputs, quantity)

    base_time = int(rec.get("time_seconds", 60))
    total_duration = _seconds_with_perks(pdata, base_time * quantity) 
    
    base_xp = int(rec.get("xp_gain", 1))
    total_xp = int((base_xp * quantity) * 0.5) if quantity > 1 else base_xp
    total_xp = max(1, total_xp)

    finish_dt = datetime.now(timezone.utc) + timedelta(seconds=total_duration)
    
    pdata["player_state"] = {
        "action": "refining",
        "finish_time": finish_dt.isoformat(),
        "details": {
            "recipe_id": recipe_id,
            "quantity": quantity,
            "custom_xp": total_xp
        },
    }
    
    await player_manager.save_player_data(pdata["user_id"], pdata)
    
    return {
        "duration_seconds": total_duration, 
        "quantity": quantity,
        "xp_reward": total_xp
    }

async def start_refine(pdata: dict, recipe_id: str) -> dict | str:
    return await start_batch_refine(pdata, recipe_id, 1)

async def finish_refine(pdata: dict) -> dict | str:
    # Use sua função original de finish_refine aqui ou a padrão
    if not pdata: return "Jogador não encontrado."
    state = pdata.get("player_state", {}) or {}
    if state.get("action") != "refining": return {} 

    details = state.get("details") or {}
    rid = details.get("recipe_id")
    qty_made = int(details.get("quantity", 1))
    rec = game_data.REFINING_RECIPES.get(rid)
    user_id = pdata.get("user_id") 

    if not rec:
        pdata["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(user_id, pdata)
        return "Receita sumiu."

    outputs_given = {}
    for item_id, base_qty in (rec.get("outputs", {}) or {}).items():
        total_qty = int(base_qty) * qty_made
        player_manager.add_item_to_inventory(pdata, item_id, total_qty)
        outputs_given[item_id] = total_qty

    xp_gain = details.get("custom_xp", int(rec.get("xp_gain", 1)))
    prof = pdata.get("profession", {}) or {}
    prof["xp"] = int(prof.get("xp", 0)) + int(xp_gain)
    
    # Level Up simples
    cur = int(prof.get("level", 1))
    # Se estava 0, corrige pra 1
    if cur < 1: cur = 1
    
    for _ in range(10):
        try:
            need = int(100 * (cur ** 1.5))
            if hasattr(game_data, 'get_xp_for_next_collection_level'):
                need = int(game_data.get_xp_for_next_collection_level(cur))
        except: need = 999999
        if need <= 0 or prof["xp"] < need: break
        prof["xp"] -= need
        cur += 1
    
    prof["level"] = cur
    pdata["profession"] = prof
    pdata["player_state"] = {"action": "idle"}
    await player_manager.save_player_data(user_id, pdata)

    return {
        "status": "success", "outputs": outputs_given, 
        "quantity": qty_made, "xp_gained": xp_gain
    }