# Arquivo: main.py (VERSÃO FINAL COM AMBOS OS EVENTOS AGENDADOS)

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

from telegram import Update
from telegram.ext import Application, ContextTypes

# <<< MUDANÇA: Importa a nova lista de horários >>>
from config import ADMIN_ID, TELEGRAM_TOKEN, EVENT_TIMES, JOB_TIMEZONE, WORLD_BOSS_TIMES
from registries import register_all_handlers

# --- Importa os jobs corretos ---
from handlers.jobs import (
    regenerate_energy_job,
    daily_crystal_grant_job,
    afternoon_event_reminder_job,
    timed_actions_watchdog,
    start_kingdom_defense_event, # Job da Defesa do Reino
    end_kingdom_defense_event,   # Job da Defesa do Reino
    daily_arena_ticket_job       # Job do Ticket da Arena
)
# (Removemos a importação do daily_pvp_entry_reset_job)

# <<< MUDANÇA: Importa os jobs corretos do World Boss >>>
from handlers.world_boss.engine import (
    iniciar_world_boss_job,
    end_world_boss_job
)
# (Removemos a importação do agendador_mestre_do_boss)

from modules.player import core as player_core

# --- CONFIGURAÇÃO DE LOGGING ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# --- FLASK ---
flask_app = Flask(__name__)
@flask_app.route('/')
def health_check():
    return "Bot is alive and running!", 200
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)

# --- HANDLERS DE ERRO E STARTUP ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.exception("Exceção ao processar update: %s", context.error)

async def send_startup_message(application: Application):
    if not ADMIN_ID: return
    try:
        await application.bot.send_message(
            chat_id=ADMIN_ID,
            text="🤖 𝑭𝒂𝒍𝒂 𝑨𝒗𝒆𝒏𝒕𝒖𝒓𝒆𝒊𝒓𝒐 𝒐 👾 𝑴𝒖𝒏𝒅𝒐 𝒅𝒆 𝑬𝒍𝒅𝒐𝒓𝒂 𝒂𝒄𝒂𝒃𝒂 𝒅𝒆 𝒓𝒆𝒕𝒐𝒓𝒏𝒂𝒓 𝒅𝒆 𝒔𝒖𝒂 𝑨𝒕𝒖𝒂𝒍𝒊𝒛𝒂𝒄̧𝒂̃𝒐 👾",
            parse_mode="HTML",
            disable_notification=True,
        )
    except Exception as e:
        logging.warning("Não foi possível enviar mensagem inicial: %s", e)

# (A função de diagnóstico schedule_checker_job fica igual)
async def schedule_checker_job(context: ContextTypes.DEFAULT_TYPE):
    # ... (código de diagnóstico) ...
    pass

# ====================================================================

# --- FUNÇÃO DE REGISTRO DE JOBS (CORRIGIDA PARA OS DOIS EVENTOS) ---

