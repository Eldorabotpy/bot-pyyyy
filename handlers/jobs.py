# Arquivo: handlers/jobs.py (VERSÃO FINAL: NOTIFICAÇÃO DE LOCAL E ABA DE AVISOS)

from __future__ import annotations

import logging
import datetime
import asyncio
from zoneinfo import ZoneInfo
from typing import Dict, Optional, Any
from telegram.ext import ContextTypes

# --- MONGODB IMPORTS ---
from pymongo import MongoClient
import certifi

from modules import player_manager
from modules.player_manager import (
    save_player_data, get_perk_value, 
    add_item_to_inventory, iter_player_ids
)

# --- CONFIG & MANAGERS ---
# Importa IDs do Grupo e da Aba de Avisos
from config import EVENT_TIMES, JOB_TIMEZONE, ANNOUNCEMENT_CHAT_ID, ANNOUNCEMENT_THREAD_ID

# Importações dos Engines
try:
    from modules.world_boss.engine import (
        world_boss_manager, 
        broadcast_boss_announcement, 
        distribute_loot_and_announce
    )
except ImportError:
    world_boss_manager = None

try:
    from kingdom_defense.engine import event_manager
except ImportError:
    event_manager = None

from pvp.pvp_config import MONTHLY_RANKING_REWARDS

logger = logging.getLogger(__name__)

# ==============================================================================
# CONFIGURAÇÃO DO MONGODB
# ==============================================================================
MONGO_STR = "mongodb+srv://eldora-cluster:pb060987@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
players_col = None

try:
    client = MongoClient(MONGO_STR, tlsCAFile=certifi.where())
    db = client["eldora_db"]
    players_col = db["players"]
    logger.info("✅ [JOBS] Conexão MongoDB OK.")
except Exception as e:
    logger.critical(f"❌ [JOBS] FALHA CRÍTICA NA CONEXÃO MONGODB: {e}")
    players_col = None

# ==============================================================================
# CONSTANTES E UTILITÁRIOS
# ==============================================================================
DAILY_CRYSTAL_ITEM_ID = "cristal_de_abertura"
DAILY_CRYSTAL_BASE_QTY = 4
DAILY_NOTIFY_USERS = True
_non_premium_tick: Dict[str, int] = {"count": 0}

def _today_str(tzname: str = JOB_TIMEZONE) -> str:
    try:
        tz = ZoneInfo(tzname)
        now = datetime.datetime.now(tz)
    except Exception:
        now = datetime.datetime.now()
    return now.date().isoformat()

