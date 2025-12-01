# handlers/guild/dashboard.py
# (VERSÃO FINAL: CORREÇÃO DE IMPORTAÇÃO DOS NOMES DE SAIR)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaAnimation, InputMediaVideo
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

from modules import player_manager, clan_manager
from modules import file_ids 
from modules.game_data.clans import CLAN_PRESTIGE_LEVELS

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

    # Tenta determinar se a mensagem atual tem mídia
    current_has_media = False
    if query.message:
        current_has_media = bool(query.message.photo or query.message.video or query.message.animation)

    # Lógica de Decisão: Deletar e Reenviar se os tipos forem incompatíveis
    must_delete_resend = False
    
    # Se não tinha mídia e agora tem (ou vice versa), ou se trocou o tipo de mídia
    if target_has_media != current_has_media:
        must_delete_resend = True
    elif target_has_media:
        # Se mudou de foto para vídeo ou vice-versa, é mais seguro reenviar
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
            # Se a edição falhar, cai no fallback
            must_delete_resend = True

    # Fallback: Deletar e Reenviar
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
# 2. DASHBOARD
# ==============================================================================
async def show_clan_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE, came_from: str = "kingdom"):
    query = update.callback_query
    try: await query.answer()
    except: pass
    
    user_id = update.effective_user.id
    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return
    clan_id = player_data.get("clan_id")
    
    try:
        res = clan_manager.get_clan(clan_id)
        clan_data = await res if hasattr(res, '__await__') else res
    except: clan_data = None

    if not clan_data:
        try: await query.edit_message_text("Você não está em um clã.")
        except: pass
        return

    # Dados
    clan_name = clan_data.get('display_name', 'Clã')
    level = clan_data.get('prestige_level', 1)
    xp = clan_data.get('prestige_points', 0)
    
    # DEBUG: Garante que is_leader seja calculado corretamente
    leader_id = str(clan_data.get("leader_id", 0))
    is_leader = (str(user_id) == leader_id)

    # CORREÇÃO DA BARRA DE PROGRESSO E XP NECESSÁRIO
    # Pega os dados do nível ATUAL para saber quanto falta para completar
    current_level_info = CLAN_PRESTIGE_LEVELS.get(level, {})
    xp_needed = current_level_info.get("points_to_next_level", 999999)
    
    # Prevenção contra divisão por zero ou None
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

    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="adventurer_guild_main")])

    await _render_clan_screen(update, context, clan_data, text, keyboard)
# ==============================================================================
# 3. ROTEADOR (CORRIGIDO PARA ACEITAR O BOTÃO DA GESTÃO)
# ==============================================================================
async def clan_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action = query.data
    
    # Importação Tardia
    from handlers.guild.management import (
        show_clan_management_menu, show_members_list, show_kick_member_menu,
        warn_kick_member, do_kick_member, warn_leave_clan, do_leave_clan
    )
    
    try:
        from handlers.guild.missions import show_guild_mission_details
        from handlers.guild.bank import show_clan_bank_menu
        from handlers.guild.upgrades import show_clan_upgrade_menu 
    except ImportError: pass
    
    came_from = "kingdom"
    if ":" in action:
         try: action, came_from = action.split(":", 1)
         except: action = action.split(":", 1)[0]
             
    if action == 'clan_menu': await show_clan_dashboard(update, context, came_from=came_from) 
    
    # --- Ações de Sair ---
    elif action == 'clan_leave_ask': await warn_leave_clan(update, context)
    elif action == 'clan_leave_perform': await do_leave_clan(update, context)
    
    # --- Navegação ---
    elif action == 'clan_back_to_kingdom': await query.edit_message_text("Retornando ao reino...", reply_markup=None)
    elif action == 'clan_mission_details': await show_guild_mission_details(update, context)
    elif action == 'clan_bank_menu': await show_clan_bank_menu(update, context)
    elif action == 'clan_manage_menu': await show_clan_management_menu(update, context)
    
    # --- CORREÇÃO AQUI: Aceita OS DOIS tipos de botões de membros ---
    elif action == 'gld_view_members': await show_members_list(update, context)  # Botão do Painel Principal
    elif action == 'clan_view_members': await show_members_list(update, context) # Botão do Menu de Gestão
    
    # --- Gestão de Membros ---
    elif action == 'clan_kick_menu': await show_kick_member_menu(update, context)
    elif action == 'clan_kick_ask': await warn_kick_member(update, context)
    elif action == 'clan_kick_do': await do_kick_member(update, context)
    
    elif action == 'clan_upgrade_menu': 
        try: await show_clan_upgrade_menu(update, context)
        except: await query.answer("Em breve!", show_alert=True)
        
    else:
        try: await query.answer("Opção não encontrada.", show_alert=True)
        except: pass

# Regex atualizado para pegar os dois tipos de botões
clan_handler = CallbackQueryHandler(clan_router, pattern=r'^clan_|^gld_view_members')