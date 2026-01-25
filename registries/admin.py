# registries/admin.py
from telegram.ext import Application, CommandHandler

# Importa lista geral (Que já inclui o premium_panel_handler)
from handlers.admin_handler import all_admin_handlers
from handlers.admin.pvp_panel_handler import pvp_panel_handlers

# Importa handlers especiais separadamente
from handlers.admin.sell_gems import sell_gems_conv_handler
from handlers.admin.player_edit_panel import create_admin_edit_player_handler
from handlers.admin.admin_tools import cmd_trocar_id

# Guerra de Clãs (sistema único) — somente comandos seguros
from handlers.admin.clan_war_admin import (
    cmd_wardom,
    cmd_warthu,
    cmd_warend,
    cmd_warstatus,
    cmd_war_hard_reset,
)


def register_admin_handlers(application: Application):

    # 1. Registra Gemas (Alta Prioridade)
    application.add_handler(sell_gems_conv_handler)

    # 2. Registra Edição de Jogador (Alta Prioridade)
    application.add_handler(create_admin_edit_player_handler())

    # 3. Registra o resto dos admins (Inclui Premium, Delete, etc.)
    application.add_handlers(all_admin_handlers)

    # 4. Painéis extras e ferramentas
    application.add_handlers(pvp_panel_handlers)
    application.add_handler(CommandHandler("trocarid", cmd_trocar_id))

    # 5. Guerra de Clãs — comandos oficiais/seguros
    application.add_handler(CommandHandler("wardom", cmd_wardom))
    application.add_handler(CommandHandler("warthu", cmd_warthu))
    application.add_handler(CommandHandler("warend", cmd_warend))
    application.add_handler(CommandHandler("warstatus", cmd_warstatus))
    application.add_handler(CommandHandler("warreset", cmd_war_hard_reset))
