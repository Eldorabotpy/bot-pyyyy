# handlers/jobs.py

from __future__ import annotations

import logging
import datetime
import asyncio
import certifi
from telegram import Update
from telegram.ext import CommandHandler
from zoneinfo import ZoneInfo
from typing import Dict, Optional, Any
from telegram.ext import ContextTypes
from modules import game_data
from modules.player.premium import PremiumManager
# --- AUTH IMPORT ---
from modules.auth_utils import get_current_player_id
# --- MONGODB IMPORTS ---
from pymongo import MongoClient
from bson import ObjectId
from modules import player_manager
from modules.player_manager import (
    save_player_data, get_perk_value, 
    add_item_to_inventory, iter_player_ids
)

# --- CONFIG & MANAGERS ---
from config import EVENT_TIMES, JOB_TIMEZONE, ANNOUNCEMENT_CHAT_ID, ANNOUNCEMENT_THREAD_ID
from pvp.pvp_scheduler import executar_reset_pvp
from modules.world_boss.engine import (
    world_boss_manager, 
    broadcast_boss_announcement, 
    distribute_loot_and_announce
)

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
users_col = None
try:
    client = MongoClient(MONGO_STR, tlsCAFile=certifi.where())
    db = client["eldora_db"]
    players_col = db["players"]
    users_col = db["users"] 
    logger.info("✅ [JOBS] Conexão MongoDB Híbrida OK.")
except Exception as e:
    logger.critical(f"❌ [JOBS] FALHA CRÍTICA NA CONEXÃO MONGODB: {e}")
    players_col = None
    users_col = None

def get_col_and_id(user_id):
    """
    Retorna a coleção correta e o formato do ID para query.
    BLINDADA contra erro de boolean do PyMongo.
    """
    # 1. Se já for ObjectId
    if isinstance(user_id, ObjectId):
        if users_col is not None:
            return users_col, user_id
        return None, None

    # 2. Legado (Int)
    if isinstance(user_id, int):
        if players_col is not None:
            return players_col, user_id
        return None, None
    
    # 3. String (Pode ser ObjectId ou Int em string)
    elif isinstance(user_id, str):
        # CORREÇÃO AQUI: Usa "is not None" explicitamente
        if users_col is not None and ObjectId.is_valid(user_id):
            return users_col, ObjectId(user_id)
        if user_id.isdigit():
            if players_col is not None:
                return players_col, int(user_id)
            
    return None, None

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
# ⚔️ JOBS DE ARENA PVP (CORRIGIDOS)
# ==============================================================================

async def daily_pvp_entry_reset_job(context: ContextTypes.DEFAULT_TYPE):
    """Reseta os tickets de arena para 5 diariamente."""
    today = _today_str()
    count = 0
    msg_reset = "⚔️ <b>ARENA DE ELDORA</b>\nSeus tickets diários foram renovados (5/5)! Boa sorte."

    async for user_id, pdata in player_manager.iter_players():
        try:
            last_reset = pdata.get("last_pvp_entry_reset")
            if last_reset == today: continue
            
            col, query_id = get_col_and_id(user_id)
            
            # Fallback para ID numérico se get_col falhar mas for digito
            if col is None and str(user_id).isdigit() and players_col is not None:
                query_id = int(user_id)
                col = players_col

            if col is not None:
                result = col.update_one(
                    {"_id": query_id},
                    {
                        "$set": {
                            "inventory.ticket_arena": 5, 
                            "last_pvp_entry_reset": today
                        }
                    }
                )
                
                if result.modified_count > 0:
                    try:
                        if hasattr(player_manager, "clear_player_cache"):
                            await player_manager.clear_player_cache(user_id)
                    except: pass
                    
                    telegram_chat_id = pdata.get("telegram_id_owner")
                    if not telegram_chat_id and str(user_id).isdigit():
                        telegram_chat_id = int(user_id)
                    
                    if telegram_chat_id:
                        try:
                            await context.bot.send_message(chat_id=telegram_chat_id, text=msg_reset, parse_mode='HTML')
                            await asyncio.sleep(0.05) 
                        except: pass
                    count += 1
        except Exception as e:
            logger.error(f"[JOB PvP] Erro ao resetar usuário {user_id}: {e}")
            continue
        
    logger.info(f"[JOB] Tickets de Arena (Item) resetados para {count} jogadores.")

