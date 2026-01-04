# modules/auth_utils.py
# (VERSÃO DEFINITIVA: Auto-Login + Proteção contra Crash + Compatibilidade)

from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

# Tenta importar a persistência (falha graciosamente se não existir)
try:
    from modules.sessions import get_persistent_session
except ImportError:
    async def get_persistent_session(tid): return None

def get_current_player_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str | None:
    """
    Retorna o ID do jogador logado.
    1. Verifica memória RAM (context.user_data).
    2. Se não achar, retorna ID do Telegram (para compatibilidade).
    """
    # 1. Proteção: Verifica se user_data existe antes de acessar
    user_data = getattr(context, "user_data", None)
    if user_data and "logged_player_id" in user_data:
        return user_data["logged_player_id"]

    # 2. Fallback
    if update and update.effective_user:
        return update.effective_user.id
        
    return None

def requires_login(func):
    """
    Decorator que garante que o usuário está logado.
    Faz o 'Auto-Login' no banco de dados se o bot tiver reiniciado.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        # 1. Proteção contra Crash (NoneType)
        user_data = getattr(context, "user_data", None)
        
        # 2. Verifica se NÃO está logado na RAM
        if not user_data or not user_data.get("logged_player_id"):
            
            # [REGRA DE EXCEÇÃO]: Se a função recebeu 'player_data' manualmente, deixa passar.
            # Isso conserta o erro do Menu do Reino (region.py).
            if "player_data" in kwargs and kwargs["player_data"]:
                return await func(update, context, *args, **kwargs)

            # 3. Tenta AUTO-LOGIN (Recuperar do Banco)
            if update.effective_user:
                tg_id = update.effective_user.id
                saved_player_id = await get_persistent_session(tg_id)
                
                if saved_player_id:
                    # ACHOU! Restaura a sessão na memória RAM
                    if user_data is not None:
                        context.user_data["logged_player_id"] = saved_player_id
                    # Sucesso! Pode prosseguir para a função original
                    return await func(update, context, *args, **kwargs)

            # 4. Falhou tudo? Pede Login.
            if update.effective_message:
                try:
                    if update.callback_query:
                        await update.callback_query.answer("⚠️ Sessão expirada. Faça login novamente.", show_alert=True)
                    else:
                        await update.effective_message.reply_text("⚠️ <b>Sessão expirada.</b>\nUse /start para logar.", parse_mode="HTML")
                except: pass
            return

        return await func(update, context, *args, **kwargs)
    return wrapper

# --- ALIAS DE COMPATIBILIDADE ---
# Garante que arquivos procurando por 'requires_auth' funcionem
requires_auth = requires_login