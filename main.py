# main.py
# (VERSÃO FINAL - COM NOTIFICAÇÃO DE ERRO PRO ADMIN E BLINDAGEM DE STARTUP)

from __future__ import annotations
import asyncio
import os
import sys
import traceback
import html
import json
import logging
from threading import Thread
from datetime import time, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# Adiciona diretório raiz ao path (ajuda em alguns ambientes de hospedagem)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, ContextTypes
from telegram.error import BadRequest, Forbidden

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

# Jobs Específicos (Refino, Craft, Coleta)
from handlers.refining_handler import finish_refine_job, finish_dismantle_job
from handlers.forge_handler import finish_craft_notification_job
from handlers.job_handler import finish_collection_job 

# Jobs Opcionais (Try/Except para evitar crash se arquivo faltar)
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

# World Boss
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
# Silencia logs excessivos de bibliotecas externas
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# --- FLASK (Health Check para Render/Heroku) ---
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "Mundo de Eldora is ALIVE!", 200

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port, use_reloader=False)

# ==============================================================================
# 1. HANDLER DE ERRO GLOBAL (Envia para o Admin)
# ==============================================================================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia o erro formatado para o Admin no privado e loga no console."""
    
    # 1. Loga no terminal
    logger.error("🚨 Exceção não tratada:", exc_info=context.error)

    # 2. Se não tiver ADMIN_ID configurado, para por aqui
    if not ADMIN_ID:
        return

    # 3. Formata o Traceback
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    
    # Pega apenas as últimas 15 linhas para não poluir o chat
    tb_short = "".join(tb_list[-15:])

    message = (
        f"🚨 <b>ERRO CRÍTICO NO MUNDO DE ELDORA</b> 🚨\n\n"
        f"<b>Erro:</b> <code>{html.escape(str(context.error))}</code>\n\n"
        f"<b>Local (Traceback):</b>\n<pre>{html.escape(tb_short)}</pre>"
    )

    # 4. Envia para o Admin
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID, 
            text=message, 
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Falha ao enviar alerta de erro para o admin: {e}")

# ==============================================================================
# 2. WATCHDOG DE INICIALIZAÇÃO (Recupera Ações)
# ==============================================================================
async def check_stale_actions_on_startup(application: Application):
    """
    Recupera ações presas após reinício do servidor (Refino, Craft, Coleta, etc).
    """
    if player_core.players_collection is None: return

    logging.info("[Watchdog] 🔍 Verificando ações interrompidas pelo reinício...")
    now = utcnow()
    
    actions_to_check = ["crafting", "refining", "dismantling", "collecting"]
    
    if finish_auto_hunt_job: actions_to_check.append("auto_hunting")
    if finish_travel_job: actions_to_check.append("travel")

    query = {"player_state.action": {"$in": actions_to_check}}

    try:
        cursor = player_core.players_collection.find(query)
        restored_count = 0
        
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

            # Se já passou do tempo, executa em 1 segundo. Se não, agenda pro futuro.
            delay = 1 if now >= end_time else (end_time - now).total_seconds()
            name_job = f"fix_{action}_{user_id}"

            # Só agenda se já não existir um job com esse nome (evita duplicação)
            current_jobs = application.job_queue.get_jobs_by_name(name_job)
            if current_jobs:
                continue

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
            
            restored_count += 1
        
        if restored_count > 0:
            logging.info(f"[Watchdog] ✅ {restored_count} ações restauradas.")
                
    except Exception as e:
        logging.error(f"[Watchdog] Erro ao restaurar ações: {e}")

# ==============================================================================
# 3. BROADCAST DE INICIALIZAÇÃO
# ==============================================================================
async def broadcast_startup_message(application: Application):
    """
    Envia mensagem de inicialização para o GRUPO OFICIAL.
    """
    # --- CONFIGURAÇÃO DO GRUPO ---
    GRUPO_ID = -1002881364171 
    TOPIC_ID = 21 # ID do Tópico (se for grupo normal, use None)
    # -----------------------------

    logging.info(f"[Broadcast] Tentando enviar notificação de startup...")

    mensagem = (
        "📢 <b>Mundo de Eldora Atualizado!</b>\n\n"
        "O sistema foi reiniciado para aplicar melhorias e correções.\n"
        "✅ Suas ações em andamento foram preservadas.\n"
        "⚡ Energia e recursos sincronizados.\n\n"
        "<i>Divirtam-se!</i>"
    )

    # Verifica se a constante STARTUP_IMAGE_ID é válida
    tem_imagem = bool(STARTUP_IMAGE_ID and isinstance(STARTUP_IMAGE_ID, str) and len(STARTUP_IMAGE_ID) > 5)

    try:
        enviado = False

        # 1. Tenta enviar com IMAGEM
        if tem_imagem:
            try:
                await application.bot.send_photo(
                    chat_id=GRUPO_ID,
                    message_thread_id=TOPIC_ID, 
                    photo=STARTUP_IMAGE_ID,
                    caption=mensagem,
                    parse_mode="HTML"
                )
                enviado = True
                logging.info("[Broadcast] Foto enviada com sucesso.")
            except Exception as e:
                logging.warning(f"[Broadcast] Falha ao enviar foto (ID pode estar inválido): {e}")
                # Falhou a foto, o código continua para tentar enviar texto

        # 2. Tenta enviar apenas TEXTO (Fallback)
        if not enviado:
            await application.bot.send_message(
                chat_id=GRUPO_ID,
                message_thread_id=TOPIC_ID,
                text=mensagem,
                parse_mode="HTML"
            )
            logging.info("[Broadcast] Texto (fallback) enviado com sucesso.")

    except Exception as e:
        # Se der erro aqui, é provável que o bot não esteja no grupo ou ID esteja errado
        logging.error(f"[Broadcast] Não foi possível enviar no grupo: {e}")

