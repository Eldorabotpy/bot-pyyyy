# handlers/utils_timed.py
from datetime import datetime, timezone
from telegram.ext import ContextTypes

def schedule_or_replace_job(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    job_id: str,
    when,
    callback,
    data=None,
    chat_id=None,
    user_id=None,
):
    """
    Agenda um job com nome estável, removendo um anterior com mesmo nome.
    'when' pode ser segundos (float/int) ou datetime tz-aware.
    """
    # remove anteriores com o mesmo nome
    for j in context.job_queue.get_jobs_by_name(job_id):
        j.schedule_removal()

    # calcula delay
    if isinstance(when, datetime):
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        delay = max(0, (when - datetime.now(timezone.utc)).total_seconds())
    else:
        delay = max(0, float(when))

    context.job_queue.run_once(
        callback=callback,
        when=delay,
        chat_id=chat_id,
        user_id=user_id,
        data=data or {},
        name=job_id,  # <- NOME ESTÁVEL
    )
