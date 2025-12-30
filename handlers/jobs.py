# Arquivo: handlers/jobs.py (VERSÃO FINAL: NOTIFICAÇÃO DE LOCAL E ABA DE AVISOS)

from __future__ import annotations

import logging
import datetime
import asyncio
import certifi
from zoneinfo import ZoneInfo
from typing import Dict, Optional, Any
from telegram.ext import ContextTypes
from modules import game_data
# --- MONGODB IMPORTS ---
from pymongo import MongoClient
from bson import ObjectId
from modules import player_manager
from modules.player_manager import (
    save_player_data, get_perk_value, 
    add_item_to_inventory, iter_player_ids
)

# --- CONFIG & MANAGERS ---
# Importa IDs do Grupo e da Aba de Avisos
from config import EVENT_TIMES, JOB_TIMEZONE, ANNOUNCEMENT_CHAT_ID, ANNOUNCEMENT_THREAD_ID
from pvp.pvp_scheduler import executar_reset_pvp
# --- IMPORTAÇÃO DOS ENGINES (SEM TRY/EXCEPT PARA MOSTRAR ERROS REAIS) ---
# Se der erro aqui, queremos que o bot avise no console, e não que esconda!
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
    users_col = db["users"] # Conecta na coleção nova também
    logger.info("✅ [JOBS] Conexão MongoDB Híbrida OK.")
except Exception as e:
    logger.critical(f"❌ [JOBS] FALHA CRÍTICA NA CONEXÃO MONGODB: {e}")
    players_col = None
    users_col = None

def get_col_and_id(user_id):
    """
    Retorna a coleção correta e o formato do ID para query.
    - Int -> players_col, int
    - Str -> users_col, ObjectId
    """
    if isinstance(user_id, int):
        return players_col, user_id
    elif isinstance(user_id, str):
        if users_col is not None and ObjectId.is_valid(user_id):
            return users_col, ObjectId(user_id)
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
    """Reseta as 10 entradas diárias da Arena PvP."""
    today = _today_str()
    count = 0
    
    msg_reset = "⚔️ <b>ARENA DE ELDORA</b>\nSuas 10 batalhas diárias foram restauradas! Boa sorte."

    async for user_id, pdata in player_manager.iter_players():
        try:
            # Verifica se já recebeu HOJE
            last_reset = pdata.get("last_pvp_entry_reset")
            if last_reset == today: 
                continue
            
            # --- CORREÇÃO: Força conversão e roteamento seguro ---
            col, query_id = get_col_and_id(user_id)
            
            # Se falhar o roteamento automático, tenta converter ID numérico para int
            if col is None and str(user_id).isdigit():
                query_id = int(user_id)
                col = players_col

            if col is not None:
                # Atualiza no Banco
                result = col.update_one(
                    {"_id": query_id},
                    {
                        "$set": {
                            "pvp_entries_left": 10,
                            "last_pvp_entry_reset": today
                        }
                    }
                )
                
                # Se atualizou no banco, limpa cache e notifica
                if result.modified_count > 0 or result.matched_count > 0:
                    try:
                        if hasattr(player_manager, "clear_player_cache"):
                            res = player_manager.clear_player_cache(user_id)
                            if asyncio.iscoroutine(res): await res
                    except: pass
                    
                    # Notificação ao Jogador
                    try:
                        await context.bot.send_message(chat_id=user_id, text=msg_reset, parse_mode='HTML')
                        await asyncio.sleep(0.05) # Anti-flood leve
                    except Exception as e:
                        # Ignora erro de chat não encontrado (bot bloqueado)
                        pass
                    
                    count += 1
            else:
                logger.warning(f"[JOB PvP] Não foi possível determinar coleção para user_id: {user_id}")

        except Exception as e:
            logger.error(f"[JOB PvP] Erro ao resetar usuário {user_id}: {e}")
            continue
        
    logger.info(f"[JOB] PvP Resetado para {count} jogadores.")

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
            
            # Roteamento Híbrido
            col, query_id = get_col_and_id(user_id)
            
            if col is not None:
                col.update_one(
                    {"_id": query_id},
                    {
                        "$inc": {"inventory.ticket_arena": 10},
                        "$set": {"daily_awards.last_arena_ticket_date": today}
                    }
                )
                
                try:
                    if hasattr(player_manager, "clear_player_cache"):
                        res = player_manager.clear_player_cache(user_id)
                        if asyncio.iscoroutine(res): await res
                except: pass
                
                try:
                    await context.bot.send_message(chat_id=user_id, text=msg_arena, parse_mode='HTML')
                    await asyncio.sleep(0.05)
                except: pass
                
                granted += 1
        except: pass
        
    logger.info(f"[JOB] Tickets de Arena entregues: {granted}")

