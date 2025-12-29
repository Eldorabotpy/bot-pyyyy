# handlers/start_handler.py
# (VERSÃO REFATORADA PARA AUTH SYSTEM)

import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from handlers.menu.kingdom import show_kingdom_menu
from handlers.menu.region import show_region_menu
from modules import player_manager

# Tenta importar o banco para converter ID (caso necessário)
try:
    from bson import ObjectId
except ImportError:
    ObjectId = None

logger = logging.getLogger(__name__)

# ==============================================================================
# COMANDO /START (Versão Pós-Auth)
# ==============================================================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Agora o /start serve apenas para abrir o menu SE o jogador estiver logado.
    Se não estiver logado, o auth_handler (que roda antes) já terá capturado.
    """
    if not update.message: return
    
    # 1. PEGA O ID DA SESSÃO (Não mais o do Telegram)
    session_id = context.user_data.get("logged_player_id")
    
    # Se não tem sessão, ignoramos (o auth_handler deve lidar com o login)
    # ou mandamos um aviso amigável.
    if not session_id:
        await update.message.reply_text("⚠️ Você não está logado. Use /login ou crie uma conta.")
        return

    logger.info("[START] Abrindo menu para Sessão ID=%s", session_id)

    # 2. CARREGA DADOS DO JOGADOR
    # Nota: Precisaremos atualizar o player_manager.get_player_data para aceitar esse ID
    # Por enquanto, passamos o session_id.
    try:
        # Se session_id for string, converte para ObjectId se seu banco usar ObjectId
        # Se seu player_manager esperar string, mande string.
        lookup_id = ObjectId(session_id) if ObjectId else session_id
        
        player_data = await player_manager.get_player_data(lookup_id)
    except Exception as e:
        logger.error(f"Erro ao converter ID: {e}")
        return

    if not player_data:
        await update.message.reply_text("❌ Erro: Dados da conta não encontrados. Tente relogar: /start")
        context.user_data.clear() # Limpa sessão quebrada
        return

    # 3. ATUALIZA CHAT ID
    # Importante para notificações chegarem no lugar certo
    try:
        if "user_id" in player_data:
            # Se o documento tiver o ID antigo ou novo, tentamos atualizar
            await player_manager.set_last_chat_id(player_data["user_id"], update.effective_chat.id)
    except Exception:
        pass

    # 4. ABRE O MENU DO JOGO
    await update.message.reply_text("🎒 Abrindo seu menu...")
    await resume_game_state(update, context, player_data)

# ==============================================================================
# FUNÇÃO DE RESUMO (Menu)
# ==============================================================================
async def resume_game_state(update: Update, context: ContextTypes.DEFAULT_TYPE, player_data: dict):
    """Direciona para o Menu do Reino ou Região."""
    try:
        current_location = player_data.get('current_location', 'reino_eldora')
        
        if current_location == 'reino_eldora':
            await show_kingdom_menu(update, context, player_data=player_data) 
        else:
            await show_region_menu(update, context, region_key=current_location) 
            
    except Exception as e:
        logger.error("Erro abrindo menu: %s", e, exc_info=True)
        await update.message.reply_text("⚠️ Erro ao abrir o menu.")

# ==============================================================================
# REGISTRO
# ==============================================================================
# Removemos handlers de texto (handle_character_creation) pois não existem mais.
# Removemos /nome pois o nome é definido no registro.

start_command_handler = CommandHandler("menu", start_command) 
# Mudei para /menu para não conflitar com o /start do Auth, 
# mas você pode adicionar "start" aqui também se quiser redundância.
start_fallback_handler = CommandHandler("start", start_command)