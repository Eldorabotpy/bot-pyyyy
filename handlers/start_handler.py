# handlers/start_handler.py
# (VERSÃO CORRIGIDA - Auto-criação sem Dora)

import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ParseMode

from handlers.menu.kingdom import show_kingdom_menu
from handlers.menu.region import show_region_menu

# Importação necessária para garantir a criação do player
from modules.player.queries import get_or_create_player 
from modules import player_manager
from modules.auth_utils import requires_login
from modules.player.account_lock import check_account_lock

logger = logging.getLogger(__name__)

@requires_login
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    session_id = context.user_data["logged_player_id"]
    logger.info("[START] Menu solicitado por Sessão ID=%s", session_id)

    try:
        # Substitui a busca simples pela auto-criação inteligente
        user_name = update.effective_user.first_name or "Aventureiro"
        player_data = await get_or_create_player(session_id, user_name)
        
        if not player_data:
            await update.message.reply_text("❌ Falha crítica ao inicializar personagem.")
            return
            
    except Exception as e:
        logger.error(f"Erro ao processar dados em /start: {e}")
        await update.message.reply_text("❌ Erro interno ao acessar os dados da conta.")
        return

    # Verificação de bloqueio
    locked, lock_msg = check_account_lock(player_data)

    if not locked and "account_lock" not in player_data:
        try:
            await player_manager.save_player_data(player_data["_id"], player_data)
        except Exception:
            pass

    if locked:
        await update.message.reply_text(lock_msg, parse_mode=ParseMode.HTML)
        return

    # Redireciona para o estado atual do jogo
    await resume_game_state(update, context, player_data)

async def resume_game_state(update: Update, context: ContextTypes.DEFAULT_TYPE, player_data: dict):
    try:
        current_location = player_data.get("current_location", "reino_eldora")
        if current_location == "reino_eldora":
            await show_kingdom_menu(update, context, player_data=player_data)
        else:
            await show_region_menu(update, context, region_key=current_location)
    except Exception as e:
        logger.error(f"[START] Erro ao retomar estado: {e}")
        await update.message.reply_text("Erro ao carregar o menu. Tente /menu.")

start_command_handler = CommandHandler(['start', 'menu'], start_command) 