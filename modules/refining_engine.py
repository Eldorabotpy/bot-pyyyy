# modules/refining_engine.py
# (VERSÃO ADAPTADA PARA MONGODB OBJECTID)

from datetime import datetime, timedelta, timezone
import logging
from modules import game_data, player_manager
from modules.game_data import refining 

logger = logging.getLogger(__name__)

# ==============================================================================
# 🛠️ HELPER: Extrair ID Seguro
# ==============================================================================
def get_uid_str(player_data: dict) -> str:
    """
    Tenta pegar o ID do jogador, seja da estrutura nova (_id) ou antiga (user_id).
    Retorna sempre string.
    """
    if "_id" in player_data:
        return str(player_data["_id"])
    if "user_id" in player_data:
        return str(player_data["user_id"])
    return "unknown"

# ==============================================================================
# 1. PREVIEW (Verificar se pode refinar)
# ==============================================================================
def preview_refine(recipe_id: str, player_data: dict) -> dict | None:
    rec = game_data.REFINING_RECIPES.get(recipe_id)
    if not rec: return None

    # Verifica Inventário
    inv = player_data.get("inventory", {})
    inputs = rec.get("inputs", {})
    can_craft = True
    
    for item, qty in inputs.items():
        # Suporte híbrido para inventário (int ou dict)
        if isinstance(inv.get(item), dict):
            # Itens únicos não empilham da mesma forma, mas para refino geralmente é qtd simples
            can_craft = False # Refino geralmente usa materiais simples
        else:
            held = int(inv.get(item, 0) if isinstance(inv.get(item), (int, float, str)) else 0)
            if held < qty:
                can_craft = False
                break
                
    # Verifica Nível Profissão
    prof = player_data.get("profession", {})
    # Suporte a múltiplas profissões na receita
    allowed = rec.get("profession")
    if isinstance(allowed, str): allowed = [allowed]
    
    my_prof = prof.get("type", "none")
    my_lvl = int(prof.get("level", 1))
    
    prof_ok = (not allowed) or (my_prof in allowed)
    lvl_ok = my_lvl >= rec.get("level_req", 1)
    
    # Cálculo de Tempo (Bônus de Nível reduz tempo)
    base_time = rec.get("time_seconds", 60)
    # Ex: Reduz 1% por nível
    reduction = min(0.5, (my_lvl * 0.01)) 
    final_time = int(base_time * (1.0 - reduction))

    return {
        "can_refine": (can_craft and prof_ok and lvl_ok),
        "inputs": inputs,
        "outputs": rec.get("outputs", {}),
        "duration_seconds": final_time,
        "missing_req": [] # Poderia detalhar o que falta
    }

def get_max_refine_quantity(player_data: dict, recipe: dict) -> int:
    """Calcula quantos itens dá para fazer com os materiais atuais."""
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
    """
    Consome itens e define o estado do jogador como 'refining'.
    Retorna Dict com dados do job ou String com erro.
    """
    # 1. Validações
    prev = preview_refine(recipe_id, player_data)
    if not prev: return "Receita inválida."
    if not prev["can_refine"]: return "Materiais ou nível insuficientes."
    
    # 2. Consumir Materiais
    inputs = prev["inputs"]
    for item, qty in inputs.items():
        if not player_manager.consume_item(player_data, item, qty):
            return f"Erro ao consumir {item}."

    # 3. Definir Estado (Travamento)
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
    
    # 4. Salvar (Usando o ID correto via helper)
    uid_str = get_uid_str(player_data)
    await player_manager.save_player_data(uid_str, player_data)
    
    return {
        "success": True,
        "duration_seconds": duration,
        "finish_time": finish_time
    }

async def start_batch_refine(player_data: dict, recipe_id: str, quantity: int) -> dict | str:
    """Refino em lote (Processa X vezes o tempo e custo)."""
    rec = game_data.REFINING_RECIPES.get(recipe_id)
    if not rec: return "Receita inválida."
    
    # Valida quantidade real
    real_max = get_max_refine_quantity(player_data, rec)
    if quantity > real_max: quantity = real_max
    if quantity < 1: return "Materiais insuficientes."

    # Consome
    inputs = rec.get("inputs", {})
    for item, req in inputs.items():
        total_need = req * quantity
        player_manager.consume_item(player_data, item, total_need)

    # Tempo e XP (Lote tem penalidade de XP por ser 'afk')
    base_time = rec.get("time_seconds", 60)
    total_time = base_time * quantity
    
    base_xp = rec.get("xp_gain", 0)
    # Ex: 50% de XP no modo lote
    total_xp = int((base_xp * quantity) * 0.5) 

    now = datetime.now(timezone.utc)
    finish_time = now + timedelta(seconds=total_time)
    
    player_data["player_state"] = {
        "action": "refining_batch", # Action diferente para diferenciar
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
    """
    Chamado pelo Job quando o tempo acaba.
    Verifica estado, entrega itens e XP, destrava jogador.
    """
    state = player_data.get("player_state", {})
    action = state.get("action")
    
    if action not in ("refining", "refining_batch"):
        return None # Já foi finalizado ou cancelado

    details = state.get("details", {})
    rid = details.get("recipe_id")
    qty = details.get("quantity", 1) # Se for single, qty é None ou 1
    
    rec = game_data.REFINING_RECIPES.get(rid)
    if not rec:
        # Destrava para não bugar
        player_data["player_state"] = {"action": "idle"}
        uid_str = get_uid_str(player_data)
        await player_manager.save_player_data(uid_str, player_data)
        return "Erro: Receita não existe mais."

    # Entregar Itens
    outputs = rec.get("outputs", {})
    final_outputs = {}
    
    for item, base_amt in outputs.items():
        total_amt = base_amt * qty
        player_manager.add_item_to_inventory(player_data, item, total_amt)
        final_outputs[item] = total_amt

    # XP Profissão
    xp_gain = details.get("xp_gain") or details.get("xp_reward") or rec.get("xp_gain", 0)
    # Se for single refine, o XP não estava somado no details, pega da receita
    if action == "refining": 
        xp_gain = rec.get("xp_gain", 0)
    
    prof = player_data.get("profession", {})
    prof["xp"] = int(prof.get("xp", 0)) + int(xp_gain)
    
    # Upa nível (lógica simples)
    cur_lvl = int(prof.get("level", 1))
    req = cur_lvl * 100
    if prof["xp"] >= req:
        prof["xp"] -= req
        prof["level"] = cur_lvl + 1
    
    player_data["profession"] = prof
    
    # Limpa Estado
    player_data["player_state"] = {"action": "idle"}
    
    # Salva
    uid_str = get_uid_str(player_data)
    await player_manager.save_player_data(uid_str, player_data)
    
    return {
        "success": True,
        "outputs": final_outputs,
        "xp_gained": xp_gain
    }