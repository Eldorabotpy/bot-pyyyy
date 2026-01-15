# handlers/guild/dashboard.py
# (VERSÃO CORRIGIDA E BLINDADA)
# - Mantém anti-fantasma
# - Aba "Guerra de Clãs" funcionando mesmo com engine em transição (compat de assinatura/retorno)
# - Evita cair em "Opção não encontrada" por retorno inesperado do engine

import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputMediaPhoto, InputMediaAnimation, InputMediaVideo
)
from telegram.ext import ContextTypes, CallbackQueryHandler
from typing import Any, Dict, Optional, Tuple

from modules import player_manager, clan_manager
from modules import file_ids
from modules.game_data.clans import CLAN_PRESTIGE_LEVELS
from modules.auth_utils import get_current_player_id

# Engine Guerra de Clãs (assinaturas podem variar entre versões)
from modules import clan_war_engine

logger = logging.getLogger(__name__)

# ==============================================================================
# 0. COMPAT LAYER (NORMALIZA engine)
# ==============================================================================

def _norm_engine_result(res: Any) -> Dict[str, Any]:
    """
    Normaliza resultados do engine para o formato:
      {"ok": bool, "reason": str|None, "message": str|None, ...}
    Aceita:
      - dict já no formato
      - bool
      - tuple/list (ok, msg) ou (ok, msg, reason)
      - None
    """
    if isinstance(res, dict):
        out = dict(res)
        if "ok" not in out:
            out["ok"] = bool(out.get("success", False))
        return out

    if isinstance(res, bool):
        return {"ok": res, "reason": None, "message": None}

    if isinstance(res, (tuple, list)) and len(res) >= 1:
        ok = bool(res[0])
        msg = res[1] if len(res) >= 2 else None
        reason = res[2] if len(res) >= 3 else None
        return {"ok": ok, "message": msg, "reason": reason}

    return {"ok": False, "reason": "engine_error", "message": None}


async def _engine_call(fn_name: str, *args, **kwargs) -> Dict[str, Any]:
    """
    Chama clan_war_engine.<fn_name> com compat de assinatura.
    Se der TypeError por assinatura diferente, tenta fallback com menos parâmetros.
    """
    fn = getattr(clan_war_engine, fn_name, None)
    if not fn:
        return {"ok": False, "reason": "missing_fn", "message": f"Função ausente: {fn_name}"}

    try:
        res = fn(*args, **kwargs)
        if hasattr(res, "__await__"):
            res = await res
        return _norm_engine_result(res)
    except TypeError:
        # fallback 1: tenta sem kwargs
        try:
            res = fn(*args)
            if hasattr(res, "__await__"):
                res = await res
            return _norm_engine_result(res)
        except TypeError:
            # fallback 2: tenta só (clan_id)
            try:
                if args:
                    res = fn(args[0])
                    if hasattr(res, "__await__"):
                        res = await res
                    return _norm_engine_result(res)
            except Exception:
                pass
        return {"ok": False, "reason": "signature_mismatch", "message": None}
    except Exception as e:
        return {"ok": False, "reason": "engine_exception", "message": str(e)}


def _extract_war_ui_state(ws: Dict[str, Any]) -> Dict[str, Any]:
    """
    Seu dashboard antigo esperava campos (war_id, war_type, horários, registrations_by_clan).
    Como o engine semanal pode não fornecer isso, fazemos fallback coerente.
    """
    state = (ws or {}).get("state") or {}
    season = (ws or {}).get("season") or {}

    # phase preferencial
    phase = state.get("phase") or season.get("phase") or "idle"

    # war_id: preferir season_id, senão week_id se existir, senão "-"
    war_id = (
        state.get("war_id")
        or season.get("season_id")
        or state.get("week_id")
        or "-"
    )

    # tipo (pode ser semanal/territorial)
    war_type = state.get("war_type") or "SEMANAL"

    # horários (se não houver, mostra "-")
    prep_at = state.get("prep_starts_at") or "-"
    start_at = state.get("starts_at") or "-"
    end_at = state.get("ends_at") or "-"

    # registros por clã (se não houver, vazio)
    reg_by_clan = state.get("registrations_by_clan") or {}

    # registered_players: dict {player_id: clan_id}
    registered_players = state.get("registered_players") or {}

    return {
        "war_id": war_id,
        "phase": phase,
        "war_type": war_type,
        "prep_at": prep_at,
        "start_at": start_at,
        "end_at": end_at,
        "registrations_by_clan": reg_by_clan if isinstance(reg_by_clan, dict) else {},
        "registered_players": registered_players if isinstance(registered_players, dict) else {},
    }


