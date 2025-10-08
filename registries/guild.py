# registries/guild.py

from telegram.ext import Application
from handlers.guild_handler import all_guild_handlers

def register_guild_handlers(application: Application):
    """Registra todos os handlers relacionados ao sistema de guildas."""
    for handler in all_guild_handlers:
        application.add_handler(handler)