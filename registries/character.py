from telegram.ext import Application

# 1. Do fluxo de início e criação de personagem
from handlers.start_handler import (
    start_command_handler,
    name_command_handler,
    character_creation_handler,
)

from handlers.status_handler import ( 
    status_command_handler,
    status_open_handler,
    status_callback_handler,
    close_status_handler,
)

from handlers.profile_handler import profile_handler

from handlers.inventory_handler import ( 
    inventory_handler,
    noop_inventory_handler,
)

# 5. Do painel de equipamentos
from handlers.equipment_handler import ( 
    equipment_menu_handler,
    equip_slot_handler,
    equip_pick_handler,
    equip_unequip_handler,
)

from handlers.class_selection_handler import class_selection_handler 
from handlers.class_evolution_handler import ( 
    status_evolution_open_handler,
    evolution_command_handler,
    evolution_callback_handler,
    evolution_do_handler,
    evolution_cancel_handler,
)

from handlers.profession_handler import ( 
    job_menu_handler,
    job_pick_handler,
)

# ✅ 1. IMPORTAÇÃO SIMPLIFICADA: Importamos apenas a lista única de handlers da guilda.
from handlers.guild_handler import all_guild_handlers


def register_character_handlers(application: Application):
    """Regista todos os handlers relacionados ao personagem."""

    # --- Grupo 1: Início e Criação ---
    application.add_handler(start_command_handler)
    application.add_handler(name_command_handler)
    application.add_handler(character_creation_handler)

    # --- Grupo 2: Status e Atributos --- 
    application.add_handler(status_command_handler)
    application.add_handler(status_open_handler)
    application.add_handler(status_callback_handler)
    application.add_handler(close_status_handler)
    
    # --- Grupo 3: Perfil do Personagem ---
    application.add_handler(profile_handler)

    # --- Grupo 4: Inventário e Itens --- 
    application.add_handler(inventory_handler)
    application.add_handler(noop_inventory_handler)
    application.add_handler(equipment_menu_handler) 
    application.add_handler(equip_slot_handler)
    application.add_handler(equip_pick_handler)
    application.add_handler(equip_unequip_handler)

    # --- Grupo 5: Classes e Evolução ---
    application.add_handler(class_selection_handler)
    application.add_handler(status_evolution_open_handler) 
    application.add_handler(evolution_command_handler)      
    application.add_handler(evolution_callback_handler)     
    application.add_handler(evolution_do_handler)      
    application.add_handler(evolution_cancel_handler)

    # --- Grupo 6: Profissões --- 
    application.add_handler(job_menu_handler)
    application.add_handler(job_pick_handler)

    # ✅ 2. REGISTO AUTOMATIZADO: Um loop simples regista todos os handlers da guilda.
    # Removemos todas as linhas 'application.add_handler' individuais para a guilda.
    for handler in all_guild_handlers:
        application.add_handler(handler)