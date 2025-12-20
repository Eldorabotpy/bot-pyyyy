# registries/class_evolution.py

from telegram.ext import Application, CallbackQueryHandler
from handlers import class_evolution_handler as evo_h
# 👇 Importe o novo módulo
from modules import evolution_battle 

def register_evolution_handlers(app: Application):
    """Registra todos os handlers para o menu de evolução de classe."""
    
    # 1. Menu Principal
    app.add_handler(CallbackQueryHandler(
        evo_h.open_evolution_menu, 
        pattern=r'^open_evolution_menu$'
    ))
    
    # 2. Handlers da Árvore
    app.add_handler(CallbackQueryHandler(
        evo_h.show_node_info, 
        pattern=r'^evo_node_info:'
    ))
    app.add_handler(CallbackQueryHandler(
        evo_h.complete_node, 
        pattern=r'^evo_complete_node:'
    ))
    
    # 3. Handlers do Teste (Confirmação e Apresentação)
    app.add_handler(CallbackQueryHandler(
        evo_h.start_trial_confirmation, 
        pattern=r'^evo_start_trial_confirm:'
    ))
    app.add_handler(CallbackQueryHandler(
        evo_h.start_trial_execute, 
        pattern=r'^evo_start_trial_execute:'
    ))

    # 4. Skills
    app.add_handler(CallbackQueryHandler(
        evo_h.show_skill_ascension_menu,
        pattern=r'^evo_skill_ascend_menu$'
    ))
    app.add_handler(CallbackQueryHandler(
        evo_h.show_skill_ascension_info,
        pattern=r'^evo_skill_ascend_info:'
    ))
    app.add_handler(CallbackQueryHandler(
        evo_h.confirm_skill_ascension,
        pattern=r'^evo_skill_ascend_confirm:'
    ))

    # 👇 5. HANDLER DO COMBATE (O PASSO QUE FALTAVA) 👇
    app.add_handler(CallbackQueryHandler(
        evolution_battle.start_evo_combat_callback,
        pattern=r'^start_evo_combat$'
    ))