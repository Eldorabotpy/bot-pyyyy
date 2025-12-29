# handlers/admin/utils.py
import os
import sys
import logging
from bson import ObjectId  
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from modules import player_manager

logger = logging.getLogger(__name__)

# --- CONFIGURAÇÃO ADMIN ---
admin_id_str = os.getenv("ADMIN_ID")
ADMIN_ID = None

if not admin_id_str:
    logging.critical("ADMIN_ID não definido!")
    # sys.exit pode ser drástico demais em alguns ambientes, cuidado
    # sys.exit("ERRO: ADMIN_ID não definido.") 
else:
    try:
        ADMIN_ID = int(admin_id_str)
    except ValueError:
        logging.critical("ADMIN_ID inválido!")

ADMIN_LIST = [ADMIN_ID] if ADMIN_ID else []

# --- ESTADOS ---
INPUT_TEXTO = 0
CONFIRMAR_JOGADOR = 1

# --- HELPER: Conversor de ID Híbrido ---
def parse_hybrid_id(text: str):
    """
    Tenta converter string para Int (Antigo) ou ObjectId (Novo).
    Retorna o ID tipado ou a string original se falhar.
    """
    text = str(text).strip()
    if text.isdigit():
        return int(text)
    if ObjectId.is_valid(text):
        return ObjectId(text)
    return text

# --- FUNÇÕES ---
async def ensure_admin(update: Update) -> bool:
    uid = update.effective_user.id if update.effective_user else None
    if ADMIN_ID and uid != ADMIN_ID:
        # Lógica de rejeição
        return False
    return True

async def find_player_from_input(text_input: str) -> tuple | None:
    text_input = text_input.strip()
    
    # Tenta usar o conversor híbrido
    user_id = parse_hybrid_id(text_input)
    
    # Se o conversor retornou Int ou ObjectId, busca direto pelo ID
    if isinstance(user_id, (int, ObjectId)):
        pdata = await player_manager.get_player_data(user_id)
        if pdata:
            return user_id, pdata

    # Se não achou ou não é ID, busca por nome
    found = await player_manager.find_player_by_name(text_input)
    if found:
        return found

    return None

def confirmar_jogador(proximo_passo_correto: callable):
    async def _handle_player_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        target_input = update.message.text.strip()
        found_player = await find_player_from_input(target_input)
        
        if found_player:
            user_id, player_data = found_player
            player_name = player_data.get('character_name', 'Nome não encontrado')
            
            # ATENÇÃO: Convertemos para string para salvar no user_data, 
            # mas teremos que reconverter depois
            context.user_data['target_user_id'] = str(user_id)
            context.user_data['target_player_name'] = player_name
            
            # Se for ID numérico ou ObjectId, pula confirmação se quiser, 
            # mas vamos manter fluxo padrão
            text = (
                f"Jogador encontrado:\n"
                f"👤 <b>{player_name}</b> (ID: <code>{user_id}</code>)\n\n"
                f"Confirma?"
            )
            keyboard = [
                # Usamos str(user_id) no botão
                [InlineKeyboardButton("✅ Sim", callback_data=f"confirm_player_{user_id}")],
                [InlineKeyboardButton("❌ Não", callback_data="try_again")],
            ]
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            return CONFIRMAR_JOGADOR
        else:
            await update.message.reply_text(f"❌ Jogador não encontrado: {target_input}")
            return INPUT_TEXTO 
    return _handle_player_input

def jogador_confirmado(proximo_passo_correto: callable):
    async def _handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        
        if query.data == "try_again":
            await query.edit_message_text("Tente novamente (envie ID ou Nome).")
            return INPUT_TEXTO
        
        # Recupera o ID salvo (que é string)
        saved_id_str = str(context.user_data.get('target_user_id'))
        
        # Recupera o ID do botão (que é string)
        clicked_id_str = query.data.split('_')[-1]

        if saved_id_str == clicked_id_str:
            # RECONVERSÃO IMPORTANTE:
            # Transforma a string de volta em Int ou ObjectId para o próximo passo usar
            real_id = parse_hybrid_id(saved_id_str)
            context.user_data['target_user_id'] = real_id
            
            try: await query.delete_message()
            except: pass
            
            # Simula update para o próximo passo
            fake_update = Update(update.update_id, message=query.message, callback_query=query)
            return await proximo_passo_correto(fake_update, context)
        else:
            await query.edit_message_text("Erro de validação de ID.")
            return ConversationHandler.END
    return _handle_confirmation

async def cancelar_conversa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text("Ação cancelada.")
        except: pass
    elif update.message:
        await update.message.reply_text("Ação cancelada.")
    return ConversationHandler.END
