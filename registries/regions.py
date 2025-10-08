from telegram.ext import Application
import logging

# --- Grupo 1: Navegação Principal ---
from handlers.menu_handler import ( 
    kingdom_menu_handler,
    travel_handler,
    continue_after_action_handler,
)

# --- Grupo 2: Ações em Regiões ---
from handlers.menu.region import ( 
    region_handler,
    collect_handler,
    open_region_handler,
    restore_durability_menu_handler,
    restore_durability_fix_handler,
)

# --- Grupo 3: Calabouços (Dungeons) - Usando o sistema unificado ---
from modules.dungeons.runtime import (
    dungeon_open_handler,
    dungeon_pick_handler,
)


def register_regions_handlers(application: Application):
    """Regista os handlers de regiões, viagens, coleta e calabouços."""

    # --- Grupo 1: Navegação Principal --- 
    application.add_handler(kingdom_menu_handler)
    application.add_handler(travel_handler)
    application.add_handler(continue_after_action_handler)
    
    # --- Grupo 2: Ações em Regiões --- 
    application.add_handler(region_handler)
    application.add_handler(collect_handler)
    application.add_handler(open_region_handler)
    application.add_handler(restore_durability_menu_handler)
    application.add_handler(restore_durability_fix_handler)
    
    # --- Grupo 3: Calabouços (Dungeons) ---
    application.add_handler(dungeon_open_handler)
    application.add_handler(dungeon_pick_handler)