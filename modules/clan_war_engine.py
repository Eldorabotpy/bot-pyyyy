# modules/clan_war_engine.py
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, List
from modules import player_manager
from datetime import timedelta
# Para resolver nomes dos clãs no ranking
from modules import clan_manager 
from bson import ObjectId
from modules.database import db

logger = logging.getLogger(__name__)
UTC = timezone.utc
BRT = timezone(timedelta(hours=-3))

# =============================================================================
# EXPORTS
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
# 1. API DE LEITURA
# =============================================================================

async def get_war_status() -> Dict[str, Any]:
    """Retorna o status atual da guerra para o Dashboard."""
    try:
        # Apenas lê, não executa lógica de tempo
        campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
    except Exception as e:
        logger.exception(f"[CLAN_WAR_ENGINE] ensure_weekly_campaign falhou: {e}")
        return {"season": {"phase": "PREP", "active": False}, "state": {}}

    campaign_id = _safe_str(campaign.get("campaign_id") or current_week_id())
    
    # Confia no banco
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
    """
    Retorna dados de inscrição com CORREÇÃO DE TIPOS e 'ok=True'.
    """
    campaign_id = _safe_str(campaign_id)
    clan_id = _safe_str(clan_id)

    repo = WarSignupRepo()
    doc = await repo.get(campaign_id, clan_id)
    
    if doc:
        doc["ok"] = True
        # Tradutor de IDs (String <-> ObjectId <-> Int) para o painel não se perder
        raw_ids = doc.get("member_ids", [])
        clean_members = []
        for mid in raw_ids:
            clean_members.append(str(mid)) 
        
        doc["members"] = clean_members
        return doc
        
    return {"ok": False, "campaign_id": campaign_id, "clan_id": clan_id, "members": []}

# --- NOVA FUNÇÃO QUE FALTAVA ---
async def get_region_leaderboard(region_key: str) -> List[Dict[str, Any]]:
    """
    Retorna o ranking de clãs para uma região específica.
    """
    # 1. Verifica se a região pedida é o alvo da semana
    campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
    target_region = str(campaign.get("target_region_id") or "")
    
    # Se pedir ranking de uma região que não é o alvo atual, retorna vazio
    if str(region_key) != target_region:
        return []
    
    # 2. Busca os top clãs no banco de scores
    cid = campaign.get("campaign_id")
    repo = WarScoreRepo()
    top_docs = await repo.top_clans(cid, limit=10)
    
    # 3. Formata para o UI (Adiciona nomes dos clãs)
    results = []
    for d in top_docs:
        c_id = d.get("clan_id")
        points = d.get("total", 0)
        
        # Busca nome do clã
        clan_name = f"Clã {c_id}"
        try:
            if clan_manager:
                c_data = await clan_manager.get_clan(c_id)
                if c_data:
                    clan_name = c_data.get("display_name", clan_name)
        except:
            pass
            
        results.append({
            "clan_name": clan_name,
            "points": points
        })
        
    return results

# =============================================================================
# 2. API DE AÇÕES (TRAVAS REMOVIDAS 🔓)
# =============================================================================

async def register_clan_for_war(clan_id: str, leader_id: Optional[str] = None) -> Dict[str, Any]:
    """Inscreve o Clã (Força Bruta)."""
    clan_id = _safe_str(clan_id)
    
    try:
        campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
        campaign_id = _safe_str(campaign.get("campaign_id") or current_week_id())
    except:
        campaign_id = current_week_id()
    
    repo = WarSignupRepo()
    lid = _safe_str(leader_id)
    await repo.upsert_add_member(
        campaign_id,
        clan_id,
        member_id=lid,          # líder entra como membro se tiver id
        leader_id=lid or None,
    )

    return {"ok": True, "campaign_id": campaign_id}

async def member_join_war(clan_id: str, user_id: str) -> Dict[str, Any]:
    """Membro se inscreve (Força Bruta)."""
    try:
        campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
        campaign_id = _safe_str(campaign.get("campaign_id"))
    except:
        campaign_id = current_week_id()
    
    repo = WarSignupRepo()
    # Inscreve direto
    await repo.upsert_add_member(campaign_id, clan_id, _safe_str(user_id))
    return {"ok": True}

async def member_leave_war(clan_id: str, user_id: str) -> Dict[str, Any]:
    try:
        campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
        campaign_id = _safe_str(campaign.get("campaign_id"))
    except:
        campaign_id = current_week_id()

    repo = WarSignupRepo()
    await repo.remove_member(campaign_id, clan_id, _safe_str(user_id))
    return {"ok": True}

async def set_signup_status(open: bool) -> Dict[str, Any]:
    """Permite reabrir vagas manualmente."""
    campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
    campaign_id = _safe_str(campaign.get("campaign_id"))
    await set_campaign_phase(campaign_id, "PREP", signup_open=open)
    return {"ok": True}

# =============================================================================
# 3. SCHEDULER (DESLIGADO)
# =============================================================================

async def tick_weekly_campaign() -> Dict[str, Any]:
    return await ensure_weekly_campaign(game_data_regions_module=game_data_regions)

async def _job_war_tick(context) -> None:
    pass

def register_war_jobs(application) -> None:
    """JOB DESLIGADO MANUALMENTE."""
    pass

# =============================================================================
# 4. DISPATCHER CENTRAL
# =============================================================================

