# handlers/market_browse.py (exemplo)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes # Adiciona ContextTypes
from modules.market_manager import list_active, render_listing_line
from modules import player_manager

async def open_market(update: Update, context: ContextTypes.DEFAULT_TYPE): # Adiciona context
    user_id = update.effective_user.id
    # <<< CORREÇÃO 1: Adiciona await >>>
    pdata = await player_manager.get_player_data(user_id) or {}

    # <<< CORREÇÃO 2: Adiciona await (Assumindo que list_active é async) >>>
    listings = await list_active(sort_by="price", ascending=True, price_per_unit=True)

    lines = []
    buttons = []
    # Loop síncrono
    for l in listings:
        # Assumindo render_listing_line síncrono
        line = render_listing_line(l, viewer_player_data=pdata, show_price_per_unit=True)
        lines.append(line)
        # Botão curto
        short = line
        if len(short) > 48:
            short = short[:22] + "… " + short[-22:]
        buttons.append([InlineKeyboardButton(short, callback_data=f"mk_view:{l['id']}")]) # Assume mk_view handler existe

    text = "📦 Mercado — anúncios ativos:\n" + ("\n".join(lines) if lines else "— Sem anúncios —")
    # Usa await (já estava correto)
    await update.effective_message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
    )