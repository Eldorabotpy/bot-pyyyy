# registries/__init__.py (VERSÃO FINAL QUE LIGA O BOTÃO)

import logging
from telegram import Update
from telegram.ext import Application, TypeHandler, ContextTypes, CallbackQueryHandler
from modules import player_manager
from datetime import datetime, timezone

# --- IMPORTS DOS REGISTROS (SEUS MÓDULOS) ---
from .admin import register_admin_handlers
from .character import register_character_handlers
from .combat import register_combat_handlers
from .crafting import register_crafting_handlers
from .market import register_market_handlers
from .regions import register_regions_handlers
from .guild import register_guild_handlers 
from .events import register_event_handlers

# --- IMPORTS DIRETOS DE HANDLERS ESPECÍFICOS ---
from handlers.world_boss.handler import all_world_boss_handlers
from handlers.potion_handler import all_potion_handlers
# from handlers.autohunt_handler import all_autohunt_handlers

# [IMPORTANTE] Importa o registro da Defesa do Reino
from kingdom_defense.handler import register_handlers as register_kingdom_defense_handlers

# --- IMPORTS DE MENUS E NAVEGAÇÃO ---
from handlers.menu import kingdom  # Para o botão "Voltar ao Reino"

# [CORREÇÃO CRÍTICA]: Usamos o handler de menu que TEM o botão da defesa configurado corretamente
# Se o seu arquivo estiver em 'handlers/menu/events.py', o import é este:
try:
    from handlers.menu import events as events_menu_handler
except ImportError:
    # Fallback caso você ainda use o caminho antigo, mas recomendo fortemente usar o handlers.menu.events
    from modules.events import event_menu as events_menu_handler

# Importa Entry (Entrada/Lobby) E Combat (Luta) das Catacumbas
from modules.events.catacumbas import entry_handler as cat_entry
from modules.events.catacumbas import combat_handler as cat_combat

logger = logging.getLogger(__name__)

async def update_last_seen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler global (Middleware) que atualiza 'last_seen'."""
    if not update.effective_user:
        return 
        
    user_id = update.effective_user.id
    try:
        # Otimização: Não precisamos carregar o dado todo se for só pra salvar timestamp, 
        # mas mantendo sua lógica original para segurança:
        pdata = await player_manager.get_player_data(user_id) 
        if pdata:
            pdata['last_seen'] = datetime.now(timezone.utc).isoformat()
            await player_manager.save_player_data(user_id, pdata)
    except Exception as e:
        logger.warning(f"Erro ao atualizar last_seen: {e}")

def register_all_handlers(application: Application):
    """Chama todas as funções de registo de cada categoria na ordem correta."""
    logger.info("Iniciando o registo de todos os handlers...")

    # 1. Middleware Global
    application.add_handler(TypeHandler(Update, update_last_seen), group=-1)
    
    # 2. Registo por Módulos (Organização Padrão)
    register_admin_handlers(application)
    register_character_handlers(application)
    register_combat_handlers(application)
    register_crafting_handlers(application) 
    register_market_handlers(application)
    register_guild_handlers(application)
    register_regions_handlers(application)
    
    # 3. Registra eventos gerais
    register_event_handlers(application)
    
    # [IMPORTANTE] Registra a Defesa do Reino explicitamente
    # Isso garante que o botão 'defesa_reino_main' seja ouvido
    register_kingdom_defense_handlers(application)
    
    # 4. Registo de Listas de Handlers (Legado/Outros)
    application.add_handlers(all_world_boss_handlers)
    application.add_handlers(all_potion_handlers)
    # application.add_handlers(all_autohunt_handlers)
    
    # ============================================================
    # 💀 REGISTRO DO SISTEMA DE EVENTOS & NAVEGAÇÃO
    # ============================================================
    
    # A. Menu Principal de Eventos (O Hub)
    # Conecta o botão "💀 Eventos Especiais" ao menu que mostra as opções
    # Tenta usar a função 'show_events_menu', se não existir, usa 'show_active_events'
    if hasattr(events_menu_handler, 'show_events_menu'):
        application.add_handler(CallbackQueryHandler(events_menu_handler.show_events_menu, pattern="^evt_hub_principal$"))
    else:
        application.add_handler(CallbackQueryHandler(events_menu_handler.show_active_events, pattern="^evt_hub_principal$"))
    
    # B. Botão Voltar para o Reino
    application.add_handler(CallbackQueryHandler(kingdom.show_kingdom_menu, pattern="^back_to_kingdom$"))
    
    # C. Lógica das Catacumbas (Lobby, Criar Sala, Entrar)
    application.add_handlers(cat_entry.handlers)

    # D. Lógica de Combate das Catacumbas
    application.add_handlers(cat_combat.handlers)
    
    logger.info("Todos os handlers foram registrados com sucesso no __init__.")