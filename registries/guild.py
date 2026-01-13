# registries/guild.py
# (VERSÃO FINAL: Todos os botões de gestão registrados e funcionais)

from telegram.ext import Application

# --- Importação dos ConversationHandlers (Alta Prioridade) ---
from handlers.guild.creation_search import (
    clan_creation_conv_handler, 
    clan_search_conv_handler
)
from handlers.guild.management import (
    invite_conv_handler, 
    clan_transfer_leader_conv_handler, 
    clan_logo_conv_handler
)
from handlers.guild.bank import (
    clan_deposit_conv_handler, 
    clan_withdraw_conv_handler
)

# --- Importação dos CallbackHandlers Específicos ---
from handlers.guild.creation_search import (
    clan_create_menu_handler,
    clan_apply_handler,
    clan_manage_apps_handler,
    clan_app_accept_handler,
    clan_app_decline_handler
)

# 👇 IMPORTAÇÃO DOS HANDLERS DE GESTÃO (ATUALIZADO) 👇
from handlers.guild.management import (
    clan_manage_menu_handler,
    clan_view_members_handler,
    
    # Novos Handlers de Perfil e Hierarquia
    clan_profile_handler,       # <--- NOVO
    clan_setrank_menu_handler,  # <--- NOVO
    clan_do_rank_handler,       # <--- NOVO
    
    # Convites
    clan_invite_accept_handler,
    clan_invite_decline_handler,
    
    # Cargos (Legado/Compatibilidade)
    clan_promote_handler,
    clan_demote_handler,
    
    # Expulsar
    clan_kick_menu_handler,
    clan_kick_ask_handler,
    clan_kick_do_handler,
    
    # Sair
    clan_leave_warn_handler,
    clan_leave_do_handler,
    
    # Deletar (Dissolver)
    clan_delete_warn_handler,
    clan_delete_do_handler
)

# --- Importação dos Handlers de Missão (Se necessário registro explícito) ---
try:
    from handlers.guild.missions import (
        clan_mission_start_handler,
        clan_guild_mission_details_handler,
        clan_mission_accept_handler,
        clan_mission_finish_handler,
        clan_mission_cancel_handler
    )
except ImportError:
    clan_mission_start_handler = None

from handlers.guild.war import (
    war_menu_handler,
    war_ranking_handler
)

# --- Importação do Router Principal (Dashboard) ---
from handlers.guild.dashboard import clan_handler

def register_guild_handlers(application: Application):
    """
    Registra todos os handlers do sistema de Guilda/Clã.
    """
    print("🛡️ [REGISTRY] Registrando Módulo de Guilda (Completo)...")

    # 1. Conversation Handlers (Prioridade Máxima)
    application.add_handler(clan_creation_conv_handler)
    application.add_handler(clan_search_conv_handler)
    
    application.add_handler(invite_conv_handler)
    application.add_handler(clan_transfer_leader_conv_handler)
    application.add_handler(clan_logo_conv_handler)
    
    application.add_handler(clan_deposit_conv_handler)
    application.add_handler(clan_withdraw_conv_handler)

    # 2. Criação e Busca
    application.add_handler(clan_create_menu_handler)
    application.add_handler(clan_apply_handler)
    application.add_handler(clan_manage_apps_handler)
    application.add_handler(clan_app_accept_handler)
    application.add_handler(clan_app_decline_handler)

    # 3. Gestão de Membros e Hierarquia
    application.add_handler(clan_manage_menu_handler)
    application.add_handler(clan_view_members_handler)
    
    # Novos Handlers de Perfil (Ficha RPG e Cargos)
    application.add_handler(clan_profile_handler)
    application.add_handler(clan_setrank_menu_handler)
    application.add_handler(clan_do_rank_handler)
    
    application.add_handler(clan_invite_accept_handler)
    application.add_handler(clan_invite_decline_handler)
    
    # Legado (Mantido para segurança)
    application.add_handler(clan_promote_handler)
    application.add_handler(clan_demote_handler)
    
    # Expulsão e Saída
    application.add_handler(clan_kick_menu_handler)
    application.add_handler(clan_kick_ask_handler)
    application.add_handler(clan_kick_do_handler)
    
    application.add_handler(clan_leave_warn_handler)
    application.add_handler(clan_leave_do_handler)
    
    application.add_handler(clan_delete_warn_handler)
    application.add_handler(clan_delete_do_handler)
    
    # 4. Missões (Registro Explícito para garantir prioridade sobre o Router)
    if clan_mission_start_handler:
        application.add_handler(clan_mission_start_handler)
        application.add_handler(clan_guild_mission_details_handler)
        application.add_handler(clan_mission_accept_handler)
        application.add_handler(clan_mission_finish_handler)
        application.add_handler(clan_mission_cancel_handler)

    # 5. Sistema de Guerra
    application.add_handler(war_menu_handler)
    application.add_handler(war_ranking_handler)

    # 6. Router Principal (Dashboard)
    # Pega tudo que sobrar com 'clan_' (como navegação e botões genéricos)
    application.add_handler(clan_handler)

    print("✅ [REGISTRY] Guilda registrada com sucesso.")