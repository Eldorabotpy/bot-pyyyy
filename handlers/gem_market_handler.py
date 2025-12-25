# handlers/gem_market_handler.py
# (VERSÃO 6.1 FINAL - CORRIGIDO IMPORT DE FILE_IDS)

import logging
import math
from typing import List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

# --- Nossos Módulos ---
from modules import player_manager, game_data
# CORREÇÃO AQUI: Importa file_ids
from modules import file_ids 
from modules import gem_market_manager
from modules import market_utils
from modules.game_data.items_evolution import EVOLUTION_ITEMS_DATA

try:
    from modules import display_utils
except ImportError:
    display_utils = None

logger = logging.getLogger(__name__)

# ==============================
#  CONFIGURAÇÕES
# ==============================
LOG_GROUP_ID = -1002881364171
LOG_TOPIC_ID = 24475

CLASS_ICONS = {
    "guerreiro": "🛡️", "cavaleiro": "🛡️", "gladiador": "⚔️",
    "mago": "🧙‍♂️", "arquimago": "🔮", "feiticeiro": "🔥",
    "cacador": "🏹", "arqueiro": "🏹",
    "assassino": "🗡️", "ninja": "🥷",
    "monge": "👊", "mestre": "🙏",
    "bardo": "🎵", "musico": "🪕",
    "berserker": "🪓", "barbaro": "👹",
    "samurai": "👺", "ronin": "🗡️",
    "sacerdote": "✝️", "clerigo": "✨",
    "universal": "🌎"
}

# ==============================
#  Helpers
# ==============================
def _get_item_info(base_id: str) -> dict:
    try:
        info = game_data.get_item_info(base_id)
        if info: return dict(info)
    except Exception: pass
    if base_id in EVOLUTION_ITEMS_DATA:
        return EVOLUTION_ITEMS_DATA[base_id]
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

def _item_label(base_id: str) -> str:
    info = _get_item_info(base_id)
    emoji = info.get("emoji", "💎")
    name = info.get("display_name", base_id)
    return f"{emoji} {name}"

def _format_class_name(item_info: dict) -> str:
    name = item_info.get("display_name", "").lower()
    base_id = item_info.get("id", "").lower()
    for cls, icon in CLASS_ICONS.items():
        if cls in name or cls in base_id:
            return f"{icon} {cls.capitalize()}"
    return "🌎 Global"

def _render_card_simple(base_id: str, qty: int, price: int = 0, seller_name: str = None, lote_qty: int = 1) -> str:
    info = _get_item_info(base_id)
    name = info.get("display_name") or base_id.replace("_", " ").title()
    emoji = info.get("emoji", "📦")
    desc = info.get("description", "Item Raro")
    if len(desc) > 30: desc = desc[:29] + "..."
    
    line1 = f"{emoji} <b>{name}</b> (x{qty})"
    class_str = _format_class_name(info)
    line2 = f"├┈➤ {class_str} │ ℹ️ <i>{desc}</i>"

    if price > 0:
        seller_txt = f"👤 <i>{seller_name}</i>" if seller_name else ""
        lote_txt = f"📦 {lote_qty} Lotes" if lote_qty > 1 else "📦 1 Lote"
        line3 = f"╰┈➤ 💎 <b>{price}</b> │ {lote_txt} │ {seller_txt}"
        return f"{line1}\n{line2}\n{line3}"
    return f"{line1}\n╰┈➤ 📦 Estoque: <b>{qty}</b>"

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    try: await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except:
        try: await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        except: await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

async def _send_with_media(chat_id, context, text, kb, keys):
    for k in keys:
        # CORREÇÃO: Usando file_ids
        fd = file_ids.get_file_data(k)
        if fd:
            try:
                await context.bot.send_photo(chat_id, fd["id"], caption=text, reply_markup=kb, parse_mode="HTML")
                return
            except: pass
    await context.bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")

# ==============================
#  MENU PRINCIPAL
# ==============================

