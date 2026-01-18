# modules/guild_war/war_event.py
from __future__ import annotations

import logging
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List, Tuple

from modules.database import db

from .campaign import ensure_weekly_campaign, set_campaign_phase
from .region import CampaignPhase

logger = logging.getLogger(__name__)
UTC = timezone.utc

WAR_SIGNUPS_COLLECTION = "war_signups"
WAR_SCORES_COLLECTION = "war_scores"


def _get_col(name: str):
    if db is None:
        raise RuntimeError("Mongo db não inicializado (modules.database.db is None).")
    return db.get_collection(name)


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _norm_id(v: Any) -> str:
    if v is None:
        return ""
    return str(v)


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return int(default)


# =============================================================================
# Repositórios (campanha -> inscrições -> placares)
# =============================================================================

class WarSignupRepo:
    def __init__(self):
        self.col = _get_col(WAR_SIGNUPS_COLLECTION)

    async def get(self, campaign_id: str, clan_id: str) -> Optional[Dict[str, Any]]:
        cid = _norm_id(campaign_id)
        gid = _norm_id(clan_id)
        return await asyncio.to_thread(self.col.find_one, {"campaign_id": cid, "clan_id": gid})

    async def upsert_add_member(
        self,
        campaign_id: str,
        clan_id: str,
        member_id: str,
        leader_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Insere doc se não existir e adiciona membro ao set.
        """
        cid = _norm_id(campaign_id)
        gid = _norm_id(clan_id)
        mid = _norm_id(member_id)
        now_iso = _now_utc().isoformat()

        base_set: Dict[str, Any] = {"updated_at": now_iso}
        if leader_id:
            base_set["leader_id"] = _norm_id(leader_id)

        await asyncio.to_thread(
            self.col.update_one,
            {"campaign_id": cid, "clan_id": gid},
            {
                "$setOnInsert": {
                    "campaign_id": cid,
                    "clan_id": gid,
                    "leader_id": base_set.get("leader_id"),
                    "member_ids": [],
                    "created_at": now_iso,
                },
                "$set": base_set,
                "$addToSet": {"member_ids": mid},
            },
            True,
        )
        return (await self.get(cid, gid)) or {"campaign_id": cid, "clan_id": gid, "member_ids": [mid]}

    async def remove_member(self, campaign_id: str, clan_id: str, member_id: str) -> None:
        cid = _norm_id(campaign_id)
        gid = _norm_id(clan_id)
        mid = _norm_id(member_id)
        await asyncio.to_thread(
            self.col.update_one,
            {"campaign_id": cid, "clan_id": gid},
            {"$pull": {"member_ids": mid}, "$set": {"updated_at": _now_utc().isoformat()}},
            False,
        )

    async def is_member_signed_up(self, campaign_id: str, clan_id: str, member_id: str) -> bool:
        doc = await self.get(campaign_id, clan_id)
        if not doc:
            return False
        mids = doc.get("member_ids") or []
        return _norm_id(member_id) in set(_norm_id(x) for x in mids)

    async def count_members(self, campaign_id: str, clan_id: str) -> int:
        doc = await self.get(campaign_id, clan_id)
        if not doc:
            return 0
        return len(doc.get("member_ids") or [])


class WarScoreRepo:
    def __init__(self):
        self.col = _get_col(WAR_SCORES_COLLECTION)

    async def get(self, campaign_id: str, clan_id: str) -> Dict[str, Any]:
        cid = _norm_id(campaign_id)
        gid = _norm_id(clan_id)
        doc = await asyncio.to_thread(self.col.find_one, {"campaign_id": cid, "clan_id": gid})
        if not doc:
            return {"campaign_id": cid, "clan_id": gid, "total": 0, "pve": 0, "pvp": 0}
        return {
            "campaign_id": cid,
            "clan_id": gid,
            "total": _safe_int(doc.get("total"), 0),
            "pve": _safe_int(doc.get("pve"), 0),
            "pvp": _safe_int(doc.get("pvp"), 0),
        }

    async def add_points(self, campaign_id: str, clan_id: str, pve: int = 0, pvp: int = 0) -> Dict[str, Any]:
        cid = _norm_id(campaign_id)
        gid = _norm_id(clan_id)
        pve = _safe_int(pve, 0)
        pvp = _safe_int(pvp, 0)
        total = pve + pvp
        if total == 0:
            return await self.get(cid, gid)

        now_iso = _now_utc().isoformat()
        await asyncio.to_thread(
            self.col.update_one,
            {"campaign_id": cid, "clan_id": gid},
            {
                "$setOnInsert": {"campaign_id": cid, "clan_id": gid, "created_at": now_iso},
                "$inc": {"total": total, "pve": pve, "pvp": pvp},
                "$set": {"updated_at": now_iso},
            },
            True,
        )
        return await self.get(cid, gid)

    async def reset_campaign(self, campaign_id: str) -> None:
        cid = _norm_id(campaign_id)
        await asyncio.to_thread(self.col.delete_many, {"campaign_id": cid})

    async def top_clans(self, campaign_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        cid = _norm_id(campaign_id)
        cursor = await asyncio.to_thread(
            lambda: list(self.col.find({"campaign_id": cid}).sort("total", -1).limit(int(limit)))
        )
        out: List[Dict[str, Any]] = []
        for d in cursor or []:
            out.append({
                "clan_id": _norm_id(d.get("clan_id")),
                "total": _safe_int(d.get("total"), 0),
                "pve": _safe_int(d.get("pve"), 0),
                "pvp": _safe_int(d.get("pvp"), 0),
            })
        return out


# =============================================================================
# Orquestração (admin/testes e tick)
# =============================================================================

async def start_week_prep(game_data_regions_module, now: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Admin: inicia semana em PREP, abre inscrição, zera placar.
    """
    now = now or _now_utc()
    campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions_module, now=now)

    campaign_id = _norm_id(campaign.get("campaign_id"))
    await set_campaign_phase(campaign_id, phase=CampaignPhase.PREP.value, signup_open=True)

    # zera placares da campanha
    await WarScoreRepo().reset_campaign(campaign_id)

    # opcional: limpar inscrições da campanha (recomeço de teste rápido)
    await asyncio.to_thread(_get_col(WAR_SIGNUPS_COLLECTION).delete_many, {"campaign_id": campaign_id})

    campaign["phase"] = CampaignPhase.PREP.value
    campaign["signup_open"] = True
    return campaign


