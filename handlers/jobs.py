# Arquivo: handlers/jobs.py (VERSÃO FINAL: DB BLINDADO + VISUAL ATUALIZADO)

from __future__ import annotations

import logging
import datetime
import asyncio
import os
from zoneinfo import ZoneInfo
from typing import Dict, Optional, Any, Tuple, Iterator
from telegram.ext import ContextTypes
from telegram.error import Forbidden

# --- 1. MONGODB IMPORTS ---
from pymongo import MongoClient
import certifi

from modules import player_manager
# Módulos do player
from modules.player_manager import (
    iter_players, add_energy, save_player_data, has_premium_plan,
    get_perk_value, get_player_max_energy, add_item_to_inventory,
    get_pvp_points, add_gems, get_player_data, iter_player_ids
)

# --- 2. IMPORTAÇÃO DO CACHE (A CORREÇÃO VISUAL) ---
try:
    from modules.player.core import player_cache
except ImportError:
    # Se falhar, define um dict vazio para não quebrar o bot, 
    # mas o visual pode demorar a atualizar.
    player_cache = {}

from config import EVENT_TIMES, JOB_TIMEZONE
from kingdom_defense.engine import event_manager

# Imports opcionais de handlers
try:
    from handlers.refining_handler import finish_dismantle_job, finish_refine_job
    from handlers.forge_handler import finish_craft_notification_job as finish_crafting_job
    from handlers.job_handler import finish_collection_job
    from handlers.menu.region import finish_travel_job
except ImportError:
    pass 

from modules.player.actions import _parse_iso as _parse_iso_utc 
from pvp.pvp_config import MONTHLY_RANKING_REWARDS

logger = logging.getLogger(__name__)

# ==============================================================================
# CONFIGURAÇÃO BLINDADA DO MONGODB
# ==============================================================================
MONGO_STR = "mongodb+srv://eldora-cluster:pb060987@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

players_col = None

try:
    client = MongoClient(MONGO_STR, tlsCAFile=certifi.where())
    db = client["eldora_db"]
    players_col = db["players"]
    logger.info("✅ [JOBS] Conexão SEGURA estabelecida. Ouro e Energia sincronizados.")
except Exception as e:
    logger.critical(f"❌ [JOBS] FALHA CRÍTICA NA CONEXÃO: {e}")
    players_col = None

# ==============================================================================

# --- CONSTANTES ---
DAILY_CRYSTAL_ITEM_ID = "cristal_de_abertura"
DAILY_CRYSTAL_BASE_QTY = 4
DAILY_NOTIFY_USERS = True
_non_premium_tick: Dict[str, int] = {"count": 0}

# IDs ANÚNCIOS
ANNOUNCEMENT_CHAT_ID = -1002881364171 
ANNOUNCEMENT_THREAD_ID = 24 

# --- HELPERS ---
def _today_str(tzname: str = JOB_TIMEZONE) -> str:
    try:
        tz = ZoneInfo(tzname)
        now = datetime.datetime.now(tz)
    except Exception:
        now = datetime.datetime.now()
    return now.date().isoformat()

def _safe_add_stack(pdata: dict, item_id: str, qty: int) -> None:
    try:
        add_item_to_inventory(pdata, item_id, qty)
    except Exception as e:
        logger.debug("[_safe_add_stack] Fallback: %s", e)
        inv = pdata.setdefault("inventory", {})
        inv[item_id] = int(inv.get(item_id, 0)) + int(qty)

# --- JOBS PRINCIPAIS ---

