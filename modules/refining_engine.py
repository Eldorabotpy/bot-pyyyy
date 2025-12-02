# modules/refining_engine.py

from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from modules.player.premium import PremiumManager
from modules import player_manager, game_data


# ----------------------- helpers -----------------------

def _seconds_with_perks(player_data: dict, base_seconds: int) -> int:
    """
    Aplica o multiplicador de velocidade de refino do premium.
    """
    
    premium = PremiumManager(player_data)
    mult = float(premium.get_perk_value('refine_speed_multiplier', 1.0))
    if mult <= 0:
        return 0
    mult = max(0.25, min(4.0, mult))
    
    final_seconds = base_seconds / mult
    return max(1, int(final_seconds))

def _norm_profession(pdata: dict) -> Tuple[Optional[str], int]:
    """
    Normaliza a profissão ativa do jogador.
    """
    raw = (pdata or {}).get("profession")
    if not raw: return (None, 0)
    if isinstance(raw, str): return (raw, 1)
    if isinstance(raw, dict):
        if "type" in raw:
            return (raw.get("type") or None, int(raw.get("level", 1)))
        for k, v in raw.items():
            if isinstance(v, dict):
                return (k, int(v.get("level", 1)))
            return (k, 1)
    return (None, 0)

def _is_crafting_profession(prof_type: Optional[str]) -> bool:
    """
    Verdadeiro se a profissão está cadastrada como category == 'crafting'.
    """
    if not prof_type: return False
    meta = game_data.PROFESSIONS_DATA.get(prof_type, {})
    return (meta.get("category") == "crafting")

def _has_materials(player_data: dict, inputs: dict) -> bool:
    inv = player_data.get("inventory", {}) or {}
    return all(int(inv.get(k, 0)) >= int(v) for k, v in (inputs or {}).items())

def _consume_materials(player_data: dict, inputs: dict) -> None:
    for item_id, qty in (inputs or {}).items():
        player_manager.remove_item_from_inventory(player_data, item_id, int(qty))

# ------------------- API principal -------------------

def preview_refine(recipe_id: str, player_data: dict) -> dict | None:
    """(Esta função permanece síncrona, o que está correto)"""
    rec = game_data.REFINING_RECIPES.get(recipe_id)
    if not rec: return None

    prof_type, prof_lvl = _norm_profession(player_data)
    meets_prof = _is_crafting_profession(prof_type) and (prof_lvl >= int(rec.get("level_req", 1)))
    has_mats   = _has_materials(player_data, rec.get("inputs", {}))
    duration   = _seconds_with_perks(player_data, int(rec.get("time_seconds", 60)))

    return {
        "can_refine": bool(meets_prof and has_mats),
        "duration_seconds": duration,
        "inputs": dict(rec.get("inputs", {})),
        "outputs": dict(rec.get("outputs", {})),
    }

async def start_refine(pdata: dict, recipe_id: str) -> dict | str:
    """
    Inicia o refino, modificando 'pdata' e salvando-o.
    Agora é 'async' e recebe 'pdata' diretamente.
    """
    rec = game_data.REFINING_RECIPES.get(recipe_id)

    if not pdata or not rec:
        return "Receita de refino inválida."

    prof_type, prof_lvl = _norm_profession(pdata)
    if not _is_crafting_profession(prof_type):
        return "Você precisa ter uma profissão de criação para refinar."
    if prof_lvl < int(rec.get("level_req", 1)):
        return "Nível de profissão insuficiente para esta receita."
    if not _has_materials(pdata, rec.get("inputs", {})):
        return "Materiais insuficientes."

    duration = _seconds_with_perks(pdata, int(rec.get("time_seconds", 60)))
    _consume_materials(pdata, rec.get("inputs", {}))

    finish_dt = datetime.now(timezone.utc) + timedelta(seconds=duration)
    pdata["player_state"] = {
        "action": "refining",
        "finish_time": finish_dt.isoformat(),
        "details": {"recipe_id": recipe_id},
    }
    
    user_id = pdata.get("user_id")
    if user_id:
        await player_manager.save_player_data(user_id, pdata)
    else:
        return "Erro: user_id não encontrado em pdata."


    return {"duration_seconds": duration, "finish_time": finish_dt.isoformat()}

