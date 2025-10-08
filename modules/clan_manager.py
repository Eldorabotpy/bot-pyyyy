# Ficheiro: modules/clan_manager.py

import json
import os
import re
import unicodedata
from datetime import datetime, timezone, timedelta
import random

# --- IMPORTS DE DADOS DO JOGO ---
from modules.game_data.clans import CLAN_PRESTIGE_LEVELS, CLAN_CONFIG
# Este ficheiro precisará de ser criado no próximo passo
from modules.game_data.guild_missions import GUILD_MISSIONS_CATALOG 
from modules import player_manager
from telegram.ext import ContextTypes
# --- CONSTANTES ---
CLANS_DIR_PATH = "data/clans/"


# =========================================================
#  NOVAS FUNÇÕES PARA MISSÕES DE GUILDA (Adicionado)
# =========================================================

def get_active_guild_mission(clan_id: str) -> dict | None:
    """
    Busca a missão ativa de um clã e enriquece os dados com informações
    do catálogo de missões (título, descrição, recompensas, etc.).
    """
    clan_data = get_clan(clan_id)
    if not clan_data or "active_mission" not in clan_data:
        return None

    mission_state = clan_data["active_mission"]
    mission_id = mission_state.get("mission_id")
    
    mission_template = GUILD_MISSIONS_CATALOG.get(mission_id)
    if not mission_template:
        # A missão pode ter sido removida do catálogo; tratamos como se não existisse.
        return None

    # Combina os dados do template com o estado atual da missão
    full_mission_details = {**mission_template, **mission_state}

    # Converte a string de tempo final para um objeto datetime para cálculos
    try:
        full_mission_details["end_time"] = datetime.fromisoformat(mission_state["end_time"])
    except (ValueError, KeyError):
        full_mission_details["end_time"] = None
        
    return full_mission_details

def set_clan_media(clan_id: str, leader_id: int, media_data: dict):
    """
    Define os dados de mídia (logo/vídeo) de um clã. Apenas o líder pode executar.
    'media_data' deve ser um dicionário como: {"file_id": "...", "type": "photo"}
    Levanta um ValueError em caso de erro.
    """
    clan_data = get_clan(clan_id)
    if not clan_data:
        raise ValueError("Clã não encontrado.")
    if clan_data.get("leader_id") != leader_id:
        raise ValueError("Apenas o líder do clã pode alterar a logo.")
    if not media_data or not isinstance(media_data, dict) or "file_id" not in media_data or "type" not in media_data:
        raise ValueError("Dados de mídia inválidos.")
        
    clan_data["logo_media"] = media_data  # Guarda o dicionário inteiro
    save_clan(clan_id, clan_data)

async def update_guild_mission_progress(clan_id: str, mission_type: str, details: dict, context: ContextTypes.DEFAULT_TYPE): # <-- MUDANÇA: Adicionado 'context'
    """
    Verifica a ação de um jogador e, se for relevante para a missão
    ativa da guilda, atualiza o progresso e dispara a conclusão.
    """
    clan_data = get_clan(clan_id)
    mission = (clan_data or {}).get("active_mission")

    if not mission or mission.get("current_progress", 0) >= mission.get("target_count", 1):
        return

    # A sua lógica de verificação de tipo e alvo está perfeita!
    if mission.get("type") != mission_type:
        return
    if mission_type == 'HUNT' and mission.get("target_monster_id") != details.get("monster_id"):
        return
            
    current_progress = mission.get("current_progress", 0)
    mission["current_progress"] = current_progress + details.get("count", 1)
    
    target_count = mission.get("target_count", 1)
    
    # Verifica se a missão foi concluída
    if mission["current_progress"] >= target_count:
        mission["current_progress"] = target_count # Garante que não ultrapasse o alvo
        
        # Passa o 'context' para a função de conclusão
        await _complete_guild_mission(clan_id, clan_data, mission.get("mission_id"), context) # <-- MUDANÇA: Passando 'context'
    
    save_clan(clan_id, clan_data)

def deposit_gold(clan_id: str, user_id: int, amount: int) -> tuple[bool, str]:
    """
    Deposita ouro da conta de um jogador para o banco do clã.
    Retorna (True, "Mensagem de sucesso") ou (False, "Mensagem de erro").
    """
    if amount <= 0:
        return False, "A quantidade para depositar deve ser positiva."

    clan_data = get_clan(clan_id)
    if not clan_data:
        return False, "Clã não encontrado."
        
    player_data = player_manager.get_player_data(user_id)
    if not player_data:
        return False, "Jogador não encontrado."

    # Tenta gastar o ouro do jogador
    if player_data.get("gold", 0) < amount:
        return False, "Você não tem ouro suficiente para depositar essa quantia."
    
    # Se o gasto foi bem-sucedido, executa a transação
    player_data["gold"] -= amount
    
    bank = clan_data.setdefault("bank", {})
    bank["gold"] = bank.get("gold", 0) + amount
    
    # Salva ambas as entidades
    save_clan(clan_id, clan_data)
    player_manager.save_player_data(user_id, player_data)
    
    return True, f"Você depositou {amount:,} de ouro com sucesso."


