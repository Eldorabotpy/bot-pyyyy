# registries/__init__.py (VERSÃO FINAL CORRIGIDA)

import logging
from telegram import Update
from telegram.ext import Application, TypeHandler, ContextTypes, CallbackQueryHandler
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

# --- IMPORTS DO SISTEMA DE EVENTOS ---
from handlers.menu import kingdom  # Para o botão "Voltar ao Reino"
from modules.events import event_menu  # O menu que lista os eventos

# Importa Entry (Entrada/Lobby) E Combat (Luta)
from modules.events.catacumbas import entry_handler as cat_entry
from modules.events.catacumbas import combat_handler as cat_combat

async def update_last_seen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler global (Middleware) que atualiza 'last_seen'."""
    if not update.effective_user:
        return 
        
    user_id = update.effective_user.id
    pdata = await player_manager.get_player_data(user_id) 
    
    if pdata:
        pdata['last_seen'] = datetime.now(timezone.utc).isoformat()
        await player_manager.save_player_data(user_id, pdata)

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
    # application.add_handlers(all_autohunt_handlers)
    application.add_handlers(all_world_boss_handlers)
    application.add_handlers(all_potion_handlers)
    
    # ============================================================
    # 💀 REGISTRO DO SISTEMA DE EVENTOS (CATACUMBAS)
    # ============================================================
    
    # 1. Menu Principal de Eventos (Atualizado para evitar conflito)
    application.add_handler(CallbackQueryHandler(event_menu.show_active_events, pattern="^evt_hub_principal$"))    
    # 2. Botão Voltar para o Reino
    application.add_handler(CallbackQueryHandler(kingdom.show_kingdom_menu, pattern="^back_to_kingdom$"))
    
    # 3. Lógica das Catacumbas (Lobby, Criar Sala, Entrar)
    application.add_handlers(cat_entry.handlers)

    # 4. Lógica de Combate (Ataques, Skills, Boss) - MUITO IMPORTANTE
    application.add_handlers(cat_combat.handlers)
    
    logging.info("Todos os handlers foram registrados com sucesso.")