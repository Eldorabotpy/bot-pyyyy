# handlers/guild/dashboard.py
# (VERSÃO CORRIGIDA E BLINDADA)
# - Mantém anti-fantasma
# - Aba "Guerra de Clãs" funcionando com engine semanal/compat
# - Corrige comparação de fase (PREP/ACTIVE/ENDED)
# - Corrige 400 BadRequest: nunca tenta sendPhoto com media_fid None/inválido

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

# Engine Guerra de Clãs
from modules import clan_war_engine

logger = logging.getLogger(__name__)

# ==============================================================================
# 0. HELPERS
# ==============================================================================

def _sid(x: Any) -> str:
    try:
        return str(x)
    except Exception:
        return ""

def _phase_norm(x: Any) -> str:
    p = _sid(x).strip()
    return p.upper() if p else "IDLE"

def _looks_like_telegram_file_id(x: str) -> bool:
    """
    Heurística simples: file_id do Telegram costuma ter comprimento grande e não parece 'chave' interna.
    Não é perfeito, mas evita 400 por ids óbvios errados.
    """
    if not x or not isinstance(x, str):
        return False
    x = x.strip()
    if not x:
        return False
    # URL também vale
    if x.startswith("http://") or x.startswith("https://"):
        return True
    if len(x) < 20:
        return False
    # chaves internas comuns
    if x.startswith(("img_", "menu_", "file_", "logo_", "clan_", "guild_")):
        return False
    return True


# ==============================================================================
# 1. COMPAT LAYER (NORMALIZA engine)
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
    Estratégia:
      1) tenta com args/kwargs
      2) tenta só args
      3) tenta sem args (muito importante p/ engine semanal)
      4) tenta só (args[0]) se existir
    """
    fn = getattr(clan_war_engine, fn_name, None)
    if not fn:
        return {"ok": False, "reason": "missing_fn", "message": f"Função ausente: {fn_name}"}

    # 1) args + kwargs
    try:
        res = fn(*args, **kwargs)
        if hasattr(res, "__await__"):
            res = await res
        return _norm_engine_result(res)
    except TypeError:
        pass
    except Exception as e:
        return {"ok": False, "reason": "engine_exception", "message": str(e)}

    # 2) só args
    try:
        res = fn(*args)
        if hasattr(res, "__await__"):
            res = await res
        return _norm_engine_result(res)
    except TypeError:
        pass
    except Exception as e:
        return {"ok": False, "reason": "engine_exception", "message": str(e)}

    # 3) sem args (✅ necessário para open/close no engine semanal)
    try:
        res = fn()
        if hasattr(res, "__await__"):
            res = await res
        return _norm_engine_result(res)
    except TypeError:
        pass
    except Exception as e:
        return {"ok": False, "reason": "engine_exception", "message": str(e)}

    # 4) só (args[0])
    try:
        if args:
            res = fn(args[0])
            if hasattr(res, "__await__"):
                res = await res
            return _norm_engine_result(res)
    except Exception:
        pass

    return {"ok": False, "reason": "signature_mismatch", "message": None}


def _extract_war_ui_state(ws: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza estado retornado por get_war_status() para a UI.
    """
    state = (ws or {}).get("state") or {}
    season = (ws or {}).get("season") or {}

    phase = state.get("phase") or season.get("phase") or "IDLE"
    phase = _phase_norm(phase)

    war_id = (
        state.get("war_id")
        or season.get("season_id")
        or state.get("week_id")
        or "-"
    )

    war_type = state.get("war_type") or "SEMANAL"

    prep_at = state.get("prep_starts_at") or "-"
    start_at = state.get("starts_at") or "-"
    end_at = state.get("ends_at") or "-"

    reg_by_clan = state.get("registrations_by_clan") or {}
    registered_players = state.get("registered_players") or {}

    # ✅ Flag opcional (se engine guardar no season)
    registration_open = bool(season.get("registration_open", False))

    return {
        "war_id": war_id,
        "phase": phase,  # PREP/ACTIVE/ENDED/IDLE
        "war_type": war_type,
        "prep_at": prep_at,
        "start_at": start_at,
        "end_at": end_at,
        "registrations_by_clan": reg_by_clan if isinstance(reg_by_clan, dict) else {},
        "registered_players": registered_players if isinstance(registered_players, dict) else {},
        "registration_open": registration_open,
    }


