# modules/refining_engine.py

from datetime import datetime, timedelta, timezone
import logging
from modules import game_data

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

def _get_player_best_profession_for_recipe(player_data: dict, recipe: dict, forced_prof: str = None) -> tuple[str, int]:
    allowed_profs = recipe.get("profession")
    if not allowed_profs: return "none", 1
    if isinstance(allowed_profs, str): allowed_profs = [allowed_profs]
    allowed_profs = [p.lower().strip() for p in allowed_profs]
    
    all_profs = dict(player_data.get("learned_professions", player_data.get("professions", {})))
    all_profs_norm = {k.lower().strip(): v for k, v in all_profs.items()}

    # 🛡️ NOVA REGRA: Se o JavaScript enviou a profissão da aba, NÓS OBEDECEMOS!
    if forced_prof:
        forced = forced_prof.lower().strip()
        if forced in allowed_profs and forced in all_profs_norm:
            return forced, int(all_profs_norm[forced].get("level", 1))

    # Fallback (só se o JS não mandar nada)
    best_prof, best_lvl = "none", 0
    for req_prof in allowed_profs:
        if req_prof in all_profs_norm:
            lvl = int(all_profs_norm[req_prof].get("level", 1))
            if lvl > best_lvl:
                best_lvl, best_prof = lvl, req_prof

    return best_prof, max(1, best_lvl)

def _calculate_single_duration(recipe: dict, player_data: dict, forced_prof: str = None) -> int:
    base_time = recipe.get("time_seconds", 60)
    _, my_lvl = _get_player_best_profession_for_recipe(player_data, recipe, forced_prof)
    
    reduction = min(0.5, (my_lvl * 0.01)) 
    time_after_level = base_time * (1.0 - reduction)
    
    try:
        from modules.player.premium import PremiumManager
        speed_mult = float(PremiumManager(player_data).get_perk_value("refine_speed_multiplier", 1.0))
    except: speed_mult = 1.0

    return max(1, int(time_after_level / max(0.1, speed_mult)))


# ==============================================================================
# 1. PREVIEW
# ==============================================================================
def preview_refine(recipe_id: str, player_data: dict, forced_prof: str = None) -> dict | None:
    rec = game_data.REFINING_RECIPES.get(recipe_id)
    if not rec: return None
    
    inv = player_data.get("inventory", {})
    inputs = rec.get("inputs", {})
    can_craft = True

    for item, qty in inputs.items():
        item_data = inv.get(item, 0)
        if isinstance(item_data, dict):
            held = int(item_data.get("quantity", 0))
        else:
            held = int(item_data)
            
        if held < qty:
            can_craft = False
            break
            
    best_prof, my_lvl = _get_player_best_profession_for_recipe(player_data, rec, forced_prof)
    allowed = rec.get("profession")
    prof_ok = (not allowed) or (best_prof != "none")
    lvl_ok = my_lvl >= rec.get("level_req", 1)
    final_time = _calculate_single_duration(rec, player_data, forced_prof)

    return {
        "can_refine": (can_craft and prof_ok and lvl_ok),
        "inputs": inputs,
        "outputs": rec.get("outputs", {}),
        "duration_seconds": final_time,
        "missing_req": []
    }

# Substitua a função get_max_refine_quantity existente por esta:
def get_max_refine_quantity(player_data: dict, recipe: dict, forced_prof: str = None) -> int:
    if not recipe: return 0
    inv = player_data.get("inventory", {})
    inputs = recipe.get("inputs", {})
    
    max_qty = 9999
    for item, req_qty in inputs.items():
        if req_qty <= 0: continue
        
        item_data = inv.get(item, 0)
        if isinstance(item_data, dict):
            held = int(item_data.get("quantity", 0))
        else:
            held = int(item_data)
            
        can_make = held // req_qty
        if can_make < max_qty:
            max_qty = can_make
            
    inv_limit = max_qty if max_qty != 9999 else 0
    if inv_limit == 0:
        return 0
        
    # 🔴 NOVA REGRA: Extrai o nível e limita a fornalha! Nível 1 = 1 item.
    _, my_lvl = _get_player_best_profession_for_recipe(player_data, recipe, forced_prof)
    return min(inv_limit, max(1, my_lvl))

