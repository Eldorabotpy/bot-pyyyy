# handlers/admin/utils.py
import os
import sys
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from modules import player_manager

logger = logging.getLogger(__name__)

# --- 1. DEFINIÇÃO CENTRAL DE ADMIN ---
admin_id_str = os.getenv("ADMIN_ID")
ADMIN_ID = None

if not admin_id_str:
    logging.critical("A variável de ambiente ADMIN_ID não foi definida! O bot não pode iniciar sem ela.")
    sys.exit("ERRO: ADMIN_ID não definido.")
try:
    ADMIN_ID = int(admin_id_str)
except (ValueError, TypeError):
    logging.critical(f"O valor de ADMIN_ID ('{admin_id_str}') não é um número válido!")
    sys.exit("ERRO: ADMIN_ID inválido.")

# --- 👇 ADICIONADO: Define a ADMIN_LIST aqui, uma vez ---
ADMIN_LIST = [ADMIN_ID]
# (Se você voltar a usar a ADMIN_LIST do config.py, pode mudar aqui)

# --- 2. ESTADOS DE CONVERSA (Centralizados) ---
INPUT_TEXTO = 0
CONFIRMAR_JOGADOR = 1
# (Pode adicionar mais estados aqui se precisar, ex: ASK_QUANTITY = 2)

# --- 3. FUNÇÕES DE ADMIN (As suas funções originais) ---
async def ensure_admin(update: Update) -> bool:
    """Verifica se o usuário é o admin (usando ADMIN_ID central)"""
    uid = update.effective_user.id if update.effective_user else None

    if ADMIN_ID and uid != ADMIN_ID:
        q = getattr(update, "callback_query", None)
        if q:
            await q.answer("Somente ADMIN pode usar esta função.", show_alert=True)
        elif update.effective_chat:
            await update.effective_chat.send_message("Somente ADMIN pode usar esta função.")
        return False

    return True

async def find_player_from_input(text_input: str) -> tuple | None:
    """
    Encontra um jogador a partir de um input de texto (ID ou Nome).
    Retorna (user_id, player_data) ou None.
    """
    text_input = text_input.strip()
    try:
        user_id = int(text_input)
        pdata = await player_manager.get_player_data(user_id)
        if pdata:
            return user_id, pdata
    except ValueError:
        found = await player_manager.find_player_by_name(text_input)
        if found:
            return found

    return None

# --- 4. FUNÇÕES DE CONVERSA (Que faltavam) ---

async def cancelar_conversa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a conversa atual e limpa os dados do utilizador."""
    context.user_data.clear()
    
    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text("Ação cancelada.")
        except Exception:
            pass 
    else:
        await update.message.reply_text("Ação cancelada.")
        
    return ConversationHandler.END

def confirmar_jogador(proximo_passo_correto: callable):
    """Gera o handler para o estado INPUT_TEXTO."""
    async def _handle_player_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        target_input = update.message.text.strip()
        found_player = await find_player_from_input(target_input)
        
        if found_player:
            user_id, player_data = found_player
            player_name = player_data.get('character_name', 'Nome não encontrado')
            
            context.user_data['target_user_id'] = user_id
            context.user_data['target_player_name'] = player_name
            
            # Se encontrou por ID, avança direto
            if target_input.isdigit():
                return await proximo_passo_correto(update, context)
            
            # Se foi por nome, pede confirmação
            text = (
                f"Jogador encontrado pelo nome:\n"
                f"👤 <b>{player_name}</b> (ID: <code>{user_id}</code>)\n\n"
                f"É este o jogador correto?"
            )
            keyboard = [
                [InlineKeyboardButton("✅ Sim, este é o jogador", callback_data=f"confirm_player_{user_id}")],
                [InlineKeyboardButton("❌ Não, digitar novamente", callback_data="try_again")],
            ]
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            return CONFIRMAR_JOGADOR
        else:
            await update.message.reply_text(
                f"❌ Jogador não encontrado com o ID/Nome '<code>{target_input}</code>'.\n"
                "Tente novamente ou use /cancelar.",
                parse_mode="HTML"
            )
            return INPUT_TEXTO 

    return _handle_player_input

# Em: handlers/admin/utils.py

def jogador_confirmado(proximo_passo_correto: callable):
    """
    Gera o handler para o estado CONFIRMAR_JOGADOR.
    Verifica se o ID do botão corresponde ao ID guardado.
    """
    async def _handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.callback_query.answer()
        
        target_user_id = context.user_data.get('target_user_id')
        
        if update.callback_query.data == "try_again":
            await update.callback_query.edit_message_text(
                "Ação cancelada. Por favor, envie o ID ou Nome exato do personagem.",
                parse_mode="HTML"
            )
            return INPUT_TEXTO
        
        try:
            clicked_user_id = int(update.callback_query.data.split('_')[-1])
        except (ValueError, IndexError):
            await update.callback_query.edit_message_text("Erro no botão. Ação cancelada.")
            return ConversationHandler.END

        if target_user_id == clicked_user_id:
            # Simula uma nova mensagem (para que o próximo passo possa usar .reply_text)
            fake_update = Update(update_id=update.update_id, message=update.callback_query.message)
            
            # --- A LINHA QUE CAUSAVA O ERRO FOI REMOVIDA DAQUI ---
            
            await update.callback_query.delete_message() # Limpa a mensagem de confirmação
            
            # Chama o próximo passo (ex: ask_skill_id ou ask_skin_id)
            return await proximo_passo_correto(fake_update, context)
        else:
            await update.callback_query.edit_message_text("Erro de confirmação. Ação cancelada.")
            return ConversationHandler.END

    return _handle_confirmation
