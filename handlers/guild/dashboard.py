# handlers/guild/dashboard.py
# (VERSÃO CORRIGIDA: valida membresia para impedir "fantasmas" + remove import inexistente)
# + (NOVO) ABA "GUERRA DE CLÃS": líder abre inscrição, membros aderem (PREP), gating no engine.

import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputMediaPhoto, InputMediaAnimation, InputMediaVideo
)
from telegram.ext import ContextTypes, CallbackQueryHandler
from typing import Any, Dict, Optional, Tuple

from bson import ObjectId

from modules import player_manager, clan_manager
from modules import file_ids
from modules.game_data.clans import CLAN_PRESTIGE_LEVELS
from modules.auth_utils import get_current_player_id

# ✅ Engine Guerra de Clãs (compat)
from modules import clan_war_engine

logger = logging.getLogger(__name__)


# ==============================================================================
# 0. HELPERS / COMPAT
# ==============================================================================

def _sid(x: Any) -> str:
    try:
        return str(x)
    except Exception:
        return ""

def _phase_norm(x: Any) -> str:
    p = _sid(x).strip()
    return p.upper() if p else "IDLE"


def _norm_engine_result(res: Any) -> Dict[str, Any]:
    # Normaliza retornos do engine para {ok, reason, message, ...}
    if isinstance(res, dict):
        out = dict(res)
        if "ok" not in out:
            # Heurística: status do engine vem como {'season':..., 'state':...}
            if 'state' in out or 'season' in out:
                out['ok'] = True
            else:
                out['ok'] = bool(out.get('success', False))
        return out
    if isinstance(res, bool):
        return {"ok": res, "reason": None, "message": None}
    if isinstance(res, (tuple, list)) and res:
        ok = bool(res[0])
        msg = res[1] if len(res) >= 2 else None
        reason = res[2] if len(res) >= 3 else None
        return {"ok": ok, "message": msg, "reason": reason}
    return {"ok": False, "reason": "engine_error", "message": None}


async def _engine_call(fn_name: str, *args, **kwargs) -> Dict[str, Any]:
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

    # 3) sem args
    try:
        res = fn()
        if hasattr(res, "__await__"):
            res = await res
        return _norm_engine_result(res)
    except Exception as e:
        return {"ok": False, "reason": "engine_exception", "message": str(e)}


async def _safe_answer(query, text: str = "", show_alert: bool = False):
    if not query:
        return
    try:
        await query.answer(text, show_alert=show_alert)
    except Exception:
        pass


async def _show_loading_overlay(update: Update, context: ContextTypes.DEFAULT_TYPE, title: str, subtitle: str = ""):
    # Simula um popup de carregamento editando a mensagem atual
    query = update.callback_query
    if not query or not query.message:
        return

    txt = f"⏳ <b>{title}</b>"
    if subtitle:
        txt += f"\n\n<i>{subtitle}</i>"

    try:
        if query.message.photo or query.message.video or query.message.animation:
            await query.edit_message_caption(txt, parse_mode="HTML", reply_markup=None)
        else:
            await query.edit_message_text(txt, parse_mode="HTML", reply_markup=None)
    except Exception:
        pass


