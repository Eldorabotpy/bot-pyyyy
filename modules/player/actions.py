# modules/player/actions.py
# (VERSÃO CORRIGIDA: Imports movidos para evitar travamento da Caçada Automática)

from __future__ import annotations
from datetime import datetime, timedelta, timezone
import time
from typing import Optional, Tuple
import random
import logging
import asyncio

# Imports internos do pacote (Estes são seguros)
from . import core
from .premium import PremiumManager
from .core import get_player_data, save_player_data, players_collection
from .inventory import add_item_to_inventory
from modules import game_data
from .stats import get_player_total_stats
from telegram.ext import Application
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from modules.game_data.skills import SKILL_DATA
# -------------------------------------------------------------------------
# ⚠️ REMOVIDO IMPORTS GLOBAIS DE HANDLERS AQUI PARA EVITAR CICLO
# Eles foram movidos para dentro da função check_stale_actions_on_startup
# -------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# -------------------------
# Tempo / utilitários
# -------------------------
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
    try: return int(float(x))
    except Exception: return int(default)

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
    player_data['current_mp'] = max(0, min(cur + int(amount), max_m))

def spend_mana(player_data: dict, amount: int) -> bool:
    amount = max(0, int(amount))
    cur = _ival(player_data.get('current_mp', 0))
    if cur < amount: return False
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
        
    # Se a energia estava cheia, reseta o relógio para AGORA
    # Isso evita regeneração instantânea se o player ficou ocioso muito tempo
    if cur >= max_e:
        player_data['energy_last_ts'] = utcnow().isoformat()

    player_data['energy'] = cur - amount
    return True

def apply_item_effects(player_data: dict, effects: dict) -> list[str]:
    """
    Aplica os efeitos de um item no jogador.
    Retorna uma lista de mensagens de feedback.
    """
    messages = []
    
    # 1. Efeito: Aprender Skill (TOMOS)
    if "learn_skill" in effects:
        skill_id = effects["learn_skill"]
        skill_info = SKILL_DATA.get(skill_id)
        
        if not skill_info:
            messages.append("⚠️ A habilidade deste tomo parece não existir mais.")
        else:
            # Verifica se já tem a skill
            current_skills = player_data.get("skills", {})
            # Garante que é um dicionário (correção de bugs antigos)
            if not isinstance(current_skills, dict):
                current_skills = {} 
                player_data["skills"] = current_skills

            if skill_id in current_skills:
                messages.append(f"⚠️ Você já conhece a técnica {skill_info['display_name']}!")
                # Nota: Idealmente você retornaria False para não consumir o item, 
                # mas aqui vamos apenas avisar.
            else:
                # --- A MÁGICA ACONTECE AQUI ---
                # Salva a skill no formato correto (Dicionário com raridade)
                player_data["skills"][skill_id] = {
                    "rarity": "comum",
                    "progress": 0
                }
                messages.append(f"✨ <b>Nova Habilidade Aprendida:</b> {skill_info['display_name']}!")

    # 2. Efeito: Skins
    if "grant_skin" in effects:
        skin_id = effects["grant_skin"]
        unlocked = player_data.get("unlocked_skins", [])
        if skin_id not in unlocked:
            unlocked.append(skin_id)
            player_data["unlocked_skins"] = unlocked
            messages.append(f"👘 Nova aparência desbloqueada!")
        else:
            messages.append("⚠️ Você já possui esta aparência.")

    # 3. Efeitos de Poção (Cura, XP, Energia...)
    if "heal" in effects:
        amount = effects["heal"]
        stats = get_player_total_stats(player_data) # Certifique-se de importar isso
        old_hp = player_data.get("current_hp", 0)
        max_hp = stats["max_hp"]
        new_hp = min(max_hp, old_hp + amount)
        player_data["current_hp"] = new_hp
        recovered = new_hp - old_hp
        if recovered > 0:
            messages.append(f"❤️ Recuperou {recovered} HP.")
        else:
            messages.append("❤️ HP já está cheio.")

    if "add_energy" in effects:
        amount = effects["add_energy"]
        player_data["energy"] = player_data.get("energy", 0) + amount
        messages.append(f"⚡ Recuperou {amount} Energia.")

    if "add_xp" in effects:
        amount = effects["add_xp"]
        # Aqui você chamaria sua função de dar XP
        player_data["xp"] = player_data.get("xp", 0) + amount
        messages.append(f"🧠 Ganhou {amount} XP.")

    return messages

def add_energy(player_data: dict, amount: int = 1) -> dict:
    max_e = get_player_max_energy(player_data)
    cur = _ival(player_data.get('energy', 0))
    player_data['energy'] = max(0, min(cur + int(amount), max_e))
    return player_data

