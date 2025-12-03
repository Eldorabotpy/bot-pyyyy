# Arquivo: main.py (VERSÃO FINAL - BLINDADA CONTRA ERRO DE IMAGEM)

from __future__ import annotations
import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logging
from dotenv import load_dotenv
load_dotenv()
from datetime import time, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from threading import Thread
from flask import Flask

from telegram import Update
from telegram.ext import Application, ContextTypes
from telegram.error import BadRequest, Forbidden # Import para tratamento de erro

from config import ADMIN_ID, TELEGRAM_TOKEN, EVENT_TIMES, JOB_TIMEZONE, WORLD_BOSS_TIMES, STARTUP_IMAGE_ID
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

# 1. Refino e Desmanche
from handlers.refining_handler import finish_refine_job, finish_dismantle_job

# 2. Forja
from handlers.forge_handler import finish_craft_notification_job

# 3. Coleta
from handlers.job_handler import finish_collection_job 

# 4. Caça
try:
    from handlers.hunt_handler import finish_auto_hunt_job
except ImportError:
    logging.warning("Job 'finish_auto_hunt_job' não encontrado em handlers.hunt_handler.")
    finish_auto_hunt_job = None

# 5. Viagem
try:
    from handlers.menu_handler import finish_travel_job
except ImportError:
    logging.warning("Job 'finish_travel_job' não encontrado em handlers.menu_handler.")
    finish_travel_job = None

# 6. World Boss
from handlers.world_boss.engine import (
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

# --- FLASK ---
flask_app = Flask(__name__)
@flask_app.route('/')
def health_check():
    return "Bot is alive and running!", 200
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port, use_reloader=False)

# --- HANDLERS DE ERRO E STARTUP ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.exception("Exceção ao processar update: %s", context.error)

async def check_stale_actions_on_startup(application: Application):
    """
    Recupera ações presas após reinício do servidor.
    """
    if player_core.players_collection is None: return

    logging.info("[Watchdog] Verificando ações interrompidas pelo reinício...")
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

            if action == "refining":
                application.job_queue.run_once(
                    finish_refine_job, when=delay, user_id=user_id, chat_id=chat_id,
                    data={"rid": details.get("recipe_id")}, name=name_job
                )
            
            elif action == "dismantling":
                application.job_queue.run_once(
                    finish_dismantle_job, when=delay, user_id=user_id, chat_id=chat_id,
                    data=details, name=name_job
                )
                
            elif action == "crafting":
                application.job_queue.run_once(
                    finish_craft_notification_job, when=delay, user_id=user_id, chat_id=chat_id,
                    data={"recipe_id": details.get("recipe_id")}, name=name_job
                )

            elif action == "collecting":
                 job_data = {
                    'resource_id': details.get("resource_id"),
                    'item_id_yielded': details.get("item_id_yielded"),
                    'energy_cost': details.get("energy_cost", 1),
                    'speed_mult': details.get("speed_mult", 1.0)
                }
                 application.job_queue.run_once(
                    finish_collection_job, when=delay, user_id=user_id, chat_id=chat_id,
                    data=job_data, name=name_job
                )
            
            elif action == "auto_hunting" and finish_auto_hunt_job:
                job_data = {
                    "user_id": user_id, "chat_id": chat_id,
                    "message_id": state.get("message_id"),
                    "hunt_count": details.get('hunt_count'),
                    "region_key": details.get('region_key')
                }
                application.job_queue.run_once(
                    finish_auto_hunt_job, when=delay, data=job_data, name=name_job
                )

            elif action == "travel" and finish_travel_job:
                application.job_queue.run_once(
                    finish_travel_job, when=delay, user_id=user_id, chat_id=chat_id,
                    data={"dest": details.get("destination")}, name=name_job
                )
                
    except Exception as e:
        logging.error(f"[Watchdog] Erro: {e}")

