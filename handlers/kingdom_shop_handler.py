# handlers/kingdom_shop_handler.py

import logging
from typing import List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules import player_manager, game_data, file_id_manager

# --- INÍCIO DAS FUNÇÕES DE UTILIDADE (copiadas do seu arquivo original) ---
# Apenas as funções necessárias para a Loja do Reino estão aqui.

logger = logging.getLogger(__name__)

def _gold(pdata: dict) -> int:
    return int(pdata.get("gold", 0))

def _set_gold(pdata: dict, value: int):
    pdata["gold"] = max(0, int(value))

def _item_label_from_base(base_id: str) -> str:
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}).get("display_name", base_id)

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception:
        pass
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception:
        pass
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

async def _send_with_media(chat_id: int, context: ContextTypes.DEFAULT_TYPE, caption: str, kb: InlineKeyboardMarkup, media_keys: List[str]):
    for key in media_keys:
        fd = file_id_manager.get_file_data(key)
        if fd and fd.get("id"):
            fid, ftype = fd["id"], fd.get("type")
            try:
                if ftype == "video":
                    await context.bot.send_video(chat_id=chat_id, video=fid, caption=caption, reply_markup=kb, parse_mode="HTML")
                else:
                    await context.bot.send_photo(chat_id=chat_id, photo=fid, caption=caption, reply_markup=kb, parse_mode="HTML")
                return
            except Exception:
                continue
    await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=kb, parse_mode="HTML")

# --- FIM DAS FUNÇÕES DE UTILIDADE ---


# ==============================
#  CONFIG: Loja do Reino
# ==============================
KINGDOM_SHOP = {
    "pedra_do_aprimoramento": ("Pedra de Aprimoramento", 350),
    "pergaminho_durabilidade": ("Pergaminho de Durabilidade", 100),
    "joia_da_forja": ("Joia de Aprimoramento", 400),
    "nucleo_forja_fraco": ("Núcleo de Forja Fraco", 500),
    "nucleo_forja_comum": ("Núcleo de Forja Comum", 1000),
}


# ==============================
#  Loja do Reino (lógica principal)
# ==============================
def _king_state(context: ContextTypes.DEFAULT_TYPE) -> dict:
    st = context.user_data.get("kingdom_shop") or {}
    if not st:
        first_key = next(iter(KINGDOM_SHOP.keys()))
        st = {"base_id": first_key, "qty": 1}
        context.user_data["kingdom_shop"] = st
    return st

