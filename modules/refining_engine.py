# modules/refining_engine.py

from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from modules import player_manager, game_data

# ----------------------- helpers -----------------------

def _seconds_with_perks(player_data: dict, base_seconds: int) -> int:
    """
    Aplica o multiplicador de velocidade de refino.
    """
    mult_raw = player_manager.get_perk_value(player_data, 'refine_speed_multiplier', None)
    if mult_raw is None:
        mult_raw = player_manager.get_perk_value(player_data, 'craft_speed_multiplier', 1.0)
    try:
        mult = float(mult_raw)
    except (ValueError, TypeError):
        mult = 1.0
    if mult <= 0: mult = 0.1
    mult = max(0.25, min(4.0, mult))
    return max(1, int(base_seconds / mult))

def _norm_profession(pdata: dict) -> Tuple[Optional[str], int]:
    """Normaliza a profissão ativa do jogador."""
    raw = (pdata or {}).get("profession")
    if not raw: return (None, 0)
    if isinstance(raw, str): return (raw, 1)
    if isinstance(raw, dict):
        if "type" in raw:
            return (raw.get("type") or None, int(raw.get("level", 1)))
        for k, v in raw.items():
            if isinstance(v, dict): return (k, int(v.get("level", 1)))
            return (k, 1)
    return (None, 0)

def _is_crafting_profession(prof_type: Optional[str]) -> bool:
    if not prof_type: return False
    meta = game_data.PROFESSIONS_DATA.get(prof_type, {})
    return (meta.get("category") == "crafting")

def _has_materials(player_data: dict, inputs: dict, multiplier: int = 1) -> bool:
    """Verifica se tem materiais para N cópias."""
    inv = player_data.get("inventory", {}) or {}
    for k, v in (inputs or {}).items():
        needed = int(v) * multiplier
        if int(inv.get(k, 0)) < needed:
            return False
    return True

def _consume_materials(player_data: dict, inputs: dict, multiplier: int = 1) -> None:
    """Consome materiais para N cópias."""
    for item_id, qty in (inputs or {}).items():
        total_qty = int(qty) * multiplier
        player_manager.remove_item_from_inventory(player_data, item_id, total_qty)

# ------------------- Lógica de Lote (Batch) -------------------

def get_max_refine_quantity(player_data: dict, recipe: dict) -> int:
    """
    Calcula o máximo que pode ser refinado baseado nos materiais E no nível da profissão.
    Regra sugerida: Nível 5 = Limite de 5 itens por vez.
    """
    # 1. Limite por Materiais
    inv = player_data.get("inventory", {}) or {}
    inputs = recipe.get("inputs", {})
    max_by_mats = 99999
    
    if not inputs: return 1

    for item_id, req_qty in inputs.items():
        if req_qty > 0:
            # Suporta tanto formato antigo (dict) quanto novo (int)
            item_entry = inv.get(item_id, 0)
            player_has = int(item_entry.get("quantity", 0)) if isinstance(item_entry, dict) else int(item_entry)
            
            can_make = player_has // int(req_qty)
            if can_make < max_by_mats:
                max_by_mats = can_make

    # 2. Limite por Nível da Profissão (Progression Cap)
    prof_name = recipe.get("profession")
    # Pega o nível da profissão correspondente
    prof_data = player_data.get("profession", {})
    
    # Verifica se a profissão bate (seja string ou dict)
    current_prof_type = prof_data.get("type")
    
    # Se a receita pede lista (ex: ['curtidor']), verifica se está nela
    recipe_profs = prof_name if isinstance(prof_name, list) else [prof_name]
    
    if current_prof_type in recipe_profs:
        prof_lvl = int(prof_data.get("level", 1))
    else:
        prof_lvl = 1
        
    # O limite de lote é igual ao nível (ex: Nvl 10 pode fazer 10 de uma vez)
    max_by_level = prof_lvl

    return min(max_by_mats, max_by_level)
# ------------------- API principal -------------------

def preview_refine(recipe_id: str, player_data: dict) -> dict | None:
    rec = game_data.REFINING_RECIPES.get(recipe_id)
    if not rec: return None

    prof_type, prof_lvl = _norm_profession(player_data)
    meets_prof = _is_crafting_profession(prof_type) and (prof_lvl >= int(rec.get("level_req", 1)))
    
    # Preview padrão para 1 unidade
    has_mats = _has_materials(player_data, rec.get("inputs", {}), 1)
    duration = _seconds_with_perks(player_data, int(rec.get("time_seconds", 60)))

    return {
        "can_refine": bool(meets_prof and has_mats),
        "duration_seconds": duration,
        "inputs": dict(rec.get("inputs", {})),
        "outputs": dict(rec.get("outputs", {})),
    }