# ==============================================================================
# 1. RENDERIZADOR INTELIGENTE
# ==============================================================================
async def _render_clan_screen(update, context, clan_data, text, keyboard):
    query = update.callback_query
    if not query or not query.message:
        return

    media_fid = None
    media_type = "photo"

    try:
        if clan_data and clan_data.get("logo_media_key"):
            media_fid = clan_data.get("logo_media_key")
            media_type = clan_data.get("logo_type", "photo")
    except Exception:
        pass

    if not media_fid:
        try:
            media_fid = file_ids.get_file_id("img_clan_default")
            if not media_fid:
                media_fid = file_ids.get_file_id("guild_dashboard_media")
        except Exception:
            media_fid = None

    reply_markup = InlineKeyboardMarkup(keyboard)
    target_has_media = bool(media_fid)

    try:
        current_has_media = bool(query.message.photo or query.message.video or query.message.animation)
    except Exception:
        current_has_media = False

    must_delete_resend = False

    if target_has_media != current_has_media:
        must_delete_resend = True
    elif target_has_media:
        try:
            if media_type == "video" and not query.message.video:
                must_delete_resend = True
            elif media_type == "animation" and not query.message.animation:
                must_delete_resend = True
            elif media_type == "photo" and not query.message.photo:
                must_delete_resend = True
        except Exception:
            must_delete_resend = True

    # 1) tenta editar
    if not must_delete_resend:
        try:
            if target_has_media:
                if media_type == "video":
                    new_media = InputMediaVideo(media=media_fid, caption=text, parse_mode="HTML")
                elif media_type == "animation":
                    new_media = InputMediaAnimation(media=media_fid, caption=text, parse_mode="HTML")
                else:
                    new_media = InputMediaPhoto(media=media_fid, caption=text, parse_mode="HTML")

                await query.edit_message_media(media=new_media, reply_markup=reply_markup)
            else:
                await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
            return
        except Exception:
            must_delete_resend = True

    # 2) se falhar, reenvia
    if must_delete_resend:
        try:
            await query.delete_message()
        except Exception:
            pass

        try:
            chat_id = query.message.chat_id
            if media_fid:
                if media_type == "video":
                    await context.bot.send_video(chat_id, video=media_fid, caption=text, reply_markup=reply_markup, parse_mode="HTML")
                elif media_type == "animation":
                    await context.bot.send_animation(chat_id, animation=media_fid, caption=text, reply_markup=reply_markup, parse_mode="HTML")
                else:
                    await context.bot.send_photo(chat_id, photo=media_fid, caption=text, reply_markup=reply_markup, parse_mode="HTML")
            else:
                await context.bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Erro fatal rendering clan dashboard: {e}")


# ==============================================================================
# 2. ENTRY POINT
# ==============================================================================
async def adventurer_guild_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    user_id = get_current_player_id(update, context)
    if not user_id:
        if query:
            try:
                await query.answer("Sessão inválida.", show_alert=True)
            except Exception:
                pass
        return

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        if query:
            try:
                await query.answer("Perfil não encontrado.", show_alert=True)
            except Exception:
                pass
        return

    clan_id = player_data.get("clan_id")
    if clan_id:
        await show_clan_dashboard(update, context)
    else:
        try:
            from handlers.guild.creation_search import show_create_clan_menu
            await show_create_clan_menu(update, context)
        except ImportError:
            if query:
                try:
                    await query.answer("Erro: Módulo de criação não encontrado.", show_alert=True)
                except Exception:
                    pass


