# registries/character.py (VERSÃO CORRIGIDA FINAL)

from telegram.ext import Application

# 1. Do fluxo de início e criação de personagem
from handlers.start_handler import (
    start_command_handler,
    name_command_handler,
    character_creation_handler,
)

# 2. Do Status, Perfil e Inventário
from handlers.status_handler import (
    status_command_handler,
    status_open_handler,
    status_callback_handler,
    close_status_handler,       # <-- ADICIONADO (estava em falta)
)
from handlers.profile_handler import (
    profile_handler,
    character_command_handler,  # <-- ADICIONADO (O FIX DO ERRO)
    skills_menu_handler,        # <-- ADICIONADO (Skills)
    skills_equip_menu_handler,  # <-- ADICIONADO (Skills)
    equip_skill_handler,        # <-- ADICIONADO (Skills)
    unequip_skill_handler,      # <-- ADICIONADO (Skills)
    noop_handler,               # <-- ADICIONADO (Skills)
)
from handlers.inventory_handler import (
    inventory_handler,
    noop_inventory_handler,
)

# 3. Do painel de equipamentos
from handlers.equipment_handler import (
    equipment_menu_handler,
    equip_slot_handler,
    equip_pick_handler,
    equip_unequip_handler,
)

# 4. Das Classes e Evolução
from handlers.class_selection_handler import class_selection_handler
from handlers.class_evolution_handler import (
    status_evolution_open_handler,
    evolution_command_handler,
    evolution_callback_handler,
    evolution_do_handler,
    evolution_cancel_handler,
)

# 5. Das Profissões
from handlers.profession_handler import (
    job_menu_handler,
    job_pick_handler,
)


def register_character_handlers(application: Application):
    """Regista todos os handlers relacionados ao personagem."""

    # Handlers normais (irão para o group=0 por padrão)
    normal_handlers = [
        # Início e Criação (exceto o ladrão)
        start_command_handler,
        name_command_handler,
        
        # Status, Perfil, Inventário
        status_command_handler,
        status_open_handler,
        status_callback_handler,
        close_status_handler,       # <-- ADICIONADO
        
        profile_handler,
        character_command_handler,  # <-- ADICIONADO
        
        inventory_handler,
        noop_inventory_handler,
        
        # Handlers de Skills (Nova secção)
        skills_menu_handler,
        skills_equip_menu_handler,
        equip_skill_handler,
        unequip_skill_handler,
        noop_handler,
        
        # Equipamentos
        equipment_menu_handler,
        equip_slot_handler,
        equip_pick_handler,
        equip_unequip_handler,
        
        # Classes e Evolução
        class_selection_handler,
        status_evolution_open_handler,
        evolution_command_handler,
        evolution_callback_handler,
        evolution_do_handler,
        evolution_cancel_handler,
        
        # Profissões
        job_menu_handler,
        job_pick_handler,
    ]

    # --- CORREÇÃO APLICADA AQUI ---
    # Registramos os handlers normais primeiro
    application.add_handlers(normal_handlers)

    # Registramos o 'character_creation_handler' SEPARADAMENTE
    # e o colocamos no group=1 (prioridade menor)
    application.add_handler(character_creation_handler, group=1)
    # --- FIM DA CORREÇÃO ---