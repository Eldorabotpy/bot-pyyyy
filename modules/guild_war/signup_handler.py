# handlers/guild_war/signup_handler.py
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from modules.auth_utils import requires_login, get_current_player_id_async
from modules import player_manager
from modules.game_data import regions as game_data_regions

from modules.guild_war.campaign import ensure_weekly_campaign
from modules.guild_war.war_event import WarSignupRepo
from modules.guild_war.region import (
    CampaignPhase,
    get_region_meta,
    can_participate_in_region_war,
)

logger = logging.getLogger(__name__)

BRT = timezone(timedelta(hours=-3))


def _fmt_dt_br(dt: Optional[datetime]) -> str:
    if not dt:
        return "—"
    try:
        return dt.astimezone(BRT).strftime("%d/%m %H:%M (BRT)")
    except Exception:
        return str(dt)


def _safe_level(player_data: Dict[str, Any]) -> int:
    for k in ("level", "lvl", "player_level"):
        v = player_data.get(k)
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.isdigit():
            return int(v)
    return 1


def _safe_clan_id(player_data: Dict[str, Any]) -> Optional[str]:
    cid = player_data.get("clan_id")
    if cid:
        return str(cid)

    cid = player_data.get("guild_id")
    if cid:
        return str(cid)

    clan_obj = player_data.get("clan") or player_data.get("guild") or {}
    if isinstance(clan_obj, dict):
        cid = clan_obj.get("id") or clan_obj.get("_id")
        if cid:
            return str(cid)

    return None


def _kb_after_signup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Guerra da Semana", callback_data="guild_war_menu")],
        [InlineKeyboardButton("🏰 Voltar ao Clã", callback_data="clan_menu")],
    ])


@requires_login
async def guild_war_signup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler do botão: "Inscrever-se na Guerra".

    Regras do sistema único:
    - 1 alvo por semana via war_campaigns.target_region_id
    - Inscrição só quando phase==PREP e signup_open==True
    - Registro de inscrição em war_signups (campaign_id+clan_id)
    """
    cq = update.callback_query
    if cq:
        try:
            await cq.answer()
        except Exception:
            pass

    player_id = await get_current_player_id_async(update, context)
    if not player_id:
        if cq:
            await cq.answer("⚠️ Sessão expirada. Use /start.", show_alert=True)
        return

    player_data = await player_manager.get_player_data(player_id)
    if not player_data:
        if cq:
            await cq.answer("❌ Não consegui carregar seu personagem.", show_alert=True)
        return

    clan_id = _safe_clan_id(player_data)
    if not clan_id:
        msg = (
            "❌ <b>Você não está em um clã.</b>\n\n"
            "Para participar da Guerra de Clãs, entre ou crie um clã primeiro."
        )
        if cq:
            await cq.edit_message_text(msg, parse_mode="HTML", reply_markup=_kb_after_signup())
        return

    # 1) campanha semanal (fonte única do alvo)
    campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
    campaign_id = str(campaign.get("campaign_id") or "")
    target_region_id = str(campaign.get("target_region_id") or "")
    phase = str(campaign.get("phase") or "PREP").upper()
    signup_open = bool(campaign.get("signup_open", True))

    if not campaign_id or not target_region_id:
        msg = "⚠️ <b>Campanha semanal indisponível.</b>\nTente novamente em instantes."
        if cq:
            await cq.edit_message_text(msg, parse_mode="HTML", reply_markup=_kb_after_signup())
        return

    region_meta = get_region_meta(game_data_regions, target_region_id)

    # 2) valida fase/inscrição
    if phase != CampaignPhase.PREP.value or not signup_open:
        msg = (
            f"{region_meta.get('emoji','📍')} <b>Guerra de Clãs</b>\n"
            f"Rodada: <b>{campaign_id}</b>\n"
            f"Alvo da Semana: <b>{region_meta.get('display_name')}</b>\n\n"
            f"Status: <b>{phase}</b>\n"
            f"Inscrição: <b>{'ABERTA' if signup_open else 'FECHADA'}</b>\n\n"
            f"<i>A inscrição só é liberada durante o período de preparação (PREP) com inscrições abertas.</i>"
        )
        if cq:
            await cq.edit_message_text(msg, parse_mode="HTML", reply_markup=_kb_after_signup())
        return

    # 3) valida nível vs região (se quiser ser 100% livre, você pode remover este bloco)
    level = _safe_level(player_data)
    level_range = region_meta.get("level_range", (1, 999))
    if not can_participate_in_region_war(level, level_range):
        msg = (
            f"❌ <b>Nível insuficiente para este alvo.</b>\n\n"
            f"Alvo: <b>{region_meta.get('display_name')}</b>\n"
            f"Faixa recomendada: <b>{level_range[0]}–{level_range[1]}</b>\n"
            f"Seu nível: <b>{level}</b>\n"
        )
        if cq:
            await cq.edit_message_text(msg, parse_mode="HTML", reply_markup=_kb_after_signup())
        return

    # 4) registra inscrição (por campanha + clã)
    repo = WarSignupRepo()
    already = await repo.is_member_signed_up(campaign_id, clan_id, str(player_id))
    if already:
        msg = (
            f"✅ Você já está inscrito(a) na Guerra desta semana.\n\n"
            f"Rodada: <b>{campaign_id}</b>\n"
            f"Alvo: <b>{region_meta.get('display_name')}</b>"
        )
        if cq:
            await cq.answer("✅ Você já está inscrito.", show_alert=False)
            await cq.edit_message_text(msg, parse_mode="HTML", reply_markup=_kb_after_signup())
        return

    await repo.upsert_add_member(campaign_id, clan_id, member_id=str(player_id), leader_id=None)

    msg = (
        f"✅ <b>Inscrição confirmada!</b>\n\n"
        f"Rodada: <b>{campaign_id}</b>\n"
        f"{region_meta.get('emoji','📍')} Alvo: <b>{region_meta.get('display_name')}</b>\n"
        f"🏰 Clã: <b>{clan_id}</b>\n"
        f"🎚️ Nível: <b>{level}</b>\n\n"
        f"<i>Quando estiver ACTIVE, lute na região-alvo para somar pontos ao seu clã.</i>"
    )

    if cq:
        await cq.edit_message_text(msg, parse_mode="HTML", reply_markup=_kb_after_signup())
    else:
        await update.effective_message.reply_text(msg, parse_mode="HTML", reply_markup=_kb_after_signup())
