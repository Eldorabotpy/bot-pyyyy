# Arquivo: main.py (VERSÃO CORRIGIDA PARA DEPLOY NO RENDER)

from __future__ import annotations
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logging
from dotenv import load_dotenv
load_dotenv()
from datetime import time, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from threading import Thread
from flask import Flask
import asyncio 
from telegram.ext import CommandHandler
from modules import player_manager

from telegram import Update
from telegram.ext import Application, ContextTypes
# --- [CORREÇÃO 1] Imports Adicionados ---
from telegram.request import HTTPXRequest 
from telegram.error import Conflict 

from config import ADMIN_ID, TELEGRAM_TOKEN, EVENT_TIMES, JOB_TIMEZONE, WORLD_BOSS_TIMES
from registries import register_all_handlers
from registries.events import register_event_handlers
from registries.class_evolution import register_evolution_handlers

# Importa o Watchdog
from modules.player.actions import check_stale_actions_on_startup

# --- Importa os jobs corretos ---
from handlers.jobs import (
    regenerate_energy_job, daily_crystal_grant_job, afternoon_event_reminder_job,
    timed_actions_watchdog, start_kingdom_defense_event, end_kingdom_defense_event,
    daily_arena_ticket_job,
    # --- !!! IMPORTAÇÃO ADICIONADA !!! ---
    distribute_kingdom_defense_ticket_job 
)
from handlers.world_boss.engine import (
    iniciar_world_boss_job, end_world_boss_job
)
from modules.player import core as player_core

# --- CONFIGURAÇÃO DE LOGGING ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- FLASK ---
flask_app = Flask(__name__)
@flask_app.route('/')
def health_check():
    return "Bot is alive and running!", 200
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)

# --- [CORREÇÃO 2] HANDLER DE ERRO MODIFICADO ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Loga o erro, mas ignora 'Conflict' (comum no Render)."""
    
    # Verifica se o erro é o 'Conflict' que esperamos no Render
    if isinstance(context.error, Conflict):
        logger.warning(f"Conflito de polling detectado: {context.error} - (Isso é normal durante deploys no Render)")
        return # Ignora o erro e não faz mais nada
        
    # Se for qualquer outro erro, loga como exceção (como antes)
    logger.exception(f"Exceção ao processar update: {context.error}")

async def send_startup_message(application: Application):
    """Envia a mensagem de que o bot iniciou."""
    if not ADMIN_ID: return
    try:
        await application.bot.send_message(
            chat_id=ADMIN_ID,
            text="🤖 𝑭𝒂𝒍𝒂 𝑨𝒗𝒆𝒏𝒕𝒖𝒓𝒆𝒊𝒓𝒐 𝒐 👾 𝑴𝒖𝒏𝒅𝒐 𝒅𝒆 𝑬𝒍𝒅𝒐𝒓𝒂 𝒂𝒄𝒂𝒃𝒂 𝒅𝒆 𝒓𝒆𝒕𝒐𝒓𝒏𝒂𝒓 𝒅𝒆 𝒔𝒖𝒂 𝑨𝒕𝒖𝒂𝒍𝒊𝒛𝒂𝒄̧𝒂̃𝒐 👾",
            parse_mode="HTML",
            disable_notification=True,
        )
    except Exception as e:
        logger.warning("Não foi possível enviar mensagem inicial: %s", e)

