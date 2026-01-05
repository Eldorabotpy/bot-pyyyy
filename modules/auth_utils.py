# modules/auth_utils.py
# (VERSÃO SANITIZADA: Rejeita sessões legadas)

from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from bson import ObjectId

try:
    from modules.sessions import get_persistent_session
except ImportError:
    async def get_persistent_session(tid): return None

def get_current_player_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str | None:
    """
    Retorna o ID do jogador logado.
    AGORA: Só aceita strings/ObjectIds válidos. Rejeita INT (Legado).
    """
    user_data = getattr(context, "user_data", None)
    if user_data:
        pid = user_data.get("logged_player_id")
        
        # Validação Estrita: Se for int ou string numérica simples, ignora (força re-login)
        if isinstance(pid, int): return None
        if isinstance(pid, str) and pid.isdigit(): return None
        
        if pid: return pid

    return None

def requires_login(func):
    """
    Decorator de Auth. Se não tiver sessão válida (Novo Sistema), bloqueia.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        # Permite injeção manual (casos de teste ou admin interno)
        if "player_data" in kwargs and kwargs["player_data"]:
            return await func(update, context, *args, **kwargs)

        user_data = getattr(context, "user_data", None)
        
        # 1. Verifica RAM
        if not user_data or not get_current_player_id(update, context):
            
            # 2. Tenta Auto-Login Persistente
            if update.effective_user:
                tg_id = update.effective_user.id
                saved_player_id = await get_persistent_session(tg_id)
                
                # Só restaura se for um ID válido do novo sistema (ObjectId string)
                if saved_player_id and not saved_player_id.isdigit():
                    if user_data is not None:
                        context.user_data["logged_player_id"] = saved_player_id
                    return await func(update, context, *args, **kwargs)

            # 3. Falhou? Avisa.
            if update.effective_message:
                msg = "⚠️ <b>Sessão expirada ou sistema atualizado.</b>\nPor favor, use /start para logar ou migrar sua conta."
                try:
                    if update.callback_query:
                        await update.callback_query.answer("⚠️ Faça login novamente.", show_alert=True)
                        # Opcional: enviar msg de texto se for botão crítico
                    else:
                        await update.effective_message.reply_text(msg, parse_mode="HTML")
                except: pass
            return

        return await func(update, context, *args, **kwargs)
    return wrapper