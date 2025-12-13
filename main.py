# main.py
# (VERSÃO FINAL - COM RETRY AUTOMÁTICO PARA O RENDER)

from __future__ import annotations
import asyncio
import os
import sys
import traceback
import html
import json
import logging
import time  # <--- IMPORTANTE PARA O RETRY
from threading import Thread
from datetime import time as dt_time, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# Adiciona diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from telegram import Update
from telegram.constants import ParseMode
from modules.recovery_manager import recover_active_hunts
from telegram.ext import Application, ContextTypes
from telegram.error import BadRequest, Forbidden, Conflict, NetworkError # <--- IMPORTS DE ERRO
from pvp.pvp_scheduler import job_pvp_monthly_reset, executar_reset_pvp
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
from handlers.jobs import (
    regenerate_energy_job,
    daily_crystal_grant_job,
    afternoon_event_reminder_job,
    timed_actions_watchdog,
    start_kingdom_defense_event,
    end_kingdom_defense_event,
    daily_arena_ticket_job
)

from handlers.refining_handler import finish_refine_job, finish_dismantle_job
from handlers.forge_handler import finish_craft_notification_job
from handlers.job_handler import finish_collection_job 

try:
    from handlers.hunt_handler import finish_auto_hunt_job
except ImportError:
    logging.warning("Job 'finish_auto_hunt_job' não encontrado.")
    finish_auto_hunt_job = None

try:
    from handlers.menu_handler import finish_travel_job
except ImportError:
    logging.warning("Job 'finish_travel_job' não encontrado.")
    finish_travel_job = None

# CORRETO (Novo endereço na pasta modules):
from modules.world_boss.engine import (
    iniciar_world_boss_job,
    end_world_boss_job
)

from modules.player import core as player_core
from modules.player.actions import _parse_iso, utcnow

# --- CONFIGURAÇÃO DE LOGGING ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# --- FLASK ---
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "Mundo de Eldora is ALIVE!", 200

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port, use_reloader=False)

# ==============================================================================
# 1. HANDLER DE ERRO
# ==============================================================================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Ignora erro de conflito aqui, pois trataremos no loop principal
    if isinstance(context.error, Conflict):
        logger.warning("⚠️ Conflito de instância detectado no error_handler (Ignorando pois será tratado no main).")
        return

    logger.error("🚨 Exceção não tratada:", exc_info=context.error)
    if not ADMIN_ID: return

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_short = "".join(tb_list[-15:])

    message = (
        f"🚨 <b>ERRO CRÍTICO NO MUNDO DE ELDORA</b> 🚨\n\n"
        f"<b>Erro:</b> <code>{html.escape(str(context.error))}</code>\n\n"
        f"<b>Local:</b>\n<pre>{html.escape(tb_short)}</pre>"
    )
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=message, parse_mode=ParseMode.HTML)
    except: pass

# ==============================================================================
# 2. WATCHDOG
# ==============================================================================
async def check_stale_actions_on_startup(application: Application):
    if player_core.players_collection is None: return
    logging.info("[Watchdog] 🔍 Verificando ações interrompidas...")
    now = utcnow()
    actions_to_check = ["crafting", "refining", "dismantling", "collecting"]
    if finish_auto_hunt_job: actions_to_check.append("auto_hunting")
    if finish_travel_job: actions_to_check.append("travel")

    query = {"player_state.action": {"$in": actions_to_check}}
    try:
        cursor = player_core.players_collection.find(query)
        for pdata in cursor:
            user_id = pdata.get("_id")
            chat_id = pdata.get("last_chat_id")
            state = pdata.get("player_state", {})
            action = state.get("action")
            details = state.get("details") or {}
            finish_iso = state.get("finish_time")
            if not finish_iso: continue
            end_time = _parse_iso(finish_iso)
            if not end_time: continue
            
            delay = 1 if now >= end_time else (end_time - now).total_seconds()
            name_job = f"fix_{action}_{user_id}"
            
            if application.job_queue.get_jobs_by_name(name_job): continue

            if action == "refining":
                application.job_queue.run_once(finish_refine_job, when=delay, user_id=user_id, chat_id=chat_id, data={"rid": details.get("recipe_id")}, name=name_job)
            elif action == "dismantling":
                application.job_queue.run_once(finish_dismantle_job, when=delay, user_id=user_id, chat_id=chat_id, data=details, name=name_job)
            elif action == "crafting":
                application.job_queue.run_once(finish_craft_notification_job, when=delay, user_id=user_id, chat_id=chat_id, data={"recipe_id": details.get("recipe_id")}, name=name_job)
            elif action == "collecting":
                 job_data = {'resource_id': details.get("resource_id"), 'item_id_yielded': details.get("item_id_yielded"), 'energy_cost': details.get("energy_cost", 1), 'speed_mult': details.get("speed_mult", 1.0)}
                 application.job_queue.run_once(finish_collection_job, when=delay, user_id=user_id, chat_id=chat_id, data=job_data, name=name_job)
            elif action == "auto_hunting" and finish_auto_hunt_job:
                job_data = {"user_id": user_id, "chat_id": chat_id, "message_id": state.get("message_id"), "hunt_count": details.get('hunt_count'), "region_key": details.get('region_key')}
                application.job_queue.run_once(finish_auto_hunt_job, when=delay, data=job_data, name=name_job)
            elif action == "travel" and finish_travel_job:
                application.job_queue.run_once(finish_travel_job, when=delay, user_id=user_id, chat_id=chat_id, data={"dest": details.get("destination")}, name=name_job)
    except Exception as e:
        logging.error(f"[Watchdog] Erro: {e}")

