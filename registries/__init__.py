# registries/__init__.py (VERSÃO FINAL E LIMPA)

import logging
from telegram.ext import Application
from telegram import Update
from telegram.ext import Application, TypeHandler, ContextTypes
from modules import player_manager
from datetime import datetime, timezone

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

async def update_last_seen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler global (Middleware) que atualiza 'last_seen' para CADA interação do jogador.
    """
    if not update.effective_user:
        return # Ignora se não conseguirmos identificar o utilizador
        
    user_id = update.effective_user.id
    
    # Tenta pegar os dados do cache (rápido)
    pdata = await player_manager.get_player_data(user_id) 
    
    if pdata:
        # Atualiza o timestamp
        pdata['last_seen'] = datetime.now(timezone.utc).isoformat()
        # Salva (o save_player_data vai atualizar o cache e o DB)
        await player_manager.save_player_data(user_id, pdata)
    
    # Nota: Se pdata for None (jogador não existe/nunca deu /start), 
    # não fazemos nada. O 'created_at' e 'last_seen' serão definidos no /start.

# --- 👆 FIM DA NOVA FUNÇÃO 👆 ---

def register_all_handlers(application: Application):
    """Chama todas as funções de registo de cada categoria na ordem correta."""
    logging.info("Iniciando o registo de todos os handlers...")

    application.add_handler(TypeHandler(Update, update_last_seen), group=-1)
    
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
    