# ==============================================================================
# 3. DASHBOARD (COM VALIDAÇÃO ANTI-FANTASMA)
# ==============================================================================
async def show_clan_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE, came_from: str = "kingdom"):
    query = update.callback_query
    try:
        if query:
            await query.answer()
    except Exception:
        pass

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

    # ✅ FIX ANTI-FANTASMA: precisa estar em members (ou ser líder)
    members = [str(x) for x in clan_data.get("members", [])]
    if (not is_leader) and (str(user_id) not in members):
        try:
            player_data["clan_id"] = None
            await player_manager.save_player_data(user_id, player_data)
        except Exception:
            pass
        if query:
            try:
                await query.answer("Você não faz mais parte deste clã.", show_alert=True)
            except Exception:
                pass
        await adventurer_guild_menu(update, context)
        return

    clan_name = clan_data.get("display_name", "Clã")
    level = clan_data.get("prestige_level", 1)
    xp = clan_data.get("prestige_points", 0)

    current_level_info = CLAN_PRESTIGE_LEVELS.get(level, {})
    xp_needed = current_level_info.get("points_to_next_level", 999999)
    if not xp_needed:
        xp_needed = xp if xp > 0 else 1

    percent = min(1.0, max(0.0, xp / xp_needed))
    filled = int(percent * 10)
    bar = "🟦" * filled + "⬜" * (10 - filled)

    members_count = len(members)
    max_members = current_level_info.get("max_members", 10)

    text = (
        f"🛡️ <b>CLÃ: {clan_name.upper()}</b> [Nv. {level}]\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>Membros:</b> {members_count}/{max_members}\n"
        f"💰 <b>Cofre:</b> {clan_data.get('bank', 0):,} Ouro\n"
        f"💠 <b>Progresso:</b>\n"
        f"<code>[{bar}]</code> {xp}/{xp_needed} XP\n\n"
        f"📢 <b>Mural:</b> <i>{clan_data.get('mural_text', 'Juntos somos mais fortes!')}</i>"
    )

    keyboard = [
        [InlineKeyboardButton("📜 Missões", callback_data="clan_mission_details"),
         InlineKeyboardButton("🏦 Banco", callback_data="clan_bank_menu")],
        [InlineKeyboardButton("👥 Membros", callback_data="gld_view_members"),
         InlineKeyboardButton("✨ Melhorias", callback_data="clan_upgrade_menu")],
        # ✅ Texto alinhado com sua UI ("Evento"), callback permanece estável
        [InlineKeyboardButton("⚔️ Guerra de Clãs (Evento)", callback_data="clan_war_menu")],
    ]

    if is_leader:
        keyboard.append([InlineKeyboardButton("👑 Gerir Clã", callback_data="clan_manage_menu")])

    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data="show_kingdom_menu")])

    await _render_clan_screen(update, context, clan_data, text, keyboard)


