# handlers/action_lock_handler.py
# Middleware de bloqueio global por ação em andamento

from telegram import Update
from telegram.ext import (
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from modules.action_guard import guard_or_notify


# ==========================================================
# 🔒 BLOQUEIO DE CALLBACKS (botões antigos)
# ==========================================================
async def block_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Intercepta TODOS os callbacks antes dos handlers reais.
    Se o jogador estiver em ação, o guard:
    - responde com alert (popup)
    - retorna False
    - e impede outros handlers (block=True)
    """
    allowed = await guard_or_notify(update, context)
    if not allowed:
        return
    # se allowed=True, deixa o fluxo continuar para outros handlers


# ==========================================================
# 🔒 BLOQUEIO DE MENSAGENS (/menu, /start, texto)
# ==========================================================
async def block_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Intercepta mensagens/comandos globais.
    Se estiver em ação:
    - envia mensagem curta
    - não deixa abrir menu
    """
    allowed = await guard_or_notify(update, context)
    if not allowed:
        return


# ==========================================================
# HANDLERS EXPORTÁVEIS
# ==========================================================
# CallbackQueryHandler:
# - pattern pega QUALQUER callback_data
# - block=True impede que handlers abaixo rodem
action_lock_callback_handler = CallbackQueryHandler(
    block_callbacks,
    pattern=r"^(?!$).+",
    block=True,
)

# MessageHandler:
# - pega qualquer mensagem (inclusive comandos)
# - block=True garante que o fluxo pare aqui
action_lock_message_handler = MessageHandler(
    filters.ALL,
    block_messages,
    block=True,
)
