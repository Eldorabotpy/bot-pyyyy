# handlers/kingdom_shop_handler.py
import logging
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules import player_manager, game_data, file_ids

logger = logging.getLogger(__name__)

# ==============================
#  CONFIG: Loja do Reino (Gold)
# ==============================
KINGDOM_SHOP = {
    "pedra_do_aprimoramento": ("Pedra de Aprimoramento", 350),
    "pergaminho_durabilidade": ("Pergaminho de Reparo", 350),
    "joia_da_forja": ("Joia de Aprimoramento", 400),
    "nucleo_forja_fraco": ("Núcleo Fraco", 500),
    "nucleo_forja_comum": ("Núcleo Comum", 1000),

}

# ==============================
#  FUNÇÕES AUXILIARES
# ==============================
def _gold(pdata: dict) -> int:
    return int(pdata.get("gold", 0))

def _set_gold(pdata: dict, value: int):
    pdata["gold"] = max(0, int(value))

def _item_info(base_id: str) -> dict:
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {})

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    try: await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except: pass
    try: await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except: pass
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

async def _send_with_media(chat_id, context, caption, kb, keys):
    for key in keys:
        fd = file_ids.get_file_data(key)
        if fd and fd.get("id"):
            try:
                if fd.get("type") == "video":
                    await context.bot.send_video(chat_id, fd["id"], caption=caption, reply_markup=kb, parse_mode="HTML")
                else:
                    await context.bot.send_photo(chat_id, fd["id"], caption=caption, reply_markup=kb, parse_mode="HTML")
                return
            except: pass
    await context.bot.send_message(chat_id, caption, reply_markup=kb, parse_mode="HTML")

# ==============================
#  LÓGICA PRINCIPAL
# ==============================

def _king_state(context: ContextTypes.DEFAULT_TYPE) -> dict:
    st = context.user_data.get("kingdom_shop")
    if not st:
        # Seleciona o primeiro item por padrão
        first = next(iter(KINGDOM_SHOP.keys()))
        st = {"base_id": first, "qty": 1}
        context.user_data["kingdom_shop"] = st
    return st

def _build_kingdom_keyboard(selected_id: str, qty: int) -> InlineKeyboardMarkup:
    # 1. Grade de Itens (2 Colunas)
    item_rows = []
    row = []
    for i, (base_id, (name_override, price)) in enumerate(KINGDOM_SHOP.items(), 1):
        # Nome curto para caber no botão
        label_name = name_override.split(" ")[0] if len(name_override) > 15 else name_override
        
        # Marcador visual se selecionado
        prefix = "✅ " if base_id == selected_id else "📦 "
        
        btn_text = f"{prefix}{label_name} ({price})"
        row.append(InlineKeyboardButton(btn_text, callback_data=f"king_set_{base_id}"))
        
        if len(row) == 2:
            item_rows.append(row); row = []
    if row: item_rows.append(row)

    # 2. Controles de Quantidade (Só aparecem se tiver seleção)
    control_rows = []
    if selected_id:
        qty_row = [
            InlineKeyboardButton("➖", callback_data="king_q_minus"),
            InlineKeyboardButton(f"📝 {qty}", callback_data="noop"),
            InlineKeyboardButton("➕", callback_data="king_q_plus"),
        ]
        
        unit_price = KINGDOM_SHOP[selected_id][1]
        total = unit_price * qty
        buy_btn = [InlineKeyboardButton(f"🛒 Comprar por {total:,} 🪙", callback_data="king_buy")]
        
        control_rows.append(qty_row)
        control_rows.append(buy_btn)

    # 3. Navegação
    nav_row = [InlineKeyboardButton("⬅️ Voltar ao Centro", callback_data="market")]

    return InlineKeyboardMarkup(item_rows + control_rows + [nav_row])

