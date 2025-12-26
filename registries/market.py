# registries/market.py
from telegram.ext import Application, CallbackQueryHandler, MessageHandler, filters
import logging

# Configuração de Logger
logger = logging.getLogger(__name__)

def register_market_handlers(application: Application):
    """
    Registra todos os handlers relacionados ao sistema de economia:
    1. Mercado de Ouro (Jogadores)
    2. Casa de Leilões (Gemas)
    3. Loja de Gemas (Premium)
    4. Loja do Reino (NPC)
    """
    
    # ===============================================================
    # 1. MERCADO DO AVENTUREIRO (OURO)
    # Arquivo: handlers/adventurer_market_handler.py
    # ===============================================================
    try:
        from handlers.adventurer_market_handler import (
            market_open_handler, 
            market_adventurer_handler,
            market_list_handler, 
            market_my_handler,
            market_sell_menu_handler,
            market_sell_cat_handler,
            market_sell_legacy_handler,
            market_buy_handler, 
            market_cancel_handler,
            market_pick_unique_handler, 
            market_pick_stack_handler,
            # Spinners e Confirmações
            market_pack_qty_spin_handler, 
            market_pack_qty_confirm_handler,
            market_lote_qty_spin_handler, 
            market_lote_qty_confirm_handler,
            market_price_spin_handler, 
            market_price_confirm_handler, 
            market_cancel_new_handler,
            market_finish_public_handler,
            market_ask_private_handler,
            # Handler de input direto (removido do registro principal para usar o Router)
            market_input_id_handler, 
            # NOVOS HANDLERS DE INPUT
            market_input_qty_start_handler,
            market_input_price_start_handler,
            market_text_processor_handler,
            market_lot_size_spin,      # <--- NOVO
            market_lot_size_confirm,   # <--- NOVO
            market_start_input_size,
            # O ROTEADOR INTELIGENTE
            market_text_router_handler 
        )
        
        # Menu Principal e Navegação
        application.add_handler(market_open_handler)
        application.add_handler(market_adventurer_handler)
        application.add_handler(market_list_handler)
        application.add_handler(market_my_handler)
        
        # Fluxo de Venda
        application.add_handler(market_sell_menu_handler)
        application.add_handler(market_sell_cat_handler)
        application.add_handler(market_sell_legacy_handler) # Compatibilidade
        
        # Ações de Item
        application.add_handler(market_pick_unique_handler)
        application.add_handler(market_pick_stack_handler)
        application.add_handler(market_buy_handler)
        application.add_handler(market_cancel_handler)
        
        # Spinners (Seletores de Quantidade e Preço)
        application.add_handler(market_pack_qty_spin_handler)
        application.add_handler(market_pack_qty_confirm_handler)
        application.add_handler(market_lote_qty_spin_handler)
        application.add_handler(market_lote_qty_confirm_handler)
        application.add_handler(market_price_spin_handler)
        application.add_handler(market_price_confirm_handler)
        application.add_handler(market_cancel_new_handler)
        application.add_handler(market_finish_public_handler)
        application.add_handler(market_ask_private_handler)
        
        # NOVOS: Ativação do modo input
        application.add_handler(market_input_qty_start_handler)
        application.add_handler(market_input_price_start_handler)
        application.add_handler(CallbackQueryHandler(market_lot_size_spin, pattern=r'^mkt_size_(inc|dec|max).*'))
        application.add_handler(CallbackQueryHandler(market_lot_size_confirm, pattern=r'^mkt_size_confirm$'))
        application.add_handler(CallbackQueryHandler(market_start_input_size, pattern=r'^mkt_input_size_start$'))

        application.add_handler(market_text_router_handler, group=2)
        # -----------------------------------------------------------
        
        logger.info("✅ Handlers do Mercado de Ouro registrados com sucesso.")

    except ImportError as e:
        logger.error(f"❌ Erro ao importar Mercado de Ouro (adventurer_market_handler): {e}")

    # ===============================================================
    # 2. CASA DE LEILÕES (GEMAS)
    # Arquivo: handlers/gem_market_handler.py
    # ===============================================================
    try:
        from handlers.gem_market_handler import (
            gem_market_main_handler, 
            gem_list_cats_handler, 
            gem_sell_cats_handler,
            gem_list_filter_handler, 
            gem_list_class_handler, 
            gem_sell_filter_handler, 
            gem_sell_class_handler, 
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
            gem_market_cancel_execute_handler
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
        
        logger.info("✅ Handlers do Mercado de Gemas registrados com sucesso.")

    except ImportError as e:
        logger.warning(f"⚠️ Mercado de Gemas não carregado (gem_market_handler): {e}")

    # ===============================================================
    # 3. LOJA DE GEMAS (PREMIUM SHOP)
    # Arquivo: handlers/gem_shop_handler.py
    # ===============================================================
    try:
        from handlers.gem_shop_handler import (
            gem_shop_open_handler,
            gem_tab_handler,
            gem_pick_handler,
            gem_qty_minus_handler,
            gem_qty_plus_handler,
            gem_buy_handler,
            gem_shop_command_handler
        )
        
        application.add_handler(gem_shop_open_handler)
        application.add_handler(gem_tab_handler)
        application.add_handler(gem_pick_handler)
        application.add_handler(gem_qty_minus_handler)
        application.add_handler(gem_qty_plus_handler)
        application.add_handler(gem_buy_handler)
        application.add_handler(gem_shop_command_handler)
        
        logger.info("✅ Handlers da Loja Premium registrados com sucesso.")
        
    except ImportError as e:
        logger.error(f"❌ Erro ao importar Loja de Gemas (gem_shop_handler): {e}")

    # ===============================================================
    # 4. LOJA DO REINO (NPC)
    # Arquivo: handlers/kingdom_shop_handler.py
    # ===============================================================
    try:
        from handlers.kingdom_shop_handler import (
            market_kingdom_handler, 
            kingdom_set_item_handler, 
            kingdom_qty_minus_handler,
            kingdom_qty_plus_handler, 
            market_kingdom_buy_handler, 
            market_kingdom_buy_legacy_handler,
        )
        application.add_handler(market_kingdom_handler)
        application.add_handler(kingdom_set_item_handler)
        application.add_handler(kingdom_qty_minus_handler)
        application.add_handler(kingdom_qty_plus_handler)
        application.add_handler(market_kingdom_buy_handler)
        application.add_handler(market_kingdom_buy_legacy_handler)
        
        logger.info("✅ Handlers da Loja do Reino registrados com sucesso.")

    except ImportError:
        logger.warning("⚠️ Kingdom Shop handlers não encontrados (Opcional).")