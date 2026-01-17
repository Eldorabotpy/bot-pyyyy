# handlers/guild/dashboard.py
# (VERSÃO UNIFICADA E CORRIGIDA)
# - Render robusto via ui_renderer (fallback automático de mídia)
# - Guerra de Clãs usando fonte única: war_campaigns + war_signups + war_scores
# - Botões que antes "não respondiam" agora sempre dão feedback (alert/toast)
# - Remove chamadas a funções que não existem no engine (open_clan_registration/join_war_as_member/etc.)

import logging
from typing import Any, Dict, Optional, Tuple, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, clan_manager, file_ids
from modules.game_data.clans import CLAN_PRESTIGE_LEVELS
from modules.auth_utils import get_current_player_id

# UI renderer (blindado para mídia inválida)
from ui.ui_renderer import render_photo_or_text

# Engine compat (status + score + register_clan_for_war)
from modules import clan_war_engine

logger = logging.getLogger(__name__)


# ==============================================================================
# 0) HELPERS
# ==============================================================================

def _sid(x: Any) -> str:
    try:
        return str(x)
    except Exception:
        return ""

def _phase_norm(x: Any) -> str:
    p = _sid(x).strip().upper()
    return p if p else "PREP"

def _bool(v: Any, default: bool = False) -> bool:
    try:
        return bool(v)
    except Exception:
        return default

async def _safe_answer(query, text: str = "", show_alert: bool = False) -> None:
    if not query:
        return
    try:
        await query.answer(text, show_alert=show_alert)
    except Exception:
        pass

async def _show_loading_overlay(update: Update, context: ContextTypes.DEFAULT_TYPE, title: str, subtitle: str = ""):
    # Mantém o usuário “vendo” que o clique foi processado
    query = update.callback_query
    if not query or not query.message:
        return

    txt = f"⏳ <b>{title}</b>"
    if subtitle:
        txt += f"\n\n<i>{subtitle}</i>"

    try:
        # Se mensagem for foto: editar caption; senão, editar texto
        if query.message.photo or query.message.video or query.message.animation:
            await query.edit_message_caption(txt, parse_mode="HTML", reply_markup=None)
        else:
            await query.edit_message_text(txt, parse_mode="HTML", reply_markup=None)
    except Exception:
        pass


def _norm_engine_result(res: Any) -> Dict[str, Any]:
    """
    Normaliza retornos do engine para {ok, reason, message, ...}
    """
    if isinstance(res, dict):
        out = dict(res)
        if "ok" not in out:
            # Heurística: status do engine vem como {'season':..., 'state':...}
            if "season" in out or "state" in out:
                out["ok"] = True
            else:
                out["ok"] = bool(out.get("success", False))
        return out
    if isinstance(res, bool):
        return {"ok": res}
    if isinstance(res, (tuple, list)) and res:
        ok = bool(res[0])
        msg = res[1] if len(res) >= 2 else None
        reason = res[2] if len(res) >= 3 else None
        return {"ok": ok, "message": msg, "reason": reason}
    return {"ok": False, "reason": "engine_error"}


async def _engine_call(fn_name: str, *args, **kwargs) -> Dict[str, Any]:
    fn = getattr(clan_war_engine, fn_name, None)
    if not fn:
        return {"ok": False, "reason": "missing_fn", "message": f"Função ausente: {fn_name}"}

    try:
        res = fn(*args, **kwargs)
        if hasattr(res, "__await__"):
            res = await res
        return _norm_engine_result(res)
    except Exception as e:
        logger.exception("[DASHBOARD] engine_call falhou: %s(%s,%s) err=%s", fn_name, args, kwargs, e)
        return {"ok": False, "reason": "engine_exception", "message": str(e)}


