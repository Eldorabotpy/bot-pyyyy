# registries/startup.py
import logging
import asyncio
from datetime import time as dt_time
from zoneinfo import ZoneInfo
from telegram.ext import Application

# Config Imports
from config import ADMIN_ID, STARTUP_IMAGE_ID, JOB_TIMEZONE, EVENT_TIMES, WORLD_BOSS_TIMES

# Jobs e Watchdogs Imports
from handlers.jobs import (
    daily_crystal_grant_job,
    daily_arena_ticket_job,      # Adicionado
    daily_kingdom_ticket_job,    # Adicionado
    daily_pvp_entry_reset_job,   # Adicionado/Garantido
    regenerate_energy_job,       # Adicionado (CRÍTICO para energia)
    start_kingdom_defense_event,
    start_world_boss_job,
    end_world_boss_job,
    check_premium_expiry_job,
    job_pvp_monthly_reset
)

logger = logging.getLogger(__name__)

async def run_system_startup_tasks(application: Application):
    """
    Centraliza TODAS as tarefas que rodam ao ligar o bot:
    - Watchdogs (Destravar jogadores)
    - Mensagem de Startup
    - Agendamento de Jobs
    """
    
    # 1. WATCHDOGS (Essencial para destravar Auto Hunt)
    logger.info("🐶 Iniciando Watchdogs...")
    try:
        from modules.player.actions import check_stale_actions_on_startup
        await check_stale_actions_on_startup(application)
    except ImportError:
        logger.error("Falha ao importar check_stale_actions_on_startup")
    except Exception as e:
        logger.error(f"Erro no Watchdog de Ações: {e}")

    try:
        from modules.recovery_manager import recover_active_hunts
        asyncio.create_task(recover_active_hunts(application))
    except ImportError: pass

    # 2. MENSAGEM DE BOAS-VINDAS AO ADMIN
    if ADMIN_ID:
        try: 
            msg_text = "🤖 <b>Sistema Online!</b>\n🛡️ <i>Barreira de Grupos: ATIVADA</i>\n🐶 <i>Watchdog: ATIVO</i>\n📅 <i>Scheduler: SINCRONIZADO</i>"
            target_chat_id = int(ADMIN_ID) if str(ADMIN_ID).isdigit() else ADMIN_ID
            
            if STARTUP_IMAGE_ID:
                await application.bot.send_photo(chat_id=target_chat_id, photo=STARTUP_IMAGE_ID, caption=msg_text, parse_mode="HTML")
            else:
                await application.bot.send_message(chat_id=target_chat_id, text=msg_text, parse_mode="HTML")
        except Exception as e: 
            logger.error(f"Falha ao enviar msg de startup: {e}")

    # 3. AGENDAMENTO DE JOBS (Scheduler)
    setup_scheduler(application)

def setup_scheduler(application: Application):
    """Configura todos os Jobs repetitivos"""
    jq = application.job_queue 
    try:
        # Garante fuso horário BR
        tz = ZoneInfo(JOB_TIMEZONE)
    except Exception:
        from datetime import timezone
        tz = timezone.utc
        logger.warning("⚠️ Timezone inválida no config. Usando UTC.")

    logger.info(f"📅 Configurando Jobs no fuso: {tz}")

    # ==========================================================================
    # 1. WATCHDOGS CONTÍNUOS (Rodam a cada X segundos)
    # ==========================================================================
    
    # Premium Checker (Rigoroso: 60s)
    # Verifica a cada minuto se o plano venceu para cortar imediatamente
    jq.run_repeating(check_premium_expiry_job, interval=60, first=10, name="premium_watchdog")

    # Regeneração de Energia (60s)
    # Verifica a cada minuto quem precisa ganhar +1 de energia
    jq.run_repeating(regenerate_energy_job, interval=60, first=5, name="energy_regen")

    # ==========================================================================
    # 2. JOBS DIÁRIOS (Sincronizados com Meia-Noite)
    # ==========================================================================
    midnight = dt_time(hour=0, minute=0, tzinfo=tz)

    # Cristais Diários
    jq.run_daily(daily_crystal_grant_job, time=midnight, name="daily_crystal")
    
    # Tickets de Arena (Item)
    jq.run_daily(daily_arena_ticket_job, time=midnight, name="daily_arena_ticket")
    
    # Tickets de Defesa do Reino
    jq.run_daily(daily_kingdom_ticket_job, time=midnight, name="daily_kingdom_ticket")
    
    # Reset de Entradas PvP (Define 5/5)
    jq.run_daily(daily_pvp_entry_reset_job, time=midnight, name="daily_pvp_entry_reset")

    # ==========================================================================
    # 3. JOBS MENSAIS / ESPECÍFICOS
    # ==========================================================================
    
    # Reset Mensal PvP (Roda todo dia, mas a função checa se é dia 1)
    jq.run_daily(job_pvp_monthly_reset, time=dt_time(hour=0, minute=5, tzinfo=tz), name="pvp_monthly_check")

    # ==========================================================================
    # 4. EVENTOS AGENDADOS (Config)
    # ==========================================================================
    
    # Defesa do Reino (Kingdom Defense)
    if EVENT_TIMES:
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
            except: pass

    # World Boss
    if WORLD_BOSS_TIMES:
        for i, (sh, sm, eh, em) in enumerate(WORLD_BOSS_TIMES):
            try:
                jq.run_daily(start_world_boss_job, time=dt_time(hour=sh, minute=sm, tzinfo=tz), name=f"start_boss_{i}")
                jq.run_daily(end_world_boss_job, time=dt_time(hour=eh, minute=em, tzinfo=tz), name=f"end_boss_{i}")
            except: pass
            
    logger.info(f"✅ [SCHEDULER] Todos os jobs agendados em {JOB_TIMEZONE}.")