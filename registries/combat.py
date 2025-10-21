# registries/combat.py (VERSÃO FINAL E CORRIGIDA)

from telegram.ext import Application

# Importa os handlers individuais dos seus novos ficheiros
from handlers.hunt_handler import hunt_handler 
from handlers.combat.main_handler import combat_handler
from handlers.combat.potion_handler import combat_potion_menu_handler, combat_use_potion_handler
from pvp.pvp_handler import pvp_handlers

def register_combat_handlers(application: Application):
    """Regista todos os handlers relacionados a combate."""

    # --- Grupo 1: Caça e Combate PvE --- 
    application.add_handler(hunt_handler)
    
    # Adiciona os handlers de combate refatorados um a um
    application.add_handler(combat_handler)
    application.add_handler(combat_potion_menu_handler)
    application.add_handler(combat_use_potion_handler)
    
    # --- Grupo 2: Arena PvP ---
    # A função pvp_handlers() retorna uma lista de handlers
    for handler in pvp_handlers():
        application.add_handler(handler)