# Em modules/dungeon_manager.py (VERSÃO CORRIGIDA PARA ASYNC I/O)

import json
import os
import re
import unicodedata
from datetime import datetime, timezone, timedelta
import random
import logging # Adiciona logging
import asyncio # <<< ADICIONADO para to_thread

from modules.game_data.clans import CLAN_PRESTIGE_LEVELS, CLAN_CONFIG
from modules.game_data.guild_missions import GUILD_MISSIONS_CATALOG 
from modules import player_manager, game_data, clan_manager, dungeon_definitions, party_manager

logger = logging.getLogger(__name__) # Adiciona logger

CLANS_DIR_PATH = "data/clans/" # Parece ser um erro de cópia, devia ser DUNGEONS_DIR_PATH?
DUNGEONS_DIR_PATH = "dungeons" # Nome correto do diretório

# =========================================================
# Funções SÍNCRONAS (SYNC I/O) - Não chame estas diretamente de handlers async
# =========================================================

def _garantir_que_diretorio_exista():
    """Garante que o diretório 'dungeons' exista."""
    os.makedirs(DUNGEONS_DIR_PATH, exist_ok=True) # Usa a constante correta

def _pegar_instancia_sync(id_da_instancia: str) -> dict | None:
    """Função SÍNCRONA: Carrega dados do JSON."""
    _garantir_que_diretorio_exista()
    caminho_arquivo = os.path.join(DUNGEONS_DIR_PATH, f"{id_da_instancia}.json")
    if not os.path.exists(caminho_arquivo):
        return None
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, FileNotFoundError): # Adiciona FileNotFoundError
        return None

def _salvar_instancia_sync(id_da_instancia: str, dados_da_masmorra: dict):
    """Função SÍNCRONA: Salva dados no JSON."""
    _garantir_que_diretorio_exista()
    caminho_arquivo = os.path.join(DUNGEONS_DIR_PATH, f"{id_da_instancia}.json")
    try:
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados_da_masmorra, f, indent=4, ensure_ascii=False)
    except IOError as e:
         logger.error(f"Erro ao salvar a instância da dungeon {id_da_instancia}: {e}")

def _deletar_instancia_sync(id_da_instancia: str):
    """Função SÍNCRONA: Apaga o arquivo JSON."""
    _garantir_que_diretorio_exista()
    caminho_arquivo = os.path.join(DUNGEONS_DIR_PATH, f"{id_da_instancia}.json")
    if os.path.exists(caminho_arquivo):
        try:
             os.remove(caminho_arquivo)
        except IOError as e:
             logger.error(f"Erro ao deletar a instância da dungeon {id_da_instancia}: {e}")


# =========================================================
# Funções ASSÍNCRONAS (ASYNC I/O) - Interface para o resto do bot
# =========================================================

async def pegar_instancia_masmorra(id_da_instancia: str) -> dict | None:
    """Busca os dados de uma instância de masmorra ativa de forma assíncrona."""
    # <<< CORREÇÃO: Usa asyncio.to_thread para I/O de ficheiro >>>
    return await asyncio.to_thread(_pegar_instancia_sync, id_da_instancia)

async def salvar_instancia_masmorra(id_da_instancia: str, dados_da_masmorra: dict):
    """Salva os dados de uma instância de masmorra ativa de forma assíncrona."""
    # <<< CORREÇÃO: Usa asyncio.to_thread para I/O de ficheiro >>>
    await asyncio.to_thread(_salvar_instancia_sync, id_da_instancia, dados_da_masmorra.copy())

async def deletar_instancia_masmorra(id_da_instancia: str):
    """Apaga o arquivo de uma instância de masmorra de forma assíncrona."""
    # <<< CORREÇÃO: Usa asyncio.to_thread para I/O de ficheiro >>>
    await asyncio.to_thread(_deletar_instancia_sync, id_da_instancia)

# =====================================================================
# Lógica de Criação (CORRIGIDA)
# =====================================================================

# <<< CORREÇÃO: Adiciona async def >>>
async def criar_instancia_masmorra(dungeon_id: str, party_id: str) -> dict | None:
    """Cria uma nova instância de masmorra para um grupo, usando o party_id como chave."""
    print("\n\n--- [DEBUG] Tentando criar instância da dungeon ---")
    print(f"--- [DEBUG] ID da Dungeon recebido: {dungeon_id}")
    print(f"--- [DEBUG] ID do Grupo recebido: {party_id}")

    # <<< CORREÇÃO: Adiciona await (assumindo que party_manager é async) >>>
    party_data = await party_manager.get_party_data(party_id)
    dungeon_template = dungeon_definitions.DUNGEONS.get(dungeon_id) # Síncrono

    if not party_data: print("--- [DEBUG] FALHA: Não foi possível encontrar os dados do grupo (party_data is None).")
    else: print("--- [DEBUG] SUCESSO: Dados do grupo encontrados.")
    if not dungeon_template: print(f"--- [DEBUG] FALHA: Não foi possível encontrar o modelo da dungeon com o ID '{dungeon_id}'.")
    else: print("--- [DEBUG] SUCESSO: Modelo da dungeon encontrado.")
    
    if not dungeon_template or not party_data:
        print("--- [DEBUG] A criação da instância foi cancelada por falta de dados.")
        return None

    # Lógica síncrona de criação de monstros
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
                    # Adiciona outros stats se necessário
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
    
    # <<< CORREÇÃO: Adiciona await >>>
    await salvar_instancia_masmorra(instance_id, new_instance) # Chama a nova função async
    print(f"--- [DEBUG] SUCESSO: Instância da dungeon salva no arquivo: {DUNGEONS_DIR_PATH}/{instance_id}.json")
    return new_instance