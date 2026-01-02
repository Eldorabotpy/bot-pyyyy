# registries/character.py
# (VERSÃO CORRIGIDA: ATUALIZADO PARA O NOVO SISTEMA DE PROFISSÕES)

import logging
from telegram.ext import Application, BaseHandler 

# 1. Do fluxo de início
from handlers.start_handler import start_command_handler

# 2. Do Status e Perfil
from handlers.status_handler import (
    status_command_handler,
    status_open_handler,
    status_callback_handler,
    close_status_handler,
)
from handlers.profile_handler import (
    profile_handler,
    character_command_handler,
    skills_menu_handler,
    skills_equip_menu_handler,
    equip_skill_handler,
    unequip_skill_handler,
    noop_handler,
)

# 3. Inventário e Conversor
from handlers.inventory_handler import (
    inventory_menu_handler,
    inventory_cat_handler,
    use_item_handler,
    noop_inventory_handler
)
from handlers.converter_handler import (
    converter_main_handler,
    converter_list_handler,
    converter_confirm_handler,
    converter_execute_handler,
)
from handlers.skin_handler import all_skin_handlers

# 4. Equipamentos
from handlers.equipment_handler import (
    equipment_menu_handler,
    equip_slot_handler,
    equip_pick_handler,
    equip_unequip_handler,
)

# 5. Classes e Evolução
from handlers.class_selection_handler import class_selection_handler
from handlers.class_evolution_handler import (
    status_evolution_open_handler,
    show_node_info_handler,
    complete_node_handler,
    start_trial_confirmation_handler,
    start_trial_execute_handler,
)

# 6. Profissões (ATUALIZADO)
from handlers.profession_handler import (
    job_menu_handler,
    job_pick_handler,
    job_list_handler,  # Substituiu job_view_handler
    job_do_handler,    # Substituiu job_confirm_handler
)

# 7. Menu do Reino
from telegram.ext import CallbackQueryHandler
from handlers.menu.kingdom import show_kingdom_menu
kingdom_menu_handler = CallbackQueryHandler(show_kingdom_menu, pattern=r'^continue_after_action$')

# 8. GUILDA E CLÃ
from handlers.guild_menu_handler import (
    adventurer_guild_handler, 
    clan_board_handler,
    mission_view_handler,
    mission_claim_handler
)
from handlers.guild_handler import all_guild_handlers

logger = logging.getLogger(__name__)

def register_character_handlers(application: Application):
    """Regista todos os handlers relacionados ao personagem (exceto login)."""

    # Lista inicial de handlers
    raw_handlers = [
        # --- PRIORIDADE MÁXIMA ---
        job_pick_handler,
        
        # O novo /menu (start_command_handler)
        start_command_handler,
        
        # Status
        status_command_handler,
        status_open_handler,
        status_callback_handler,
        close_status_handler,
        
        # Perfil e Reino
        profile_handler,
        character_command_handler,
        kingdom_menu_handler,
        
        # Inventário Novo
        inventory_menu_handler,
        inventory_cat_handler,
        use_item_handler,
        noop_inventory_handler,
        
        # Conversor
        converter_main_handler,
        converter_list_handler,
        converter_confirm_handler,
        converter_execute_handler,
        
        # Skills
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
        
        # Classes
        class_selection_handler,
        status_evolution_open_handler,
        show_node_info_handler,
        complete_node_handler,
        start_trial_confirmation_handler,
        start_trial_execute_handler,
        
        # Profissões (ATUALIZADO)
        job_menu_handler,
        job_list_handler,     
        job_do_handler,  
        
        # --- SISTEMA DE GUILDA ---
        adventurer_guild_handler,
        clan_board_handler,
        mission_view_handler,
        mission_claim_handler
    ]
    
    # Adiciona listas externas
    if all_skin_handlers:
        raw_handlers.extend(all_skin_handlers)
    
    if all_guild_handlers:
        raw_handlers.extend(all_guild_handlers)
    
    # === FILTRO DE SEGURANÇA ===
    clean_handlers = []
    for h in raw_handlers:
        if isinstance(h, BaseHandler):
            clean_handlers.append(h)
        elif h is None:
            continue
        else:
            logger.warning(f"⚠️ Ignorando handler inválido no registro: {type(h)}")

    # Registra apenas os handlers válidos e limpos
    application.add_handlers(clean_handlers)