# main.py
# (VERSÃO FINAL: Importação direta e ordem de prioridade corrigida)

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

# --- IMPORTS DOS REGISTROS ---
from registries import register_all_handlers
from registries.class_evolution import register_evolution_handlers
from registries.market import register_market_handlers

# Importa handler de personagem (Start/Criação)
try:
    from registries.character import register_character_handlers
except ImportError:
    from registries import register_character_handlers

# --- IMPORTAÇÃO DO GERENCIADOR DE ARQUIVOS (ADMIN) ---
# Se este import falhar, verifique se existe handlers/admin/__init__.py
from handlers.admin.file_id_conv import file_id_conv_handler

# --- JOBS ---
from handlers.jobs import (
    regenerate_energy_job,
    daily_crystal_grant_job,
    afternoon_event_reminder_job,
    start_kingdom_defense_event,
    end_kingdom_defense_event,
    daily_arena_ticket_job,
    start_world_boss_job,
    end_world_boss_job,
    job_pvp_monthly_reset,
    distribute_kingdom_defense_ticket_job
)

try:
    from modules.world_boss.engine import world_boss_manager
except ImportError:
    world_boss_manager = None

# Configuração de Logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==============================================================================
# SERVIDOR WEB (KEEP ALIVE)
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
# TAREFAS DE INICIALIZAÇÃO
# ==============================================================================
async def post_init_tasks(application: Application):
    
    # 1. Limpeza de Boss Fantasma
    if world_boss_manager and world_boss_manager.is_active:
        logger.warning("Detectado World Boss ativo de sessão anterior. Encerrando...")
        world_boss_manager.end_event(reason="Reinício do Sistema")
    
    # 2. Notificação Admin
    if ADMIN_ID:
        try: 
            msg_text = "🤖 <b>Sistema Online!</b>"
            if STARTUP_IMAGE_ID:
                await application.bot.send_photo(chat_id=ADMIN_ID, photo=STARTUP_IMAGE_ID, caption=msg_text, parse_mode="HTML")
            else:
                await application.bot.send_message(chat_id=ADMIN_ID, text=msg_text, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Msg Admin falhou: {e}")
    
    # 3. Recuperação de Ações (Watchdog)
    try:
        from modules.player.actions import check_stale_actions_on_startup
        await check_stale_actions_on_startup(application)
    except ImportError: pass
    
    # 4. Recuperação de Caças
    try:
        from modules.recovery_manager import recover_active_hunts
        asyncio.create_task(recover_active_hunts(application))
    except ImportError: pass
    
    # 5. Agendamento de Jobs
    jq = application.job_queue 
    try:
        tz = ZoneInfo(JOB_TIMEZONE)
    except Exception:
        tz = timezone.utc

    jq.run_daily(daily_crystal_grant_job, time=dt_time(hour=0, minute=0, tzinfo=tz), name="daily_crystal")
    
    if EVENT_TIMES:
        for i, (sh, sm, eh, em) in enumerate(EVENT_TIMES):
            try:
                start_min = sh * 60 + sm
                end_min = eh * 60 + em
                duration = end_min - start_min
                if duration < 0: duration += 1440 
                jq.run_daily(start_kingdom_defense_event, time=dt_time(hour=sh, minute=sm, tzinfo=tz), name=f"kingdom_defense_{i}", data={"event_duration_minutes": duration})
            except: pass

    if WORLD_BOSS_TIMES:
        for i, (sh, sm, eh, em) in enumerate(WORLD_BOSS_TIMES):
            try:
                jq.run_daily(start_world_boss_job, time=dt_time(hour=sh, minute=sm, tzinfo=tz), name=f"start_boss_{i}")
                jq.run_daily(end_world_boss_job, time=dt_time(hour=eh, minute=em, tzinfo=tz), name=f"end_boss_{i}")
            except: pass

    try:
        from handlers.jobs import job_pvp_monthly_reset
        jq.run_daily(job_pvp_monthly_reset, time=dt_time(hour=0, minute=0, tzinfo=tz), name="pvp_monthly_check")
    except ImportError: pass

    logging.info("Jobs agendados.")

# ==============================================================================
# EXECUÇÃO PRINCIPAL
# ==============================================================================
if __name__ == '__main__':
    try:
        start_keep_alive()
        logging.info("Servidor Web iniciado.")
    except Exception as e:
        logging.warning(f"Erro no servidor Web: {e}")

    application = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init_tasks).build()

    # --- REGISTRO DE HANDLERS (ORDEM IMPORTANTE) ---

    # 1. Admin / Ferramentas (Prioridade Máxima)
    # Deve vir antes de tudo para capturar input de configuração
    application.add_handler(file_id_conv_handler)

    # 2. Criação de Personagem (Start/Nome)
    register_character_handlers(application)
    
    # 3. Sistemas de Jogo (Mercado, Evolução)
    register_market_handlers(application)
    register_evolution_handlers(application)

    # 4. Outros Handlers (Chat Global, etc)
    register_all_handlers(application)

    logging.info("Bot iniciado com sucesso.")

    MAX_RETRIES = 100
    RETRY_DELAY = 10 

    for attempt in range(MAX_RETRIES):
        try:
            application.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
            break 
        except Conflict:
            logging.warning(f"Conflito: Aguardando {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)
        except NetworkError:
            logging.warning("Erro de Rede. Reconectando em 5s...")
            time.sleep(5)
        except KeyboardInterrupt:
            logging.info("Bot paralisado pelo usuário.")
            break
        except Exception as e:
            logging.error(f"Erro fatal: {e}")
            time.sleep(5)