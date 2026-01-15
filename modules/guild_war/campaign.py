# modules/guild_war/campaign.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple
import random
import asyncio

from modules.database import db  # usa o db global (pymongo sync) :contentReference[oaicite:2]{index=2}

UTC = timezone.utc
WAR_CAMPAIGNS_COLLECTION = "war_campaigns"


@dataclass
class WarCampaign:
    campaign_id: str          # ex: "2026-W03"
    season: int               # ano ISO
    week: int                 # semana ISO
    starts_at: str            # ISO UTC
    ends_at: str              # ISO UTC
    target_region_id: str
    created_at: str           # ISO UTC


def _col():
    if db is None:
        raise RuntimeError("Mongo db não inicializado (modules.database.db is None).")
    return db.get_collection(WAR_CAMPAIGNS_COLLECTION)


def _iso_week_id(dt: datetime) -> Tuple[int, int, str]:
    iso = dt.isocalendar()  # (year, week, weekday)
    season = int(iso.year)
    week = int(iso.week)
    cid = f"{season}-W{week:02d}"
    return season, week, cid


def _week_bounds_utc(dt: datetime) -> Tuple[datetime, datetime]:
    """
    Semana ISO: segunda 00:00:00 até domingo 23:59:59.999 (UTC).
    """
    dt = dt.astimezone(UTC)
    monday = dt - timedelta(days=dt.weekday())
    monday0 = datetime(monday.year, monday.month, monday.day, 0, 0, 0, tzinfo=UTC)
    sunday_end = monday0 + timedelta(days=7) - timedelta(milliseconds=1)
    return monday0, sunday_end


async def get_campaign(campaign_id: str) -> Optional[Dict[str, Any]]:
    col = _col()
    return await asyncio.to_thread(col.find_one, {"campaign_id": str(campaign_id)})


async def get_latest_campaign() -> Optional[Dict[str, Any]]:
    col = _col()
    return await asyncio.to_thread(col.find_one, {}, sort=[("created_at", -1)])


async def upsert_campaign(payload: Dict[str, Any]) -> None:
    col = _col()
    await asyncio.to_thread(
        col.update_one,
        {"campaign_id": payload["campaign_id"]},
        {"$set": payload},
        True,  # upsert=True
    )


async def get_current_campaign(now: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
    now = now or datetime.now(UTC)
    _, _, cid = _iso_week_id(now)
    return await get_campaign(cid)


def choose_weekly_target_region(
    regions_data: Dict[str, Any],
    previous_targets: List[str],
) -> str:
    """
    Seleciona 1 alvo por semana.
    Regras:
    - evita repetir as últimas N (previous_targets)
    - ignora regiões marcadas como disabled=True (se existir)
    """
    regions_data = regions_data or {}
    all_ids = list(regions_data.keys())

    candidates: List[str] = []
    for rid in all_ids:
        meta = regions_data.get(rid) or {}
        if meta.get("disabled") is True:
            continue
        candidates.append(rid)

    if not candidates:
        raise ValueError("Nenhuma região candidata disponível (REGIONS_DATA vazio ou tudo disabled).")

    blocked = set(previous_targets or [])
    non_repeating = [r for r in candidates if r not in blocked]

    pool = non_repeating if non_repeating else candidates
    return random.choice(pool)


async def ensure_weekly_campaign(
    game_data_regions_module,
    now: Optional[datetime] = None,
    avoid_last_n: int = 2,
) -> Dict[str, Any]:
    """
    Garante campanha da semana atual.
    - Se existe, retorna.
    - Se não existe, cria com 1 alvo (bot escolhe).
    """
    now = now or datetime.now(UTC)
    season, week, cid = _iso_week_id(now)

    existing = await get_campaign(cid)
    if existing:
        return existing

    # histórico mínimo: evita repetir a última (ou mais, se você buscar N docs)
    previous_targets: List[str] = []
    latest = await get_latest_campaign()
    if latest and latest.get("target_region_id"):
        previous_targets.append(str(latest["target_region_id"]))

    previous_targets = previous_targets[:max(0, int(avoid_last_n))]

    regions_data = getattr(game_data_regions_module, "REGIONS_DATA", {}) or {}
    target = choose_weekly_target_region(regions_data, previous_targets)

    start, end = _week_bounds_utc(now)

    payload = {
        "campaign_id": cid,
        "season": season,
        "week": week,
        "starts_at": start.isoformat(),
        "ends_at": end.isoformat(),
        "target_region_id": str(target),
        "created_at": datetime.now(UTC).isoformat(),
    }

    await upsert_campaign(payload)
    return payload