async def post_init_tasks(application: Application):
    """Tarefas executadas assim que o bot conecta."""
    
    # Avisa o Admin no privado
    if ADMIN_ID:
        try:
            await application.bot.send_message(chat_id=ADMIN_ID, text="🤖 <b>Sistema Online e Operante!</b>", parse_mode="HTML")
        except Exception: 
            logging.warning("Não foi possível enviar msg de startup para o Admin (bloqueado?)")
    
    # Recupera ações do banco
    await check_stale_actions_on_startup(application)
    
    # Envia no grupo (em background para não travar o boot)
    asyncio.create_task(broadcast_startup_message(application))

# ==============================================================================
# 4. REGISTRO DE JOBS
# ==============================================================================
def register_jobs(application: Application):
    j = application.job_queue
    try: 
        local_tz = ZoneInfo(JOB_TIMEZONE)
    except: 
        logging.warning(f"Timezone {JOB_TIMEZONE} inválida, usando UTC.")
        local_tz = timezone.utc

    # Jobs recorrentes
    j.run_repeating(regenerate_energy_job, interval=60, first=10, name="regenerate_energy")
    j.run_repeating(timed_actions_watchdog, interval=60, first=20, name="watchdog_acoes")
    
    # Jobs Diários
    j.run_daily(daily_crystal_grant_job, time=time(0,0,tzinfo=local_tz), name="daily_crystals")
    j.run_daily(daily_arena_ticket_job, time=time(2,0,tzinfo=local_tz), name="daily_arena_tickets")
    j.run_daily(afternoon_event_reminder_job, time=time(13,30,tzinfo=local_tz), name="reminder")

    # Eventos Dinâmicos (Defesa do Reino)
    if EVENT_TIMES:
        for i, (sh, sm, eh, em) in enumerate(EVENT_TIMES):
            j.run_daily(start_kingdom_defense_event, time=time(sh,sm,tzinfo=local_tz), name=f"start_def_{i}", data={"event_duration_minutes": 30})
            j.run_daily(end_kingdom_defense_event, time=time(eh,em,tzinfo=local_tz), name=f"end_def_{i}")

    # World Boss
    if WORLD_BOSS_TIMES:
        for i, (sh, sm, eh, em) in enumerate(WORLD_BOSS_TIMES):
            j.run_daily(iniciar_world_boss_job, time=time(sh,sm,tzinfo=local_tz), name=f"start_boss_{i}", data={"duration_hours": 1})
            j.run_daily(end_world_boss_job, time=time(eh,em,tzinfo=local_tz), name=f"end_boss_{i}")

# ==============================================================================
# 5. EXECUÇÃO PRINCIPAL
# ==============================================================================
def main():
    # Inicia Flask em Thread separada (para manter o bot vivo)
    Thread(target=run_flask, daemon=True).start()
    
    # Configura o Bot
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Adiciona o Tratamento de Erro Global
    application.add_error_handler(error_handler)
    
    # Registra Comandos e Callbacks
    register_all_handlers(application)
    
    # Registra Jobs (Cron)
    register_jobs(application)
    
    # Tarefas de pós-inicialização (msg startup, recuperação)
    application.post_init = post_init_tasks
    
    logging.info("🤖 Iniciando Polling do Telegram...")
    application.run_polling()

if __name__ == "__main__":
    # BLINDAGEM DE STARTUP
    # Se houver erro de importação (game_data, config, etc), pegamos aqui
    try:
        main()
    except Exception as e:
        print("\n" + "="*50)
        print("❌ ERRO FATAL NA INICIALIZAÇÃO DO BOT!")
        print(f"O bot falhou antes de conectar ao Telegram.")
        print(f"ERRO: {e}")
        traceback.print_exc()
        print("="*50 + "\n")