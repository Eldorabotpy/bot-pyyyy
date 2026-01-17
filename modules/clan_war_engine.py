# modules/clan_war_engine.py
from __future__ import annotations
import asyncio

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)
UTC = timezone.utc

# =============================================================================
# LEGACY COMPAT EXPORTS (para não quebrar imports antigos)
# =============================================================================

PHASE_PREP = "PREP"
PHASE_ACTIVE = "ACTIVE"
PHASE_ENDED = "ENDED"

SYSTEM_COL = None
SEASON_DOC_ID = "season"
STATE_DOC_ID = "state"
WEEKLY_DOC_ID = "weekly"

# =============================================================================
# Imports do sistema único (NOVO) - sempre absolutos
# =============================================================================

from modules.game_data import regions as game_data_regions
from modules.guild_war.campaign import ensure_weekly_campaign
from modules.guild_war.region import CampaignPhase, get_region_meta
from modules.guild_war.war_event import (
    WarScoreRepo,
    WarSignupRepo,
    tick_weekly_campaign as _tick_weekly_campaign,
    start_week_prep as _start_week_prep,
    force_active as _force_active,
    finalize_campaign as _finalize_campaign,
)

# =============================================================================
# Helpers
# =============================================================================

def _now_utc() -> datetime:
    return datetime.now(UTC)

def _safe_str(v: Any) -> str:
    return "" if v is None else str(v)

def current_week_id(now: Optional[datetime] = None) -> str:
    now = now or _now_utc()
    iso = now.isocalendar()
    year = int(iso.year)
    week = int(iso.week)
    return f"{year}-W{week:02d}"

def _phase_norm(phase: Any) -> str:
    p = _safe_str(phase).strip().upper()
    if p in ("PREP", "ACTIVE", "ENDED"):
        return p
    return "PREP"

# =============================================================================
# API COMPAT (menus antigos)
# =============================================================================

async def get_war_status() -> Dict[str, Any]:
    try:
        campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
    except Exception as e:
        logger.exception(f"[CLAN_WAR_ENGINE] ensure_weekly_campaign falhou: {e}")
        return {
            "season": {
                "season_id": "-",
                "campaign_id": "-",
                "phase": "PREP",
                "active": False,
                "registration_open": False,
                "signup_open": False,
                "target_region_id": "",
                "domination_region": "",
                "domination_region_name": "—",
            },
            "state": {"phase": "PREP", "registered_players": {}},
        }

    campaign_id = _safe_str(campaign.get("campaign_id") or campaign.get("season_id") or current_week_id())
    phase = _phase_norm(campaign.get("phase") or CampaignPhase.PREP.value)
    signup_open = bool(campaign.get("signup_open", True))
    target_region_id = _safe_str(campaign.get("target_region_id") or "")

    meta = get_region_meta(game_data_regions, target_region_id) if target_region_id else {}
    region_name = meta.get("display_name", target_region_id or "—")

    return {
        "season": {
            "season_id": campaign_id,
            "campaign_id": campaign_id,
            "active": True,
            "phase": phase,
            "registration_open": signup_open,  # compat antigo
            "signup_open": signup_open,
            "target_region_id": target_region_id,
            "domination_region": target_region_id,  # compat
            "domination_region_name": region_name,
        },
        "state": {
            "phase": phase,
            "registered_players": {},  # inscritos agora vêm de war_signups
        },
    }

# =============================================================================
# API COMPAT (pontuação/inscrição)
# =============================================================================

async def get_clan_weekly_score(clan_id: str) -> Dict[str, Any]:
    clan_id = _safe_str(clan_id)
    campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
    cid = _safe_str(campaign.get("campaign_id") or current_week_id())
    return await WarScoreRepo().get(cid, clan_id)

async def add_clan_points(clan_id: str, *, pve: int = 0, pvp: int = 0) -> Dict[str, Any]:
    clan_id = _safe_str(clan_id)
    campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
    cid = _safe_str(campaign.get("campaign_id") or current_week_id())
    return await WarScoreRepo().add_points(cid, clan_id, pve=int(pve or 0), pvp=int(pvp or 0))

