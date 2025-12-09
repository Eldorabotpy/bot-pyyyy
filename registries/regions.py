# registries/regions.py
# (VERSÃO CORRIGIDA: Importando coleta do lugar certo)

from telegram.ext import Application
import logging

# --- INICIALIZAÇÃO DO LOGGER ---
logger = logging.getLogger(__name__)

# --- Grupo 1 & 2: Navegação, Menus e COLETA ---
# Tudo isso vive em handlers/menu/region.py
from handlers.menu.region import ( 
    region_handler,
    travel_handler,      
    open_region_handler,
    region_info_handler,
    restore_durability_menu_handler,
    restore_durability_fix_handler,
    collect_handler  # <--- ADICIONADO AQUI (Vem do region.py)
)
from handlers.christmas_shop import christmas_shop_handler, christmas_buy_handler

# (Removido: from handlers.collection_handler import collection_handler)

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

# Tenta importar handlers do Reino
try:
    from handlers.menu.kingdom import kingdom_menu_handler
except ImportError:
    kingdom_menu_handler = None
    logger.warning("🚨 [REGISTRY] Falha ao importar kingdom_menu_handler.")

def register_regions_handlers(application: Application):
    """Regista os handlers de regiões, viagens, coleta e calabouços."""

    # --- Grupo 1: Região e Viagem --- 
    if kingdom_menu_handler:
        application.add_handler(kingdom_menu_handler)
        
    application.add_handler(travel_handler)
    application.add_handler(region_handler)
    application.add_handler(open_region_handler)
    application.add_handler(region_info_handler)
    
    # Durabilidade
    application.add_handler(restore_durability_menu_handler)
    application.add_handler(restore_durability_fix_handler)
    
    # --- Grupo 2: Coleta --- 
    # Usamos o collect_handler que importamos do region.py
    application.add_handler(collect_handler)

    # --- Grupo 3: Calabouços ---
    application.add_handler(dungeon_open_handler)
    application.add_handler(dungeon_pick_handler)

    # --- Grupo 4: NPCs ---
    if all_npc_handlers:
        application.add_handlers(all_npc_handlers)
        # 👇👇👇 ADICIONE O NATAL AQUI 👇👇👇
        # 🎅 Loja de Natal (Evento)
        application.add_handler(christmas_shop_handler)
        application.add_handler(christmas_buy_handler)