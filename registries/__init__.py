# registries/__init__.py (VERSÃO FINAL E LIMPA)

import logging
from telegram.ext import Application

# Importa as funções de registo de cada módulo
from .admin import register_admin_handlers
from .character import register_character_handlers
from .combat import register_combat_handlers
from .crafting import register_crafting_handlers
from .market import register_market_handlers
from .regions import register_regions_handlers
from .guild import register_guild_handlers 
from .events import register_event_handlers

# Importa handlers que são registados diretamente
from handlers.world_boss.handler import all_world_boss_handlers
from handlers.potion_handler import all_potion_handlers
#from handlers.autohunt_handler import all_autohunt_handlers
from kingdom_defense.handler import register_handlers as register_kingdom_defense_handlers


def register_all_handlers(application: Application):
    """Chama todas as funções de registo de cada categoria na ordem correta."""
    logging.info("Iniciando o registo de todos os handlers...")
    
    # --- Registo por Módulos ---
    register_admin_handlers(application)
    register_character_handlers(application)
    register_combat_handlers(application)
    register_crafting_handlers(application) 
    register_market_handlers(application)
    register_guild_handlers(application)
    register_regions_handlers(application)
    register_event_handlers(application)
    register_kingdom_defense_handlers(application)
    
    # --- Registo de Listas de Handlers ---
    # Estes são os handlers que não têm uma função de registo própria
    #application.add_handlers(all_autohunt_handlers)
    application.add_handlers(all_world_boss_handlers)
    application.add_handlers(all_potion_handlers)
    
    logging.info("Todos os handlers foram registrados com sucesso.")