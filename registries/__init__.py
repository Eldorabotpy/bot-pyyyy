# registries/__init__.py
# (VERSÃO CORRIGIDA: Importação de Eventos + Registro do Claim Diário + Compatibilidade de callbacks)

import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import Application, TypeHandler, ContextTypes, CallbackQueryHandler
from modules.auth_utils import get_current_player_id_async

from modules import player_manager
from handlers import runes_handler

# 🔒 ACTION LOCK (IMPORTS)
from handlers.action_lock_handler import (
    action_lock_callback_handler,
    action_lock_message_handler,
)

# --- IMPORTS DOS REGISTROS (SEUS MÓDULOS) ---
from .admin import register_admin_handlers
from .character import register_character_handlers
from .combat import register_combat_handlers
from .crafting import register_crafting_handlers
from .market import register_market_handlers
from .regions import register_regions_handlers
from .guild import register_guild_handlers
from .events import register_event_handlers

# --- IMPORTS DIRETOS DE HANDLERS ESPECÍFICOS ---
from handlers.world_boss.handler import all_world_boss_handlers
from handlers.potion_handler import all_potion_handlers
# from handlers.autohunt_handler import all_autohunt_handlers

# --- IMPORTS DE MENUS E NAVEGAÇÃO ---
from handlers.menu import kingdom  # Para voltar ao Reino

# [CORREÇÃO]: Importação robusta do Menu de Eventos
try:
    from handlers.events import event_menu as events_menu_handler
except ImportError:
    try:
        from handlers.menu import events as events_menu_handler
    except ImportError:
        from modules.events import event_menu as events_menu_handler

# Importa Entry (Entrada/Lobby) e Combat das Catacumbas
from modules.events.catacumbas import entry_handler as cat_entry
from modules.events.catacumbas import combat_handler as cat_combat

from modules.auth_utils import get_current_player_id
from modules.clan_war_engine import register_war_jobs

logger = logging.getLogger(__name__)


async def update_last_seen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler global (Middleware) que atualiza 'last_seen'."""
    if not update.effective_user:
        return

    user_id = get_current_player_id(update, context)
    try:
        pdata = await player_manager.get_player_data(user_id)
        if pdata:
            pdata["last_seen"] = datetime.now(timezone.utc).isoformat()
            await player_manager.save_player_data(user_id, pdata)
    except Exception as e:
        logger.warning(f"Erro ao atualizar last_seen: {e}")


async def restore_session_from_persistent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Middleware global: após restart, repõe logged_player_id na RAM
    usando a sessão persistente do Mongo, sem exigir /start.
    NÃO faz logout e NÃO limpa nada.
    """
    try:
        if getattr(context, "user_data", None) and context.user_data.get("logged_player_id"):
            return

        pid = await get_current_player_id_async(update, context)
        if pid:
            if getattr(context, "user_data", None) is not None:
                context.user_data["logged_player_id"] = pid
    except Exception:
        pass


def _register_events_hub_and_claim(application: Application):
    """
    Registra:
      - Hub de Eventos (evt_hub_principal, abrir_hub_eventos_v2, back_to_event_hub)
      - Claim diário (evt_claim_daily_entries)
    """
    if hasattr(events_menu_handler, "register_handlers"):
        try:
            events_menu_handler.register_handlers(application)
            logger.info("✅ Eventos: register_handlers() do event_menu registrado com sucesso.")
            return
        except Exception as e:
            logger.warning(f"Falha ao chamar event_menu.register_handlers: {e}")

    hub_fn = None
    if hasattr(events_menu_handler, "show_events_menu"):
        hub_fn = events_menu_handler.show_events_menu
    elif hasattr(events_menu_handler, "show_active_events"):
        hub_fn = events_menu_handler.show_active_events

    if hub_fn:
        application.add_handler(CallbackQueryHandler(hub_fn, pattern=r"^evt_hub_principal$"))
        application.add_handler(CallbackQueryHandler(hub_fn, pattern=r"^back_to_event_hub$"))
        application.add_handler(CallbackQueryHandler(hub_fn, pattern=r"^abrir_hub_eventos_v2$"))
        logger.info("✅ Eventos: Hub registrado (evt_hub_principal/back_to_event_hub/abrir_hub_eventos_v2).")
    else:
        logger.warning("⚠️ Eventos: Não achei show_events_menu nem show_active_events no módulo event_menu.")

    if hasattr(events_menu_handler, "evt_claim_daily_entries"):
        application.add_handler(
            CallbackQueryHandler(events_menu_handler.evt_claim_daily_entries, pattern=r"^evt_claim_daily_entries$")
        )
        logger.info("✅ Eventos: Claim diário registrado (evt_claim_daily_entries).")
    else:
        logger.warning("⚠️ Eventos: Não achei evt_claim_daily_entries no módulo event_menu.")


def register_all_handlers(application: Application):
    """Chama todas as funções de registro de cada categoria na ordem correta."""
    logger.info("Iniciando o registro de todos os handlers...")

    # ============================================================
    # 1) Sessão PRIMEIRO (senão o lock não acha pid e libera tudo)
    # ============================================================
    application.add_handler(TypeHandler(Update, restore_session_from_persistent), group=-100)

    # ============================================================
    # 2) 🔒 ACTION LOCK TOTAL (firewall de verdade)
    # ============================================================
    application.add_handler(action_lock_callback_handler, group=-90)
    application.add_handler(action_lock_message_handler,  group=-90)

    # ============================================================
    # 3) Outros middlewares
    # ============================================================
    application.add_handler(TypeHandler(Update, update_last_seen), group=-10)

    # ============================================================
    # 4) Registro por Módulos
    # ============================================================
    register_admin_handlers(application)
    register_character_handlers(application)
    register_combat_handlers(application)
    register_crafting_handlers(application)
    register_market_handlers(application)
    register_guild_handlers(application)
    register_regions_handlers(application)
    register_war_jobs(application)

    # 5) Eventos gerais (Defesa do Reino, World Boss etc.)
    register_event_handlers(application)

    # 6) Rúnico
    application.add_handler(CallbackQueryHandler(runes_handler.action_router, pattern=r"^rune_npc:"))
    application.add_handler(CallbackQueryHandler(runes_handler.runes_router, pattern=r"^rune_mgr:"))

    # 7) Listas de handlers (legado/outros)
    application.add_handlers(all_world_boss_handlers)
    application.add_handlers(all_potion_handlers)
    # application.add_handlers(all_autohunt_handlers)

    # ============================================================
    # 💀 EVENTOS (HUB + CLAIM) & NAVEGAÇÃO
    # ============================================================
    _register_events_hub_and_claim(application)

    application.add_handler(CallbackQueryHandler(kingdom.show_kingdom_menu, pattern=r"^back_to_kingdom$"))
    application.add_handler(CallbackQueryHandler(kingdom.show_kingdom_menu, pattern=r"^show_kingdom_menu$"))

    application.add_handlers(cat_entry.handlers)
    application.add_handlers(cat_combat.handlers)

    logger.info("✅ Todos os handlers foram registrados com sucesso no registries/__init__.py")
