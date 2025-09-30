# modules/dungeon_manager.py (VERSÃO CORRIGIDA E FINAL)

import json
import os
import random
from modules import game_data, dungeon_definitions, party_manager # Adicionado party_manager

DIRETORIO_MASMORRAS = "dungeons"

def _garantir_que_diretorio_exista():
    """Garante que o diretório 'dungeons' exista."""
    os.makedirs(DIRETORIO_MASMORRAS, exist_ok=True)

def pegar_instancia_masmorra(id_da_instancia: str):
    """Busca os dados de uma instância de masmorra ativa pelo seu ID (que será o party_id)."""
    _garantir_que_diretorio_exista()
    caminho_arquivo = os.path.join(DIRETORIO_MASMORRAS, f"{id_da_instancia}.json")
    if not os.path.exists(caminho_arquivo):
        return None
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None

def salvar_instancia_masmorra(id_da_instancia: str, dados_da_masmorra: dict):
    """Salva os dados de uma instância de masmorra ativa."""
    _garantir_que_diretorio_exista()
    caminho_arquivo = os.path.join(DIRETORIO_MASMORRAS, f"{id_da_instancia}.json")
    with open(caminho_arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados_da_masmorra, f, indent=4, ensure_ascii=False)

def deletar_instancia_masmorra(id_da_instancia: str):
    """Apaga o arquivo de uma instância de masmorra (ex: ao finalizá-la)."""
    _garantir_que_diretorio_exista()
    caminho_arquivo = os.path.join(DIRETORIO_MASMORRAS, f"{id_da_instancia}.json")
    if os.path.exists(caminho_arquivo):
        os.remove(caminho_arquivo)

# =====================================================================
# AQUI ESTÁ A CORREÇÃO PRINCIPAL
# =====================================================================
# Em modules/dungeon_manager.py

def criar_instancia_masmorra(dungeon_id: str, party_id: str) -> dict | None:
    """Cria uma nova instância de masmorra para um grupo, usando o party_id como chave."""
    # --- DEBUG PRINTS PARA A CRIAÇÃO DA SALA ---
    print("\n\n--- [DEBUG] Tentando criar instância da dungeon ---")
    print(f"--- [DEBUG] ID da Dungeon recebido: {dungeon_id}")
    print(f"--- [DEBUG] ID do Grupo recebido: {party_id}")
    # -----------------------------------------------

    party_data = party_manager.get_party_data(party_id)
    dungeon_template = dungeon_definitions.DUNGEONS.get(dungeon_id)

    # --- DEBUG PRINTS PARA VERIFICAR OS DADOS ---
    if not party_data:
        print("--- [DEBUG] FALHA: Não foi possível encontrar os dados do grupo (party_data is None).")
    else:
        print("--- [DEBUG] SUCESSO: Dados do grupo encontrados.")

    if not dungeon_template:
        print(f"--- [DEBUG] FALHA: Não foi possível encontrar o modelo da dungeon com o ID '{dungeon_id}'.")
    else:
        print("--- [DEBUG] SUCESSO: Modelo da dungeon encontrado.")
    # --------------------------------------------
    
    if not dungeon_template or not party_data:
        print("--- [DEBUG] A criação da instância foi cancelada por falta de dados.")
        return None

    # (O resto da função continua igual)
    current_floor_str = str(party_data.get('dungeon_floor', 1))
    monster_definitions_for_floor = dungeon_template['floors'][current_floor_str]['monsters']
    
    combat_monsters = {}
    monster_counter = 1
    for monster_group in monster_definitions_for_floor:
        base_id = monster_group['base_id']
        quantity = monster_group['quantity']
        
        all_monster_templates = game_data.MONSTERS_DATA.get(dungeon_id, [])
        monster_template = next((m for m in all_monster_templates if m.get('id') == base_id), None)

        if monster_template:
            for _ in range(quantity):
                unique_monster_key = f"monster_{monster_counter}"
                combat_monsters[unique_monster_key] = {
                    "base_id": base_id, "name": monster_template.get('display_name', 'Monstro'),
                    "hp": monster_template.get('hp', 10), "max_hp": monster_template.get('hp', 10),
                    "attack": monster_template.get('attack', 1), "defense": monster_template.get('defense', 0)
                }
                monster_counter += 1

    instance_id = party_id
    new_instance = {
        "id": instance_id, "dungeon_id": dungeon_id, "party_id": party_id, "current_floor": 1,
        "combat_state": {
            "active": True, "monsters": combat_monsters, "participants": {},
            "turn_order": [], "current_turn_index": 0, "battle_log": []
        },
        "player_messages": {}
    }
    
    salvar_instancia_masmorra(instance_id, new_instance)
    print(f"--- [DEBUG] SUCESSO: Instância da dungeon salva no arquivo: dungeons/{instance_id}.json")
    return new_instance

    