def _build_kingdom_keyboard(selected_base: str, qty: int) -> InlineKeyboardMarkup:
    item_buttons = []
    row = []
    for i, (base_id, (name_override, _price)) in enumerate(KINGDOM_SHOP.items(), 1):
        name = name_override or _item_label_from_base(base_id)
        prefix = "✅ " if base_id == selected_base else ""
        row.append(InlineKeyboardButton(f"{prefix}{name}", callback_data=f"king_set_{base_id}"))
        if i % 2 == 0:
            item_buttons.append(row); row = []
    if row:
        item_buttons.append(row)

    qty_row = [
        InlineKeyboardButton("➖", callback_data="king_q_minus"),
        InlineKeyboardButton(f"Qtd: {qty}", callback_data="noop"),
        InlineKeyboardButton("➕", callback_data="king_q_plus"),
    ]

    unit_price = KINGDOM_SHOP[selected_base][1]
    total = unit_price * max(1, qty)
    actions = [
        [InlineKeyboardButton(f"🛒 Comprar (Total: {total} 🪙)", callback_data="king_buy")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market")]
    ]
    return InlineKeyboardMarkup(item_buttons + [qty_row] + actions)

async def market_kingdom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id

    st = _king_state(context)
    base_id, qty = st["base_id"], max(1, int(st.get("qty", 1)))
    name = (KINGDOM_SHOP[base_id][0] or _item_label_from_base(base_id))
    unit_price = KINGDOM_SHOP[base_id][1]

    lines = ["🏰 <b>Loja do Reino</b>"]
    lines.append("Itens oficiais do reino (selecione um):\n")
    for b_id, (n_over, price) in KINGDOM_SHOP.items():
        n = n_over or _item_label_from_base(b_id)
        mark = "•" if b_id != base_id else "• <b>"
        end = "" if b_id != base_id else "</b>"
        lines.append(f"{mark} {n} — {price} 🪙/un{end}")
    lines.append("")
    lines.append(f"Selecionado: <b>{name}</b> — {unit_price} 🪙/un")

    kb = _build_kingdom_keyboard(base_id, qty)

    keys = ["loja_do_reino", "img_loja_reino", "market_kingdom", "kingdom_store_img"]
    try:
        await q.delete_message()
    except Exception:
        pass
    await _send_with_media(chat_id, context, "\n".join(lines), kb, keys)

async def kingdom_set_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    base_id = q.data.replace("king_set_", "")
    if base_id not in KINGDOM_SHOP:
        await q.answer("Item indisponível.", show_alert=True); return

    st = _king_state(context)
    st["base_id"] = base_id
    context.user_data["kingdom_shop"] = st
    await market_kingdom(update, context)

async def kingdom_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    st = _king_state(context)
    qty = max(1, int(st.get("qty", 1)))

    if q.data == "king_q_minus":
        qty = max(1, qty - 1)
    elif q.data == "king_q_plus":
        qty = qty + 1

    st["qty"] = qty
    context.user_data["kingdom_shop"] = st
    await market_kingdom(update, context)

async def market_kingdom_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    buyer_id = q.from_user.id
    chat_id = update.effective_chat.id

    st = _king_state(context)
    base_id = st["base_id"]
    qty = max(1, int(st.get("qty", 1)))

    if base_id not in KINGDOM_SHOP:
        await q.answer("Item não disponível na loja.", show_alert=True); return

    name_override, unit_price = KINGDOM_SHOP[base_id]
    name = name_override or _item_label_from_base(base_id)
    total = unit_price * qty

    buyer = player_manager.get_player_data(buyer_id)
    if not buyer:
        await q.answer("Jogador não encontrado.", show_alert=True); return

    if _gold(buyer) < total:
        await q.answer("Gold insuficiente.", show_alert=True); return

    _set_gold(buyer, _gold(buyer) - total)
    player_manager.add_item_to_inventory(buyer, base_id, qty)
    player_manager.save_player_data(buyer_id, buyer)

    await _safe_edit_or_send(q, context, chat_id, f"✅ Você comprou {qty}× {name} por {total} 🪙.", InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market_kingdom")]
    ]))

async def market_kingdom_buy_legacy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data.replace("king_buy_", "")
    try:
        base_id, qty_s = data.rsplit("_", 1)
        qty = int(qty_s)
    except Exception:
        await q.answer("Pedido inválido.", show_alert=True); return
    if base_id not in KINGDOM_SHOP or qty <= 0:
        await q.answer("Item/quantidade inválidos.", show_alert=True); return

    context.user_data["kingdom_shop"] = {"base_id": base_id, "qty": qty}
    await market_kingdom_buy(update, context)


# ==============================
#  Handlers (exports para este arquivo)
# ==============================
market_kingdom_handler          = CallbackQueryHandler(market_kingdom, pattern=r'^market_kingdom$')
kingdom_set_item_handler        = CallbackQueryHandler(kingdom_set_item, pattern=r'^king_set_[A-Za-z0-9_]+$')
kingdom_qty_minus_handler       = CallbackQueryHandler(kingdom_qty, pattern=r'^king_q_minus$')
kingdom_qty_plus_handler        = CallbackQueryHandler(kingdom_qty, pattern=r'^king_q_plus$')
market_kingdom_buy_handler      = CallbackQueryHandler(market_kingdom_buy, pattern=r'^king_buy$')
market_kingdom_buy_legacy_handler = CallbackQueryHandler(market_kingdom_buy_legacy, pattern=r'^king_buy_.+$')