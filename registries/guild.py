# registries/guild.py
# REGISTRY COMPLETO DO SISTEMA DE GUILDA / CLÃ
# (inclui: Guilda de Aventureiros (NPC) + Clã (guilda real) + Banco + Missões + Guerra)

from telegram.ext import Application, CallbackQueryHandler

# ==============================================================================
# CONVERSATIONS (Fluxos longos – prioridade máxima)
# ==============================================================================
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

# ==============================================================================
# CALLBACKS – CRIAÇÃO / BUSCA
# ==============================================================================
from handlers.guild.creation_search import (
    clan_create_menu_handler,
    clan_apply_handler,
    clan_manage_apps_handler,
    clan_app_accept_handler,
    clan_app_decline_handler
)

# ==============================================================================
# CALLBACKS – GESTÃO DE MEMBROS / PERFIL / CARGOS / LIMPEZA
# ==============================================================================
from handlers.guild.management import (
    clan_manage_menu_handler,
    clan_view_members_handler,

    # PERFIL E CARGOS
    clan_profile_handler,
    clan_setrank_menu_handler,
    clan_do_rank_handler,

    # LIMPEZA (LEGADOS / INVÁLIDOS)
    clan_cleanup_menu_handler,
    clan_cleanup_apps_handler,
    clan_cleanup_members_handler,

    # AÇÕES DIVERSAS
    clan_invite_accept_handler,
    clan_invite_decline_handler,
    clan_promote_handler,
    clan_demote_handler,
    clan_kick_menu_handler,
    clan_kick_ask_handler,
    clan_kick_do_handler,
    clan_leave_warn_handler,
    clan_leave_do_handler,
    clan_delete_warn_handler,
    clan_delete_do_handler
)

# ==============================================================================
# GUERRA (handlers.guild.war) — manter, mas evitar colisão
# ==============================================================================
from handlers.guild.war import (
    war_menu_handler,
    war_ranking_handler,
)

# ==============================================================================
# MISSÕES (opcional – protegido por try)
# ==============================================================================
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
    clan_guild_mission_details_handler = None
    clan_mission_accept_handler = None
    clan_mission_finish_handler = None
    clan_mission_cancel_handler = None

# ==============================================================================
# DASHBOARD / ROTEADOR FINAL DO CLÃ
# ==============================================================================
from handlers.guild.dashboard import clan_handler, show_clan_dashboard, show_clan_war_menu

# ==============================================================================
# ✅ GUILDA DE AVENTUREIROS (NPC)
# ==============================================================================
from handlers.guild_menu_handler import (
    adventurer_guild_handler,
    mission_view_handler,
    mission_claim_handler,
    clan_board_handler,
)

# ==============================================================================
# ✅ FIX: botão "Acessar Meu Clã" (callback_data="clan_menu")
# ==============================================================================
clan_menu_shortcut_handler = CallbackQueryHandler(
    show_clan_dashboard,
    pattern=r"^clan_menu$"
)

# ==============================================================================
# ✅ FIX: atalho dedicado para a aba Guerra do Dashboard (blindagem)
# ==============================================================================
clan_war_menu_shortcut_handler = CallbackQueryHandler(
    show_clan_war_menu,
    pattern=r"^clan_war_menu$"
)

# ==============================================================================
# REGISTRO PRINCIPAL
# ==============================================================================
def register_guild_handlers(application: Application):
    """
    Registra TODOS os handlers do sistema de Guilda/Clã.
    A ordem é crítica: específicos primeiro, genéricos por último.
    """
    print("🛡️ [REGISTRY] Conectando botões de Guilda...")

    # --------------------------------------------------------------------------
    # 1) CONVERSATIONS (prioridade máxima)
    # --------------------------------------------------------------------------
    application.add_handler(clan_creation_conv_handler)
    application.add_handler(clan_search_conv_handler)
    application.add_handler(invite_conv_handler)
    application.add_handler(clan_transfer_leader_conv_handler)
    application.add_handler(clan_logo_conv_handler)
    application.add_handler(clan_deposit_conv_handler)
    application.add_handler(clan_withdraw_conv_handler)

    # --------------------------------------------------------------------------
    # 2) CRIAÇÃO E BUSCA DE CLÃ
    # --------------------------------------------------------------------------
    application.add_handler(clan_create_menu_handler)
    application.add_handler(clan_apply_handler)
    application.add_handler(clan_manage_apps_handler)
    application.add_handler(clan_app_accept_handler)
    application.add_handler(clan_app_decline_handler)

    # --------------------------------------------------------------------------
    # 3) GESTÃO DE MEMBROS / PERFIL / CARGOS / LIMPEZA
    # --------------------------------------------------------------------------
    application.add_handler(clan_manage_menu_handler)
    application.add_handler(clan_view_members_handler)

    # PERFIL / CARGOS
    application.add_handler(clan_profile_handler)
    application.add_handler(clan_setrank_menu_handler)
    application.add_handler(clan_do_rank_handler)

    # LIMPEZA
    application.add_handler(clan_cleanup_menu_handler)
    application.add_handler(clan_cleanup_apps_handler)
    application.add_handler(clan_cleanup_members_handler)

    # AÇÕES DIVERSAS
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

    # --------------------------------------------------------------------------
    # 4) MISSÕES DO CLÃ
    # --------------------------------------------------------------------------
    if clan_mission_start_handler:
        application.add_handler(clan_mission_start_handler)
        application.add_handler(clan_guild_mission_details_handler)
        application.add_handler(clan_mission_accept_handler)
        application.add_handler(clan_mission_finish_handler)
        application.add_handler(clan_mission_cancel_handler)

    # --------------------------------------------------------------------------
    # 5) GUERRA (handlers.guild.war)
    # --------------------------------------------------------------------------
    # IMPORTANTE: estes handlers devem usar pattern '^war_' (e não '^clan_war_')
    # para não colidir com o router do dashboard.
    application.add_handler(war_menu_handler)
    application.add_handler(war_ranking_handler)

    # --------------------------------------------------------------------------
    # 6) ✅ GUILDA DE AVENTUREIROS (NPC)
    # --------------------------------------------------------------------------
    application.add_handler(adventurer_guild_handler)
    application.add_handler(mission_view_handler)
    application.add_handler(mission_claim_handler)
    application.add_handler(clan_board_handler)

    # --------------------------------------------------------------------------
    # 7) ✅ FIX: atalhos de callbacks que precisam cair no clã
    # --------------------------------------------------------------------------
    application.add_handler(clan_menu_shortcut_handler)
    application.add_handler(clan_war_menu_shortcut_handler)

    # --------------------------------------------------------------------------
    # 8) ROTEADOR GENÉRICO DO CLÃ (SEMPRE POR ÚLTIMO)
    # --------------------------------------------------------------------------
    application.add_handler(clan_handler)

    print("✅ [REGISTRY] Botões de Guilda conectados com sucesso.")