# ==============================================================================
# 👹 JOB: WORLD BOSS (Lógica de Notificação Ajustada)
# ==============================================================================
async def start_world_boss_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Nasce o World Boss e notifica:
    1. Grupo na Aba de Avisos (Com local formatado).
    2. Jogadores no Privado (Broadcast).
    """
    if not world_boss_manager:
        logger.error("⚠️ [JOB] Manager do Boss não encontrado/importado.")
        return

    if world_boss_manager.is_active:
         logger.info("👹 [JOB] Boss já está vivo. Ignorando spawn.")
         return

    logger.info("👹 [JOB] Invocando World Boss...")
    
    # Inicia e recebe o local (ex: "floresta_sombria")
    result = world_boss_manager.start_event()
    
    if result.get("success"):
        location_key = result.get('location', 'desconhecido')
        # Formata o texto para ficar bonito no grupo (ex: "Floresta Sombria")
        location_display = location_key.replace("_", " ").title()
        
        # 1. Notifica no Canal/Grupo (Aba de Avisos)
        if ANNOUNCEMENT_CHAT_ID:
            try:
                msg_text = (
                    f"👹 <b>WORLD BOSS SURGIU!</b>\n\n"
                    f"📍 <b>Local:</b> {location_display}\n\n"
                    f"O monstro despertou! Corram para derrotá-lo!"
                )
                
                await context.bot.send_message(
                    chat_id=ANNOUNCEMENT_CHAT_ID, 
                    message_thread_id=ANNOUNCEMENT_THREAD_ID, # ✅ Envia para a Aba correta
                    text=msg_text, 
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"❌ ERRO NOTIFICAR GRUPO (BOSS): {e}")
        
        # 2. Broadcast (DM para os players)
        # Passamos a chave original, o engine.py cuida de buscar o nome oficial do game_data
        try:
            await broadcast_boss_announcement(context.application, location_key)
        except Exception as e:
            logger.error(f"Erro no broadcast do boss: {e}")
    else:
        logger.error(f"Falha ao iniciar Boss: {result.get('error')}")

async def end_world_boss_job(context: ContextTypes.DEFAULT_TYPE):
    if not world_boss_manager: return

    if not world_boss_manager.is_active:
        return

    logger.info("👹 [JOB] O tempo acabou! Removendo o Boss...")
    battle_results = world_boss_manager.end_event(reason="Tempo esgotado")
    await distribute_loot_and_announce(context, battle_results)

# ==============================================================================
# 🛡️ JOB: KINGDOM DEFENSE
# ==============================================================================
async def start_kingdom_defense_event(context: ContextTypes.DEFAULT_TYPE):
    """Inicia o evento e notifica Grupo e Jogadores."""
    if not event_manager:
        logger.error("⚠️ [JOB] Event Manager (KD) não encontrado.")
        return

    job_data = context.job.data or {}
    duration_minutes = job_data.get("event_duration_minutes", 30)
    location_name = "🏰 Portões do Reino" # Local Fixo

    try:
        await event_manager.start_event()
        
        msg_text = (
            f"⚔️ <b>INVASÃO AO REINO!</b>\n\n"
            f"📍 <b>Local:</b> {location_name}\n"
            f"⏳ <b>Duração:</b> {duration_minutes} minutos\n\n"
            f"Preparem suas defesas!"
        )

        # 1. Notifica no Grupo (Aba de Avisos)
        if ANNOUNCEMENT_CHAT_ID:
            try:
                await context.bot.send_message(
                    chat_id=ANNOUNCEMENT_CHAT_ID, 
                    message_thread_id=ANNOUNCEMENT_THREAD_ID, # ✅ Aba correta
                    text=msg_text, 
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"❌ ERRO NOTIFICAR GRUPO (KD): {e}")
        
        # 2. Notifica JOGADORES (Broadcast DM)
        async for user_id, _ in player_manager.iter_players():
            try:
                await context.bot.send_message(chat_id=user_id, text=msg_text, parse_mode="HTML")
                await asyncio.sleep(0.05) 
            except Exception: 
                continue

        # 3. Agenda o FIM
        context.job_queue.run_once(
            end_kingdom_defense_event, 
            when=duration_minutes * 60,
            name="auto_end_kingdom_defense"
        )
        logger.info(f"🛡️ Defesa Iniciada.")

    except Exception as e:
        logger.error(f"Erro ao iniciar Kingdom Defense: {e}")

async def end_kingdom_defense_event(context: ContextTypes.DEFAULT_TYPE):
    if not event_manager: return
    try:
        success, msg = await event_manager.end_event()
        if success:
            if ANNOUNCEMENT_CHAT_ID:
                try:
                    await context.bot.send_message(
                        chat_id=ANNOUNCEMENT_CHAT_ID, 
                        message_thread_id=ANNOUNCEMENT_THREAD_ID,
                        text=f"🛡️ <b>FIM DA INVASÃO!</b>\n{msg}", 
                        parse_mode="HTML"
                    )
                except: pass
    except Exception as e:
        logger.error(f"Erro ao finalizar Kingdom Defense: {e}")

# ==============================================================================
# 🔧 FUNÇÕES ADMINISTRATIVAS
# ==============================================================================

async def distribute_kingdom_defense_ticket_job(context: ContextTypes.DEFAULT_TYPE) -> int:
    job_data = context.job.data or {} if context.job else {}
    event_time_str = job_data.get("event_time", "breve")
    TICKET_ID = "ticket_defesa_reino"
    delivered = 0
    
    all_player_ids = []
    try: all_player_ids = list(player_manager.iter_player_ids())
    except Exception: return 0

    for user_id in all_player_ids:
        try:
            if players_col is not None:
                players_col.update_one(
                    {"_id": user_id},
                    {"$inc": {f"inventory.{TICKET_ID}": 1}}
                )
                delivered += 1
            else:
                pdata = await player_manager.get_player_data(user_id)
                if not pdata: continue
                player_manager.add_item_to_inventory(pdata, TICKET_ID, 1)
                await save_player_data(user_id, pdata)
                delivered += 1
            
            try:
                await context.bot.send_message(chat_id=user_id, text=f"🎟️ Recebeu 1 Ticket para o evento das {event_time_str}!", parse_mode='HTML')
                await asyncio.sleep(0.05) 
            except Exception: pass
        except Exception: pass
    return delivered

async def daily_event_ticket_job(context: ContextTypes.DEFAULT_TYPE) -> int:
    return await distribute_kingdom_defense_ticket_job(context)

async def force_grant_daily_crystals(context: ContextTypes.DEFAULT_TYPE) -> int:
    granted = 0
    try:
        async for user_id, pdata in player_manager.iter_players():
            try:
                if not pdata: continue
                player_manager.add_item_to_inventory(pdata, DAILY_CRYSTAL_ITEM_ID, DAILY_CRYSTAL_BASE_QTY)
                if "daily_awards" not in pdata: pdata["daily_awards"] = {}
                pdata["daily_awards"]["last_crystal_date"] = _today_str()
                await save_player_data(user_id, pdata)
                granted += 1
                try: await context.bot.send_message(chat_id=user_id, text=f"🎁 Admin enviou {DAILY_CRYSTAL_BASE_QTY}x Cristais!")
                except Exception: pass
            except Exception: pass
    except Exception: pass
    return granted

# ==============================================================================
# ⚔️ PVP E OUTROS JOBS
# ==============================================================================
async def job_pvp_monthly_reset(context: ContextTypes.DEFAULT_TYPE):
    try:
        tz = ZoneInfo(JOB_TIMEZONE)
    except Exception:
        tz = datetime.timezone.utc
    now = datetime.datetime.now(tz)
    
    if now.day != 1: return
    await distribute_pvp_rewards(context)
    await reset_pvp_season(context)

async def distribute_pvp_rewards(context: ContextTypes.DEFAULT_TYPE):
    all_players_ranked = []
    try:
        async for user_id, p_data in player_manager.iter_players():
            try:
                pts = player_manager.get_pvp_points(p_data)
                if pts > 0: all_players_ranked.append({"user_id": user_id, "points": pts})
            except: pass
    except: return

    all_players_ranked.sort(key=lambda p: p["points"], reverse=True)
    if MONTHLY_RANKING_REWARDS:
        for i, player in enumerate(all_players_ranked):
            rank = i + 1
            reward_amount = MONTHLY_RANKING_REWARDS.get(rank)
            if reward_amount:
                user_id = player["user_id"]
                if players_col is not None:
                     players_col.update_one({"_id": user_id}, {"$inc": {"gems": reward_amount}})
                     try: await context.bot.send_message(chat_id=user_id, text=f"🏆 Rank {rank}: Recebeu {reward_amount} gemas!")
                     except: pass
    if ANNOUNCEMENT_CHAT_ID:
        try: await context.bot.send_message(chat_id=ANNOUNCEMENT_CHAT_ID, message_thread_id=ANNOUNCEMENT_THREAD_ID, text="🏆 <b>Ranking PvP Finalizado!</b>", parse_mode="HTML")
        except: pass

async def reset_pvp_season(context: ContextTypes.DEFAULT_TYPE):
    if players_col is not None:
        players_col.update_many({}, {"$set": {"pvp_points": 0}})
    if ANNOUNCEMENT_CHAT_ID:
        try: await context.bot.send_message(chat_id=ANNOUNCEMENT_CHAT_ID, message_thread_id=ANNOUNCEMENT_THREAD_ID, text="⚔️ <b>Nova Temporada PvP!</b>", parse_mode="HTML")
        except: pass

async def regenerate_energy_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    _non_premium_tick["count"] = (_non_premium_tick["count"] + 1) % 2
    regenerate_non_premium = (_non_premium_tick["count"] == 0)
    
    try:
        async for user_id, pdata in player_manager.iter_players():
            try:
                if not isinstance(pdata, dict): continue
                max_e = int(player_manager.get_player_max_energy(pdata)) 
                cur_e = int(pdata.get("energy", 0))
                if cur_e >= max_e: continue 

                is_premium = player_manager.has_premium_plan(pdata) 
                
                if is_premium or regenerate_non_premium:
                    if players_col is not None:
                        players_col.update_one({"_id": user_id}, {"$inc": {"energy": 1}})
                        try:
                            if hasattr(player_manager, "clear_player_cache"):
                                res = player_manager.clear_player_cache(user_id)
                                if asyncio.iscoroutine(res): await res
                        except: pass
            except: pass
    except Exception as e:
        logger.error(f"Erro regenerate_energy_job: {e}")

async def daily_crystal_grant_job(context: ContextTypes.DEFAULT_TYPE) -> int:
    today = _today_str()
    granted = 0
    try:
        async for user_id, pdata in player_manager.iter_players():
            try:
                daily = pdata.get("daily_awards") or {}
                if daily.get("last_crystal_date") == today: continue
                
                if players_col is not None:
                    players_col.update_one(
                        {"_id": user_id},
                        {
                            "$inc": {f"inventory.{DAILY_CRYSTAL_ITEM_ID}": 4},
                            "$set": {"daily_awards.last_crystal_date": today}
                        }
                    )
                    try:
                        if hasattr(player_manager, "clear_player_cache"):
                            res = player_manager.clear_player_cache(user_id)
                            if asyncio.iscoroutine(res): await res
                    except: pass
                
                if DAILY_NOTIFY_USERS:
                    msg = f"🎁 Você recebeu 4× Cristal de Abertura."
                    try: await context.bot.send_message(chat_id=user_id, text=msg)
                    except: pass
                granted += 1
            except: pass
    except Exception: pass
    return granted

async def daily_arena_ticket_job(context: ContextTypes.DEFAULT_TYPE) -> int:
    today = _today_str()
    granted = 0
    async for user_id, pdata in player_manager.iter_players():
        try:
            daily = pdata.get("daily_awards") or {}
            if daily.get("last_arena_ticket_date") == today: continue
            
            if players_col is not None:
                players_col.update_one(
                    {"_id": user_id},
                    {
                        "$inc": {f"inventory.ticket_arena": 10},
                        "$set": {"daily_awards.last_arena_ticket_date": today}
                    }
                )
                granted += 1
        except: pass
    return granted

async def afternoon_event_reminder_job(context: ContextTypes.DEFAULT_TYPE) -> int:
    return 0