async def distribute_event_ticket(context: ContextTypes.DEFAULT_TYPE):
    """
    Entrega 1 Ticket para todos os jogadores SEM limite diário.
    """
    logger.info("[JOB] Distribuindo tickets de evento (sem limite diário)...")
    
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
            # Roteamento Híbrido
            col, query_id = get_col_and_id(user_id)

            if col is not None:
                col.update_one(
                    {"_id": query_id},
                    {"$inc": {"inventory.ticket_defesa_reino": 1}}
                )
                
                try:
                    if hasattr(player_manager, "clear_player_cache"):
                        res = player_manager.clear_player_cache(user_id)
                        if asyncio.iscoroutine(res): await res
                except Exception: pass

            else:
                # Fallback Memória
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
    if world_boss_manager is None:
        logger.error("⚠️ [JOB] CRÍTICO: world_boss_manager é None!")
        return

    if world_boss_manager.is_active:
         logger.info("👹 [JOB] Boss já está vivo. Ignorando spawn duplicado.")
         return

    logger.info("👹 [JOB] Iniciando sequência de spawn do World Boss...")
    
    result = world_boss_manager.start_event()
    
    if result.get("success"):
        location_key = result.get('location', 'desconhecido')
        region_info = (game_data.REGIONS_DATA.get(location_key) or {})
        location_display = region_info.get("display_name", location_key.replace("_", " ").title())
        
        if ANNOUNCEMENT_CHAT_ID:
            try:
                msg_text = (
                    f"👹 𝕎𝕆ℝ𝕃𝔻 𝔹𝕆𝕊𝕊 𝕊𝕌ℝ𝔾𝕀𝕌!\n\n"
                    f"📍 𝕃𝕠𝕔𝕒𝕝: {location_display}\n\n"
                    f"O monstro despertou! Corram para derrotá-lo!"
                )
                
                await context.bot.send_message(
                    chat_id=ANNOUNCEMENT_CHAT_ID, 
                    message_thread_id=ANNOUNCEMENT_THREAD_ID, 
                    text=msg_text, 
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"❌ ERRO NOTIFICAR GRUPO (BOSS): {e}")
        
        try:
            await broadcast_boss_announcement(context.application, location_key)
        except Exception as e:
            logger.error(f"Erro no broadcast do boss: {e}")
    else:
        logger.error(f"Falha ao iniciar Boss: {result.get('error')}")

async def end_world_boss_job(context: ContextTypes.DEFAULT_TYPE):
    if not world_boss_manager: return
    if not world_boss_manager.is_active: return

    logger.info("👹 [JOB] O tempo acabou! Removendo o Boss...")
    battle_results = world_boss_manager.end_event(reason="Tempo esgotado")
    await distribute_loot_and_announce(context, battle_results)


# ==============================================================================
# 🛡️ JOB: KINGDOM DEFENSE
# ==============================================================================
# Em handlers/jobs.py

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
    # Reseta nas duas coleções
    if players_col: players_col.update_many({}, {"$set": {"pvp_points": 0}})
    if users_col: users_col.update_many({}, {"$set": {"pvp_points": 0}})
    
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
                if not isinstance(pdata, dict): continue
                max_e = int(player_manager.get_player_max_energy(pdata)) 
                cur_e = int(pdata.get("energy", 0))
                if cur_e >= max_e: continue 

                is_premium = player_manager.has_premium_plan(pdata) 
                
                if is_premium or regenerate_non_premium:
                    col, query_id = get_col_and_id(user_id)
                    if col is not None:
                        col.update_one({"_id": query_id}, {"$inc": {"energy": 1}})
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
                
                col, query_id = get_col_and_id(user_id)
                
                if col is not None:
                    col.update_one(
                        {"_id": query_id},
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

# Em handlers/jobs.py

async def check_premium_expiry_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Job periódico: Verifica assinaturas vencidas, remove o status e notifica o usuário.
    Atualiza TANTO a coleção 'players' QUANTO a coleção 'users'.
    """
    from modules.player.premium import PremiumManager
    
    count_downgraded = 0
    now = datetime.datetime.now(datetime.timezone.utc)

    # Itera sobre todos os jogadores
    async for user_id, pdata in player_manager.iter_players():
        try:
            # Pula quem já é Free
            current_tier = pdata.get("premium_tier")
            if not current_tier or current_tier == "free":
                continue

            # Instancia o gerenciador
            pm = PremiumManager(pdata)
            
            # Se a data venceu...
            if not pm.is_premium():
                exp_date = pm.expiration_date
                
                # Só remove se tiver uma data de validade definida (ignora permanentes)
                if exp_date is not None and exp_date < now:
                    
                    # 1. Revoga na memória e salva na coleção PLAYERS
                    pm.revoke()
                    await player_manager.save_player_data(user_id, pdata)
                    
                    # 2. --- CORREÇÃO: Sincroniza com a coleção USERS ---
                    if users_col is not None:
                        query_user = None
                        
                        # Descobre como achar esse usuário na tabela 'users'
                        if isinstance(user_id, int):
                            # Contas antigas (Telegram ID)
                            query_user = {"telegram_id_owner": user_id}
                        elif isinstance(user_id, ObjectId):
                            # Contas novas (ObjectId)
                            query_user = {"_id": user_id}
                        elif isinstance(user_id, str) and ObjectId.is_valid(user_id):
                            # Caso venha como string
                            query_user = {"_id": ObjectId(user_id)}
                            
                        if query_user:
                            users_col.update_one(
                                query_user, 
                                {"$set": {"premium_tier": "free", "premium_expires_at": None}}
                            )
                    # ---------------------------------------------------
                    
                    # 3. Notifica o Jogador
                    try:
                        msg = (
                            "⚠️ <b>ASSINATURA EXPIRADA</b>\n\n"
                            f"O seu plano <b>{current_tier.title()}</b> chegou ao fim.\n"
                            "Sua conta retornou para o status <b>Free</b>.\n\n"
                            "💎 <i>Renove no menu Premium para recuperar seus benefícios!</i>"
                        )
                        await context.bot.send_message(chat_id=user_id, text=msg, parse_mode="HTML")
                    except Exception:
                        pass
                        
                    count_downgraded += 1
                    
        except Exception as e:
            logger.error(f"Erro ao verificar validade premium para {user_id}: {e}")
            continue

    if count_downgraded > 0:
        logger.info(f"[JOB PREMIUM] {count_downgraded} assinaturas vencidas foram removidas de Players e Users.")
        