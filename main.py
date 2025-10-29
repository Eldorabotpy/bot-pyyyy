# Arquivo: main.py

from __future__ import annotations
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logging
from dotenv import load_dotenv
load_dotenv()
# Importações de datetime/timezone
from datetime import time, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from threading import Thread
from flask import Flask

from telegram import Update
from telegram.ext import Application, ContextTypes

from config import ADMIN_ID, TELEGRAM_TOKEN, EVENT_TIMES, JOB_TIMEZONE
from registries import register_all_handlers

# Importações dos Jobs
from handlers.jobs import (
    regenerate_energy_job,
    daily_crystal_grant_job,
    daily_event_ticket_job,
    afternoon_event_reminder_job,
    distribute_pvp_rewards,
    reset_pvp_season,
    timed_actions_watchdog
)
from handlers.daily_jobs import daily_pvp_entry_reset_job
from kingdom_defense.engine import start_event_job, end_event_job
from handlers.world_boss.engine import agendador_mestre_do_boss
from modules.player import core as player_core

# --- CONFIGURAÇÃO DE LOGGING ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# --- FLASK (para Uptime Robot/Render) ---
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    """Esta é a página que o Uptime Robot vai 'visitar'."""
    return "Bot is alive and running!", 200

def run_flask():
    """Função que inicia o servidor Flask."""
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)

# ======================================================

# --- HANDLERS DE ERRO E STARTUP ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.exception("Exceção ao processar update: %s", context.error)

async def send_startup_message(application: Application):
    if not ADMIN_ID: return
    try:
        # Await já estava correto
        await application.bot.send_message(
            chat_id=ADMIN_ID,
            text="🤖 𝑭𝒂𝒍𝒂 𝑨𝒗𝒆𝒏𝒕𝒖𝒓𝒆𝒊𝒓𝒐 𝒐 👾 𝑴𝒖𝒏𝒅𝒐 𝒅𝒆 𝑬𝒍𝒅𝒐𝒓𝒂 𝒂𝒄𝒂𝒃𝒂 𝒅𝒆 𝒓𝒆𝒕𝒐𝒓𝒏𝒂𝒓 𝒅𝒆 𝒔𝒖𝒂 𝑨𝒕𝒖𝒂𝒍𝒊𝒛𝒂𝒄̧𝒂̃𝒐 👾",
            parse_mode="HTML", # Corrigido para HTML (Markdown estava incorreto para <b>)
            disable_notification=True,
        )
    except Exception as e:
        logging.warning("Não foi possível enviar mensagem inicial: %s", e)

