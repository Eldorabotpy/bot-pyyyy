# registries/combat.py

from telegram.ext import Application

# Importa handlers de caça
# Se der erro aqui, verifique o arquivo handlers/hunt_handler.py
from handlers.hunt_handler import hunt_handler, autohunt_start_handler

# Importa handlers de combate direto
from handlers.combat.main_handler import combat_handler

# Importa handlers de poções
from handlers.combat.potion_handler import combat_potion_menu_handler, combat_use_potion_handler

# Importa handlers de skills
from handlers.combat.skill_handler import (
    combat_skill_menu_handler, 
    combat_use_skill_handler, 
    combat_skill_on_cooldown_handler,
    combat_skill_info_handler
)

# Importa PvP
from pvp.pvp_handler import pvp_handlers

def register_combat_handlers(application: Application):
    """Regista todos os handlers relacionados a combate."""

    # 1. Caça e Auto Hunt
    application.add_handler(hunt_handler)
    application.add_handler(autohunt_start_handler)
    
    # 2. Combate PvE (Ataque, Fuga)
    application.add_handler(combat_handler)
    
    # 3. Poções em Combate
    application.add_handler(combat_potion_menu_handler)
    application.add_handler(combat_use_potion_handler)

    # 4. Skills em Combate
    application.add_handler(combat_skill_menu_handler)
    application.add_handler(combat_use_skill_handler)
    application.add_handler(combat_skill_on_cooldown_handler)
    application.add_handler(combat_skill_info_handler)

    # 5. PvP
    for handler in pvp_handlers():
        application.add_handler(handler)