# registries/regions.py
# (VERSÃO CORRIGIDA: logger inicializado corretamente)

from telegram.ext import Application
import logging

# --- INICIALIZAÇÃO DO LOGGER (MOVIDO PARA O TOPO) ---
logger = logging.getLogger(__name__)
# ----------------------------------------------------

# --- Grupo 1: Navegação e Menus de Região ---
# O travel_handler agora vive em handlers.menu.region
from handlers.menu.region import ( 
    region_handler,
    travel_handler,      # <--- Movido para cá
    open_region_handler,
    region_info_handler,
    restore_durability_menu_handler,
    restore_durability_fix_handler,
)

# --- Grupo 2: Coleta (Novo Arquivo) ---
# O handler de coleta agora vem daqui
from handlers.collection_handler import collection_handler

# --- Grupo 3: Calabouços (Dungeons) ---
from modules.dungeons.runtime import (
    dungeon_open_handler,
    dungeon_pick_handler,
)

# --- Grupo 4: NPCs ---
try:
    from handlers.npc_handler import all_npc_handlers
except ImportError:
    all_npc_handlers = [] # Fallback se não existir

# Tenta importar handlers do Reino se existirem em local separado
try:
    from handlers.menu.kingdom import kingdom_menu_handler
except ImportError:
    kingdom_menu_handler = None
    logger.warning("🚨 [REGISTRY] Falha ao importar kingdom_menu_handler. O botão 'Voltar ao Reino' não funcionará.")

def register_regions_handlers(application: Application):
    """Regista os handlers de regiões, viagens, coleta e calabouços."""

    # --- Grupo 1: Região e Viagem --- 
    if kingdom_menu_handler:
        application.add_handler(kingdom_menu_handler)
        logger.info("✅ [REGISTRY] kingdom_menu_handler REGISTRADO.")
        
    application.add_handler(travel_handler)
    application.add_handler(region_handler)
    application.add_handler(open_region_handler)
    application.add_handler(region_info_handler)
    
    # Durabilidade
    application.add_handler(restore_durability_menu_handler)
    application.add_handler(restore_durability_fix_handler)
    
    # --- Grupo 2: Coleta --- 
    # [CORREÇÃO] Registra o novo handler de coleta
    application.add_handler(collection_handler)

    # --- Grupo 3: Calabouços ---
    application.add_handler(dungeon_open_handler)
    application.add_handler(dungeon_pick_handler)

    # --- Grupo 4: NPCs ---
    if all_npc_handlers:
        application.add_handlers(all_npc_handlers)