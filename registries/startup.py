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
    daily_reset_event_entries_job,
    regenerate_energy_job,
    start_kingdom_defense_event,
    end_kingdom_defense_event,
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
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Erro ao iniciar recover_active_hunts: {e}")

    # 2. MENSAGEM DE BOAS-VINDAS AO ADMIN
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

    # 3. AGENDAMENTO DE JOBS (Scheduler)
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

    # ✅ OPCIONAL: reseta entradas do sistema de claim (se existir no projeto)
    # Evita crash quando a função não existe/ não foi implementada.
    try:
        # Ajuste este import se o job estiver em outro local:
        from handlers.jobs import daily_reset_event_entries_job  # type: ignore
        jq.run_daily(daily_reset_event_entries_job, time=midnight, name="daily_reset_event_entries")
        logger.info("✅ [SCHEDULER] Job daily_reset_event_entries agendado.")
    except ImportError:
        logger.warning("⚠️ [SCHEDULER] daily_reset_event_entries_job não encontrado (import). Job ignorado.")
    except NameError:
        logger.warning("⚠️ [SCHEDULER] daily_reset_event_entries_job não definido. Job ignorado.")
    except Exception as e:
        logger.warning(f"⚠️ [SCHEDULER] Falha ao agendar daily_reset_event_entries_job: {e}")

    # PvP mensal (mantido)
    jq.run_daily(job_pvp_monthly_reset, time=dt_time(hour=0, minute=5, tzinfo=tz), name="pvp_monthly_check")

    # ✅ GUERRA DE CLÃS: tick + jobs específicos (não derruba caso engine falhe)

    try:
        from modules import clan_war_engine
        clan_war_engine.register_war_jobs(application)
        logger.info("✅ [SCHEDULER] Jobs de Guerra de Clãs registrados.")
    except Exception as e:
        logger.warning(f"⚠️ [SCHEDULER] Falha ao registrar jobs da Guerra de Clãs: {e}")


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
            except Exception as e:
                logger.warning(f"⚠️ Falha ao agendar kingdom_defense_{i}: {e}")

    # World Boss
    if WORLD_BOSS_TIMES:
        for i, (sh, sm, eh, em) in enumerate(WORLD_BOSS_TIMES):
            try:
                jq.run_daily(start_world_boss_job, time=dt_time(hour=sh, minute=sm, tzinfo=tz), name=f"start_boss_{i}")
                jq.run_daily(end_world_boss_job, time=dt_time(hour=eh, minute=em, tzinfo=tz), name=f"end_boss_{i}")
            except Exception as e:
                logger.warning(f"⚠️ Falha ao agendar WorldBoss {i}: {e}")

    logger.info(f"✅ [SCHEDULER] Todos os jobs agendados em {JOB_TIMEZONE}.")
