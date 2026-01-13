# registries/guild.py
# (VERSÃO CORRIGIDA: Imports dos Cargos Adicionados)

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

# 👇 ADICIONAMOS OS HANDLERS DE CARGO AQUI
from handlers.guild.management import (
    clan_invite_accept_handler,
    clan_invite_decline_handler,
    clan_promote_handler,  # <--- NOVO
    clan_demote_handler    # <--- NOVO
)

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
    print("🛡️ [REGISTRY] Registrando Módulo de Guilda (Com Sistema de Cargos)...")

    # 1. Conversation Handlers
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

    # 3. Convites e Gestão
    application.add_handler(clan_invite_accept_handler)
    application.add_handler(clan_invite_decline_handler)
    
    # 👇 Registra os botões de Promover/Rebaixar
    application.add_handler(clan_promote_handler)
    application.add_handler(clan_demote_handler)
    
    # 4. Guerra
    application.add_handler(war_menu_handler)
    application.add_handler(war_ranking_handler)

    # 5. Router Principal (Dashboard)
    application.add_handler(clan_handler)

    print("✅ [REGISTRY] Guilda registrada com sucesso.")