# ==============================================================================
# 3.1 WAR MENU (ABA GUERRA DE CLÃS)
# ==============================================================================
async def show_clan_war_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        if query:
            await query.answer()
    except Exception:
        pass

    user_id = get_current_player_id(update, context)
    if not user_id:
        return

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        return

    clan_id = pdata.get("clan_id")
    if not clan_id:
        await adventurer_guild_menu(update, context)
        return

    # carrega clã (para logo + validações)
    try:
        res = clan_manager.get_clan(clan_id)
        clan_data = await res if hasattr(res, "__await__") else res
    except Exception:
        clan_data = None

    if not clan_data:
        await show_clan_dashboard(update, context)
        return

    leader_id = str(clan_data.get("leader_id", "0"))
    is_leader = (str(user_id) == leader_id)
    members = [str(x) for x in clan_data.get("members", [])]
    if (not is_leader) and (str(user_id) not in members):
        # anti-fantasma
        try:
            pdata["clan_id"] = None
            await player_manager.save_player_data(user_id, pdata)
        except Exception:
            pass
        if query:
            try:
                await query.answer("Você não faz mais parte deste clã.", show_alert=True)
            except Exception:
                pass
        await adventurer_guild_menu(update, context)
        return

    ws = await clan_war_engine.get_war_status()
    ui = _extract_war_ui_state(ws)

    war_id = ui["war_id"]
    phase = ui["phase"]
    war_type = ui["war_type"]
    prep_at = ui["prep_at"]
    start_at = ui["start_at"]
    end_at = ui["end_at"]

    # registrations_by_clan pode não existir no engine semanal — fallback vazio
    reg_by_clan = ui["registrations_by_clan"]
    reg = reg_by_clan.get(str(clan_id), {}) if isinstance(reg_by_clan, dict) else {}

    is_open = bool(reg.get("is_open")) if isinstance(reg, dict) else False
    reg_members = reg.get("members", []) if isinstance(reg, dict) and isinstance(reg.get("members"), list) else []
    reg_count = len(reg_members)

    registered_players = ui["registered_players"]
    me_registered = False
    if isinstance(registered_players, dict):
        me_registered = (registered_players.get(str(user_id)) == str(clan_id))

    clan_name = clan_data.get("display_name", "Clã")

    # Texto
    text = (
        f"⚔️ <b>GUERRA DE CLÃS — {clan_name.upper()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>Rodada:</b> <code>{war_id}</code>\n"
        f"🧭 <b>Tipo:</b> <b>{war_type}</b>\n"
        f"⏳ <b>Fase:</b> <b>{phase}</b>\n\n"
        f"🕰️ <b>Horários:</b>\n"
        f"• PREP: <code>{prep_at}</code>\n"
        f"• Início: <code>{start_at}</code>\n"
        f"• Fim: <code>{end_at}</code>\n\n"
        f"📝 <b>Inscrição do Clã:</b> {'<b>ABERTA</b>' if is_open else '<b>FECHADA</b>'}\n"
        f"👥 <b>Inscritos:</b> {reg_count}\n"
        f"✅ <b>Você:</b> {'INSCRITO' if me_registered else 'NÃO INSCRITO'}\n"
    )

    keyboard = []

    if phase == "prep":
        if is_leader:
            if not is_open:
                keyboard.append([InlineKeyboardButton("📝 Abrir inscrição do Clã", callback_data="clan_war_open")])
            else:
                keyboard.append([InlineKeyboardButton("🔒 Fechar inscrição do Clã", callback_data="clan_war_close")])

        if is_open:
            if not me_registered:
                keyboard.append([InlineKeyboardButton("✅ Participar desta rodada", callback_data="clan_war_join")])
            else:
                keyboard.append([InlineKeyboardButton("❌ Sair da lista", callback_data="clan_war_leave")])

        keyboard.append([InlineKeyboardButton("👥 Ver inscritos", callback_data="clan_war_view")])

    elif phase == "active" or phase == "ACTIVE":
        text += "\n🔥 <b>Guerra ativa!</b>\n"
        text += "⚠️ Somente inscritos nesta rodada podem caçar/atacar e pontuar.\n"
        keyboard.append([InlineKeyboardButton("👥 Ver inscritos", callback_data="clan_war_view")])
    else:
        text += "\nℹ️ Inscrição só pode ser feita durante <b>PREP</b> (no dia do evento).\n"

    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="clan_menu")])

    await _render_clan_screen(update, context, clan_data, text, keyboard)


async def _require_clan_leader(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[Dict[str, Any]], bool]:
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    if not user_id:
        return None, None, None, False

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
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

    members = [str(x) for x in clan_data.get("members", [])]
    if (not is_leader) and (str(user_id) not in members):
        try:
            pdata["clan_id"] = None
            await player_manager.save_player_data(user_id, pdata)
        except Exception:
            pass
        if query:
            try:
                await query.answer("Você não faz mais parte deste clã.", show_alert=True)
            except Exception:
                pass
        return None, None, None, False

    return str(user_id), pdata, clan_data, is_leader