async def start_batch_refine(pdata: dict, recipe_id: str, quantity: int) -> dict | str:
    rec = game_data.REFINING_RECIPES.get(recipe_id)
    if not pdata or not rec: return "Receita inválida."

    if quantity < 1: return "Quantidade inválida."

    # Validações de Profissão
    prof_type, prof_lvl = _norm_profession(pdata)
    if not _is_crafting_profession(prof_type):
        return "Profissão inadequada."
    
    req_lvl = int(rec.get("level_req", 1))
    if prof_lvl < req_lvl:
        return f"Nível insuficiente (Req: {req_lvl})."

    # Verifica limite real
    max_allowed = get_max_refine_quantity(pdata, rec)
    if quantity > max_allowed:
        return f"Você só pode refinar até {max_allowed} itens (Limitado por Materiais ou Nível)."

    # Consome Materiais Multiplicados
    inputs = rec.get("inputs", {})
    final_inputs = {k: v * quantity for k, v in inputs.items()}
    
    # Usa a função interna de consumo (que já lida com o inventário)
    # Precisamos garantir que ela remova a quantidade total
    for item_id, total_req in final_inputs.items():
        if not player_manager.has_item(pdata, item_id, total_req):
             return f"Falta material: {item_id}"
        player_manager.remove_item_from_inventory(pdata, item_id, total_req)

    # Cálculos
    base_time = int(rec.get("time_seconds", 60))
    # O tempo soma, mas aplica perks de velocidade
    total_duration = _seconds_with_perks(pdata, base_time * quantity) 
    
    # XP: 50% de penalidade para lotes > 1
    base_xp = int(rec.get("xp_gain", 1))
    if quantity > 1:
        total_xp = int((base_xp * quantity) * 0.5)
        total_xp = max(1, total_xp)
    else:
        total_xp = base_xp

    finish_dt = datetime.now(timezone.utc) + timedelta(seconds=total_duration)
    
    # Salva Estado
    pdata["player_state"] = {
        "action": "refining", # Mantém 'refining' para compatibilidade com actions.py
        "finish_time": finish_dt.isoformat(),
        "details": {
            "recipe_id": recipe_id,
            "quantity": quantity,      # Salva a quantidade
            "custom_xp": total_xp      # Salva o XP já calculado
        },
    }
    
    await player_manager.save_player_data(pdata["user_id"], pdata)
    
    return {
        "duration_seconds": total_duration, 
        "quantity": quantity,
        "xp_reward": total_xp
    }

# Wrapper para single refine (para compatibilidade antiga se necessário)
async def start_refine(pdata: dict, recipe_id: str) -> dict | str:
    return await start_batch_refine(pdata, recipe_id, 1)

async def finish_refine(pdata: dict) -> dict | str:
    if not pdata: return "Jogador não encontrado."

    state = pdata.get("player_state", {}) or {}
    if state.get("action") != "refining": return {} 

    details = state.get("details") or {}
    rid = details.get("recipe_id")
    # LÊ A QUANTIDADE (Default 1)
    qty_made = int(details.get("quantity", 1))
    
    rec = game_data.REFINING_RECIPES.get(rid)
    user_id = pdata.get("user_id") 

    if not user_id: return "Erro fatal: ID ausente."
    if not rec:
        pdata["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(user_id, pdata)
        return "Receita sumiu."

    # Entrega Itens (Multiplicado)
    outputs_given = {}
    for item_id, base_qty in (rec.get("outputs", {}) or {}).items():
        total_qty = int(base_qty) * qty_made
        player_manager.add_item_to_inventory(pdata, item_id, total_qty)
        outputs_given[item_id] = total_qty

    # Aplica XP
    prof_type, prof_lvl = _norm_profession(pdata)
    if _is_crafting_profession(prof_type):
        prof = pdata.get("profession", {}) or {}
        
        # Usa o XP calculado no inicio (se existir) ou calcula o base
        xp_gain = details.get("custom_xp", int(rec.get("xp_gain", 1)))

        prof["type"] = prof_type
        prof["level"] = int(prof.get("level", prof_lvl or 1))
        prof["xp"] = int(prof.get("xp", 0)) + int(xp_gain)

        # Level Up Loop
        cur = int(prof.get("level", 1))
        while True:
            try:
                need = int(game_data.get_xp_for_next_collection_level(cur))
            except Exception: need = 999999
            if need <= 0 or prof["xp"] < need: break
            prof["xp"] -= need
            cur += 1
            prof["level"] = cur
        
        pdata["profession"] = prof

    pdata["player_state"] = {"action": "idle"}
    await player_manager.save_player_data(user_id, pdata)

    return {
        "status": "success", 
        "outputs": outputs_given, 
        "quantity": qty_made,
        "xp_gained": locals().get("xp_gain", 0)
    }