# ==============================================================================
# 2. RENDERIZADOR INTELIGENTE (corrigido 400)
# ==============================================================================
async def _render_clan_screen(update, context, clan_data, text, keyboard):
    query = update.callback_query
    if not query or not query.message:
        return

    media_fid = None
    media_type = "photo"

    # 1) tenta logo do clã
    try:
        if clan_data and clan_data.get("logo_media_key"):
            media_fid = clan_data.get("logo_media_key")
            media_type = clan_data.get("logo_type", "photo")
    except Exception:
        pass

    # 2) fallback padrão do sistema
    if not media_fid:
        try:
            media_fid = file_ids.get_file_id("img_clan_default")
            if not media_fid:
                media_fid = file_ids.get_file_id("guild_dashboard_media")
        except Exception:
            media_fid = None

    # 3) blindagem: não tente mídia inválida
    if media_fid and not _looks_like_telegram_file_id(str(media_fid)):
        media_fid = None
        media_type = "photo"

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

    # 2) se falhar, reenvia (✅ nunca manda send_photo com None)
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
# 3. ENTRY POINT
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
# 4. DASHBOARD (COM VALIDAÇÃO ANTI-FANTASMA)
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

    leader_id = _sid(clan_data.get("leader_id", "0"))
    is_leader = (_sid(user_id) == leader_id)

    # anti-fantasma
    members = [_sid(x) for x in clan_data.get("members", [])]
    if (not is_leader) and (_sid(user_id) not in members):
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
        [InlineKeyboardButton("⚔️ Guerra de Clãs (Evento)", callback_data="clan_war_menu")],
    ]

    if is_leader:
        keyboard.append([InlineKeyboardButton("👑 Gerir Clã", callback_data="clan_manage_menu")])

    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data="show_kingdom_menu")])

    await _render_clan_screen(update, context, clan_data, text, keyboard)


