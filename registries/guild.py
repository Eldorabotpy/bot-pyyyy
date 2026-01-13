# registries/guild.py
# CORREÇÃO: Registra os novos botões (clan_profile, clan_setrank) para que eles respondam

from telegram.ext import Application

# --- Conversas (Fluxos longos) ---
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

# --- Callbacks (Cliques de botão) ---
from handlers.guild.creation_search import (
    clan_create_menu_handler,
    clan_apply_handler,
    clan_manage_apps_handler,
    clan_app_accept_handler,
    clan_app_decline_handler
)

# AQUI ESTÁ A CORREÇÃO: Importando os novos handlers que você pediu
from handlers.guild.management import (
    clan_manage_menu_handler,
    clan_view_members_handler,  # Lista de Membros
    
    # NOVOS (Essenciais para o clique no nome funcionar)
    clan_profile_handler,       # Abre o perfil do membro
    clan_setrank_menu_handler,  # Abre o menu de cargos
    clan_do_rank_handler,       # Executa a troca de cargo
    
    # Ações Extras
    clan_invite_accept_handler,
    clan_invite_decline_handler,
    clan_promote_handler,       # Mantido para compatibilidade
    clan_demote_handler,        # Mantido para compatibilidade
    clan_kick_menu_handler,
    clan_kick_ask_handler,
    clan_kick_do_handler,
    clan_leave_warn_handler,
    clan_leave_do_handler,
    clan_delete_warn_handler,
    clan_delete_do_handler
)

from handlers.guild.war import (
    war_menu_handler,
    war_ranking_handler
)

# Roteador Principal (Dashboard)
from handlers.guild.dashboard import clan_handler

# Tenta importar missões (se existir)
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

def register_guild_handlers(application: Application):
    """
    Registra todos os handlers do sistema de Guilda/Clã.
    """
    print("🛡️ [REGISTRY] Conectando botões de Guilda...")

    # 1. Conversations (Prioridade Máxima)
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

    # 3. Gestão de Membros (CORREÇÃO AQUI)
    application.add_handler(clan_manage_menu_handler)
    application.add_handler(clan_view_members_handler)
    
    # Registra os botões novos para não ficarem mudos
    application.add_handler(clan_profile_handler)       # <--- FAZ O CLIQUE NO NOME RESPONDER
    application.add_handler(clan_setrank_menu_handler)  # <--- FAZ O MENU DE CARGO ABRIR
    application.add_handler(clan_do_rank_handler)       # <--- FAZ O CARGO MUDAR
    
    application.add_handler(clan_invite_accept_handler)
    application.add_handler(clan_invite_decline_handler)
    application.add_handler(clan_promote_handler)
    application.add_handler(clan_demote_handler)
    application.add_handler(clan_kick_menu_handler)
    application.add_handler(clan_kick_ask_handler)
    application.add_handler(clan_kick_do_handler)
    application.add_handler(clan_leave_warn_handler)
    application.add_handler(clan_leave_do_handler)
    application.add_handler(clan_delete_warn_handler)
    application.add_handler(clan_delete_do_handler)
    
    # 4. Missões
    if clan_mission_start_handler:
        application.add_handler(clan_mission_start_handler)
        application.add_handler(clan_guild_mission_details_handler)
        application.add_handler(clan_mission_accept_handler)
        application.add_handler(clan_mission_finish_handler)
        application.add_handler(clan_mission_cancel_handler)

    # 5. Guerra e Dashboard
    application.add_handler(war_menu_handler)
    application.add_handler(war_ranking_handler)
    
    # Roteador genérico (pega o resto)
    application.add_handler(clan_handler)

    print("✅ [REGISTRY] Botões de Guilda conectados.")