def register_jobs(application: Application):
    logging.info("Registrando jobs...")
    j = application.job_queue
    
    try:
        local_tz = ZoneInfo(JOB_TIMEZONE)
        logging.info(f"Usando timezone local '{JOB_TIMEZONE}' para jobs diários.")
    except Exception as e_tz:
        logging.error(f"CRÍTICO: Falha ao carregar timezone '{JOB_TIMEZONE}': {e_tz}. Usando UTC como fallback.")
        local_tz = timezone.utc

    # --- Jobs Repetitivos (Intervalo Fixo) ---
    j.run_repeating(regenerate_energy_job, interval=60, first=timedelta(seconds=5), name="regenerate_energy")
    j.run_repeating(timed_actions_watchdog, interval=60, first=timedelta(seconds=15), name="watchdog_acoes")
    logging.info("-> Job 'watchdog_acoes' agendado para rodar a cada minuto.")

    # --- Jobs Diários ('cron' - Hora Específica no Fuso Local) ---
    j.run_daily(daily_crystal_grant_job, time=time(hour=0, minute=0, tzinfo=local_tz), name="daily_crystals")
    
    # Job de Tickets da Arena (às 02:00)
    j.run_daily(
        daily_arena_ticket_job, 
        time=time(hour=2, minute=0, tzinfo=local_tz),
        name="daily_arena_tickets"
    )
    logging.info("-> Job 'daily_arena_ticket_job' agendado para 02:00 diariamente.")
    
    # Lembrete (13:30)
    j.run_daily(afternoon_event_reminder_job, time=time(hour=13, minute=30, tzinfo=local_tz), name="afternoon_event_reminder")

    # --- [MUDANÇA] Agendamento Evento 1: Defesa do Reino ---
    logging.info("Registrando jobs de eventos do reino (Defesa)...")
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
            
            j.run_daily(
                start_kingdom_defense_event, 
                time=time(hour=start_h, minute=start_m, tzinfo=local_tz), 
                name=f"start_defense_{i}_{start_h}h{start_m:02d}",
                data=job_data_start
            )
            j.run_daily(
                end_kingdom_defense_event, 
                time=time(hour=end_h, minute=end_m, tzinfo=local_tz), 
                name=f"end_defense_{i}_{end_h}h{end_m:02d}"
            )
            logging.info(f"-> Evento Defesa {i+1} agendado: {start_h:02d}:{start_m:02d} até {end_h:02d}:{end_m:02d} ({JOB_TIMEZONE})")
            
    else:
        logging.warning("Lista EVENT_TIMES vazia. Jobs de Defesa do Reino não agendados.")

    # --- [MUDANÇA] Agendamento Evento 2: Demônio Dimensional ---
    logging.info("Agendando o Demônio Dimensional (World Boss)...")
    
    # Remove o agendador aleatório antigo
    # j.run_daily(agendador_mestre_do_boss, ...)
    
    if WORLD_BOSS_TIMES:
        for i, (start_h, start_m, end_h, end_m) in enumerate(WORLD_BOSS_TIMES):
            # Calcula a duração em horas (precisa ser float)
            try:
                start_dt = datetime(2000, 1, 1, start_h, start_m)
                end_dt = datetime(2000, 1, 1, end_h, end_m)
                # Lida com o evento que atravessa a meia-noite (ex: 23:00 -> 01:00)
                if end_dt < start_dt:
                    end_dt += timedelta(days=1)
                
                duration_hours = (end_dt - start_dt).total_seconds() / 3600.0
                if duration_hours <= 0: duration_hours = 1.0 # Fallback 1 hora
            except Exception:
                duration_hours = 1.0 # Fallback 1 hora
            
            job_data_start = {"duration_hours": duration_hours}

            # Agenda o INÍCIO do boss
            j.run_daily(
                iniciar_world_boss_job, # <<< Função correta
                time=time(hour=start_h, minute=start_m, tzinfo=local_tz),
                name=f"start_world_boss_{i}_{start_h}h{start_m:02d}",
                data=job_data_start # Passa a duração
            )
            
            # Agenda o FIM do boss
            j.run_daily(
                end_world_boss_job, # <<< Função correta
                time=time(hour=end_h, minute=end_m, tzinfo=local_tz),
                name=f"end_world_boss_{i}_{end_h}h{end_m:02d}"
            )
            logging.info(f"-> World Boss {i+1} agendado: {start_h:02d}:{start_m:02d} até {end_h:02d}:{end_m:02d} ({JOB_TIMEZONE})")
            
    else:
        logging.warning("Lista WORLD_BOSS_TIMES vazia. Jobs do World Boss não agendados.")

    logging.info("Agendando jobs de temporada PvP... (DESATIVADOS - agora manuais via admin)")
    logging.info("Todos os jobs foram registrados com sucesso.")
    
# --- FUNÇÃO PRINCIPAL ---
def main():
    logging.info("Iniciando o servidor Flask em segundo plano...")
    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    logging.info("Configurando a aplicação Telegram...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_error_handler(error_handler)
    
    register_jobs(application) 
    register_all_handlers(application)

    application.post_init = send_startup_message

    logging.info("Iniciando o bot em modo polling...")
    application.run_polling()

if __name__ == "__main__":
    main()