async def start_refine(pdata: dict, recipe_id: str) -> dict | str:
    """
    Inicia o refino, modificando 'pdata' e salvando-o.
    Agora é 'async' e recebe 'pdata' diretamente.
    """
    rec = game_data.REFINING_RECIPES.get(recipe_id)

    if not pdata or not rec:
        return "Receita de refino inválida."

    prof_type, prof_lvl = _norm_profession(pdata)
    if not _is_crafting_profession(prof_type):
        return "Você precisa ter uma profissão de criação para refinar."
    if prof_lvl < int(rec.get("level_req", 1)):
        return "Nível de profissão insuficiente para esta receita."
    if not _has_materials(pdata, rec.get("inputs", {})):
        return "Materiais insuficientes."

    duration = _seconds_with_perks(pdata, int(rec.get("time_seconds", 60)))
    _consume_materials(pdata, rec.get("inputs", {}))

    finish_dt = datetime.now(timezone.utc) + timedelta(seconds=duration)
    pdata["player_state"] = {
        "action": "refining",
        "finish_time": finish_dt.isoformat(),
        "details": {"recipe_id": recipe_id},
    }
    
    # <<< CORREÇÃO 2: Adiciona 'await' (e usa o user_id de 'pdata') >>>
    user_id = pdata.get("user_id")
    if user_id:
        await player_manager.save_player_data(user_id, pdata)
    else:
        return "Erro: user_id não encontrado em pdata."


    return {"duration_seconds": duration, "finish_time": finish_dt.isoformat()}


# Em: modules/refining_engine.py