async def is_member_signed_up(campaign_id: str, clan_id: str, member_id: str) -> bool:
    return await WarSignupRepo().is_member_signed_up(
        _safe_str(campaign_id), _safe_str(clan_id), _safe_str(member_id)
    )

# =============================================================================
# Orquestração (admin/scheduler compat)
# =============================================================================

async def start_week_prep() -> Dict[str, Any]:
    return await _start_week_prep(game_data_regions_module=game_data_regions)

async def force_active() -> Dict[str, Any]:
    return await _force_active(game_data_regions_module=game_data_regions)

async def finalize_campaign(top_n: int = 5) -> Dict[str, Any]:
    return await _finalize_campaign(game_data_regions_module=game_data_regions, top_n=int(top_n or 5))

async def tick_weekly_campaign() -> Dict[str, Any]:
    return await _tick_weekly_campaign(game_data_regions_module=game_data_regions)

# =============================================================================
# ✅ LEGACY: register_war_jobs(application)
# =============================================================================

def register_war_jobs(application) -> None:
    """
    Compat com registries/__init__.py
    Agenda o tick da guerra no JobQueue do PTB.
    - Mantém execução segura (não derruba se db estiver off)
    """
    try:
        jq = getattr(application, "job_queue", None)
        if not jq:
            logger.warning("[CLAN_WAR_ENGINE] Sem job_queue; não foi possível agendar guerra.")
            return

        # Remove jobs duplicados (se o bot reiniciar)
        try:
            for job in jq.jobs():
                if getattr(job, "name", "") == "guild_war_tick":
                    job.schedule_removal()
        except Exception:
            pass

        # Tick a cada 60s (teste rápido). Depois você pode subir para 5min.
        jq.run_repeating(
            _job_war_tick,
            interval=60,
            first=5,
            name="guild_war_tick",
        )

        logger.info("[CLAN_WAR_ENGINE] Job guild_war_tick agendado (interval=60s).")
    except Exception as e:
        logger.exception(f"[CLAN_WAR_ENGINE] Falha ao registrar jobs: {e}")


async def _job_war_tick(context) -> None:
    """
    Callback do JobQueue.
    """
    try:
        await tick_weekly_campaign()
    except Exception as e:
        logger.exception(f"[CLAN_WAR_ENGINE] tick_weekly_campaign falhou: {e}")