# ==============================================================================
# 3. BROADCAST
# ==============================================================================
async def broadcast_startup_message(application: Application):
    GRUPO_ID = -1002881364171 
    TOPIC_ID = 21 
    logging.info(f"[Broadcast] Tentando enviar notificação...")
    mensagem = "📢 <b>Mundo de Eldora Atualizado!</b>\n\nSistema reiniciado.\n✅ Ações preservadas.\n⚡ Recursos sincronizados."
    tem_imagem = bool(STARTUP_IMAGE_ID and isinstance(STARTUP_IMAGE_ID, str) and len(STARTUP_IMAGE_ID) > 5)

    try:
        enviado = False
        if tem_imagem:
            try:
                await application.bot.send_photo(chat_id=GRUPO_ID, message_thread_id=TOPIC_ID, photo=STARTUP_IMAGE_ID, caption=mensagem, parse_mode="HTML")
                enviado = True
            except: pass
        if not enviado:
            await application.bot.send_message(chat_id=GRUPO_ID, message_thread_id=TOPIC_ID, text=mensagem, parse_mode="HTML")
    except Exception as e:
        logging.error(f"[Broadcast] Erro: {e}")

async def check_stale_actions_on_startup(application: Application):
    """
    1. Busca no MongoDB quem está 'preso' fazendo algo (ex: forjando).
    2. Calcula quanto tempo falta (ou se já acabou).
    3. Reagenda a entrega do item.
    """
    if player_core.players_collection is None: return

    logging.info("[Watchdog] 🔍 Iniciando varredura no Banco de Dados...")
    now = utcnow()
    
    # --- CONFIGURAÇÃO: O que vamos buscar? ---
    # Aqui definimos que queremos buscar quem está 'crafting' (forjando)
    query = {
        "player_state.action": "crafting"
    }

    try:
        # Busca no Mongo
        cursor = player_core.players_collection.find(query)
        count = 0
        
        for pdata in cursor:
            user_id = pdata.get("_id")
            chat_id = pdata.get("last_chat_id")
            
            # Pega os detalhes salvos
            state = pdata.get("player_state", {})
            details = state.get("details", {})
            finish_iso = state.get("finish_time")
            
            # Se não tem data de fim, algo está errado, ignora
            if not finish_iso: continue
            
            end_time = _parse_iso(finish_iso)
            if not end_time: continue

            # --- A LÓGICA DE TEMPO ---
            seconds_left = (end_time - now).total_seconds()
            
            # Se seconds_left for negativo (ex: -300), significa que acabou há 5 minutos.
            # Se for positivo (ex: 600), significa que faltam 10 minutos.
            
            # Definimos o 'delay' para rodar o job.
            # Se já acabou, delay = 1 segundo (executa "agora").
            delay = max(1, seconds_left)
            
            job_name = f"fix_craft_{user_id}"
            
            # Se o job já estiver na memória (raro no boot), pula
            if application.job_queue.get_jobs_by_name(job_name):
                continue

            # Agenda a finalização!
            application.job_queue.run_once(
                finish_craft_notification_job, 
                when=delay, 
                user_id=user_id, 
                chat_id=chat_id,
                data={"recipe_id": details.get("recipe_id")}, 
                name=job_name
            )
            
            status_msg = "Finalizando AGORA" if delay == 1 else f"Faltam {int(delay)}s"
            logging.info(f"[Watchdog] 🔨 Forja recuperada para User {user_id}. Status: {status_msg}")
            count += 1
            
        if count > 0:
            logging.info(f"[Watchdog] ✅ Total de {count} forjas recuperadas do banco de dados!")
        else:
            logging.info("[Watchdog] Nenhuma forja pendente encontrada no banco.")
                
    except Exception as e:
        logging.error(f"[Watchdog] ❌ Erro ao ler o banco de dados: {e}")
        
