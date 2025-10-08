# Arquivo: registries/admin.py (versão final e corrigida)

from telegram.ext import Application

# --- Handlers do painel de admin principal ---
from handlers.admin_handler import (
    admin_command_handler,
    force_daily_handler,
    delete_player_handler,
    clear_cache_conv_handler,
    inspect_item_handler,
    # Handlers de botão individuais (aqui está a correção)
    admin_main_handler,
    admin_force_daily_callback_handler,
    admin_event_menu_handler,
    admin_force_start_handler,
    admin_force_end_handler,
    admin_force_ticket_handler,
)

# --- Handlers dos sub-paineis ---
from handlers.admin.file_id_conv import file_id_conv_handler
from handlers.admin.premium_panel import premium_panel_handler, premium_command_handler
from handlers.admin.reset_panel import reset_panel_conversation_handler
from handlers.admin.generate_equip import generate_equip_conv_handler

def register_admin_handlers(application: Application):
    """Regista todos os handlers relacionados à administração."""

    # Handlers de Comando
    application.add_handler(admin_command_handler)
    application.add_handler(force_daily_handler)
    application.add_handler(delete_player_handler)
    application.add_handler(premium_command_handler)
    application.add_handler(inspect_item_handler)

    # Handlers de CallbackQuery (Botões)
    # A linha que causava o erro foi removida e substituída por estas
    application.add_handler(admin_main_handler)
    application.add_handler(admin_force_daily_callback_handler)
    application.add_handler(admin_event_menu_handler)
    application.add_handler(admin_force_start_handler)
    application.add_handler(admin_force_end_handler)
    application.add_handler(admin_force_ticket_handler)
    
    # Handlers de Conversa
    application.add_handler(clear_cache_conv_handler)
    application.add_handler(file_id_conv_handler)
    application.add_handler(premium_panel_handler)
    application.add_handler(reset_panel_conversation_handler)
    application.add_handler(generate_equip_conv_handler)