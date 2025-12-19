# registries/crafting.py

from telegram.ext import Application

# --- Importação dos Handlers de Forja ---
from handlers.crafting_handler import craft_open_handler 
from handlers.forge_handler import forge_handler

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
    # --- NOVOS HANDLERS DE LOTE (IMPORTADOS AGORA) ---
    ref_batch_menu_handler,  
    ref_batch_go_handler,    
    # -------------------------------------------------
    dismantle_list_handler,
    dismantle_preview_handler,
    dismantle_confirm_handler,
    dismantle_bulk_handler,
    noop_handler,
)

def register_crafting_handlers(application: Application):
    """Registra todos os handlers relacionados aos sistemas de forja."""

    # --- Grupo 1: Forja e Criação de Itens ---
    application.add_handler(forge_handler)
    application.add_handler(craft_open_handler)
    
    # --- Grupo 2: Aprimoramento / Enhance ---
    application.add_handler(enhance_menu_handler)
    application.add_handler(enhance_select_handler)
    application.add_handler(enhance_action_handler)
    
    # --- Grupo 3: Refino e Desmontagem ---
    application.add_handler(refining_main_handler)
    application.add_handler(noop_handler)
    application.add_handler(ref_select_handler)
    application.add_handler(ref_confirm_handler)
    
    # --- REGISTRO DOS NOVOS BOTÕES DE LOTE ---
    application.add_handler(ref_batch_menu_handler) # Menu de escolher quantidade
    application.add_handler(ref_batch_go_handler)   # Ação de confirmar lote
    # -------------------------------------------

    application.add_handler(dismantle_list_handler)
    application.add_handler(dismantle_preview_handler)
    application.add_handler(dismantle_confirm_handler)
    application.add_handler(dismantle_bulk_handler)