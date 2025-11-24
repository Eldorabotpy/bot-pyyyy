from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from modules.market_manager import list_active, render_listing_line
from modules import player_manager

async def open_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # 1. Pega dados do jogador (Async - Correto)
    pdata = await player_manager.get_player_data(user_id) or {}

    # 2. Pega listagens (Síncrono - CORRIGIDO)
    # Removemos o 'await' aqui porque list_active lê arquivo JSON localmente.
    # Adicionamos 'viewer_id' para ver itens privados.
    # Adicionamos 'page_size' para evitar erro de mensagem muito grande.
    listings = list_active(
        sort_by="price", 
        ascending=True, 
        price_per_unit=True,
        viewer_id=user_id, # <--- Importante para ver itens privados!
        page=1,
        page_size=10       # <--- Limite de segurança
    )

    lines = []
    buttons = []
    
    if not listings:
        text = "📦 <b>Mercado do Aventureiro</b>\n\n— Nenhum anúncio ativo no momento. —"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]])
        await update.effective_message.reply_text(text, reply_markup=kb, parse_mode="HTML")
        return

    # Loop síncrono para renderizar as linhas
    for l in listings:
        # render_listing_line é síncrono
        line = render_listing_line(l, viewer_player_data=pdata, show_price_per_unit=True)
        lines.append(f"• {line}")
        
        # Botão de compra (Lógica simples para encurtar texto)
        # Se for privado, adiciona um ícone visual no botão
        is_private = l.get("target_buyer_id") is not None
        btn_text = f"Comprar #{l['id']}" 
        if is_private:
            btn_text = f"🔒 Comprar #{l['id']}"
            
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"market_buy_{l['id']}")])

    buttons.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])

    text = "📦 <b>Mercado — Anúncios Ativos:</b>\n\n" + "\n".join(lines)
    
    # Envia a mensagem
    await update.effective_message.reply_text(
        text, 
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="HTML"
    )