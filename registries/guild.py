# registries/guild.py
# (DESATIVADO: A responsabilidade passou para registries/character.py)

from telegram.ext import Application

def register_guild_handlers(application: Application):
    """
    Este arquivo agora está vazio propositalmente.
    
    Motivo: Todos os handlers de guilda já estão sendo registrados 
    no arquivo 'registries/character.py' com filtros de segurança anti-crash.
    
    Manter este arquivo vazio evita:
    1. Erro de duplicidade.
    2. Erro de 'handler is not an instance of BaseHandler'.
    """
    pass