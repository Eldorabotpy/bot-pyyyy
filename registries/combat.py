# registries/combat.py (VERSÃO CORRIGIDA)

from telegram.ext import Application

# Importa os handlers individuais dos seus novos ficheiros
from handlers.hunt_handler import hunt_handler 

# <<< [CORREÇÃO 1] Importa o novo handler que definiste no hunt_handler.py >>>
from handlers.hunt_handler import autohunt_start_handler 

from handlers.combat.main_handler import combat_handler
from handlers.combat.potion_handler import combat_potion_menu_handler, combat_use_potion_handler

# <<< [CORREÇÃO 2] APAGA a linha que estava a dar erro >>>
# autohunt_start_handler = CallbackQueryHandler(start_auto_hunt_callback, pattern=r'^autohunt_start_') # <-- LINHA APAGADA

# Importa os handlers de SKILL
from handlers.combat.skill_handler import (
    combat_skill_menu_handler, 
    combat_use_skill_handler, 
    combat_skill_on_cooldown_handler,
    combat_skill_info_handler
)

from pvp.pvp_handler import pvp_handlers

def register_combat_handlers(application: Application):
    """Regista todos os handlers relacionados a combate."""

    # --- Grupo 1: Caça e Combate PvE --- 
    application.add_handler(hunt_handler)
    
    # <<< [CORREÇÃO 3] Esta linha agora funciona, pois o handler foi importado >>>
    application.add_handler(autohunt_start_handler)
    
    # Handlers de Combate (Ataque, Fuga)
    application.add_handler(combat_handler)
    
    # Handlers de Poções
    application.add_handler(combat_potion_menu_handler)
    application.add_handler(combat_use_potion_handler)

    # Regista os novos handlers de SKILL
    application.add_handler(combat_skill_menu_handler)
    application.add_handler(combat_use_skill_handler)
    application.add_handler(combat_skill_on_cooldown_handler)
    application.add_handler(combat_skill_info_handler)
    # --- Grupo 2: Arena PvP ---
    # A função pvp_handlers() retorna uma lista de handlers
    for handler in pvp_handlers():
        application.add_handler(handler)