# ... (A tua função 'register_jobs' fica exatamente igual) ...
def register_jobs(application: Application):
    logger.info("Registrando jobs...")
    j = application.job_queue

    try:
        local_tz = ZoneInfo(JOB_TIMEZONE)
        logger.info(f"Usando timezone local '{JOB_TIMEZONE}' para jobs diários.")
    except Exception as e_tz:
        logger.error(f"CRÍTICO: Falha ao carregar timezone '{JOB_TIMEZONE}': {e_tz}. Usando UTC como fallback.")
        local_tz = timezone.utc

    # --- Jobs Repetitivos (Intervalo Fixo) ---
    j.run_repeating(regenerate_energy_job, interval=60, first=timedelta(seconds=5), name="regenerate_energy")
    j.run_repeating(timed_actions_watchdog, interval=60, first=timedelta(seconds=15), name="watchdog_acoes")
    logger.info("-> Job 'watchdog_acoes' agendado para rodar a cada minuto.")

    # --- Jobs Diários ('cron' - Hora Específica no Fuso Local) ---
    j.run_daily(daily_crystal_grant_job, time=time(hour=0, minute=0, tzinfo=local_tz), name="daily_crystals")
    
    # Job de Tickets da Arena (às 02:00)
    j.run_daily(
        daily_arena_ticket_job, 
        time=time(hour=2, minute=0, tzinfo=local_tz),
        name="daily_arena_tickets"
    )
    logger.info("-> Job 'daily_arena_ticket_job' agendado para 02:00 diariamente.")
    
    # Lembrete (13:30)
    j.run_daily(afternoon_event_reminder_job, time=time(hour=13, minute=30, tzinfo=local_tz), name="afternoon_event_reminder")

    # --- [CORREÇÃO] Agendamento Evento 1: Defesa do Reino (COM TICKETS) ---
    logger.info("Registrando jobs de eventos do reino (Defesa)...")
    if EVENT_TIMES: 
        for i, (start_h, start_m, end_h, end_m) in enumerate(EVENT_TIMES):
            try:
                start_dt = datetime(2000, 1, 1, start_h, start_m)
                end_dt = datetime(2000, 1, 1, end_h, end_m)
                duration_minutes = (end_dt - start_dt).total_seconds() / 60
                if duration_minutes <= 0: duration_minutes = 30
            except Exception:
                duration_minutes = 30
            
            job_data_start = {"event_duration_minutes": duration_minutes}
            
            # --- !!! INÍCIO DA CORREÇÃO !!! ---
            # 1. Agendar a ENTREGA DE TICKETS (10 minutos ANTES do evento)
            
            # Calcula o horário de entrega (10 min antes)
            ticket_time_dt = datetime(2000, 1, 1, start_h, start_m) - timedelta(minutes=10)
            ticket_h = ticket_time_dt.hour
            ticket_m = ticket_time_dt.minute
            
            # Prepara os dados para o job (para a notificação)
            event_time_str = f"{start_h:02d}:{start_m:02d}"
            job_data_ticket = {"event_time": event_time_str}
            
            j.run_daily(
                distribute_kingdom_defense_ticket_job,
                time=time(hour=ticket_h, minute=ticket_m, tzinfo=local_tz),
                name=f"distribute_ticket_{i}_{ticket_h}h{ticket_m:02d}",
                data=job_data_ticket
            )
            logger.info(f"-> Job de Ticket {i+1} agendado para: {ticket_h:02d}:{ticket_m:02d}")
            # --- !!! FIM DA CORREÇÃO !!! ---

            # 2. Agendar o INÍCIO do evento (no horário certo)
            j.run_daily(
                start_kingdom_defense_event, 
                time=time(hour=start_h, minute=start_m, tzinfo=local_tz), 
                name=f"start_defense_{i}_{start_h}h{start_m:02d}",
                data=job_data_start
            )
            
            # 3. Agendar o FIM do evento
            j.run_daily(
                end_kingdom_defense_event, 
                time=time(hour=end_h, minute=end_m, tzinfo=local_tz), 
                name=f"end_defense_{i}_{end_h}h{end_m:02d}"
            )
            logger.info(f"-> Evento Defesa {i+1} agendado: {start_h:02d}:{start_m:02d} até {end_h:02d}:{end_m:02d} ({JOB_TIMEZONE})")

    else:
        logger.warning("Lista EVENT_TIMES vazia. Jobs de Defesa do Reino não agendados.")

    # --- [MUDANÇA] Agendamento Evento 2: Demônio Dimensional ---
    logger.info("Agendando o Demônio Dimensional (World Boss)...")
    
    if WORLD_BOSS_TIMES:
        for i, (start_h, start_m, end_h, end_m) in enumerate(WORLD_BOSS_TIMES):
            try:
                start_dt = datetime(2000, 1, 1, start_h, start_m)
                end_dt = datetime(2000, 1, 1, end_h, end_m)
                if end_dt < start_dt:
                    end_dt += timedelta(days=1)

                duration_hours = (end_dt - start_dt).total_seconds() / 3600.0
                if duration_hours <= 0: duration_hours = 1.0 
            except Exception:
                duration_hours = 1.0 

            job_data_start = {"duration_hours": duration_hours}

            j.run_daily(
                iniciar_world_boss_job, 
                time=time(hour=start_h, minute=start_m, tzinfo=local_tz),
                name=f"start_world_boss_{i}_{start_h}h{start_m:02d}",
                data=job_data_start 
            )

            j.run_daily(
                end_world_boss_job, 
                time=time(hour=end_h, minute=end_m, tzinfo=local_tz), 
                name=f"end_world_boss_{i}_{end_h}h{end_m:02d}"
            )
            logger.info(f"-> World Boss {i+1} agendado: {start_h:02d}:{start_m:02d} até {end_h:02d}:{end_m:02d} ({JOB_TIMEZONE})")

    else:
        logger.warning("Lista WORLD_BOSS_TIMES vazia. Jobs do World Boss não agendados.")

    logging.info("Agendando jobs de temporada PvP... (DESATIVADOS - agora manuais via admin)")
    logging.info("Todos os jobs foram registrados com sucesso.")


