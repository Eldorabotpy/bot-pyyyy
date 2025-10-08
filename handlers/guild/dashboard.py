# handlers/guild/dashboard.py

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, clan_manager
from modules.game_data.clans import CLAN_PRESTIGE_LEVELS
from ..utils import create_progress_bar
from handlers.menu.kingdom import show_kingdom_menu 

# Importações das suas outras funcionalidades
from handlers.guild.missions import show_guild_mission_details
from handlers.guild.bank import show_clan_bank_menu
from handlers.guild.management import show_clan_management_menu

logger = logging.getLogger(__name__)

# --- Funções de Exibição ---

# ✅ 1. A FUNÇÃO AGORA ACEITA O NOVO PARÂMETRO 'came_from'
async def show_clan_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE, came_from: str = "kingdom"):
    """Mostra o painel principal do clã, com botão Voltar dinâmico."""
    query = update.callback_query
    user_id = update.effective_user.id
    player_data = player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")
    clan_data = clan_manager.get_clan(clan_id)

    if not clan_data:
        await query.answer("Você não está em um clã.", show_alert=True)
        return

    # Construção da mensagem (o seu código original)
    clan_name = clan_data.get('display_name', 'Nome do Clã')
    level = clan_data.get('prestige_level', 1)
    members_count = len(clan_data.get('members', []))
    level_info = CLAN_PRESTIGE_LEVELS.get(level, {})
    max_members = level_info.get('max_members', 5)
    mission = clan_manager.get_active_guild_mission(clan_id)
    mission_line = "Nenhuma missão ativa."
    if mission:
        progress = mission.get('current_progress', 0)
        target = mission.get('target_count', 1)
        mission_title = mission.get('title', 'Missão')
        mission_line = f"▫️ {mission_title}: [{progress}/{target}]"
    members_list_str = ""
    for member_id in clan_data.get("members", []):
        member_data = player_manager.get_player_data(member_id)
        if member_data:
            member_name = member_data.get("character_name", f"ID:{member_id}")
            members_list_str += f"   - {member_name}\n"
    text = (
        f"⚜️ <b>Painel do Clã: {clan_name}</b> ⚜️\n\n"
        f"<b>Nível:</b> {level}\n"
        f"<b>Membros:</b> {members_count}/{max_members}\n\n"
        f"<b>Missão do Clã Ativa:</b>\n{mission_line}\n\n"
        f"<b>Membros do Clã:</b>\n"
        f"{members_list_str}"
    )

    # ✅ 2. LÓGICA PARA DECIDIR O DESTINO DO BOTÃO "VOLTAR"
    if came_from == 'profile':
        # Se veio do perfil, o botão "Voltar" deve ter o callback 'profile'
        back_callback = 'profile'
    else:
        # Em todos os outros casos, o "Voltar" vai para o reino
        back_callback = 'clan_back_to_kingdom'

    # --- Construção do Teclado ---
    keyboard = [
        [InlineKeyboardButton("📜 Ver Detalhes da Missão", callback_data="clan_mission_details")],
        [InlineKeyboardButton("🏦 Banco do Clã", callback_data="clan_bank_menu")],
        [InlineKeyboardButton("👑 Gerir Clã", callback_data="clan_manage_menu")],
        [InlineKeyboardButton("🚪 Sair do Clã", callback_data="clan_leave_confirm")],
        # ✅ 3. O BOTÃO "VOLTAR" AGORA USA O CALLBACK DINÂMICO
        [InlineKeyboardButton("⬅️ Voltar", callback_data=back_callback)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await query.delete_message()
    except Exception as e:
        logger.debug(f"Não foi possível apagar a mensagem anterior: {e}")
    
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def show_leave_clan_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    text = "Tem a certeza que deseja sair do seu clã? Esta ação não pode ser desfeita."
    keyboard = [[
        InlineKeyboardButton("✅ Sim, desejo sair", callback_data="clan_leave_do"),
        InlineKeyboardButton("❌ Não, quero ficar", callback_data="clan_menu")
    ]]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

async def do_leave_clan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    player_data = player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")

    if not clan_id:
        await query.edit_message_text("Você já não está em um clã.")
        return
        
    try:
        clan_name = clan_manager.get_clan(clan_id).get("display_name")
        clan_manager.remove_member(clan_id, user_id)
        player_data["clan_id"] = None
        player_manager.save_player_data(user_id, player_data)
        await query.edit_message_text(f"Você saiu do clã '{clan_name}'.")
    except ValueError as e:
        await context.bot.answer_callback_query(query.id, str(e), show_alert=True)
        await show_clan_dashboard(update, context)

# --- FUNÇÃO ROUTER FINAL E CORRETA ---
async def clan_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe todos os callbacks que começam com 'clan_' e direciona para a função correta."""
    query = update.callback_query
    await query.answer()

    action = query.data

    if action == 'clan_menu':
        await show_clan_dashboard(update, context)
    elif action == 'clan_leave_confirm':
        await show_leave_clan_confirm(update, context)
    elif action == 'clan_leave_do':
        await do_leave_clan_callback(update, context)
    elif action == 'clan_back_to_kingdom':
        await show_kingdom_menu(update, context)
    
    # ✅ CHAMADAS FINAIS E CORRETAS
    elif action == 'clan_mission_details':
        await show_guild_mission_details(update, context)
    elif action == 'clan_bank_menu':
        await show_clan_bank_menu(update, context)
    elif action == 'clan_manage_menu':
        await show_clan_management_menu(update, context)
    
# --- UM ÚNICO HANDLER EFICIENTE ---
clan_handler = CallbackQueryHandler(clan_router, pattern=r'^clan_')