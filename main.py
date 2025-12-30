# main.py
# (VERSÃO: BARREIRA TOTAL - Bloqueia Texto e Botões em Grupos)

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
from telegram.ext import (
    Application, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    CommandHandler, 
    CallbackQueryHandler,
    TypeHandler,          # <--- O SEGREDO: Para interceptar tudo
    ApplicationHandlerStop # <--- O FREIO: Para parar o processamento
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

from registries import register_all_handlers
from registries.class_evolution import register_evolution_handlers
from registries.market import register_market_handlers

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
    if world_boss_manager and world_boss_manager.is_active:
        logger.warning("Boss ativo detectado. Reiniciando status...")
        world_boss_manager.end_event(reason="Reinício")
    
    if ADMIN_ID:
        try: 
            msg_text = "🤖 <b>Sistema Online!</b>\n🛡️ <i>Barreira de Grupos: ATIVADA</i>"
            if STARTUP_IMAGE_ID:
                await application.bot.send_photo(chat_id=ADMIN_ID, photo=STARTUP_IMAGE_ID, caption=msg_text, parse_mode="HTML")
            else:
                await application.bot.send_message(chat_id=ADMIN_ID, text=msg_text, parse_mode="HTML")
        except Exception: pass
    
    # Recuperações e Watchdogs
    try:
        from modules.player.actions import check_stale_actions_on_startup
        await check_stale_actions_on_startup(application)
    except ImportError: pass
    
    try:
        from modules.recovery_manager import recover_active_hunts
        asyncio.create_task(recover_active_hunts(application))
    except ImportError: pass
    
    # Agendamento de Jobs
    jq = application.job_queue 
    try:
        tz = ZoneInfo(JOB_TIMEZONE)
    except Exception:
        tz = timezone.utc

    jq.run_daily(daily_crystal_grant_job, time=dt_time(hour=0, minute=0, tzinfo=tz), name="daily_crystal")
    jq.run_repeating(check_premium_expiry_job, interval=3600, first=60, name="premium_checker")
    
    if daily_pvp_entry_reset_job:
        jq.run_daily(daily_pvp_entry_reset_job, time=dt_time(hour=16, minute=27, tzinfo=tz), name="pvp_daily_entry_reset")

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
        jq.run_daily(job_pvp_monthly_reset, time=dt_time(hour=17, minute=15, tzinfo=tz), name="pvp_monthly_check")
    except ImportError: pass

    logging.info("Jobs e Sistemas iniciados.")

# ==============================================================================
# 1. BOAS-VINDAS (Permitido em Grupos)
# ==============================================================================
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.new_chat_members: return

    IMG_BOAS_VINDAS = STARTUP_IMAGE_ID if STARTUP_IMAGE_ID else "AgACAgEAAxkBAAEEbP5pUVfo8d4oSZTe1twEpMxGv-elcgACpwtrG71CiUbxmRRM9xLX1wEAAwIAA3kAAzYE"

    for member in update.message.new_chat_members:
        if member.id == context.bot.id: continue
        
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
    """
    Este middleware roda em TODAS as atualizações.
    Lógica:
    1. Se for Chat PRIVADO -> Deixa passar (return None).
    2. Se for GRUPO e for o ADMIN -> Deixa passar.
    3. Se for GRUPO e NÃO for Admin -> PARE (raise ApplicationHandlerStop).
    """
    if update.effective_chat.type == ChatType.PRIVATE:
        return # ✅ PRIVADO SEMPRE PASSA

    if update.effective_chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        # Permite apenas o Admin (Você) usar o bot no grupo para manutenção
        if update.effective_user and update.effective_user.id == ADMIN_ID:
            return # ✅ ADMIN NO GRUPO PASSA
        
        # ⛔ USUÁRIO COMUM NO GRUPO É BLOQUEADO
        raise ApplicationHandlerStop
# ==============================================================================
# EXECUÇÃO PRINCIPAL
# ==============================================================================
if __name__ == '__main__':
    try:
        start_keep_alive()
        logging.info("Web Server OK.")
    except Exception: pass

    application = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init_tasks).build()
    
    # --- ORDEM DE HANDLERS (CRÍTICA) ---

    # 1. Boas-vindas (Isso precisa rodar antes do bloqueio, pois é permitido em grupo)
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member), group=-1)

    application.add_handler(TypeHandler(Update, master_group_blocker), group=-1)

    # --------------------------------------------------------------------------
    # DAQUI PARA BAIXO, SÓ CHEGAM MENSAGENS PRIVADAS (OU DO ADMIN)
    # --------------------------------------------------------------------------

    # 3. Autenticação
    application.add_handler(auth_handler)
    application.add_handler(CommandHandler("logout", logout_command))
    application.add_handler(CallbackQueryHandler(logout_callback, pattern='^logout_btn$'))

    # 4. Menu Principal
    application.add_handler(start_command_handler)

    # 5. Admin / Ferramentas
    application.add_handler(file_id_conv_handler)
    
    # 6. Sistemas de Jogo
    register_market_handlers(application)
    register_evolution_handlers(application)
    register_all_handlers(application)

    # 7. Debug
    try:
        from handlers.jobs import cmd_force_pvp_reset
        application.add_handler(CommandHandler("debug_reset", cmd_force_pvp_reset))
    except ImportError: pass

    logging.info("Handlers registrados. Bot 100% BLINDADO contra spam de grupo.")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)