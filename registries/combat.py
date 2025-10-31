# registries/combat.py (VERSÃO FINAL E CORRIGIDA)

from telegram.ext import Application

# Importa os handlers individuais dos seus novos ficheiros
from handlers.hunt_handler import hunt_handler 
from handlers.combat.main_handler import combat_handler
from handlers.combat.potion_handler import combat_potion_menu_handler, combat_use_potion_handler

# <<< MUDANÇA: Importa os novos handlers de SKILL >>>
from handlers.combat.skill_handler import (
    combat_skill_menu_handler, 
    combat_use_skill_handler, 
    combat_skill_on_cooldown_handler
)

from pvp.pvp_handler import pvp_handlers

def register_combat_handlers(application: Application):
    """Regista todos os handlers relacionados a combate."""

    # --- Grupo 1: Caça e Combate PvE --- 
    application.add_handler(hunt_handler)

    # Handlers de Combate (Ataque, Fuga)
    application.add_handler(combat_handler)

    # Handlers de Poções
    application.add_handler(combat_potion_menu_handler)
    application.add_handler(combat_use_potion_handler)

    # <<< MUDANÇA: Regista os novos handlers de SKILL >>>
    application.add_handler(combat_skill_menu_handler)
    application.add_handler(combat_use_skill_handler)
    application.add_handler(combat_skill_on_cooldown_handler)

    # --- Grupo 2: Arena PvP ---
    # A função pvp_handlers() retorna uma lista de handlers
    for handler in pvp_handlers():
        application.add_handler(handler)