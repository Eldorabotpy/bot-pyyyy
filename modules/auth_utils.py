# modules/auth_utils.py
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from modules.sessions import get_persistent_session # <--- Importe o novo módulo

def get_current_player_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str | None:
    """
    Retorna o ID do jogador logado.
    1. Verifica memória RAM (context.user_data).
    2. Se não achar, verifica Banco de Dados (Sessão Persistente).
    """
    # 1. Tenta pegar da memória (Rápido)
    user_id = context.user_data.get("logged_player_id")
    if user_id:
        return user_id

    # 2. Se não está na memória, tenta recuperar do banco (Auto-Login)
    tg_id = update.effective_user.id
    # Nota: Como get_persistent_session é async, não podemos chamar direto aqui se esta função for sincrona.
    # Mas geralmente usamos isso dentro de handlers async.
    # Se você precisar chamar isso de forma sincrona, a lógica muda um pouco,
    # mas o ideal é que a verificação ocorra no decorator @requires_login.
    return None

def requires_login(func):
    """
    Decorator que garante que o usuário está logado.
    Faz o 'Auto-Login' se o bot tiver reiniciado.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        # 1. Verifica memória
        if not context.user_data.get("logged_player_id"):
            
            # 2. Memória vazia? Tenta AUTO-LOGIN pelo banco
            tg_id = update.effective_user.id
            saved_player_id = await get_persistent_session(tg_id)
            
            if saved_player_id:
                # ACHOU! Restaura a sessão na memória
                context.user_data["logged_player_id"] = saved_player_id
                # Opcional: Avisar no log
                print(f"🔄 Auto-login realizado para Telegram ID {tg_id}")
            else:
                # Não achou nada, pede login
                if update.callback_query:
                    await update.callback_query.answer("⚠️ Você precisa fazer login novamente.", show_alert=True)
                    # Aqui você pode redirecionar para o menu de login se quiser
                else:
                    await update.message.reply_text("⚠️ <b>Sessão expirada.</b>\nPor favor, faça login novamente com /login ou /start.", parse_mode="HTML")
                return

        return await func(update, context, *args, **kwargs)
    return wrapper