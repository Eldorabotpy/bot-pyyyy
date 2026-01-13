# registries/guild.py
# (VERSÃO ATIVADA: REGISTRO CENTRAL DO NOVO SISTEMA DE GUILDA)

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
# Estes cuidam de lógicas que não passam pelo Router principal ou são entry points externos
from handlers.guild.creation_search import (
    clan_create_menu_handler,
    clan_apply_handler,
    clan_manage_apps_handler,
    clan_app_accept_handler,
    clan_app_decline_handler
)

from handlers.guild.management import (
    clan_invite_accept_handler,
    clan_invite_decline_handler,
    # clan_manage_menu_handler (Coberto pelo router, mas pode ser importado se necessário)
)

from handlers.guild.war import (
    war_menu_handler,
    war_ranking_handler
)

# --- Importação do Router Principal (Dashboard) ---
# Este handler captura a maioria dos padrões 'clan_' e 'gld_' para navegação interna
from handlers.guild.dashboard import clan_handler

def register_guild_handlers(application: Application):
    """
    Registra todos os handlers do sistema de Guilda/Clã.
    Ordem: Conversations -> Specific Callbacks -> General Router
    """
    print("🛡️ [REGISTRY] Registrando Módulo de Guilda...")

    # 1. Conversation Handlers (Devem vir primeiro para capturar estados)
    application.add_handler(clan_creation_conv_handler)
    application.add_handler(clan_search_conv_handler)
    
    application.add_handler(invite_conv_handler)
    application.add_handler(clan_transfer_leader_conv_handler)
    application.add_handler(clan_logo_conv_handler)
    
    application.add_handler(clan_deposit_conv_handler)
    application.add_handler(clan_withdraw_conv_handler)

    # 2. Handlers de Criação e Busca (Entry Points)
    application.add_handler(clan_create_menu_handler)
    application.add_handler(clan_apply_handler)
    application.add_handler(clan_manage_apps_handler)
    application.add_handler(clan_app_accept_handler)
    application.add_handler(clan_app_decline_handler)

    # 3. Handlers de Convite Externo (Aceitar/Recusar via PM ou Chat)
    application.add_handler(clan_invite_accept_handler)
    application.add_handler(clan_invite_decline_handler)
    
    # 4. Sistema de Guerra
    application.add_handler(war_menu_handler)
    application.add_handler(war_ranking_handler)

    # 5. Router Principal (Dashboard e Navegação Interna)
    # Captura patterns: r'^clan_|^gld_'
    # Colocado por último para não interceptar callbacks específicos acima se houver conflito de regex
    application.add_handler(clan_handler)

    print("✅ [REGISTRY] Guilda registrada com sucesso.")