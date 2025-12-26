# registries/admin.py

from telegram.ext import Application, CommandHandler

# Importa lista geral (agora SEM a venda de gemas)
from handlers.admin_handler import all_admin_handlers
from handlers.admin.pvp_panel_handler import pvp_panel_handlers

# Importa a venda de gemas separadamente (NOVO)
from handlers.admin.sell_gems import sell_gems_conv_handler 

# Outros imports
try:
    from handlers.admin.premium_panel import premium_command_handler
    PREMIUM_OK = True
except ImportError:
    PREMIUM_OK = False

from handlers.admin.player_edit_panel import create_admin_edit_player_handler 
from handlers.admin.admin_tools import cmd_trocar_id

def register_admin_handlers(application: Application):
    
    # 1. Registra Gemas (Prioridade)
    application.add_handler(sell_gems_conv_handler)

    # 2. Registra o resto (agora seguro, pois removemos a duplicata da lista)
    application.add_handlers(all_admin_handlers) 
    
    # 3. Painéis extras
    application.add_handlers(pvp_panel_handlers)
    application.add_handler(CommandHandler("trocarid", cmd_trocar_id))
    
    if PREMIUM_OK:
        application.add_handler(premium_command_handler)
        
    application.add_handler(create_admin_edit_player_handler())