async def engine_call(method: str, *args, **kwargs) -> Any:
    """Roteador de chamadas."""
    m = (method or "").strip()

    if m == "get_war_status": return await get_war_status()
    if m == "get_clan_weekly_score": return await get_clan_weekly_score(*args)
    if m == "get_clan_signup": return await get_clan_signup(*args)
    if m == "get_region_leaderboard": return await get_region_leaderboard(*args) # <--- NOVO!

    if m == "register_clan_for_war": return await register_clan_for_war(*args)
    if m == "member_join_war": return await member_join_war(*args)
    if m == "member_leave_war": return await member_leave_war(*args)
    
    if m == "set_signup_status":
        val = kwargs.get('open') if 'open' in kwargs else args[0]
        return await set_signup_status(bool(val))

    if m == "start_week_prep": return await _start_week_prep(game_data_regions)
    if m == "force_active": return await _force_active(game_data_regions)
    if m == "tick_weekly_campaign": return await tick_weekly_campaign()
    
    if m == "is_member_signed_up":
        return await WarSignupRepo().is_member_signed_up(str(args[0]), str(args[1]), str(args[2]))

    # Fallback para métodos PVE/PVP diretos se necessário
    if m == "get_current_war_mode": return "PVE" 

    logger.error(f"[CLAN_WAR_ENGINE] Método desconhecido: {m}")
    return {"ok": False, "message": f"Método {m} não suportado."}

async def _engine_call(method: str, *args, **kwargs) -> Any:
    return await engine_call(method, *args, **kwargs)

async def get_war_targets_in_region(current_user_id: str, region_key: str) -> list:
    """Busca inimigos da guerra na região."""
    # 1. Meus dados
    me = await player_manager.get_player_data(current_user_id)
    my_clan = str(me.get("clan_id", ""))
    
    # 2. Campanha
    campaign = await ensure_weekly_campaign(game_data_regions)
    cid = campaign.get("campaign_id")

    # 3. Busca jogadores (Exclui meu clã e eu mesmo)
    candidates = await asyncio.to_thread(
        lambda: list(db.players.find(
            {
                "current_location": region_key,
                "clan_id": {"$ne": None, "$ne": my_clan},
                "_id": {"$ne": ObjectId(current_user_id) if ObjectId.is_valid(current_user_id) else current_user_id}
            },
            {"character_name": 1, "clan_id": 1, "level": 1, "class": 1}
        ).limit(15))
    )

    valid_targets = []
    repo = WarSignupRepo()
    
    for p in candidates:
        pid = str(p["_id"])
        pclan = str(p.get("clan_id"))
        
        # Verifica se o inimigo está inscrito
        if await repo.is_member_signed_up(cid, pclan, pid):
            valid_targets.append({
                "user_id": pid,
                "name": p.get("character_name", "Inimigo"),
                "lvl": p.get("level", 1),
                "clan": pclan
            })
            
    return valid_targets

async def check_war_attack_cooldown(user_id: str) -> Optional[float]:
    """Retorna quantos segundos faltam ou None se puder atacar."""
    pdata = await player_manager.get_player_data(user_id)
    cooldowns = pdata.get("cooldowns", {})
    last_attack = cooldowns.get("war_pvp_attack")
    
    if not last_attack: return None
    
    # Converte string ISO para datetime
    try:
        dt_last = datetime.fromisoformat(last_attack)
        if dt_last.tzinfo is None: dt_last = dt_last.replace(tzinfo=UTC)
        
        now = datetime.now(UTC)
        # Cooldown de 5 minutos
        diff = (now - dt_last).total_seconds()
        if diff < 300: # 300s = 5 min
            return 300 - diff
    except:
        pass
        
    return None

async def is_player_blocked_from_hunting(user_id: str) -> bool:
    """Verifica se o jogador tomou ban de PvE na guerra."""
    pdata = await player_manager.get_player_data(user_id)
    cooldowns = pdata.get("cooldowns", {})
    ban_until = cooldowns.get("war_pve_ban")
    
    if not ban_until: return False
    
    try:
        dt_ban = datetime.fromisoformat(ban_until)
        if dt_ban.tzinfo is None: dt_ban = dt_ban.replace(tzinfo=UTC)
        
        if datetime.now(UTC) < dt_ban:
            return True # Ainda está banido
    except:
        pass
    return False

async def is_war_pvp_active() -> bool:
    """Regras de horário do PvP (Domingo ON, Seg-Qui 19-22h)."""
    now = datetime.now(BRT)
    wd = now.weekday() # 0=Seg ... 6=Dom
    hour = now.hour

    if wd == 6: return True # Domingo
    if wd in [4, 5]: return False # Sex/Sab OFF
    
    # Seg-Qui: 19h as 22h
    if 19 <= hour < 22: return True
    
    return False

async def can_player_participate_in_war(player_data: dict) -> tuple[bool, str]:
    """
    Verifica se o jogador pode ver/interagir com os botões de guerra.
    Retorna: (Pode?, Motivo)
    """
    if not player_data:
        return False, "Dados inválidos."
        
    clan_id = player_data.get("clan_id")
    if not clan_id:
        return False, "Sem clã."
        
    user_id = str(player_data.get("_id") or "")
    
    # Pega campanha atual
    campaign = await ensure_weekly_campaign(game_data_regions)
    cid = campaign.get("campaign_id")
    
    # Verifica inscrição no banco
    repo = WarSignupRepo()
    signed = await repo.is_member_signed_up(cid, str(clan_id), user_id)
    
    if not signed:
        return False, "Você não está inscrito na guerra."
        
    return True, None