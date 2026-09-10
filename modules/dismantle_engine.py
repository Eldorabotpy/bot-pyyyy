import math
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from modules import player_manager, crafting_registry, profession_engine

# --- CONFIGURAÇÕES ---
# Tempo em segundos POR ITEM. (3 minutos)
TIME_PER_ITEM_SECONDS = 3 * 60 

# Itens que nunca devem ser devolvidos (consumíveis de crafting)
BLACKLIST_MATERIALS = {
    "nucleo_forja_fraco",
    "nucleo_de_forja",
    "carvao",
    "martelo_gasto",
    "fluxo_solda"
}

# --- HELPERS (Lógica Matemática) ---

def calculate_rarity_fallback(rarity: str) -> Dict[str, int]:
    """Retorna materiais genéricos caso o item não tenha receita."""
    tabela = {
        "comum": {"po_de_ferro": 2},
        "incomum": {"po_de_ferro": 4, "couro_tratado": 1},
        "raro": {"cristal_bruto": 1, "po_de_ferro": 5},
        "epico": {"essencia_magica": 1},
        "lendario": {"alma_do_dragao": 1}
    }
    return tabela.get(rarity.lower(), {"sucata": 1})

def calculate_recipe_return(base_id: str, qty_dismantled: int = 1, item_rarity: str = "comum") -> Dict[str, int]:
    """
    Calcula os materiais devolvidos baseando-se na RECEITA ORIGINAL.
    Usa math.ceil para arredondar para cima (50% de 1 = 1).
    """
    returned_materials = {}
    
    # 1. Tenta pegar a receita
    recipe = crafting_registry.get_recipe_by_item_id(base_id)
    
    # CENÁRIO A: Tem Receita
    if recipe:
        inputs = (
            recipe.get("inputs")
            or recipe.get("materials")
            or recipe.get("ingredients")
            or {}
        )

        for mat_id, req_qty in inputs.items():
            if mat_id in BLACKLIST_MATERIALS: 
                continue
            
            # Lógica: 50% do valor, arredondado para CIMA.
            # Ex: Pede 1 -> Devolve 1. Pede 3 -> Devolve 2.
            single_return = math.ceil(req_qty * 0.5)
            
            if single_return > 0:
                returned_materials[mat_id] = single_return * qty_dismantled

    # CENÁRIO B: Não tem receita (Drop) -> Usa Fallback
    else:
        fallback = calculate_rarity_fallback(item_rarity)
        for mat_id, amount in fallback.items():
            returned_materials[mat_id] = amount * qty_dismantled
            
    return returned_materials


# --- FUNÇÕES PRINCIPAIS (ASYNC) ---

async def start_dismantle(player_data: dict, unique_item_id: str) -> Dict[str, Any] | str:
    """
    Inicia o desmonte de UM item específico pelo UID.
    """
    user_id = str(player_data.get("_id") or player_data.get("user_id") or "")

    if not user_id or user_id == "None":
        return "Erro: Player ID não encontrado nos dados."

    inventory = player_data.get("inventory", {}) or {}

    item = inventory.get(unique_item_id)
    if not item or not isinstance(item, dict):
        return "Item não encontrado."

    equipped = set((player_data.get("equipment", {}) or {}).values())

    equipment_tools = player_data.get("equipment_tools", {}) or {}
    if isinstance(equipment_tools, dict):
        equipped.update(equipment_tools.values())

    if unique_item_id in equipped:
        return "Você não pode desmontar um item equipado."

    base_id = item.get("base_id")
    name = item.get("display_name", item.get("nome", "Item"))
    rarity = item.get("rarity", item.get("raridade", "comum"))

    tool_result = profession_engine.validate_and_consume_tool_for_item(
        player_data=player_data,
        item_obj=item,
        fallback_tool_type="ferreiro",
        action_name="desmontar"
    )

    if not tool_result.get("ok"):
        return tool_result.get("error", "Ferramenta inválida para desmontar.")

    del inventory[unique_item_id]
    player_data["inventory"] = inventory

    prof_key_speed = profession_engine.get_profession_key_from_item_for_speed(
        item_inst=item,
        fallback="ferreiro"
    )

    tempo_calc = profession_engine.calculate_profession_work_duration(
        player_data=player_data,
        base_seconds=TIME_PER_ITEM_SECONDS,
        profession_key=prof_key_speed,
        apply_perks=True
    )

    duration = int(tempo_calc.get("duration_seconds", TIME_PER_ITEM_SECONDS))
    finish_time = datetime.now(timezone.utc) + timedelta(seconds=duration)

    player_data["player_state"] = {
        "action": "dismantling",
        "finish_time": finish_time.isoformat(),
        "details": {
            "unique_item_id": unique_item_id,
            "base_id": base_id,
            "item_name": name,
            "rarity": rarity,
            "work_speed": tempo_calc,
            "tool_uid": tool_result.get("tool_uid"),
            "tool_type": tool_result.get("tool_type"),
            "tool_broke": tool_result.get("tool_broke", False)
        }
    }

    await player_manager.save_player_data(user_id, player_data)

    return {
        "success": True,
        "duration_seconds": duration,
        "item_name": name,
        "base_id": base_id,
        "work_speed": tempo_calc,
        "tool_broke": tool_result.get("tool_broke", False),
        "tool_message": tool_result.get("message", "")
    }