async def market_kingdom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    user_id = q.from_user.id

    pdata = await player_manager.get_player_data(user_id)
    gold = _gold(pdata)
    
    st = _king_state(context)
    base_id = st["base_id"]
    qty = max(1, int(st.get("qty", 1)))

    # --- TEXTO VISUAL ---
    item_info = _item_info(base_id)
    shop_name = KINGDOM_SHOP.get(base_id, ["Item", 0])[0]
    desc = item_info.get("description", "Item essencial para aventureiros.")
    price = KINGDOM_SHOP.get(base_id, [0, 0])[1]
    
    text = (
        f"🏰 <b>SUPRIMENTOS DO REINO</b>\n"
        f"╰┈➤ <i>Qualidade garantida pelo Rei.</i>\n\n"
        f"💰 <b>Seu Ouro:</b> {gold:,} 🪙\n"
        f"──────────────────\n"
        f"📦 <b>{shop_name}</b>\n"
        f"ℹ️ <i>{desc}</i>\n"
        f"🏷️ <b>Preço:</b> {price} 🪙/un\n"
    )

    kb = _build_kingdom_keyboard(base_id, qty)
    
    # Tenta apagar a mensagem anterior para enviar a nova com foto limpa
    try: await q.delete_message()
    except: pass
    
    keys = ["loja_do_reino", "img_loja_reino", "market_kingdom"]
    await _send_with_media(chat_id, context, text, kb, keys)

# ==============================
#  AÇÕES (Seleção, Qtd, Compra)
# ==============================

async def kingdom_set_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    base_id = q.data.replace("king_set_", "")
    
    if base_id not in KINGDOM_SHOP:
        await q.answer("Item indisponível.", show_alert=True); return

    st = _king_state(context)
    if st["base_id"] == base_id:
        # Se clicar no mesmo, não faz nada ou reseta (opcional)
        pass
    else:
        st["base_id"] = base_id
        st["qty"] = 1 # Reseta qtd ao trocar item
        
    context.user_data["kingdom_shop"] = st
    await market_kingdom(update, context)

async def kingdom_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    # Pequeno hack para feedback tátil sem popup
    try: await q.answer() 
    except: pass
    
    st = _king_state(context)
    qty = max(1, int(st.get("qty", 1)))

    if q.data == "king_q_minus": qty = max(1, qty - 1)
    elif q.data == "king_q_plus": qty += 1

    st["qty"] = qty
    context.user_data["kingdom_shop"] = st
    await market_kingdom(update, context)

async def market_kingdom_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    
    st = _king_state(context)
    base_id = st["base_id"]
    qty = max(1, int(st.get("qty", 1)))

    if base_id not in KINGDOM_SHOP:
        await q.answer("Erro: Item inválido.", show_alert=True); return

    name, price = KINGDOM_SHOP[base_id]
    total_cost = price * qty

    # Transação Segura
    pdata = await player_manager.get_player_data(user_id)
    if _gold(pdata) < total_cost:
        await q.answer(f"Falta Ouro! Custa {total_cost}.", show_alert=True); return

    _set_gold(pdata, _gold(pdata) - total_cost)
    player_manager.add_item_to_inventory(pdata, base_id, qty)
    await player_manager.save_player_data(user_id, pdata)

    # Feedback
    await q.answer("Compra realizada!", show_alert=False)
    
    # Reseta qtd e atualiza tela
    st["qty"] = 1
    context.user_data["kingdom_shop"] = st
    
    # Envia mensagem de sucesso temporária ou atualiza o menu
    await market_kingdom(update, context)

async def market_kingdom_buy_legacy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Compatibilidade com botões antigos se houver."""
    await market_kingdom(update, context)

# ==============================
#  EXPORTS
# ==============================
market_kingdom_handler = CallbackQueryHandler(market_kingdom, pattern=r'^market_kingdom$')
kingdom_set_item_handler = CallbackQueryHandler(kingdom_set_item, pattern=r'^king_set_')
kingdom_qty_minus_handler = CallbackQueryHandler(kingdom_qty, pattern=r'^king_q_minus$')
kingdom_qty_plus_handler = CallbackQueryHandler(kingdom_qty, pattern=r'^king_q_plus$')
market_kingdom_buy_handler = CallbackQueryHandler(market_kingdom_buy, pattern=r'^king_buy$')
market_kingdom_buy_legacy_handler = CallbackQueryHandler(market_kingdom_buy_legacy, pattern=r'^king_buy_')