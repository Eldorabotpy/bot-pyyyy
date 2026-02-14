# handlers/start_handler.py
# (VERSÃO BLINDADA 4.4 - Sem Tutorial)

import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ParseMode

from handlers.menu.kingdom import show_kingdom_menu
from handlers.menu.region import show_region_menu

from modules import player_manager
from modules.auth_utils import requires_login
from modules.player.account_lock import check_account_lock

logger = logging.getLogger(__name__)


# ==============================================================================
# COMANDO /MENU e /START (Protegido)
# ==============================================================================
@requires_login
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Abre o menu principal. O decorator @requires_login garante que o jogador
    está autenticado. Se não estiver, exibe o botão de login automaticamente.
    """
    if not update.message:
        return

    # Se passou pelo decorator, logged_player_id existe.
    session_id = context.user_data["logged_player_id"]
    logger.info("[START] Menu solicitado por Sessão ID=%s", session_id)

    # Carrega dados do jogador
    try:
        player_data = await player_manager.get_player_data(session_id)
        if not player_data:
            await update.message.reply_text("❌ Conta não encontrada no banco de dados. Use /login.")
            return
    except Exception as e:
        logger.error(f"Erro ao carregar dados em /start: {e}")
        await update.message.reply_text("❌ Erro interno ao acessar os dados da conta.")
        return

    # ===============================
    # 2. VERIFICAÇÃO DE BLOQUEIO DE CONTA
    # ===============================
    locked, lock_msg = check_account_lock(player_data)

    # Persistir auto-unlock (se o lock expirou e foi removido)
    if not locked and "account_lock" not in player_data:
        try:
            await player_manager.save_player_data(player_data["_id"], player_data)
        except Exception:
            pass

    if locked:
        await update.message.reply_text(lock_msg, parse_mode=ParseMode.HTML)
        return

    # Sem tutorial: Vai direto para o jogo
    await resume_game_state(update, context, player_data)


async def resume_game_state(update: Update, context: ContextTypes.DEFAULT_TYPE, player_data: dict):
    """Direciona para o Menu do Reino ou Região."""
    try:
        current_location = player_data.get("current_location", "reino_eldora")

        if current_location == "reino_eldora":
            await show_kingdom_menu(update, context, player_data=player_data)
        else:
            await show_region_menu(update, context, region_key=current_location)

    except Exception as e:
        logger.error(f"[START] Erro ao retomar estado: {e}")
        await update.message.reply_text("Ocorreu um erro ao carregar o menu. Tente novamente.")
        
start_command_handler = CommandHandler(['start', 'menu'], start_command)