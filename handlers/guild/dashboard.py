# handlers/guild/dashboard.py
# (VERSÃO CORRIGIDA: Captura o botão 'Guilda' do menu principal e faz o roteamento)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaAnimation, InputMediaVideo
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

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
    
    media_fid = None
    media_type = "photo"
    
    if clan_data.get("logo_media_key"):
        media_fid = clan_data.get("logo_media_key")
        media_type = clan_data.get("logo_type", "photo")
    
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
    if query.message:
        current_has_media = bool(query.message.photo or query.message.video or query.message.animation)

    must_delete_resend = False
    
    if target_has_media != current_has_media:
        must_delete_resend = True
    elif target_has_media:
        if media_type == "video" and not query.message.video: must_delete_resend = True
        elif media_type == "animation" and not query.message.animation: must_delete_resend = True
        elif media_type == "photo" and not query.message.photo: must_delete_resend = True

    if not must_delete_resend:
        try:
            if target_has_media:
                new_media = None
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
        except Exception as e:
            must_delete_resend = True

    if must_delete_resend:
        try: await query.delete_message()
        except: pass
        try:
            if media_fid:
                if media_type == "video":
                    await context.bot.send_video(query.message.chat_id, video=media_fid, caption=text, reply_markup=reply_markup, parse_mode="HTML")
                elif media_type == "animation":
                    await context.bot.send_animation(query.message.chat_id, animation=media_fid, caption=text, reply_markup=reply_markup, parse_mode="HTML")
                else:
                    await context.bot.send_photo(query.message.chat_id, photo=media_fid, caption=text, reply_markup=reply_markup, parse_mode="HTML")
            else:
                await context.bot.send_message(query.message.chat_id, text, reply_markup=reply_markup, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Erro fatal rendering clan dashboard: {e}")

# ==============================================================================
# 2. ENTRY POINT (ROTEADOR DE ENTRADA) - AQUI ESTÁ A CORREÇÃO PRINCIPAL
# ==============================================================================
async def adventurer_guild_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Função principal chamada pelo botão 'Guilda' do Reino.
    Decide se mostra o Dashboard (tem clã) ou Menu de Criação (sem clã).
    """
    query = update.callback_query
    
    # 1. Autenticação
    user_id = get_current_player_id(update, context)
    if not user_id:
        if query: await query.answer("Sessão inválida.", show_alert=True)
        return

    # 2. Verifica dados do jogador
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        if query: await query.answer("Perfil não encontrado.", show_alert=True)
        return

    # 3. Verifica se tem Clã
    clan_id = player_data.get("clan_id")
    
    if clan_id:
        # --> Tem clã: Mostra Dashboard
        await show_clan_dashboard(update, context)
    else:
        # --> Não tem clã: Mostra Menu de Criação/Busca
        # Importação tardia para evitar Circular Import com creation_search.py
        try:
            from handlers.guild.creation_search import show_create_clan_menu
            await show_create_clan_menu(update, context)
        except ImportError:
            await query.answer("Erro: Módulo de criação não encontrado.", show_alert=True)

# ==============================================================================
# 3. DASHBOARD
# ==============================================================================
async def show_clan_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE, came_from: str = "kingdom"):
    query = update.callback_query
    try: await query.answer()
    except: pass
    
    user_id = get_current_player_id(update, context)
    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return
    clan_id = player_data.get("clan_id")
    
    try:
        res = clan_manager.get_clan(clan_id)
        clan_data = await res if hasattr(res, '__await__') else res
    except: clan_data = None

    if not clan_data:
        # Fallback se o ID existe no player mas o clã sumiu do banco
        pdata = await player_manager.get_player_data(user_id)
        if pdata:
            pdata["clan_id"] = None
            await player_manager.save_player_data(user_id, pdata)
        
        # Redireciona para criação
        await adventurer_guild_menu(update, context)
        return

    # Dados
    clan_name = clan_data.get('display_name', 'Clã')
    level = clan_data.get('prestige_level', 1)
    xp = clan_data.get('prestige_points', 0)
    
    leader_id = str(clan_data.get("leader_id", 0))
    is_leader = (str(user_id) == leader_id)

    # Cálculo do XP
    current_level_info = CLAN_PRESTIGE_LEVELS.get(level, {})
    xp_needed = current_level_info.get("points_to_next_level", 999999)
    if not xp_needed: xp_needed = xp if xp > 0 else 1
    
    percent = min(1.0, max(0.0, xp / xp_needed))
    filled = int(percent * 10)
    bar = "🟦" * filled + "⬜" * (10 - filled)
    
    members_count = len(clan_data.get('members', []))
    max_members = current_level_info.get('max_members', 10)

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
        [InlineKeyboardButton("📜 Missões", callback_data="clan_mission_details"), InlineKeyboardButton("🏦 Banco", callback_data="clan_bank_menu")],
        [InlineKeyboardButton("👥 Membros", callback_data="gld_view_members"), InlineKeyboardButton("✨ Melhorias", callback_data="clan_upgrade_menu")]
    ]
    
    if is_leader:
        keyboard.append([InlineKeyboardButton("👑 Gerir Clã", callback_data="clan_manage_menu")])

    # Alterado para voltar ao menu principal do Reino
    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data="show_kingdom_menu")])

    await _render_clan_screen(update, context, clan_data, text, keyboard)


# ==============================================================================
# 4. ROTEADOR
# ==============================================================================
async def clan_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action = query.data
    
    # Imports Tardios
    from handlers.guild.management import (
        show_clan_management_menu, show_members_list, show_kick_member_menu,
        warn_kick_member, do_kick_member, warn_leave_clan, do_leave_clan
    )
    
    try:
        from handlers.guild.missions import (
            show_guild_mission_details, 
            finish_mission_callback, 
            cancel_mission_callback,
            show_mission_selection_menu,
            start_mission_callback
        )
        from handlers.guild.bank import show_clan_bank_menu
        from handlers.guild.upgrades import show_clan_upgrade_menu, confirm_clan_upgrade_callback 
    except ImportError: pass
    
    came_from = "kingdom"
    
    # --- ROTEAMENTO PRINCIPAL ---
    
    # 1. Botão "Guilda" do Menu Principal
    if action == 'adventurer_guild_main': 
        await adventurer_guild_menu(update, context)
        return

    # 2. Navegação Interna
    if action == 'clan_menu': 
        await show_clan_dashboard(update, context, came_from=came_from) 
    
    # --- MISSÕES ---
    elif action == 'clan_mission_details': await show_guild_mission_details(update, context)
    elif action == 'gld_mission_finish': await finish_mission_callback(update, context)
    elif action == 'gld_mission_cancel': await cancel_mission_callback(update, context)
    elif action == 'gld_mission_select_menu': await show_mission_selection_menu(update, context)
    elif action.startswith('gld_start_hunt'): await start_mission_callback(update, context)
    
    # --- SAIR ---
    elif action == 'clan_leave_ask': await warn_leave_clan(update, context)
    elif action == 'clan_leave_perform': await do_leave_clan(update, context)
    
    # --- BANCO E GESTÃO ---
    elif action == 'clan_bank_menu': await show_clan_bank_menu(update, context)
    elif action == 'clan_manage_menu': await show_clan_management_menu(update, context)
    elif action == 'gld_view_members': await show_members_list(update, context)
    elif action == 'clan_view_members': await show_members_list(update, context)
    
    # --- UPGRADE E KICK ---
    elif action == 'clan_kick_menu': await show_kick_member_menu(update, context)
    elif action.startswith('clan_kick_ask'): await warn_kick_member(update, context)
    elif action.startswith('clan_kick_do'): await do_kick_member(update, context)
    
    elif action == 'clan_upgrade_menu': 
        try: await show_clan_upgrade_menu(update, context)
        except: await query.answer("Em breve!", show_alert=True)
        
    elif action.startswith('clan_upgrade_confirm'):
        await confirm_clan_upgrade_callback(update, context)

    else:
        try: await query.answer("Opção não encontrada.", show_alert=True)
        except: pass

# Regex expandido para capturar o botão principal
clan_handler = CallbackQueryHandler(clan_router, pattern=r'^clan_|^gld_|^adventurer_guild_main$')
