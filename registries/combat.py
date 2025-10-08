# registries/combat.py 
from telegram.ext import Application


from handlers.hunt_handler import hunt_handler 
from handlers.combat_handler import combat_handler
from pvp.pvp_handler import pvp_handlers


def register_combat_handlers(application: Application):
    """Regista todos os handlers relacionados a combate."""

    # --- Grupo 1: Caça e Combate PvE --- 
    application.add_handler(hunt_handler)
    application.add_handler(combat_handler)
    
    # --- Grupo 2: Arena PvP --- # <<< ADICIONADO
    # A função pvp_handlers() retorna uma lista de handlers
    for handler in pvp_handlers():
        application.add_handler(handler)
        