async def _require_clan_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[Dict[str, Any]], bool]:
    """
    Valida sessão + clã + anti-fantasma. Retorna (user_id, player_data, clan_data, is_leader).
    """
    query = update.callback_query

    user_id = get_current_player_id(update, context)
    if not user_id:
        if query:
            await _safe_answer(query, "Sessão inválida.", show_alert=True)
        return None, None, None, False

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        if query:
            await _safe_answer(query, "Perfil não encontrado.", show_alert=True)
        return None, None, None, False

    clan_id = pdata.get("clan_id")
    if not clan_id:
        return str(user_id), pdata, None, False

    try:
        res = clan_manager.get_clan(clan_id)
        clan_data = await res if hasattr(res, "__await__") else res
    except Exception:
        clan_data = None

    if not clan_data:
        return str(user_id), pdata, None, False

    leader_id = str(clan_data.get("leader_id", "0"))
    is_leader = (str(user_id) == leader_id)

    members = [str(x) for x in (clan_data.get("members", []) or [])]
    if (not is_leader) and (str(user_id) not in members):
        # anti-fantasma: limpa clan_id preso
        try:
            pdata["clan_id"] = None
            await player_manager.save_player_data(user_id, pdata)
        except Exception:
            pass
        if query:
            await _safe_answer(query, "Você não faz mais parte deste clã.", show_alert=True)
        return None, None, None, False

    return str(user_id), pdata, clan_data, is_leader


