# modules/refining_engine.py
# (VERSÃO FINAL: Com Bônus Premium + Correção de Lote + Sem Ciclo de Import)

from datetime import datetime, timedelta, timezone
import logging
from modules import game_data
# Importamos refining apenas para tipagem ou acesso direto se necessário
from modules.game_data import refining 

logger = logging.getLogger(__name__)

# ==============================================================================
# 🛠️ HELPERS
# ==============================================================================
def get_uid_str(player_data: dict) -> str:
    if "_id" in player_data:
        return str(player_data["_id"])
    if "user_id" in player_data:
        return str(player_data["user_id"])
    return "unknown"

def _calculate_single_duration(recipe: dict, player_data: dict) -> int:
    """
    Calcula o tempo de UM item aplicando:
    1. Redução por Nível da Profissão (Max 50%)
    2. Multiplicador de Velocidade Premium (refine_speed_multiplier)
    """
    # 1. Tempo Base
    base_time = recipe.get("time_seconds", 60)

    # 2. Bônus de Nível (Reduz 1% por nível, cap em 50%)
    prof = player_data.get("profession", {})
    my_lvl = int(prof.get("level", 1))
    reduction = min(0.5, (my_lvl * 0.01)) 
    time_after_level = base_time * (1.0 - reduction)

    # 3. Bônus Premium (Velocidade)
    # Importação Tardia para evitar Circular Import
    from modules.player.premium import PremiumManager
    
    premium = PremiumManager(player_data)
    # Pega o multiplicador do premium.py (Ex: 1.5, 2.0)
    speed_mult = float(premium.get_perk_value("refine_speed_multiplier", 1.0))
    
    # Segurança contra divisão por zero
    if speed_mult < 0.1: speed_mult = 1.0

    # Fórmula: Tempo = Tempo / Velocidade
    # Se a velocidade é 2.0x, o tempo cai pela metade.
    final_time = int(time_after_level / speed_mult)
    
    return max(1, final_time)

# ==============================================================================
# 1. PREVIEW
# ==============================================================================
def preview_refine(recipe_id: str, player_data: dict) -> dict | None:
    rec = game_data.REFINING_RECIPES.get(recipe_id)
    if not rec: return None

    inv = player_data.get("inventory", {})
    inputs = rec.get("inputs", {})
    can_craft = True
    
    for item, qty in inputs.items():
        if isinstance(inv.get(item), dict):
            can_craft = False 
        else:
            held = int(inv.get(item, 0) if isinstance(inv.get(item), (int, float, str)) else 0)
            if held < qty:
                can_craft = False
                break
                
    prof = player_data.get("profession", {})
    allowed = rec.get("profession")
    if isinstance(allowed, str): allowed = [allowed]
    
    my_prof = prof.get("type", "none")
    my_lvl = int(prof.get("level", 1))
    
    prof_ok = (not allowed) or (my_prof in allowed)
    lvl_ok = my_lvl >= rec.get("level_req", 1)
    
    # ✅ USA A NOVA LÓGICA DE TEMPO
    final_time = _calculate_single_duration(rec, player_data)

    return {
        "can_refine": (can_craft and prof_ok and lvl_ok),
        "inputs": inputs,
        "outputs": rec.get("outputs", {}),
        "duration_seconds": final_time,
        "missing_req": []
    }

def get_max_refine_quantity(player_data: dict, recipe: dict) -> int:
    if not recipe: return 0
    inv = player_data.get("inventory", {})
    inputs = recipe.get("inputs", {})
    
    max_qty = 9999
    for item, req_qty in inputs.items():
        if req_qty <= 0: continue
        held = int(inv.get(item, 0) if isinstance(inv.get(item), (int, float, str)) else 0)
        can_make = held // req_qty
        if can_make < max_qty:
            max_qty = can_make
            
    return max_qty

