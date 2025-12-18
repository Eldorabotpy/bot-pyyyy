import math
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from modules import player_manager, game_data, crafting_registry

# --- CONFIGURAÇÕES ---
# Tempo em segundos POR ITEM. (3 minutos)
TIME_PER_ITEM_SECONDS = 3 * 60 

# Itens que nunca devem ser devolvidos (consumíveis de crafting)
BLACKLIST_MATERIALS = {"nucleo_forja_fraco", "carvao", "martelo_gasto", "fluxo_solda"}

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
        inputs = recipe.get("inputs", {})
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
    Inicia o desmonte de UM item específico (pelo UID).
    """
    user_id = player_data.get("user_id")
    if not user_id: return "Erro: Player ID não encontrado."

    inventory = player_data.get("inventory", {})
    
    # 1. Validações
    item = inventory.get(unique_item_id)
    if not item: return "Item não encontrado."
    
    equipped = set(player_data.get("equipment", {}).values())
    if unique_item_id in equipped: return "Você não pode desmontar um item equipado."

    # 2. Dados do Item
    base_id = item.get("base_id")
    name = item.get("display_name", "Item")
    rarity = item.get("rarity", "comum")

    # 3. Remove do Inventário
    del inventory[unique_item_id]

    # 4. Define Estado
    finish_time = datetime.now(timezone.utc) + timedelta(seconds=TIME_PER_ITEM_SECONDS)
    
    player_data["player_state"] = {
        "action": "dismantling", # Ação Single
        "finish_time": finish_time.isoformat(),
        "details": {
            "unique_item_id": unique_item_id,
            "base_id": base_id,
            "item_name": name,
            "rarity": rarity
        }
    }

    # 5. Salva
    await player_manager.save_player_data(user_id, player_data)

    return {
        "success": True,
        "duration_seconds": TIME_PER_ITEM_SECONDS,
        "item_name": name,
        "base_id": base_id
    }

async def finish_dismantle(player_data: dict, details: dict) -> tuple[str, dict] | str:
    """
    Finaliza o desmonte SINGLE.
    """
    user_id = player_data.get("user_id")
    
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

async def start_batch_dismantle(player_data: dict, base_id_filter: str, qty_requested: int) -> Dict[str, Any] | str:
    """
    Inicia desmonte de MÚLTIPLOS itens iguais (pelo Base ID).
    Remove os itens e define um tempo acumulativo.
    """
    user_id = player_data.get("user_id")
    inventory = player_data.get("inventory", {})
    equipped = set(player_data.get("equipment", {}).values())

    # 1. Encontrar Candidatos (Pelo Base ID para garantir que são o mesmo item)
    candidates = []
    item_reference = None # Para pegar nome e raridade

    for uid, item in inventory.items():
        # --- CORREÇÃO DE SEGURANÇA ---
        # Pula itens que não são dicionários (como Ouro, Gemas ou lixo de memória)
        if not isinstance(item, dict):
            continue
        # -----------------------------

        if uid in equipped: continue
        
        if item.get("base_id") == base_id_filter:
            candidates.append(uid)
            if not item_reference: item_reference = item

    if not candidates: return "Nenhum item disponível para desmontar."
    
    # Validação extra: se a quantidade pedida for maior que a disponível
    real_qty = min(qty_requested, len(candidates))
    if real_qty < 1: return "Quantidade inválida."
    
    # 2. Seleciona os UIDs para remover
    uids_to_remove = candidates[:real_qty]
    
    # 3. Remove Itens
    for uid in uids_to_remove:
        # Verifica se ainda existe antes de deletar (segurança)
        if uid in inventory:
            del inventory[uid]
        
    # 4. Calcula Tempo Total
    total_seconds = real_qty * TIME_PER_ITEM_SECONDS
    finish_time = datetime.now(timezone.utc) + timedelta(seconds=total_seconds)
    
    # 5. Define Estado Batch
    player_data["player_state"] = {
        "action": "dismantling_batch", # Ação Batch
        "finish_time": finish_time.isoformat(),
        "details": {
            "base_id": base_id_filter,
            "item_name": item_reference.get("display_name", "Itens"),
            "rarity": item_reference.get("rarity", "comum"),
            "qty_dismantling": real_qty,
            "uids_removed": uids_to_remove 
        }
    }

    await player_manager.save_player_data(user_id, player_data)
    
    return {
        "success": True,
        "duration_seconds": total_seconds,
        "qty": real_qty,
        "item_name": item_reference.get("display_name")
    }

async def finish_dismantle_batch(player_data: dict, details: dict) -> tuple[str, dict] | str:
    """
    Finaliza o desmonte BATCH.
    """
    user_id = player_data.get("user_id")
    
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