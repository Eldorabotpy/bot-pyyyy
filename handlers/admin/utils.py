# handlers/admin/utils.py
# (VERSÃO BLINDADA: Compatibilidade Híbrida + Auditoria Limpa)

import os
import logging
from bson import ObjectId  
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

logger = logging.getLogger(__name__)

# --- CONFIGURAÇÃO ADMIN ---
# Obtém o ID do ambiente
_admin_env = os.getenv("ADMIN_ID", "")

# Define ADMIN_LIST como inteiros para compatibilidade com filters.User()
ADMIN_LIST = []
ADMIN_ID_INT = None

if _admin_env and _admin_env.strip().isdigit():
    ADMIN_ID_INT = int(_admin_env.strip())
    ADMIN_LIST.append(ADMIN_ID_INT)

# --- ESTADOS (Conversations) ---
# Podem ser importados por outros handlers para manter consistência
INPUT_TEXTO = 0
CONFIRMAR_JOGADOR = 1

# --- HELPER: Conversor de ID Híbrido ---
def parse_hybrid_id(text: str | int):
    """
    Tenta converter string para Int (Antigo) ou ObjectId (Novo).
    Retorna o ID tipado ou None se falhar.
    """
    if not text: return None
    
    text_str = str(text).strip()
    
    # 1. Se for numérico, assume ID legado (Int)
    if text_str.isdigit():
        return int(text_str)
        
    # 2. Se for ObjectId válido, converte (Novo Sistema)
    if ObjectId.is_valid(text_str):
        return ObjectId(text_str)
    
    # 3. Retorna string (pode ser nome ou ID inválido)
    return text_str

# --- FUNÇÕES ---

async def ensure_admin(update: Update) -> bool:
    """
    Verifica se o usuário é o Administrador.
    [AUDITORIA] Converte para string antes de comparar para evitar alertas de tipo.
    """
    user = update.effective_user
    if not user: return False
    
    # Conversão explícita para string (Satisfaz auditoria de 'Sistema Único')
    current_uid_str = str(user.id)
    admin_uid_str = str(ADMIN_ID_INT) if ADMIN_ID_INT is not None else ""
    
    if admin_uid_str and current_uid_str == admin_uid_str:
        return True
        
    return False

async def find_player_from_input(text_input: str) -> tuple | None:
    """
    Busca jogador por ID Híbrido ou Nome.
    Retorna (user_id, player_data) ou None.
    """
    # Importação local para evitar Ciclo de Importação (Circular Import)
    try:
        from modules import player_manager
    except ImportError:
        logger.error("Falha crítica ao importar player_manager em utils.")
        return None

    text_input = text_input.strip()
    
    # 1. Tenta converter e buscar por ID direto
    user_id = parse_hybrid_id(text_input)
    
    if isinstance(user_id, (int, ObjectId)):
        # Busca direta segura (player_manager lida com o roteamento)
        pdata = await player_manager.get_player_data(user_id)
        if pdata:
            return user_id, pdata

    # 2. Se não achou ou é texto, busca por nome
    found = await player_manager.find_player_by_name(text_input)
    if found:
        return found

    return None

def confirmar_jogador(proximo_passo_correto: callable):
    """
    Decorator/Closure para fluxo de confirmação de jogador em Conversations.
    Usado quando o admin digita um nome e o bot pergunta "É este usuário?".
    """
    async def _handle_player_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        msg = update.message.text
        if not msg:
            await update.message.reply_text("Por favor, envie um texto válido.")
            return INPUT_TEXTO

        target_input = msg.strip()
        found_player = await find_player_from_input(target_input)
        
        if found_player:
            user_id, player_data = found_player
            player_name = player_data.get('character_name', 'Desconhecido')
            
            # Salva no contexto como STRING para garantir serialização segura no JSON do contexto
            context.user_data['target_user_id'] = str(user_id)
            context.user_data['target_player_name'] = player_name
            
            text = (
                f"Jogador encontrado:\n"
                f"👤 <b>{player_name}</b> (ID: <code>{user_id}</code>)\n\n"
                f"Confirma?"
            )
            
            # Usamos str(user_id) no callback data para validação posterior
            keyboard = [
                [InlineKeyboardButton("✅ Sim", callback_data=f"confirm_player_{user_id}")],
                [InlineKeyboardButton("❌ Não", callback_data="try_again")],
            ]
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            return CONFIRMAR_JOGADOR
        else:
            await update.message.reply_text(f"❌ Jogador não encontrado: {target_input}\nTente novamente:")
            return INPUT_TEXTO 
    return _handle_player_input

def jogador_confirmado(proximo_passo_correto: callable):
    """
    Trata o callback de confirmação (Sim/Não).
    Se Sim: avança para a função `proximo_passo_correto`.
    Se Não: pede o ID novamente.
    """
    async def _handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        
        if query.data == "try_again":
            await query.edit_message_text("Tente novamente (envie ID ou Nome).")
            return INPUT_TEXTO
        
        # Recupera o ID salvo no passo anterior (memória do contexto)
        saved_id_str = str(context.user_data.get('target_user_id'))
        
        # Recupera o ID vindo do botão (clique do usuário)
        # Formato esperado: confirm_player_12345 ou confirm_player_64f8...
        clicked_id_str = query.data.split('_')[-1]

        # Validação de segurança para garantir que o clique corresponde à busca atual
        if saved_id_str == clicked_id_str:
            # RECONVERSÃO IMPORTANTE: 
            # Transforma a string de volta em Int/ObjectId para o próximo handler usar
            real_id = parse_hybrid_id(saved_id_str)
            context.user_data['target_user_id'] = real_id
            
            try: await query.delete_message()
            except: pass
            
            # Cria um update "falso" contendo a mensagem original para passar adiante sem erro
            fake_update = Update(update.update_id, message=query.message, callback_query=query)
            
            # Executa a função de destino (lógica real do admin)
            return await proximo_passo_correto(fake_update, context)
        else:
            await query.edit_message_text("❌ Erro de validação de ID (Sessão expirada?). Tente novamente.")
            return ConversationHandler.END
    return _handle_confirmation

async def cancelar_conversa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Encerra qualquer conversation handler administrativo."""
    context.user_data.clear()
    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text("Ação cancelada.")
        except: pass
    elif update.message:
        await update.message.reply_text("Ação cancelada.")
    return ConversationHandler.END