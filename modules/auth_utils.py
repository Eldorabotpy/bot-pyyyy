# modules/auth_utils.py
from telegram import Update
from telegram.ext import ContextTypes

def get_current_player_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Retorna o ID correto do jogador (Sessão de Login ou ID do Telegram).
    """
    # 1. Tenta pegar da sessão (Login Novo)
    if context.user_data:
        session_id = context.user_data.get("logged_player_id")
        if session_id:
            return session_id

    # 2. Fallback: Retorna ID do Telegram (Para contas antigas ou Admin)
    return update.effective_user.id

def ensure_logged_in(func):
    """
    Decorator para proteger funções que exigem login.
    (Opcional, mas útil para o futuro)
    """
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = get_current_player_id(update, context)
        if not user_id:
            await update.message.reply_text("⚠️ Você não está logado. Use /start.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper
