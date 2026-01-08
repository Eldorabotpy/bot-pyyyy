# main.py
# (VERSÃO FINAL CORRIGIDA: Com Registro de Evolução)

from __future__ import annotations
import asyncio
import os
import sys
import logging
from threading import Thread

# Telegram Imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

# Configuração de Path (Garante que módulos sejam encontrados)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from flask import Flask

# --- CONFIGURAÇÕES ---
from config import (
    ADMIN_ID, 
    TELEGRAM_TOKEN, 
    STARTUP_IMAGE_ID
)

# --- IMPORTS DOS HANDLERS ESPECÍFICOS ---
# Autenticação (Login/Registro)
from handlers.auth_handler import auth_handler, logout_command, logout_callback
# Comando Start e Ferramentas Admin Básicas
from handlers.start_handler import start_command_handler
from handlers.admin.file_id_conv import file_id_conv_handler
from handlers.admin.media_handler import set_media_command

# --- IMPORTS DOS REGISTROS (A Mágica acontece aqui) ---
# Importamos a função MESTRA que carrega todos os sistemas do jogo
from registries import register_all_handlers
# Importamos as tarefas de inicialização (Jobs, Watchdogs)
from registries.startup import run_system_startup_tasks
from handlers.guide_handler import guide_handlers

# 👇 [NOVO] IMPORTA O REGISTRO DE EVOLUÇÃO AQUI 👇
from registries.class_evolution import register_evolution_handlers

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
# TAREFAS DE INICIALIZAÇÃO (POST-INIT)
# ==============================================================================
async def post_init_tasks(application: Application):
    """Executado assim que o bot conecta no Telegram"""
    
    # 1. Tratamento de Boss (Evita boss travado em restart)
    if world_boss_manager and world_boss_manager.is_active:
        logger.warning("Boss ativo detectado no reinício. Resetando status...")
        world_boss_manager.end_event(reason="Reinício do Sistema")
    
    # 2. Chama o gerenciador de Startup (Jobs, Watchdogs, Msgs)
    await run_system_startup_tasks(application)

# ==============================================================================
# 1. BOAS-VINDAS EM GRUPOS (Middleware)
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
# 2. A BARREIRA DE GRUPOS (Bloqueia comandos em grupos para não-admins)
# ==============================================================================
async def master_group_blocker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == ChatType.PRIVATE:
        return 

    # Se for grupo/supergrupo
    if update.effective_chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        # Permite apenas Admin Global usar comandos no grupo (para manutenção)
        if update.effective_user:
            tg_user_id_str = str(update.effective_user.id)
            admin_id_str = str(ADMIN_ID)
            
            if tg_user_id_str == admin_id_str:
                return 
        
        # Bloqueia o processamento para qualquer outro handler abaixo
        raise ApplicationHandlerStop

# ==============================================================================
# EXECUÇÃO PRINCIPAL
# ==============================================================================
if __name__ == '__main__':
    # Inicia Web Server
    try:
        start_keep_alive()
        logging.info("Web Server OK.")
    except Exception: pass

    # Configuração HTTPX (Evita Timeouts de Rede)
    request_config = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=60.0,
        read_timeout=60.0,
        write_timeout=60.0
    )

    # Constrói a Aplicação
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .request(request_config)
        .post_init(post_init_tasks)
        .build()
    )
    
    # ==========================================================================
    # 🚨 ORDEM DE HANDLERS (NÃO ALTERE A ORDEM) 🚨
    # ==========================================================================

    # GRUPO -1: MIDDLEWARES E BLOQUEIOS (Rodam antes de tudo)
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member), group=-1)
    application.add_handler(TypeHandler(Update, master_group_blocker), group=-1)

    # --------------------------------------------------------------------------
    # GRUPO 0: FLUXO PRINCIPAL
    # --------------------------------------------------------------------------
    
    # 1️⃣ LOGIN E AUTH (Prioridade Máxima)
    application.add_handler(auth_handler)

    # 2️⃣ FERRAMENTAS BÁSICAS E ADMIN
    application.add_handler(file_id_conv_handler)
    application.add_handler(CommandHandler("setmedia", set_media_command))
    
    # 3️⃣ SISTEMAS DO JOGO (Registries)
    # Carrega: Admin, Character, Combat, Crafting, Market, Regions, Guild, Events
    register_all_handlers(application)

    # 👇 [NOVO] ATIVA O SISTEMA DE EVOLUÇÃO AQUI 👇
    # Isso carrega o arquivo registries/class_evolution.py que contém o botão de duelo
    register_evolution_handlers(application)

    # 4️⃣ FALLBACKS (Comandos Gerais)
    application.add_handler(CommandHandler("logout", logout_command))
    application.add_handler(CallbackQueryHandler(logout_callback, pattern='^logout_btn$'))
    application.add_handler(start_command_handler)
    application.add_handlers(guide_handlers)
    # --------------------------------------------------------------------------
    # DEBUG (Opcional)
    try:
        from handlers.jobs import cmd_force_pvp_reset
        application.add_handler(CommandHandler("debug_reset", cmd_force_pvp_reset))
    except ImportError: pass

    logging.info("✅ Todos os Handlers Registrados na Ordem Correta.")
    logging.info("🚀 Iniciando Polling...")
    
    # Inicia o bot
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)