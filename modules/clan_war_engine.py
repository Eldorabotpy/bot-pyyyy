# modules/clan_war_engine.py
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)
UTC = timezone.utc

# =============================================================================
# CONSTANTES E EXPORTS
# =============================================================================

PHASE_PREP = "PREP"
PHASE_ACTIVE = "ACTIVE"
PHASE_ENDED = "ENDED"

# =============================================================================
# IMPORTS DO SISTEMA
# =============================================================================

from modules.game_data import regions as game_data_regions
from modules.guild_war.campaign import ensure_weekly_campaign, set_campaign_phase
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
# HELPERS
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
# 1. API DE LEITURA (Status, Pontos, Inscrições)
# =============================================================================

async def get_war_status() -> Dict[str, Any]:
    """Retorna o status atual da guerra para o Dashboard."""
    try:
        campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
    except Exception as e:
        logger.exception(f"[CLAN_WAR_ENGINE] ensure_weekly_campaign falhou: {e}")
        return {"season": {"phase": "PREP", "active": False}, "state": {}}

    campaign_id = _safe_str(campaign.get("campaign_id") or current_week_id())
    phase = _phase_norm(campaign.get("phase") or CampaignPhase.PREP.value)
    signup_open = bool(campaign.get("signup_open", True))
    target_region_id = _safe_str(campaign.get("target_region_id") or "")

    meta = get_region_meta(game_data_regions, target_region_id) if target_region_id else {}
    region_name = meta.get("display_name", target_region_id or "—")

    return {
        "season": {
            "season_id": campaign_id,
            "campaign_id": campaign_id,
            "active": (phase == "ACTIVE"),
            "phase": phase,
            "signup_open": signup_open,
            "target_region_id": target_region_id,
            "domination_region_name": region_name,
        }
    }

async def get_clan_weekly_score(clan_id: str) -> Dict[str, Any]:
    clan_id = _safe_str(clan_id)
    campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
    cid = _safe_str(campaign.get("campaign_id") or current_week_id())
    return await WarScoreRepo().get(cid, clan_id)

async def get_clan_signup(campaign_id: str, clan_id: str) -> Dict[str, Any]:
    if not campaign_id:
        campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
        campaign_id = _safe_str(campaign.get("campaign_id") or current_week_id())
    
    repo = WarSignupRepo()
    doc = await repo.get(_safe_str(campaign_id), _safe_str(clan_id))
    
    if not doc:
        return {"campaign_id": campaign_id, "clan_id": clan_id, "member_ids": []}
    
    if "member_ids" not in doc:
        doc["member_ids"] = []
    
    return doc

# =============================================================================
# 2. API DE AÇÕES (Inscrição e Gestão)
# =============================================================================

async def register_clan_for_war(clan_id: str, leader_id: Optional[str] = None) -> Dict[str, Any]:
    """Inscreve o Clã na guerra atual."""
    clan_id = _safe_str(clan_id)
    campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
    campaign_id = _safe_str(campaign.get("campaign_id") or current_week_id())
    
    if str(campaign.get("phase")) != "PREP":
        return {"ok": False, "message": "Fase inválida para inscrição (apenas PREP)."}
    
    repo = WarSignupRepo()
    await repo.upsert_add_member(campaign_id, clan_id, _safe_str(leader_id or ""), leader_id)
    
    return {"ok": True, "campaign_id": campaign_id}

async def member_join_war(clan_id: str, user_id: str) -> Dict[str, Any]:
    """Membro se inscreve na guerra."""
    campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
    campaign_id = _safe_str(campaign.get("campaign_id"))
    
    if str(campaign.get("phase")) != "PREP" or not campaign.get("signup_open"):
        return {"ok": False, "message": "Inscrições fechadas."}

    repo = WarSignupRepo()
    clan_signup = await repo.get(campaign_id, clan_id)
    if not clan_signup:
        return {"ok": False, "message": "O Clã não está inscrito na guerra."}

    await repo.upsert_add_member(campaign_id, clan_id, _safe_str(user_id))
    return {"ok": True}