async def _is_clan_registered(clan_id: Any, season_id: str) -> bool:
    try:
        reg_col = getattr(clan_war_engine, "REGISTRATION_COL", None)
        if reg_col is None:
            return False
        # tenta ObjectId quando aplicável
        cid = clan_id
        if isinstance(clan_id, str) and ObjectId.is_valid(clan_id):
            cid = ObjectId(clan_id)
        doc = reg_col.find_one({"season_id": season_id, "clan_id": cid, "active": True})
        return bool(doc)
    except Exception:
        return False


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

    current_has_media = False
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
        # usuário está com clan_id preso, mas não é membro
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

    # Dados visuais
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
        # ✅ NOVO: Aba de evento do clã
        [InlineKeyboardButton("⚔️ Guerra de Clãs", callback_data="clan_war_menu")],
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

    ws = await _engine_call("get_war_status")

    season = ws.get("season", {}) or {}
    state = ws.get("state", {}) or {}

    # ---- fase (vem do engine)
    phase = state.get("phase", season.get("phase", "idle"))
    phase_u = _phase_norm(phase)

    # ✅ AQUI ESTÁ O FIX: inscrição aberta/fechada vem do SEASON.registration_open
    is_open = bool(season.get("registration_open", False))

    # season_id / rodada
    season_id = season.get("season_id") or season.get("war_id") or "-"
    war_id = season_id

    # inscritos (deriva de registered_players: player_id -> clan_id)
    registered_players = state.get("registered_players", {}) or {}
    clan_sid = str(clan_id)

    reg_members = []
    if isinstance(registered_players, dict):
        for pid, cid in registered_players.items():
            if str(cid) == clan_sid:
                reg_members.append(str(pid))

    reg_count = len(reg_members)

    # eu inscrito?
    me_registered = False
    if isinstance(registered_players, dict):
        me_registered = (str(registered_players.get(str(user_id))) == clan_sid)

    # clã registrado na rodada? (usa REGISTRATION_COL)
    clan_registered = await _is_clan_registered(str(clan_id), str(season_id))

    clan_name = clan_data.get("display_name", "Clã")

    text = (
        f"⚔️ <b>GUERRA DE CLÃS — {clan_name.upper()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>Rodada:</b> <code>{war_id}</code>\n"
        f"⏳ <b>Fase:</b> <b>{phase_u}</b>\n\n"
        f"📝 <b>Inscrição do Clã:</b> {'<b>ABERTA</b>' if is_open else '<b>FECHADA</b>'}\n"
        f"🏷️ <b>Clã:</b> {'<b>INSCRITO</b>' if clan_registered else '<b>NÃO INSCRITO</b>'}\n"
        f"👥 <b>Inscritos:</b> {reg_count}\n"
        f"✅ <b>Você:</b> {'INSCRITO' if me_registered else 'NÃO INSCRITO'}\n"
    )

    keyboard = []

    if phase_u == "PREP":
        # líder registra o clã na rodada
        if is_leader:
            if not clan_registered:
                keyboard.append([InlineKeyboardButton("🏷️ Inscrever Clã na Guerra", callback_data="clan_war_register_clan")])
            else:
                keyboard.append([InlineKeyboardButton("✅ Clã Inscrito na Guerra", callback_data="clan_noop")])

            # líder abre/fecha inscrição (global no engine)
            if not is_open:
                keyboard.append([InlineKeyboardButton("📝 Abrir inscrição do Clã", callback_data="clan_war_open")])
            else:
                keyboard.append([InlineKeyboardButton("🔒 Fechar inscrição do Clã", callback_data="clan_war_close")])

        # membro entra/sai (só se inscrição aberta e clã inscrito)
        if is_open:
            if not clan_registered:
                keyboard.append([InlineKeyboardButton("⛔ Clã ainda não inscrito", callback_data="clan_noop")])
            else:
                if not me_registered:
                    keyboard.append([InlineKeyboardButton("✅ Participar desta rodada", callback_data="clan_war_join")])
                else:
                    keyboard.append([InlineKeyboardButton("❌ Sair da lista", callback_data="clan_war_leave")])

        keyboard.append([InlineKeyboardButton("👥 Ver inscritos", callback_data="clan_war_view")])

    elif phase_u == "ACTIVE":
        text += "\n🔥 <b>Guerra ativa!</b>\n"
        text += "⚠️ Somente inscritos nesta rodada podem caçar/atacar e pontuar.\n"
        keyboard.append([InlineKeyboardButton("👥 Ver inscritos", callback_data="clan_war_view")])
    else:
        text += "\nℹ️ Inscrição só pode ser feita durante <b>PREP</b>.\n"

    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="clan_menu")])

    await _render_clan_screen(update, context, clan_data, text, keyboard)


async def _require_clan_leader(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[Dict[str, Any]], bool]:
    """
    Helper: valida sessão + clã + anti-fantasma. Retorna (user_id, player_data, clan_data, is_leader).
    """
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
        return None, None, None, False

    return str(user_id), pdata, clan_data, is_leader


async def clan_war_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    await _show_loading_overlay(update, context, "Processando...", "Aguarde")

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
    res = await _engine_call("open_clan_registration", clan_id, str(user_id))
    if not res.get("ok"):
        reason = res.get("reason", "erro")
        msg = "Não foi possível abrir."
        if reason == "registration_closed":
            msg = "Inscrições fechadas. Só abre durante PREP."
        elif reason == "no_war_scheduled":
            msg = "Nenhuma guerra programada."
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

    await _show_loading_overlay(update, context, "Processando...", "Aguarde")

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




