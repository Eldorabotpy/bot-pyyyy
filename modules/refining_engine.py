# modules/refining_engine.py
# (VERSÃO FINAL: Com Bônus Premium + Correção de Lote + Sem Ciclo de Import)

from datetime import datetime, timedelta, timezone
import logging
from modules import game_data
# Importamos refining apenas para tipagem ou acesso direto se necessário
from modules.game_data import refining 
from modules.game_data.xp import add_profession_xp_inplace

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

    # Preview já valida nível/materiais e calcula tempo com Premium
    prev = preview_refine(recipe_id, player_data)
    if not prev:
        return "Receita inválida."
    if not prev.get("can_refine"):
        return "Materiais ou nível insuficientes."

    inputs = prev.get("inputs", {}) or {}
    for item_id, qty in inputs.items():
        try:
            qty = int(qty or 0)
        except Exception:
            qty = 0

        if qty <= 0:
            continue

        ok = player_manager.consume_item(player_data, item_id, qty)
        if not ok:
            return f"Erro ao consumir {item_id}."

    now = datetime.now(timezone.utc)

    try:
        duration = int(prev.get("duration_seconds", 0) or 0)
    except Exception:
        duration = 0
    duration = max(1, duration)

    finish_time = now + timedelta(seconds=duration)

    # ✅ Anti-exploit: salva o tipo da profissão ATIVA no momento do start
    prof = player_data.get("profession", {}) or {}
    prof_type = (prof.get("type") or prof.get("key") or "")
    prof_type = str(prof_type).strip().lower()

    # XP base (por execução)
    rec = game_data.REFINING_RECIPES.get(recipe_id, {}) or {}
    try:
        xp_gain = int(rec.get("xp_gain", 0) or 0)
    except Exception:
        xp_gain = 0

    player_data["player_state"] = {
        "action": "refining",
        "started_at": now.isoformat(),
        "finish_time": finish_time.isoformat(),
        "details": {
            "recipe_id": recipe_id,
            "quantity": 1,
            "xp_gain": xp_gain,
            "profession_type": prof_type,  # <- CRÍTICO pro xp.py aplicar e subir nível
        }
    }

    uid_str = get_uid_str(player_data)
    await player_manager.save_player_data(uid_str, player_data)

    return {
        "success": True,
        "duration_seconds": duration,
        "finish_time": finish_time.isoformat()
    }