# ==============================================================================
# 5. WAR MENU (ABA GUERRA DE CLÃS) — CORRIGIDO
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

    # carrega clã
    try:
        res = clan_manager.get_clan(clan_id)
        clan_data = await res if hasattr(res, "__await__") else res
    except Exception:
        clan_data = None

    if not clan_data:
        await show_clan_dashboard(update, context)
        return

    leader_id = _sid(clan_data.get("leader_id", "0"))
    is_leader = (_sid(user_id) == leader_id)

    members = [_sid(x) for x in clan_data.get("members", [])]
    if (not is_leader) and (_sid(user_id) not in members):
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
    phase = ui["phase"]          # PREP/ACTIVE/ENDED/IDLE
    war_type = ui["war_type"]
    prep_at = ui["prep_at"]
    start_at = ui["start_at"]
    end_at = ui["end_at"]

    # ✅ inscrição aberta: usa flag do season se existir; senão tenta reg_by_clan
    reg_by_clan = ui["registrations_by_clan"]
    reg = reg_by_clan.get(_sid(clan_id), {}) if isinstance(reg_by_clan, dict) else {}

    # se reg_by_clan não existir no engine semanal, isso fica vazio
    is_open = bool(ui.get("registration_open", False))
    if isinstance(reg, dict) and "is_open" in reg:
        is_open = bool(reg.get("is_open"))

    reg_members = reg.get("members", []) if isinstance(reg, dict) and isinstance(reg.get("members"), list) else []
    reg_count = len(reg_members)

    registered_players = ui["registered_players"]
    me_registered = False
    if isinstance(registered_players, dict):
        me_registered = (_sid(registered_players.get(_sid(user_id))) == _sid(clan_id))

    clan_name = clan_data.get("display_name", "Clã")

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
        f"👥 <b>Inscritos (lista):</b> {reg_count}\n"
        f"✅ <b>Você:</b> {'INSCRITO' if me_registered else 'NÃO INSCRITO'}\n"
    )

    keyboard = []

    # ✅ PREP: líder sempre vê controles (não pode ficar travado em "fechada")
    if phase == "PREP":
        if is_leader:
            if not is_open:
                keyboard.append([InlineKeyboardButton("📝 Abrir inscrição do Clã", callback_data="clan_war_open")])
            else:
                keyboard.append([InlineKeyboardButton("🔒 Fechar inscrição do Clã", callback_data="clan_war_close")])

            # ✅ registro do clã na semana (necessário p/ participar)
            if is_open:
                keyboard.append([InlineKeyboardButton("🏷️ Inscrever Clã na Guerra", callback_data="clan_war_register_clan")])

        # membros só podem entrar na lista se estiver aberto
        if is_open:
            if not me_registered:
                keyboard.append([InlineKeyboardButton("✅ Participar desta rodada", callback_data="clan_war_join")])
            else:
                keyboard.append([InlineKeyboardButton("❌ Sair da lista", callback_data="clan_war_leave")])

        keyboard.append([InlineKeyboardButton("👥 Ver inscritos", callback_data="clan_war_view")])

    elif phase == "ACTIVE":
        text += "\n🔥 <b>Guerra ativa!</b>\n"
        text += "⚠️ Somente inscritos nesta rodada podem caçar/atacar e pontuar.\n"
        keyboard.append([InlineKeyboardButton("👥 Ver inscritos", callback_data="clan_war_view")])

    else:
        text += "\nℹ️ Inscrição só pode ser feita durante <b>PREP</b>.\n"

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
        return _sid(user_id), pdata, None, False

    try:
        res = clan_manager.get_clan(clan_id)
        clan_data = await res if hasattr(res, "__await__") else res
    except Exception:
        clan_data = None

    if not clan_data:
        return _sid(user_id), pdata, None, False

    leader_id = _sid(clan_data.get("leader_id", "0"))
    is_leader = (_sid(user_id) == leader_id)

    members = [_sid(x) for x in clan_data.get("members", [])]
    if (not is_leader) and (_sid(user_id) not in members):
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

    return _sid(user_id), pdata, clan_data, is_leader


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

    # ✅ engine semanal: open_clan_registration() (sem args)
    res = await _engine_call("open_clan_registration")
    if not res.get("ok"):
        try:
            await query.answer("Não foi possível abrir a inscrição agora.", show_alert=True)
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

    # ✅ engine semanal: close_clan_registration() (sem args)
    res = await _engine_call("close_clan_registration")
    if not res.get("ok"):
        try:
            await query.answer("Não foi possível fechar a inscrição.", show_alert=True)
        except Exception:
            pass
        return

    try:
        await query.answer("Inscrição do clã fechada.", show_alert=True)
    except Exception:
        pass
    await show_clan_war_menu(update, context)


async def clan_war_register_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Registra o clã na guerra da semana (REGISTRATION_COL).
    """
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
            await query.answer("Apenas o líder pode inscrever o clã.", show_alert=True)
        except Exception:
            pass
        return

    clan_id = pdata.get("clan_id")
    res = await _engine_call("register_clan_for_war", clan_id)
    if not res.get("ok"):
        try:
            await query.answer("Não foi possível inscrever o clã agora.", show_alert=True)
        except Exception:
            pass
        return

    try:
        await query.answer("Clã inscrito na Guerra desta semana!", show_alert=True)
    except Exception:
        pass
    await show_clan_war_menu(update, context)


async def clan_war_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    # ✅ engine semanal: join_war_as_member(player_id, pdata, region_key, chat_id)
    region_key = pdata.get("current_location") or "reino_eldora"
    chat_id = None
    try:
        if query and query.message:
            chat_id = query.message.chat_id
    except Exception:
        chat_id = None

    res = await _engine_call("join_war_as_member", user_id, pdata, region_key, chat_id=chat_id)
    if not res.get("ok"):
        try:
            await query.answer("Não foi possível entrar na lista agora.", show_alert=True)
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

    user_id = get_current_player_id(update, context)
    if not user_id:
        return

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        return

    res = await _engine_call("leave_war_as_member", user_id, pdata)
    if not res.get("ok"):
        try:
            await query.answer("Não foi possível sair agora.", show_alert=True)
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

    # fallback: lista via presence (registered_players)
    rp = ui["registered_players"] or {}
    members = [pid for pid, cid in rp.items() if _sid(cid) == _sid(clan_id)]

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
# 6. ROTEADOR
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
