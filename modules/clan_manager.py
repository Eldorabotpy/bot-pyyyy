# Ficheiro: modules/clan_manager.py

import json
import os
import re
import unicodedata
import random
import asyncio
from datetime import datetime, timezone, timedelta
from modules.game_data.clans import CLAN_PRESTIGE_LEVELS, CLAN_CONFIG
from modules.game_data.guild_missions import GUILD_MISSIONS_CATALOG 
from modules import player_manager
from telegram.ext import ContextTypes

CLANS_DIR_PATH = "data/clans/"


# =========================================================
#  NOVAS FUNÇÕES PARA MISSÕES DE GUILDA (Adicionado)
# =========================================================

# <<< CORREÇÃO 1: Adiciona async def >>>
async def get_active_guild_mission(clan_id: str) -> dict | None:
    """
    Busca a missão ativa de um clã e enriquece os dados com informações
    do catálogo de missões (título, descrição, recompensas, etc.).
    (Versão async)
    """
    # <<< CORREÇÃO 2: Adiciona await (se get_clan se tornar async) >>>
    # Assumindo que get_clan permanece síncrono por agora
    clan_data = get_clan(clan_id)
    if not clan_data or not clan_data.get("active_mission"):
        return None

    mission_state = clan_data["active_mission"]
    mission_id = mission_state.get("mission_id")
    
    mission_template = GUILD_MISSIONS_CATALOG.get(mission_id) # Síncrono
    if not mission_template:
        return None

    full_mission_details = {**mission_template, **mission_state} # Síncrono

    try: # Síncrono
        full_mission_details["end_time"] = datetime.fromisoformat(mission_state["end_time"])
    except (ValueError, KeyError):
        full_mission_details["end_time"] = None
        
    return full_mission_details

#
# >>> INÍCIO DO CÓDIGO PARA ADICIONAR <<<
#

async def update_guild_mission_progress(clan_id: str, mission_type: str, details: dict, context: ContextTypes.DEFAULT_TYPE):
    """
    Atualiza o progresso de uma missão ativa do clã com base numa ação do jogador.
    (Esta era a função que estava a faltar e que causou o erro no pvp_handler)
    
    :param clan_id: O ID (slug) do clã.
    :param mission_type: O tipo de ação realizada (ex: "PVP_WIN", "MONSTER_HUNT").
    :param details: Um dicionário com detalhes da ação (ex: {'count': 1} ou {'monster_id': 'goblin', 'count': 1}).
    :param context: O contexto do bot (para enviar mensagens de conclusão).
    """
    if not clan_id:
        return

    # 1. Carregar os dados "raw" do clã (síncrono)
    clan_data = get_clan(clan_id)
    if not clan_data:
        print(f"[Mission Update] Clã {clan_id} não encontrado.")
        return

    # 2. Carregar os dados "enriquecidos" da missão ativa (assíncrono)
    active_mission = await get_active_guild_mission(clan_id)
    if not active_mission:
        # Clã não tem missão ativa, o que é normal. Ignora silenciosamente.
        return

    # 3. Verificar se a missão expirou
    end_time = active_mission.get("end_time")
    if end_time and datetime.now(timezone.utc) > end_time:
        # A missão expirou, limpa-a
        clan_data["active_mission"] = None
        save_clan(clan_id, clan_data)
        return

    # 4. Verificar se a ação (mission_type) é a que a missão pede
    if active_mission.get("type") != mission_type:
        # O jogador fez uma ação (ex: PvP) mas a missão é de outro tipo (ex: Caça)
        return

    # 5. Processar o progresso
    progress_made = 0
    
    if mission_type == "PVP_WIN":
        # Para missões de PvP, só precisamos de contar a vitória
        progress_made = details.get("count", 0)
        
    elif mission_type == "MONSTER_HUNT":
        # Para missões de Caça, verificamos se o monstro é o alvo
        target_monster_id = active_mission.get("target_monster_id")
        if details.get("monster_id") == target_monster_id:
            progress_made = details.get("count", 0)
            
    # (Podes adicionar mais lógica para outros tipos de missão aqui)

    if progress_made == 0:
        # A ação não contribuiu para esta missão em específico
        return

    # 6. Atualizar o progresso no dicionário do clã
    current_progress = active_mission.get("current_progress", 0)
    target_count = active_mission.get("target_count", 1)
    
    # Garante que usamos a versão "raw" dos dados do clã para atualizar
    if "active_mission" not in clan_data or not clan_data["active_mission"]:
        return # Segurança: se a missão foi removida noutra thread
        
    new_progress = current_progress + progress_made
    clan_data["active_mission"]["current_progress"] = new_progress
    
    print(f"[Mission Update] Clã {clan_id} progrediu: {new_progress}/{target_count} (Ação: {mission_type})")

    # 7. Verificar se a missão foi concluída
    if new_progress >= target_count:
        print(f"[Mission Update] Clã {clan_id} COMPLETOU a missão!")
        mission_id = active_mission.get("mission_id")
        
        # Chama a função auxiliar para dar recompensas e limpar a missão
        await _complete_guild_mission(clan_id, clan_data, mission_id, context)

    # 8. Salvar os dados do clã (seja o progresso ou a conclusão)
    save_clan(clan_id, clan_data)

   
