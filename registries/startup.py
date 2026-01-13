# registries/startup.py

import logging
import asyncio
from datetime import time as dt_time
from zoneinfo import ZoneInfo
from telegram.ext import Application

from config import ADMIN_ID, STARTUP_IMAGE_ID, JOB_TIMEZONE, EVENT_TIMES, WORLD_BOSS_TIMES

from handlers.jobs import (
    # NOVO: reset diário do sistema de claim
    daily_reset_event_entries_job,

    # Watchdogs e essenciais
    regenerate_energy_job,
    start_kingdom_defense_event,
    start_world_boss_job,
    end_world_boss_job,
    check_premium_expiry_job,
    job_pvp_monthly_reset,
)

logger = logging.getLogger(__name__)


async def run_system_startup_tasks(application: Application):
    """
    Centraliza tarefas ao ligar o bot:
    - Watchdogs (Destravar jogadores)
    - Mensagem de Startup
    - Agendamento de Jobs
    """
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
    except ImportError:
        pass

    if ADMIN_ID:
        try:
            msg_text = (
                "🤖 <b>Sistema Online!</b>\n"
                "🛡️ <i>Barreira de Grupos: ATIVADA</i>\n"
                "🐶 <i>Watchdog: ATIVO</i>\n"
                "📅 <i>Scheduler: SINCRONIZADO</i>"
            )
            target_chat_id = int(ADMIN_ID) if str(ADMIN_ID).isdigit() else ADMIN_ID

            if STARTUP_IMAGE_ID:
                await application.bot.send_photo(
                    chat_id=target_chat_id,
                    photo=STARTUP_IMAGE_ID,
                    caption=msg_text,
                    parse_mode="HTML"
                )
            else:
                await application.bot.send_message(
                    chat_id=target_chat_id,
                    text=msg_text,
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Falha ao enviar msg de startup: {e}")

    setup_scheduler(application)


def setup_scheduler(application: Application):
    jq = application.job_queue
    try:
        tz = ZoneInfo(JOB_TIMEZONE)
    except Exception:
        from datetime import timezone
        tz = timezone.utc
        logger.warning("⚠️ Timezone inválida no config. Usando UTC.")

    logger.info(f"📅 Configurando Jobs no fuso: {tz}")

    # Watchdogs contínuos
    jq.run_repeating(check_premium_expiry_job, interval=60, first=10, name="premium_watchdog")
    jq.run_repeating(regenerate_energy_job, interval=60, first=5, name="energy_regen")

    # Jobs diários (meia-noite)
    midnight = dt_time(hour=0, minute=0, tzinfo=tz)

    # ✅ NOVO: reseta as entradas do sistema de claim (impede acúmulo)
    jq.run_daily(daily_reset_event_entries_job, time=midnight, name="daily_reset_event_entries")

    # PvP mensal (mantido)
    jq.run_daily(job_pvp_monthly_reset, time=dt_time(hour=0, minute=5, tzinfo=tz), name="pvp_monthly_check")

    # Eventos agendados
    if EVENT_TIMES:
        for i, (sh, sm, eh, em) in enumerate(EVENT_TIMES):
            try:
                start_min = sh * 60 + sm
                end_min = eh * 60 + em
                duration = end_min - start_min
                if duration < 0:
                    duration += 1440

                jq.run_daily(
                    start_kingdom_defense_event,
                    time=dt_time(hour=sh, minute=sm, tzinfo=tz),
                    name=f"kingdom_defense_{i}",
                    data={"event_duration_minutes": duration}
                )
            except Exception:
                pass

    # World Boss
    if WORLD_BOSS_TIMES:
        for i, (sh, sm, eh, em) in enumerate(WORLD_BOSS_TIMES):
            try:
                jq.run_daily(start_world_boss_job, time=dt_time(hour=sh, minute=sm, tzinfo=tz), name=f"start_boss_{i}")
                jq.run_daily(end_world_boss_job, time=dt_time(hour=eh, minute=em, tzinfo=tz), name=f"end_boss_{i}")
            except Exception:
                pass

    logger.info(f"✅ [SCHEDULER] Todos os jobs agendados em {JOB_TIMEZONE}.")
