# Arquivo: registries/events.py
from telegram.ext import Application, CallbackQueryHandler
import logging

logger = logging.getLogger(__name__)

# 1. Importa os sistemas de eventos
from kingdom_defense.handler import register_handlers as register_kingdom_defense_handlers
from handlers.world_boss.handler import all_world_boss_handlers
from handlers.menu.events import events_menu_handler, evt_claim_daily_entries_handler

# 2. Importação CORRIGIDA (Apontando para handlers/menu/events.py)
try:
    # Tenta importar do local listado no seu relatório
    from handlers.menu.events import show_active_events
    logger.info("✅ Menu de Eventos carregado de handlers.menu.events")
except ImportError:
    # Fallback caso você tenha salvo como 'event_menu.py' dentro de modules
    try:
        from modules.events.event_menu import show_active_events
        logger.info("✅ Menu de Eventos carregado de modules.events.event_menu")
    except ImportError:
        logger.error("❌ ERRO: Não achei o arquivo de menu de eventos!")
        # Função vazia para não quebrar o bot se falhar
        async def show_active_events(update, context):
            await update.callback_query.answer("Erro: Menu não encontrado.", show_alert=True)

def register_event_handlers(application: Application):
    """Registra todos os handlers relacionados a eventos."""
    
    # 1. Registra Defesa do Reino
    register_kingdom_defense_handlers(application)
    
    # 2. Registra World Boss
    application.add_handlers(all_world_boss_handlers)

    # 3. REGISTRO DO BOTÃO COM O NOVO ID
    # Isso faz a ligação direta entre o clique e o código
    application.add_handler(CallbackQueryHandler(show_active_events, pattern='^abrir_hub_eventos_v2$'))
    
    # Registra o botão de voltar também
    application.add_handler(CallbackQueryHandler(show_active_events, pattern='^back_to_event_hub$'))
    
    application.add_handler(events_menu_handler)
    application.add_handler(evt_claim_daily_entries_handler)