# =============================================================================
# Dispatcher para seu padrão _engine_call("...")
# =============================================================================
async def register_clan_for_war(clan_id: str, leader_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Registra o CLÃ na campanha semanal atual.
    Cria o documento base em war_signups.
    """
    clan_id = _safe_str(clan_id)
    leader_id = _safe_str(leader_id) if leader_id else ""

    campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
    campaign_id = _safe_str(campaign.get("campaign_id") or current_week_id())

    phase = _phase_norm(campaign.get("phase") or "PREP")
    signup_open = bool(campaign.get("signup_open", True))

    if phase != "PREP" or not signup_open:
        return {"ok": False, "error": "SIGNUP_CLOSED", "phase": phase, "signup_open": signup_open, "campaign_id": campaign_id}

    repo = WarSignupRepo()
    col = getattr(repo, "col", None)
    if col is None:
        return {"ok": False, "error": "DB_OFFLINE"}

    now_iso = _now_utc().isoformat()

    async def _do_update():
        col.update_one(
            {"campaign_id": campaign_id, "clan_id": clan_id},
            {
                "$setOnInsert": {
                    "campaign_id": campaign_id,
                    "clan_id": clan_id,
                    "leader_id": leader_id,
                    "member_ids": [],
                    "created_at": now_iso,
                },
                "$set": {
                    "updated_at": now_iso,
                    **({"leader_id": leader_id} if leader_id else {}),
                },
            },
            upsert=True,
        )

    # não bloquear o loop
    await asyncio.to_thread(lambda: asyncio.run(_do_update()) if False else col.update_one(
        {"campaign_id": campaign_id, "clan_id": clan_id},
        {
            "$setOnInsert": {
                "campaign_id": campaign_id,
                "clan_id": clan_id,
                "leader_id": leader_id,
                "member_ids": [],
                "created_at": now_iso,
            },
            "$set": {
                "updated_at": now_iso,
                **({"leader_id": leader_id} if leader_id else {}),
            },
        },
        upsert=True,
    ))

    # retorna doc final
    doc = await repo.get(campaign_id, clan_id)

    return {
        "ok": True,
        "campaign_id": campaign_id,
        "clan_id": clan_id,
        "doc": doc or {"campaign_id": campaign_id, "clan_id": clan_id}
    }

async def is_clan_registered(campaign_id: str, clan_id: str) -> bool:
    """
    Fonte única: war_signups.
    Clã está registrado se existir doc {campaign_id, clan_id}.
    """
    campaign_id = _safe_str(campaign_id)
    clan_id = _safe_str(clan_id)

    repo = WarSignupRepo()
    doc = await repo.get(campaign_id, clan_id)
    return bool(doc)


async def get_clan_signup(campaign_id: str, clan_id: str) -> Dict[str, Any]:
    """
    Retorna doc de inscrição do clã em war_signups (ou shape vazio).
    """
    campaign_id = _safe_str(campaign_id)
    clan_id = _safe_str(clan_id)

    repo = WarSignupRepo()
    doc = await repo.get(campaign_id, clan_id)
    return doc or {"campaign_id": campaign_id, "clan_id": clan_id, "member_ids": []}

async def engine_call(method: str, *args) -> Any:
    m = (method or "").strip()

    if m == "get_war_status":
        return await get_war_status()

    if m == "get_clan_weekly_score":
        clan_id = _safe_str(args[0]) if args else ""
        return await get_clan_weekly_score(clan_id)

    if m == "add_clan_points":
        clan_id = _safe_str(args[0]) if len(args) >= 1 else ""
        pve = int(args[1]) if len(args) >= 2 else 0
        pvp = int(args[2]) if len(args) >= 3 else 0
        return await add_clan_points(clan_id, pve=pve, pvp=pvp)

    if m == "is_member_signed_up":
        campaign_id = _safe_str(args[0]) if len(args) >= 1 else ""
        clan_id = _safe_str(args[1]) if len(args) >= 2 else ""
        member_id = _safe_str(args[2]) if len(args) >= 3 else ""
        return await is_member_signed_up(campaign_id, clan_id, member_id)
    
    if m == "is_clan_registered":
        campaign_id = _safe_str(args[0]) if len(args) >= 1 else ""
        clan_id = _safe_str(args[1]) if len(args) >= 2 else ""
        return await is_clan_registered(campaign_id, clan_id)

    if m == "get_clan_signup":
        campaign_id = _safe_str(args[0]) if len(args) >= 1 else ""
        clan_id = _safe_str(args[1]) if len(args) >= 2 else ""
        return await get_clan_signup(campaign_id, clan_id)

    if m == "register_clan_for_war":
        # args: clan_id, leader_id(opcional)
        clan_id = _safe_str(args[0]) if len(args) >= 1 else ""
        leader_id = _safe_str(args[1]) if len(args) >= 2 else ""
        return await register_clan_for_war(clan_id, leader_id=leader_id)

    if m == "start_week_prep":
        return await start_week_prep()

    if m == "force_active":
        return await force_active()

    if m == "finalize_campaign":
        top_n = int(args[0]) if args else 5
        return await finalize_campaign(top_n=top_n)

    if m == "tick_weekly_campaign":
        return await tick_weekly_campaign()

    raise ValueError(f"engine_call: método não suportado: {method}")

async def _engine_call(method: str, *args) -> Any:
    return await engine_call(method, *args)