# ==============================================================================
# 2. START (Iniciar o processo)
# ==============================================================================
async def start_refine(player_data: dict, recipe_id: str) -> dict | str:
    from modules import player_manager
    
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
        if qty <= 0: continue
        ok = player_manager.consume_item(player_data, item_id, qty)
        if not ok:
            return f"Erro ao consumir {item_id}."

    now = datetime.now(timezone.utc)
    duration = max(1, int(prev.get("duration_seconds", 0) or 0))
    finish_time = now + timedelta(seconds=duration)

    rec = game_data.REFINING_RECIPES.get(recipe_id, {}) or {}
    xp_gain = int(rec.get("xp_gain", 0) or 0)
    
    prof_type, _ = _get_player_best_profession_for_recipe(player_data, rec)

    player_data["player_state"] = {
        "action": "refining",
        "started_at": now.isoformat(),
        "finish_time": finish_time.isoformat(),
        "details": {
            "recipe_id": recipe_id,
            "quantity": 1,
            "xp_gain": xp_gain,
            "profession_type": prof_type,
        }
    }

    uid_str = get_uid_str(player_data)
    await player_manager.save_player_data(uid_str, player_data)

    return {
        "success": True,
        "duration_seconds": duration,
        "finish_time": finish_time.isoformat()
    }