# <<< CORREÇÃO 3: Adiciona async def >>>
async def set_clan_media(clan_id: str, leader_id: int, media_data: dict):
    """
    Define os dados de mídia (logo/vídeo) de um clã. (Versão async)
    """
    # Assumindo get_clan síncrono
    clan_data = get_clan(clan_id)
    if not clan_data:
        raise ValueError("Clã não encontrado.")
    if clan_data.get("leader_id") != leader_id:
        raise ValueError("Apenas o líder do clã pode alterar a logo.")
    if not media_data or not isinstance(media_data, dict) or "file_id" not in media_data or "type" not in media_data:
        raise ValueError("Dados de mídia inválidos.")
        
    clan_data["logo_media"] = media_data
    # Assumindo save_clan síncrono
    save_clan(clan_id, clan_data)

# <<< CORREÇÃO 4: Adiciona async def >>>
async def _add_bank_log_entry(clan_data: dict, user_id: int, action: str, amount: int):
    """Adiciona uma entrada ao log do banco do clã. (Versão async)"""
    if "bank_log" not in clan_data:
        clan_data["bank_log"] = []
    
    # <<< CORREÇÃO 5: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)
    player_name = (player_data or {}).get("character_name", f"ID: {user_id}")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    
    log_entry = {
        "timestamp": timestamp,
        "player_name": player_name,
        "action": action,
        "amount": amount
    }
    
    clan_data["bank_log"].insert(0, log_entry)
    if len(clan_data["bank_log"]) > 50:
        clan_data["bank_log"] = clan_data["bank_log"][:50]

# <<< CORREÇÃO 4: Adiciona async def >>>
async def _add_bank_log_entry(clan_data: dict, user_id: int, action: str, amount: int):
    """Adiciona uma entrada ao log do banco do clã. (Versão async)"""
    if "bank_log" not in clan_data:
        clan_data["bank_log"] = []
    
    # <<< CORREÇÃO 5: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)
    player_name = (player_data or {}).get("character_name", f"ID: {user_id}")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    
    log_entry = {
        "timestamp": timestamp,
        "player_name": player_name,
        "action": action,
        "amount": amount
    }
    
    clan_data["bank_log"].insert(0, log_entry)
    if len(clan_data["bank_log"]) > 50:
        clan_data["bank_log"] = clan_data["bank_log"][:50]

