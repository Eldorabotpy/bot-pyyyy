# main.py
# (VERSÃO CORRIGIDA: SEM PORTAL DIMENSIONAL)

from __future__ import annotations
import asyncio
import os
import sys
import logging
import time
from threading import Thread
from datetime import time as dt_time, timezone
from zoneinfo import ZoneInfo

# Adiciona diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from telegram import Update
from telegram.ext import Application
from telegram.error import Conflict, NetworkError

# --- CONFIGURAÇÕES ---
from config import (
    ADMIN_ID, 
    TELEGRAM_TOKEN, 
    EVENT_TIMES, 
    JOB_TIMEZONE, 
    WORLD_BOSS_TIMES, 
    STARTUP_IMAGE_ID
)
from registries import register_all_handlers

# --- IMPORTAÇÃO DOS JOBS ---
# (Removido o portal daqui para não dar erro)
from handlers.jobs import (
    regenerate_energy_job,
    daily_crystal_grant_job,
    job_pvp_monthly_reset
)

# Configuração de Logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==============================================================================
# 🌐 SERVIDOR WEB (KEEP ALIVE)
# ==============================================================================
app = Flask('')

@app.route('/')
def home():
    return "I'm alive! Bot is running."

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def start_keep_alive():
    t = Thread(target=run_flask)
    t.start()

# ==============================================================================
# ⚙️ TAREFAS DE INICIALIZAÇÃO (POST-INIT)
# ==============================================================================
async def post_init_tasks(application: Application):
    """Executa agendamentos, recuperações e avisos após o bot iniciar."""
    
    # 1. Notificação Admin
    if ADMIN_ID:
        try: 
            msg_text = "🤖 <b>Sistema Online!</b>\n<i>Defesa do Reino e World Boss configurados.</i>"
            if STARTUP_IMAGE_ID:
                await application.bot.send_photo(chat_id=ADMIN_ID, photo=STARTUP_IMAGE_ID, caption=msg_text, parse_mode="HTML")
            else:
                await application.bot.send_message(chat_id=ADMIN_ID, text=msg_text, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Msg Admin falhou (verifique STARTUP_IMAGE_ID no config): {e}")
    
    # 2. Watchdog
    try:
        from modules.player.actions import check_stale_actions_on_startup
        await check_stale_actions_on_startup(application)
    except ImportError: pass
    
    # 3. Recuperação de Caças
    try:
        from modules.recovery_manager import recover_active_hunts
        logging.info("[Startup] Recuperando caças ativas...")
        asyncio.create_task(recover_active_hunts(application))
    except ImportError: pass

    # ==========================================================================
    # 📅 AGENDAMENTO DE JOBS (CRON)
    # ==========================================================================
    
    jq = application.job_queue 

    try:
        tz = ZoneInfo(JOB_TIMEZONE)
    except Exception:
        tz = timezone.utc
        logging.warning(f"Fuso horário {JOB_TIMEZONE} inválido. Usando UTC.")

    # --- A. Reset Diário ---
    jq.run_daily(daily_crystal_grant_job, time=dt_time(hour=0, minute=0, tzinfo=tz), name="daily_crystal")
    
    # --- B. Defesa do Reino ---
    if EVENT_TIMES:
        from handlers.jobs import start_kingdom_defense_event
        
        # Config: [(9, 10, 9, 40), ...]
        for i, (sh, sm, eh, em) in enumerate(EVENT_TIMES):
            try:
                start_min = sh * 60 + sm
                end_min = eh * 60 + em
                duration = end_min - start_min
                if duration < 0: duration += 1440 

                jq.run_daily(
                    start_kingdom_defense_event, 
                    time=dt_time(hour=sh, minute=sm, tzinfo=tz), 
                    name=f"kingdom_defense_{i}",
                    data={"event_duration_minutes": duration}
                )
                logging.info(f"🛡️ Defesa agendada: {sh:02d}:{sm:02d} ({duration} min)")
            except Exception as e:
                logging.error(f"Erro ao agendar Defesa {i}: {e}")

    # --- C. World Boss ---
    if WORLD_BOSS_TIMES:
        from handlers.jobs import start_world_boss_job, end_world_boss_job
        
        # Config: [(18, 0, 19, 0), ...]
        for i, (sh, sm, eh, em) in enumerate(WORLD_BOSS_TIMES):
            try:
                jq.run_daily(
                    start_world_boss_job, 
                    time=dt_time(hour=sh, minute=sm, tzinfo=tz), 
                    name=f"start_boss_{i}"
                )
                jq.run_daily(
                    end_world_boss_job, 
                    time=dt_time(hour=eh, minute=em, tzinfo=tz), 
                    name=f"end_boss_{i}"
                )
                logging.info(f"👹 Boss agendado: Nasce {sh:02d}:{sm:02d} -> Foge {eh:02d}:{em:02d}")
            except Exception as e:
                logging.error(f"Erro ao agendar Boss {i}: {e}")

    # --- D. PvP Mensal ---
    try:
        # Tenta importar só se existir no jobs.py
        from handlers.jobs import job_pvp_monthly_reset
        jq.run_daily(job_pvp_monthly_reset, time=dt_time(hour=0, minute=0, tzinfo=tz), name="pvp_monthly_check")
    except ImportError:
        logging.warning("Job de PvP Mensal não encontrado, pulando.")

    logging.info("✅ Jobs agendados.")

# ==============================================================================
# 🚀 EXECUÇÃO PRINCIPAL
# ==============================================================================
if __name__ == '__main__':
    try:
        start_keep_alive()
        logging.info("🌐 Servidor Web iniciado.")
    except Exception as e:
        logging.warning(f"⚠️ Erro no servidor Web: {e}")

    application = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init_tasks).build()
    register_all_handlers(application)
    
    logging.info("🤖 Bot configurado. Iniciando...")

    MAX_RETRIES = 100
    RETRY_DELAY = 10 

    for attempt in range(MAX_RETRIES):
        try:
            application.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
            break 
        except Conflict:
            logging.warning(f"⚠️ CONFLITO: Outra instância rodando. Aguardando {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)
        except NetworkError:
            logging.warning("⚠️ Erro de Rede. Reconectando em 5s...")
            time.sleep(5)
        except KeyboardInterrupt:
            logging.info("🛑 Bot paralisado pelo usuário.")
            break
        except Exception as e:
            logging.error(f"❌ Erro fatal: {e}")
            time.sleep(5)