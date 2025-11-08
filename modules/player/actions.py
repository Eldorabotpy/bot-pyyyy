# Em modules/player/actions.py

from __future__ import annotations
from datetime import datetime, timedelta, timezone
import time
from typing import Optional, Tuple
import random
import logging # <<< ADICIONADO PARA LOG DE AVISO
import asyncio
from . import core
# --- IMPORTAÇÕES ADICIONADAS ---
from .premium import PremiumManager
from .core import get_player_data, save_player_data
from .inventory import add_item_to_inventory
from modules import game_data
from .stats import get_player_total_stats
from telegram.ext import Application
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from .core import players_collection
from modules import auto_hunt_engine
from modules import player_manager
from modules.auto_hunt_engine import finish_auto_hunt_job
from handlers.menu.region import finish_travel_job
from handlers.job_handler import finish_collection_job
from handlers.forge_handler import finish_craft_notification_job
from handlers.refining_handler import finish_refine_job, finish_dismantle_job

# ========================================
# FUNÇÕES AUXILIARES DE TEMPO E TIPO
# ========================================

logger = logging.getLogger(__name__) # <<< ADICIONADO PARA LOG DE AVISO

def utcnow():
    return datetime.now(timezone.utc)

def _parse_iso(dt_str: str) -> Optional[datetime]:
    if not dt_str: return None
    try:
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception: return None

def _ival(x, default=0):
    try: return int(x)
    except Exception: return int(default)

# ===================================================================
# <<< INÍCIO DA CORREÇÃO >>>
# ===================================================================

def _calculate_gathering_rewards(player_data: dict, details: dict) -> tuple[int, list[tuple[str, int]], str]:
    """
    <<< FUNÇÃO OBSOLETA / CORRIGIDA >>>
    
    Esta função não deve ser usada. A lógica de recompensas de coleta
    é tratada exclusivamente por 'finish_collection_job' em job_handler.py
    para calcular corretamente níveis, crits e bónus de profissão.
    """
    # Esta função é mantida para evitar erros de importação,
    # mas não deve ser chamada.
    try:
        user_id_log = player_data.get('user_id', '???')
        logger.warning(f"Função obsoleta _calculate_gathering_rewards foi chamada para user_id {user_id_log}")
    except Exception:
        logger.warning("Função obsoleta _calculate_gathering_rewards foi chamada.")
        
    # Retorna valores vazios para não dar recompensas duplicadas
    return 0, [], "Coleta finalizada (lógica obsoleta)."

# ===================================================================
# <<< FIM DA CORREÇÃO >>>
# ===================================================================

async def get_player_max_mana(player_data: dict, total_stats: dict | None = None) -> int:
    """Calcula a mana máxima de um jogador, lendo dos stats totais."""
    if total_stats is None:
        # <<< CORREÇÃO: Adiciona await >>>
        total_stats = await get_player_total_stats(player_data)
            
    return _ival(total_stats.get('max_mana'), 50)


async def add_mana(player_data: dict, amount: int, total_stats: dict | None = None):
    """Adiciona mana ao jogador, sem ultrapassar o máximo."""
    max_m = await get_player_max_mana(player_data, total_stats)
    cur = _ival(player_data.get('current_mp'))
    new_val = min(cur + int(amount), max_m)
    player_data['current_mp'] = max(0, new_val)
    
def get_player_max_energy(player_data: dict) -> int:
    """Calcula a energia máxima de um jogador, incluindo o bônus de perks."""
    base_max = _ival(player_data.get('max_energy'), 20)
    premium = PremiumManager(player_data)
    bonus = _ival(premium.get_perk_value('max_energy_bonus', 0))
    return base_max + bonus

def spend_energy(player_data: dict, amount: int = 1) -> bool:
    amount = max(0, int(amount))
    cur = _ival(player_data.get('energy'))
    if cur < amount: return False
    player_data['energy'] = cur - amount
    return True

