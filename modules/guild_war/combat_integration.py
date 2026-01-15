# modules/guild_war/combat_integration.py
from __future__ import annotations

from typing import Optional, Any, Dict

from .campaign import ensure_weekly_campaign
from .war_event import RegionWarRepo
from .region import award_pve_kill, WarPhase, is_participant


async def try_award_pve_kill_for_guild_war(
    player_id: str,
    player_data: Dict[str, Any],
    region_key: Optional[str],
    game_data_regions_module,
    base_points: int = 3,
) -> bool:
    """
    Retorna True se concedeu influência de Guerra (PvE kill).

    Regras:
    - Só conta se a região da batalha == alvo semanal
    - Só conta se guerra está ACTIVE
    - Só conta se jogador está inscrito na guerra
    - Dungeon NÃO deve chamar essa função (controle deve estar no handler)
    """
    if not region_key:
        return False

    pts = int(base_points or 0)
    if pts <= 0:
        return False

    # 1) campanha semanal (1 alvo)
    campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions_module)
    target_region_id = campaign.get("target_region_id")
    if not target_region_id:
        return False

    target_region_id = str(target_region_id)
    if str(region_key) != target_region_id:
        return False

    # 2) carrega doc da guerra da região-alvo
    repo = RegionWarRepo()
    doc = await repo.get(target_region_id)

    # 3) precisa estar ACTIVE
    if doc.war.phase != WarPhase.ACTIVE:
        return False

    # 4) precisa estar inscrito
    pid = str(player_id)
    if not is_participant(doc, pid):
        return False

    # 5) clan_id vem do cadastro de participação (garante consistência)
    part = (doc.war.participants or {}).get(pid) or {}
    clan_id = part.get("clan_id")
    if not clan_id:
        return False

    award_pve_kill(doc, player_id=pid, clan_id=str(clan_id), base_points=pts)
    await repo.upsert(doc)
    return True
