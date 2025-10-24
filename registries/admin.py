# Arquivo: registries/admin.py (VERSÃO SIMPLIFICADA E CORRIGIDA - Reconfirmada)

from telegram.ext import Application

from handlers.admin_handler import all_admin_handlers
try:
    from handlers.admin.premium_panel import premium_command_handler
    PREMIUM_COMMAND_HANDLER_EXISTS = True
except ImportError:
    PREMIUM_COMMAND_HANDLER_EXISTS = False
from handlers.admin.player_edit_panel import create_admin_edit_player_handler # A CONVERSA de edição

def register_admin_handlers(application: Application):
    application.add_handlers(all_admin_handlers) # Regista a lista (sem o botão)
    if PREMIUM_COMMAND_HANDLER_EXISTS:
        application.add_handler(premium_command_handler)
    application.add_handler(create_admin_edit_player_handler()) # Regista a CONVERSA (com os entry points corretos)