# Ficheiro: modules/dismantle_engine.py (VERSÃO CORRIGIDA)

from typing import Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from modules import player_manager, game_data, crafting_registry

# Define o tempo padrão para a desmontagem (ex: 3 minutos)
# Você pode mover isto para um ficheiro de configuração se quiser
DISMANTLE_TIME_SECONDS = 3 * 60

def start_dismantle(user_id: int, unique_item_id: str) -> Dict[str, Any] | str:
    """
    Inicia o processo de desmontagem. Valida a ação, remove o item
    e define o estado do jogador. Retorna um dicionário com os detalhes 
    do job ou uma string de erro.
    """
    player_data = player_manager.get_player_data(user_id)
    if not player_data:
        return "Jogador não encontrado."

    # --- Verificações de Segurança ---
    inventory = player_data.get("inventory", {})
    item_to_dismantle = inventory.get(unique_item_id)
    if not isinstance(item_to_dismantle, dict):
        return "O item já não se encontra no seu inventário."
    
    equipped_uids = {v for k, v in player_data.get("equipment", {}).items()}
    if unique_item_id in equipped_uids:
        return "Você não pode desmontar um item que está equipado."

    # Não há verificações de profissão ou nível, qualquer jogador pode desmontar.
    
    # --- Lógica para obter o nome do item de forma robusta ---
    base_id = item_to_dismantle.get("base_id")
    if not base_id:
        return "Item inválido, sem base_id." # Segurança extra
        
    item_info = (game_data.ITEMS_DATA or {}).get(base_id, {})
    item_name = item_to_dismantle.get("display_name") or item_info.get("display_name", base_id)

    # --- Inicia a Ação ---
    # 1. Remove o item imediatamente do inventário em memória
    del inventory[unique_item_id]
    
    # 2. Define o estado do jogador como 'dismantling' com todos os detalhes
    finish_time = datetime.now(timezone.utc) + timedelta(seconds=DISMANTLE_TIME_SECONDS)
    player_data["player_state"] = {
        "action": "dismantling",
        "finish_time": finish_time.isoformat(),
        "details": {
            "unique_item_id": unique_item_id,
            "base_id": base_id,
            "item_name": item_name # Salva o nome para a notificação final
        }
    }
    
    # 3. Salva todas as alterações (item removido e novo estado) no disco
    player_manager.save_player_data(user_id, player_data)
    
    # 4. Retorna os detalhes para a interface (handler)
    return {
        "duration_seconds": DISMANTLE_TIME_SECONDS,
        "item_name": item_name,
        "base_id": base_id  # <-- ADICIONE ESTA LINHA
    }

def finish_dismantle(user_id: int, details: dict) -> tuple[str, dict] | str:
    """
    Finaliza a desmontagem, calcula e entrega os materiais.
    (VERSÃO COM CÓDIGO DE DIAGNÓSTICO)
    """
    player_data = player_manager.get_player_data(user_id)
    if not player_data:
        return "Jogador não encontrado ao finalizar a desmontagem."

    player_data["player_state"] = {"action": "idle"}
    
    base_id = details.get("base_id")
    item_name = details.get("item_name", "O item")

    # =======================================================
    # ## INÍCIO DO CÓDIGO DE DIAGNÓSTICO ##
    # =======================================================
    print("\n\n--- DEBUG DA DESMONTAGEM ---")
    print(f"[*] A desmontagem está a procurar por uma receita que produza o item com base_id: '{base_id}'")
    
    # Usamos a função all_recipes() do seu registo para ver o que está na memória
    receitas_carregadas = crafting_registry.all_recipes()
    
    if not receitas_carregadas:
        print("[!] ATENÇÃO: Nenhuma receita foi encontrada no crafting_registry!")
    else:
        print("[*] IDs dos itens que o bot consegue produzir (e portanto desmontar):")
        ids_conhecidos = set()
        for receita_data in receitas_carregadas.values():
            id_resultado = receita_data.get("result_base_id")
            if id_resultado:
                ids_conhecidos.add(id_resultado)
        
        for item_id in sorted(list(ids_conhecidos)):
             print(f"    - '{item_id}'")

    print("----------------------------\n\n")
    # =======================================================
    # ## FIM DO CÓDIGO DE DIAGNÓSTICO ##
    # =======================================================
    
    original_recipe = crafting_registry.get_recipe_by_item_id(base_id)
    if not original_recipe:
        player_manager.save_player_data(user_id, player_data)
        # O erro que você está a ver vem daqui
        return f"Não foi possível encontrar a receita original para {item_name}."

    # (O resto da sua lógica de desmontagem continua aqui)
    ITENS_NAO_RETORNAVEIS = {"nucleo_forja_fraco"}
    returned_materials = {}
    original_inputs = original_recipe.get("inputs", {})
    for material_id, needed_qty in original_inputs.items():
        if material_id in ITENS_NAO_RETORNAVEIS:
            continue
        return_qty = needed_qty // 2
        if return_qty == 0 and needed_qty > 0:
            return_qty = 1
        if return_qty > 0:
            returned_materials[material_id] = return_qty
            player_manager.add_item_to_inventory(player_data, material_id, return_qty)
    
    player_manager.save_player_data(user_id, player_data)
    
    return item_name, returned_materials