def sanitize_and_cap_energy(player_data: dict):
    max_e = get_player_max_energy(player_data)
    current_raw = player_data.get("energy")
    current_val = _ival(current_raw, max_e) if current_raw is not None else max_e
    player_data["energy"] = max(0, min(current_val, max_e))
    
    # Se timestamp inválido ou antigo demais, reseta
    if not player_data.get('energy_last_ts'):
        anchor = _parse_iso(player_data.get('last_energy_ts')) or utcnow()
        player_data['energy_last_ts'] = anchor.isoformat()
    player_data.pop('last_energy_ts', None)

def _get_regen_seconds(player_data: dict) -> int:
    premium = PremiumManager(player_data)
    return max(1, int(premium.get_perk_value('energy_regen_seconds', 420)))

def _apply_energy_autoregen_inplace(player_data: dict) -> bool:
    changed = False
    max_e = get_player_max_energy(player_data)
    cur = _ival(player_data.get('energy'), 0)
    
    last_raw = player_data.get('energy_last_ts') or player_data.get('last_energy_ts')
    now = utcnow()
    last_ts = _parse_iso(last_raw)

    # Proteção contra relógio no futuro
    if last_ts is None or last_ts > now:
        player_data['energy_last_ts'] = now.isoformat()
        return True 

    regen_s = _get_regen_seconds(player_data)
    
    # Se cheio, mantém relógio atualizado
    if cur >= max_e:
        player_data['energy_last_ts'] = now.isoformat()
        return last_raw != player_data['energy_last_ts']

    elapsed = (now - last_ts).total_seconds()
    if elapsed < regen_s: return False

    gained = int(elapsed // regen_s)
    if gained > 0:
        new_energy = min(max_e, cur + gained)
        if new_energy != cur:
            player_data['energy'] = new_energy
            changed = True
        
        # Avança relógio preservando resto
        if new_energy >= max_e:
            player_data['energy_last_ts'] = now.isoformat()
        else:
            remainder = elapsed % regen_s
            player_data['energy_last_ts'] = (now - timedelta(seconds=remainder)).isoformat()
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
        speed_mult = max(0.1, float(premium.get_perk_value("gather_speed_multiplier", 1.0)))
    except: speed_mult = 1.0
    return max(1, int(base_seconds / speed_mult))

def _gather_cost(player_data: dict) -> int:
    try: return int(PremiumManager(player_data).get_perk_value("gather_energy_cost", 1))
    except: return 1

def _gather_xp_mult(player_data: dict) -> float:
    try: return float(PremiumManager(player_data).get_perk_value("gather_xp_multiplier", 1.0))
    except: return 1.0

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
    
    if action not in ("exploring", "travel", "crafting", "working", "auto_hunting", "collecting", "refining", "dismantling"):
        return False, None

    try:
        finish_iso = state.get("finish_time")
        if not finish_iso:
            player_data["player_state"] = {"action": "idle"}
            await save_player_data(user_id, player_data)
            return True, f"Ação '{action}' limpa (sem tempo)."

        if utcnow() < _parse_iso(finish_iso): return False, None

        reward_summary = f"Sua ação '{action}' foi interrompida (reinício)."
        if action == "travel":
            dest = (state.get("details") or {}).get("destination")
            if dest: player_data["current_location"] = dest
            reward_summary = f"Você chegou a {dest}."
        
        player_data["player_state"] = {"action": "idle"}
        await save_player_data(user_id, player_data)
        return True, reward_summary

    except Exception as e:
        logger.error(f"Erro em try_finalize_timed_action: {e}")
        try:
            player_data["player_state"] = {"action": "idle"}
            await save_player_data(user_id, player_data)
        except: pass
        return True, "Ação finalizada por erro."

# -------------------------
# PvP & Outros
# -------------------------
DEFAULT_PVP_ENTRIES = 10
def get_pvp_entries(player_data: dict) -> int:
    today = utcnow().date().isoformat()
    if player_data.get("last_pvp_entry_reset") != today:
        player_data["pvp_entries_left"] = DEFAULT_PVP_ENTRIES
        player_data["last_pvp_entry_reset"] = today
    return player_data.get("pvp_entries_left", DEFAULT_PVP_ENTRIES)

def use_pvp_entry(player_data: dict) -> bool:
    current = get_pvp_entries(player_data)
    if current > 0:
        player_data["pvp_entries_left"] = current - 1
        return True
    return False

def add_pvp_entries(player_data: dict, amount: int):
    player_data["pvp_entries_left"] = get_pvp_entries(player_data) + amount

def get_pvp_points(player_data: dict) -> int:
    return _ival(player_data.get("pvp_points"), 0)

def add_pvp_points(player_data: dict, amount: int):
    val = max(0, get_pvp_points(player_data) + int(amount))
    player_data["pvp_points"] = val
    return val

async def heal_player(player_data: dict, amount: int):
    stats = await get_player_total_stats(player_data)
    max_hp = stats.get('max_hp', 1)
    player_data['current_hp'] = min(max_hp, _ival(player_data.get('current_hp', 0)) + int(amount))

def add_buff(player_data: dict, buff_info: dict):
    if 'active_buffs' not in player_data: player_data['active_buffs'] = []
    player_data['active_buffs'].append({
        "stat": buff_info.get("stat"),
        "value": buff_info.get("value"),
        "turns_left": buff_info.get("duration_turns")
    })

async def check_stale_actions_on_startup(application: Application):
    """
    Verifica ações presas. 
    IMPORTS MOVIDOS PARA CÁ PARA EVITAR CICLO COM auto_hunt_engine.
    """
    if players_collection is None: return
    
    # -----------------------------------------------------
    # ✅ IMPORTS LOCAIS (O SEGREDO PARA NÃO TRAVAR)
    # -----------------------------------------------------
    from modules.auto_hunt_engine import finish_auto_hunt_job
    from handlers.menu.region import finish_travel_job
    from handlers.job_handler import finish_collection_job
    from handlers.forge_handler import finish_craft_notification_job
    from handlers.refining_handler import finish_refine_job, finish_dismantle_job
    # -----------------------------------------------------

    logger.info("[Watchdog] Verificando ações presas...")
    now = utcnow()
    actions_to_check = ("auto_hunting", "travel", "collecting", "crafting", "working", "refining", "dismantling")
    query = {"player_state.action": {"$in": list(actions_to_check)}}

    try:
        cursor = players_collection.find(query)
        for pdata in cursor:
            user_id = pdata.get("_id")
            chat_id = pdata.get("last_chat_id", user_id)
            state = pdata.get("player_state", {})
            action = state.get("action")
            details = state.get("details") or {}
            
            finish_iso = state.get("finish_time")
            end_time = _parse_iso(finish_iso) if finish_iso else None

            # Limpa auto-hunt bugado sem tempo
            if action == "auto_hunting" and not end_time:
                pdata["player_state"] = {"action": "idle"}
                await save_player_data(user_id, pdata)
                continue
            
            if not end_time: continue

            try:
                delay = 1 if now >= end_time else (end_time - now).total_seconds()
                prefix = f"watchdog_{action}_{user_id}"

                if action == "auto_hunting":
                    job_data = {
                        "user_id": user_id, "chat_id": chat_id,
                        "message_id": state.get("message_id"),
                        "hunt_count": details.get('hunt_count'),
                        "region_key": details.get('region_key')
                    }
                    application.job_queue.run_once(finish_auto_hunt_job, when=delay, data=job_data, name=f"{prefix}_ah")

                elif action == "travel":
                    application.job_queue.run_once(finish_travel_job, when=delay, user_id=user_id, chat_id=chat_id, data={"dest": details.get("destination")}, name=f"{prefix}_tr")

                elif action == "collecting":
                    job_data = {
                        'resource_id': details.get("resource_id"),
                        'item_id_yielded': details.get("item_id_yielded"), 
                        'quantity': details.get("quantity", 1), # Garante quantidade
                        'message_id': details.get("collect_message_id") # Garante message_id
                    }
                    application.job_queue.run_once(finish_collection_job, when=delay, user_id=user_id, chat_id=chat_id, data=job_data, name=f"{prefix}_col")

                elif action == "crafting":
                    application.job_queue.run_once(finish_craft_notification_job, when=delay, user_id=user_id, chat_id=chat_id, data={"recipe_id": details.get("recipe_id")}, name=f"{prefix}_cr")

                elif action == "refining":
                    application.job_queue.run_once(finish_refine_job, when=delay, user_id=user_id, chat_id=chat_id, data={"recipe_id": details.get("recipe_id")}, name=f"{prefix}_ref")

                elif action == "dismantling":
                    application.job_queue.run_once(finish_dismantle_job, when=delay, user_id=user_id, chat_id=chat_id, data={}, name=f"{prefix}_dis")

            except Exception as e:
                logger.error(f"[Watchdog] Erro user {user_id}: {e}")
                try:
                    pdata["player_state"] = {"action": "idle"}
                    await save_player_data(user_id, pdata)
                except: pass
    except Exception as e:
        logger.error(f"[Watchdog] Erro Geral: {e}")