# <<< CORREÇÃO 6: Adiciona async def >>>
async def deposit_gold(clan_id: str, user_id: int, amount: int) -> tuple[bool, str]:
    """
    Deposita ouro da conta de um jogador para o banco do clã. (Versão async)
    """
    if amount <= 0:
        return False, "A quantidade para depositar deve ser positiva."

    clan_data = get_clan(clan_id) # Síncrono
    if not clan_data:
        return False, "Clã não encontrado."
        
    # <<< CORREÇÃO 7: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        return False, "Jogador não encontrado."
    
    print(f"[DEBUG BANCO] Tentando depositar: {amount}. Ouro do jogador: {player_data.get('gold', 0)}")

    if player_data.get("gold", 0) < amount:
        return False, "Você não tem ouro suficiente para depositar essa quantia."
    
    player_data["gold"] -= amount # Síncrono
    
    bank = clan_data.setdefault("bank", {})
    bank["gold"] = bank.get("gold", 0) + amount
    # <<< CORREÇÃO 8: Adiciona await >>>
    await _add_bank_log_entry(clan_data, user_id, "depositou", amount) # Chama função async

    save_clan(clan_id, clan_data) # Síncrono
    # <<< CORREÇÃO 9: Adiciona await >>>
    await player_manager.save_player_data(user_id, player_data)
    
    return True, f"Você depositou {amount:,} de ouro com sucesso."


# <<< CORREÇÃO 10: Adiciona async def >>>
async def purchase_mission_board(clan_id: str, leader_id: int):
    """
    Permite que o líder compre o quadro de missões. (Versão async)
    """
    clan_data = get_clan(clan_id) # Síncrono
    if not clan_data:
        raise ValueError("Clã não encontrado.")

    if clan_data.get("leader_id") != leader_id:
        raise ValueError("Apenas o líder do clã pode fazer esta compra.")
    if clan_data.get("has_mission_board"):
        raise ValueError("O seu clã já possui um quadro de missões.")

    cost = CLAN_CONFIG.get("mission_board_cost", {}).get("gold", 100000)
    bank_gold = clan_data.get("bank", {}).get("gold", 0)

    if bank_gold < cost:
        raise ValueError(f"O banco do clã não tem ouro suficiente. Custo: {cost:,} 🪙")

    clan_data["bank"]["gold"] = bank_gold - cost
    clan_data["has_mission_board"] = True
    
    save_clan(clan_id, clan_data) # Síncrono
    print(f"[CLAN] O clã '{clan_id}' comprou o quadro de missões.")

# <<< CORREÇÃO 11: Adiciona async def >>>
async def withdraw_gold(clan_id: str, user_id: int, amount: int) -> tuple[bool, str]:
    """
    Retira ouro do banco do clã. (Versão async)
    """
    if amount <= 0:
        return False, "A quantidade para retirar deve ser positiva."

    clan_data = get_clan(clan_id) # Síncrono
    if not clan_data:
        return False, "Clã não encontrado."

    if clan_data.get("leader_id") != user_id:
        return False, "Apenas o líder do clã pode retirar ouro do banco."
        
    bank = clan_data.get("bank", {})
    current_gold = bank.get("gold", 0)
    
    if current_gold < amount:
        return False, "O banco do clã não tem ouro suficiente."
        
    bank["gold"] = current_gold - amount
    
    # <<< CORREÇÃO 12: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
         return False, "Jogador não encontrado." # Adiciona verificação
         
    player_data["gold"] = player_data.get("gold", 0) + amount
    # <<< CORREÇÃO 13: Adiciona await >>>
    await _add_bank_log_entry(clan_data, user_id, "retirou", amount) # Chama função async

    save_clan(clan_id, clan_data) # Síncrono
    # <<< CORREÇÃO 14: Adiciona await >>>
    await player_manager.save_player_data(user_id, player_data)
    
    return True, f"Você retirou {amount:,} de ouro com sucesso."