# ==============================================================================
# 2. START (Iniciar o processo)
# ==============================================================================
async def start_refine(player_data: dict, recipe_id: str) -> dict | str:
    # ✅ IMPORTAÇÃO TARDIA
    from modules import player_manager

    # Usa o preview que já calcula o tempo correto com Premium
    prev = preview_refine(recipe_id, player_data)
    if not prev: return "Receita inválida."
    if not prev["can_refine"]: return "Materiais ou nível insuficientes."
    
    inputs = prev["inputs"]
    for item, qty in inputs.items():
        if not player_manager.consume_item(player_data, item, qty):
            return f"Erro ao consumir {item}."

    now = datetime.now(timezone.utc)
    duration = prev["duration_seconds"]
    finish_time = now + timedelta(seconds=duration)
    
    player_data["player_state"] = {
        "action": "refining",
        "started_at": now.isoformat(),
        "finish_time": finish_time.isoformat(),
        "details": {
            "recipe_id": recipe_id,
            "xp_gain": game_data.REFINING_RECIPES[recipe_id].get("xp_gain", 0)
        }
    }
    
    uid_str = get_uid_str(player_data)
    await player_manager.save_player_data(uid_str, player_data)
    
    return {
        "success": True,
        "duration_seconds": duration,
        "finish_time": finish_time
    }

async def start_batch_refine(player_data: dict, recipe_id: str, quantity: int) -> dict | str:
    # ✅ IMPORTAÇÃO TARDIA
    from modules import player_manager

    rec = game_data.REFINING_RECIPES.get(recipe_id)
    if not rec: return "Receita inválida."
    
    real_max = get_max_refine_quantity(player_data, rec)
    if quantity > real_max: quantity = real_max
    if quantity < 1: return "Materiais insuficientes."

    inputs = rec.get("inputs", {})
    for item, req in inputs.items():
        total_need = req * quantity
        player_manager.consume_item(player_data, item, total_need)

    # ✅ CORREÇÃO: Calcula o tempo unitário COM bônus e multiplica pela quantidade
    unit_time = _calculate_single_duration(rec, player_data)
    total_time = unit_time * quantity
    
    base_xp = rec.get("xp_gain", 0)
    total_xp = int((base_xp * quantity) * 0.5) 

    now = datetime.now(timezone.utc)
    finish_time = now + timedelta(seconds=total_time)
    
    player_data["player_state"] = {
        "action": "refining_batch",
        "started_at": now.isoformat(),
        "finish_time": finish_time.isoformat(),
        "details": {
            "recipe_id": recipe_id,
            "quantity": quantity,
            "xp_reward": total_xp
        }
    }
    
    uid_str = get_uid_str(player_data)
    await player_manager.save_player_data(uid_str, player_data)
    
    return {
        "success": True,
        "qty": quantity,
        "duration_seconds": total_time,
        "xp_reward": total_xp
    }

# ==============================================================================
# 3. FINISH (Entregar recompensas)
# ==============================================================================
async def finish_refine(player_data: dict) -> dict | str:
    # ✅ IMPORTAÇÃO TARDIA
    from modules import player_manager

    state = player_data.get("player_state", {})
    action = state.get("action")
    
    if action not in ("refining", "refining_batch"):
        return None 

    details = state.get("details", {})
    rid = details.get("recipe_id")
    qty = details.get("quantity", 1) 
    
    rec = game_data.REFINING_RECIPES.get(rid)
    if not rec:
        player_data["player_state"] = {"action": "idle"}
        uid_str = get_uid_str(player_data)
        await player_manager.save_player_data(uid_str, player_data)
        return "Erro: Receita não existe mais."

    outputs = rec.get("outputs", {})
    final_outputs = {}
    
    for item, base_amt in outputs.items():
        total_amt = base_amt * qty
        player_manager.add_item_to_inventory(player_data, item, total_amt)
        final_outputs[item] = total_amt

    xp_gain = details.get("xp_gain") or details.get("xp_reward") or rec.get("xp_gain", 0)
    if action == "refining": 
        xp_gain = rec.get("xp_gain", 0)
    
    prof = player_data.get("profession", {})
    prof["xp"] = int(prof.get("xp", 0)) + int(xp_gain)
    
    cur_lvl = int(prof.get("level", 1))
    req = cur_lvl * 100
    if prof["xp"] >= req:
        prof["xp"] -= req
        prof["level"] = cur_lvl + 1
    
    player_data["profession"] = prof
    player_data["player_state"] = {"action": "idle"}
    
    uid_str = get_uid_str(player_data)
    await player_manager.save_player_data(uid_str, player_data)
    
    return {
        "success": True,
        "outputs": final_outputs,
        "xp_gained": xp_gain
    }