async def gem_market_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id

    text = (
        "🏛️ <b>𝐂𝐨𝐦𝐞́𝐫𝐜𝐢𝐨 𝐝𝐞 𝐑𝐞𝐥𝐢́𝐪𝐮𝐢𝐚𝐬 ✨</b>\n\n"
        "Bem-vindo! Aqui podes negociar itens raros (Evolução, Skills, Skins) "
        "com outros aventureiros usando <b>Diamantes</b> (💎)."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Ver Listagens (Comprar)", callback_data="gem_list_cats")],
        [InlineKeyboardButton("➕ Vender Item", callback_data="gem_sell_cats")],
        [InlineKeyboardButton("👤 Minhas Listagens", callback_data="gem_market_my")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market")],
    ])

    keys = ["mercado_gemas", "img_mercado_gemas", "gem_market"]
    try: await q.delete_message(); 
    except: pass
    await _send_with_media(chat_id, context, text, kb, keys)

# ==============================
#  NAVEGAÇÃO E FILTROS
# ==============================

async def show_buy_category_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    text = "📦 <b>Comprar: Escolha a Categoria</b>"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Itens de Evolução", callback_data="gem_list_filter:evo")],
        [InlineKeyboardButton("📚 Tomos de Skill", callback_data="gem_list_filter:skill")],
        [InlineKeyboardButton("🎨 Caixas de Skin", callback_data="gem_list_filter:skin")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")],
    ])
    await _safe_edit_or_send(q, context, q.message.chat_id, text, kb)

async def show_sell_category_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    text = "➕ <b>Vender: Escolha a Categoria</b>"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Itens de Evolução", callback_data="gem_sell_filter:evo")],
        [InlineKeyboardButton("📚 Tomos de Skill", callback_data="gem_sell_filter:skill")],
        [InlineKeyboardButton("🎨 Caixas de Skin", callback_data="gem_sell_filter:skin")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")],
    ])
    await _safe_edit_or_send(q, context, q.message.chat_id, text, kb)