async def schedule_checker_job(context: ContextTypes.DEFAULT_TYPE):
    """Job de diagnóstico para fuso horário."""
    try:
        tz = ZoneInfo(JOB_TIMEZONE)
        now_utc = datetime.now(timezone.utc)
        now_local = datetime.now(tz)
        logging.warning("--- RELATÓRIO DE AGENDAMENTO DE HORÁRIOS ---")
        logging.warning(f"Fuso Horário Configurado (JOB_TIMEZONE): {JOB_TIMEZONE}")
        logging.warning(f"Hora Atual no Servidor (UTC): {now_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logging.warning(f"Hora Atual (convertida para local): {now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logging.warning("--- Verificando Horários de Eventos (EVENT_TIMES) ---")
        if EVENT_TIMES: # Verifica se EVENT_TIMES não está vazio
             for start_h, start_m, end_h, end_m in EVENT_TIMES:
                 logging.warning(f"-> Evento agendado para as {start_h:02d}:{start_m:02d} no fuso '{JOB_TIMEZONE}'.")
        else:
             logging.warning("-> Lista EVENT_TIMES está vazia ou não definida.")
        logging.warning("--- FIM DO RELATÓRIO ---")
    except Exception as e:
        logging.error(f"Erro no job de diagnóstico: {e}")
# ====================================================================

# --- FUNÇÃO DE REGISTRO DE JOBS CORRIGIDA ---

def register_jobs(application: Application):
    logging.info("Registrando jobs...")
    j = application.job_queue
    utc_tz = timezone.utc # UTC é útil para 'first' em run_repeating

    # Define o timezone local para jobs 'cron' (run_daily)
    try:
        local_tz = ZoneInfo(JOB_TIMEZONE)
        logging.info(f"Usando timezone local '{JOB_TIMEZONE}' para jobs diários.")
    except Exception as e_tz:
        logging.error(f"CRÍTICO: Falha ao carregar timezone '{JOB_TIMEZONE}': {e_tz}. Usando UTC como fallback para jobs diários.")
        local_tz = utc_tz # Usa UTC se o timezone local falhar

    # --- Jobs Repetitivos (Intervalo Fixo) ---
    j.run_repeating(regenerate_energy_job, interval=60, first=timedelta(seconds=5), name="regenerate_energy")
    j.run_repeating(timed_actions_watchdog, interval=60, first=timedelta(seconds=15), name="watchdog_acoes")
    logging.info("-> Job 'watchdog_acoes' agendado para rodar a cada minuto.")

    # --- Jobs Diários ('cron' - Hora Específica no Fuso Local) ---
    j.run_daily(daily_crystal_grant_job, time=time(hour=0, minute=0, tzinfo=local_tz), name="daily_crystals")
    j.run_daily(daily_pvp_entry_reset_job, time=time(hour=0, minute=1, tzinfo=local_tz), name="daily_pvp_reset")
    logging.info("-> Job 'daily_pvp_entry_reset_job' agendado para 00:01 diariamente.")

    # --- CORREÇÃO DO HORÁRIO DO TICKET ---
    j.run_daily(
        daily_event_ticket_job, 
        time=time(hour=0, minute=10, tzinfo=local_tz), # <<< ALTERADO PARA 00:10
        name="daily_event_ticket"
    ) 
    logging.info("-> Job 'daily_event_ticket_job' agendado para 00:10 diariamente.") # <<< Log Atualizado
    # --- FIM DA CORREÇÃO ---

    j.run_daily(afternoon_event_reminder_job, time=time(hour=13, minute=30, tzinfo=local_tz), name="afternoon_event_reminder") # Ex: 13:30

    logging.info("Registrando jobs de eventos do reino...")
    if EVENT_TIMES: # Garante que a lista não está vazia
        for start_h, start_m, end_h, end_m in EVENT_TIMES:
            j.run_daily(start_event_job, time=time(hour=start_h, minute=start_m, tzinfo=local_tz), name=f"start_defense_{start_h}h{start_m:02d}")
            j.run_daily(end_event_job, time=time(hour=end_h, minute=end_m, tzinfo=local_tz), name=f"end_defense_{end_h}h{end_m:02d}")
    else:
        logging.warning("Lista EVENT_TIMES vazia ou não definida. Jobs de evento não agendados.")


    logging.info("Agendando o sorteador do Demônio Dimensional...")
    j.run_daily(agendador_mestre_do_boss, time=time(hour=0, minute=5, tzinfo=local_tz), name="agendador_mestre_do_boss")

    # --- Jobs PvP (Intervalos de Dias - Usando run_repeating com timedelta) ---
    logging.info("Agendando jobs de temporada PvP...")
    
    # Calcula a próxima ocorrência das 3:00 UTC para alinhar os intervalos
    now_utc = datetime.now(timezone.utc)
    next_3am_utc = now_utc.replace(hour=3, minute=0, second=0, microsecond=0)
    if now_utc >= next_3am_utc: # Se já passou das 3:00 UTC hoje, agenda para amanhã
        next_3am_utc += timedelta(days=1)
        
    start_time_rewards = next_3am_utc # Recompensas às 3:00 UTC
    start_time_reset = next_3am_utc.replace(minute=5) # Reset às 3:05 UTC

    # Recompensas PvP (28 dias)
    job_name_rewards = "RecompensasPvPMensais"
    # Remove jobs antigos com o mesmo nome antes de adicionar
    for job in j.get_jobs_by_name(job_name_rewards): job.schedule_removal() 
    j.run_repeating(
        callback=distribute_pvp_rewards,
        interval=timedelta(days=28),      # Intervalo correto
        first=start_time_rewards,         # Hora de início calculada (UTC)
        name=job_name_rewards
    ) 
    logging.info(f"-> Job '{job_name_rewards}' agendado para ciclo de 28 dias (próxima execução ~ {start_time_rewards.isoformat()}).")

    # Reset Temporada PvP (30 dias)
    job_name_reset = "ResetTemporadaPvP"
    for job in j.get_jobs_by_name(job_name_reset): job.schedule_removal()
    j.run_repeating(
        callback=reset_pvp_season,
        interval=timedelta(days=30),      # Intervalo correto
        first=start_time_reset,           # Hora de início calculada (UTC)
        name=job_name_reset
    ) 
    logging.info(f"-> Job '{job_name_reset}' agendado para ciclo de 30 dias (próxima execução ~ {start_time_reset.isoformat()}).")

    # Job de Diagnóstico (Opcional: correr periodicamente para verificar)
    # j.run_repeating(schedule_checker_job, interval=timedelta(hours=6), name="schedule_checker_job_periodic")

    logging.info("Todos os jobs foram registrados com sucesso.")

def register_jobs(application: Application):
    logging.info("Registrando jobs...")
    j = application.job_queue
    utc_tz = timezone.utc # UTC é útil para 'first' em run_repeating

    # Define o timezone local para jobs 'cron' (run_daily)
    try:
        local_tz = ZoneInfo(JOB_TIMEZONE)
        logging.info(f"Usando timezone local '{JOB_TIMEZONE}' para jobs diários.")
    except Exception as e_tz:
        logging.error(f"CRÍTICO: Falha ao carregar timezone '{JOB_TIMEZONE}': {e_tz}. Usando UTC como fallback para jobs diários.")
        local_tz = utc_tz # Usa UTC se o timezone local falhar

    # --- Jobs Repetitivos (Intervalo Fixo) ---
    j.run_repeating(regenerate_energy_job, interval=60, first=timedelta(seconds=5), name="regenerate_energy")
    j.run_repeating(timed_actions_watchdog, interval=60, first=timedelta(seconds=15), name="watchdog_acoes")
    logging.info("-> Job 'watchdog_acoes' agendado para rodar a cada minuto.")

    # --- Jobs Diários ('cron' - Hora Específica no Fuso Local) ---
    j.run_daily(daily_crystal_grant_job, time=time(hour=0, minute=0, tzinfo=local_tz), name="daily_crystals")
    
    # >>> JOB DESATIVADO (Será manual via painel admin) <<<
    # j.run_daily(daily_pvp_entry_reset_job, time=time(hour=0, minute=1, tzinfo=local_tz), name="daily_pvp_reset")
    # logging.info("-> Job 'daily_pvp_entry_reset_job' agendado para 00:01 diariamente.")

    # --- CORREÇÃO DO HORÁRIO DO TICKET (Mantido) ---
    #j.run_daily(
     ##  time=time(hour=0, minute=10, tzinfo=local_tz), # <<< 00:10
     # name="daily_event_ticket"
    #) 
    #logging.info("-> Job 'daily_event_ticket_job' agendado para 00:10 diariamente.")
    # --- FIM DA CORREÇÃO ---

    j.run_daily(afternoon_event_reminder_job, time=time(hour=13, minute=30, tzinfo=local_tz), name="afternoon_event_reminder") # Ex: 13:30

    logging.info("Registrando jobs de eventos do reino...")
    if EVENT_TIMES: # Garante que a lista não está vazia
        for start_h, start_m, end_h, end_m in EVENT_TIMES:
            j.run_daily(start_event_job, time=time(hour=start_h, minute=start_m, tzinfo=local_tz), name=f"start_defense_{start_h}h{start_m:02d}")
            j.run_daily(end_event_job, time=time(hour=end_h, minute=end_m, tzinfo=local_tz), name=f"end_defense_{end_h}h{end_m:02d}")
    else:
        logging.warning("Lista EVENT_TIMES vazia ou não definida. Jobs de evento não agendados.")


    logging.info("Agendando o sorteador do Demônio Dimensional...")
    j.run_daily(agendador_mestre_do_boss, time=time(hour=0, minute=5, tzinfo=local_tz), name="agendador_mestre_do_boss")

    # --- Jobs PvP (Intervalos de Dias - Usando run_repeating com timedelta) ---
    logging.info("Agendando jobs de temporada PvP... (DESATIVADOS - agora manuais via admin)")
    
    # Calcula a próxima ocorrência das 3:00 UTC (necessário para os logs, mesmo desativado)
    now_utc = datetime.now(timezone.utc)
    next_3am_utc = now_utc.replace(hour=3, minute=0, second=0, microsecond=0)
    if now_utc >= next_3am_utc: 
        next_3am_utc += timedelta(days=1)
    start_time_rewards = next_3am_utc
    start_time_reset = next_3am_utc.replace(minute=5) 

    # >>> JOB DESATIVADO (Será manual via painel admin) <<<
    # job_name_rewards = "RecompensasPvPMensais"
    # for job in j.get_jobs_by_name(job_name_rewards): job.schedule_removal() 
    # j.run_repeating(
    #     callback=distribute_pvp_rewards,
    #     interval=timedelta(days=28), 
    #     first=start_time_rewards,
    #     name=job_name_rewards
    # ) 
    # logging.info(f"-> Job '{job_name_rewards}' (DESATIVADO) seria agendado para ciclo de 28 dias.")

    # >>> JOB DESATIVADO (Será manual via painel admin) <<<
    # job_name_reset = "ResetTemporadaPvP"
    # for job in j.get_jobs_by_name(job_name_reset): job.schedule_removal()
    # j.run_repeating(
    #     callback=reset_pvp_season,
    #     interval=timedelta(days=30), 
    #     first=start_time_reset, 
    #     name=job_name_reset
    # ) 
    # logging.info(f"-> Job '{job_name_reset}' (DESATIVADO) seria agendado para ciclo de 30 dias.")

    logging.info("Todos os jobs foram registrados com sucesso.")
    
# --- FUNÇÃO PRINCIPAL (Sem alterações necessárias) ---
def main():
    logging.info("Iniciando o servidor Flask em segundo plano...")
    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    logging.info("Configurando a aplicação Telegram...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_error_handler(error_handler)
    
    register_jobs(application) # Chama a função corrigida
    register_all_handlers(application)

    application.post_init = send_startup_message

    logging.info("Iniciando o bot em modo polling...")
    application.run_polling()

if __name__ == "__main__":
    main()