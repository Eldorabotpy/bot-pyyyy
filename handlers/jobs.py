# Arquivo: handlers/jobs.py (VERSÃO FINAL E CORRIGIDA PARA ASYNC)

from __future__ import annotations

import logging
import datetime
import asyncio
import os
from zoneinfo import ZoneInfo
from typing import Dict, Optional, Any
from telegram.ext import ContextTypes
from telegram.error import Forbidden

# --- MONGODB IMPORTS ---
from pymongo import MongoClient
import certifi

from modules import player_manager
from modules.player_manager import (
    add_item_to_inventory, save_player_data, get_perk_value
)
from config import EVENT_TIMES, JOB_TIMEZONE

from kingdom_defense.engine import event_manager
# Imports opcionais
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

# Evita logs repetitivos de conexão, fazemos uma vez só na carga do módulo
try:
    # Cria o cliente mas não força o comando de rede imediatamente aqui fora do loop/função para evitar travamento na importação
    client = MongoClient(MONGO_STR, tlsCAFile=certifi.where())
    db = client["eldora_db"]
    players_col = db["players"]
    logger.info("✅ [JOBS] Cliente MongoDB inicializado.")
except Exception as e:
    logger.critical(f"❌ [JOBS] FALHA CRÍTICA NA INICIALIZAÇÃO DO MONGO: {e}")
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

def _parse_iso_utc(s: Optional[str]) -> Optional[datetime.datetime]:
    if not s: return None
    try:
        s_norm = s.strip().removesuffix("Z") + "+00:00" if s.strip().endswith("Z") else s.strip()
        dt = datetime.datetime.fromisoformat(s_norm)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)
    except Exception: return None

def _safe_add_stack(pdata: dict, item_id: str, qty: int) -> None:
    try:
        add_item_to_inventory(pdata, item_id, qty)
    except Exception:
        inv = pdata.setdefault("inventory", {})
        inv[item_id] = int(inv.get(item_id, 0)) + int(qty)

# --- JOBS PRINCIPAIS ---

async def regenerate_energy_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Regenera energia usando UPDATE ATÔMICO ($inc) para proteger o ouro.
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

                max_e = int(player_manager.get_player_max_energy(pdata)) 
                cur_e = int(pdata.get("energy", 0))
                
                if cur_e >= max_e: continue 

                is_premium = player_manager.has_premium_plan(pdata) 
                
                if is_premium or regenerate_non_premium:
                    # --- CORREÇÃO AQUI: 'is not None' ---
                    if players_col is not None:
                        # JEITO CERTO: Só mexe na energia, ignora o resto (protege o ouro)
                        players_col.update_one(
                            {"_id": user_id}, 
                            {"$inc": {"energy": 1}}
                        )
                        touched += 1
                    else:
                        # Fallback (só se o banco estiver desconectado)
                        player_manager.add_energy(pdata, 1) 
                        await save_player_data(user_id, pdata) 
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
    """Entrega o ticket do evento e anuncia os horários do dia (assíncrono)."""
    horarios_str = " e ".join([f"{start_h:02d}:{start_m:02d}" for start_h, start_m, _, _ in EVENT_TIMES])
    notify_text = (
        f"🎟️ <b>Um Ticket de Defesa do Reino foi entregue a você!</b>\n\n"
        f"📢 Hoje, as hordas atacarão Eldora nos seguintes horários:\n"
        f"   - <b>{horarios_str}</b>\n\n"
        f"Esteja no reino e prepare-se para a batalha!"
    ) 
    delivered = 0
    
    # <<< CORREÇÃO: Usa 'async for' >>>
    try:
        async for user_id, pdata in player_manager.iter_players():
            try:
                if not pdata: continue
                
                _safe_add_stack(pdata, 'ticket_defesa_reino', 1)
                
                await save_player_data(user_id, pdata) # Async
                delivered += 1
                
                try:
                    await context.bot.send_message(chat_id=user_id, text=notify_text, parse_mode='HTML')
                    await asyncio.sleep(0.1) # Delay anti-spam
                except Forbidden:
                    pass
            except Exception as e:
                logger.warning("[JOB_TICKET] Falha ao entregar ticket para %s: %s", user_id, e)
    except Exception as e_iter:
         logger.error(f"Erro crítico ao iterar jogadores em daily_event_ticket_job: {e_iter}", exc_info=True)
    
    logger.info("[JOB_TICKET] Tickets de evento entregues para %s jogadores.", delivered)
    return delivered

