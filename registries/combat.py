# registries/combat.py

from telegram.ext import Application

# 1. Importa handler de caça manual (Mantém o original)
from handlers.hunt_handler import hunt_handler

# 2. AUTO HUNT (ATUALIZADO PARA INCLUIR O POPUP)
try:
    # ✅ Importamos o start E o handler do popup (premium_info_handler)
    from handlers.autohunt_handler import autohunt_start_handler, premium_info_handler
except ImportError:
    # Fallback caso dê erro na importação
    from handlers.hunt_handler import autohunt_start_handler
    premium_info_handler = None
    print("⚠️ AVISO: Usando autohunt antigo ou premium_info_handler não encontrado.")

# Importa handlers de combate direto
from handlers.combat.main_handler import combat_handler

# Importa handlers de poções
from handlers.combat.potion_handler import combat_potion_menu_handler, combat_use_potion_handler

# Importa handlers de skills
from handlers.combat.skill_handler import (
    combat_skill_menu_handler, 
    combat_use_skill_handler, 
    combat_skill_on_cooldown_handler,
    combat_skill_info_handler
)

# Importa PvP
from pvp.pvp_handler import pvp_handlers
from pvp.tournament_admin import get_tournament_admin_handlers

# registries/combat.py

def register_combat_handlers(application: Application):
    """Regista todos os handlers relacionados a combate."""
    
    # -------------------------------------------------------------
    # 1. AUTO HUNT (PRIORIDADE MÁXIMA)
    # -------------------------------------------------------------
    if autohunt_start_handler:
        application.add_handler(autohunt_start_handler)
        print("✅ Auto Hunt Handler registrado.")

    # ✅ AQUI: Registra o Popup do Cadeado (Informações Premium)
    if premium_info_handler:
        application.add_handler(premium_info_handler)

    # -------------------------------------------------------------
    # 2. Caça Manual (Menu Geral)
    # -------------------------------------------------------------
    application.add_handler(hunt_handler)
    
    # 3. Combate PvE (Ataque, Fuga)
    application.add_handler(combat_handler)
    
    # 4. Poções em Combate
    application.add_handler(combat_potion_menu_handler)
    application.add_handler(combat_use_potion_handler)

    # 5. Skills em Combate
    application.add_handler(combat_skill_menu_handler)
    application.add_handler(combat_use_skill_handler)
    application.add_handler(combat_skill_on_cooldown_handler)
    application.add_handler(combat_skill_info_handler)

    # 6. PvP
    for handler in pvp_handlers():
        application.add_handler(handler)

    for handler in get_tournament_admin_handlers():
        application.add_handler(handler)