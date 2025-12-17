# modules/player/actions.py

from __future__ import annotations
from datetime import datetime, timedelta, timezone
import time
from typing import Optional, Tuple
import random
import logging
import asyncio

# Imports internos do pacote
from . import core
from .premium import PremiumManager
from .core import get_player_data, save_player_data, players_collection
from .inventory import add_item_to_inventory
from modules import game_data
from .stats import get_player_total_stats
from telegram.ext import Application
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

# Handlers / jobs usados pelo Watchdog
from modules.auto_hunt_engine import finish_auto_hunt_job
from handlers.menu.region import finish_travel_job
from handlers.job_handler import finish_collection_job
from handlers.forge_handler import finish_craft_notification_job
from handlers.refining_handler import finish_refine_job, finish_dismantle_job

logger = logging.getLogger(__name__)

# -------------------------
# Tempo / utilitários
# -------------------------
def utcnow():
    return datetime.now(timezone.utc)

def _parse_iso(dt_str: str) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None

def _ival(x, default=0):
    try:
        return int(float(x))
    except Exception:
        return int(default)

# -------------------------
# Mana
# -------------------------
async def get_player_max_mana(player_data: dict, total_stats: dict | None = None) -> int:
    if total_stats is None:
        total_stats = await get_player_total_stats(player_data)
    return _ival(total_stats.get('max_mana'), 50)

async def add_mana(player_data: dict, amount: int, total_stats: dict | None = None):
    max_m = await get_player_max_mana(player_data, total_stats)
    cur = _ival(player_data.get('current_mp', 0))
    new_val = min(cur + int(amount), max_m)
    player_data['current_mp'] = max(0, new_val)

def spend_mana(player_data: dict, amount: int) -> bool:
    amount = max(0, int(amount))
    cur = _ival(player_data.get('current_mp', 0))
    if cur < amount:
        return False
    player_data['current_mp'] = cur - amount
    return True

# -------------------------
# Energia (LÓGICA TEMPO REAL)
# -------------------------
def get_player_max_energy(player_data: dict) -> int:
    base_max = _ival(player_data.get('max_energy', 20))
    premium = PremiumManager(player_data)
    bonus = _ival(premium.get_perk_value('max_energy_bonus', 0))
    return base_max + bonus

def spend_energy(player_data: dict, amount: int = 1) -> bool:
    amount = max(0, int(amount))
    if amount == 0: return True
    
    max_e = get_player_max_energy(player_data)
    cur = _ival(player_data.get('energy', 0))
    
    if cur < amount:
        return False
        
    # === CORREÇÃO DE SINCRONIA TEMPO REAL ===
    # Se a energia estava cheia (ou acima do limite) e agora vamos gastar,
    # precisamos resetar o relógio para AGORA EXATAMENTE.
    # Isso impede que timestamps antigos (de horas atrás) causem regeneração instantânea.
    if cur >= max_e:
        player_data['energy_last_ts'] = utcnow().isoformat()
    # ========================================

    player_data['energy'] = cur - amount
    return True

def add_energy(player_data: dict, amount: int = 1) -> dict:
    max_e = get_player_max_energy(player_data)
    cur = _ival(player_data.get('energy', 0))
    new_val = min(cur + int(amount), max_e)
    player_data['energy'] = max(0, new_val)
    return player_data

def sanitize_and_cap_energy(player_data: dict):
    max_e = get_player_max_energy(player_data)
    current_raw = player_data.get("energy")
    
    if current_raw is None:
        current_val = max_e
    else:
        current_val = _ival(current_raw, 0)
        
    player_data["energy"] = max(0, min(current_val, max_e))
    
    if not player_data.get('energy_last_ts'):
        anchor = _parse_iso(player_data.get('last_energy_ts')) or utcnow()
        player_data['energy_last_ts'] = anchor.isoformat()
        
    if player_data.get('last_energy_ts'):
        player_data.pop('last_energy_ts', None)

def _get_regen_seconds(player_data: dict) -> int:
    premium = PremiumManager(player_data)
    val = int(premium.get_perk_value('energy_regen_seconds', 420))
    return max(1, val)

