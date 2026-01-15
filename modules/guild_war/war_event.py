# modules/guild_war/war_event.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, time
from typing import Dict, Any, Optional
import asyncio

from modules.database import db  # PyMongo sync global :contentReference[oaicite:2]{index=2}

from .region import (
    WarDay, WarPhase, WarWindow,
    RegionWarDocument, to_mongo, from_mongo,
    open_signup, start_war, lock_war, resolve_war,
)

# Campanha semanal: 1 alvo por semana definido pelo bot
from .campaign import ensure_weekly_campaign


# =============================================================================
# Configuração
# =============================================================================

UTC = timezone.utc

# Horários (UTC) - se você quiser que seja horário Brasil (-03), ajustamos depois.
THURSDAY_START = time(18, 0)
THURSDAY_END   = time(22, 0)

SUNDAY_START   = time(15, 0)
SUNDAY_END     = time(21, 0)

# Quanto tempo antes abrir inscrição
SIGNUP_LEAD_TIME = timedelta(hours=1)

# Coleção do estado de guerra por região
REGION_WAR_COLLECTION = "region_war_state"


def _get_collection():
    if db is None:
        raise RuntimeError("Mongo db não inicializado (modules.database.db is None).")
    return db.get_collection(REGION_WAR_COLLECTION)


# =============================================================================
# Persistência (PyMongo sync -> asyncio.to_thread)
# =============================================================================

class RegionWarRepo:
    """
    Repositório de estado de guerra por região.
    Como o PyMongo é síncrono no seu projeto, usamos asyncio.to_thread.
    """

    async def get(self, region_id: str) -> RegionWarDocument:
        col = _get_collection()
        data = await asyncio.to_thread(col.find_one, {"region_id": str(region_id)})

        if not data:
            doc = RegionWarDocument(region_id=str(region_id))
            await asyncio.to_thread(col.insert_one, to_mongo(doc))
            return doc

        return from_mongo(data)

    async def upsert(self, doc: RegionWarDocument) -> None:
        col = _get_collection()
        payload = to_mongo(doc)

        # update_one(filter, update, upsert=True)
        await asyncio.to_thread(
            col.update_one,
            {"region_id": doc.region_id},
            {"$set": payload},
            True,  # upsert=True (posição 4, compatível com PyMongo)
        )


# =============================================================================
# Scheduler de janelas (quinta e domingo)
# =============================================================================

def _weekday_to_war_day(dt: datetime) -> Optional[WarDay]:
    # Monday=0 ... Sunday=6
    wd = dt.weekday()
    if wd == 3:
        return WarDay.THURSDAY
    if wd == 6:
        return WarDay.SUNDAY
    return None


def _make_window_for_date(day: WarDay, date_utc: datetime) -> WarWindow:
    """
    Cria WarWindow para uma data (UTC).
    """
    if day == WarDay.THURSDAY:
        start_t, end_t = THURSDAY_START, THURSDAY_END
    else:
        start_t, end_t = SUNDAY_START, SUNDAY_END

    starts_at = datetime.combine(date_utc.date(), start_t, tzinfo=UTC)
    ends_at   = datetime.combine(date_utc.date(), end_t, tzinfo=UTC)

    if ends_at <= starts_at:
        ends_at += timedelta(days=1)

    return WarWindow(day=day, starts_at=starts_at, ends_at=ends_at)


def get_next_window(now: Optional[datetime] = None) -> WarWindow:
    """
    Retorna a próxima janela de guerra (quinta ou domingo) a partir de agora.
    """
    now = now or datetime.now(UTC)

    today_day = _weekday_to_war_day(now)
    if today_day:
        w = _make_window_for_date(today_day, now)
        if now < w.ends_at:
            return w

    for i in range(1, 8):
        d = now + timedelta(days=i)
        wd = _weekday_to_war_day(d)
        if wd:
            return _make_window_for_date(wd, d)

    # fallback (não deveria ocorrer)
    return _make_window_for_date(WarDay.SUNDAY, now + timedelta(days=7))