# <<< [CORREÇÃO] CRIA UMA NOVA FUNÇÃO PARA O 'post_init' >>>
async def post_initialization_hook(application: Application):
    """
    Função executada após application.initialize() ser chamado.
    Usada para o watchdog e para a mensagem de startup.
    """
    # 1. Executa o Watchdog
    try:
        logger.info("[Watchdog] Executando verificação de ações presas...")
        await check_stale_actions_on_startup(application)
    except Exception as e:
        logger.error(f"Falha ao executar o Watchdog de inicialização: {e}", exc_info=True)
        # Continua mesmo se o watchdog falhar

    # 2. Envia a mensagem de Startup
    await send_startup_message(application)

    
# --- [CORREÇÃO] FUNÇÃO PRINCIPAL MANUAL (EVITA O RUNTIMEERROR) ---
async def main():
    logger.info("Iniciando o servidor Flask em segundo plano...")
    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    logger.info("Configurando a aplicação Telegram...")
    
    # --- [CORREÇÃO 3] Bloco de Timeout e Request ---
    # Aumenta os tempos limite para 30 segundos
    http_request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0
    )
    application = Application.builder().token(TELEGRAM_TOKEN).request(http_request).build()
    
    application.add_handler(CommandHandler("debug_inv", debug_inv_cmd))

    application.add_error_handler(error_handler)
    
    register_jobs(application) 
    register_all_handlers(application)
    register_event_handlers(application)
    register_evolution_handlers(application)

    logger.info("Bot configurado. Iniciando...")

    try:
        # 1. Inicializa o bot (prepara o job_queue, etc.)
        await application.initialize()
        
        # 2. Executa o Watchdog e a Mensagem de Startup
        await post_initialization_hook(application) 
        
        # 3. Começa a "ouvir" (getUpdates)
        # --- [CORREÇÃO 4] Adiciona drop_pending_updates=True ---
        await application.updater.start_polling(drop_pending_updates=True)
        
        # 4. Começa a processar os handlers
        await application.start()

        logger.info("Bot iniciado. Polling... (Pressione Ctrl+C para parar)")
        
        # Mantém o script vivo
        while True:
            await asyncio.sleep(3600) # Dorme por 1 hora e repete

    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot parado (Interrupção).")
    except Exception as e:
        # O 'Conflict' não será pego aqui, será pego pelo error_handler
        logger.critical(f"Bot parado devido a erro: {e}", exc_info=True)
    finally:
        logger.info("Desligando o bot...")
        if application.updater and application.updater.running:
            await application.updater.stop()
        if application.running:
            await application.stop()
        await application.shutdown()
        logger.info("Bot desligado.")
async def debug_inv_cmd(update, context):
    """Comando secreto para ver IDs do inventário."""
    user_id = update.effective_user.id
    # Agora o player_manager vai funcionar
    pdata = await player_manager.get_player_data(user_id)
    
    inv = pdata.get("inventory", {})
    msg = "🕵️‍♂️ **RAIO-X DO INVENTÁRIO** 🕵️‍♂️\n\n"
    
    if not inv:
        msg += "Inventário vazio."
    else:
        for item_id, qtd in inv.items():
            # Mostra o ID cru e a quantidade
            msg += f"📦 ID: <code>{item_id}</code> | Qtd: {qtd}\n"
            
    await update.message.reply_text(msg, parse_mode="HTML")

if __name__ == "__main__":
    asyncio.run(main())