async def start_batch_refine(player_data: dict, recipe_id: str, quantity: int) -> dict | str:
    # ✅ IMPORTAÇÃO TARDIA
    from modules import player_manager

    rec = game_data.REFINING_RECIPES.get(recipe_id)
    if not rec:
        return "Receita inválida."

    # Normaliza quantity
    try:
        quantity = int(quantity or 0)
    except Exception:
        quantity = 0

    real_max = get_max_refine_quantity(player_data, rec)
    if quantity > real_max:
        quantity = real_max
    if quantity < 1:
        return "Materiais insuficientes."

    # ✅ Consome materiais do batch
    inputs = rec.get("inputs", {}) or {}
    for item_id, req in inputs.items():
        try:
            req = int(req or 0)
        except Exception:
            req = 0

        total_need = max(0, req * quantity)
        if total_need <= 0:
            continue

        # Obs: assumindo que consume_item já lida com stack/validação
        player_manager.consume_item(player_data, item_id, total_need)

    # ✅ Tempo total = tempo unitário (com bônus) * quantidade
    unit_time = _calculate_single_duration(rec, player_data)
    try:
        unit_time = int(unit_time or 0)
    except Exception:
        unit_time = 0
    unit_time = max(1, unit_time)

    total_time = unit_time * quantity

    # ✅ XP total do batch (sua regra: 50% do total por execução)
    try:
        base_xp = int(rec.get("xp_gain", 0) or 0)
    except Exception:
        base_xp = 0

    total_xp = max(0, int((base_xp * quantity) * 0.5))

    now = datetime.now(timezone.utc)
    finish_time = now + timedelta(seconds=total_time)

    # ✅ Anti-exploit: grava o tipo de profissão ativa no START
    prof_type = (player_data.get("profession", {}) or {}).get("type") \
        or (player_data.get("profession", {}) or {}).get("key") \
        or ""
    prof_type = str(prof_type).strip().lower()

    player_data["player_state"] = {
        "action": "refining_batch",
        "started_at": now.isoformat(),
        "finish_time": finish_time.isoformat(),
        "details": {
            "recipe_id": recipe_id,
            "quantity": quantity,
            # padroniza pro finish_refine ler sem ambiguidade
            "xp_gain": total_xp,
            # garante que o xp.py aplique XP e permita notificação de level
            "profession_type": prof_type,
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
async def finish_refine(player_data: dict) -> dict | str | None:
    # ✅ IMPORTAÇÕES TARDIAS (evita ciclos)
    from modules import player_manager
    from modules.game_data.xp import add_profession_xp_inplace

    state = player_data.get("player_state", {}) or {}
    action = state.get("action")

    if action not in ("refining", "refining_batch"):
        return None

    details = state.get("details", {}) or {}
    rid = details.get("recipe_id")

    try:
        qty = int(details.get("quantity", 1) or 1)
    except Exception:
        qty = 1
    qty = max(1, qty)

    rec = game_data.REFINING_RECIPES.get(rid)
    if not rec:
        player_data["player_state"] = {"action": "idle"}
        uid_str = get_uid_str(player_data)
        await player_manager.save_player_data(uid_str, player_data)
        return "Erro: Receita não existe mais."

    # ----------------------------
    # 1) Entrega outputs
    # ----------------------------
    outputs = rec.get("outputs", {}) or {}
    final_outputs: dict[str, int] = {}

    for item_id, base_amt in outputs.items():
        try:
            base_amt = int(base_amt or 0)
        except Exception:
            base_amt = 0

        total_amt = max(0, base_amt * qty)
        if total_amt <= 0:
            continue

        player_manager.add_item_to_inventory(player_data, item_id, total_amt)
        final_outputs[item_id] = total_amt

    # ----------------------------
    # 2) Calcula XP (centralizado no xp.py)
    # ----------------------------
    # Preferência:
    # - Se details já trouxe um TOTAL (ex: no start você calculou), respeita
    # - Senão, usa rec["xp_gain"] por execução * qty
    try:
        xp_from_details = details.get("xp_gain") or details.get("xp_reward")
        xp_from_details = int(xp_from_details) if xp_from_details is not None else None
    except Exception:
        xp_from_details = None

    try:
        base_xp = int(rec.get("xp_gain", 0) or 0)
    except Exception:
        base_xp = 0

    if xp_from_details is not None:
        xp_gain = max(0, xp_from_details)
    else:
        xp_gain = max(0, base_xp * qty)

    # expected_type: DEVE ser string (evita lista/erro e evita exploit de troca de profissão)
    expected_type = (
        (details.get("profession_type") or "").strip().lower()
        or (rec.get("profession_type") or "").strip().lower()
        or None
    )

    xp_info = {"xp_added": 0}
    if xp_gain > 0:
        xp_info = add_profession_xp_inplace(
            player_data,
            amount=int(xp_gain),
            expected_type=expected_type,
        )

    # ----------------------------
    # 3) Finaliza estado e salva
    # ----------------------------
    player_data["player_state"] = {"action": "idle"}

    uid_str = get_uid_str(player_data)
    await player_manager.save_player_data(uid_str, player_data)

    return {
        "success": True,
        "outputs": final_outputs,
        "xp_gained": int(xp_gain),
        "xp_info": xp_info,  # <-- use isso pra notificar level up no menu
        "quantity": qty,
        "recipe_id": rid,
    }