def _pick_clan_media(clan_data: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    Seleciona mídia do clã com fallback global. (Somente FOTO, pois ui_renderer é foto+texto.)
    """
    media_fid = None
    try:
        if clan_data and clan_data.get("logo_media_key"):
            media_fid = clan_data.get("logo_media_key")
    except Exception:
        pass

    if not media_fid:
        try:
            media_fid = file_ids.get_file_id("img_clan_default") or file_ids.get_file_id("guild_dashboard_media")
        except Exception:
            media_fid = None

    return media_fid


async def _render_clan_screen(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    clan_data: Optional[Dict[str, Any]],
    text: str,
    keyboard: List[List[InlineKeyboardButton]],
    scope: str,
) -> None:
    reply_markup = InlineKeyboardMarkup(keyboard)
    photo_fid = _pick_clan_media(clan_data)

    await render_photo_or_text(
        update,
        context,
        text=text,
        photo_file_id=photo_fid,
        reply_markup=reply_markup,
        scope=scope,
        allow_edit=True,
        delete_previous_on_send=True,
    )


# ==============================================================================
# 1) ENTRY POINT
# ==============================================================================

async def adventurer_guild_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    user_id = get_current_player_id(update, context)
    if not user_id:
        if query:
            await _safe_answer(query, "Sessão inválida.", show_alert=True)
        return

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        if query:
            await _safe_answer(query, "Perfil não encontrado.", show_alert=True)
        return

    clan_id = player_data.get("clan_id")
    if clan_id:
        await show_clan_dashboard(update, context)
    else:
        try:
            from handlers.guild.creation_search import show_create_clan_menu
            await show_create_clan_menu(update, context)
        except Exception:
            if query:
                await _safe_answer(query, "Erro: menu de criação indisponível.", show_alert=True)


# ==============================================================================
# 2) CLAN DASHBOARD
# ==============================================================================

async def show_clan_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE, came_from: str = "kingdom"):
    query = update.callback_query
    if query:
        await _safe_answer(query)

    user_id = get_current_player_id(update, context)
    if not user_id:
        return

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        return

    clan_id = player_data.get("clan_id")
    if not clan_id:
        await adventurer_guild_menu(update, context)
        return

    try:
        res = clan_manager.get_clan(clan_id)
        clan_data = await res if hasattr(res, "__await__") else res
    except Exception:
        clan_data = None

    if not clan_data:
        # clã sumiu: limpa e volta
        try:
            player_data["clan_id"] = None
            await player_manager.save_player_data(user_id, player_data)
        except Exception:
            pass
        await adventurer_guild_menu(update, context)
        return

    leader_id = str(clan_data.get("leader_id", "0"))
    is_leader = (str(user_id) == leader_id)

    members = [str(x) for x in (clan_data.get("members", []) or [])]
    if (not is_leader) and (str(user_id) not in members):
        try:
            player_data["clan_id"] = None
            await player_manager.save_player_data(user_id, player_data)
        except Exception:
            pass
        if query:
            await _safe_answer(query, "Você não faz mais parte deste clã.", show_alert=True)
        await adventurer_guild_menu(update, context)
        return

    clan_name = clan_data.get("display_name", "Clã")
    level = int(clan_data.get("prestige_level", 1) or 1)
    xp = int(clan_data.get("prestige_points", 0) or 0)

    current_level_info = CLAN_PRESTIGE_LEVELS.get(level, {}) or {}
    xp_needed = int(current_level_info.get("points_to_next_level", 999999) or 999999)
    if xp_needed <= 0:
        xp_needed = max(1, xp)

    percent = min(1.0, max(0.0, xp / xp_needed))
    filled = int(percent * 10)
    bar = "🟦" * filled + "⬜" * (10 - filled)

    members_count = len(members)
    max_members = int(current_level_info.get("max_members", 10) or 10)

    text = (
        f"🛡️ <b>CLÃ: {clan_name.upper()}</b> [Nv. {level}]\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>Membros:</b> {members_count}/{max_members}\n"
        f"💰 <b>Cofre:</b> {int(clan_data.get('bank', 0) or 0):,} Ouro\n"
        f"💠 <b>Progresso:</b>\n"
        f"<code>[{bar}]</code> {xp}/{xp_needed} XP\n\n"
        f"📢 <b>Mural:</b> <i>{clan_data.get('mural_text', 'Juntos somos mais fortes!')}</i>"
    )

    keyboard = [
        [InlineKeyboardButton("📜 Missões", callback_data="clan_mission_details"),
         InlineKeyboardButton("🏦 Banco", callback_data="clan_bank_menu")],
        [InlineKeyboardButton("👥 Membros", callback_data="gld_view_members"),
         InlineKeyboardButton("✨ Melhorias", callback_data="clan_upgrade_menu")],
        [InlineKeyboardButton("⚔️ Guerra de Clãs", callback_data="clan_war_menu")],
    ]

    if is_leader:
        keyboard.append([InlineKeyboardButton("👑 Gerir Clã", callback_data="clan_manage_menu")])

    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data="show_kingdom_menu")])

    await _render_clan_screen(
        update, context,
        clan_data=clan_data,
        text=text,
        keyboard=keyboard,
        scope="clan_dashboard",
    )


# ==============================================================================
# 3) GUERRA DE CLÃS — MENU
# ==============================================================================

async def show_clan_war_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await _safe_answer(query)

    user_id, pdata, clan_data, is_leader = await _require_clan_member(update, context)
    if not user_id or not pdata or not clan_data:
        # sem clã: volta
        await adventurer_guild_menu(update, context)
        return

    clan_id = str(pdata.get("clan_id"))

    # ---- STATUS ÚNICO (campanha semanal)
    ws = await _engine_call("get_war_status")
    season = (ws.get("season", {}) or {})

    phase_raw = str(season.get("phase") or "PREP").upper()
    phase_u = _phase_norm(phase_raw)

    is_open = _bool(season.get("signup_open", season.get("registration_open", False)), False)

    season_id = (
        season.get("season_id")
        or season.get("campaign_id")
        or season.get("war_id")
        or "-"
    )
    war_id = str(season_id)

    target_region_id = (
        season.get("target_region_id")
        or season.get("domination_region")
        or season.get("domination_region_id")
        or "?"
    )

    # nome bonito da região
    try:
        from modules.game_data import regions as game_data_regions
        from modules.guild_war.region import get_region_meta
        region_meta = get_region_meta(game_data_regions, str(target_region_id))
        region_name = region_meta.get("display_name", str(target_region_id))
        region_emoji = region_meta.get("emoji", "📍")
    except Exception:
        region_name = str(target_region_id)
        region_emoji = "📍"

    # ---- INSCRITOS (war_signups)
    reg_members: List[str] = []
    clan_registered = False
    me_registered = False
    try:
        from modules.guild_war.war_event import WarSignupRepo
        signup_repo = WarSignupRepo()
        signup_doc = await signup_repo.get(str(season_id), str(clan_id))
        clan_registered = bool(signup_doc)
        if signup_doc:
            reg_members = [str(x) for x in (signup_doc.get("member_ids", []) or [])]
            me_registered = (str(user_id) in reg_members)
    except Exception as e:
        logger.warning("[WAR_MENU] Falha lendo war_signups: %s", e)
        reg_members = []
        clan_registered = False
        me_registered = False

    reg_count = len(reg_members)

    # ---- SCORE (war_scores)
    score = {"total": 0, "pve": 0, "pvp": 0}
    s = await _engine_call("get_clan_weekly_score", str(clan_id))
    if isinstance(s, dict) and s.get("ok") is not False:
        # engine retorna dict direto do repo; pode conter campaign_id/clan_id/total/pve/pvp
        score = {**score, **{k: s.get(k) for k in ("total", "pve", "pvp")}}

    total_pts = int(score.get("total", 0) or 0)
    pve_pts = int(score.get("pve", 0) or 0)
    pvp_pts = int(score.get("pvp", 0) or 0)

    clan_name = clan_data.get("display_name", "Clã")

    text = (
        f"⚔️ <b>GUERRA DE CLÃS — {clan_name.upper()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>Rodada:</b> <code>{war_id}</code>\n"
        f"⏳ <b>Fase:</b> <b>{phase_u}</b>\n"
        f"{region_emoji} <b>Região da Dominação:</b> <b>{region_name}</b>\n\n"
        f"📝 <b>Inscrição:</b> {'<b>ABERTA</b>' if is_open else '<b>FECHADA</b>'}\n"
        f"🏷️ <b>Clã:</b> {'<b>INSCRITO</b>' if clan_registered else '<b>NÃO INSCRITO</b>'}\n"
        f"👥 <b>Inscritos:</b> {reg_count}\n"
        f"✅ <b>Você:</b> {'INSCRITO' if me_registered else 'NÃO INSCRITO'}\n\n"
        f"⭐ <b>PONTUAÇÃO DO CLÃ</b>\n"
        f"• <b>Total da Semana:</b> <b>{total_pts}</b> pts\n"
        f"• PvE: {pve_pts} | PvP: {pvp_pts}\n"
    )

    keyboard: List[List[InlineKeyboardButton]] = []

    if phase_raw == "PREP":
        if is_leader:
            if not clan_registered:
                keyboard.append([InlineKeyboardButton("🏷️ Inscrever Clã na Guerra", callback_data="clan_war_register_clan")])
            else:
                keyboard.append([InlineKeyboardButton("✅ Clã Inscrito na Guerra", callback_data="clan_war_view")])

            if not is_open:
                keyboard.append([InlineKeyboardButton("📝 Abrir inscrição", callback_data="clan_war_open")])
            else:
                keyboard.append([InlineKeyboardButton("🔒 Fechar inscrição", callback_data="clan_war_close")])

        if is_open:
            if not clan_registered:
                keyboard.append([InlineKeyboardButton("⛔ Clã ainda não inscrito", callback_data="clan_noop")])
            else:
                if not me_registered:
                    keyboard.append([InlineKeyboardButton("✅ Participar desta rodada", callback_data="clan_war_join")])
                else:
                    keyboard.append([InlineKeyboardButton("❌ Sair da lista", callback_data="clan_war_leave")])

        keyboard.append([InlineKeyboardButton("👥 Ver inscritos", callback_data="clan_war_view")])

    elif phase_raw == "ACTIVE":
        text += "\n🔥 <b>Guerra ativa!</b>\n⚠️ Somente inscritos nesta rodada podem pontuar.\n"
        keyboard.append([InlineKeyboardButton("👥 Ver inscritos", callback_data="clan_war_view")])
    else:
        text += "\nℹ️ Inscrição só pode ser feita durante <b>PREP</b>.\n"
        keyboard.append([InlineKeyboardButton("👥 Ver inscritos", callback_data="clan_war_view")])

    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="clan_menu")])

    await _render_clan_screen(
        update, context,
        clan_data=clan_data,
        text=text,
        keyboard=keyboard,
        scope="clan_war_menu",
    )


# ==============================================================================
# 3.1) GUERRA — AÇÕES
# ==============================================================================

async def clan_war_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await _safe_answer(query)

    await _show_loading_overlay(update, context, "Processando...", "Abrindo inscrição")

    user_id, pdata, clan_data, is_leader = await _require_clan_member(update, context)
    if not user_id or not pdata or not clan_data:
        return

    if not is_leader:
        await _safe_answer(query, "Apenas o líder pode abrir a inscrição.", show_alert=True)
        await show_clan_war_menu(update, context)
        return

    try:
        from modules.game_data import regions as game_data_regions
        from modules.guild_war.campaign import ensure_weekly_campaign, set_campaign_phase

        campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
        campaign_id = str(campaign.get("campaign_id") or "")
        phase = str(campaign.get("phase") or "PREP").upper()

        if phase != "PREP":
            await _safe_answer(query, "Só é possível abrir durante PREP.", show_alert=True)
            await show_clan_war_menu(update, context)
            return

        await set_campaign_phase(campaign_id, phase="PREP", signup_open=True)
        await _safe_answer(query, "Inscrição aberta!", show_alert=True)

    except Exception as e:
        logger.exception("[WAR_OPEN] erro: %s", e)
        await _safe_answer(query, "Erro ao abrir inscrição.", show_alert=True)

    await show_clan_war_menu(update, context)


async def clan_war_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await _safe_answer(query)

    await _show_loading_overlay(update, context, "Processando...", "Fechando inscrição")

    user_id, pdata, clan_data, is_leader = await _require_clan_member(update, context)
    if not user_id or not pdata or not clan_data:
        return

    if not is_leader:
        await _safe_answer(query, "Apenas o líder pode fechar a inscrição.", show_alert=True)
        await show_clan_war_menu(update, context)
        return

    try:
        from modules.game_data import regions as game_data_regions
        from modules.guild_war.campaign import ensure_weekly_campaign, set_campaign_phase

        campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
        campaign_id = str(campaign.get("campaign_id") or "")
        phase = str(campaign.get("phase") or "PREP").upper()

        if phase != "PREP":
            await _safe_answer(query, "Só é possível fechar durante PREP.", show_alert=True)
            await show_clan_war_menu(update, context)
            return

        await set_campaign_phase(campaign_id, phase="PREP", signup_open=False)
        await _safe_answer(query, "Inscrição fechada.", show_alert=True)

    except Exception as e:
        logger.exception("[WAR_CLOSE] erro: %s", e)
        await _safe_answer(query, "Erro ao fechar inscrição.", show_alert=True)

    await show_clan_war_menu(update, context)


async def clan_war_register_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await _safe_answer(query)

    await _show_loading_overlay(update, context, "Processando...", "Inscrevendo o clã")

    user_id, pdata, clan_data, is_leader = await _require_clan_member(update, context)
    if not user_id or not pdata or not clan_data:
        return

    if not is_leader:
        await _safe_answer(query, "Apenas o líder pode inscrever o clã.", show_alert=True)
        await show_clan_war_menu(update, context)
        return

    clan_id = str(pdata.get("clan_id"))

    res = await _engine_call("register_clan_for_war", clan_id, str(user_id))

    if not res.get("ok"):
        err = res.get("error") or res.get("reason") or "erro"
        msg = res.get("message") or "Não foi possível inscrever o clã."
        if err == "DB_OFFLINE":
            msg = "Banco indisponível no momento (Mongo)."
        await _safe_answer(query, msg, show_alert=True)
    else:
        await _safe_answer(query, "✅ Clã inscrito na rodada!", show_alert=True)

    await show_clan_war_menu(update, context)


async def clan_war_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await _safe_answer(query)

    await _show_loading_overlay(update, context, "Processando...", "Entrando na lista")

    user_id, pdata, clan_data, _is_leader = await _require_clan_member(update, context)
    if not user_id or not pdata or not clan_data:
        return

    try:
        from modules.game_data import regions as game_data_regions
        from modules.guild_war.campaign import ensure_weekly_campaign
        from modules.guild_war.war_event import WarSignupRepo

        clan_id = str(pdata.get("clan_id"))
        campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
        campaign_id = str(campaign.get("campaign_id") or "")
        phase = str(campaign.get("phase") or "PREP").upper()
        signup_open = bool(campaign.get("signup_open", False))

        if phase != "PREP" or not signup_open:
            await _safe_answer(query, "Inscrição fechada (apenas PREP).", show_alert=True)
            await show_clan_war_menu(update, context)
            return

        # precisa existir doc do clã (clã inscrito)
        signup_repo = WarSignupRepo()
        doc = await signup_repo.get(campaign_id, clan_id)
        if not doc:
            await _safe_answer(query, "Seu clã ainda não foi inscrito nesta rodada.", show_alert=True)
            await show_clan_war_menu(update, context)
            return

        await signup_repo.upsert_add_member(campaign_id, clan_id, str(user_id), leader_id=str(doc.get("leader_id") or ""))
        await _safe_answer(query, "✅ Você entrou na lista da rodada!", show_alert=True)

    except Exception as e:
        logger.exception("[WAR_JOIN] erro: %s", e)
        await _safe_answer(query, "Erro ao participar.", show_alert=True)

    await show_clan_war_menu(update, context)


async def clan_war_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await _safe_answer(query)

    await _show_loading_overlay(update, context, "Processando...", "Saindo da lista")

    user_id, pdata, clan_data, _is_leader = await _require_clan_member(update, context)
    if not user_id or not pdata or not clan_data:
        return

    try:
        from modules.game_data import regions as game_data_regions
        from modules.guild_war.campaign import ensure_weekly_campaign
        from modules.guild_war.war_event import WarSignupRepo

        clan_id = str(pdata.get("clan_id"))
        campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
        campaign_id = str(campaign.get("campaign_id") or "")
        phase = str(campaign.get("phase") or "PREP").upper()

        # permitir sair somente em PREP (evita mudar lista na guerra ativa)
        if phase != "PREP":
            await _safe_answer(query, "Só é possível sair durante PREP.", show_alert=True)
            await show_clan_war_menu(update, context)
            return

        signup_repo = WarSignupRepo()
        await signup_repo.remove_member(campaign_id, clan_id, str(user_id))
        await _safe_answer(query, "Você saiu da lista.", show_alert=True)

    except Exception as e:
        logger.exception("[WAR_LEAVE] erro: %s", e)
        await _safe_answer(query, "Erro ao sair.", show_alert=True)

    await show_clan_war_menu(update, context)


async def clan_war_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await _safe_answer(query)

    user_id, pdata, clan_data, _is_leader = await _require_clan_member(update, context)
    if not user_id or not pdata or not clan_data:
        return

    clan_id = str(pdata.get("clan_id"))

    # campanha atual
    try:
        from modules.game_data import regions as game_data_regions
        from modules.guild_war.campaign import ensure_weekly_campaign
        from modules.guild_war.war_event import WarSignupRepo

        campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
        campaign_id = str(campaign.get("campaign_id") or "-")
        phase = str(campaign.get("phase") or "PREP").upper()

        signup_repo = WarSignupRepo()
        doc = await signup_repo.get(campaign_id, clan_id)
        members = [str(x) for x in ((doc or {}).get("member_ids", []) or [])]

    except Exception as e:
        logger.exception("[WAR_VIEW] erro: %s", e)
        campaign_id = "-"
        phase = "PREP"
        members = []

    preview = members[:25]
    if preview:
        lines = "\n".join([f"• <code>{m}</code>" for m in preview])
    else:
        lines = "<i>Ninguém inscrito ainda.</i>"

    more = ""
    if len(members) > 25:
        more = f"\n\n… e mais {len(members) - 25} jogador(es)."

    clan_name = clan_data.get("display_name", "Clã")

    text = (
        f"👥 <b>INSCRITOS — GUERRA DE CLÃS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🏰 <b>Clã:</b> {clan_name}\n"
        f"🆔 <b>Rodada:</b> <code>{campaign_id}</code>\n"
        f"⏳ <b>Fase:</b> <b>{_phase_norm(phase)}</b>\n\n"
        f"{lines}{more}"
    )

    keyboard = [
        [InlineKeyboardButton("⬅️ Voltar", callback_data="clan_war_menu")],
        [InlineKeyboardButton("🏠 Dashboard do Clã", callback_data="clan_menu")],
    ]

    await _render_clan_screen(
        update, context,
        clan_data=clan_data,
        text=text,
        keyboard=keyboard,
        scope="clan_war_view",
    )


# ==============================================================================
# 4) ROUTER
# ==============================================================================

async def clan_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    action = query.data

    from handlers.guild.management import (
        show_clan_management_menu, show_members_list,
        warn_kick_member, do_kick_member, warn_leave_clan, do_leave_clan
    )

    # opcionais
    show_guild_mission_details = None
    finish_mission_callback = None
    cancel_mission_callback = None
    show_mission_selection_menu = None
    start_mission_callback = None
    show_clan_bank_menu = None
    show_clan_upgrade_menu = None
    confirm_clan_upgrade_callback = None

    try:
        from handlers.guild.missions import (
            show_guild_mission_details,
            finish_mission_callback,
            cancel_mission_callback,
            show_mission_selection_menu,
            start_mission_callback
        )
    except Exception:
        pass

    try:
        from handlers.guild.bank import show_clan_bank_menu
    except Exception:
        pass

    try:
        from handlers.guild.upgrades import show_clan_upgrade_menu, confirm_clan_upgrade_callback
    except Exception:
        pass

    # -------------------------
    # CLÃ: Dashboard / Guerra
    # -------------------------
    if action == "clan_menu":
        await show_clan_dashboard(update, context)
        return

    if action == "clan_war_menu":
        await show_clan_war_menu(update, context)
        return

    if action == "clan_war_open":
        await clan_war_open(update, context)
        return

    if action == "clan_war_close":
        await clan_war_close(update, context)
        return

    if action == "clan_war_register_clan":
        await clan_war_register_clan(update, context)
        return

    if action == "clan_war_join":
        await clan_war_join(update, context)
        return

    if action == "clan_war_leave":
        await clan_war_leave(update, context)
        return

    if action == "clan_war_view":
        await clan_war_view(update, context)
        return

    if action == "clan_noop":
        await _safe_answer(query, "⛔ Seu clã ainda não foi inscrito nesta rodada.", show_alert=True)
        return

    # -------------------------
    # CLÃ: gestão / membros
    # -------------------------
    if action == "clan_manage_menu":
        await show_clan_management_menu(update, context)
        return

    if action in ("clan_view_members", "gld_view_members"):
        await show_members_list(update, context)
        return

    if action.startswith("clan_kick_ask:"):
        await warn_kick_member(update, context)
        return

    if action.startswith("clan_kick_do:"):
        await do_kick_member(update, context)
        return

    if action == "clan_leave_ask":
        await warn_leave_clan(update, context)
        return

    if action == "clan_leave_perform":
        await do_leave_clan(update, context)
        return

    # -------------------------
    # CLÃ: banco / melhorias
    # -------------------------
    if action == "clan_bank_menu":
        if show_clan_bank_menu:
            await show_clan_bank_menu(update, context)
        else:
            await _safe_answer(query, "Em breve!", show_alert=True)
        return

    if action == "clan_upgrade_menu":
        if show_clan_upgrade_menu:
            await show_clan_upgrade_menu(update, context)
        else:
            await _safe_answer(query, "Em breve!", show_alert=True)
        return

    if action.startswith("clan_upgrade_confirm"):
        if confirm_clan_upgrade_callback:
            await confirm_clan_upgrade_callback(update, context)
        else:
            await _safe_answer(query, "Em breve!", show_alert=True)
        return

    # -------------------------
    # CLÃ: missões
    # -------------------------
    if action == "clan_mission_details":
        if show_guild_mission_details:
            await show_guild_mission_details(update, context)
        else:
            await _safe_answer(query, "Em breve!", show_alert=True)
        return

    if action == "gld_mission_finish":
        if finish_mission_callback:
            await finish_mission_callback(update, context)
        else:
            await _safe_answer(query, "Em breve!", show_alert=True)
        return

    if action == "gld_mission_cancel":
        if cancel_mission_callback:
            await cancel_mission_callback(update, context)
        else:
            await _safe_answer(query, "Em breve!", show_alert=True)
        return

    if action == "gld_mission_select_menu":
        if show_mission_selection_menu:
            await show_mission_selection_menu(update, context)
        else:
            await _safe_answer(query, "Em breve!", show_alert=True)
        return

    if action.startswith("gld_start_hunt"):
        if start_mission_callback:
            await start_mission_callback(update, context)
        else:
            await _safe_answer(query, "Em breve!", show_alert=True)
        return

    await _safe_answer(query, "Opção não encontrada.", show_alert=True)


# Handler principal do clã (router)
clan_handler = CallbackQueryHandler(
    clan_router,
    pattern=r"^clan_|^gld_|^clan_menu$"
)