async def broadcast_startup_message(application: Application):
    """
    Envia broadcast para TODOS os jogadores.
    Se não tiver 'last_chat_id', tenta usar o próprio '_id' (User ID).
    """
    if player_core.players_collection is None: return

    logging.info("[Broadcast] Iniciando envio de mensagem global...")
    
    mensagem = (
        "📢 <b>Mundo de Eldora Atualizado!</b>\n\n"
        "O sistema foi reiniciado para melhorias.\n"
        "✅ Suas ações em andamento (refino, craft) foram preservadas ou finalizadas.\n"
        "⚡ Energia e recursos sincronizados.\n\n"
        "<i>Bom jogo, aventureiro!</i>"
    )

    tem_imagem = STARTUP_IMAGE_ID is not None and isinstance(STARTUP_IMAGE_ID, str)

    try:
        # MUDANÇA: Removemos o filtro. Pegamos TODOS os jogadores.
        # Projetamos apenas os campos necessários para economizar memória.
        cursor = player_core.players_collection.find({}, {"_id": 1, "last_chat_id": 1})
        
        count = 0
        success_count = 0
        
        for doc in cursor: 
            # Tenta pegar o chat_id salvo. Se não tiver, usa o _id (User ID)
            chat_id = doc.get("last_chat_id") or doc.get("_id")
            
            if not chat_id: continue # Se mesmo assim não tiver ID, pula
            
            count += 1
            enviado = False
            
            # 1. Tenta com IMAGEM
            if tem_imagem:
                try:
                    await application.bot.send_photo(
                        chat_id=chat_id,
                        photo=STARTUP_IMAGE_ID, 
                        caption=mensagem,       
                        parse_mode="HTML"
                    )
                    enviado = True
                except Exception as e:
                    err_msg = str(e).lower()
                    if "wrong file identifier" in err_msg or "invalid file_id" in err_msg:
                        logging.warning(f"[Broadcast] ID de imagem inválido! Mudando para modo texto.")
                        tem_imagem = False
                    elif "forbidden" in err_msg or "chat not found" in err_msg:
                        pass 
                    else:
                        pass # Erro genérico de foto, tenta texto

            # 2. Tenta com TEXTO (se foto falhou ou desativada)
            if not enviado:
                try:
                    await application.bot.send_message(
                        chat_id=chat_id,
                        text=mensagem,
                        parse_mode="HTML"
                    )
                    enviado = True
                except Exception as e:
                    pass # Ignora erros silenciosamente para não sujar o log

            if enviado:
                success_count += 1
                await asyncio.sleep(0.5) 

        logging.info(f"[Broadcast] Finalizado. Enviado para {success_count} de {count} jogadores encontrados.")

    except Exception as e:
        logging.error(f"[Broadcast] Erro crítico no loop: {e}")

async def post_init_tasks(application: Application):
    if ADMIN_ID:
        try:
            await application.bot.send_message(chat_id=ADMIN_ID, text="🤖 <b>Bot Reiniciado com Sucesso!</b>", parse_mode="HTML")
        except: pass
    
    await check_stale_actions_on_startup(application)
    # Roda o broadcast em background
    asyncio.create_task(broadcast_startup_message(application))

def register_jobs(application: Application):
    j = application.job_queue
    try: local_tz = ZoneInfo(JOB_TIMEZONE)
    except: local_tz = timezone.utc

    j.run_repeating(regenerate_energy_job, interval=60, first=10, name="regenerate_energy")
    j.run_repeating(timed_actions_watchdog, interval=60, first=20, name="watchdog_acoes")
    
    j.run_daily(daily_crystal_grant_job, time=time(0,0,tzinfo=local_tz), name="daily_crystals")
    j.run_daily(daily_arena_ticket_job, time=time(2,0,tzinfo=local_tz), name="daily_arena_tickets")
    j.run_daily(afternoon_event_reminder_job, time=time(13,30,tzinfo=local_tz), name="reminder")

    if EVENT_TIMES:
        for i, (sh, sm, eh, em) in enumerate(EVENT_TIMES):
            j.run_daily(start_kingdom_defense_event, time=time(sh,sm,tzinfo=local_tz), name=f"start_def_{i}", data={"event_duration_minutes": 30})
            j.run_daily(end_kingdom_defense_event, time=time(eh,em,tzinfo=local_tz), name=f"end_def_{i}")

    if WORLD_BOSS_TIMES:
        for i, (sh, sm, eh, em) in enumerate(WORLD_BOSS_TIMES):
            j.run_daily(iniciar_world_boss_job, time=time(sh,sm,tzinfo=local_tz), name=f"start_boss_{i}", data={"duration_hours": 1})
            j.run_daily(end_world_boss_job, time=time(eh,em,tzinfo=local_tz), name=f"end_boss_{i}")

def main():
    Thread(target=run_flask, daemon=True).start()
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_error_handler(error_handler)
    
    register_all_handlers(application)
    register_jobs(application)
    
    application.post_init = post_init_tasks
    application.run_polling()

if __name__ == "__main__":
    main()