# <<< CORREÇÃO 15: Adiciona async def >>>
async def assign_mission_to_clan(clan_id: str, mission_id: str, leader_id: int):
    """
    Atribui uma nova missão a um clã. (Versão async)
    """
    clan_data = get_clan(clan_id) # Síncrono
    if not clan_data:
        raise ValueError("Clã não encontrado.")

    if clan_data.get("leader_id") != leader_id:
        raise ValueError("Apenas o líder do clã pode iniciar uma nova missão.")
    
    if "active_mission" in clan_data and clan_data.get("active_mission"):
        raise ValueError("O seu clã já tem uma missão ativa.")

    mission_template = GUILD_MISSIONS_CATALOG.get(mission_id) # Síncrono
    if not mission_template:
        raise ValueError("A missão selecionada é inválida.")

    # Lógica síncrona de criação de missão
    duration_hours = mission_template.get("duration_hours", 24)
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(hours=duration_hours)
    new_active_mission = {
        "mission_id": mission_id, "type": mission_template.get("type"),
        "target_monster_id": mission_template.get("target_monster_id"),
        "target_count": mission_template.get("target_count", 1), "current_progress": 0,
        "start_time": start_time.isoformat(), "end_time": end_time.isoformat()
    }

    clan_data["active_mission"] = new_active_mission
    save_clan(clan_id, clan_data) # Síncrono

async def _complete_guild_mission(clan_id: str, clan_data: dict, mission_id: str, context: ContextTypes.DEFAULT_TYPE):
    """
    (Função Auxiliar) Processa a conclusão de uma missão. (Já era async)
    """
    mission_template = GUILD_MISSIONS_CATALOG.get(mission_id) # Síncrono
    if not mission_template:
        clan_data["active_mission"] = None
        return

    rewards = mission_template.get("rewards", {})
    mission_title = mission_template.get("title", "Missão de Guilda")
    notification_text = f"🎉 <b>Missão de Guilda Concluída: {mission_title}</b> 🎉\n\n(...)"
    
    prestige_gain = rewards.get("guild_xp", 0)
    if prestige_gain > 0:
        add_prestige_points(clan_id, prestige_gain) # Síncrono
        notification_text += f"⚜️ Prestígio para o Clã: +{prestige_gain}\n"
        print(f"[CLAN] Clã '{clan_id}' ganhou {prestige_gain} de prestígio...")

    gold_per_member = rewards.get("gold_per_member", 0)
    if gold_per_member > 0: notification_text += f"🪙 Ouro para cada membro: +{gold_per_member}\n"
    item_per_member = rewards.get("item_per_member")
    if item_per_member: item_name = item_per_member.get("item_id", "Item Misterioso"); notification_text += f"📦 Item para cada membro: {item_name}\n"

    # Loop para dar recompensas individuais e NOTIFICAR
    for member_id in clan_data.get("members", []):
        # <<< CORREÇÃO 16: Adiciona await >>>
        member_data = await player_manager.get_player_data(member_id)
        if member_data:
            if gold_per_member > 0:
                player_manager.add_gold(member_data, gold_per_member) # Síncrono
            if item_per_member and "item_id" in item_per_member:
                player_manager.add_item_to_inventory(member_data, item_per_member["item_id"], item_per_member.get("quantity", 1)) # Síncrono
            
            # <<< CORREÇÃO 17: Adiciona await >>>
            await player_manager.save_player_data(member_id, member_data)

            try:
                await context.bot.send_message(chat_id=member_id, text=notification_text, parse_mode='HTML')
                await asyncio.sleep(0.1) # Adiciona delay anti-spam
            except Exception as e:
                print(f"Falha ao notificar membro {member_id} do clã {clan_id}. Erro: {e}")

    clan_data["active_mission"] = None
    # save_clan é chamado pela função que chamou esta (update_guild_mission_progress)

async def accept_application(clan_id: str, user_id: int):
    """Move um jogador da lista de candidaturas para a de membros. (Versão async)"""
    clan_data = get_clan(clan_id) # Síncrono
    if not clan_data:
        raise ValueError("Clã não encontrado.")

    # Lógica síncrona
    clan_level = clan_data.get("prestige_level", 1)
    level_info = CLAN_PRESTIGE_LEVELS.get(clan_level, {})
    max_members = level_info.get("max_members", 5)
    if len(clan_data.get("members", [])) >= max_members:
        raise ValueError("O clã está cheio.")
    apps = clan_data.get("pending_applications", [])
    if user_id not in apps:
        raise ValueError("Este jogador não tem uma candidatura pendente.")

    clan_data["pending_applications"].remove(user_id)
    clan_data["members"].append(user_id)
    save_clan(clan_id, clan_data) # Síncrono

