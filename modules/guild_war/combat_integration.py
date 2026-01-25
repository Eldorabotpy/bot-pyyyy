# modules/guild_war/combat_integration.py
from __future__ import annotations

from typing import Optional, Any, Dict

from .campaign import ensure_weekly_campaign
from .war_event import WarSignupRepo, WarScoreRepo
from .region import CampaignPhase
from datetime import datetime, timedelta, timezone
from modules import player_manager

UTC = timezone.utc

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

async def process_war_pvp_result(winner_id: str, loser_id: str, game_data_regions_module):
    """
    Chame ao final de um PvP escolhido na zona de guerra.
    Regras:
    - Só processa se campanha ACTIVE
    - Só processa se ambos estão na região alvo
    - Só processa se ambos estão inscritos (war_signups) e têm clã
    Efeitos:
    - Winner: +10 pvp (clã) + cooldown 5 min
    - Loser:  -6 pvp (clã) + ban PvE 30 min
    """
    campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions_module)
    campaign_id = str(campaign.get("campaign_id") or "")
    target_region_id = str(campaign.get("target_region_id") or "")
    phase = str(campaign.get("phase") or "").upper()

    if not campaign_id or not target_region_id:
        return False
    if phase != CampaignPhase.ACTIVE.value:
        return False

    win_data = await player_manager.get_player_data(winner_id)
    lose_data = await player_manager.get_player_data(loser_id)
    if not win_data or not lose_data:
        return False

    # Região (use o mesmo campo que você usa no PvE/painel)
    win_region = str(win_data.get("current_location") or "")
    lose_region = str(lose_data.get("current_location") or "")
    if win_region != target_region_id or lose_region != target_region_id:
        return False

    # Clãs
    winner_clan_id = str(win_data.get("clan_id") or win_data.get("guild_id") or "")
    loser_clan_id  = str(lose_data.get("clan_id") or lose_data.get("guild_id") or "")
    if not winner_clan_id or not loser_clan_id:
        return False

    # Inscrição
    signup_repo = WarSignupRepo()
    if not await signup_repo.is_member_signed_up(campaign_id, winner_clan_id, str(winner_id)):
        return False
    if not await signup_repo.is_member_signed_up(campaign_id, loser_clan_id, str(loser_id)):
        return False

    now = datetime.now(UTC)

    # Cooldown winner (5 min)
    win_data.setdefault("cooldowns", {})
    win_data["cooldowns"]["war_pvp_attack"] = now.isoformat()
    await player_manager.save_player_data(winner_id, win_data)

    # Ban PvE loser (30 min)
    lose_data.setdefault("cooldowns", {})
    ban_time = now + timedelta(minutes=30)
    lose_data["cooldowns"]["war_pve_ban"] = ban_time.isoformat()
    await player_manager.save_player_data(loser_id, lose_data)

    # Pontos (ajuste aqui se quiser)
    await WarScoreRepo().add_points(campaign_id, winner_clan_id, pve=0, pvp=+10)
    await WarScoreRepo().add_points(campaign_id, loser_clan_id,  pve=0, pvp=-6)

    return True