# Em: handlers/jobs.py
# SUBSTITUA a função 'distribute_kingdom_defense_ticket_job' por esta:

async def distribute_kingdom_defense_ticket_job(context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    (NOVO JOB - VERSÃO 2, MAIS ROBUSTA) 
    Concede 1 ticket de Defesa do Reino para todos os jogadores 
    antes de um evento específico começar.
    """
    
    job_data = context.job.data or {}
    event_time_str = job_data.get("event_time", "horário desconhecido")
    
    TICKET_ID = "ticket_defesa_reino"
    TICKET_QTY = 1
    
    notify_text = (
        f"🎟️ <b>Prepare-se, defensor!</b>\n\n"
        f"Você recebeu 1 {TICKET_ID} para a próxima invasão ao reino, que começará às <b>{event_time_str}</b>!"
    )
    
    logger.info(f"[JOB_KD_TICKET] Iniciando entrega de ticket para o evento das {event_time_str}...")
    
    delivered = 0
    
    # --- !!! MUDANÇA DE LÓGICA AQUI !!! ---
    # Vamos usar 'iter_player_ids' (Síncrono) que é mais simples e robusto
    # do que 'iter_players' (Assíncrono) para este loop.
    
    all_player_ids = []
    try:
        # Tenta buscar todos os IDs primeiro
        all_player_ids = list(player_manager.iter_player_ids())
        logger.info(f"[JOB_KD_TICKET] Encontrados {len(all_player_ids)} IDs de jogadores na base de dados.")
    except Exception as e_fetch_ids:
        logger.error(f"Erro CRÍTICO ao buscar 'iter_player_ids': {e_fetch_ids}", exc_info=True)
        return 0 # Não pode continuar se não consegue buscar os IDs

    # Agora iteramos pela lista de IDs
    for user_id in all_player_ids:
        try:
            # Carregamos os dados de CADA jogador (um de cada vez)
            pdata = await player_manager.get_player_data(user_id)
            if not pdata:
                logger.warning(f"[JOB_KD_TICKET] get_player_data retornou None para o ID {user_id}. Ignorando.")
                continue
            
            # Dá o ticket
            _safe_add_stack(pdata, TICKET_ID, TICKET_QTY)
            
            # Salva os dados
            await save_player_data(user_id, pdata)
            delivered += 1
            
            # Tenta notificar o jogador
            try:
                await context.bot.send_message(chat_id=user_id, text=notify_text, parse_mode='HTML')
                await asyncio.sleep(0.05) # 50ms de delay (mais rápido)
            except Forbidden:
                pass # Bot bloqueado, ignora
            except Exception:
                pass # Outros erros de envio, ignora

        except Exception as e_player:
            logger.warning(f"[JOB_KD_TICKET] Falha ao processar e entregar ticket para {user_id}: {e_player}")
            
    logger.info(f"[JOB_KD_TICKET] {delivered} jogadores receberam o ticket para o evento das {event_time_str}.")
    return delivered

async def afternoon_event_reminder_job(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Envia uma notificação de lembrete para o segundo evento do dia (assíncrono)."""
    notify_text = "🔔 <b>LEMBRETE DE EVENTO</b> 🔔\n\nA segunda horda de monstros se aproxima! O ataque ao reino começará em breve, às 14:00. Não se esqueça de participar!"
    
    notified = 0
    
    # <<< CORREÇÃO: Usa 'async for' (e iter_players para ter o user_id) >>>
    try:
        async for user_id, _ in player_manager.iter_players(): # Não precisamos do pdata aqui
            try:
                await context.bot.send_message(chat_id=user_id, text=notify_text, parse_mode='HTML')
                await asyncio.sleep(0.1) # Delay anti-spam
                notified += 1
            except Exception:
                pass
    except Exception as e_iter:
        logger.error(f"Erro crítico ao iterar jogadores em afternoon_event_reminder_job: {e_iter}", exc_info=True)
            
    logger.info("[JOB_LEMBRETE] Lembrete de evento enviado para %s jogadores.", notified)
    return notified

async def _process_watchdog_for_player(context: ContextTypes.DEFAULT_TYPE, user_id: int, now: datetime.datetime, ACTION_FINISHERS: Dict[str, Any]) -> int:
    """Processa a verificação de watchdog para um único jogador, de forma assíncrona."""
    try:
        # Puxa o pdata para verificar o estado (Assíncrono)
        pdata = await player_manager.get_player_data(user_id)
        if not pdata: return 0
        
        st = pdata.get("player_state") or {}
        action = st.get("action")

        if not action or action not in ACTION_FINISHERS:
            return 0

        ft_str = st.get("finish_time")
        # Usa a função auxiliar de parsing (importada no topo)
        ft = _parse_iso_utc(ft_str) 

        # Compara a hora de término (ft) com a hora atual (now)
        if not ft or ft > now:
            return 0

        # --- Ação Vencida: Agenda o finalizador ---
        config = ACTION_FINISHERS[action]
        finalizer_fn = config.get("fn")
        if not finalizer_fn:
            return 0

        job_data = {}
        if "data_builder" in config and callable(config["data_builder"]):
            job_data = config["data_builder"](st)

        chat_id = pdata.get("last_chat_id", user_id)
        job_name = f"{action}:{user_id}"

        # Reagenda a finalização (com when=0 para imediato)
        context.job_queue.run_once(
            finalizer_fn, when=0, chat_id=chat_id, user_id=user_id,
            data=job_data, name=job_name,
        )
        return 1 # Disparado (fired)

    except Exception as e_player:
        # Loga o erro, mas não quebra o loop
        logger.warning("[WATCHDOG] Erro ao verificar jogador %s: %s", user_id, e_player)
        return 0
        
async def timed_actions_watchdog(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Verifica ações terminadas e reagenda a finalização (Watchdog Assíncrono).
    
    ATENÇÃO: Este watchdog (Vigilante 2) foi DESATIVADO (lista vazia)
    porque o Vigilante 1 (check_stale_actions_on_startup em actions.py)
    já lida com o reagendamento de jobs de coleta, forja e viagem.
    Manter este ativo estava a causar uma "competição" (race condition)
    e a fazer com que os jobs originais falhassem.
    """
    
    # --- CORREÇÃO: Esvaziar o dicionário ---
    ACTION_FINISHERS: Dict[str, Any] = {
        # "crafting": ... (TUDO REMOVIDO PARA EVITAR O BUG DA FORJA)
    }
    # --- FIM DA CORREÇÃO ---

    now = datetime.datetime.now(datetime.timezone.utc)

    # Se a lista estiver vazia, podemos parar a função mais cedo.
    if not ACTION_FINISHERS:
        # logger.info("[WATCHDOG] O Vigilante 2 (jobs.py) está desativado (lista vazia).")
        return

    tasks = []
    try:
        async for user_id, _ in player_manager.iter_players(): 
            try:
                tasks.append(_process_watchdog_for_player(context, user_id, now, ACTION_FINISHERS))
            except Exception as e_player:
                logger.warning(f"[WATCHDOG] Erro ao preparar task para {user_id}: {e_player}")

        if tasks:
            results = await asyncio.gather(*tasks)
            fired = sum(results)
            if fired > 0:
                logger.info("[WATCHDOG] Disparadas %s finalizações de ações vencidas.", fired)

    except Exception as e_loop:
        logger.error(f"[WATCHDOG] Erro CRÍTICO durante o loop: {e_loop}", exc_info=True)

async def distribute_pvp_rewards(context: ContextTypes.DEFAULT_TYPE):
    """Distribui recompensas de Gemas (Dimas) para o Top N do ranking PvP, de forma assíncrona."""
    logger.info("Iniciando distribuição de recompensas PvP...")

    all_players_ranked = []
    try:
        # <<< CORREÇÃO: Usa 'async for' >>>
        async for user_id, p_data in player_manager.iter_players():
            try:
                if not p_data: continue

                pvp_points = player_manager.get_pvp_points(p_data) # Síncrono
                if pvp_points > 0:
                   all_players_ranked.append({
                       "user_id": user_id,
                       "name": p_data.get("character_name", f"ID: {user_id}"),
                       "points": pvp_points,
                       # Não precisamos guardar o _pdata se vamos recarregar depois
                   })
            except Exception as e_player:
                 logger.error(f"Erro ao coletar dados PvP para {user_id}: {e_player}")
                 
    except Exception as e:
        logger.error(f"Erro ao buscar jogadores para recompensas PvP: {e}", exc_info=True)
        return

    all_players_ranked.sort(key=lambda p: p["points"], reverse=True)

    winners_info = [] 
    if MONTHLY_RANKING_REWARDS:
        for i, player in enumerate(all_players_ranked):
            rank = i + 1
            reward_amount = MONTHLY_RANKING_REWARDS.get(rank)

            if reward_amount:
                user_id = player["user_id"]
                
                # Recarrega os dados do vencedor
                p_data_current = await player_manager.get_player_data(user_id) # Já usava await
                if not p_data_current:
                    logger.error(f"Não foi possível obter dados atuais para o vencedor PvP Rank {rank} ({user_id})")
                    continue

                player_name = p_data_current.get("character_name", f"ID: {user_id}") 

                try:
                    player_manager.add_gems(p_data_current, reward_amount) # Síncrono
                    await player_manager.save_player_data(user_id, p_data_current) # Já usava await

                    log_msg = f"Recompensa PvP Rank {rank}: {reward_amount} Gemas para {player_name} ({user_id})."
                    logger.info(log_msg)
                    winners_info.append(f"{rank}º: {player_name} (+{reward_amount}💎)")

                    try:
                        await context.bot.send_message(chat_id=user_id, text=f"Parabéns! ...") # Mantido
                        await asyncio.sleep(0.1) # Delay
                    except Forbidden: logger.warning(f"Bot bloqueado pelo vencedor PvP {user_id}...") # Mantido
                    except Exception as e_notify: logger.warning(f"Falha ao notificar vencedor PvP {user_id}: {e_notify}")

                except Exception as e_grant:
                    err_msg = f"Erro ao conceder recompensa PvP Rank {rank} ...: {e_grant}" # Mantido
                    logger.error(err_msg, exc_info=True)
            else:
                 if rank > max(MONTHLY_RANKING_REWARDS.keys(), default=0):
                     break
    
    if winners_info:

        announcement = "🏆 <b>Recompensas do Ranking PvP Mensal Distribuídas!</b> 🏆\n\nParabéns aos melhores combatentes deste ciclo:\n" + "\n".join(winners_info)
        try:
            await context.bot.send_message(
                 chat_id=ANNOUNCEMENT_CHAT_ID,
                 message_thread_id=ANNOUNCEMENT_THREAD_ID,
                 text=announcement,
                 parse_mode="HTML"
            )
            logger.info(f"Anúncio dos vencedores PvP enviado para o tópico {ANNOUNCEMENT_THREAD_ID} no chat {ANNOUNCEMENT_CHAT_ID}.")
        except Exception as e_announce:
             logger.error(f"Falha ao anunciar vencedores PvP: {e_announce}")

    logger.info("Distribuição de recompensas PvP concluída.")

async def reset_pvp_season(context: ContextTypes.DEFAULT_TYPE):
    """Reseta os pontos PvP de todos os jogadores, iniciando uma nova temporada."""
    logger.info("Iniciando reset da temporada PvP...")

    reset_count = 0
    try:
        # <<< CORREÇÃO: Usa 'async for' >>>
        async for user_id, p_data in player_manager.iter_players():
            try:
                if not p_data: continue

                if "pvp_points" in p_data and p_data["pvp_points"] != 0:
                    previous_points = p_data.get("pvp_points", 0)
                    p_data.setdefault("pvp_history", []).append({"date": datetime.datetime.now(datetime.timezone.utc).isoformat(), "points": previous_points})
                    p_data["pvp_points"] = 0

                    await player_manager.save_player_data(user_id, p_data) # Já usava await
                    reset_count += 1

                    try:
                        await context.bot.send_message(chat_id=user_id, text="⚔️ Uma nova temporada PvP começou! ...") # Mantido
                        await asyncio.sleep(0.1) # Delay
                    except Exception: pass # Ignora
            
            except Exception as e_player_reset:
                logger.error(f"Erro ao resetar PvP para jogador {user_id}: {e_player_reset}", exc_info=True)

    except Exception as e_iter:
        logger.error(f"Erro CRÍTICO durante a iteração para reset PvP: {e_iter}", exc_info=True)

    logger.info(f"Reset da temporada PvP concluído. Pontos de {reset_count} jogadores foram resetados.")

    announcement = "⚔️ <b>Nova Temporada PvP Iniciada!</b> ⚔️\n\nTodos os pontos de Elo foram resetados. Que comecem as batalhas pela glória na Arena!" # Corrigido para HTML
    try:
        await context.bot.send_message(
             chat_id=ANNOUNCEMENT_CHAT_ID,
             message_thread_id=ANNOUNCEMENT_THREAD_ID,
             text=announcement,
             parse_mode="HTML"
         )
        logger.info(f"Anúncio de nova temporada PvP enviado para o tópico {ANNOUNCEMENT_THREAD_ID} no chat {ANNOUNCEMENT_CHAT_ID}.")
    except Exception as e_announce:
        logger.error(f"Falha ao anunciar nova temporada PvP: {e_announce}")
        
        async def start_kingdom_defense_event(context: ContextTypes.DEFAULT_TYPE):
            """Inicia o evento Defesa do Reino."""
    try:
        # Pega o nome do job (ex: 'kd_start_09:00')
        job_name = context.job.name 
        logger.info(f"Iniciando job: {job_name}")
        
        # 'event_duration_minutes' é passado como parte do 'job_data'
        duration = context.job.data.get("event_duration_minutes", 30) 
        
        success, message = await event_manager.start_event(duration_minutes=duration)
        
        if success:
            logger.info(f"Evento de Defesa do Reino INICIADO. Duração: {duration} min.")
            # Envia o anúncio global
            await context.bot.send_message(
                chat_id=ANNOUNCEMENT_CHAT_ID,
                message_thread_id=ANNOUNCEMENT_THREAD_ID,
                text=f"⚔️ <b>INVASÃO IMINENTE!</b> ⚔️\n\n{message}\n\nA defesa durará {duration} minutos. Defensores, ao reino!",
                parse_mode="HTML"
            )
        else:
            logger.warning(f"Não foi possível iniciar o evento: {message}")
            
    except Exception as e:
        logger.error(f"Erro crítico ao tentar iniciar o evento Defesa do Reino: {e}", exc_info=True)
        
async def start_kingdom_defense_event(context: ContextTypes.DEFAULT_TYPE):
    """Inicia o evento Defesa do Reino."""
    try:
        job_name = context.job.name 
        logger.info(f"Iniciando job: {job_name}")
        duration = (context.job.data or {}).get("event_duration_minutes", 30) 
        await event_manager.start_event()
        logger.info(f"Evento de Defesa do Reino INICIADO (Chamada ao event_manager bem-sucedida). Duração: {duration} min.")
        message_para_anunciar = "As hordas de monstros estão a atacar o reino!"

        await context.bot.send_message(
            chat_id=ANNOUNCEMENT_CHAT_ID,
            message_thread_id=ANNOUNCEMENT_THREAD_ID,
            text=f"⚔️ <b>INVASÃO IMINENTE!</b> ⚔️\n\n{message_para_anunciar}\n\nA defesa durará {duration} minutos. Defensores, ao reino!",
            parse_mode="HTML"
        )
            
    except Exception as e:
        logger.error(f"Erro crítico ao tentar iniciar o evento Defesa do Reino: {e}", exc_info=True)
        
async def end_kingdom_defense_event(context: ContextTypes.DEFAULT_TYPE):
    """Finaliza o evento Defesa do Reino."""
    try:
        job_name = context.job.name
        logger.info(f"Iniciando job: {job_name}")
        
        if not event_manager.is_active:
            logger.info("Job de finalização executado, mas o evento já estava inativo.")
            return

        success, message = await event_manager.end_event()
        
        if success:
            logger.info("Evento de Defesa do Reino FINALIZADO.")
            await context.bot.send_message(
                chat_id=ANNOUNCEMENT_CHAT_ID,
                message_thread_id=ANNOUNCEMENT_THREAD_ID,
                text=f"🛡️ <b>A INVASÃO TERMINOU!</b> 🛡️\n\n{message}",
                parse_mode="HTML"
            )
        else:
            logger.warning(f"Não foi possível finalizar o evento: {message}")

    except Exception as e:
        logger.error(f"Erro crítico ao tentar finalizar o evento Defesa do Reino: {e}", exc_info=True)

# <<< [MUDANÇA] ADICIONADO O NOVO JOB DE TICKET DA ARENA >>>
async def daily_arena_ticket_job(context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Concede 10 Tickets da Arena (item) para todos os jogadores diariamente.
    """
    today = _today_str()
    granted = 0
    TICKET_ID = "ticket_arena" # <<< ID DO ITEM
    TICKET_QTY = 10            # <<< QUANTIDADE

    logger.info(f"[DAILY_ARENA] Iniciando job de entrega de {TICKET_QTY}x {TICKET_ID}...")
    
    try:
        async for user_id, pdata in player_manager.iter_players():
            try:
                if not pdata: continue
                
                daily = pdata.get("daily_awards") or {}
                
                if daily.get("last_arena_ticket_date") == today: 
                    continue # Já recebeu hoje
                
                _safe_add_stack(pdata, TICKET_ID, TICKET_QTY)
                
                daily["last_arena_ticket_date"] = today
                pdata["daily_awards"] = daily
                
                await save_player_data(user_id, pdata)
                granted += 1
                
                try: 
                    await context.bot.send_message(chat_id=user_id, text=f"🎟️ Você recebeu seus {TICKET_QTY} Tickets da Arena diários!")
                    await asyncio.sleep(0.1) # Delay anti-spam
                except Forbidden: pass
                except Exception: pass
                
            except Exception as e:
                logger.warning(f"[DAILY_ARENA] Falha ao conceder tickets para {user_id}: {e}")
                
    except Exception as e_iter:
        logger.error(f"Erro crítico ao iterar jogadores em daily_arena_ticket_job: {e_iter}", exc_info=True)
            
    logger.info(f"[DAILY_ARENA] {granted} jogadores receberam tickets da arena.")
    return granted