async def finish_dismantle(player_data: dict, details: dict) -> tuple[str, dict] | str:
    """
    Finaliza o desmonte SINGLE.
    """
    user_id = str(player_data.get("_id") or player_data.get("user_id") or "")

    if not user_id or user_id == "None":
        return "Erro: Player ID não encontrado ao finalizar desmonte."
    
    base_id = details.get("base_id")
    item_name = details.get("item_name", "Item")
    rarity = details.get("rarity", "comum")
    
    # 1. Calcula Materiais (1 unidade)
    rewards = calculate_recipe_return(base_id, 1, rarity)
    
    # 2. Entrega
    for mat_id, qty in rewards.items():
        player_manager.add_item_to_inventory(player_data, mat_id, qty)
        
    # 3. Limpa Estado
    player_data["player_state"] = {"action": "idle"}
    await player_manager.save_player_data(user_id, player_data)
    
    return item_name, rewards


# --- FUNÇÕES DE LOTE (BATCH / BULK) ---
async def start_batch_dismantle(player_data: dict, base_id_filter: str, rarity_filter: str, qty_requested: int) -> Dict[str, Any] | str:
    """
    Inicia desmonte de MÚLTIPLOS itens iguais.
    Mesmo base_id e mesma raridade.
    """
    user_id = str(player_data.get("_id") or player_data.get("user_id") or "")

    if not user_id or user_id == "None":
        return "Erro: Player ID não encontrado ao iniciar desmonte em lote."

    inventory = player_data.get("inventory", {}) or {}

    equipped = set((player_data.get("equipment", {}) or {}).values())

    equipment_tools = player_data.get("equipment_tools", {}) or {}
    if isinstance(equipment_tools, dict):
        equipped.update(equipment_tools.values())

    candidates = []
    item_reference = None

    for uid, item in inventory.items():
        if not isinstance(item, dict):
            continue

        if uid in equipped:
            continue

        item_rarity = item.get("rarity", item.get("raridade", "comum"))

        if item.get("base_id") == base_id_filter and item_rarity == rarity_filter:
            candidates.append(uid)

            if not item_reference:
                item_reference = item

    if not candidates:
        return "Nenhum item com essa raridade disponível para desmontar."

    try:
        qtd_pedida = int(qty_requested or 1)
    except Exception:
        qtd_pedida = 1

    real_qty = min(qtd_pedida, len(candidates))

    if real_qty < 1:
        return "Quantidade inválida."

    tool_result = None

    for _ in range(real_qty):
        tool_result = profession_engine.validate_and_consume_tool_for_item(
            player_data=player_data,
            item_obj=item_reference,
            fallback_tool_type="ferreiro",
            action_name="desmontar"
        )

        if not tool_result.get("ok"):
            return tool_result.get("error", "Ferramenta inválida para desmontar em lote.")

    uids_to_remove = candidates[:real_qty]

    for uid in uids_to_remove:
        if uid in inventory:
            del inventory[uid]

    player_data["inventory"] = inventory

    base_total_seconds = real_qty * TIME_PER_ITEM_SECONDS

    prof_key_speed = profession_engine.get_profession_key_from_item_for_speed(
        item_inst=item_reference,
        fallback="ferreiro"
    )

    tempo_calc = profession_engine.calculate_profession_work_duration(
        player_data=player_data,
        base_seconds=base_total_seconds,
        profession_key=prof_key_speed,
        apply_perks=True
    )

    total_seconds = int(tempo_calc.get("duration_seconds", base_total_seconds))
    finish_time = datetime.now(timezone.utc) + timedelta(seconds=total_seconds)

    player_data["player_state"] = {
        "action": "dismantling_batch",
        "finish_time": finish_time.isoformat(),
        "details": {
            "base_id": base_id_filter,
            "item_name": item_reference.get("display_name", "Itens"),
            "rarity": rarity_filter,
            "qty_dismantling": real_qty,
            "uids_removed": uids_to_remove,
            "work_speed": tempo_calc,
            "tool_uid": tool_result.get("tool_uid") if tool_result else None,
            "tool_type": tool_result.get("tool_type") if tool_result else None,
            "tool_broke": tool_result.get("tool_broke", False) if tool_result else False
        }
    }

    await player_manager.save_player_data(user_id, player_data)

    return {
        "success": True,
        "duration_seconds": total_seconds,
        "qty": real_qty,
        "item_name": item_reference.get("display_name", "Itens"),
        "work_speed": tempo_calc,
        "tool_broke": tool_result.get("tool_broke", False) if tool_result else False,
        "tool_message": tool_result.get("message", "") if tool_result else ""
    }

async def finish_dismantle_batch(player_data: dict, details: dict) -> tuple[str, dict] | str:
    """
    Finaliza o desmonte BATCH.
    """
    user_id = str(player_data.get("_id") or player_data.get("user_id") or "")

    if not user_id or user_id == "None":
        return "Erro: Player ID não encontrado ao finalizar desmonte em lote."
    
    base_id = details.get("base_id")
    item_name = details.get("item_name", "Itens")
    rarity = details.get("rarity", "comum")
    qty = details.get("qty_dismantling", 1)
    
    # 1. Calcula Materiais (Multiplicado pela Qty)
    rewards = calculate_recipe_return(base_id, qty, rarity)
    
    # 2. Entrega
    for mat_id, amount in rewards.items():
        player_manager.add_item_to_inventory(player_data, mat_id, amount)
        
    # 3. Limpa Estado
    player_data["player_state"] = {"action": "idle"}
    await player_manager.save_player_data(user_id, player_data)
    
    return item_name, rewards