async def post_init_tasks(application: Application):
    if ADMIN_ID:
        try: 
            await application.bot.send_message(chat_id=ADMIN_ID, text="🤖 <b>Sistema Online!</b>", parse_mode="HTML")
        except: pass
    
    # Verificações antigas (Craft/Refine/Travel)
    await check_stale_actions_on_startup(application)
    
    # >>> ADICIONE ESTAS LINHAS AQUI (RECUPERAÇÃO DO AUTO HUNT) <<<
    logging.info("[Startup] Iniciando recuperação de caças ativas...")
    asyncio.create_task(recover_active_hunts(application))
    # -------------------------------------------------------------

    # Broadcast de reinício
    asyncio.create_task(broadcast_startup_message(application))

def register_jobs(application: Application):
    j = application.job_queue
    try: local_tz = ZoneInfo(JOB_TIMEZONE)
    except: local_tz = timezone.utc

    j.run_repeating(regenerate_energy_job, interval=60, first=10, name="regenerate_energy")
    j.run_repeating(timed_actions_watchdog, interval=60, first=20, name="watchdog_acoes")
    j.run_daily(daily_crystal_grant_job, time=dt_time(0,0,tzinfo=local_tz), name="daily_crystals")
    j.run_daily(daily_arena_ticket_job, time=dt_time(2,0,tzinfo=local_tz), name="daily_arena_tickets")
    j.run_daily(afternoon_event_reminder_job, time=dt_time(13,30,tzinfo=local_tz), name="reminder")
    j.run_daily(job_pvp_monthly_reset, time=dt_time(4, 0, tzinfo=local_tz), name="pvp_monthly_reset")
    
    if EVENT_TIMES:
        for i, (sh, sm, eh, em) in enumerate(EVENT_TIMES):
            j.run_daily(start_kingdom_defense_event, time=dt_time(sh,sm,tzinfo=local_tz), name=f"start_def_{i}", data={"event_duration_minutes": 30})
            j.run_daily(end_kingdom_defense_event, time=dt_time(eh,em,tzinfo=local_tz), name=f"end_def_{i}")
    if WORLD_BOSS_TIMES:
        for i, (sh, sm, eh, em) in enumerate(WORLD_BOSS_TIMES):
            j.run_daily(iniciar_world_boss_job, time=dt_time(sh,sm,tzinfo=local_tz), name=f"start_boss_{i}", data={"duration_hours": 1})
            j.run_daily(end_world_boss_job, time=dt_time(eh,em,tzinfo=local_tz), name=f"end_boss_{i}")
            
# ==============================================================================
# 5. EXECUÇÃO PRINCIPAL (COM RETRY LOGIC)
# ==============================================================================
def main():
    Thread(target=run_flask, daemon=True).start()
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_error_handler(error_handler)
    register_all_handlers(application)
    register_jobs(application)
    application.post_init = post_init_tasks
    
    logging.info("🤖 Bot configurado. Iniciando loop de conexão...")

    # --- LÓGICA DE RECONEXÃO ROBUSTA ---
    # Se der conflito (Render ainda não matou o bot antigo), a gente espera e tenta de novo.
    MAX_RETRIES = 5
    RETRY_DELAY = 10  # segundos

    for attempt in range(MAX_RETRIES):
        try:
            # drop_pending_updates=True ajuda a 'limpar a linha' e assumir o controle
            application.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
            
            # Se a função run_polling retornar (o que geralmente só acontece se der stop), saímos do loop
            break 
            
        except Conflict:
            logging.warning(f"⚠️ CONFLITO DETECTADO (Tentativa {attempt+1}/{MAX_RETRIES})")
            logging.warning(f"O Render ainda não finalizou o bot antigo. Aguardando {RETRY_DELAY} segundos...")
            time.sleep(RETRY_DELAY)
        
        except NetworkError:
            logging.warning("⚠️ Erro de Rede. Tentando reconectar em 5s...")
            time.sleep(5)
            
        except Exception as e:
            logging.error(f"❌ Erro fatal no Polling: {e}")
            raise e # Erros desconhecidos devem parar o bot

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"❌ ERRO FATAL NA INICIALIZAÇÃO: {e}")
        traceback.print_exc()