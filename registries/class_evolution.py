# registries/class_evolution.py
# (VERSÃO FINAL: Conecta o botão azul ao novo arquivo de Skills)

from telegram.ext import Application, CallbackQueryHandler
from handlers import class_evolution_handler as evo_h

# --- IMPORTAÇÃO SEGURA DO NOVO HANDLER ---
# Isso garante que o bot encontre o arquivo 'skill_upgrade_handler.py' na pasta handlers
import handlers.skill_upgrade_handler as skill_h

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
    # 2. NOVO SISTEMA DE SKILLS (O BOTÃO AZUL 📘)
    # ====================================================
    
    # É aqui que a mágica acontece. Registramos os listeners para o novo menu.
    
    # 1. Abre a lista de skills
    app.add_handler(CallbackQueryHandler(
        skill_h.menu_skills_main_callback,
        pattern=r'^menu_skills_main$'
    ))
    
    # 2. Mostra detalhes e preço da skill
    app.add_handler(CallbackQueryHandler(
        skill_h.skill_detail_callback,
        pattern=r'^skill_detail:'
    ))
    
    # 3. Executa a compra/upgrade
    app.add_handler(CallbackQueryHandler(
        skill_h.skill_upgrade_action_callback,
        pattern=r'^skill_upgrade_do:'
    ))