async def clan_war_register_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    await _show_loading_overlay(update, context, "Inscrevendo clã na rodada...", "Aguarde")

    user_id, pdata, clan_data, is_leader = await _require_clan_leader(update, context)
    if not user_id or not pdata or not clan_data:
        return

    if not is_leader:
        await _safe_answer(query, "Apenas o líder pode inscrever o clã.", show_alert=True)
        await show_clan_war_menu(update, context)
        return

    clan_id = pdata.get("clan_id")
    res = await _engine_call("register_clan_for_war", clan_id)
    if not res.get("ok"):
        msg = res.get("message") or "Não foi possível inscrever o clã agora."
        await _safe_answer(query, msg, show_alert=True)
        await show_clan_war_menu(update, context)
        return

    await _safe_answer(query, res.get("message") or "✅ Clã inscrito na Guerra!", show_alert=True)
    await show_clan_war_menu(update, context)

async def clan_war_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    # ✅ modal de carregamento (em vez de toast silencioso)
    await _show_loading_overlay(update, context, '⏳ Processando sua inscrição...', 'Aguarde')

    user_id = get_current_player_id(update, context)
    if not user_id:
        try:
            await query.answer('Sessão inválida.', show_alert=True)
        except Exception:
            pass
        return

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        try:
            await query.answer('Perfil não encontrado.', show_alert=True)
        except Exception:
            pass
        return

    region_key = pdata.get('current_location') or 'reino_eldora'

    chat_id = None
    try:
        if query.message:
            chat_id = query.message.chat_id
    except Exception:
        chat_id = None

    res = await _engine_call('join_war_as_member', user_id, pdata, region_key, chat_id=chat_id)
    if not res.get('ok'):
        msg = res.get('message') or 'Não foi possível participar agora.'
        try:
            await query.answer(msg, show_alert=True)
        except Exception:
            pass
        # volta para o menu para o usuário não ficar preso no loading
        await show_clan_war_menu(update, context)
        return

    # confirma e re-renderiza
    try:
        await query.answer(res.get('message') or '✅ Você foi inscrito na Guerra de Clãs!', show_alert=True)
    except Exception:
        pass

    await show_clan_war_menu(update, context)


async def clan_war_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    await _show_loading_overlay(update, context, "Removendo você da lista...", "Aguarde")

    user_id, pdata, clan_data, _is_leader = await _require_clan_leader(update, context)
    if not user_id or not pdata or not clan_data:
        return

    clan_id = str(pdata.get("clan_id"))
    res = await _engine_call("leave_war_as_member", user_id, pdata)

    if not res.get("ok"):
        reason = res.get("reason", "erro")
        msg = "Não foi possível sair."
        if reason == "registration_closed":
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

    # Carrega clã (para logo + validações)
    try:
        res = clan_manager.get_clan(clan_id)
        clan_data = await res if hasattr(res, "__await__") else res
    except Exception:
        clan_data = None

    if not clan_data:
        await show_clan_dashboard(update, context)
        return

    # Estado da guerra
    ws = await _engine_call("get_war_status")
    state = ws.get("state", {}) or {}

    war_id = state.get("war_id", "-")
    phase = state.get("phase", "idle")
    phase_u = _phase_norm(phase)  # ✅ FIX DEFINITIVO

    # Inscrições
    reg_by_clan = state.get("registrations_by_clan", {}) or {}
    reg = reg_by_clan.get(str(clan_id), {}) if isinstance(reg_by_clan, dict) else {}
    members = (
        reg.get("members", [])
        if isinstance(reg, dict) and isinstance(reg.get("members"), list)
        else []
    )

    # Lista (limite visual)
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
        f"🆔 <b>Rodada:</b> <code>{war_id}</code>\n"
        f"⏳ <b>Fase:</b> <b>{phase_u}</b>\n\n"
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
    action = query.data

    # ✅ IMPORT CORRIGIDO: removido show_kick_member_menu (não existe)
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
        try:
            await query.answer("Nada a fazer aqui.", show_alert=False)
        except Exception:
            pass
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

    try:
        await query.answer("Opção não encontrada.", show_alert=True)
    except Exception:
        pass


# Handler principal do clã (router)
clan_handler = CallbackQueryHandler(
    clan_router,
    pattern=r"^clan_|^gld_|^clan_menu$"
)
