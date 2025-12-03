# registries/market.py
from telegram.ext import Application, CallbackQueryHandler, MessageHandler, filters
import logging

def register_market_handlers(application: Application):
    """Registra todos os handlers relacionados ao mercado (Ouro) e à Casa de Leilões (Gemas)."""
    
    try:
        # ===============================================================
        # 1. MERCADO DO AVENTUREIRO (OURO)
        # ===============================================================
        
        from handlers.market_handler import (
            market_open_handler, 
            market_adventurer_handler,
            market_list_handler, market_my_handler,
            market_sell_handler, market_buy_handler, market_cancel_handler,
            market_pick_unique_handler, market_pick_stack_handler,
            # Spinners
            market_pack_qty_spin_handler, market_pack_qty_confirm_handler,
            market_lote_qty_spin_handler, market_lote_qty_confirm_handler,
            market_price_spin_handler, market_price_confirm_handler, 
            market_cancel_new_handler,
            # Lógica de Venda Privada
            market_type_public,
            market_type_private,
            # IMPORTANTE: Aqui importamos o HANDLER PRONTO que criamos no market_handler.py
            market_catch_input_text_handler
        )
        
        # Menu Principal
        application.add_handler(market_open_handler)
        application.add_handler(market_adventurer_handler)
        
        # Navegação e Ações Básicas
        application.add_handler(market_list_handler)
        application.add_handler(market_my_handler)
        application.add_handler(market_sell_handler)
        application.add_handler(market_buy_handler)
        application.add_handler(market_cancel_handler)
        
        # Fluxo de Venda (Item -> Qtd -> Preço)
        application.add_handler(market_pick_unique_handler)
        application.add_handler(market_pick_stack_handler)
        
        # Spinners (Lotes e Tamanhos)
        application.add_handler(market_pack_qty_spin_handler)
        application.add_handler(market_pack_qty_confirm_handler)
        application.add_handler(market_lote_qty_spin_handler)
        application.add_handler(market_lote_qty_confirm_handler)
        
        # Preço e Confirmação
        application.add_handler(market_price_spin_handler)
        application.add_handler(market_price_confirm_handler) 
        application.add_handler(market_cancel_new_handler)
        
        # Decisão Público/Privado
        application.add_handler(CallbackQueryHandler(market_type_public, pattern="^mkt_type_public$"))
        application.add_handler(CallbackQueryHandler(market_type_private, pattern="^mkt_type_private$"))
        
        # --- NOVO: Captura de Texto (Nome do Jogador) ---
        # Adiciona o handler que importamos lá em cima.
        # Ele já contem o MessageHandler(filters.TEXT...) configurado no market_handler.py
        application.add_handler(market_catch_input_text_handler, group=1)

        # ===============================================================
        # 2. OUTROS MERCADOS (GEMAS / REINO)
        # ===============================================================
        
        # Casa de Leilões (Gemas)
        try:
            from handlers.gem_market_handler import (
                gem_market_main_handler, gem_list_cats_handler, gem_sell_cats_handler,
                gem_list_filter_handler, gem_list_class_handler, gem_sell_filter_handler,
                gem_sell_class_handler, gem_market_pick_item_handler, gem_market_cancel_new_handler,
                gem_market_pack_spin_handler, gem_market_pack_confirm_handler,
                gem_market_lote_spin_handler, gem_market_lote_confirm_handler,
                gem_market_price_spin_handler, gem_market_price_confirm_handler,
                gem_market_buy_confirm_handler, gem_market_buy_execute_handler,
                gem_market_my_handler, gem_market_cancel_execute_handler
            )
            application.add_handler(gem_market_main_handler)
            application.add_handler(gem_list_cats_handler)
            application.add_handler(gem_sell_cats_handler)
            application.add_handler(gem_list_filter_handler)
            application.add_handler(gem_list_class_handler)
            application.add_handler(gem_sell_filter_handler)
            application.add_handler(gem_sell_class_handler)
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
        except ImportError:
            logging.warning("Gem Market handlers not found (optional).")

        # Loja de Gemas (Bot)
        try:
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
        except ImportError:
            logging.warning("Gem Shop handlers not found (optional).")

        # Loja do Reino
        try:
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
        except ImportError:
            logging.warning("Kingdom Shop handlers not found (optional).")

    except ImportError as e:
        logging.error(f"### ERRO FATAL AO REGISTRAR MERCADOS ###: {e}")
        logging.exception("Verifique se o arquivo 'handlers/market_handler.py' existe e exporta 'market_catch_input_text_handler'.")