def decline_application(clan_id: str, user_id: int):
    """Remove uma candidatura pendente."""
    clan_data = get_clan(clan_id)
    if not clan_data:
        return

    if "pending_applications" in clan_data and user_id in clan_data["pending_applications"]:
        clan_data["pending_applications"].remove(user_id)
        save_clan(clan_id, clan_data)

# <<< CORREÇÃO 19: Adiciona async def >>>
async def find_clan_by_display_name(clan_name: str) -> dict | None:
    """
    Procura um clã pelo seu nome de exibição (case-insensitive). (Versão async)
    """
    if not os.path.isdir(CLANS_DIR_PATH):
        return None
        
    # Leitura de ficheiros é I/O, idealmente seria async, mas mantemos síncrono por agora
    for filename in os.listdir(CLANS_DIR_PATH):
        if filename.endswith(".json"):
            clan_id = filename[:-5]
            clan_data = get_clan(clan_id) # Síncrono
            if clan_data and clan_data.get("display_name", "").lower() == clan_name.lower():
                clan_data['id'] = clan_id
                return clan_data
    return None

def add_application(clan_id: str, user_id: int):
    """Adiciona a candidatura de um jogador a um clã."""
    clan_data = get_clan(clan_id)
    if not clan_data:
        raise ValueError("O clã não foi encontrado.")

    if user_id in clan_data.get("members", []):
        raise ValueError("Você já é membro deste clã.")

    if "pending_applications" not in clan_data:
        clan_data["pending_applications"] = []
    
    if user_id in clan_data["pending_applications"]:
        raise ValueError("Você já se candidatou a este clã.")

    clan_data["pending_applications"].append(user_id)
    save_clan(clan_id, clan_data)

def _slugify(text: str) -> str:
    """Normaliza o nome do clã para ser usado como nome de ficheiro."""
    if not text:
        return ""
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    norm = re.sub(r'\s+', '_', norm.strip().lower())
    norm = re.sub(r'[^a-z0-9_]', '', norm)
    return norm

def get_clan(clan_id: str) -> dict | None:
    """
    Carrega os dados de um clã específico a partir do seu ficheiro JSON.
    """
    if not clan_id:
        return None
    
    file_path = os.path.join(CLANS_DIR_PATH, f"{clan_id}.json")
    
    try:
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None

