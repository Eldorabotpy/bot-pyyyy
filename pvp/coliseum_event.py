"""Agenda semanal do evento aberto do Coliseu."""
from datetime import datetime, time, timedelta, timezone


# Brasília permanece em UTC-3. Janela ajustável para o administrador.
BRASILIA = timezone(timedelta(hours=-3), name="BRT")
EVENT_WEEKDAYS = (1, 3, 5)  # terça, quinta e sábado
EVENT_START = time(20, 0)
EVENT_DURATION_MINUTES = 60
EVENT_DAY_NAMES = {
    1: "terça-feira",
    3: "quinta-feira",
    5: "sábado",
}


def get_event_status(now=None):
    """Devolve a janela ativa, ou o próximo horário, sempre em horário de Brasília."""
    current = now or datetime.now(BRASILIA)
    if current.tzinfo is None:
        current = current.replace(tzinfo=BRASILIA)
    else:
        current = current.astimezone(BRASILIA)

    next_start = None
    active_start = None
    active_end = None
    for offset in range(8):
        day = current.date() + timedelta(days=offset)
        if day.weekday() not in EVENT_WEEKDAYS:
            continue
        start = datetime.combine(day, EVENT_START, tzinfo=BRASILIA)
        end = start + timedelta(minutes=EVENT_DURATION_MINUTES)
        if start <= current < end:
            active_start, active_end = start, end
            break
        if start > current:
            next_start = start
            break

    scheduled_start = active_start or next_start
    return {
        "active": active_start is not None,
        "event_id": scheduled_start.date().isoformat() if scheduled_start else None,
        "starts_at": scheduled_start.isoformat() if scheduled_start else None,
        "ends_at": active_end.isoformat() if active_end else None,
        "next_starts_at": next_start.isoformat() if next_start else None,
        "timezone": "America/Sao_Paulo",
        "days": [EVENT_DAY_NAMES[day] for day in EVENT_WEEKDAYS],
        "duration_minutes": EVENT_DURATION_MINUTES,
    }


def get_ended_event_ids(now=None, lookback_days=42):
    """Datas de eventos cuja janela terminou, da mais recente para a mais antiga."""
    current = now or datetime.now(BRASILIA)
    if current.tzinfo is None:
        current = current.replace(tzinfo=BRASILIA)
    else:
        current = current.astimezone(BRASILIA)

    ended = []
    for offset in range(lookback_days):
        day = current.date() - timedelta(days=offset)
        if day.weekday() not in EVENT_WEEKDAYS:
            continue
        start = datetime.combine(day, EVENT_START, tzinfo=BRASILIA)
        end = start + timedelta(minutes=EVENT_DURATION_MINUTES)
        if end <= current:
            ended.append(day.isoformat())
    return ended
