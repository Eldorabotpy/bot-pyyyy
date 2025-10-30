# Arquivo: registries/admin.py
# (Versão Corrigida - Adiciona o Painel PvP)

from telegram.ext import Application

# Importa a lista principal de handlers (comandos, painel principal)
from handlers.admin_handler import all_admin_handlers

# <<< 1. IMPORTA a nova lista de handlers do Painel PvP >>>
from handlers.admin.pvp_panel_handler import pvp_panel_handlers

# Importa o handler de /premium (se existir)
try:
    from handlers.admin.premium_panel import premium_command_handler
    PREMIUM_COMMAND_HANDLER_EXISTS = True
except ImportError:
    PREMIUM_COMMAND_HANDLER_EXISTS = False

# Importa a CONVERSA de edição de jogador
from handlers.admin.player_edit_panel import create_admin_edit_player_handler 

def register_admin_handlers(application: Application):
    
    # Regista os comandos principais de admin (ex: /admin)
    application.add_handlers(all_admin_handlers) 
    
    # <<< 2. REGISTA os handlers do Painel PvP (botões) >>>
    application.add_handlers(pvp_panel_handlers)
    
    # Regista o comando /premium (se existir)
    if PREMIUM_COMMAND_HANDLER_EXISTS:
        application.add_handler(premium_command_handler)
        
    # Regista a CONVERSA de edição de jogador
    application.add_handler(create_admin_edit_player_handler())