def add_energy(player_data: dict, amount: int = 1) -> dict:
    max_e = get_player_max_energy(player_data)
    cur = _ival(player_data.get('energy'))
    new_val = min(cur + int(amount), max_e)
    player_data['energy'] = max(0, new_val)
    return player_data
    
def sanitize_and_cap_energy(player_data: dict):
    """Garante que a energia está dentro dos limites e o timestamp existe."""
    max_e = get_player_max_energy(player_data)
    player_data["energy"] = max(0, min(_ival(player_data.get("energy"), max_e), max_e))
    if not player_data.get('energy_last_ts'):
        anchor = _parse_iso(player_data.get('last_energy_ts')) or utcnow()
        player_data['energy_last_ts'] = anchor.isoformat()
    if player_data.get('last_energy_ts'): player_data.pop('last_energy_ts', None)


def _get_regen_seconds(player_data: dict) -> int:
    """Obtém o tempo de regeneração de energia com base nos perks do jogador."""
    # Usando o PremiumManager para buscar o perk de forma segura
    premium = PremiumManager(player_data)
    return int(premium.get_perk_value('energy_regen_seconds', 300))

def _apply_energy_autoregen_inplace(player_data: dict) -> bool:
    
    changed = False
    max_e = get_player_max_energy(player_data)
    cur = _ival(player_data.get('energy'), 0)
    last_raw = player_data.get('energy_last_ts') or player_data.get('last_energy_ts')
    last_ts = _parse_iso(last_raw) or utcnow()
    regen_s = _get_regen_seconds(player_data)
    now = utcnow()
    if cur >= max_e:
        player_data['energy_last_ts'] = now.isoformat()
        return last_raw != player_data['energy_last_ts']
    if regen_s <= 0:
        if cur < max_e:
            player_data['energy'] = max_e
            changed = True
        player_data['energy_last_ts'] = now.isoformat()
        return changed or (last_raw != player_data['energy_last_ts'])
    elapsed = (now - last_ts).total_seconds()
    if elapsed < regen_s: return False
    gained = int(elapsed // regen_s)
    if gained > 0:
        new_energy = min(max_e, cur + gained)
        if new_energy != cur:
            player_data['energy'] = new_energy
            changed = True
        remainder_seconds = elapsed % regen_s
        new_anchor = now - timedelta(seconds=remainder_seconds)
        player_data['energy_last_ts'] = new_anchor.isoformat()
        changed = True
    return changed

# ========================================
# AÇÕES TEMPORIZADAS E ESTADO
# ========================================
async def set_last_chat_id(user_id: int, chat_id: int):
    pdata = await get_player_data(user_id)
    if not pdata: return
    pdata["last_chat_id"] = int(chat_id)
    await core.save_player_data(user_id, pdata)

def ensure_timed_state(pdata: dict, action: str, seconds: int, details: dict | None, chat_id: int | None):
    start = utcnow().replace(microsecond=0)
    finish = start + timedelta(seconds=int(seconds))
    pdata["player_state"] = {
        "action": action,
        "started_at": start.isoformat(),
        "finish_time": finish.isoformat(),
        "details": details or {}
    }
    if chat_id is not None:
        pdata["last_chat_id"] = int(chat_id)
    return pdata

# <<< CORREÇÃO 4: Adiciona async def >>>
async def try_finalize_timed_action_for_user(user_id: int) -> tuple[bool, str | None]:
    """
    Verifica e finaliza ações "presas" (TRAVEL, EXPLORING, CRAFTING, WORKING, AUTO_HUNTING).
    """
    player_data = await get_player_data(user_id)
    if not player_data: 
        return False, None

    state = player_data.get("player_state") or {}
    action = state.get("action")

    # <<< [CORREÇÃO] Adiciona as novas ações temporizadas à lista >>>
    actions_com_timer = ("exploring", "travel", "crafting", "working", "auto_hunting")

    if action not in actions_com_timer:
        return False, None # Não está numa ação que precise ser destravada
   
    try:
        finish_time_iso = state.get("finish_time")
        if not finish_time_iso:
            # Se não tem tempo de fim, destrava por segurança
            player_data["player_state"] = {"action": "idle"}
            await save_player_data(user_id, player_data)
            return True, f"Sua ação '{action}' foi finalizada (sem tempo definido)."

        hora_de_termino = _parse_iso(finish_time_iso) # Síncrono

        # Se o tempo AINDA NÃO PASSOU, não faz nada
        if utcnow() < hora_de_termino:
            return False, None 

        # --- O TEMPO JÁ PASSOU ---
        # O jogador estava preso. Vamos libertá-lo e notificá-lo.

        reward_summary = f"Sua ação '{action}' foi interrompida (o bot reiniciou)."

        # Lógica específica para cada ação
        if action == "travel":
            dest = (state.get("details") or {}).get("destination")
            if dest:
                player_data["current_location"] = dest
            reward_summary = f"Você chegou ao seu destino ({dest}) após o bot reiniciar."

        elif action == "collecting": # (O teu código tinha 'exploring', mas o teu handler usa 'collecting')
            reward_summary = f"Sua coleta foi interrompida (o bot reiniciou)."
 
        elif action == "crafting" or action == "working":
            reward_summary = f"Sua Forja/Trabalho foi interrompido (o bot reiniciou). Os materiais não foram devolvidos."

        elif action == "auto_hunting":
            # O jogador perdeu as recompensas, apenas o destravamos
            reward_summary = f"Sua Caçada Rápida foi interrompida (o bot reiniciou). As recompensas não foram ganhas."
        
        # Destrava o jogador
        player_data["player_state"] = {"action": "idle"}
        await save_player_data(user_id, player_data)
        return True, reward_summary

    except Exception as e:
        logger.error(f"Erro em try_finalize_timed_action para {user_id}: {e}", exc_info=True)
        player_data["player_state"] = {"action": "idle"}
        await save_player_data(user_id, player_data)
        return True, f"Sua ação foi finalizada devido a um erro: {e}"

# ========================================
# ENTRADAS DE PVP
# ========================================
DEFAULT_PVP_ENTRIES = 10

def get_pvp_entries(player_data: dict) -> int:
    today = utcnow().date().isoformat()
    if player_data.get("last_pvp_entry_reset") != today:
        player_data["pvp_entries_left"] = DEFAULT_PVP_ENTRIES
        player_data["last_pvp_entry_reset"] = today
    return player_data.get("pvp_entries_left", DEFAULT_PVP_ENTRIES)

def use_pvp_entry(player_data: dict) -> bool:
    current_entries = get_pvp_entries(player_data)
    if current_entries > 0:
        player_data["pvp_entries_left"] = current_entries - 1
        return True
    return False

def add_pvp_entries(player_data: dict, amount: int):
    current_entries = get_pvp_entries(player_data)
    player_data["pvp_entries_left"] = current_entries + amount

def get_pvp_points(player_data: dict) -> int:
    """
    Retorna a pontuação PvP (Elo) atual do jogador.
    """
    # O .get("pvp_points", 0) garante que, se o jogador ainda não tiver
    # essa chave, a função retorna 0 em vez de dar erro.
    return _ival(player_data.get("pvp_points"), 0)

def add_pvp_points(player_data: dict, amount: int):
    """
    Adiciona ou remove (se 'amount' for negativo) pontos PvP de um jogador.
    Garante que os pontos nunca ficam abaixo de 0.
    """
    # 1. Obtém os pontos atuais
    current_points = get_pvp_points(player_data)
    
    # 2. Calcula os novos pontos
    new_points = current_points + amount
    
    # 3. Garante que os pontos não ficam negativos
    if new_points < 0:
        new_points = 0
        
    # 4. Salva os novos pontos no dicionário
    player_data["pvp_points"] = new_points
    
    # 5. Retorna os novos pontos (opcional, mas útil)
    return new_points

# ======================================================
# --- NOVO: EFEITOS DE CONSUMÍVEIS (POÇÕES, ETC.) ---
# ======================================================

async def heal_player(player_data: dict, amount: int):
    """Cura o jogador, sem ultrapassar o HP máximo."""
    total_stats = await get_player_total_stats(player_data)
    max_hp = total_stats.get('max_hp', 1)
    current_hp = player_data.get('current_hp', 0)
    
    player_data['current_hp'] = min(max_hp, current_hp + amount)
    # Garante que o HP não fica negativo por acidente
    if player_data['current_hp'] < 0:
        player_data['current_hp'] = 0

def add_buff(player_data: dict, buff_info: dict):
    """Adiciona um novo buff à lista de buffs ativos do jogador."""
    if 'active_buffs' not in player_data or not isinstance(player_data['active_buffs'], list):
        player_data['active_buffs'] = []
    
    # TODO: No futuro, podemos adicionar aqui lógica para acumular 
    # ou substituir buffs do mesmo tipo. Por agora, apenas adicionamos.
    
    new_buff = {
        "stat": buff_info.get("stat"),
        "value": buff_info.get("value"),
        "turns_left": buff_info.get("duration_turns")
    }
    
    # Adiciona o novo buff apenas se ele for válido
    if new_buff["stat"] and new_buff["turns_left"]:
        player_data['active_buffs'].append(new_buff)
        
async def get_player_max_mana(player_data: dict, total_stats: dict | None = None) -> int:
    """Calcula a mana máxima de um jogador, lendo dos stats totais."""
    if total_stats is None:
        # <<< [MUDANÇA] Adiciona 'await' >>>
        total_stats = await get_player_total_stats(player_data)
            
    return _ival(total_stats.get('max_mana'), 50)  

def spend_mana(player_data: dict, amount: int) -> bool:
    """Consome a mana do jogador. Retorna True se foi bem-sucedido."""
    amount = max(0, int(amount))
    cur = _ival(player_data.get('current_mp'))
    if cur < amount: 
        return False # Não tem mana suficiente
    player_data['current_mp'] = cur - amount
    return True
      
async def add_mana(player_data: dict, amount: int, total_stats: dict | None = None):
    """Adiciona mana ao jogador, sem ultrapassar o máximo."""
    # <<< [MUDANÇA] Adiciona 'await' >>>
    max_m = await get_player_max_mana(player_data, total_stats)
    cur = _ival(player_data.get('current_mp'))
    new_val = min(cur + int(amount), max_m)
    player_data['current_mp'] = max(0, new_val)      

async def check_stale_actions_on_startup(application: Application):
    """
    Executado UMA VEZ quando o bot inicia.
    Verifica TODOS os jogadores e finaliza/re-agenda ações "presas"
    que deveriam ter terminado (ou que estão a meio) 
    enquanto o bot estava offline.
    """
    if players_collection is None:
        logger.error("[Watchdog] Coleção de jogadores não disponível. Watchdog de ações cancelado.")
        return

    logger.info("[Watchdog] Iniciando verificação de ações presas (viagem, caça, etc.)...")
    now = utcnow()
    
    actions_to_check = (
        "auto_hunting", "travel", "collecting", 
        "crafting", "working", "refining", "dismantling"
    )
    query = {"player_state.action": {"$in": actions_to_check}}
    
    # --- CORREÇÃO 1: Mover contadores para fora do TRY ---
    # Isto corrige o 'UnboundLocalError'
    count_reagendados = 0
    count_finalizados_imediatos = 0
    
    try:
        # --- CORREÇÃO 2: Remover 'await' e '.to_list()' ---
        # Isto corrige o 'TypeError'
        # Estamos a usar o Pymongo síncrono aqui.
        player_docs_cursor = players_collection.find(query)
        
        if not player_docs_cursor:
            logger.info("[Watchdog] Nenhum jogador encontrado com ações presas.")
            return

        # Iteramos sobre o cursor síncrono
        for pdata in player_docs_cursor:
            user_id = pdata["_id"]
            chat_id = pdata.get("last_chat_id")
            state = pdata.get("player_state", {})
            action = state.get("action")

            # Corrige o bug 'AttributeError: 'str' object'
            details_raw = state.get("details")
            details = details_raw if isinstance(details_raw, dict) else {}

            finish_time_iso = state.get("finish_time")
            if not finish_time_iso:
                continue 

            try:
                hora_de_termino = _parse_iso(finish_time_iso)
                if not hora_de_termino:
                    continue
                
                job_name_prefix = f"watchdog_fix_{action}_{user_id}"
                
                if now >= hora_de_termino:
                    when_seconds = 1
                    count_finalizados_imediatos += 1
                else:
                    when_seconds = (hora_de_termino - now).total_seconds()
                    count_reagendados += 1

                # --- LÓGICA DE AGENDAMENTO (ÚNICA) ---
                
                if action == "auto_hunting":
                    job_data = {
                        "user_id": user_id, "chat_id": chat_id,
                        "message_id": state.get("message_id"),
                        "hunt_count": details.get('hunt_count'),
                        "region_key": details.get('region_key')
                    }
                    application.job_queue.run_once(
                        finish_auto_hunt_job,
                        when=when_seconds, 
                        data=job_data, name=f"{job_name_prefix}_autohunt"
                    )
                
                elif action == "travel":
                    application.job_queue.run_once(
                        finish_travel_job,
                        when=when_seconds,
                        user_id=user_id, chat_id=chat_id,
                        data={"dest": details.get("destination")},
                        name=f"{job_name_prefix}_travel",
                    )
                
                elif action == "collecting":
                    job_data = {
                        'resource_id': details.get("resource_id"),
                        'item_id_yielded': details.get("item_id_yielded"),
                        'energy_cost': details.get("energy_cost", 1),
                        'speed_mult': details.get("speed_mult", 1.0)
                    }
                    application.job_queue.run_once(
                        finish_collection_job,
                        when=when_seconds,
                        user_id=user_id, chat_id=chat_id,
                        data=job_data, name=f"{job_name_prefix}_collect"
                    )

                elif action == "crafting":
                    job_data = {"recipe_id": details.get("recipe_id")}
                    application.job_queue.run_once(
                        finish_craft_notification_job,
                        when=when_seconds,
                        user_id=user_id, chat_id=chat_id,
                        data=job_data, name=f"{job_name_prefix}_craft"
                    )

                elif action == "refining":
                    job_data = {"recipe_id": details.get("recipe_id")}
                    application.job_queue.run_once(
                        finish_refine_job,
                        when=when_seconds,
                        user_id=user_id, chat_id=chat_id,
                        data=job_data, name=f"{job_name_prefix}_refine"
                    )
                
                elif action == "dismantling":
                    application.job_queue.run_once(
                        finish_dismantle_job,
                        when=when_seconds,
                        user_id=user_id, chat_id=chat_id,
                        data={}, name=f"{job_name_prefix}_dismantle"
                    )

            except Exception as e_inner:
                logger.error(f"[Watchdog] Erro ao processar o jogador {user_id}: {e_inner}", exc_info=True)
                # Tenta destravar o jogador mesmo se a lógica falhar
                try:
                    pdata["player_state"] = {"action": "idle"}
                    # IMPORTANTE: A sua função save_player_data É async, por isso precisa de await!
                    await save_player_data(user_id, pdata)
                except Exception as e_save_fail:
                    logger.error(f"[Watchdog] FALHA CRÍTICA ao destravar {user_id}: {e_save_fail}")

    except Exception as e_outer:
        logger.error(f"[Watchdog] Erro ao consultar o DB para ações presas: {e_outer}", exc_info=True)
        
    # Esta linha agora é segura por causa da Correção 1
    logger.info(f"[Watchdog] Verificação concluída. {count_finalizados_imediatos} ações finalizadas imediatamente, {count_reagendados} ações reagendadas.")
    