async def force_active(game_data_regions_module, now: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Admin: força ACTIVE (quinta/domingo) para teste.
    """
    now = now or _now_utc()
    campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions_module, now=now)
    campaign_id = _norm_id(campaign.get("campaign_id"))
    await set_campaign_phase(campaign_id, phase=CampaignPhase.ACTIVE.value, signup_open=False)
    campaign["phase"] = CampaignPhase.ACTIVE.value
    campaign["signup_open"] = False
    return campaign


async def finalize_campaign(game_data_regions_module, now: Optional[datetime] = None, top_n: int = 5) -> Dict[str, Any]:
    """
    Admin: encerra e gera ranking (topN).
    """
    now = now or _now_utc()
    campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions_module, now=now)
    campaign_id = _norm_id(campaign.get("campaign_id"))

    score_repo = WarScoreRepo()
    top = await score_repo.top_clans(campaign_id, limit=int(top_n))

    winner = top[0] if top else None

    await set_campaign_phase(
        campaign_id,
        phase=CampaignPhase.ENDED.value,
        signup_open=False,
        extra_set={
            "result": {
                "winner": winner,
                "top": top,
                "finalized_at": _now_utc().isoformat(),
            }
        }
    )

    campaign["phase"] = CampaignPhase.ENDED.value
    campaign["signup_open"] = False
    campaign["result"] = {"winner": winner, "top": top}
    return campaign


async def tick_weekly_campaign(game_data_regions_module, now: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Tick único do evento (scheduler chamará isso):
    - garante campanha semanal
    - (LÓGICA AUTOMÁTICA DESLIGADA PARA TESTES MANUAIS)
    """
    now = now or _now_utc()
    campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions_module, now=now)
    
    # --- BLOCO COMENTADO PARA PARAR O ROBÔ ---
    # campaign_id = _norm_id(campaign.get("campaign_id"))

    # # ISO weekday: Monday=1 ... Sunday=7
    # wd = int(now.isoweekday())

    # # Quinta (4) e Domingo (7) -> ACTIVE
    # should_be_active = wd in (4, 7)

    # if should_be_active:
    #     await set_campaign_phase(campaign_id, phase=CampaignPhase.ACTIVE.value, signup_open=False)
    #     campaign["phase"] = CampaignPhase.ACTIVE.value
    #     campaign["signup_open"] = False
    # else:
    #     await set_campaign_phase(campaign_id, phase=CampaignPhase.PREP.value, signup_open=True)
    #     campaign["phase"] = CampaignPhase.PREP.value
    #     campaign["signup_open"] = True
    # -----------------------------------------

    return campaign
