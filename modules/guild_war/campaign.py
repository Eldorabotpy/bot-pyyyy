# modules/guild_war/campaign.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple
import random
import asyncio
import logging

from modules.database import db  # pymongo sync

logger = logging.getLogger(__name__)

UTC = timezone.utc
WAR_CAMPAIGNS_COLLECTION = "war_campaigns"


@dataclass
class WarCampaign:
    campaign_id: str
    season: int
    week: int
    starts_at: str
    ends_at: str
    target_region_id: str
    phase: str
    signup_open: bool
    created_at: str
    updated_at: str


def _col():
    """
    Retorna a collection de campanhas.
    NÃO derruba a aplicação se o DB ainda não estiver inicializado.
    """
    if db is None:
        return None
    return db.get_collection(WAR_CAMPAIGNS_COLLECTION)


def _iso_week_id(dt: datetime) -> Tuple[int, int, str]:
    iso = dt.isocalendar()
    season = int(iso.year)
    week = int(iso.week)
    cid = f"{season}-W{week:02d}"
    return season, week, cid


def _week_bounds_utc(dt: datetime) -> Tuple[datetime, datetime]:
    dt = dt.astimezone(UTC)
    monday = dt - timedelta(days=dt.weekday())
    monday0 = datetime(monday.year, monday.month, monday.day, 0, 0, 0, tzinfo=UTC)
    sunday_end = monday0 + timedelta(days=7) - timedelta(milliseconds=1)
    return monday0, sunday_end


async def get_campaign(campaign_id: str) -> Optional[Dict[str, Any]]:
    col = _col()
    if col is None:
        return None
    return await asyncio.to_thread(col.find_one, {"campaign_id": str(campaign_id)})


async def get_latest_campaign() -> Optional[Dict[str, Any]]:
    col = _col()
    if col is None:
        return None
    return await asyncio.to_thread(col.find_one, {}, sort=[("created_at", -1)])


async def upsert_campaign(payload: Dict[str, Any]) -> None:
    col = _col()
    if col is None:
        logger.warning("[GUILD_WAR] DB indisponível — campanha não persistida.")
        return

    now_iso = datetime.now(UTC).isoformat()

    payload = dict(payload or {})
    payload.setdefault("phase", "PREP")
    payload.setdefault("signup_open", True)
    payload.setdefault("updated_at", now_iso)
    payload.setdefault("created_at", now_iso)

    await asyncio.to_thread(
        col.update_one,
        {"campaign_id": payload["campaign_id"]},
        {"$set": payload},
        True,
    )


async def set_campaign_phase(
    campaign_id: str,
    phase: str,
    signup_open: Optional[bool] = None,
    extra_set: Optional[Dict[str, Any]] = None,
) -> None:
    col = _col()
    if col is None:
        logger.warning("[GUILD_WAR] DB indisponível — set_campaign_phase ignorado.")
        return

    phase = str(phase).upper()
    if phase not in ("PREP", "ACTIVE", "ENDED"):
        raise ValueError(f"phase inválida: {phase}")

    payload: Dict[str, Any] = {
        "phase": phase,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    if signup_open is not None:
        payload["signup_open"] = bool(signup_open)
    if extra_set:
        payload.update(extra_set)

    await asyncio.to_thread(
        col.update_one,
        {"campaign_id": str(campaign_id)},
        {"$set": payload},
        False,
    )


async def get_current_campaign(now: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
    now = now or datetime.now(UTC)
    _, _, cid = _iso_week_id(now)
    return await get_campaign(cid)


def choose_weekly_target_region(
    regions_data: Dict[str, Any],
    previous_targets: List[str],
) -> str:
    regions_data = regions_data or {}
    all_ids = list(regions_data.keys())

    candidates: List[str] = []
    for rid in all_ids:
        meta = regions_data.get(rid) or {}
        if meta.get("disabled") is True:
            continue
        candidates.append(str(rid))

    if not candidates:
        raise ValueError("Nenhuma região candidata disponível.")

    blocked = set(str(x) for x in (previous_targets or []))
    non_repeating = [r for r in candidates if r not in blocked]

    pool = non_repeating if non_repeating else candidates
    return str(random.choice(pool))


async def ensure_weekly_campaign(
    game_data_regions_module,
    now: Optional[datetime] = None,
    avoid_last_n: int = 2,
) -> Dict[str, Any]:
    """
    Garante campanha da semana atual.
    Se DB não estiver disponível, retorna fallback seguro.
    """
    now = now or datetime.now(UTC)
    season, week, cid = _iso_week_id(now)

    # --- DB OFFLINE: fallback seguro ---
    if _col() is None:
        return {
            "campaign_id": cid,
            "season": season,
            "week": week,
            "starts_at": "",
            "ends_at": "",
            "target_region_id": "",
            "phase": "PREP",
            "signup_open": False,
            "created_at": "",
            "updated_at": "",
        }

    existing = await get_campaign(cid)
    if existing:
        phase = str(existing.get("phase") or "PREP").upper()
        signup_open = bool(existing.get("signup_open", True))
        if phase not in ("PREP", "ACTIVE", "ENDED"):
            phase = "PREP"
        if existing.get("phase") != phase or existing.get("signup_open") != signup_open:
            await set_campaign_phase(cid, phase=phase, signup_open=signup_open)
            existing["phase"] = phase
            existing["signup_open"] = signup_open
        return existing

    previous_targets: List[str] = []
    latest = await get_latest_campaign()
    if latest and latest.get("target_region_id"):
        previous_targets.append(str(latest["target_region_id"]))

    previous_targets = previous_targets[:max(0, int(avoid_last_n))]

    regions_data = getattr(game_data_regions_module, "REGIONS_DATA", {}) or {}
    target = choose_weekly_target_region(regions_data, previous_targets)

    start, end = _week_bounds_utc(now)
    now_iso = datetime.now(UTC).isoformat()

    payload = {
        "campaign_id": cid,
        "season": season,
        "week": week,
        "starts_at": start.isoformat(),
        "ends_at": end.isoformat(),
        "target_region_id": str(target),
        "phase": "PREP",
        "signup_open": True,
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    await upsert_campaign(payload)
    return payload
