# registries/class_evolution.py
# (VERSÃO ATUALIZADA: Registra Ascensão + Novo Sistema de Skills)

from telegram.ext import Application, CallbackQueryHandler
from handlers import class_evolution_handler as evo_h
from handlers import skill_upgrade_handler as skill_h  # <--- Importa o novo handler

def register_evolution_handlers(app: Application):
    """Registra todos os handlers para evolução de classe e skills."""
    
    # ====================================================
    # 1. SISTEMA DE EVOLUÇÃO (ÁRVORE E TESTE)
    # ====================================================
    
    # Menu Principal da Ascensão
    app.add_handler(CallbackQueryHandler(
        evo_h.open_evolution_menu, 
        pattern=r'^open_evolution_menu$'
    ))
    
    # Nós da Árvore (Ver info e Completar)
    app.add_handler(CallbackQueryHandler(
        evo_h.show_node_info, 
        pattern=r'^evo_node_info:'
    ))
    app.add_handler(CallbackQueryHandler(
        evo_h.complete_node, 
        pattern=r'^evo_complete_node:'
    ))
    
    # Teste de Batalha (Confirmação e Início)
    app.add_handler(CallbackQueryHandler(
        evo_h.start_trial_confirmation, 
        pattern=r'^evo_start_trial_confirm:'
    ))
    app.add_handler(CallbackQueryHandler(
        evo_h.start_trial_execute, 
        pattern=r'^evo_start_trial_execute:'
    ))
    
    # Batalha de Evolução (Engine Visual)
    app.add_handler(evo_h.evo_battle_start_handler)

    # ====================================================
    # 2. NOVO SISTEMA DE SKILLS (GRIMOIRE)
    # ====================================================
    
    # Menu Principal de Skills (Lista)
    app.add_handler(CallbackQueryHandler(
        skill_h.menu_skills_main_callback,
        pattern=r'^menu_skills_main$'
    ))
    
    # Detalhes da Skill (Info + Botão Upar)
    app.add_handler(CallbackQueryHandler(
        skill_h.skill_detail_callback,
        pattern=r'^skill_detail:'
    ))
    
    # Ação de Upar (Upgrade)
    app.add_handler(CallbackQueryHandler(
        skill_h.skill_upgrade_action_callback,
        pattern=r'^skill_upgrade_do:'
    ))

    # (Os handlers antigos 'evo_skill_ascend_...' foram removidos pois não usamos mais)# registries/class_evolution.py
# (VERSÃO ATUALIZADA: Registra Ascensão + Novo Sistema de Skills)

from telegram.ext import Application, CallbackQueryHandler
from handlers import class_evolution_handler as evo_h
from handlers import skill_upgrade_handler as skill_h  # <--- Importa o novo handler

def register_evolution_handlers(app: Application):
    """Registra todos os handlers para evolução de classe e skills."""
    
    # ====================================================
    # 1. SISTEMA DE EVOLUÇÃO (ÁRVORE E TESTE)
    # ====================================================
    
    # Menu Principal da Ascensão
    app.add_handler(CallbackQueryHandler(
        evo_h.open_evolution_menu, 
        pattern=r'^open_evolution_menu$'
    ))
    
    # Nós da Árvore (Ver info e Completar)
    app.add_handler(CallbackQueryHandler(
        evo_h.show_node_info, 
        pattern=r'^evo_node_info:'
    ))
    app.add_handler(CallbackQueryHandler(
        evo_h.complete_node, 
        pattern=r'^evo_complete_node:'
    ))
    
    # Teste de Batalha (Confirmação e Início)
    app.add_handler(CallbackQueryHandler(
        evo_h.start_trial_confirmation, 
        pattern=r'^evo_start_trial_confirm:'
    ))
    app.add_handler(CallbackQueryHandler(
        evo_h.start_trial_execute, 
        pattern=r'^evo_start_trial_execute:'
    ))
    
    # Batalha de Evolução (Engine Visual)
    app.add_handler(evo_h.evo_battle_start_handler)

    # ====================================================
    # 2. NOVO SISTEMA DE SKILLS (GRIMOIRE)
    # ====================================================
    
    # Menu Principal de Skills (Lista)
    app.add_handler(CallbackQueryHandler(
        skill_h.menu_skills_main_callback,
        pattern=r'^menu_skills_main$'
    ))
    
    # Detalhes da Skill (Info + Botão Upar)
    app.add_handler(CallbackQueryHandler(
        skill_h.skill_detail_callback,
        pattern=r'^skill_detail:'
    ))
    
    # Ação de Upar (Upgrade)
    app.add_handler(CallbackQueryHandler(
        skill_h.skill_upgrade_action_callback,
        pattern=r'^skill_upgrade_do:'
    ))

    # (Os handlers antigos 'evo_skill_ascend_...' foram removidos pois não usamos mais)