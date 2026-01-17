# modules/guild_war/combat_integration.py
from __future__ import annotations

from typing import Optional, Any, Dict

from .campaign import ensure_weekly_campaign
from .war_event import WarSignupRepo, WarScoreRepo
from .region import CampaignPhase


async def try_award_pve_kill_for_guild_war(
    player_id: str,
    player_data: Dict[str, Any],
    region_key: Optional[str],
    game_data_regions_module,
    base_points: int = 3,
) -> bool:
    """
    Retorna True se concedeu pontos de Guerra (PvE kill).

    Regras:
    - Só conta se a região da batalha == alvo semanal (war_campaigns.target_region_id)
    - Só conta se campanha está ACTIVE
    - Só conta se jogador está inscrito (war_signups)
    - Atribui pontos ao clã do jogador (clan_id em player_data)
    """
    if not region_key:
        return False

    pts = int(base_points or 0)
    if pts <= 0:
        return False

    pid = str(player_id)

    # 1) campanha semanal (1 alvo)
    campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions_module)
    campaign_id = str(campaign.get("campaign_id") or "")
    target_region_id = str(campaign.get("target_region_id") or "")
    phase = str(campaign.get("phase") or "PREP").upper()

    if not campaign_id or not target_region_id:
        return False

    # 2) precisa ser a região alvo
    if str(region_key) != target_region_id:
        return False

    # 3) precisa estar ACTIVE
    if phase != CampaignPhase.ACTIVE.value:
        return False

    # 4) precisa ter clan_id no player_data
    clan_id = player_data.get("clan_id") or player_data.get("guild_id")
    if not clan_id:
        return False
    clan_id = str(clan_id)

    # 5) precisa estar inscrito
    signup_repo = WarSignupRepo()
    if not await signup_repo.is_member_signed_up(campaign_id, clan_id, pid):
        return False

    # 6) pontua
    await WarScoreRepo().add_points(campaign_id, clan_id, pve=pts, pvp=0)
    return True
