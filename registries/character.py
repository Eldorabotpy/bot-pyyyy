# registries/character.py
# (VERSÃO FINAL: CONECTANDO GUILDA, CLÃ E INVENTÁRIO NOVO)

from telegram.ext import Application

# 1. Do fluxo de início e criação de personagem
from handlers.start_handler import (
    start_command_handler,
    name_command_handler,
    character_creation_handler,
)

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

# 3. Inventário e Conversor (Atualizado)
from handlers.inventory_handler import (
    inventory_menu_handler,   # Menu Principal
    inventory_cat_handler,    # Categorias
    use_item_handler,         # Usar Item
    noop_inventory_handler    # Travas de Classe
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

# 6. Profissões (Atualizado)
from handlers.profession_handler import (
    job_menu_handler,
    job_view_handler,     
    job_confirm_handler,  
    job_guide_handler,    
)

# 7. Menu do Reino (Atualizado)
from handlers.menu.kingdom import show_kingdom_menu # Se você tiver um handler específico para o callback, importe aqui. 
# Geralmente o reino é chamado via callback, então precisamos do handler dele se ele não estiver em outro lugar.
# Assumindo que existe um handler para 'continue_after_action' ou similar que chama o reino:
from telegram.ext import CallbackQueryHandler
kingdom_menu_handler = CallbackQueryHandler(show_kingdom_menu, pattern=r'^continue_after_action$')

# 8. GUILDA E CLÃ (AQUI ESTÁ A MUDANÇA CRÍTICA)
# Importa o NPC da Guilda
from handlers.guild_menu_handler import adventurer_guild_handler, clan_board_handler

# Importa todos os handlers do Clã de uma vez (que definimos na lista 'all_guild_handlers')
from handlers.guild_handler import all_guild_handlers


def register_character_handlers(application: Application):
    """Regista todos os handlers relacionados ao personagem."""

    # Handlers normais (group=0)
    normal_handlers = [
        # Básicos
        start_command_handler,
        name_command_handler,
        status_command_handler,
        status_open_handler,
        status_callback_handler,
        close_status_handler,
        
        # Perfil e Reino
        profile_handler,
        character_command_handler,
        kingdom_menu_handler, # Botão de voltar
        
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
        
        # Profissões
        job_menu_handler,
        job_view_handler,     
        job_confirm_handler,  
        job_guide_handler,    
        
        # --- SISTEMA DE GUILDA (NOVO) ---
        adventurer_guild_handler, # Menu da Instituição (NPC)
        clan_board_handler,       # Quadro de Missões do Clã
    ]
    
    # Adiciona Skins
    normal_handlers.extend(all_skin_handlers)
    
    # Adiciona TODOS os handlers de Clã (Banco, Gestão, Criação...)
    # Isso importa a lista que criamos no final do guild_handler.py
    normal_handlers.extend(all_guild_handlers)
    
    # Registra tudo
    application.add_handlers(normal_handlers)

    # Registra criação de personagem (prioridade menor)
    application.add_handler(character_creation_handler, group=1)