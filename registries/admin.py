# registries/admin.py
# (VERSÃO FINAL: Gerencia a ordem de registro corretamente)

from telegram.ext import Application, CommandHandler

# Importa lista geral (Que agora NÃO tem gemas nem edit player)
from handlers.admin_handler import all_admin_handlers
from handlers.admin.pvp_panel_handler import pvp_panel_handlers

# Importa handlers especiais separadamente
from handlers.admin.sell_gems import sell_gems_conv_handler 
from handlers.admin.player_edit_panel import create_admin_edit_player_handler 
from handlers.admin.admin_tools import cmd_trocar_id

# Premium check
try:
    from handlers.admin.premium_panel import premium_command_handler
    PREMIUM_OK = True
except ImportError:
    PREMIUM_OK = False

def register_admin_handlers(application: Application):
    
    # 1. Registra Gemas (Alta Prioridade)
    application.add_handler(sell_gems_conv_handler)

    # 2. Registra Edição de Jogador (Alta Prioridade)
    # Usamos a fábrica para criar a instância nova
    application.add_handler(create_admin_edit_player_handler())

    # 3. Registra o resto dos admins
    application.add_handlers(all_admin_handlers) 
    
    # 4. Painéis extras e ferramentas
    application.add_handlers(pvp_panel_handlers)
    application.add_handler(CommandHandler("trocarid", cmd_trocar_id))
    
    if PREMIUM_OK:
        application.add_handler(premium_command_handler)