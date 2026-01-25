# handlers/admin/clan_war_admin.py
from __future__ import annotations

import logging
import asyncio
from typing import List

from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_ID
from modules.database import db
from modules.game_data import regions as game_data_regions

from modules.guild_war.war_event import (
    start_week_prep,
    force_active,
    finalize_campaign,
)
from modules.guild_war.campaign import ensure_weekly_campaign
from modules.guild_war.region import get_region_meta

logger = logging.getLogger(__name__)


def _is_admin(update: Update) -> bool:
    uid = update.effective_user.id if update.effective_user else None
    return str(uid) == str(ADMIN_ID)


async def _reply(update: Update, text: str) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(text, parse_mode="HTML")


async def cmd_warstatus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/warstatus -> status atual (campanha/fase/inscrição/alvo)"""
    if not _is_admin(update):
        return

    campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
    cid = str(campaign.get("campaign_id") or "-")
    phase = str(campaign.get("phase") or "PREP").upper()
    signup_open = bool(campaign.get("signup_open", True))
    target = str(campaign.get("target_region_id") or "")
    meta = get_region_meta(game_data_regions, target) if target else {}

    await _reply(
        update,
        (
            "📌 <b>Status — Guerra de Clãs</b>\n\n"
            f"Rodada: <b>{cid}</b>\n"
            f"Fase: <b>{phase}</b>\n"
            f"Inscrição: <b>{'ABERTA' if signup_open else 'FECHADA'}</b>\n"
            f"{meta.get('emoji','📍')} Alvo: <b>{meta.get('display_name', target)}</b>"
        ),
    )


async def cmd_wardom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/wardom -> PREP + inscrição aberta + zera placar (e limpa inscrições da rodada)"""
    if not _is_admin(update):
        return

    campaign = await start_week_prep(game_data_regions_module=game_data_regions)
    cid = str(campaign.get("campaign_id") or "-")
    target = str(campaign.get("target_region_id") or "")
    meta = get_region_meta(game_data_regions, target) if target else {}

    await _reply(
        update,
        (
            "✅ <b>Guerra de Clãs</b> — semana iniciada\n\n"
            f"Rodada: <b>{cid}</b>\n"
            f"{meta.get('emoji','📍')} Alvo: <b>{meta.get('display_name', target)}</b>\n"
            "Fase: <b>PREP</b>\n"
            "Inscrição: <b>ABERTA</b>\n"
            "Placar: <b>ZERADO</b>\n"
            "<i>(Inscrições/placares da rodada atual foram reiniciados para teste.)</i>"
        ),
    )


async def cmd_warthu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/warthu -> força ACTIVE (teste)"""
    if not _is_admin(update):
        return

    campaign = await force_active(game_data_regions_module=game_data_regions)
    cid = str(campaign.get("campaign_id") or "-")
    target = str(campaign.get("target_region_id") or "")
    meta = get_region_meta(game_data_regions, target) if target else {}

    await _reply(
        update,
        (
            "🔥 <b>Guerra de Clãs</b> — ACTIVE forçado\n\n"
            f"Rodada: <b>{cid}</b>\n"
            f"{meta.get('emoji','📍')} Alvo: <b>{meta.get('display_name', target)}</b>\n"
            "Fase: <b>ACTIVE</b>\n"
            "Inscrição: <b>FECHADA</b>"
        ),
    )


async def cmd_warend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/warend -> encerra e gera ranking top5"""
    if not _is_admin(update):
        return

    campaign = await finalize_campaign(game_data_regions_module=game_data_regions, top_n=5)
    cid = str(campaign.get("campaign_id") or "-")
    target = str(campaign.get("target_region_id") or "")
    meta = get_region_meta(game_data_regions, target) if target else {}

    result = campaign.get("result") or {}
    winner = result.get("winner")
    top = result.get("top") or []

    lines: List[str] = []
    for i, row in enumerate(top, start=1):
        lines.append(
            f"{i}. <code>{row.get('clan_id')}</code> — <b>{row.get('total', 0)}</b> "
            f"(PvE {row.get('pve', 0)} | PvP {row.get('pvp', 0)})"
        )

    ranking_txt = "\n".join(lines) if lines else "<i>Ninguém pontuou nesta rodada.</i>"
    winner_txt = (
        f"🏆 Vencedor: <code>{winner.get('clan_id')}</code> — <b>{winner.get('total')}</b>"
        if winner else "🏆 Vencedor: <i>sem vencedor</i>"
    )

    await _reply(
        update,
        (
            "🏁 <b>Guerra de Clãs</b> — encerrada\n\n"
            f"Rodada: <b>{cid}</b>\n"
            f"{meta.get('emoji','📍')} Alvo: <b>{meta.get('display_name', target)}</b>\n\n"
            f"{winner_txt}\n\n"
            f"<b>Top 5:</b>\n{ranking_txt}"
        ),
    )


async def cmd_war_hard_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/warreset -> reset total (campanhas/inscrições/placares). Somente teste."""
    if not _is_admin(update):
        return

    if db is None:
        await _reply(update, "❌ DB não inicializado.")
        return

    # nomes conforme modules/guild_war/war_event.py (coleções)
    await asyncio.to_thread(db.get_collection("war_campaigns").delete_many, {})
    await asyncio.to_thread(db.get_collection("war_signups").delete_many, {})
    await asyncio.to_thread(db.get_collection("war_scores").delete_many, {})

    await _reply(
        update,
        "☢️ <b>RESET TOTAL!</b>\n"
        "Campanhas, inscrições e placares foram apagados.\n"
        "Use /wardom para gerar a semana de teste novamente."
    )
