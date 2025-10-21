# Arquivo: registries/admin.py (VERSÃO FINAL E CORRIGIDA)

from telegram.ext import Application

# --- 1. Importa a lista completa de handlers do ficheiro principal de admin ---
from handlers.admin_handler import all_admin_handlers

# --- 2. Importa os handlers dos outros ficheiros de sub-painel ---
from handlers.admin.file_id_conv import file_id_conv_handler
from handlers.admin.premium_panel import premium_panel_handler, premium_command_handler
from handlers.admin.reset_panel import reset_panel_conversation_handler
from handlers.admin.generate_equip import generate_equip_conv_handler

def register_admin_handlers(application: Application):
    """Regista todos os handlers relacionados à administração."""

    # PASSO 1: Regista TODOS os handlers do admin_handler.py de uma só vez.
    # Isto inclui o /admin, /delete_player, /fixme, menus de cache, etc.
    application.add_handlers(all_admin_handlers)
    
    # PASSO 2: Regista os handlers dos outros ficheiros que não estão na lista.
    application.add_handler(file_id_conv_handler)
    application.add_handler(premium_panel_handler)
    application.add_handler(premium_command_handler)
    application.add_handler(reset_panel_conversation_handler)
    application.add_handler(generate_equip_conv_handler)