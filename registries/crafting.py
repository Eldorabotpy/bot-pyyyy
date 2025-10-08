# registries/crafting.py

from telegram.ext import Application

# --- Importação dos Handlers de Forja ---
# O roteador geral que lida com callbacks como 'open_crafting'.
from handlers.crafting_handler import craft_open_handler 
# O novo roteador específico para o fluxo da forja (forge:main, forge:prof, etc.).
from handlers.forge_handler import forge_handler # <<< NOVO IMPORT

# --- Handlers de Aprimoramento (Enhance) ---
from handlers.enhance_handler import (
    enhance_menu_handler,
    enhance_select_handler,
    enhance_action_handler,
)

# --- Handlers de Refino e Desmontagem ---
from handlers.refining_handler import (
    refining_main_handler,
    ref_select_handler,
    ref_confirm_handler,
    dismantle_list_handler,
    dismantle_preview_handler,
    dismantle_confirm_handler,
)

def register_crafting_handlers(application: Application):
    """Registra todos os handlers relacionados aos sistemas de forja."""

    # --- Grupo 1: Forja e Criação de Itens ---
    # Adiciona o handler que lida com todos os callbacks que começam com "forge:"
    application.add_handler(forge_handler) # <<< NOVO HANDLER REGISTRADO
    
    # Adiciona o handler genérico para abrir o sistema de craft (se usado em outros lugares)
    application.add_handler(craft_open_handler)
    
    # --- Grupo 2: Aprimoramento / Enhance ---
    application.add_handler(enhance_menu_handler)
    application.add_handler(enhance_select_handler)
    application.add_handler(enhance_action_handler)
    
    # --- Grupo 3: Refino e Desmontagem ---
    application.add_handler(refining_main_handler)
    application.add_handler(ref_select_handler)
    application.add_handler(ref_confirm_handler)
    application.add_handler(dismantle_list_handler)
    application.add_handler(dismantle_preview_handler)
    application.add_handler(dismantle_confirm_handler)