async def clan_war_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    user_id, pdata, clan_data, is_leader = await _require_clan_leader(update, context)
    if not user_id or not pdata or not clan_data:
        return

    if not is_leader:
        try:
            await query.answer("Apenas o líder pode abrir a inscrição.", show_alert=True)
        except Exception:
            pass
        return

    clan_id = str(pdata.get("clan_id"))
    # Compat: engine pode aceitar (clan_id, user_id) ou só ()
    res = await _engine_call("open_clan_registration", clan_id, str(user_id))
    if not res.get("ok"):
        reason = res.get("reason", "erro")
        msg = "Não foi possível abrir."
        if reason in ("registration_closed", "not_prep"):
            msg = "Inscrições fechadas. Só abre durante PREP."
        elif reason == "no_war_scheduled":
            msg = "Nenhuma guerra programada."
        elif reason in ("missing_fn", "signature_mismatch"):
            msg = "Engine de guerra em atualização (função não compatível)."
        try:
            await query.answer(msg, show_alert=True)
        except Exception:
            pass
        return

    try:
        await query.answer("Inscrição do clã aberta!", show_alert=True)
    except Exception:
        pass
    await show_clan_war_menu(update, context)


async def clan_war_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    user_id, pdata, clan_data, is_leader = await _require_clan_leader(update, context)
    if not user_id or not pdata or not clan_data:
        return

    if not is_leader:
        try:
            await query.answer("Apenas o líder pode fechar a inscrição.", show_alert=True)
        except Exception:
            pass
        return

    clan_id = str(pdata.get("clan_id"))
    res = await _engine_call("close_clan_registration", clan_id, str(user_id))
    if not res.get("ok"):
        try:
            await query.answer("Não foi possível fechar.", show_alert=True)
        except Exception:
            pass
        return

    try:
        await query.answer("Inscrição do clã fechada.", show_alert=True)
    except Exception:
        pass
    await show_clan_war_menu(update, context)


async def clan_war_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    user_id, pdata, clan_data, _is_leader = await _require_clan_leader(update, context)
    if not user_id or not pdata or not clan_data:
        return

    clan_id = str(pdata.get("clan_id"))

    # Preferência: engine legado (clan_id, user_id)
    res = await _engine_call("join_war_as_member", clan_id, str(user_id))

    # Fallback: se engine novo exigir (player_id, pdata, region_key, chat_id)
    if not res.get("ok") and res.get("reason") in ("signature_mismatch", "missing_fn"):
        region_key = pdata.get("current_location") or "reino_eldora"
        chat_id = None
        try:
            if query and query.message:
                chat_id = query.message.chat_id
        except Exception:
            chat_id = None
        res = await _engine_call("join_war_as_member", user_id, pdata, region_key, chat_id=chat_id)

    if not res.get("ok"):
        reason = res.get("reason", "erro")
        msg = "Não foi possível participar."
        if reason in ("registration_closed", "not_prep"):
            msg = "Inscrições fechadas. Só durante PREP."
        elif reason == "clan_registration_not_open":
            msg = "O líder ainda não abriu a inscrição do clã."
        elif reason == "no_war_scheduled":
            msg = "Nenhuma guerra programada."
        try:
            await query.answer(msg, show_alert=True)
        except Exception:
            pass
        return

    try:
        await query.answer("Você entrou na lista de inscritos!", show_alert=True)
    except Exception:
        pass
    await show_clan_war_menu(update, context)


async def clan_war_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    user_id, pdata, clan_data, _is_leader = await _require_clan_leader(update, context)
    if not user_id or not pdata or not clan_data:
        return

    clan_id = str(pdata.get("clan_id"))
    res = await _engine_call("leave_war_as_member", clan_id, str(user_id))

    # fallback: engine novo pode esperar (player_id, pdata)
    if not res.get("ok") and res.get("reason") in ("signature_mismatch", "missing_fn"):
        res = await _engine_call("leave_war_as_member", user_id, pdata)

    if not res.get("ok"):
        reason = res.get("reason", "erro")
        msg = "Não foi possível sair."
        if reason in ("registration_closed", "not_prep"):
            msg = "Inscrições fechadas. Só durante PREP."
        try:
            await query.answer(msg, show_alert=True)
        except Exception:
            pass
        return

    try:
        await query.answer("Você saiu da lista.", show_alert=True)
    except Exception:
        pass
    await show_clan_war_menu(update, context)


