# handlers/guild_handler.py
# (VERSÃO FINAL: TODAS AS FUNÇÕES ATIVAS E ORGANIZADAS)

import logging
from telegram.ext import CallbackQueryHandler

logger = logging.getLogger(__name__)

# --- Criação e Busca ---
try:
    from handlers.guild.creation_search import (
        clan_create_menu_handler,
        clan_creation_conv_handler, clan_search_conv_handler, clan_apply_handler,
        clan_manage_apps_handler, clan_app_accept_handler, clan_app_decline_handler
    )
except ImportError: clan_creation_conv_handler = None

# --- Gestão ---
try:
    from handlers.guild.management import (
        clan_logo_conv_handler, invite_conv_handler, clan_transfer_leader_conv_handler,
        clan_invite_accept_handler, clan_invite_decline_handler,
        clan_delete_warn_handler, clan_delete_do_handler
    )
except ImportError: clan_logo_conv_handler = None

# --- Banco ---
try:
    from handlers.guild.bank import (clan_deposit_conv_handler, clan_withdraw_conv_handler)
except ImportError: clan_deposit_conv_handler = None

# --- Guilda Pessoal (NPC) e Missões Pessoais ---
from handlers.guild_menu_handler import (
    adventurer_guild_handler, 
    mission_view_handler,   # <--- ESSE É O QUE FALTAVA
    mission_claim_handler   # <--- E ESSE TAMBÉM
)

# --- Roteador Principal do Clã (Dashboard) ---
from handlers.guild.dashboard import clan_handler as dashboard_router

# ==============================================================================
# LISTA DE HANDLERS (A ORDEM IMPORTA!)
# ==============================================================================
raw_handlers = [
    # 1. Conversations (Alta Prioridade)
    clan_creation_conv_handler,
    clan_search_conv_handler,
    clan_logo_conv_handler,
    invite_conv_handler,
    clan_deposit_conv_handler,
    clan_withdraw_conv_handler,
    clan_transfer_leader_conv_handler,

    # 2. Menu de Criação Direto
    clan_create_menu_handler,

    # 3. Ações Simples de Clã
    clan_apply_handler,
    clan_manage_apps_handler,
    clan_app_accept_handler,
    clan_app_decline_handler,
    clan_invite_accept_handler,
    clan_invite_decline_handler,
    clan_delete_warn_handler,
    clan_delete_do_handler,

    # 4. Missões PESSOAIS (Agora elas vão responder!)
    mission_view_handler,
    mission_claim_handler,

    # 5. Roteador Geral do Clã
    dashboard_router,

    # 6. Menu Principal da Guilda
    adventurer_guild_handler
]

all_guild_handlers = [h for h in raw_handlers if h is not None]
logger.info(f"Handlers carregados: {len(all_guild_handlers)}")