def save_clan(clan_id: str, clan_data: dict):
    """
    Salva os dados de um clã específico no seu ficheiro JSON.
    """
    os.makedirs(CLANS_DIR_PATH, exist_ok=True)
    
    file_path = os.path.join(CLANS_DIR_PATH, f"{clan_id}.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(clan_data, f, indent=4, ensure_ascii=False)

def get_clan_buffs(clan_id: str) -> dict:
    """
    Lê os dados de um clã e retorna o dicionário de buffs do seu nível atual.
    """
    if not clan_id:
        return {}
        
    clan_data = get_clan(clan_id)
    if not clan_data:
        return {}
        
    clan_level = clan_data.get("prestige_level", 1)
    level_info = CLAN_PRESTIGE_LEVELS.get(clan_level, {})
    
    return level_info.get("buffs", {})

def remove_member(clan_id: str, user_id: int, kicked_by_leader: bool = False): # <-- Argumento adicionado
    """Remove um membro da lista de membros de um clã."""
    clan_data = get_clan(clan_id)
    if not clan_data:
        return

    if "members" in clan_data and user_id in clan_data["members"]:
        if clan_data.get("leader_id") == user_id:
            raise ValueError("O líder não pode abandonar ou ser expulso do clã.")

        clan_data["members"].remove(user_id)
        save_clan(clan_id, clan_data)

        # Aqui você poderia adicionar lógica futura baseada em 'kicked_by_leader'
        if kicked_by_leader:
            print(f"[LOG] O jogador {user_id} foi expulso do clã {clan_id}.")
        else:
            print(f"[LOG] O jogador {user_id} saiu do clã {clan_id}.")

def transfer_leadership(clan_id: str, current_leader_id: int, new_leader_id: int):
    """Transfere a liderança de um clã para um novo membro."""
    clan_data = get_clan(clan_id)
    if not clan_data:
        raise ValueError("Clã não encontrado.")
    
    if clan_data.get("leader_id") != current_leader_id:
        raise ValueError("Você não é o líder deste clã.")
    if new_leader_id not in clan_data.get("members", []):
        raise ValueError("O jogador alvo não é um membro deste clã.")
    if current_leader_id == new_leader_id:
        raise ValueError("Você não pode transferir a liderança para si mesmo.")

    clan_data["leader_id"] = new_leader_id
    save_clan(clan_id, clan_data)

def add_prestige_points(clan_id: str, points_to_add: int):
    """Adiciona pontos de prestígio a um clã."""
    clan_data = get_clan(clan_id)
    if not clan_data or points_to_add <= 0:
        return
    
    current_points = clan_data.get("prestige_points", 0)
    clan_data["prestige_points"] = current_points + points_to_add
    save_clan(clan_id, clan_data)
    
async def create_clan(leader_id: int, clan_name: str, payment_method: str) -> str:
    """Cria um novo clã, cobra o custo e salva o novo ficheiro."""
    clan_id = _slugify(clan_name)

    if get_clan(clan_id):
        raise ValueError("Um clã com este nome já existe.")

    player_data = await player_manager.get_player_data(leader_id)
    cost = CLAN_CONFIG["creation_cost"][payment_method]

    if payment_method == "gold":
        if player_data.get("gold", 0) < cost:
            raise ValueError("Ouro insuficiente.")
        player_data["gold"] -= cost


    await player_manager.save_player_data(leader_id, player_data)

    new_clan_data = {
        "display_name": clan_name,
        "leader_id": leader_id,
        "members": [leader_id],
        "prestige_level": 1,
        "prestige_points": 0,
        "creation_date": datetime.now(timezone.utc).isoformat()
    }

    save_clan(clan_id, new_clan_data)
    return clan_id

async def level_up_clan(clan_id: str, leader_id: int, payment_method: str):
    """
    Verifica os requisitos e, se cumpridos, sobe o nível de prestígio do clã.
    """
    clan_data = get_clan(clan_id)
    if not clan_data:
        raise ValueError("Clã não encontrado.")

    current_level = clan_data.get("prestige_level", 1)
    if current_level + 1 not in CLAN_PRESTIGE_LEVELS:
        raise ValueError("O clã já atingiu o nível máximo.")

    current_level_info = CLAN_PRESTIGE_LEVELS.get(current_level, {})
    points_needed = current_level_info.get("points_to_next_level")
    if points_needed is None:
        raise ValueError("O clã já atingiu o nível máximo.")
        
    current_points = clan_data.get("prestige_points", 0)
    if current_points < points_needed:
        raise ValueError("Pontos de prestígio insuficientes.")
        
    next_level_info = CLAN_PRESTIGE_LEVELS.get(current_level + 1, {})
    upgrade_cost = next_level_info.get("upgrade_cost", {})
    cost = upgrade_cost.get(payment_method)
    if cost is None:
        raise ValueError(f"Método de pagamento '{payment_method}' inválido.")

    leader_data = await player_manager.get_player_data(leader_id)
    if payment_method == "gold":
        if leader_data.get("gold", 0) < cost:
            raise ValueError(f"Ouro insuficiente. Você precisa de {cost:,} de ouro.")
        leader_data["gold"] -= cost
    # ... (lógica para outros tipos de pagamento)
    
    clan_data["prestige_points"] -= points_needed
    clan_data["prestige_level"] += 1
    
    save_clan(clan_id, clan_data)
    await player_manager.save_player_data(leader_id, leader_data)
