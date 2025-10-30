# handlers/guild_handler.py (Versão Corrigida)

import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager

# --- Constantes de Estado ---
(
    ASKING_NAME, ASKING_INVITEE, ASKING_SEARCH_NAME, SHOWING_SEARCH_RESULT,
    ASKING_LEADER_TARGET, CONFIRM_LEADER_TRANSFER, ASKING_DEPOSIT_AMOUNT,
    ASKING_WITHDRAW_AMOUNT, ASKING_CLAN_LOGO,
) = range(9)


# --- Handlers de Menus Principais ---

async def guild_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    # <<< CORREÇÃO 1: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)

    if player_data is None: # Adiciona verificação para caso o jogador não exista
         # Informa o usuário e sai
         await query.edit_message_text("Erro ao carregar dados. Use /start.")
         return

    if player_data.get("clan_id"):
        from handlers.guild.dashboard import show_clan_dashboard
        # <<< CORREÇÃO 2: Adiciona await >>>
        await show_clan_dashboard(update, context)
    else:
        from handlers.guild.creation_search import show_create_clan_menu
        # <<< CORREÇÃO 3: Adiciona await >>>
        await show_create_clan_menu(update, context, came_from='guild_menu')

async def clan_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    # <<< CORREÇÃO 4: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)

    if player_data is None: # Adiciona verificação
         await query.edit_message_text("Erro ao carregar dados. Use /start.")
         return

    origem = 'guild_menu' # Valor padrão
    if ':' in query.data:
        try:
            origem = query.data.split(':')[1]
        except IndexError: pass

    if player_data.get("clan_id"):
        from handlers.guild.dashboard import show_clan_dashboard
        # <<< CORREÇÃO 5: Adiciona await >>>
        await show_clan_dashboard(update, context, came_from=origem)
    else:
        from handlers.guild.creation_search import show_create_clan_menu
        # <<< CORREÇÃO 6: Adiciona await >>>
        await show_create_clan_menu(update, context, came_from=origem)
        
# --- Handlers ---
guild_menu_handler = CallbackQueryHandler(guild_menu_callback, pattern=r'^guild_menu$')
clan_menu_handler = CallbackQueryHandler(clan_menu_callback, pattern=r"^clan_menu(:.*)?$")
noop_handler = CallbackQueryHandler(lambda u, c: c.bot.answer_callback_query(u.callback_query.id), pattern=r'^noop$')


# --- Importação e Agrupamento de Handlers ---
from handlers.guild.creation_search import (
    clan_creation_conv_handler, clan_search_conv_handler, clan_apply_handler,
    clan_manage_apps_handler, clan_app_accept_handler, clan_app_decline_handler,
)
from handlers.guild.dashboard import clan_handler
from handlers.guild.management import (
    clan_transfer_leader_conv_handler, clan_logo_conv_handler, clan_manage_menu_handler,
    clan_kick_menu_handler, clan_kick_confirm_handler, clan_kick_do_handler,
)
from handlers.guild.missions import (
    missions_menu_handler, mission_claim_handler, mission_reroll_handler,
    clan_mission_start_handler, clan_board_purchase_handler,
    clan_guild_mission_details_handler,
    clan_mission_details_handler,
    clan_mission_preview_handler,
    clan_mission_accept_handler,
)
from handlers.guild.bank import (
    clan_bank_menu_handler, 
    clan_deposit_conv_handler, 
    clan_withdraw_conv_handler,
    clan_bank_log_handler,
)

from handlers.guild.upgrades import (
    clan_upgrade_menu_handler, clan_upgrade_confirm_handler,
)

# --- Lista Final de Todos os Handlers ---
all_guild_handlers = [
    guild_menu_handler, clan_menu_handler, noop_handler,
    clan_creation_conv_handler, clan_search_conv_handler, clan_transfer_leader_conv_handler,
    clan_logo_conv_handler, clan_deposit_conv_handler, clan_withdraw_conv_handler,
    clan_apply_handler, clan_manage_apps_handler, clan_app_accept_handler,
    clan_app_decline_handler,
    clan_handler,
    clan_manage_menu_handler, clan_kick_menu_handler, clan_kick_confirm_handler,
    clan_kick_do_handler, missions_menu_handler, mission_claim_handler,
    mission_reroll_handler, clan_mission_start_handler,
    clan_board_purchase_handler, clan_guild_mission_details_handler,
    clan_bank_menu_handler, clan_upgrade_menu_handler, clan_upgrade_confirm_handler, clan_mission_details_handler,
    clan_bank_log_handler,
    clan_mission_preview_handler,
    clan_mission_accept_handler,
]