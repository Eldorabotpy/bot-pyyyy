# registries/combat.py

from telegram.ext import Application

# 1. Importa handler de caça manual (Mantém o original)
from handlers.hunt_handler import hunt_handler

# 2. CORREÇÃO: Importa o Auto Hunt do arquivo NOVO/CORRIGIDO
# Isso garante que ele use a versão que apaga o menu e envia a mídia
try:
    from handlers.autohunt_handler import autohunt_start_handler
except ImportError:
    # Fallback caso você não tenha definido a variável no arquivo novo ainda
    from handlers.hunt_handler import autohunt_start_handler
    print("⚠️ AVISO: Usando autohunt antigo. Verifique handlers/autohunt_handler.py")

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
    # Colocamos ele PRIMEIRO para garantir que ele capture o clique antes do hunt_handler
    if autohunt_start_handler:
        application.add_handler(autohunt_start_handler)
        print("✅ Auto Hunt Handler registrado com prioridade.")

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