async def finish_refine(pdata: dict) -> dict | str:
    """
    Finaliza o refino, modificando 'pdata' e salvando-o.
    Agora é 'async' e recebe 'pdata' diretamente.
    (VERSÃO CORRIGIDA COM RETORNO DE XP)
    """
    if not pdata: return "Jogador não encontrado."

    state = pdata.get("player_state", {}) or {}
    if state.get("action") != "refining":
        return {} # Já finalizado, não faz nada

    rid = (pdata.get("player_state", {}).get("details") or {}).get("recipe_id")
    rec = game_data.REFINING_RECIPES.get(rid)
    user_id = pdata.get("user_id") 
    
    if not user_id:
        return "Erro fatal: user_id não encontrado em pdata ao finalizar."

    if not rec:
        pdata["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(user_id, pdata)
        return "Receita não encontrada ao concluir."

    # Entrega os itens
    for item_id, qty in (rec.get("outputs", {}) or {}).items():
        player_manager.add_item_to_inventory(pdata, item_id, int(qty))

    # Calcula e aplica o XP
    xp_gained = 0 # Valor padrão
    prof_type, prof_lvl = _norm_profession(pdata)
    
    if _is_crafting_profession(prof_type):
        xp_gained = int(rec.get("xp_gain", 1)) # Pega o XP da receita
        
        prof = pdata.get("profession", {}) or {}
        prof["type"]  = prof_type
        prof["level"] = int(prof.get("level", prof_lvl or 1))
        prof["xp"]    = int(prof.get("xp", 0)) + xp_gained

        # Lógica de Level Up da Profissão
        cur = int(prof.get("level", 1))
        while True:
            need = int(game_data.get_xp_for_next_collection_level(cur))
            if need <= 0 or prof["xp"] < need: break
            prof["xp"] -= need
            cur += 1
            prof["level"] = cur
        
        pdata["profession"] = prof

    pdata["player_state"] = {"action": "idle"}
    await player_manager.save_player_data(user_id, pdata)

    # Retorna o resultado com XP
    return {
        "status": "success", 
        "outputs": dict(rec.get("outputs", {})),
        "xp_gained": xp_gained # <-- ADICIONADO
    }# modules/refining_engine.py

from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
# REMOVIDO: from modules.player.premium import PremiumManager (Usaremos player_manager direto)
from modules import player_manager, game_data

# ----------------------- helpers -----------------------

def _seconds_with_perks(player_data: dict, base_seconds: int) -> int:
    """
    Aplica o multiplicador de velocidade de refino usando get_perk_value do player_manager.
    Seguro e consistente com a forja.
    """
    # Busca o valor de forma segura (síncrona)
    # Tenta 'refine_speed_multiplier' primeiro
    mult_raw = player_manager.get_perk_value(player_data, 'refine_speed_multiplier', None)
    
    if mult_raw is None:
        # Fallback para 'craft_speed_multiplier' se não houver específico de refino
        mult_raw = player_manager.get_perk_value(player_data, 'craft_speed_multiplier', 1.0)
        
    try:
        mult = float(mult_raw)
    except (ValueError, TypeError):
        mult = 1.0

    if mult <= 0:
        mult = 0.1 # Evita divisão por zero
        
    mult = max(0.25, min(4.0, mult))
    
    final_seconds = base_seconds / mult
    return max(1, int(final_seconds))

def _norm_profession(pdata: dict) -> Tuple[Optional[str], int]:
    """
    Normaliza a profissão ativa do jogador.
    """
    raw = (pdata or {}).get("profession")
    if not raw: return (None, 0)
    if isinstance(raw, str): return (raw, 1)
    if isinstance(raw, dict):
        if "type" in raw:
            return (raw.get("type") or None, int(raw.get("level", 1)))
        for k, v in raw.items():
            if isinstance(v, dict):
                return (k, int(v.get("level", 1)))
            return (k, 1)
    return (None, 0)

def _is_crafting_profession(prof_type: Optional[str]) -> bool:
    """
    Verdadeiro se a profissão está cadastrada como category == 'crafting'.
    """
    if not prof_type: return False
    meta = game_data.PROFESSIONS_DATA.get(prof_type, {})
    return (meta.get("category") == "crafting")

def _has_materials(player_data: dict, inputs: dict) -> bool:
    inv = player_data.get("inventory", {}) or {}
    return all(int(inv.get(k, 0)) >= int(v) for k, v in (inputs or {}).items())

def _consume_materials(player_data: dict, inputs: dict) -> None:
    for item_id, qty in (inputs or {}).items():
        player_manager.remove_item_from_inventory(player_data, item_id, int(qty))

# ------------------- API principal -------------------

def preview_refine(recipe_id: str, player_data: dict) -> dict | None:
    """(Esta função permanece síncrona, o que está correto)"""
    rec = game_data.REFINING_RECIPES.get(recipe_id)
    if not rec: return None

    prof_type, prof_lvl = _norm_profession(player_data)
    meets_prof = _is_crafting_profession(prof_type) and (prof_lvl >= int(rec.get("level_req", 1)))
    has_mats   = _has_materials(player_data, rec.get("inputs", {}))
    duration   = _seconds_with_perks(player_data, int(rec.get("time_seconds", 60)))

    return {
        "can_refine": bool(meets_prof and has_mats),
        "duration_seconds": duration,
        "inputs": dict(rec.get("inputs", {})),
        "outputs": dict(rec.get("outputs", {})),
    }

async def start_refine(pdata: dict, recipe_id: str) -> dict | str:
    """
    Inicia o refino, modificando 'pdata' e salvando-o.
    Agora é 'async' e recebe 'pdata' diretamente.
    """
    rec = game_data.REFINING_RECIPES.get(recipe_id)

    if not pdata or not rec:
        return "Receita de refino inválida."

    prof_type, prof_lvl = _norm_profession(pdata)
    if not _is_crafting_profession(prof_type):
        return "Você precisa ter uma profissão de criação para refinar."
    if prof_lvl < int(rec.get("level_req", 1)):
        return "Nível de profissão insuficiente para esta receita."
    if not _has_materials(pdata, rec.get("inputs", {})):
        return "Materiais insuficientes."

    duration = _seconds_with_perks(pdata, int(rec.get("time_seconds", 60)))
    _consume_materials(pdata, rec.get("inputs", {}))

    finish_dt = datetime.now(timezone.utc) + timedelta(seconds=duration)
    pdata["player_state"] = {
        "action": "refining",
        "finish_time": finish_dt.isoformat(),
        "details": {"recipe_id": recipe_id},
    }
    
    user_id = pdata.get("user_id")
    if user_id:
        await player_manager.save_player_data(user_id, pdata)
    else:
        return "Erro: user_id não encontrado em pdata."

    return {"duration_seconds": duration, "finish_time": finish_dt.isoformat()}

async def finish_refine(pdata: dict) -> dict | str:
    """
    Finaliza o refino, modificando 'pdata' e salvando-o.
    Agora é 'async' e recebe 'pdata' diretamente.
    """
    if not pdata: return "Jogador não encontrado."

    state = pdata.get("player_state", {}) or {}
    if state.get("action") != "refining":
        return {} # Já finalizado, não faz nada

    rid = (pdata.get("player_state", {}).get("details") or {}).get("recipe_id")
    rec = game_data.REFINING_RECIPES.get(rid)
    user_id = pdata.get("user_id") # Pega o user_id para salvar
    
    if not user_id:
        return "Erro fatal: user_id não encontrado em pdata ao finalizar."

    if not rec:
        pdata["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(user_id, pdata)
        return "Receita não encontrada ao concluir."

    for item_id, qty in (rec.get("outputs", {}) or {}).items():
        player_manager.add_item_to_inventory(pdata, item_id, int(qty))

    prof_type, prof_lvl = _norm_profession(pdata)
    if _is_crafting_profession(prof_type):
        prof = pdata.get("profession", {}) or {}
        prof["type"]  = prof_type
        prof["level"] = int(prof.get("level", prof_lvl or 1))
        prof["xp"]    = int(prof.get("xp", 0)) + int(rec.get("xp_gain", 1))

        cur = int(prof.get("level", 1))
        while True:
            try:
                # Tenta buscar XP necessária, se falhar assume valor alto pra evitar loop
                need = int(game_data.get_xp_for_next_collection_level(cur))
            except Exception:
                need = 999999
                
            if need <= 0 or prof["xp"] < need: break
            prof["xp"] -= need
            cur += 1
            prof["level"] = cur
        
        pdata["profession"] = prof

    pdata["player_state"] = {"action": "idle"}
    await player_manager.save_player_data(user_id, pdata)

    return {"status": "success", "outputs": dict(rec.get("outputs", {}))}