# ==============================
#  LISTAGEM DE COMPRA
# ==============================
async def show_buy_items_filtered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    
    parts = q.data.split(":")
    item_type = parts[1] # evo, skill, skin
    page = int(parts[2]) if len(parts) > 2 else 1

    all_listings = gem_market_manager.list_active(page=1, page_size=200)
    if all_listings is None: all_listings = []

    # Filtro
    filtered = []
    for l in all_listings:
        it = l.get("item", {})
        bid = it.get("base_id", "")
        is_match = False
        if item_type == "evo" and (bid in EVOLUTION_ITEMS_DATA or "essencia" in bid): is_match = True
        elif item_type == "skill" and ("tomo" in bid or "livro" in bid): is_match = True
        elif item_type == "skin" and ("caixa" in bid or "skin" in bid): is_match = True
        if is_match: filtered.append(l)

    # Paginação
    PER_PAGE = 5
    total_items = len(filtered)
    total_pages = math.ceil(total_items / PER_PAGE)
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1
    
    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE
    page_items = filtered[start:end]

    pdata = await player_manager.get_player_data(user_id)
    gems = player_manager.get_gems(pdata)

    lines = [
        f"╭┈┈┈┈┈➤ 🏛️ <b>MERCADO</b> ({page}/{total_pages}) ┈┈┈┈┈╮",
        f" │ 💎 <b>Seus Diamantes:</b> {gems}",
        f"╰┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤",
        ""
    ]

    if not page_items:
        lines.append("<i>Nenhum item encontrado nesta categoria.</i>")

    buttons_map = {}
    num_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

    for idx, listing in enumerate(page_items):
        icon_num = num_emojis[idx] if idx < 5 else f"{idx+1}"
        item_data = listing.get("item", {})
        base_id = item_data.get("base_id")
        qty = item_data.get("qty", 1)
        price = listing.get("unit_price_gems", 0)
        lotes = listing.get("quantity", 1)
        seller_id = listing.get("seller_id")
        lid = listing.get("id")
        
        seller_name = "Vendedor" 
        if int(seller_id) == user_id: seller_name = "Você"

        card = _render_card_simple(base_id, qty, price, seller_name, lotes)
        lines.append(f"{icon_num}┈➤{card}")
        lines.append("") 
        buttons_map[icon_num] = lid

    kb_rows = []
    btn_row = []
    for idx, (icon, lid) in enumerate(buttons_map.items()):
        btn_row.append(InlineKeyboardButton(f"🛒 {icon}", callback_data=f"gem_buy_confirm:{lid}"))
    if btn_row: kb_rows.append(btn_row)

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ Ant.", callback_data=f"gem_list_filter:{item_type}:{page-1}"))
    nav.append(InlineKeyboardButton("🔙 Menu", callback_data="gem_market_main"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("Prox. ➡️", callback_data=f"gem_list_filter:{item_type}:{page+1}"))
    kb_rows.append(nav)

    await _safe_edit_or_send(q, context, q.message.chat_id, "\n".join(lines), InlineKeyboardMarkup(kb_rows))

# ==============================
#  LISTAGEM DE VENDA
# ==============================
async def show_sell_items_filtered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    
    parts = q.data.split(":")
    item_type = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 1

    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {})

    sellable = []
    for bid, item_data in inv.items():
        qty = item_data.get("quantity", 0) if isinstance(item_data, dict) else int(item_data)
        if qty <= 0: continue
        
        is_match = False
        if item_type == "evo" and (bid in EVOLUTION_ITEMS_DATA or "essencia" in bid): is_match = True
        elif item_type == "skill" and ("tomo" in bid or "livro" in bid): is_match = True
        elif item_type == "skin" and ("caixa" in bid or "skin" in bid): is_match = True
        
        if is_match: sellable.append({"base_id": bid, "qty": qty})

    PER_PAGE = 5
    total_items = len(sellable)
    total_pages = math.ceil(total_items / PER_PAGE)
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1
    
    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE
    page_items = sellable[start:end]

    lines = [f"➕ <b>VENDER ITEM</b> ({page}/{total_pages})\n<i>Selecione o número para vender:</i>\n"]
    if not page_items:
        lines.append("🎒 <i>Você não possui itens desta categoria.</i>")

    buttons_map = {}
    num_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

    for idx, item in enumerate(page_items):
        icon_num = num_emojis[idx] if idx < 5 else f"{idx+1}"
        base_id = item["base_id"]
        qty = item["qty"]
        
        card = _render_card_simple(base_id, qty)
        lines.append(f"{icon_num}┈➤{card}")
        lines.append("")
        buttons_map[icon_num] = base_id

    kb_rows = []
    btn_row = []
    for icon, bid in buttons_map.items():
        btn_row.append(InlineKeyboardButton(f"🛒 {icon}", callback_data=f"gem_sell_item_{bid}"))
    if btn_row: kb_rows.append(btn_row)

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ Ant.", callback_data=f"gem_sell_filter:{item_type}:{page-1}"))
    nav.append(InlineKeyboardButton("🔙 Menu", callback_data="gem_market_main"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("Prox. ➡️", callback_data=f"gem_sell_filter:{item_type}:{page+1}"))
    kb_rows.append(nav)

    await _safe_edit_or_send(q, context, q.message.chat_id, "\n".join(lines), InlineKeyboardMarkup(kb_rows))

# ==============================
#  LÓGICA DE COMPRA
# ==============================

async def gem_market_buy_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    try: lid = int(q.data.split(":")[1])
    except: return

    listing = gem_market_manager.get_listing(lid)
    if not listing or not listing.get("active"):
        await q.answer("Item não disponível.", show_alert=True)
        await show_buy_category_menu(update, context)
        return

    item = listing.get("item", {})
    price = listing.get("unit_price_gems", 0)
    base_id = item.get("base_id")
    qty = item.get("qty", 1)
    info = _get_item_info(base_id)
    name = info.get("display_name", base_id)
    
    text = (
        f"🛒 <b>CONFIRMAR COMPRA</b>\n\n"
        f"📦 <b>Item:</b> {name} (x{qty})\n"
        f"💎 <b>Preço:</b> {price} Gemas\n\n"
        f"Deseja confirmar a transação?"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirmar", callback_data=f"gem_buy_execute_{lid}")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="gem_market_main")]
    ])
    await _safe_edit_or_send(q, context, q.message.chat_id, text, kb)

