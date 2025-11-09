# registries/market.py

from telegram.ext import Application
import logging

def register_market_handlers(application: Application):
    """Registra todos os handlers relacionados ao mercado (Ouro) e à Casa de Leilões (Gemas)."""
    
    try:
        # --- 1. Mercado do Aventureiro (Ouro) ---
        from handlers.adventurer_market_handler import (
            market_adventurer_handler, market_list_handler, market_my_handler,
            market_sell_handler, market_buy_handler, market_cancel_handler,
            market_pick_unique_handler, market_pick_stack_handler,
            market_pack_qty_spin_handler, market_pack_qty_confirm_handler,
            market_price_spin_handler, market_price_confirm_handler, market_cancel_new_handler,
            market_lote_qty_spin_handler, market_lote_qty_confirm_handler,
        )
        
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

        # --- 2. Casa de Leilões (Gemas / Diamantes) ---
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

        # --- 3. Loja de Gemas (do Bot) ---
        from handlers.gem_shop_handler import (
            gem_shop_command_handler, gem_shop_menu_handler, gem_shop_items_handler,
            gem_item_pick_handler, gem_item_qty_handler, gem_item_buy_handler,
            gem_shop_premium_handler, gem_prem_confirm_handler, gem_prem_execute_handler,
        )
        
        application.add_handler(gem_shop_command_handler)
        application.add_handler(gem_shop_menu_handler)
        application.add_handler(gem_shop_items_handler)
        application.add_handler(gem_item_pick_handler)
        application.add_handler(gem_item_qty_handler)
        application.add_handler(gem_item_buy_handler)
        application.add_handler(gem_shop_premium_handler)
        application.add_handler(gem_prem_confirm_handler)
        application.add_handler(gem_prem_execute_handler)

        # --- 4. Loja do Reino (Honra) ---
        from handlers.kingdom_shop_handler import (
            market_kingdom_handler, kingdom_set_item_handler, kingdom_qty_minus_handler,
            kingdom_qty_plus_handler, market_kingdom_buy_handler, market_kingdom_buy_legacy_handler,
        )
        
        application.add_handler(market_kingdom_handler)
        application.add_handler(kingdom_set_item_handler)
        application.add_handler(kingdom_qty_minus_handler)
        application.add_handler(kingdom_qty_plus_handler)
        application.add_handler(market_kingdom_buy_handler)
        application.add_handler(market_kingdom_buy_legacy_handler)
        
        # --- 5. Menu Principal (/mercado) ---
        from handlers.market_handler import market_open_handler
        application.add_handler(market_open_handler)
        
    except ImportError as e:
        logging.error(f"### ERRO FATAL AO REGISTRAR MERCADOS ###: {e}")
        logging.exception("Verifique se os handlers (adventurer, gem_market, etc.) existem e não têm erros de sintaxe.")