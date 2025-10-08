# Arquivo: main.py

from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()
import logging
from datetime import time
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import Application, ContextTypes

# --- IMPORTAÇÕES PRINCIPAIS ---
# GARANTA QUE JOB_TIMEZONE ESTÁ SENDO IMPORTADO DAQUI
from config import ADMIN_ID, TELEGRAM_TOKEN, EVENT_TIMES, JOB_TIMEZONE
from registries import register_all_handlers

# Importe suas funções de jobs
from handlers.jobs import (
    regenerate_energy_job,
    daily_crystal_grant_job,
    daily_event_ticket_job,
    afternoon_event_reminder_job
)
from handlers.daily_jobs import daily_pvp_entry_reset_job
from kingdom_defense.engine import start_event_job, end_event_job

# --- CONFIGURAÇÃO DE LOGGING ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# --- HANDLERS DE ERRO E STARTUP ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.exception("Exceção ao processar update: %s", context.error)

async def send_startup_message(application: Application):
    if not ADMIN_ID: return
    try:
        await application.bot.send_message(
            chat_id=ADMIN_ID,
            text="🤖 𝑭𝒂𝒍𝒂 𝑨𝒗𝒆𝒏𝒕𝒖𝒓𝒆𝒊𝒓𝒐 𝒐 👾 𝑴𝒖𝒏𝒅𝒐 𝒅𝒆 𝑬𝒍𝒅𝒐𝒓𝒂 𝒂𝒄𝒂𝒃𝒂 𝒅𝒆 𝒓𝒆𝒕𝒐𝒓𝒏𝒂𝒓 𝒅𝒆 𝒔𝒖𝒂 𝑨𝒕𝒖𝒂𝒍𝒊𝒛𝒂𝒄̧𝒂̃𝒐 👾",
            parse_mode="Markdown",
            disable_notification=True,
        )
    except Exception as e:
        logging.warning("Não foi possível enviar mensagem inicial: %s", e)

# --- FUNÇÃO DE REGISTRO DE JOBS (CORRIGIDA) ---
def register_jobs(application: Application):
    logging.info("Registrando jobs...")
    j = application.job_queue
    # A variável tz agora usa o JOB_TIMEZONE importado do config.py
    tz = ZoneInfo(JOB_TIMEZONE)

    # Jobs existentes
    j.run_repeating(regenerate_energy_job, interval=60, first=5, name="regenerate_energy")
    j.run_daily(daily_crystal_grant_job, time=time(0, 0, tzinfo=tz), name="daily_crystals")
    j.run_daily(daily_pvp_entry_reset_job, time=time(0, 1, tzinfo=tz), name="daily_pvp_reset")
    
    # Novos Jobs de Evento
    logging.info("Registrando jobs de eventos do reino...")
    j.run_daily(daily_event_ticket_job, time=time(hour=9, minute=0, tzinfo=tz), name="daily_event_ticket")
    j.run_daily(afternoon_event_reminder_job, time=time(hour=14, minute=0, tzinfo=tz), name="afternoon_event_reminder")
    
    # Agendamento dos eventos
    for start_h, start_m, end_h, end_m in EVENT_TIMES:
        j.run_daily(start_event_job, time=time(hour=start_h, minute=start_m, tzinfo=tz), name=f"start_defense_{start_h}h{start_m:02d}")
        j.run_daily(end_event_job, time=time(hour=end_h, minute=end_m, tzinfo=tz), name=f"end_defense_{end_h}h{end_m:02d}")

    logging.info("Todos os jobs foram registrados com sucesso.")

# --- FUNÇÃO PRINCIPAL ---
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_error_handler(error_handler)
    
    register_jobs(application)
    register_all_handlers(application)
    
    application.post_init = send_startup_message
    
    logging.info("Iniciando o bot...")
    application.run_polling()

if __name__ == "__main__":
    main()