def get_current_window(now: Optional[datetime] = None) -> Optional[WarWindow]:
    """
    Se estamos dentro de uma janela de quinta/domingo, retorna a janela atual.
    """
    now = now or datetime.now(UTC)
    wd = _weekday_to_war_day(now)
    if not wd:
        return None

    w = _make_window_for_date(wd, now)
    return w if w.is_open(now) else None


# =============================================================================
# Orquestrador por região
# =============================================================================

@dataclass
class TickResult:
    did_change: bool
    message: Optional[str] = None
    resolved_result: Optional[Dict[str, Any]] = None


class WarEventService:
    """
    Serviço que roda periodicamente (tick) e:
    - abre inscrição (SIGNUP_OPEN)
    - inicia guerra (ACTIVE)
    - fecha e resolve (LOCKED -> resolve -> PEACE)
    """

    def __init__(self, repo: RegionWarRepo):
        self.repo = repo

    async def tick_region(self, region_id: str, now: Optional[datetime] = None) -> TickResult:
        now = now or datetime.now(UTC)
        doc = await self.repo.get(region_id)

        # Se já existe uma janela associada, continua nela; senão calcula a próxima.
        next_window = doc.war.current_window or get_next_window(now)

        # 1) PEACE -> SIGNUP_OPEN quando entra no lead time
        if doc.war.phase == WarPhase.PEACE:
            if (next_window.starts_at - SIGNUP_LEAD_TIME) <= now < next_window.starts_at:
                open_signup(doc, next_window)
                await self.repo.upsert(doc)
                return TickResult(True, f"[WAR] Signup aberto para {next_window.day.value} (region={region_id})")
            return TickResult(False)

        # 2) SIGNUP_OPEN -> ACTIVE ao iniciar janela
        if doc.war.phase == WarPhase.SIGNUP_OPEN:
            if next_window.starts_at <= now < next_window.ends_at:
                start_war(doc)
                await self.repo.upsert(doc)
                return TickResult(True, f"[WAR] Guerra iniciada ({next_window.day.value}) (region={region_id})")

            # Se já passou do fim sem iniciar, reseta
            if now >= next_window.ends_at:
                doc.war.phase = WarPhase.PEACE
                doc.war.current_window = None
                await self.repo.upsert(doc)
                return TickResult(True, f"[WAR] Janela expirou sem iniciar. Reset (region={region_id})")

            return TickResult(False)

        # 3) ACTIVE -> resolve no fim
        if doc.war.phase == WarPhase.ACTIVE:
            if now >= next_window.ends_at:
                lock_war(doc)
                result = resolve_war(doc, next_window.day)
                await self.repo.upsert(doc)
                return TickResult(True, f"[WAR] Guerra encerrada ({next_window.day.value}) (region={region_id})", result)

            return TickResult(False)

        # 4) LOCKED -> PEACE (segurança, normalmente resolve_war já voltou pra PEACE)
        if doc.war.phase == WarPhase.LOCKED:
            doc.war.phase = WarPhase.PEACE
            doc.war.current_window = None
            await self.repo.upsert(doc)
            return TickResult(True, f"[WAR] LOCKED limpo (region={region_id})")

        return TickResult(False)


# =============================================================================
# Tick do ALVO SEMANAL (1 alvo por semana, bot escolhe)
# =============================================================================

async def tick_weekly_target(
    game_data_regions_module,
    now: Optional[datetime] = None,
) -> TickResult:
    """
    Garante a campanha semanal e roda o tick SOMENTE na região-alvo da semana.
    """
    now = now or datetime.now(UTC)

    campaign = await ensure_weekly_campaign(
        game_data_regions_module=game_data_regions_module,
        now=now,
        avoid_last_n=2,
    )
    target_region_id = str(campaign["target_region_id"])

    service = WarEventService(repo=RegionWarRepo())
    return await service.tick_region(target_region_id, now=now)