async def gem_market_buy_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("Processando...")
    buyer_id = q.from_user.id
    try: lid = int(q.data.replace("gem_buy_execute_", ""))
    except: await q.answer("ID inválido.", show_alert=True); return
        
    listing = gem_market_manager.get_listing(lid)
    if not listing or not listing.get("active"):
        await q.answer("Item já vendido!", show_alert=True)
        await gem_market_main(update, context); return
        
    seller_id = int(listing.get("seller_id", 0))
    if buyer_id == seller_id:
        await q.answer("Não podes comprar o teu próprio item.", show_alert=True); return

    buyer_pdata = await player_manager.get_player_data(buyer_id)
    seller_pdata = await player_manager.get_player_data(seller_id)
    
    total_cost = int(listing.get("unit_price_gems", 0)) 
    buyer_gems = int(buyer_pdata.get("gems", 0))
    
    if buyer_gems < total_cost:
        await q.answer(f"Gemas insuficientes! Precisas de {total_cost}.", show_alert=True); return

    try:
        buyer_pdata["gems"] = max(0, buyer_gems - total_cost)
        await gem_market_manager.purchase_listing( 
            buyer_pdata=buyer_pdata, 
            seller_pdata=seller_pdata, 
            listing_id=lid,
            quantity=1
        )
    except Exception as e:
        await q.answer(f"Erro na transação: {e}", show_alert=True); return

    item_payload = listing.get("item", {})
    base_id = item_payload.get("base_id") 
    pack_qty = int(item_payload.get("qty", 1))
    player_manager.add_item_to_inventory(buyer_pdata, base_id, pack_qty) 
    await player_manager.save_player_data(buyer_id, buyer_pdata)

    item_label = _item_label(base_id)
    if seller_id:
        try: await context.bot.send_message(seller_id, f"💎 <b>Venda Realizada!</b>\nVendeste <b>{item_label}</b> por <b>{total_cost} Gemas</b>.", parse_mode="HTML")
        except: pass

    try:
        buyer_name = buyer_pdata.get("character_name", q.from_user.first_name)
        seller_name = seller_pdata.get("character_name", "Desconhecido") if seller_pdata else "Desconhecido"
        log_text = (f"💎 <b>MERCADO GEMAS (VENDA)</b>\n👤 <b>Comprador:</b> {buyer_name}\n📦 <b>Item:</b> {item_label} x{pack_qty}\n💰 <b>Valor:</b> {total_cost} Gemas\n🤝 <b>Vendedor:</b> {seller_name}")
        await context.bot.send_message(chat_id=LOG_GROUP_ID, message_thread_id=LOG_TOPIC_ID, text=log_text, parse_mode="HTML")
    except: pass

    text = f"✅ <b>Sucesso!</b>\nRecebeste <b>{item_label} (x{pack_qty})</b>.\nCusto: 💎 {total_cost}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_list_cats")]])
    await _safe_edit_or_send(q, context, q.message.chat_id, text, kb)

# ==============================
#  MINHAS LISTAGENS
# ==============================

