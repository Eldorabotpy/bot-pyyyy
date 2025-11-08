# registries/market.py (VERSÃO ATUALIZADA)

from telegram.ext import Application

# 1. Importa o handler do menu principal do mercado
from handlers.market_handler import market_open_handler

# 2. Importa os handlers do Mercado do Aventureiro (Ouro)
from handlers.adventurer_market_handler import (
    market_adventurer_handler, market_list_handler, market_my_handler,
    market_sell_handler, market_buy_handler, market_cancel_handler,
    market_pick_unique_handler, market_pick_stack_handler,
    market_pack_qty_spin_handler, market_pack_qty_confirm_handler,
    market_price_spin_handler, market_price_confirm_handler, market_cancel_new_handler,
    market_lote_qty_spin_handler, market_lote_qty_confirm_handler,
)

# 3. Importa os handlers da Loja do Reino
from handlers.kingdom_shop_handler import (
    market_kingdom_handler, kingdom_set_item_handler, kingdom_qty_minus_handler,
    kingdom_qty_plus_handler, market_kingdom_buy_handler, market_kingdom_buy_legacy_handler,
)

# 4. Importa os handlers da Loja de Gemas Unificada
from handlers.gem_shop_handler import (
    gem_shop_command_handler, gem_shop_menu_handler, gem_shop_items_handler,
    gem_item_pick_handler, gem_item_qty_handler, gem_item_buy_handler,
    gem_shop_premium_handler, gem_prem_confirm_handler, gem_prem_execute_handler,
)

# --- 5. (NOVO) Importa os handlers do Mercado de Gemas (Player-2-Player) ---
from handlers.gem_market_handler import (
    gem_market_main_handler,
    gem_market_list_handler,
    gem_market_sell_handler,
    gem_market_pick_item_handler,
    gem_market_cancel_new_handler,
    gem_market_pack_spin_handler,
    gem_market_pack_confirm_handler,
    gem_market_lote_spin_handler,
    gem_market_lote_confirm_handler,
    gem_market_price_spin_handler,
    gem_market_price_confirm_handler,
    gem_market_buy_confirm_handler,
    gem_market_buy_execute_handler,
    gem_market_my_handler,
    gem_market_cancel_execute_handler,
)


def register_market_handlers(application: Application):
    """Registra todos os handlers relacionados ao mercado e suas lojas."""

    # --- Menu Principal do Mercado ---
    application.add_handler(market_open_handler)
    
    # --- Mercado do Aventureiro (Ouro) ---
    application.add_handler(market_adventurer_handler)
    application.add_handler(market_list_handler)
    application.add_handler(market_my_handler)
    application.add_handler(market_sell_handler)
    application.add_handler(market_buy_handler)
    application.add_handler(market_cancel_handler)
    application.add_handler(market_pick_unique_handler)
    application.add_handler(market_pick_stack_handler)
    application.add_handler(market_pack_qty_spin_handler)
    application.add_handler(market_pack_qty_confirm_handler)
    application.add_handler(market_price_spin_handler)
    application.add_handler(market_price_confirm_handler)
    application.add_handler(market_lote_qty_spin_handler)
    application.add_handler(market_lote_qty_confirm_handler)
    application.add_handler(market_cancel_new_handler)

    # --- Loja do Reino ---
    application.add_handler(market_kingdom_handler)
    application.add_handler(kingdom_set_item_handler)
    application.add_handler(kingdom_qty_minus_handler)
    application.add_handler(kingdom_qty_plus_handler)
    application.add_handler(market_kingdom_buy_handler)
    application.add_handler(market_kingdom_buy_legacy_handler)
    
    # --- Loja de Gemas Unificada (/gemas) ---
    application.add_handler(gem_shop_command_handler)
    application.add_handler(gem_shop_menu_handler)
    application.add_handler(gem_shop_items_handler)
    application.add_handler(gem_item_pick_handler)
    application.add_handler(gem_item_qty_handler)
    application.add_handler(gem_item_buy_handler)
    application.add_handler(gem_shop_premium_handler)
    application.add_handler(gem_prem_confirm_handler)
    application.add_handler(gem_prem_execute_handler)

    # --- (NOVO) Mercado de Gemas (Player-2-Player) ---
    application.add_handler(gem_market_main_handler)
    application.add_handler(gem_market_list_handler)
    application.add_handler(gem_market_sell_handler)
    application.add_handler(gem_market_pick_item_handler)
    application.add_handler(gem_market_cancel_new_handler)
    application.add_handler(gem_market_pack_spin_handler)
    application.add_handler(gem_market_pack_confirm_handler)
    application.add_handler(gem_market_lote_spin_handler)
    application.add_handler(gem_market_lote_confirm_handler)
    application.add_handler(gem_market_price_spin_handler)
    application.add_handler(gem_market_price_confirm_handler)
    application.add_handler(gem_market_buy_confirm_handler)
    application.add_handler(gem_market_buy_execute_handler)
    application.add_handler(gem_market_my_handler)
    application.add_handler(gem_market_cancel_execute_handler)