def purchase_mission_board(clan_id: str, leader_id: int):
    """
    Permite que o líder de um clã compre o quadro de missões usando o ouro do banco.
    Levanta um ValueError em caso de erro.
    """
    clan_data = get_clan(clan_id)
    if not clan_data:
        raise ValueError("Clã não encontrado.")

    # 1. Validações
    if clan_data.get("leader_id") != leader_id:
        raise ValueError("Apenas o líder do clã pode fazer esta compra.")
    if clan_data.get("has_mission_board"):
        raise ValueError("O seu clã já possui um quadro de missões.")

    # 2. Verifica o custo e o saldo do banco
    cost = CLAN_CONFIG.get("mission_board_cost", {}).get("gold", 100000)
    bank_gold = clan_data.get("bank", {}).get("gold", 0)

    if bank_gold < cost:
        raise ValueError(f"O banco do clã não tem ouro suficiente. Custo: {cost:,} 🪙")

    # 3. Executa a transação
    clan_data["bank"]["gold"] = bank_gold - cost
    clan_data["has_mission_board"] = True # Adiciona a flag de que o clã comprou!
    
    save_clan(clan_id, clan_data)
    
    # Notificação para o log do servidor (opcional)
    print(f"[CLAN] O clã '{clan_id}' comprou o quadro de missões.")

def withdraw_gold(clan_id: str, user_id: int, amount: int) -> tuple[bool, str]:
    """
    Retira ouro do banco do clã para a conta de um jogador.
    Apenas o líder pode fazer isso.
    Retorna (True, "Mensagem de sucesso") ou (False, "Mensagem de erro").
    """
    if amount <= 0:
        return False, "A quantidade para retirar deve ser positiva."

    clan_data = get_clan(clan_id)
    if not clan_data:
        return False, "Clã não encontrado."

    # Regra de permissão: só o líder pode retirar
    if clan_data.get("leader_id") != user_id:
        return False, "Apenas o líder do clã pode retirar ouro do banco."
        
    bank = clan_data.get("bank", {})
    current_gold = bank.get("gold", 0)
    
    if current_gold < amount:
        return False, "O banco do clã não tem ouro suficiente."
        
    # Se o banco tem ouro, transfere para o jogador
    bank["gold"] = current_gold - amount
    
    player_data = player_manager.get_player_data(user_id)
    player_data["gold"] = player_data.get("gold", 0) + amount
    
    # Salva ambas as entidades
    save_clan(clan_id, clan_data)
    player_manager.save_player_data(user_id, player_data)
    
    return True, f"Você retirou {amount:,} de ouro com sucesso."


def assign_mission_to_clan(clan_id: str, mission_id: str, leader_id: int):
    """
    Atribui uma nova missão a um clã, se os requisitos forem cumpridos.
    Apenas o líder pode executar esta ação.
    """
    clan_data = get_clan(clan_id)
    if not clan_data:
        raise ValueError("Clã não encontrado.")

    # 1. Validação de Permissão e Condição
    if clan_data.get("leader_id") != leader_id:
        raise ValueError("Apenas o líder do clã pode iniciar uma nova missão.")
    
    if "active_mission" in clan_data and clan_data.get("active_mission"):
        raise ValueError("O seu clã já tem uma missão ativa.")

    # 2. Validação da Missão
    mission_template = GUILD_MISSIONS_CATALOG.get(mission_id)
    if not mission_template:
        raise ValueError("A missão selecionada é inválida.")

    # 3. Cria o objeto da missão ativa
    duration_hours = mission_template.get("duration_hours", 24)
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(hours=duration_hours)

    new_active_mission = {
        "mission_id": mission_id,
        "type": mission_template.get("type"),
        "target_monster_id": mission_template.get("target_monster_id"), # Será None se não for de caça
        "target_count": mission_template.get("target_count", 1),
        "current_progress": 0,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat()
    }

    # 4. Salva a missão no clã
    clan_data["active_mission"] = new_active_mission
    save_clan(clan_id, clan_data)