async def clan_war_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    user_id = get_current_player_id(update, context)
    if not user_id:
        return

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        return

    clan_id = pdata.get("clan_id")
    if not clan_id:
        await show_clan_dashboard(update, context)
        return

    # carrega clã (para logo + validações)
    try:
        res = clan_manager.get_clan(clan_id)
        clan_data = await res if hasattr(res, "__await__") else res
    except Exception:
        clan_data = None

    if not clan_data:
        await show_clan_dashboard(update, context)
        return

    ws = await clan_war_engine.get_war_status()
    ui = _extract_war_ui_state(ws)

    war_id = ui["war_id"]
    phase = ui["phase"]

    # registrations_by_clan pode não existir: tenta fallback em registered_players (apenas presença)
    reg_by_clan = ui["registrations_by_clan"]
    reg = reg_by_clan.get(str(clan_id), {}) if isinstance(reg_by_clan, dict) else {}
    members = reg.get("members", []) if isinstance(reg, dict) and isinstance(reg.get("members"), list) else []

    if not members:
        # fallback mínimo: lista quem está em presença do mesmo clã (registered_players)
        rp = ui["registered_players"]
        members = [pid for pid, cid in (rp or {}).items() if str(cid) == str(clan_id)]

    preview = members[:25]
    lines = "\n".join([f"• <code>{m}</code>" for m in preview]) if preview else "<i>Ninguém inscrito ainda.</i>"
    more = f"\n\n… e mais {len(members) - 25}." if len(members) > 25 else ""

    text = (
        f"👥 <b>INSCRITOS — GUERRA DE CLÃS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>Rodada:</b> <code>{war_id}</code>\n"
        f"⏳ <b>Fase:</b> <b>{phase}</b>\n\n"
        f"{lines}{more}"
    )

    keyboard = [
        [InlineKeyboardButton("⬅️ Voltar", callback_data="clan_war_menu")],
        [InlineKeyboardButton("🏠 Dashboard do Clã", callback_data="clan_menu")],
    ]
    await _render_clan_screen(update, context, clan_data, text, keyboard)


# ==============================================================================
# 4. ROTEADOR
# ==============================================================================
async def clan_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    action = query.data or ""

    from handlers.guild.management import (
        show_clan_management_menu, show_members_list,
        warn_kick_member, do_kick_member, warn_leave_clan, do_leave_clan
    )

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

    if action == "clan_war_join":
        await clan_war_join(update, context)
        return

    if action == "clan_war_leave":
        await clan_war_leave(update, context)
        return

    if action == "clan_war_view":
        await clan_war_view(update, context)
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
            await query.answer("Em breve!", show_alert=True)
        return

    if action == "clan_upgrade_menu":
        if show_clan_upgrade_menu:
            await show_clan_upgrade_menu(update, context)
        else:
            await query.answer("Em breve!", show_alert=True)
        return

    if action.startswith("clan_upgrade_confirm"):
        if confirm_clan_upgrade_callback:
            await confirm_clan_upgrade_callback(update, context)
        else:
            await query.answer("Em breve!", show_alert=True)
        return

    # -------------------------
    # CLÃ: missões
    # -------------------------
    if action == "clan_mission_details":
        if show_guild_mission_details:
            await show_guild_mission_details(update, context)
        else:
            await query.answer("Em breve!", show_alert=True)
        return

    if action == "gld_mission_finish":
        if finish_mission_callback:
            await finish_mission_callback(update, context)
        else:
            await query.answer("Em breve!", show_alert=True)
        return

    if action == "gld_mission_cancel":
        if cancel_mission_callback:
            await cancel_mission_callback(update, context)
        else:
            await query.answer("Em breve!", show_alert=True)
        return

    if action == "gld_mission_select_menu":
        if show_mission_selection_menu:
            await show_mission_selection_menu(update, context)
        else:
            await query.answer("Em breve!", show_alert=True)
        return

    if action.startswith("gld_start_hunt"):
        if start_mission_callback:
            await start_mission_callback(update, context)
        else:
            await query.answer("Em breve!", show_alert=True)
        return

    # fallback
    try:
        await query.answer("Opção não encontrada.", show_alert=True)
    except Exception:
        pass


# Handler principal do clã (router)
clan_handler = CallbackQueryHandler(
    clan_router,
    pattern=r"^clan_|^gld_|^clan_menu$"
)
