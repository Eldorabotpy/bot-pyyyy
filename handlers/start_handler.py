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
        # Captura TODOS os dados do Telegram do jogador
        user_name = update.effective_user.first_name or "Aventureiro"
        tg_username = update.effective_user.username or ""
        tg_id = update.effective_user.id

        # Passa os dados completos (contas novas já nascerão perfeitas aqui)
        player_data = await get_or_create_player(
            user_id=session_id, 
            default_name=user_name,
            username=tg_username,
            telegram_id=tg_id
        )
        
        if not player_data:
            await update.message.reply_text("❌ Falha crítica ao inicializar personagem.")
            return

        # ==========================================
        # 🛠️ AUTO-REPARO PARA CONTAS ANTIGAS BUGADAS
        # ==========================================
        needs_repair = False
        
        # 1. Conserta o ID do Telegram e Username ausentes
        if not player_data.get("telegram_id"):
            player_data["telegram_id"] = tg_id
            player_data["username"] = tg_username
            needs_repair = True
            
        # 2. Conserta as estruturas que quebravam o menu
        missing_keys = {
            "inventory": {}, "equipment": {}, "equipped_items": {}, 
            "skills": [], "equipped_skills": [], "invested": {},
            "profession": {}, "guild": None # <-- Mudado de None para {}
        }
        
        for key, default_value in missing_keys.items():
            if key not in player_data:
                player_data[key] = default_value
                needs_repair = True
                
        # Se a conta era "oca", salva o conserto no banco de dados silenciosamente
        if needs_repair:
            await player_manager.save_player_data(player_data["_id"], player_data)
            logger.info(f"[AUTO-REPARO] Conta {player_data['_id']} ({user_name}) consertada com sucesso!")

    except Exception as e:
        logger.error(f"Erro ao processar dados em /start: {e}")
        await update.message.reply_text("❌ Erro interno ao acessar os dados da conta.")
        return

    # Verificação de bloqueio
    locked, lock_msg = check_account_lock(player_data)

    if not locked and "account_lock" not in player_data:
        try:
            # Salva qualquer atualização de lock
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