async def member_leave_war(clan_id: str, user_id: str) -> Dict[str, Any]:
    """Membro sai da lista de guerra."""
    campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
    campaign_id = _safe_str(campaign.get("campaign_id"))
    
    if str(campaign.get("phase")) == "ENDED":
        return {"ok": False, "message": "Guerra já finalizada."}

    repo = WarSignupRepo()
    await repo.remove_member(campaign_id, clan_id, _safe_str(user_id))
    return {"ok": True}

async def set_signup_status(open: bool) -> Dict[str, Any]:
    """Admin/Líder abre ou fecha inscrições."""
    campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
    campaign_id = _safe_str(campaign.get("campaign_id"))
    
    if str(campaign.get("phase")) != "PREP":
        return {"ok": False, "message": "Só é possível alterar vagas na fase PREP."}

    await set_campaign_phase(campaign_id, "PREP", signup_open=open)
    return {"ok": True}

# =============================================================================
# 3. SCHEDULER (JOBS) - Para rodar automático
# =============================================================================

async def tick_weekly_campaign() -> Dict[str, Any]:
    """Wrapper para o evento de tick."""
    return await _tick_weekly_campaign(game_data_regions_module=game_data_regions)

async def _job_war_tick(context) -> None:
    """Callback do JobQueue."""
    try:
        await tick_weekly_campaign()
    except Exception as e:
        logger.exception(f"[CLAN_WAR_ENGINE] tick_weekly_campaign falhou: {e}")

def register_war_jobs(application) -> None:
    """Registra o job de verificação periódica da guerra no PTB."""
    try:
        jq = getattr(application, "job_queue", None)
        if not jq:
            logger.warning("[CLAN_WAR_ENGINE] Sem job_queue; agendamento falhou.")
            return

        # Limpa jobs duplicados
        try:
            for job in jq.jobs():
                if getattr(job, "name", "") == "guild_war_tick":
                    job.schedule_removal()
        except Exception:
            pass

        # Roda a cada 60s
        jq.run_repeating(
            _job_war_tick,
            interval=60,
            first=10,
            name="guild_war_tick",
        )
        logger.info("[CLAN_WAR_ENGINE] Job guild_war_tick agendado (interval=60s).")
    except Exception as e:
        logger.exception(f"[CLAN_WAR_ENGINE] Falha ao registrar jobs: {e}")

# =============================================================================
# 4. DISPATCHER CENTRAL
# =============================================================================

async def engine_call(method: str, *args, **kwargs) -> Any:
    """Roteador de chamadas (Dashboard -> Engine)."""
    m = (method or "").strip()

    # Leitura
    if m == "get_war_status": return await get_war_status()
    if m == "get_clan_weekly_score": return await get_clan_weekly_score(*args)
    if m == "get_clan_signup": return await get_clan_signup(*args)

    # Ações
    if m == "register_clan_for_war": return await register_clan_for_war(*args)
    if m == "member_join_war": return await member_join_war(*args)
    if m == "member_leave_war": return await member_leave_war(*args)
    
    # Gestão
    if m == "set_signup_status":
        val = kwargs.get('open') if 'open' in kwargs else args[0]
        return await set_signup_status(bool(val))

    # Admin/Sistema
    if m == "start_week_prep": return await _start_week_prep(game_data_regions)
    if m == "force_active": return await _force_active(game_data_regions)
    if m == "tick_weekly_campaign": return await tick_weekly_campaign()
    
    # Compatibilidade
    if m == "is_member_signed_up":
        return await WarSignupRepo().is_member_signed_up(str(args[0]), str(args[1]), str(args[2]))

    logger.error(f"[CLAN_WAR_ENGINE] Método desconhecido: {m}")
    return {"ok": False, "message": f"Método {m} não suportado."}

async def _engine_call(method: str, *args, **kwargs) -> Any:
    return await engine_call(method, *args, **kwargs)