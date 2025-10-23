# registries/guild.py (VERSÃO CORRIGIDA)

from telegram.ext import Application
from handlers.guild_handler import all_guild_handlers

def register_guild_handlers(application: Application):
    """Registra todos os handlers relacionados ao sistema de guildas."""
    
    # MUDANÇA: Em vez de um loop, registramos a lista inteira de uma vez.
    # O 'group=0' é o grupo padrão para ConversationHandlers e
    # garante que eles sejam processados na ordem correta.
    application.add_handlers(all_guild_handlers, group=0)