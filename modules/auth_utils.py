# modules/auth_utils.py
# (VERSÃO ATUALIZADA: Com Middleware de verificação de Sessão)

import logging
from functools import wraps
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

def get_current_player_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Retorna o ID correto do jogador (Sessão de Login ou ID do Telegram).
    """
    # 1. Tenta pegar da sessão (Login Novo)
    if context.user_data:
        session_id = context.user_data.get("logged_player_id")
        if session_id:
            return str(session_id)

    # 2. Fallback: Retorna None (TOLERÂNCIA ZERO ativada)
    # Se não tiver sessão, não retornamos o ID do Telegram para evitar bugs de contas misturadas.
    return None

def requires_login(func):
    """
    Decorator: Coloque @requires_login em cima de qualquer função de botão (callback).
    Se o bot tiver reiniciado e perdido a sessão, ele avisa o usuário e pede login.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        # Verifica se tem o ID na sessão
        user_id = get_current_player_id(update, context)
        
        if not user_id:
            # --- SESSÃO PERDIDA / BOT REINICIADO ---
            
            # 1. Responde o "loading" do botão para parar de girar
            if update.callback_query:
                try:
                    await update.callback_query.answer("⚠️ Sessão expirada.", show_alert=True)
                except: pass

            # 2. Mensagem amigável explicativa
            msg_text = (
                "⚠️ <b>Sessão Expirada</b>\n\n"
                "O Reino de Eldora passou por uma manutenção mágica (o bot foi atualizado/reiniciado) "
                "e sua conexão foi encerrada por segurança.\n\n"
                "👇 <b>Clique abaixo para reconectar:</b>"
            )
            
            kb = [[InlineKeyboardButton("🔐 Reconectar / Login", callback_data="start_login_flow")]]
            
            # Envia a mensagem (ou edita se possível, mas enviar nova é melhor para chamar atenção)
            if update.effective_chat:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=msg_text,
                    reply_markup=InlineKeyboardMarkup(kb),
                    parse_mode="HTML"
                )
            
            # Interrompe a execução da função original (não tenta caçar/abrir inventário)
            return 
            
        # Se tiver logado, executa a função normal
        return await func(update, context, *args, **kwargs)
    
    return wrapper