# handlers/guild/dashboard.py
# (VERSÃO CORRIGIDA: valida membresia para impedir "fantasmas" + remove import inexistente)

import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputMediaPhoto, InputMediaAnimation, InputMediaVideo
)
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, clan_manager
from modules import file_ids
from modules.game_data.clans import CLAN_PRESTIGE_LEVELS
from modules.auth_utils import get_current_player_id

logger = logging.getLogger(__name__)

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
         InlineKeyboardButton("✨ Melhorias", callback_data="clan_upgrade_menu")]
    ]

    if is_leader:
        keyboard.append([InlineKeyboardButton("👑 Gerir Clã", callback_data="clan_manage_menu")])

    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data="show_kingdom_menu")])

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

    if action == "clan_menu":
        await show_clan_dashboard(update, context)
        return

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
