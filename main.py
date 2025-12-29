# main.py
# (VERSÃO CORRIGIDA PARA SISTEMA DE LOGIN/MIGRAÇÃO)

from __future__ import annotations
import asyncio
import os
import sys
import logging
from threading import Thread
from datetime import time as dt_time, timezone
from zoneinfo import ZoneInfo

# Telegram Imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler, CallbackQueryHandler

# Configuração de Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from flask import Flask

# --- CONFIGURAÇÕES ---
from config import (
    ADMIN_ID, 
    TELEGRAM_TOKEN, 
    EVENT_TIMES, 
    JOB_TIMEZONE, 
    WORLD_BOSS_TIMES, 
    STARTUP_IMAGE_ID
)

# --- NOVOS IMPORTS (SISTEMA DE AUTH) ---
from handlers.auth_handler import auth_handler, logout_command, logout_callback
from handlers.start_handler import start_command_handler

# --- IMPORTS DOS REGISTROS (LEGADO) ---
from registries import register_all_handlers
from registries.class_evolution import register_evolution_handlers
from registries.market import register_market_handlers

# [REMOVIDO] register_character_handlers causaria conflito com o auth_handler
# from registries.character import register_character_handlers 

# --- IMPORTAÇÃO DO GERENCIADOR DE ARQUIVOS (ADMIN) ---
from handlers.admin.file_id_conv import file_id_conv_handler

# --- JOBS ---
from handlers.jobs import (
    daily_crystal_grant_job,
    start_kingdom_defense_event,
    start_world_boss_job,
    end_world_boss_job,
    job_pvp_monthly_reset
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
# SERVIDOR WEB (KEEP ALIVE - RENDER)
# ==============================================================================
app = Flask('')

@app.route('/')
def home():
    return "I'm alive! Eldora Bot is running."

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
            msg_text = "🤖 <b>Sistema Online com Auth Híbrida!</b>"
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

    # (Jobs mantidos do seu código original)
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
# FUNÇÕES DE GRUPO E BOAS-VINDAS
# ==============================================================================
# No main.py, substitua a função welcome_new_member antiga por esta:

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Boas-vindas com IMAGEM, MARCAÇÃO e BOTÃO DE AÇÃO.
    """
    if not update.message.new_chat_members:
        return

    # --- CONFIGURAÇÃO DA IMAGEM ---
    
    IMG_BOAS_VINDAS = STARTUP_IMAGE_ID if STARTUP_IMAGE_ID else "AgACAgEAAxkBAAEEbP5pUVfo8d4oSZTe1twEpMxGv-elcgACpwtrG71CiUbxmRRM9xLX1wEAAwIAA3kAAzYE" 

    for member in update.message.new_chat_members:
        # Ignora se for o próprio bot
        if member.id == context.bot.id:
            continue
            
        # O PULO DO GATO: Deep Link para criar conta direto
        bot_username = context.bot.username
        deep_link = f"https://t.me/{bot_username}?start=criar_conta"
        
        # Botão Chamativo
        keyboard = [
            [InlineKeyboardButton("⚔️ CRIAR PERSONAGEM AGORA ⚔️", url=deep_link)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Texto Épico com Marcação
        # member.mention_html() é o que faz o nome ficar azul e clicável (Marca a pessoa)
        caption_text = (
            f"🔔 <b>UM NOVO AVENTUREIRO CHEGOU!</b>\n\n"
            f"Seja bem-vindo(a), {member.mention_html()}!\n"
            f"Os portões de <b>Eldora</b> se abrem para você.\n\n"
            "⛔ <i>Por segurança, sua jornada começa no privado.</i>\n"
            "👇 <b>Toque no botão abaixo para criar sua conta:</b>"
        )
        
        try:
            # Envia a FOTO com a legenda
            await update.message.reply_photo(
                photo=IMG_BOAS_VINDAS,
                caption=caption_text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception as e:
            # Fallback: Se der erro na imagem (link quebrado), manda só texto para não falhar
            logging.error(f"Erro ao enviar imagem de boas-vindas: {e}")
            await update.message.reply_text(
                f"Olá {member.mention_html()}! Clique abaixo para jogar:",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )

# ==============================================================================
# EXECUÇÃO PRINCIPAL
# ==============================================================================
if __name__ == '__main__':
    # Inicia o servidor Flask
    try:
        start_keep_alive()
        logging.info("Servidor Web iniciado.")
    except Exception as e:
        logging.warning(f"Erro no servidor Web: {e}")

    # Constrói a aplicação
    application = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init_tasks).build()
    
    # --- REGISTRO DE HANDLERS (ORDEM CRÍTICA) ---

    # 1. Detector de Entrada no Grupo (Prioridade Máxima para Boas-vindas)
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))

    # 2. SISTEMA DE AUTENTICAÇÃO (O Porteiro)
    # Deve vir antes de qualquer outro handler de comando para interceptar o /start
    application.add_handler(auth_handler)
    application.add_handler(CommandHandler("logout", logout_command))
    application.add_handler(CallbackQueryHandler(logout_callback, pattern='^logout_btn$'))

    # 3. Menu Principal (Novo Start Handler)
    # Só é acionado se o auth_handler liberar (usuário já logado)
    application.add_handler(start_command_handler)

    # 4. Admin / Ferramentas
    application.add_handler(file_id_conv_handler)
    
    # 5. Sistemas de Jogo (Mercado, Evolução, Registros Gerais)
    # IMPORTANTE: register_character_handlers foi REMOVIDO para não conflitar com o auth
    register_market_handlers(application)
    register_evolution_handlers(application)
    register_all_handlers(application)

    logging.info("Handlers registrados. Iniciando Polling...")

    # Loop principal
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)