# handlers/market_browse.py (exemplo)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from modules.market_manager import list_active, render_listing_line
from modules import player_manager

async def open_market(update, context):
    user_id = update.effective_user.id
    pdata = player_manager.get_player_data(user_id) or {}

    listings = list_active(sort_by="price", ascending=True, price_per_unit=True)

    lines = []
    buttons = []
    for l in listings:
        # Linha idêntica ao inventário (para unique) e com emoji/quantidade (para stack)
        line = render_listing_line(l, viewer_player_data=pdata, show_price_per_unit=True)
        lines.append(line)
        # Botão curto para abrir os detalhes/comprar
        short = line
        if len(short) > 48:
            short = short[:22] + "… " + short[-22:]
        buttons.append([InlineKeyboardButton(short, callback_data=f"mk_view:{l['id']}")])

    text = "📦 Mercado — anúncios ativos:\n" + ("\n".join(lines) if lines else "— Sem anúncios —")
    await update.effective_message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
    )