async def start_batch_refine(player_data: dict, recipe_id: str, quantity: int, forced_prof: str = None) -> dict | str:
    from modules import player_manager
    
    rec = game_data.REFINING_RECIPES.get(recipe_id)
    if not rec: 
        return "Receita inválida."

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        quantity = 0

    real_max = get_max_refine_quantity(player_data, rec, forced_prof)
    if quantity > real_max: quantity = real_max
    if quantity < 1: return "Materiais insuficientes."

    inputs = rec.get("inputs", {}) or {}
    consumo_map = {}
    
    for item_id, req in inputs.items():
        consumo_map[item_id] = int(req) * quantity

    for item_id, total_need in consumo_map.items():
        ok = player_manager.consume_item(player_data, item_id, total_need)
        if not ok:
            return f"Erro ao consumir {total_need} de {item_id}."

    # 👇 CORREÇÃO: Passa a profissão forçada da UI para calcular o tempo correto
    unit_time = _calculate_single_duration(rec, player_data, forced_prof)
    total_time = max(1, int(unit_time) * quantity)

    # 🔴 CORREÇÃO DO LOTE: Removida a punição de * 0.5 que zerava a XP!
    base_xp = int(rec.get("xp_gain", 0) or 0)
    total_xp = max(0, int(base_xp * quantity))

    now = datetime.now(timezone.utc)
    finish_time = now + timedelta(seconds=total_time)

    # 👇 CORREÇÃO: Pega a profissão exata selecionada para salvar na memória
    prof_type, _ = _get_player_best_profession_for_recipe(player_data, rec, forced_prof)

    player_data["player_state"] = {
        "action": "refining_batch",
        "started_at": now.isoformat(),
        "finish_time": finish_time.isoformat(),
        "details": {
            "recipe_id": recipe_id,
            "quantity": quantity,
            "xp_gain": total_xp,
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
# 3. FINISH (Entregar recompensas e XP blindada)
# ==============================================================================
async def finish_refine(player_data: dict) -> dict | str | None:
    from modules import player_manager

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

    # Pegar a receita 
    from modules import game_data
    rec = game_data.REFINING_RECIPES.get(rid)
    
    if not rec:
        player_data["player_state"] = {"action": "idle"}
        uid_str = get_uid_str(player_data)
        await player_manager.save_player_data(uid_str, player_data)
        return "Erro: Receita não existe mais."

    # 1) Entrega outputs para o inventário
    outputs = rec.get("outputs", {}) or {}
    final_outputs = {}

    for item_id, base_amt in outputs.items():
        try:
            base_amt = int(base_amt or 0)
        except Exception:
            base_amt = 0

        total_amt = max(0, base_amt * qty)
        if total_amt <= 0: continue
        player_manager.add_item_to_inventory(player_data, item_id, total_amt)
        final_outputs[item_id] = total_amt

    # 2) Calcula XP
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

    expected_type = (
        (details.get("profession_type") or "").strip().lower()
        or (rec.get("profession_type") or "").strip().lower()
        or None
    )

    xp_info = {"xp_added": 0}
    
    if xp_gain > 0:
        # Tenta usar o sistema do xp.py
        try:
            from modules.game_data.xp import add_profession_xp_inplace
            xp_info = add_profession_xp_inplace(
                player_data,
                amount=int(xp_gain),
                expected_type=expected_type,
            )
        except Exception:
            pass
            
        # 🛡️ SINCRONIZAÇÃO FORÇADA ABSOLUTA 🛡️
        # Não importa se o xp.py falhou ou se usou a gaveta errada.
        # Nós vamos forçar o salvamento na mochila correta AGORA.
        if expected_type:
            learned = player_data.get("learned_professions", {})
            chave_real = None
            
            # Encontra a chave exata
            for k in learned.keys():
                if k.lower().strip() == expected_type:
                    chave_real = k
                    break
                    
            if not chave_real and "profession" in player_data:
                leg = player_data.get("profession", {})
                if str(leg.get("type", "")).lower() == expected_type or str(leg.get("key", "")).lower() == expected_type:
                    chave_real = expected_type
                    learned[chave_real] = leg
                    
            if chave_real:
                prof_data = learned[chave_real]
                legado = player_data.get("profession", {})
                
                is_legacy_matching = (str(legado.get("type", "")).lower() == expected_type or str(legado.get("key", "")).lower() == expected_type)
                
                # Pega o nível e XP atuais comparando as duas gavetas
                lvl_atual = int(prof_data.get("level", 1))
                xp_atual = int(prof_data.get("xp", 0))
                
                if is_legacy_matching:
                    if int(legado.get("level", 1)) > lvl_atual:
                        lvl_atual = int(legado.get("level", 1))
                    if int(legado.get("xp", 0)) > xp_atual:
                        xp_atual = int(legado.get("xp", 0))
                
                # Soma a XP se o sistema falhou em reportar!
                if xp_info.get("xp_added", 0) <= 0:
                    xp_atual += int(xp_gain)
                    xp_info["xp_added"] = int(xp_gain)
                    
                # Roda a tabela de Level Up na unha!
                while True:
                    need = 40 + (25 * (lvl_atual - 1)) + (8 * ((lvl_atual - 1) ** 2))
                    if xp_atual >= need:
                        xp_atual -= int(need)
                        lvl_atual += 1
                    else:
                        break
                        
                prof_data["xp"] = xp_atual
                prof_data["level"] = lvl_atual
                
                # FORÇA SALVAR NAS DUAS GAVETAS PARA FALAREM A MESMA LÍNGUA!
                learned[chave_real] = prof_data
                player_data["learned_professions"] = learned
                
                if is_legacy_matching:
                    player_data["profession"] = prof_data

    # 3) Finaliza estado e salva
    player_data["player_state"] = {"action": "idle"}
    uid_str = get_uid_str(player_data)
    await player_manager.save_player_data(uid_str, player_data)

    return {
        "success": True,
        "outputs": final_outputs,
        "xp_gained": int(xp_gain),
        "xp_reward": int(xp_gain), # JS vai ler isto
        "xp_info": xp_info,
        "quantity": qty,
        "recipe_id": rid,
    }