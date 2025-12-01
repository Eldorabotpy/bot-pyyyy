# handlers/guild_handler.py
# (VERSÃO FINAL: ORGANIZAÇÃO DE TRÁFEGO CORRETA)

import logging
from telegram.ext import CallbackQueryHandler

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. IMPORTAÇÃO DOS HANDLERS (COM TRATAMENTO DE ERROS)
# ==============================================================================

# --- Criação e Busca ---
try:
    from handlers.guild.creation_search import (
        clan_creation_conv_handler, 
        clan_search_conv_handler, 
        clan_apply_handler,
        clan_manage_apps_handler, 
        clan_app_accept_handler, 
        clan_app_decline_handler
    )
except ImportError as e:
    logger.error(f"Erro ao importar creation_search: {e}")
    clan_creation_conv_handler = None

# --- Gestão (Logo, Convites, Transferência) ---
try:
    from handlers.guild.management import (
        clan_logo_conv_handler,
        invite_conv_handler,
        clan_transfer_leader_conv_handler,
        clan_invite_accept_handler, 
        clan_invite_decline_handler,
        clan_delete_warn_handler,
        clan_delete_do_handler
    )
except ImportError as e:
    logger.error(f"Erro ao importar management: {e}")
    clan_logo_conv_handler = None

# --- Banco (Depósito/Saque) ---
try:
    from handlers.guild.bank import (
        clan_deposit_conv_handler, 
        clan_withdraw_conv_handler
    )
except ImportError as e:
    logger.error(f"Erro ao importar bank: {e}")
    clan_deposit_conv_handler = None

# --- Menu da Guilda (NPC) ---
from handlers.guild_menu_handler import adventurer_guild_handler

# --- ROTEADOR PRINCIPAL DO CLÃ (O Dashboard Inteligente) ---
# Este é o mais importante! Ele traz a lógica do dashboard.py com as correções.
from handlers.guild.dashboard import clan_handler as dashboard_router


# ==============================================================================
# 2. MONTAGEM DA LISTA (A ORDEM IMPORTA!)
# ==============================================================================

raw_handlers = [
    # 1. ConversationHandlers (Alta Prioridade)
    clan_creation_conv_handler,
    clan_search_conv_handler,
    clan_logo_conv_handler,
    invite_conv_handler,
    clan_deposit_conv_handler,
    clan_withdraw_conv_handler,
    clan_transfer_leader_conv_handler,

    # 2. Ações Específicas de Criação/Busca/Convite
    clan_apply_handler,
    clan_manage_apps_handler,
    clan_app_accept_handler,
    clan_app_decline_handler,
    clan_invite_accept_handler,
    clan_invite_decline_handler,
    clan_delete_warn_handler, 
    clan_delete_do_handler,

    # 3. Roteador Principal do Clã (Dashboard & Gestão Visual)
    # É AQUI que o botão 'clan_menu' vai cair e executar o código do dashboard.py
    dashboard_router,

    # 4. Guilda de Aventureiros (NPC)
    adventurer_guild_handler
]

# Filtra possíveis Nones (caso alguma importação falhe)
all_guild_handlers = [h for h in raw_handlers if h is not None]
