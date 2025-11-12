# registries/class_evolution.py

from telegram.ext import Application, CallbackQueryHandler
from handlers import class_evolution_handler as evo_h

def register_evolution_handlers(app: Application):
    """Registra todos os handlers para o menu de evolução de classe."""
    
    app.add_handler(CallbackQueryHandler(
        evo_h.open_evolution_menu, 
        pattern=r'^open_evolution_menu$'
    ))
    
    # Handlers da Árvore (Novos)
    app.add_handler(CallbackQueryHandler(
        evo_h.show_node_info, 
        pattern=r'^evo_node_info:'
    ))
    app.add_handler(CallbackQueryHandler(
        evo_h.complete_node, 
        pattern=r'^evo_complete_node:'
    ))
    
    # Handlers do Teste (Trial)
    app.add_handler(CallbackQueryHandler(
        evo_h.start_trial_confirmation, 
        pattern=r'^evo_start_trial_confirm:'
    ))
    app.add_handler(CallbackQueryHandler(
        evo_h.start_trial_execute, 
        pattern=r'^evo_start_trial_execute:'
    ))
    