async def gem_market_my(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    my_listings = gem_market_manager.list_by_seller(user_id) 

    if not my_listings:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")]])
        await _safe_edit_or_send(q, context, q.message.chat_id, "Você não tem listagens ativas.", kb)
        return

    lines = ["👤 <b>Minhas Listagens (Gemas)</b>\n"]
    kb_rows = []
    
    for l in my_listings:
        item = l.get("item", {})
        price = l.get("unit_price_gems", 0)
        label = _item_label(item.get("base_id"))
        lines.append(f"• {label} (x{item.get('qty', 1)}) — 💎 {price}")
        kb_rows.append([InlineKeyboardButton(f"Cancelar #{l['id']}", callback_data=f"gem_cancel_{l['id']}")])

    kb_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")])
    await _safe_edit_or_send(q, context, q.message.chat_id, "\n".join(lines), InlineKeyboardMarkup(kb_rows))

async def gem_market_cancel_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("A cancelar...")
    user_id = q.from_user.id
    try: lid = int(q.data.replace("gem_cancel_", ""))
    except: return

    try:
        await gem_market_manager.cancel_listing(seller_id=user_id, listing_id=lid)
    except Exception as e:
        await q.answer(f"Erro: {e}", show_alert=True)
        await gem_market_my(update, context); return
    
    await _safe_edit_or_send(q, context, q.message.chat_id, f"✅ Listagem #{lid} cancelada. Itens devolvidos.", 
                             InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_my")]]))

# ==============================
#  LÓGICA DE VENDA (SPINNERS)
# ==============================

async def gem_market_pick_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    base_id = q.data.replace("gem_sell_item_", "")
    
    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {}) or {}
    qty_have = int(inv.get(base_id, 0))
    
    if qty_have <= 0:
        await q.answer("Você não tem mais esse item.", show_alert=True); return

    context.user_data["gem_market_pending"] = {
        "type": "item_stack", "base_id": base_id, "qty_have": qty_have, "qty": 1
    }
    
    if base_id in EVOLUTION_ITEMS_DATA:
        context.user_data["gem_market_pending"]["qty"] = 1
        await _show_gem_lote_spinner(q, context, q.message.chat_id)
    else:
        await _show_gem_pack_spinner(q, context, q.message.chat_id)

async def _show_gem_pack_spinner(q, context, chat_id):
    pending = context.user_data.get("gem_market_pending")
    qty_have = pending["qty_have"]
    cur = pending["qty"]
    kb = market_utils.render_spinner_kb(value=cur, prefix_inc="gem_pack_inc_", prefix_dec="gem_pack_dec_", label="Itens/Lote", confirm_cb="gem_pack_confirm")
    await _safe_edit_or_send(q, context, chat_id, f"Defina o tamanho do pacote:\nTotal disponível: {qty_have}", kb)

async def gem_market_pack_spin(update, context):
    q = update.callback_query; await q.answer()
    pending = context.user_data.get("gem_market_pending")
    max_q = pending["qty_have"]
    cur = market_utils.calculate_spin_value(pending["qty"], q.data, "gem_pack_inc_", "gem_pack_dec_", 1, max_q)
    pending["qty"] = cur
    await _show_gem_pack_spinner(q, context, update.effective_chat.id)

async def gem_market_pack_confirm(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["gem_market_lotes"] = 1
    await _show_gem_lote_spinner(q, context, update.effective_chat.id)

async def _show_gem_lote_spinner(q, context, chat_id):
    pending = context.user_data.get("gem_market_pending")
    qty_have = pending["qty_have"]
    pack_qty = pending["qty"]
    max_lotes = max(1, qty_have // pack_qty)
    context.user_data["gem_market_lote_max"] = max_lotes
    
    cur = context.user_data.get("gem_market_lotes", 1)
    kb = market_utils.render_spinner_kb(value=cur, prefix_inc="gem_lote_inc_", prefix_dec="gem_lote_dec_", label="Qtd Lotes", confirm_cb="gem_lote_confirm", allow_large_steps=False)
    await _safe_edit_or_send(q, context, chat_id, f"Quantos lotes de {pack_qty} itens?", kb)

async def gem_market_lote_spin(update, context):
    q = update.callback_query; await q.answer()
    max_l = context.user_data.get("gem_market_lote_max", 1)
    cur = market_utils.calculate_spin_value(context.user_data.get("gem_market_lotes", 1), q.data, "gem_lote_inc_", "gem_lote_dec_", 1, max_l)
    context.user_data["gem_market_lotes"] = cur
    await _show_gem_lote_spinner(q, context, update.effective_chat.id)

async def gem_market_lote_confirm(update, context):
    q = update.callback_query; await q.answer()
    pending = context.user_data.get("gem_market_pending")
    base_id = pending.get("base_id")
    min_price = 10 if base_id in EVOLUTION_ITEMS_DATA else 1
    context.user_data["gem_market_price"] = min_price
    await _show_gem_price_spinner(q, context, update.effective_chat.id)

async def _show_gem_price_spinner(q, context, chat_id):
    price = context.user_data.get("gem_market_price", 1)
    kb = market_utils.render_spinner_kb(value=price, prefix_inc="gem_p_inc_", prefix_dec="gem_p_dec_", label="Preço (Gemas)", confirm_cb="gem_p_confirm", currency_emoji="💎", allow_large_steps=False)
    await _safe_edit_or_send(q, context, chat_id, f"Defina o preço por lote (Gemas): <b>{price}</b>", kb)

async def gem_market_price_spin(update, context):
    q = update.callback_query; await q.answer()
    pending = context.user_data.get("gem_market_pending")
    min_p = 10 if pending and pending["base_id"] in EVOLUTION_ITEMS_DATA else 1
    cur = market_utils.calculate_spin_value(context.user_data.get("gem_market_price", min_p), q.data, "gem_p_inc_", "gem_p_dec_", min_p)
    context.user_data["gem_market_price"] = cur
    await _show_gem_price_spinner(q, context, update.effective_chat.id)

async def gem_market_price_confirm(update, context):
    q = update.callback_query; await q.answer()
    price = context.user_data.get("gem_market_price", 1)
    user_id = q.from_user.id
    pending = context.user_data.get("gem_market_pending")
    base_id = pending["base_id"]
    pack_qty = pending["qty"]
    lotes = context.user_data.get("gem_market_lotes", 1)
    total_remove = pack_qty * lotes
    
    pdata = await player_manager.get_player_data(user_id)
    if not player_manager.has_item(pdata, base_id, total_remove):
        await q.answer("Erro de estoque.", show_alert=True); return

    player_manager.remove_item_from_inventory(pdata, base_id, total_remove)
    await player_manager.save_player_data(user_id, pdata)
    
    itype = "evo_item" if base_id in EVOLUTION_ITEMS_DATA else "item_stack"
    if "tomo_" in base_id: itype = "skill"
    elif "skin_" in base_id or "caixa_" in base_id: itype = "skin"
    
    item_payload = {"type": itype, "base_id": base_id, "qty": pack_qty}
    gem_market_manager.create_listing(seller_id=user_id, item_payload=item_payload, unit_price=price, quantity=lotes)
    
    await _safe_edit_or_send(q, context, update.effective_chat.id, "✅ <b>Listagem criada com sucesso!</b>", 
                             InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")]]))

async def gem_market_cancel_new(update, context):
    q = update.callback_query; await q.answer()
    context.user_data.pop("gem_market_pending", None)
    await _safe_edit_or_send(q, context, update.effective_chat.id, "Operação cancelada.", 
                             InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")]]))

# ==============================
#  EXPORTS
# ==============================
gem_market_main_handler = CallbackQueryHandler(gem_market_main, pattern=r'^gem_market_main$')
gem_list_cats_handler = CallbackQueryHandler(show_buy_category_menu, pattern=r'^gem_list_cats$')
gem_sell_cats_handler = CallbackQueryHandler(show_sell_category_menu, pattern=r'^gem_sell_cats$')
gem_list_filter_handler = CallbackQueryHandler(show_buy_items_filtered, pattern=r'^gem_list_filter:')
gem_sell_filter_handler = CallbackQueryHandler(show_sell_items_filtered, pattern=r'^gem_sell_filter:')
gem_market_pick_item_handler = CallbackQueryHandler(gem_market_pick_item, pattern=r'^gem_sell_item_')
gem_market_buy_confirm_handler = CallbackQueryHandler(gem_market_buy_confirm, pattern=r'^gem_buy_confirm:')
gem_market_buy_execute_handler = CallbackQueryHandler(gem_market_buy_execute, pattern=r'^gem_buy_execute_')
gem_market_my_handler = CallbackQueryHandler(gem_market_my, pattern=r'^gem_market_my$')
gem_market_cancel_execute_handler = CallbackQueryHandler(gem_market_cancel_execute, pattern=r'^gem_cancel_')
gem_market_pack_spin_handler = CallbackQueryHandler(gem_market_pack_spin, pattern=r'^gem_pack_(inc|dec)_[0-9]+$')
gem_market_pack_confirm_handler = CallbackQueryHandler(gem_market_pack_confirm, pattern=r'^gem_pack_confirm$')
gem_market_lote_spin_handler = CallbackQueryHandler(gem_market_lote_spin, pattern=r'^gem_lote_(inc|dec)_[0-9]+$')
gem_market_lote_confirm_handler = CallbackQueryHandler(gem_market_lote_confirm, pattern=r'^gem_lote_confirm$')
gem_market_price_spin_handler = CallbackQueryHandler(gem_market_price_spin, pattern=r'^gem_p_(inc|dec)_[0-9]+$')
gem_market_price_confirm_handler = CallbackQueryHandler(gem_market_price_confirm, pattern=r'^gem_p_confirm$')
gem_market_cancel_new_handler = CallbackQueryHandler(gem_market_cancel_new, pattern=r'^gem_market_cancel_new$')
# Handlers de filtro de classe (legado ou futuro)
gem_list_class_handler = CallbackQueryHandler(show_buy_items_filtered, pattern=r'^gem_list_class:')
gem_sell_class_handler = CallbackQueryHandler(show_sell_items_filtered, pattern=r'^gem_sell_class:')