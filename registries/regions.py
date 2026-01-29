# registries/regions.py
# (VERSÃO FINAL: Compatível com a Nova Loja de Natal) — FIX: Ordem de handlers (Coleta prioridade)

from telegram.ext import Application
import logging

logger = logging.getLogger(__name__)

# --- Grupo 1 & 2: Navegação, Menus e COLETA ---
from handlers.menu.region import (
    region_handler,
    travel_handler,
    open_region_handler,
    region_info_handler,
    restore_durability_menu_handler,
    restore_durability_fix_handler,
    collect_handler,
    noop_handler,
    war_claim_handler,
    war_attack_handler,
    continue_after_action_handler,
    war_search_handler,
    war_pvp_fight_handler,
)

# --- Loja de Natal ---
from handlers.christmas_shop import (
    open_christmas_shop_handler,
    buy_christmas_item_handler,
    switch_tab_handler,
    christmas_command
)

# --- Grupo 3: Calabouços (Dungeons) ---
from modules.dungeons.runtime import (
    dungeon_open_handler,
    dungeon_pick_handler,
)

# --- Grupo 4: NPCs ---
try:
    from handlers.npc_handler import all_npc_handlers
except ImportError:
    all_npc_handlers = []

# Tenta importar handlers do Reino
try:
    from handlers.menu.kingdom import kingdom_menu_handler
except ImportError:
    kingdom_menu_handler = None
    logger.warning("🚨 [REGISTRY] Falha ao importar kingdom_menu_handler.")


def register_regions_handlers(application: Application):
    """Regista os handlers de regiões, viagens, coleta e calabouços.

    FIX IMPORTANTE:
    - `collect_handler` precisa vir ANTES de handlers genéricos/routers (noop/continue),
      para não ser capturado por patterns amplos e ficar "sem resposta".
    """

    # ==========================================================
    # ✅ PRIORIDADE 0: COLETA (evita ser "comida" por handlers amplos)
    # ==========================================================
    application.add_handler(collect_handler)

    # ==========================================================
    # Grupo: Guerra (seu fluxo atual)
    # ==========================================================
    application.add_handler(war_search_handler)
    application.add_handler(war_pvp_fight_handler)
    application.add_handler(war_claim_handler)
    application.add_handler(war_attack_handler)

    # ==========================================================
    # Grupo 1: Região e Viagem
    # ==========================================================
    if kingdom_menu_handler:
        application.add_handler(kingdom_menu_handler)

    application.add_handler(travel_handler)
    application.add_handler(region_handler)
    application.add_handler(open_region_handler)
    application.add_handler(region_info_handler)

    # ==========================================================
    # Durabilidade
    # ==========================================================
    application.add_handler(restore_durability_menu_handler)
    application.add_handler(restore_durability_fix_handler)

    # ==========================================================
    # Grupo 3: Calabouços
    # ==========================================================
    application.add_handler(dungeon_open_handler)
    application.add_handler(dungeon_pick_handler)

    # ==========================================================
    # Grupo 4: NPCs
    # ==========================================================
    if all_npc_handlers:
        application.add_handlers(all_npc_handlers)

    # ==========================================================
    # 🎅 Loja de Natal
    # ==========================================================
    if open_christmas_shop_handler:
        application.add_handler(open_christmas_shop_handler)
        application.add_handler(buy_christmas_item_handler)
        application.add_handler(switch_tab_handler)
        application.add_handler(christmas_command)
        logger.info("🎄 Loja de Natal registrada com sucesso!")

    # ==========================================================
    # ⚠️ HANDLERS GENÉRICOS / FALLBACKS (sempre por último)
    # ==========================================================
    application.add_handler(continue_after_action_handler)
    application.add_handler(noop_handler)
