# Arquivo: main.py

from __future__ import annotations
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()
import logging
# Importações de datetime/timezone
from datetime import time, datetime, timedelta, timezone # Garante timezone aqui
from zoneinfo import ZoneInfo

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
        await application.bot.send_message(
            chat_id=ADMIN_ID,
            text="🤖 𝑭𝒂𝒍𝒂 𝑨𝒗𝒆𝒏𝒕𝒖𝒓𝒆𝒊𝒓𝒐 𝒐 👾 𝑴𝒖𝒏𝒅𝒐 𝒅𝒆 𝑬𝒍𝒅𝒐𝒓𝒂 𝒂𝒄𝒂𝒃𝒂 𝒅𝒆 𝒓𝒆𝒕𝒐𝒓𝒏𝒂𝒓 𝒅𝒆 𝒔𝒖𝒂 𝑨𝒕𝒖𝒂𝒍𝒊𝒛𝒂𝒄̧𝒂̃𝒐 👾",
            parse_mode="Markdown", # Verifica se a formatação está correta para Markdown
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

        for start_h, start_m, end_h, end_m in EVENT_TIMES:
            logging.warning(
                f"-> Evento agendado para as {start_h:02d}:{start_m:02d} no fuso '{JOB_TIMEZONE}'."
            )
        logging.warning("--- FIM DO RELATÓRIO ---")

    except Exception as e:
        logging.error(f"Erro no job de diagnóstico: {e}")
# ====================================================================

# --- FUNÇÃO DE REGISTRO DE JOBS ---
def register_jobs(application: Application):
    logging.info("Registrando jobs...")
    j = application.job_queue
    utc_tz = timezone.utc # Define UTC

    # Tenta carregar o timezone local, usa UTC como fallback
    try:
        local_tz = ZoneInfo(JOB_TIMEZONE)
        logging.info(f"Usando timezone local '{JOB_TIMEZONE}' para jobs diários.")
    except Exception as e_tz:
        logging.error(f"CRÍTICO: Falha ao carregar timezone '{JOB_TIMEZONE}': {e_tz}. Usando UTC como fallback para jobs diários.")
        local_tz = utc_tz # Fallback

    # Job de Diagnóstico
    j.run_once(schedule_checker_job, 10)

    # Jobs Existentes (Corrigidos para usar local_tz)
    j.run_repeating(regenerate_energy_job, interval=60, first=5, name="regenerate_energy")
    j.run_repeating(
        timed_actions_watchdog, 
        interval=60,  # Verifica a cada 60 segundos
        first=15,     # Começa 15 segundos após o bot iniciar
        name="watchdog_acoes"
    )
    logging.info("-> Job 'watchdog_acoes' agendado para rodar a cada minuto.")
    # Usa local_tz para todos os run_daily
    j.run_daily(daily_crystal_grant_job, time=time(0, 0, tzinfo=local_tz), name="daily_crystals")
    j.run_daily(daily_pvp_entry_reset_job, time=time(0, 1, tzinfo=local_tz), name="daily_pvp_reset")

    logging.info("Registrando jobs de eventos do reino...")
    j.run_daily(daily_event_ticket_job, time=time(hour=9, minute=0, tzinfo=local_tz), name="daily_event_ticket")
    j.run_daily(afternoon_event_reminder_job, time=time(hour=14, minute=0, tzinfo=local_tz), name="afternoon_event_reminder")
    for start_h, start_m, end_h, end_m in EVENT_TIMES:
        j.run_daily(start_event_job, time=time(hour=start_h, minute=start_m, tzinfo=local_tz), name=f"start_defense_{start_h}h{start_m:02d}")
        j.run_daily(end_event_job, time=time(hour=end_h, minute=end_m, tzinfo=local_tz), name=f"end_defense_{end_h}h{end_m:02d}")

    logging.info("Agendando o sorteador do Demônio Dimensional...")
    j.run_daily(agendador_mestre_do_boss, time=time(hour=0, minute=5, tzinfo=local_tz), name="agendador_mestre_do_boss")

    # [NOVOS JOBS] Agendamento Recompensa e Reset PvP (usando utc_tz para clareza)
    logging.info("Agendando jobs de temporada PvP...")
    j.run_repeating(
        callback=distribute_pvp_rewards,
        interval=timedelta(days=28),
        first=time(hour=3, minute=0, tzinfo=utc_tz), # 3:00 UTC
        name="RecompensasPvPMensais"
    )
    logging.info("-> Job 'RecompensasPvPMensais' agendado para 3:00 UTC a cada 28 dias.")

    j.run_repeating(
        callback=reset_pvp_season,
        interval=timedelta(days=30),
        first=time(hour=3, minute=5, tzinfo=utc_tz), # 3:05 UTC
        name="ResetTemporadaPvP"
    )
    logging.info("-> Job 'ResetTemporadaPvP' agendado para 3:05 UTC a cada 30 dias.")

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