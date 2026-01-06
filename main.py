# main.py
# (VERSÃO CORRIGIDA: Chama register_admin_handlers corretamente)

from __future__ import annotations
import asyncio
import os
import sys
import logging
from threading import Thread
from datetime import time as dt_time, timezone
from zoneinfo import ZoneInfo
from registries.startup import run_system_startup_tasks
from handlers.admin.media_handler import set_media_command

# Telegram Imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
# Importação necessária para corrigir o erro de Timeout
from telegram.request import HTTPXRequest 
from telegram.ext import (
    Application, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    CommandHandler, 
    CallbackQueryHandler,
    TypeHandler,          
    ApplicationHandlerStop 
)
from telegram.constants import ChatType

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

# --- IMPORTS DOS HANDLERS ---
from handlers.auth_handler import auth_handler, logout_command, logout_callback
from handlers.start_handler import start_command_handler
from handlers.admin.file_id_conv import file_id_conv_handler

# --- IMPORTS DOS REGISTRIES (AQUI ESTÁ A CORREÇÃO) ---
from registries import register_all_handlers
from registries.class_evolution import register_evolution_handlers
from registries.market import register_market_handlers
# Importa o registro mestre de admins que você criou
from registries.admin import register_admin_handlers 

# --- IMPORTS DOS JOBS ---
from handlers.jobs import (
    daily_crystal_grant_job,
    start_kingdom_defense_event,
    start_world_boss_job,
    end_world_boss_job,
    job_pvp_monthly_reset,
    check_premium_expiry_job
)

try:
    from handlers.jobs import daily_pvp_entry_reset_job
except ImportError:
    daily_pvp_entry_reset_job = None

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
    # 1. Tratamento de Boss
    if world_boss_manager and world_boss_manager.is_active:
        logger.warning("Boss ativo detectado. Reiniciando status...")
        world_boss_manager.end_event(reason="Reinício")
    
    # 2. Inicialização do Sistema (Mensagens Admin, Agendamentos, Watchdogs)
    await run_system_startup_tasks(application)

# ==============================================================================
# 1. BOAS-VINDAS (Permitido em Grupos)
# ==============================================================================
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.new_chat_members: return

    IMG_BOAS_VINDAS = STARTUP_IMAGE_ID if STARTUP_IMAGE_ID else "AgACAgEAAxkBAAEEbP5pUVfo8d4oSZTe1twEpMxGv-elcgACpwtrG71CiUbxmRRM9xLX1wEAAwIAA3kAAzYE"

    for member in update.message.new_chat_members:
        if str(member.id) == str(context.bot.id): continue
        
        bot_username = context.bot.username
        deep_link = f"https://t.me/{bot_username}?start=criar_conta"
        
        keyboard = [[InlineKeyboardButton("⚔️ CRIAR PERSONAGEM ⚔️", url=deep_link)]]
        caption_text = (
            f"🔔 <b>UM NOVO AVENTUREIRO CHEGOU!</b>\n\n"
            f"Seja bem-vindo(a), {member.mention_html()}!\n"
            f"Os portões de <b>Eldora</b> se abrem para você.\n\n"
            "👇 <b>Comece sua jornada no botão abaixo:</b>"
        )
        
        try:
            await update.message.reply_photo(photo=IMG_BOAS_VINDAS, caption=caption_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        except:
            await update.message.reply_text(f"Bem-vindo {member.mention_html()}! Jogue aqui: @{bot_username}", parse_mode="HTML")

# ==============================================================================
# 2. A BARREIRA (TypeHandler)
# ==============================================================================
async def master_group_blocker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == ChatType.PRIVATE:
        return 

    if update.effective_chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        if update.effective_user:
            tg_user_id_str = str(update.effective_user.id)
            admin_id_str = str(ADMIN_ID)
            
            if tg_user_id_str == admin_id_str:
                return 
        
        raise ApplicationHandlerStop

# ==============================================================================
# EXECUÇÃO PRINCIPAL
# ==============================================================================
if __name__ == '__main__':
    try:
        start_keep_alive()
        logging.info("Web Server OK.")
    except Exception: pass

    # --- CORREÇÃO DE TIMEOUT ---
    request_config = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=60.0,
        read_timeout=60.0,
        write_timeout=60.0
    )

    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .request(request_config)
        .post_init(post_init_tasks)
        .build()
    )
    
    # ==========================================================================
    # ORDEM DE HANDLERS (CRÍTICA PARA FUNCIONAMENTO)
    # ==========================================================================

    # 1. BARREIRA GLOBAL (Group -1)
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member), group=-1)
    application.add_handler(TypeHandler(Update, master_group_blocker), group=-1)

    # --------------------------------------------------------------------------
    # 2. SISTEMAS PRIORITÁRIOS & CONVERSATIONS (Group 0 - Topo)
    # Devem vir ANTES do Auth para capturar inputs de menus abertos
    # --------------------------------------------------------------------------
    
    # Ferramentas Admin Básicas
    application.add_handler(file_id_conv_handler)
    application.add_handler(CommandHandler("setmedia", set_media_command))
    
    # >>> AQUI ESTÁ A CORREÇÃO PRINCIPAL <<<
    # Chama o seu arquivo registries/admin.py que gerencia premium, gemas e edit player
    register_admin_handlers(application)
    
    # Sistemas de Jogo (Mercado, Evolução)
    register_market_handlers(application)
    register_evolution_handlers(application)
    
    # Registro Geral (Outros sistemas do jogo)
    register_all_handlers(application)

    # --------------------------------------------------------------------------
    # 3. AUTENTICAÇÃO E MENU PRINCIPAL (Group 0 - Fundo)
    # Só capturam o que não foi pego pelos sistemas acima
    # --------------------------------------------------------------------------
    
    # Autenticação (Login)
    application.add_handler(auth_handler)
    
    # Logout e Start
    application.add_handler(CommandHandler("logout", logout_command))
    application.add_handler(CallbackQueryHandler(logout_callback, pattern='^logout_btn$'))
    application.add_handler(start_command_handler)

    # --------------------------------------------------------------------------
    # 4. DEBUG (Opcional)
    # --------------------------------------------------------------------------
    try:
        from handlers.jobs import cmd_force_pvp_reset
        application.add_handler(CommandHandler("debug_reset", cmd_force_pvp_reset))
    except ImportError: pass

    logging.info("Handlers registrados. Admin Registry ativado.")
    
    # Inicia o bot
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)