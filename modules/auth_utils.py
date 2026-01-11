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
    Retorna o ID do jogador logado como STRING (Representação do ObjectId).
    NÃO aceita IDs numéricos antigos.
    """
    user_data = getattr(context, "user_data", None)
    
    # 1. Verifica na RAM (user_data)
    if user_data:
        pid = user_data.get("logged_player_id")
        
        if pid:
            # Se for um objeto ObjectId, converte pra string e retorna
            if isinstance(pid, ObjectId):
                return str(pid)
            
            # Se for string (Verifica se parece ObjectId)
            if isinstance(pid, str) and ObjectId.is_valid(pid):
                return pid
            
            # Ignora int/legacy

    return None

def requires_login(func):
    """
    Decorator blindado: Tenta recuperar a sessão do banco se a RAM falhar.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        # Permite injeção manual para testes
        if "player_data" in kwargs and kwargs["player_data"]:
            return await func(update, context, *args, **kwargs)

        user_data = getattr(context, "user_data", None)
        
        # 1. Se não achou na RAM, tenta recuperar do Banco (Persistência)
        if not user_data or not get_current_player_id(update, context):
            
            if update.effective_user:
                tg_id = update.effective_user.id
                
                # Busca no banco de sessões
                saved_player_id = await get_persistent_session(tg_id)
                
                if saved_player_id:
                    # [CORREÇÃO]: Usando a variável correta 'saved_player_id'
                    if ObjectId.is_valid(saved_player_id):
                        if user_data is not None:
                            context.user_data["logged_player_id"] = str(saved_player_id)
                        return await func(update, context, *args, **kwargs)

            # 2. Se falhou tudo, avisa o usuário
            if update.effective_message:
                msg = "⚠️ <b>Sessão expirada.</b>\nPor favor, digite /start para reconectar."
                try:
                    if update.callback_query:
                        try: await update.callback_query.answer("⚠️ Reconectando...", show_alert=False)
                        except: pass
                    else:
                        await update.effective_message.reply_text(msg, parse_mode="HTML")
                except: pass
            return

        return await func(update, context, *args, **kwargs)
    return wrapper