async def daily_arena_ticket_job(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entrega 10 Tickets de Arena diariamente."""
    today = _today_str()
    granted = 0
    msg_arena = (
        "🎫 <b>SUPRIMENTO DE BATALHA</b>\n"
        "Você recebeu <b>10x 🎟️ Ticket de Arena</b>.\n"
        "<i>Use-os para desafiar oponentes além do limite diário!</i>"
    )

    async for user_id, pdata in player_manager.iter_players():
        try:
            daily = pdata.get("daily_awards") or {}
            if daily.get("last_arena_ticket_date") == today: continue
            
            col, query_id = get_col_and_id(user_id)
            if col is not None:
                col.update_one(
                    {"_id": query_id},
                    {
                        "$inc": {"inventory.ticket_arena": 10},
                        "$set": {"daily_awards.last_arena_ticket_date": today}
                    }
                )
                try: await context.bot.send_message(chat_id=user_id, text=msg_arena, parse_mode='HTML')
                except: pass
                granted += 1
        except: pass
        
    logger.info(f"[JOB] Tickets de Arena entregues: {granted}")

async def distribute_event_ticket(context: ContextTypes.DEFAULT_TYPE):
    logger.info("[JOB] Distribuindo tickets de evento...")
    msg_ticket = (
        "╭─────── [ 📜 <b>DECRETO REAL</b> ] ───────➤\n"
        "│\n"
        "│ ⚔️ <b>AS TROMBETAS SOARAM!</b>\n"
        "│ <i>As forças das trevas marcham contra</i>\n"
        "│ <i>os Portões de Eldora!</i>\n"
        "│\n"
        "│ 📦 <b>SUPRIMENTO DE GUERRA:</b>\n"
        "│ ╰┈➤ 🎟️ <b>1x Ticket de Defesa</b>\n"
        "│\n"
        "╰──────────────────────────────➤\n"
        "🔥 <i>Vá ao menu 'Eventos' e lute!</i>"
    )

    count = 0
    async for user_id, pdata in player_manager.iter_players():
        try:
            col, query_id = get_col_and_id(user_id)
            if col is not None:
                col.update_one(
                    {"_id": query_id},
                    {"$inc": {"inventory.ticket_defesa_reino": 1}}
                )
            else:
                if not pdata: continue
                player_manager.add_item_to_inventory(pdata, "ticket_defesa_reino", 1)
                await player_manager.save_player_data(user_id, pdata)
            
            try:
                await context.bot.send_message(chat_id=user_id, text=msg_ticket, parse_mode='HTML')
                await asyncio.sleep(0.05)
            except Exception: pass
            count += 1
        except Exception: pass
        
    logger.info(f"[JOB] Tickets de evento entregues: {count}")

async def start_world_boss_job(context: ContextTypes.DEFAULT_TYPE):
    if world_boss_manager is None: return
    if world_boss_manager.is_active: return

    logger.info("👹 [JOB] Iniciando World Boss...")
    result = world_boss_manager.start_event()
    
    if result.get("success"):
        location_key = result.get('location', 'desconhecido')
        region_info = (game_data.REGIONS_DATA.get(location_key) or {})
        location_display = region_info.get("display_name", location_key.replace("_", " ").title())
        
        if ANNOUNCEMENT_CHAT_ID:
            try:
                msg_text = (
                    f"👹 𝕎𝕆ℝ𝕃𝔻 𝔹𝕆𝕊𝕊 𝕊𝕌ℝ𝔾𝕀𝕌!\n"
                    f"📍 𝕃𝕠𝕔𝕒𝕝: {location_display}\n"
                    f"O monstro despertou! Ataquem!"
                )
                await context.bot.send_message(
                    chat_id=ANNOUNCEMENT_CHAT_ID, 
                    message_thread_id=ANNOUNCEMENT_THREAD_ID, 
                    text=msg_text, 
                    parse_mode="HTML"
                )
            except Exception: pass
        
        try:
            await broadcast_boss_announcement(context.application, location_key)
        except Exception: pass

async def end_world_boss_job(context: ContextTypes.DEFAULT_TYPE):
    if not world_boss_manager or not world_boss_manager.is_active: return
    logger.info("👹 [JOB] Boss Time Out.")
    battle_results = world_boss_manager.end_event(reason="Tempo esgotado")
    await distribute_loot_and_announce(context, battle_results)


# ==============================================================================
# 🛡️ JOB: KINGDOM DEFENSE
# ==============================================================================

async def start_kingdom_defense_event(context: ContextTypes.DEFAULT_TYPE):
    if not event_manager: return

    job_data = context.job.data or {}
    duration_minutes = job_data.get("event_duration_minutes", 30)
    location_name = "🏰 Portões do Reino" 

    try:
        result = await event_manager.start_event()
        
        if result and "error" in result:
            logger.warning(f"[KD] Evento já ativo ou erro: {result['error']}")
            return

        await distribute_event_ticket(context)

        group_msg = (
            "🔥 <b>INVASÃO EM ANDAMENTO!</b> 🔥\n\n"
            "‼️ <b>ATENÇÃO HERÓIS DE ELDORA!</b>\n"
            f"Monstros estão atacando os <b>{location_name}</b>!\n\n"
            f"⏳ <b>Tempo Restante:</b> {duration_minutes} minutos\n"
            "🎟️ <i>Todos os guerreiros receberam 1 Ticket de entrada!</i>\n"
            "👉 <b>CORRAM PARA O MENU 'DEFESA DO REINO'!</b>"
        )

        if ANNOUNCEMENT_CHAT_ID:
            try:
                thread_id = ANNOUNCEMENT_THREAD_ID if ANNOUNCEMENT_THREAD_ID else None
                await context.bot.send_message(
                    chat_id=ANNOUNCEMENT_CHAT_ID, 
                    message_thread_id=thread_id,
                    text=group_msg, 
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"❌ ERRO NOTIFICAR GRUPO: {e}")

        context.job_queue.run_once(
            end_kingdom_defense_event, 
            when=duration_minutes * 60,
            name="auto_end_kingdom_defense"
        )
        logger.info(f"🛡️ Defesa Iniciada com sucesso.")

    except Exception as e:
        logger.error(f"Erro ao iniciar Kingdom Defense: {e}")

async def end_kingdom_defense_event(context: ContextTypes.DEFAULT_TYPE):
    if not event_manager: return
    if not event_manager.is_active: return

    try:
        await event_manager.end_event() 
        
        end_msg = (
            "🏁 <b>FIM DA INVASÃO!</b> 🏁\n\n"
            "As poeiras da batalha baixaram.\n"
            "Obrigado a todos os defensores!\n\n"
            "🏆 <i>Verifique o Ranking no menu do evento para ver os maiores danos!</i>"
        )

        if ANNOUNCEMENT_CHAT_ID:
            try:
                thread_id = ANNOUNCEMENT_THREAD_ID if ANNOUNCEMENT_THREAD_ID else None
                
                await context.bot.send_message(
                    chat_id=ANNOUNCEMENT_CHAT_ID, 
                    message_thread_id=thread_id,
                    text=end_msg, 
                    parse_mode="HTML"
                )
            except Exception as e:
                 logger.error(f"❌ ERRO NOTIFICAR GRUPO (KD END): {e}")
                 
    except Exception as e:
        logger.error(f"Erro ao finalizar Kingdom Defense: {e}")

# ==============================================================================
# 🔧 FUNÇÕES ADMINISTRATIVAS (Tickets e Recompensas)
# ==============================================================================

async def distribute_kingdom_defense_ticket_job(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data or {} if context.job else {}
    event_time_str = job_data.get("event_time", "agora")
    TICKET_ID = "ticket_defesa_reino"
    delivered = 0
    
    logger.info(f"[JOB] Distribuindo tickets para evento das {event_time_str}...")

    try:
        async for user_id, pdata in player_manager.iter_players():
            try:
                col, query_id = get_col_and_id(user_id)
                
                if col is not None:
                    col.update_one(
                        {"_id": query_id},
                        {"$inc": {f"inventory.{TICKET_ID}": 1}}
                    )
                    delivered += 1
                else:
                    if not pdata: continue
                    player_manager.add_item_to_inventory(pdata, TICKET_ID, 1)
                    await save_player_data(user_id, pdata)
                    delivered += 1
            except Exception: pass
    except Exception as e:
        logger.error(f"Erro distribuindo tickets: {e}")
        
    logger.info(f"[JOB] Tickets distribuídos: {delivered}")

async def daily_event_ticket_job(context: ContextTypes.DEFAULT_TYPE):
    return await distribute_kingdom_defense_ticket_job(context)


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

    await executar_reset_pvp(context.bot, force_run=False)

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
                col, query_id = get_col_and_id(user_id)
                
                if col is not None:
                     col.update_one({"_id": query_id}, {"$inc": {"gems": reward_amount}})
                     try: await context.bot.send_message(chat_id=user_id, text=f"🏆 Rank {rank}: Recebeu {reward_amount} gemas!")
                     except: pass
                     
    if ANNOUNCEMENT_CHAT_ID:
        try: await context.bot.send_message(chat_id=ANNOUNCEMENT_CHAT_ID, message_thread_id=ANNOUNCEMENT_THREAD_ID, text="🏆 <b>Ranking PvP Finalizado!</b>", parse_mode="HTML")
        except: pass

async def reset_pvp_season(context: ContextTypes.DEFAULT_TYPE):
    # CORREÇÃO CRÍTICA: Verifica se as coleções existem antes de chamar update_many
    if players_col is not None:
        players_col.update_many({}, {"$set": {"pvp_points": 0}})
    
    if users_col is not None:
        users_col.update_many({}, {"$set": {"pvp_points": 0}})
    
    if ANNOUNCEMENT_CHAT_ID:
        msg_season = (
            "╭────── [ 🏆 <b>NOVA TEMPORADA</b> ] ──────➤\n"
            "│\n"
            "│ ⚔️ <b>A ARENA FOI REINICIADA!</b>\n"
            "│ <i>Os deuses da guerra limparam o sangue</i>\n"
            "│ <i>da areia. A glória aguarda novos heróis!</i>\n"
            "│\n"
            "│ 🔄 <b>Status:</b> Pontos Resetados\n"
            "│ 💎 <b>Prêmios:</b> Entregues aos Top Rankings\n"
            "│\n"
            "╰──────────────────────────────➤\n"
            "🔥 <i>Vá à Arena e conquiste seu lugar na história!</i>"
        )
        
        try: 
            await context.bot.send_message(
                chat_id=ANNOUNCEMENT_CHAT_ID, 
                message_thread_id=ANNOUNCEMENT_THREAD_ID, 
                text=msg_season, 
                parse_mode="HTML"
            )
        except: pass

async def regenerate_energy_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    _non_premium_tick["count"] = (_non_premium_tick["count"] + 1) % 2
    regenerate_non_premium = (_non_premium_tick["count"] == 0)
    
    try:
        async for user_id, pdata in player_manager.iter_players():
            try:
                max_e = int(player_manager.get_player_max_energy(pdata)) 
                cur_e = int(pdata.get("energy", 0))
                if cur_e >= max_e: continue 

                is_premium = player_manager.has_premium_plan(pdata) 
                
                if is_premium or regenerate_non_premium:
                    col, query_id = get_col_and_id(user_id)
                    if col is not None:
                        col.update_one({"_id": query_id}, {"$inc": {"energy": 1}})
            except: pass
    except Exception as e:
        logger.error(f"Erro regenerate_energy_job: {e}")

async def daily_crystal_grant_job(context: ContextTypes.DEFAULT_TYPE) -> int:
    today = _today_str()
    try:
        async for user_id, pdata in player_manager.iter_players():
            try:
                daily = pdata.get("daily_awards") or {}
                if daily.get("last_crystal_date") == today: continue
                
                col, query_id = get_col_and_id(user_id)
                if col is not None:
                    col.update_one(
                        {"_id": query_id},
                        {
                            "$inc": {f"inventory.{DAILY_CRYSTAL_ITEM_ID}": 4},
                            "$set": {"daily_awards.last_crystal_date": today}
                        }
                    )
                    if DAILY_NOTIFY_USERS:
                        try: await context.bot.send_message(chat_id=user_id, text="🎁 4x Cristais recebidos.")
                        except: pass
            except: pass
    except: pass
    return 0



async def afternoon_event_reminder_job(context: ContextTypes.DEFAULT_TYPE) -> int:
    return 0

async def daily_kingdom_ticket_job(context: ContextTypes.DEFAULT_TYPE) -> int:
    today = _today_str() 
    granted = 0
    
    msg_ticket = (
        "📜 <b>CONVOCAÇÃO REAL</b> 📜\n\n"
        "Guerreiro, o Reino precisa de sua força!\n"
        "Os batedores relatam movimentos nas sombras...\n\n"
        "🎁 <b>Você recebeu:</b> 1x 🎟️ <b>Ticket de Defesa do Reino</b>\n"
        "<i>Esteja pronto quando a trombeta de guerra soar!</i>"
    )

    async for user_id, pdata in player_manager.iter_players():
        try:
            daily = pdata.get("daily_awards") or {}
            
            if daily.get("last_kingdom_ticket_date") == today: 
                continue
            
            col, query_id = get_col_and_id(user_id)
            
            if col is not None:
                col.update_one(
                    {"_id": query_id},
                    {
                        "$inc": {"inventory.ticket_defesa_reino": 1},
                        "$set": {"daily_awards.last_kingdom_ticket_date": today}
                    }
                )
                
                try:
                    if hasattr(player_manager, "clear_player_cache"):
                        res = player_manager.clear_player_cache(user_id)
                        if asyncio.iscoroutine(res): await res
                except Exception: pass

                granted += 1
                
                try:
                    await context.bot.send_message(
                        chat_id=user_id, 
                        text=msg_ticket, 
                        parse_mode='HTML'
                    )
                    await asyncio.sleep(0.05) 
                except Exception:
                    pass
        except Exception: 
            pass
            
    return granted

async def force_grant_daily_crystals(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Wrapper para forçar a entrega de cristais diários via admin."""
    return await daily_crystal_grant_job(context)

async def check_premium_expiry_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Verifica assinaturas vencidas.
    BLINDADO contra erros de 'Chat not found' e falhas de conexão.
    """
    count_downgraded = 0
    now = datetime.datetime.now(datetime.timezone.utc)

    async for user_id, pdata in player_manager.iter_players():
        try:
            current_tier = pdata.get("premium_tier")
            if not current_tier or current_tier == "free": 
                continue

            pm = PremiumManager(pdata)
            # Se não for premium (expirou data ou status inválido)
            if not pm.is_premium():
                exp_date = pm.expiration_date
                should_remove = (exp_date is None) or (exp_date < now)
                
                if should_remove:
                    logger.info(f"[PREMIUM] Expirou para user {user_id}. Resetando...")
                    
                    # 1. Revoga na memória
                    pm.revoke()
                    
                    # 2. Atualiza no Banco (Usando a função blindada acima)
                    col, query_id = get_col_and_id(user_id)
                    
                    if col is not None:
                        col.update_one(
                            {"_id": query_id}, 
                            {"$set": {"premium_tier": "free", "premium_expires_at": None}}
                        )
                    
                    # 3. Sincronia Híbrida (se necessário)
                    if users_col is not None and col != users_col:
                        try:
                            users_col.update_one(
                                {"telegram_id_owner": int(str(user_id))},
                                {"$set": {"premium_tier": "free", "premium_expires_at": None}}
                            )
                        except: pass

                    # 4. Notifica o Jogador (Com proteção anti-erro)
                    try:
                        target_chat_id = pdata.get("last_chat_id") or pdata.get("telegram_id_owner") or user_id
                        msg = (
                            "⚠️ <b>ASSINATURA EXPIRADA</b>\n\n"
                            f"O seu plano <b>{str(current_tier).title()}</b> chegou ao fim.\n"
                            "Sua conta retornou para o status <b>Aventureiro Comum</b>."
                        )
                        await context.bot.send_message(chat_id=target_chat_id, text=msg, parse_mode="HTML")
                        await asyncio.sleep(0.05)
                    except Exception:
                        # Se o usuário bloqueou ou não existe, apenas ignora
                        pass 
                        
                    count_downgraded += 1
                    
        except Exception as e:
            logger.error(f"Erro check_premium_expiry_job user {user_id}: {e}")
            continue

    if count_downgraded > 0:
        logger.info(f"[JOB PREMIUM] {count_downgraded} assinaturas vencidas processadas.")

async def cmd_force_pvp_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando ADMIN debug."""
    from config import ADMIN_ID
    user_id = get_current_player_id(update, context)
    if str(user_id) != str(ADMIN_ID): return
        
    await update.message.reply_text("🔄 DEBUG: Iniciando reset PvP...")
    await daily_pvp_entry_reset_job(context)
    await job_pvp_monthly_reset(context)
    await update.message.reply_text("✅ DEBUG: Concluído.")