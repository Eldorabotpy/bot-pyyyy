# registries/guild.py
# CORREÇÃO: Registra todos os handlers necessários para Guilda/Clã,
# evitando botões mudos (Perfil, Kingdom, lista de membros, cargos, etc.)

from telegram.ext import Application

# ============================================================================
# CONVERSATIONS (Fluxos longos – prioridade máxima)
# ============================================================================

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

# ============================================================================
# CALLBACKS DE CRIAÇÃO / BUSCA
# ============================================================================

from handlers.guild.creation_search import (
    clan_create_menu_handler,
    clan_apply_handler,
    clan_manage_apps_handler,
    clan_app_accept_handler,
    clan_app_decline_handler
)

# ============================================================================
# GESTÃO DE MEMBROS E CARGOS  (ESSENCIAL PARA NÃO FICAR MUDO)
# ============================================================================

from handlers.guild.management import (
    clan_manage_menu_handler,
    clan_view_members_handler,

    # PERFIL E CARGOS
    clan_profile_handler,
    clan_setrank_menu_handler,
    clan_do_rank_handler,

    # Ações diversas
    clan_invite_accept_handler,
    clan_invite_decline_handler,
    clan_promote_handler,    # compatibilidade
    clan_demote_handler,     # compatibilidade
    clan_kick_menu_handler,
    clan_kick_ask_handler,
    clan_kick_do_handler,
    clan_leave_warn_handler,
    clan_leave_do_handler,
    clan_delete_warn_handler,
    clan_delete_do_handler
)

# ============================================================================
# GUERRA DE CLÃS
# ============================================================================

from handlers.guild.war import (
    war_menu_handler,
    war_ranking_handler
)

# ============================================================================
# DASHBOARD / ROTEADOR PRINCIPAL DO CLÃ
# ============================================================================

from handlers.guild.dashboard import clan_handler

# ============================================================================
# MISSÕES DE CLÃ (opcional)
# ============================================================================

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


# ============================================================================
# REGISTRO CENTRAL
# ============================================================================

def register_guild_handlers(application: Application):
    """
    Registra todos os handlers do sistema de Guilda/Clã.
    A ORDEM IMPORTA.
    """
    print("🛡️ [REGISTRY] Conectando botões de Guilda...")

    # ----------------------------------------------------------------------
    # 1. CONVERSATIONS (PRIORIDADE MÁXIMA)
    # ----------------------------------------------------------------------
    application.add_handler(clan_creation_conv_handler)
    application.add_handler(clan_search_conv_handler)
    application.add_handler(invite_conv_handler)
    application.add_handler(clan_transfer_leader_conv_handler)
    application.add_handler(clan_logo_conv_handler)
    application.add_handler(clan_deposit_conv_handler)
    application.add_handler(clan_withdraw_conv_handler)

    # ----------------------------------------------------------------------
    # 2. CRIAÇÃO / BUSCA
    # ----------------------------------------------------------------------
    application.add_handler(clan_create_menu_handler)
    application.add_handler(clan_apply_handler)
    application.add_handler(clan_manage_apps_handler)
    application.add_handler(clan_app_accept_handler)
    application.add_handler(clan_app_decline_handler)

    # ----------------------------------------------------------------------
    # 3. GESTÃO DE MEMBROS E CARGOS (CORREÇÃO CRÍTICA)
    # ----------------------------------------------------------------------
    application.add_handler(clan_manage_menu_handler)
    application.add_handler(clan_view_members_handler)

    # PERFIL E CARGOS — SEM ISSO O CLIQUE FICA MUDO
    application.add_handler(clan_profile_handler)
    application.add_handler(clan_setrank_menu_handler)
    application.add_handler(clan_do_rank_handler)

    # AÇÕES
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

    # ----------------------------------------------------------------------
    # 4. MISSÕES DE CLÃ
    # ----------------------------------------------------------------------
    if clan_mission_start_handler:
        application.add_handler(clan_mission_start_handler)
        application.add_handler(clan_guild_mission_details_handler)
        application.add_handler(clan_mission_accept_handler)
        application.add_handler(clan_mission_finish_handler)
        application.add_handler(clan_mission_cancel_handler)

    # ----------------------------------------------------------------------
    # 5. GUERRA E DASHBOARD
    # ----------------------------------------------------------------------
    application.add_handler(war_menu_handler)
    application.add_handler(war_ranking_handler)

    # ROTEADOR FINAL (SEMPRE POR ÚLTIMO)
    application.add_handler(clan_handler)

    print("✅ [REGISTRY] Botões de Guilda conectados.")