async def _complete_guild_mission(clan_id: str, clan_data: dict, mission_id: str, context: ContextTypes.DEFAULT_TYPE): # <-- MUDANÇA: Adicionado 'context'
    """
    (Função Auxiliar) Processa a conclusão de uma missão, distribui as
    recompensas, envia notificações e limpa a missão ativa.
    """
    mission_template = GUILD_MISSIONS_CATALOG.get(mission_id)
    if not mission_template:
        clan_data["active_mission"] = None
        return

    rewards = mission_template.get("rewards", {})
    mission_title = mission_template.get("title", "Missão de Guilda")
    
    # Prepara o texto da notificação ANTES de distribuir as recompensas
    notification_text = f"🎉 <b>Missão de Guilda Concluída: {mission_title}</b> 🎉\n\n"
    notification_text += "O vosso esforço foi recompensado!\n\n"
    
    # --- Distribuição de Recompensas ---
    
    # PRESTÍGIO (guild_xp)
    prestige_gain = rewards.get("guild_xp", 0)
    if prestige_gain > 0:
        add_prestige_points(clan_id, prestige_gain)
        notification_text += f"⚜️ Prestígio para o Clã: +{prestige_gain}\n"
        print(f"[CLAN] Clã '{clan_id}' ganhou {prestige_gain} de prestígio da missão '{mission_title}'.") # LOG para debug

    # OURO POR MEMBRO
    gold_per_member = rewards.get("gold_per_member", 0)
    if gold_per_member > 0:
        notification_text += f"🪙 Ouro para cada membro: +{gold_per_member}\n"
        
    # ITEM POR MEMBRO (Exemplo, se existir)
    item_per_member = rewards.get("item_per_member")
    if item_per_member:
        # Assumindo que você tem uma função para pegar o nome do item
        item_name = item_per_member.get("item_id", "Item Misterioso")
        notification_text += f"📦 Item para cada membro: {item_name}\n"

    # Loop para dar recompensas individuais e NOTIFICAR
    for member_id in clan_data.get("members", []):
        member_data = player_manager.get_player_data(member_id)
        if member_data:
            if gold_per_member > 0:
                player_manager.add_gold(member_data, gold_per_member)
            if item_per_member and "item_id" in item_per_member:
                player_manager.add_item_to_inventory(member_data, item_per_member["item_id"], item_per_member.get("quantity", 1))
            
            player_manager.save_player_data(member_id, member_data)

            # Envia a notificação!
            try:
                await context.bot.send_message(chat_id=member_id, text=notification_text, parse_mode='HTML')
            except Exception as e:
                print(f"Falha ao notificar membro {member_id} do clã {clan_id}. Erro: {e}")

    # Limpa a missão ativa do clã
    clan_data["active_mission"] = None
    
    # A função que chamou esta já salva o clan_data.

def accept_application(clan_id: str, user_id: int):
    """Move um jogador da lista de candidaturas para a de membros."""
    clan_data = get_clan(clan_id)
    if not clan_data:
        raise ValueError("Clã não encontrado.")

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
    save_clan(clan_id, clan_data)

def decline_application(clan_id: str, user_id: int):
    """Remove uma candidatura pendente."""
    clan_data = get_clan(clan_id)
    if not clan_data:
        return

    if "pending_applications" in clan_data and user_id in clan_data["pending_applications"]:
        clan_data["pending_applications"].remove(user_id)
        save_clan(clan_id, clan_data)

def find_clan_by_display_name(clan_name: str) -> dict | None:
    """
    Procura um clã pelo seu nome de exibição (case-insensitive).
    """
    if not os.path.isdir(CLANS_DIR_PATH):
        return None
        
    for filename in os.listdir(CLANS_DIR_PATH):
        if filename.endswith(".json"):
            clan_id = filename[:-5]
            clan_data = get_clan(clan_id)
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

def level_up_clan(clan_id: str, leader_id: int, payment_method: str):
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

    leader_data = player_manager.get_player_data(leader_id)
    if payment_method == "gold":
        if leader_data.get("gold", 0) < cost:
            raise ValueError(f"Ouro insuficiente. Você precisa de {cost:,} de ouro.")
        leader_data["gold"] -= cost
    # ... (lógica para outros tipos de pagamento)
    
    clan_data["prestige_points"] -= points_needed
    clan_data["prestige_level"] += 1
    
    save_clan(clan_id, clan_data)
    player_manager.save_player_data(leader_id, leader_data)

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
    
def create_clan(leader_id: int, clan_name: str, payment_method: str) -> str:
    """Cria um novo clã, cobra o custo e salva o novo ficheiro."""
    clan_id = _slugify(clan_name)

    if get_clan(clan_id):
        raise ValueError("Um clã com este nome já existe.")

    player_data = player_manager.get_player_data(leader_id)
    cost = CLAN_CONFIG["creation_cost"][payment_method]

    if payment_method == "gold":
        if player_data.get("gold", 0) < cost:
            raise ValueError("Ouro insuficiente.")
        player_data["gold"] -= cost
    # ... (lógica para outros tipos de pagamento)

    player_manager.save_player_data(leader_id, player_data)

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