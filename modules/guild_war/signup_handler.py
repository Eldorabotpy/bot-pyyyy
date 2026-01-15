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
from modules.guild_war.war_event import RegionWarRepo
from modules.guild_war.region import (
    register_participant,
    is_participant,
    WarPhase,
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
    # fallback defensivo
    for k in ("level", "lvl", "player_level"):
        v = player_data.get(k)
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.isdigit():
            return int(v)
    return 1


def _safe_clan_id(player_data: Dict[str, Any]) -> Optional[str]:
    """
    Ajuste aqui se no seu projeto o campo tiver outro nome.
    """
    # Mais comum
    cid = player_data.get("clan_id")
    if cid:
        return str(cid)

    # Alternativas comuns
    cid = player_data.get("guild_id")
    if cid:
        return str(cid)

    # Às vezes vem aninhado
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

    Regras:
    - 1 alvo por semana (bot define)
    - Só permite inscrição se phase == SIGNUP_OPEN
    - Dungeon não entra aqui (isso é no combate)
    """
    cq = update.callback_query
    if cq:
        try:
            await cq.answer()
        except Exception:
            pass

    player_id = await get_current_player_id_async(update, context)
    if not player_id:
        # requires_login já cuida normalmente, mas mantém segurança
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

    # 1) campanha semanal (bot escolhe)
    campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
    target_region_id = str(campaign.get("target_region_id") or "")
    if not target_region_id:
        msg = "⚠️ <b>Campanha semanal indisponível.</b>\nTente novamente em instantes."
        if cq:
            await cq.edit_message_text(msg, parse_mode="HTML", reply_markup=_kb_after_signup())
        return

    # 2) carrega doc da região alvo
    repo = RegionWarRepo()
    doc = await repo.get(target_region_id)

    # 3) valida fase
    if doc.war.phase != WarPhase.SIGNUP_OPEN:
        # Mostra status e janela se existir
        window = doc.war.current_window
        region_meta = get_region_meta(game_data_regions, target_region_id)

        phase_label = {
            WarPhase.PEACE: "Fora de Guerra",
            WarPhase.SIGNUP_OPEN: "Inscrições Abertas",
            WarPhase.ACTIVE: "Guerra Ativa",
            WarPhase.LOCKED: "Apuração",
        }.get(doc.war.phase, doc.war.phase.value)

        msg = (
            f"{region_meta.get('emoji','📍')} <b>Guerra de Clãs</b>\n"
            f"Alvo da Semana: <b>{region_meta.get('display_name')}</b>\n\n"
            f"Status: <b>{phase_label}</b>\n\n"
        )

        if window:
            msg += (
                f"🕒 Janela: <b>{window.day.value}</b>\n"
                f"Início: {_fmt_dt_br(window.starts_at)}\n"
                f"Fim: {_fmt_dt_br(window.ends_at)}\n"
            )
        else:
            msg += "🕒 Janela: —\n"

        msg += "\n<i>A inscrição só é liberada quando o período de inscrição estiver aberto.</i>"

        if cq:
            await cq.edit_message_text(msg, parse_mode="HTML", reply_markup=_kb_after_signup())
        return

    # 4) já inscrito?
    if is_participant(doc, str(player_id)):
        region_meta = get_region_meta(game_data_regions, target_region_id)
        msg = (
            f"✅ Você já está inscrito(a) na Guerra desta semana.\n\n"
            f"Alvo: <b>{region_meta.get('display_name')}</b>"
        )
        if cq:
            await cq.answer("✅ Você já está inscrito.", show_alert=False)
            await cq.edit_message_text(msg, parse_mode="HTML", reply_markup=_kb_after_signup())
        return

    # 5) valida level x região (se você quiser ser mais permissivo, pode remover)
    level = _safe_level(player_data)
    region_meta = get_region_meta(game_data_regions, target_region_id)
    level_range = region_meta.get("level_range", (1, 999))

    if not can_participate_in_region_war(level, level_range):
        msg = (
            f"❌ <b>Nível insuficiente para este alvo.</b>\n\n"
            f"Alvo: <b>{region_meta.get('display_name')}</b>\n"
            f"Faixa recomendada: <b>{level_range[0]}–{level_range[1]}</b>\n"
            f"Seu nível: <b>{level}</b>\n\n"
            f"<i>Suba de nível e tente novamente na próxima janela de inscrição.</i>"
        )
        if cq:
            await cq.edit_message_text(msg, parse_mode="HTML", reply_markup=_kb_after_signup())
        return

    # 6) registra inscrição
    register_participant(doc, player_id=str(player_id), clan_id=str(clan_id), level=int(level))
    await repo.upsert(doc)

    window = doc.war.current_window
    msg = (
        f"✅ <b>Inscrição confirmada!</b>\n\n"
        f"{region_meta.get('emoji','📍')} Alvo da Semana: <b>{region_meta.get('display_name')}</b>\n"
        f"🏰 Seu clã: <b>{clan_id}</b>\n"
        f"🎚️ Seu nível: <b>{level}</b>\n\n"
    )
    if window:
        msg += (
            f"🕒 <b>Janela da Guerra</b>\n"
            f"Dia: <b>{window.day.value}</b>\n"
            f"Início: {_fmt_dt_br(window.starts_at)}\n"
            f"Fim: {_fmt_dt_br(window.ends_at)}\n\n"
        )

    msg += "<i>Agora é só aguardar a guerra começar e lutar na região-alvo para somar influência.</i>"

    if cq:
        await cq.edit_message_text(msg, parse_mode="HTML", reply_markup=_kb_after_signup())
    else:
        await update.effective_message.reply_text(msg, parse_mode="HTML", reply_markup=_kb_after_signup())
