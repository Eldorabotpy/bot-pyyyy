# registries/__init__.py
import logging
from telegram.ext import Application

from .admin import register_admin_handlers
from .character import register_character_handlers
from .combat import register_combat_handlers
from .crafting import register_crafting_handlers
from .market import register_market_handlers
from .regions import register_regions_handlers
from .guild import register_guild_handlers 
from .events import register_event_handlers


def register_all_handlers(application: Application):
    """Chama todas as funções de registo de cada categoria na ordem correta."""
    logging.info("Iniciando o registo de todos os handlers...")
    
    # Ordem de registo: dos mais específicos para os mais genéricos, se houver conflito.
    register_admin_handlers(application)
    register_crafting_handlers(application) 
    register_market_handlers(application)
    register_guild_handlers(application)  # <-- LINHA ADICIONADA
    register_combat_handlers(application)
    register_regions_handlers(application)
    register_character_handlers(application)
    register_event_handlers(application)
    
    logging.info("Todos os handlers foram registrados com sucesso.")