# Arquivo: registries/events.py

from telegram.ext import Application
from kingdom_defense.handler import register_handlers as register_kingdom_defense_handlers

def register_event_handlers(application: Application):
    """Registra todos os handlers relacionados a eventos."""
    register_kingdom_defense_handlers(application)
    # No futuro, se você criar um novo evento (ex: "Tesouro do Dragão"),
    # você adicionará a chamada para o registro dele aqui.