def _apply_energy_autoregen_inplace(player_data: dict) -> bool:
    """
    Aplica regeneração baseada no tempo real decorrido.
    """
    changed = False
    max_e = get_player_max_energy(player_data)
    cur = _ival(player_data.get('energy'), 0)
    
    last_raw = player_data.get('energy_last_ts') or player_data.get('last_energy_ts')
    now = utcnow()
    last_ts = _parse_iso(last_raw)

    # 1. Proteção contra bugs de data (data no futuro ou nula)
    if last_ts is None or last_ts > now:
        player_data['energy_last_ts'] = now.isoformat()
        return True 

    regen_s = _get_regen_seconds(player_data)
    
    # 2. Se já está cheio, mantemos o relógio atualizado para "agora"
    # Isso evita que o tempo acumule enquanto o jogador está ocioso com energia cheia
    if cur >= max_e:
        player_data['energy_last_ts'] = now.isoformat()
        return last_raw != player_data['energy_last_ts']

    elapsed = (now - last_ts).total_seconds()
    
    if elapsed < regen_s:
        return False # Ainda não deu tempo de regenerar 1 ponto

    gained = int(elapsed // regen_s)
    
    if gained > 0:
        new_energy = min(max_e, cur + gained)
        if new_energy != cur:
            player_data['energy'] = new_energy
            changed = True
        
        # 3. Atualiza o relógio preservando os segundos "sobrando"
        if new_energy >= max_e:
            player_data['energy_last_ts'] = now.isoformat()
        else:
            remainder_seconds = elapsed % regen_s
            new_anchor = now - timedelta(seconds=remainder_seconds)
            player_data['energy_last_ts'] = new_anchor.isoformat()
        
        changed = True
        
    return changed

# -------------------------
# Funções de COLETA
# -------------------------
def _collect_duration_seconds(player_data: dict) -> int:
    base_minutes = int(getattr(game_data, "COLLECTION_TIME_MINUTES", 1))
    base_seconds = base_minutes * 60
    try:
        premium = PremiumManager(player_data)
        speed_mult = float(premium.get_perk_value("gather_speed_multiplier", 1.0))
    except:
        speed_mult = 1.0
    speed_mult = max(0.1, speed_mult)
    return max(1, int(base_seconds / speed_mult))

def _gather_cost(player_data: dict) -> int:
    try:
        premium = PremiumManager(player_data)
        return int(premium.get_perk_value("gather_energy_cost", 1))
    except:
        return 1

def _gather_xp_mult(player_data: dict) -> float:
    try:
        premium = PremiumManager(player_data)
        return float(premium.get_perk_value("gather_xp_multiplier", 1.0))
    except:
        return 1.0

# -------------------------
# Ações temporizadas & Estado
# -------------------------
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

async def try_finalize_timed_action_for_user(user_id: int) -> tuple[bool, str | None]:
    player_data = await get_player_data(user_id)
    if not player_data: return False, None

    state = player_data.get("player_state") or {}
    action = state.get("action")
    actions_com_timer = ("exploring", "travel", "crafting", "working", "auto_hunting", "collecting", "refining", "dismantling")

    if action not in actions_com_timer: return False, None

    try:
        finish_time_iso = state.get("finish_time")
        if not finish_time_iso:
            player_data["player_state"] = {"action": "idle"}
            await save_player_data(user_id, player_data)
            return True, f"Sua ação '{action}' foi finalizada (sem tempo definido)."

        hora_de_termino = _parse_iso(finish_time_iso)
        if utcnow() < hora_de_termino: return False, None

        reward_summary = f"Sua ação '{action}' foi interrompida (o bot reiniciou)."
        
        if action == "travel":
            dest = (state.get("details") or {}).get("destination")
            if dest: player_data["current_location"] = dest
            reward_summary = f"Você chegou ao seu destino ({dest}) após o bot reiniciar."
        elif action == "collecting":
            reward_summary = f"Sua coleta foi interrompida."
        elif action == "auto_hunting":
            reward_summary = f"Sua Caçada Rápida foi interrompida."

        player_data["player_state"] = {"action": "idle"}
        await save_player_data(user_id, player_data)
        return True, reward_summary

    except Exception as e:
        logger.error(f"Erro em try_finalize_timed_action para {user_id}: {e}", exc_info=True)
        try:
            player_data["player_state"] = {"action": "idle"}
            await save_player_data(user_id, player_data)
        except: pass
        return True, f"Sua ação foi finalizada devido a um erro: {e}"

# -------------------------
# PvP & Watchdog
# -------------------------
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
    return _ival(player_data.get("pvp_points"), 0)

def add_pvp_points(player_data: dict, amount: int):
    current_points = get_pvp_points(player_data)
    new_points = current_points + int(amount)
    if new_points < 0: new_points = 0
    player_data["pvp_points"] = new_points
    return new_points

async def heal_player(player_data: dict, amount: int):
    total_stats = await get_player_total_stats(player_data)
    max_hp = total_stats.get('max_hp', 1)
    current_hp = _ival(player_data.get('current_hp', 0))
    player_data['current_hp'] = min(max_hp, current_hp + int(amount))

def add_buff(player_data: dict, buff_info: dict):
    if 'active_buffs' not in player_data: player_data['active_buffs'] = []
    new_buff = {
        "stat": buff_info.get("stat"),
        "value": buff_info.get("value"),
        "turns_left": buff_info.get("duration_turns")
    }
    if new_buff["stat"] and new_buff["turns_left"]:
        player_data['active_buffs'].append(new_buff)

async def check_stale_actions_on_startup(application: Application):
    """Verifica ações travadas no startup."""
    if players_collection is None: return
    logger.info("[Watchdog] Iniciando verificação de ações presas...")
    now = utcnow()
    actions_to_check = ("auto_hunting", "travel", "collecting", "crafting", "working", "refining", "dismantling")
    query = {"player_state.action": {"$in": list(actions_to_check)}}

    try:
        player_docs_cursor = players_collection.find(query)
        for pdata in player_docs_cursor:
            user_id = pdata.get("_id")
            chat_id = pdata.get("last_chat_id", user_id)
            state = pdata.get("player_state", {})
            action = state.get("action")
            details = state.get("details") or {}
            
            finish_time_iso = state.get("finish_time")
            hora_de_termino = _parse_iso(finish_time_iso) if finish_time_iso else None

            if action == "auto_hunting" and not hora_de_termino:
                pdata["player_state"] = {"action": "idle"}
                await save_player_data(user_id, pdata)
                continue
            
            if not hora_de_termino: continue

            try:
                job_name_prefix = f"watchdog_fix_{action}_{user_id}"
                if now >= hora_de_termino:
                    when_seconds = 1
                else:
                    when_seconds = (hora_de_termino - now).total_seconds()

                if action == "auto_hunting":
                    job_data = {
                        "user_id": user_id, "chat_id": chat_id,
                        "message_id": state.get("message_id"),
                        "hunt_count": details.get('hunt_count'),
                        "region_key": details.get('region_key')
                    }
                    application.job_queue.run_once(finish_auto_hunt_job, when=when_seconds, data=job_data, name=f"{job_name_prefix}_autohunt")

                elif action == "travel":
                    application.job_queue.run_once(finish_travel_job, when=when_seconds, user_id=user_id, chat_id=chat_id, data={"dest": details.get("destination")}, name=f"{job_name_prefix}_travel")

                elif action == "collecting":
                    job_data = {
                        'resource_id': details.get("resource_id"),
                        'item_id_yielded': details.get("item_id_yielded"), 
                        'energy_cost': details.get("energy_cost", 1),
                        'speed_mult': details.get("speed_mult", 1.0)
                    }
                    application.job_queue.run_once(finish_collection_job, when=when_seconds, user_id=user_id, chat_id=chat_id, data=job_data, name=f"{job_name_prefix}_collect")

                elif action == "crafting":
                    application.job_queue.run_once(finish_craft_notification_job, when=when_seconds, user_id=user_id, chat_id=chat_id, data={"recipe_id": details.get("recipe_id")}, name=f"{job_name_prefix}_craft")

                elif action == "refining":
                    application.job_queue.run_once(finish_refine_job, when=when_seconds, user_id=user_id, chat_id=chat_id, data={"recipe_id": details.get("recipe_id")}, name=f"{job_name_prefix}_refine")

                elif action == "dismantling":
                    application.job_queue.run_once(finish_dismantle_job, when=when_seconds, user_id=user_id, chat_id=chat_id, data={}, name=f"{job_name_prefix}_dismantle")

            except Exception as e:
                logger.error(f"[Watchdog] Erro ao processar user {user_id}: {e}")
                try:
                    pdata["player_state"] = {"action": "idle"}
                    await save_player_data(user_id, pdata)
                except: pass
    except Exception as e:
        logger.error(f"[Watchdog] Erro geral: {e}")