async def regenerate_energy_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Regenera energia no Banco ($inc) E na Memória (Cache).
    """
    _non_premium_tick["count"] = (_non_premium_tick["count"] + 1) % 2
    regenerate_non_premium = (_non_premium_tick["count"] == 0)
    
    touched = 0 
    processed_count = 0 
    
    try:
        async for user_id, pdata in player_manager.iter_players():
            processed_count += 1
            try:
                if not isinstance(pdata, dict): continue

                # Tenta pegar a versão mais recente da memória, se existir
                current_data = player_cache.get(user_id, pdata)

                max_e = int(player_manager.get_player_max_energy(current_data)) 
                cur_e = int(current_data.get("energy", 0))
                
                if cur_e >= max_e: continue 

                is_premium = player_manager.has_premium_plan(current_data) 
                
                if is_premium or regenerate_non_premium:
                    # --- ATUALIZAÇÃO DUPLA (BANCO + MEMÓRIA) ---
                    if players_col is not None:
                        # 1. Atualiza o Banco (Segurança)
                        players_col.update_one(
                            {"_id": user_id}, 
                            {"$inc": {"energy": 1}}
                        )
                        
                        # 2. Atualiza a Memória (Visual)
                        # Isso garante que o jogador veja a energia subindo na hora
                        current_data["energy"] = cur_e + 1
                        
                        touched += 1
                    else:
                        # Fallback
                        player_manager.add_energy(current_data, 1) 
                        await save_player_data(user_id, current_data) 
                        touched += 1
            
            except Exception as e_player:
                logger.warning(f"[ENERGY] Falha no jogador {user_id}: {e_player}")

    except Exception as e_iter:
        logger.error(f"Erro regenerate_energy_job: {e_iter}")
            
    logger.info(f"[ENERGY] Job concluído. Processados: {processed_count}. Regenerados: {touched}.")

async def daily_crystal_grant_job(context: ContextTypes.DEFAULT_TYPE) -> int:
    today = _today_str()
    granted = 0
    try:
        async for user_id, pdata in player_manager.iter_players():
            try:
                if not pdata: continue
                daily = pdata.get("daily_awards") or {}
                if daily.get("last_crystal_date") == today: continue

                bonus_qty = get_perk_value(pdata, "daily_crystal_bonus", 0) 
                total_qty = DAILY_CRYSTAL_BASE_QTY + bonus_qty
                
                _safe_add_stack(pdata, DAILY_CRYSTAL_ITEM_ID, total_qty)
                daily["last_crystal_date"] = today
                pdata["daily_awards"] = daily
                
                await save_player_data(user_id, pdata) 
                granted += 1
                
                if DAILY_NOTIFY_USERS:
                    msg = f"🎁 Recebeu {total_qty}x Cristais Diários."
                    if bonus_qty > 0: msg += f" (+{bonus_qty} bônus)"
                    try: 
                        await context.bot.send_message(chat_id=user_id, text=msg)
                        await asyncio.sleep(0.1) 
                    except Exception: pass
            except Exception: pass
    except Exception: pass
    return granted

async def force_grant_daily_crystals(context: ContextTypes.DEFAULT_TYPE) -> int:
    granted = 0
    try:
        async for user_id, pdata in player_manager.iter_players():
            try:
                if not pdata: continue
                _safe_add_stack(pdata, DAILY_CRYSTAL_ITEM_ID, DAILY_CRYSTAL_BASE_QTY)
                daily = pdata.get("daily_awards") or {}
                daily["last_crystal_date"] = _today_str()
                pdata["daily_awards"] = daily
                await save_player_data(user_id, pdata) 
                granted += 1
                try: 
                    await context.bot.send_message(chat_id=user_id, text=f"🎁 Admin enviou {DAILY_CRYSTAL_BASE_QTY}x Cristais!")
                    await asyncio.sleep(0.1) 
                except Exception: pass
            except Exception: pass
    except Exception: pass
    return granted

async def daily_event_ticket_job(context: ContextTypes.DEFAULT_TYPE) -> int:
    return await distribute_kingdom_defense_ticket_job(context)

async def distribute_kingdom_defense_ticket_job(context: ContextTypes.DEFAULT_TYPE) -> int:
    job_data = context.job.data or {}
    event_time_str = job_data.get("event_time", "horário desconhecido")
    TICKET_ID = "ticket_defesa_reino"
    
    delivered = 0
    all_player_ids = []
    try: all_player_ids = list(player_manager.iter_player_ids())
    except Exception: return 0

    for user_id in all_player_ids:
        try:
            pdata = await player_manager.get_player_data(user_id)
            if not pdata: continue
            _safe_add_stack(pdata, TICKET_ID, 1)
            await save_player_data(user_id, pdata)
            delivered += 1
            try:
                await context.bot.send_message(chat_id=user_id, text=f"🎟️ Recebeu Ticket de Defesa para as {event_time_str}!", parse_mode='HTML')
                await asyncio.sleep(0.05) 
            except Exception: pass
        except Exception: pass
    return delivered

async def afternoon_event_reminder_job(context: ContextTypes.DEFAULT_TYPE) -> int:
    notified = 0
    try:
        async for user_id, _ in player_manager.iter_players(): 
            try:
                await context.bot.send_message(chat_id=user_id, text="🔔 <b>LEMBRETE:</b> Invasão às 14:00!", parse_mode='HTML')
                await asyncio.sleep(0.1) 
                notified += 1
            except Exception: pass
    except Exception: pass
    return notified

async def _process_watchdog_for_player(context: ContextTypes.DEFAULT_TYPE, user_id: int, now: datetime.datetime, ACTION_FINISHERS: Dict[str, Any]) -> int:
    try:
        pdata = await player_manager.get_player_data(user_id)
        if not pdata: return 0
        st = pdata.get("player_state") or {}
        action = st.get("action")
        if not action or action not in ACTION_FINISHERS: return 0

        ft = _parse_iso_utc(st.get("finish_time")) 
        if not ft or ft > now: return 0

        config = ACTION_FINISHERS[action]
        finalizer_fn = config.get("fn")
        if not finalizer_fn: return 0
        
        job_data = config.get("data_builder")(st) if "data_builder" in config else {}
        chat_id = pdata.get("last_chat_id", user_id)

        context.job_queue.run_once(
            finalizer_fn, when=0, chat_id=chat_id, user_id=user_id,
            data=job_data, name=f"{action}:{user_id}",
        )
        return 1 
    except Exception: return 0
        
async def timed_actions_watchdog(context: ContextTypes.DEFAULT_TYPE) -> None:
    ACTION_FINISHERS: Dict[str, Any] = {}
    now = datetime.datetime.now(datetime.timezone.utc)
    if not ACTION_FINISHERS: return
    tasks = []
    try:
        async for user_id, _ in player_manager.iter_players(): 
            tasks.append(_process_watchdog_for_player(context, user_id, now, ACTION_FINISHERS))
        if tasks: await asyncio.gather(*tasks)
    except Exception: pass

async def distribute_pvp_rewards(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Distribuindo PvP...")
    all_players_ranked = []
    try:
        async for user_id, p_data in player_manager.iter_players():
            try:
                if not p_data: continue
                pts = player_manager.get_pvp_points(p_data)
                if pts > 0: all_players_ranked.append({"user_id": user_id, "points": pts})
            except Exception: pass
    except Exception: return

    all_players_ranked.sort(key=lambda p: p["points"], reverse=True)
    winners_info = [] 
    
    if MONTHLY_RANKING_REWARDS:
        for i, player in enumerate(all_players_ranked):
            rank = i + 1
            reward_amount = MONTHLY_RANKING_REWARDS.get(rank)
            if reward_amount:
                user_id = player["user_id"]
                try:
                    if players_col is not None:
                         players_col.update_one({"_id": user_id}, {"$inc": {"gems": reward_amount}})
                         winners_info.append(f"{rank}º: ID {user_id} (+{reward_amount}💎)")
                         try: await context.bot.send_message(chat_id=user_id, text=f"🏆 Rank {rank}: Recebeu {reward_amount} gemas!")
                         except Exception: pass
                    else:
                        p_data = await player_manager.get_player_data(user_id)
                        player_manager.add_gems(p_data, reward_amount)
                        await save_player_data(user_id, p_data)
                except Exception: pass
            else:
                 if rank > max(MONTHLY_RANKING_REWARDS.keys(), default=0): break
    
    if winners_info:
        try: await context.bot.send_message(chat_id=ANNOUNCEMENT_CHAT_ID, message_thread_id=ANNOUNCEMENT_THREAD_ID, text="🏆 <b>Ranking PvP Finalizado!</b>", parse_mode="HTML")
        except Exception: pass

async def reset_pvp_season(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Reset PvP...")
    if players_col is not None:
        players_col.update_many({}, {"$set": {"pvp_points": 0}})
    else:
        async for user_id, p_data in player_manager.iter_players():
            if p_data.get("pvp_points", 0) > 0:
                p_data["pvp_points"] = 0
                await save_player_data(user_id, p_data)
    try: await context.bot.send_message(chat_id=ANNOUNCEMENT_CHAT_ID, message_thread_id=ANNOUNCEMENT_THREAD_ID, text="⚔️ <b>Nova Temporada PvP!</b>", parse_mode="HTML")
    except Exception: pass

async def start_kingdom_defense_event(context: ContextTypes.DEFAULT_TYPE):
    try:
        duration = (context.job.data or {}).get("event_duration_minutes", 30) 
        await event_manager.start_event()
        await context.bot.send_message(chat_id=ANNOUNCEMENT_CHAT_ID, message_thread_id=ANNOUNCEMENT_THREAD_ID, text=f"⚔️ <b>INVASÃO!</b> ({duration} min)", parse_mode="HTML")
    except Exception: pass

async def end_kingdom_defense_event(context: ContextTypes.DEFAULT_TYPE):
    try:
        success, msg = await event_manager.end_event()
        if success:
            await context.bot.send_message(chat_id=ANNOUNCEMENT_CHAT_ID, message_thread_id=ANNOUNCEMENT_THREAD_ID, text=f"🛡️ <b>FIM DA INVASÃO!</b>\n{msg}", parse_mode="HTML")
    except Exception: pass

async def daily_arena_ticket_job(context: ContextTypes.DEFAULT_TYPE) -> int:
    today = _today_str()
    granted = 0
    TICKET_ID = "ticket_arena"
    TICKET_QTY = 10
    async for user_id, pdata in player_manager.iter_players():
        try:
            if not pdata: continue
            daily = pdata.get("daily_awards") or {}
            if daily.get("last_arena_ticket_date") == today: continue
            _safe_add_stack(pdata, TICKET_ID, TICKET_QTY)
            daily["last_arena_ticket_date"] = today
            pdata["daily_awards"] = daily
            await save_player_data(user_id, pdata)
            granted += 1
            try: await context.bot.send_message(chat_id=user_id, text=f"🎟️ Recebeu {TICKET_QTY} Tickets Arena!")
            except Exception: pass
        except Exception: pass
    return granted