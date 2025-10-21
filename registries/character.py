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
)
from handlers.profile_handler import profile_handler
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

    handlers_to_add = [
        # Início e Criação
        start_command_handler,
        name_command_handler,
        character_creation_handler,
        # Status, Perfil, Inventário
        status_command_handler,
        status_open_handler,
        status_callback_handler,
        profile_handler,
        inventory_handler,
        noop_inventory_handler,
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

    application.add_handlers(handlers_to_add)