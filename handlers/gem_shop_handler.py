# handlers/gem_shop_handler.py
# (VERSÃO CORRIGIDA: AUTH OBJECTID E SYNC MANUAL SEGURO)

import logging
import math
from typing import Dict, List, Union
from datetime import datetime, timezone, timedelta

from telegram.error import BadRequest
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
from bson import ObjectId

from modules import player_manager, game_data
from modules.game_data.items_evolution import EVOLUTION_ITEMS_DATA
from modules.auth_utils import get_current_player_id
try:
    from modules.game_data.premium import PREMIUM_PLANS_FOR_SALE, get_benefits_text
except ImportError:
    PREMIUM_PLANS_FOR_SALE = {}
    def get_benefits_text(t): return "Benefícios indisponíveis."

logger = logging.getLogger(__name__)

# ==============================================================================
# CONFIGURAÇÃO DE NOTIFICAÇÃO
# ==============================================================================
NOTIFICATION_GROUP_ID = -1002881364171
NOTIFICATION_TOPIC_ID = 24475 

# -------------------------------
# Configuração de Listas
# -------------------------------
TAB_PREMIUM = list(PREMIUM_PLANS_FOR_SALE.keys())
TAB_EVOLUTION = list(EVOLUTION_ITEMS_DATA.keys())
TAB_MISC = ["sigilo_protecao", "ticket_arena", "cristal_de_abertura", "pocao_mana_grande"]

GEM_SHOP: Dict[str, int] = {
    "sigilo_protecao": 5,
    "ticket_arena": 5,
    "cristal_de_abertura": 5,
    "pocao_mana_grande": 5,
}

ITEMS_PER_PAGE = 3 

# -------------------------------
# Helpers Básicos
# -------------------------------
def _gems(pdata: dict) -> int:
    return max(0, int(pdata.get("gems", 0)))

def _set_gems(pdata: dict, value: int) -> None:
    pdata["gems"] = max(0, int(value))

def _spend_gems(pdata: dict, amount: int) -> bool:
    if _gems(pdata) < amount: return False
    _set_gems(pdata, _gems(pdata) - amount)
    return True

def _get_item_info(base_id: str) -> dict:
    try:
        info = game_data.get_item_info(base_id)
        if info: return dict(info)
    except: pass
    if base_id in EVOLUTION_ITEMS_DATA: return EVOLUTION_ITEMS_DATA[base_id]
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

def _price_for(base_id: str) -> int:
    if base_id in PREMIUM_PLANS_FOR_SALE:
        return int(PREMIUM_PLANS_FOR_SALE[base_id].get("price", 999999))
    return int(GEM_SHOP.get(base_id, 10))

def _state(context: ContextTypes.DEFAULT_TYPE, user_id: str) -> dict:
    st = context.user_data.get("gemshop")
    if not st:
        st = {"tab": "premium", "base_id": None, "qty": 1, "page": 1}
        context.user_data["gemshop"] = st
    return st

# -------------------------------
# CONSTRUTOR DE TECLADO
# -------------------------------
def _build_shop_keyboard(context_state: dict, page_items: list = None) -> InlineKeyboardMarkup:
    current_tab = context_state.get("tab", "premium")
    selected_id = context_state.get("base_id")
    qty = context_state.get("qty", 1)
    page = context_state.get("page", 1)

    if selected_id:
        is_plan = selected_id in PREMIUM_PLANS_FOR_SALE
        actions = []
        if not is_plan:
            qty_row = [
                InlineKeyboardButton("➖", callback_data="gem_qty_minus"),
                InlineKeyboardButton(f"📦 {qty}", callback_data="noop"),
                InlineKeyboardButton("➕", callback_data="gem_qty_plus"),
            ]
            actions.append(qty_row)
        
        buy_text = "✨ ASSINAR" if is_plan else "🛒 COMPRAR"
        actions.append([InlineKeyboardButton(buy_text, callback_data="gem_buy")])
        actions.append([InlineKeyboardButton("🔙 Voltar à Lista", callback_data=f"gem_pick_{selected_id}")]) 
        return InlineKeyboardMarkup(actions)

    tp = "💠 VIP" if current_tab == "premium" else "VIP"
    te = "💠 Evo" if current_tab == "evolution" else "Evo"
    tm = "💠 Itens" if current_tab == "misc" else "Itens"
    
    tabs_row = [
        InlineKeyboardButton(tp, callback_data="gem_tab_premium"),
        InlineKeyboardButton(te, callback_data="gem_tab_evolution"),
        InlineKeyboardButton(tm, callback_data="gem_tab_misc")
    ]
    
    kb_rows = [tabs_row]

    if page_items:
        btn_row = []
        for idx, base_id in enumerate(page_items, start=1):
            btn_row.append(InlineKeyboardButton(f"{idx} 🛒", callback_data=f"gem_pick_{base_id}"))
            if len(btn_row) >= 5:
                kb_rows.append(btn_row); btn_row = []
        if btn_row: kb_rows.append(btn_row)

    total_pages = context_state.get("total_pages", 1)
    nav_row = []
    if total_pages > 1:
        if page > 1: nav_row.append(InlineKeyboardButton("⬅️", callback_data="gem_page_prev"))
        else: nav_row.append(InlineKeyboardButton("🔲", callback_data="noop"))
        nav_row.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="noop"))
        if page < total_pages: nav_row.append(InlineKeyboardButton("➡️", callback_data="gem_page_next"))
        else: nav_row.append(InlineKeyboardButton("🔲", callback_data="noop"))
            
    if nav_row: kb_rows.append(nav_row)
    kb_rows.append([InlineKeyboardButton("⬅️ Sair da Loja", callback_data="market")])
    return InlineKeyboardMarkup(kb_rows)

# -------------------------------
# Handlers
# -------------------------------
async def gem_shop_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q: await q.answer()

    user_id = get_current_player_id(update, context)
    if not user_id:
        if q: await q.answer("Sessão inválida.", show_alert=True)
        return

    st = _state(context, user_id)
    current_tab = st.get("tab", "premium")
    base_id = st.get("base_id")
    qty = st.get("qty", 1)
    page = st.get("page", 1)
    
    pdata = await player_manager.get_player_data(user_id) or {}
    gems_now = _gems(pdata)

    lines = [f"╭┈┈➤➤➤ 💎 𝐋𝐎𝐉𝐀 𝐃𝐄 𝐆𝐄𝐌𝐀𝐒 ", f"│💰 <i>Saldo: {gems_now} diamantes</i>", f"╰┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤➤➤"]
    
    items_source = []
    if current_tab == "premium": items_source = TAB_PREMIUM
    elif current_tab == "evolution": items_source = TAB_EVOLUTION
    elif current_tab == "misc": items_source = TAB_MISC

    total_items = len(items_source)
    total_pages = math.ceil(total_items / ITEMS_PER_PAGE) or 1
    if page > total_pages: page = 1; st["page"] = 1
    st["total_pages"] = total_pages 

    if base_id:
        price = _price_for(base_id)
        if base_id in PREMIUM_PLANS_FOR_SALE:
            plan = PREMIUM_PLANS_FOR_SALE[base_id]
            lines.append(f"👑 <b>{plan['name']}</b>")
            lines.append(f"⏱ <b>Duração:</b> {plan.get('days', 30)} dias")
            lines.append(f"<i>{get_benefits_text(plan.get('tier', 'free'))}</i>")
            lines.append(f"🏷️ <b>Valor: {price} 💎</b>")
        else:
            info = _get_item_info(base_id)
            total = price * qty
            lines.append(f"📦 <b>{info.get('display_name', base_id).upper()}</b>")
            lines.append(f"<i>{info.get('description', '...')}</i>")
            lines.append(f"🔹 Unitário: {price} 💎 | ✖️ Qtd: {qty}")
            lines.append(f"💵 <b>TOTAL: {total} 💎</b>")
        page_items_for_kb = None 
    else:
        start_idx = (page - 1) * ITEMS_PER_PAGE
        page_items_for_kb = items_source[start_idx : start_idx + ITEMS_PER_PAGE]
        cat_name = {"premium": "PLANOS VIP", "evolution": "EVOLUÇÃO", "misc": "DIVERSOS"}.get(current_tab, "ITENS")
        lines.append(f"📂 <b>{cat_name}</b> ({page}/{total_pages})\n")
        
        for idx, item_id in enumerate(page_items_for_kb):
            price = _price_for(item_id)
            num = ["1️⃣","2️⃣","3️⃣"][idx] if idx < 3 else f"{idx+1}."
            if current_tab == "premium":
                plan = PREMIUM_PLANS_FOR_SALE.get(item_id, {})
                name = plan.get("name", item_id).replace("Aventureiro ", "")
                lines.append(f"{num} 👑 <b>{name}</b>\n   ╰┈➤ 💎 {price} │ ⏱ {plan.get('days')} Dias\n")
            else:
                info = _get_item_info(item_id)
                lines.append(f"{num} {info.get('emoji','🔮')} <b>{info.get('display_name', item_id)}</b>\n   ╰┈➤ 💎 {price}\n")

    text_content = "\n".join(lines)
    kb = _build_shop_keyboard(st, page_items_for_kb)
    
    chat_id = update.effective_chat.id
    if q:
        try: await q.edit_message_caption(caption=text_content, reply_markup=kb, parse_mode="HTML")
        except: 
            try: await q.edit_message_text(text=text_content, reply_markup=kb, parse_mode="HTML")
            except: pass
    else:
        await context.bot.send_message(chat_id, text_content, reply_markup=kb, parse_mode="HTML")

# --- ACTIONS ---
async def gem_switch_tab(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_current_player_id(update, context)
    if not user_id: return
    new_tab = update.callback_query.data.replace("gem_tab_", "")
    st = _state(context, user_id)
    if st["tab"] != new_tab:
        st.update({"tab": new_tab, "base_id": None, "qty": 1, "page": 1})
    await gem_shop_open(update, context)

async def gem_change_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_current_player_id(update, context)
    if not user_id: return
    st = _state(context, user_id)
    d = update.callback_query.data
    st["page"] = st.get("page", 1) + (1 if "next" in d else -1)
    st["page"] = max(1, st["page"])
    await gem_shop_open(update, context)

async def gem_pick_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_current_player_id(update, context)
    if not user_id: return
    base_id = update.callback_query.data.replace("gem_pick_", "")
    st = _state(context, user_id)
    st["base_id"] = None if st["base_id"] == base_id else base_id
    st["qty"] = 1
    await gem_shop_open(update, context)

async def gem_change_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_current_player_id(update, context)
    if not user_id: return
    st = _state(context, user_id)
    if not st["base_id"]: return
    d = update.callback_query.data
    st["qty"] = max(1, st.get("qty", 1) + (1 if "plus" in d else -1))
    await gem_shop_open(update, context)

async def gem_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    buyer_id = get_current_player_id(update, context)
    if not buyer_id: await q.answer("Erro login.", show_alert=True); return

    st = _state(context, buyer_id)
    base_id = st.get("base_id")
    qty = max(1, int(st.get("qty", 1)))
    if not base_id: return

    unit_price = _price_for(base_id)
    total_cost = unit_price * qty
    is_vip = base_id in PREMIUM_PLANS_FOR_SALE
    if is_vip: qty = 1; total_cost = unit_price

    buyer = await player_manager.get_player_data(buyer_id)
    if not buyer: return
    if _gems(buyer) < total_cost:
        await q.answer(f"Faltam {total_cost - _gems(buyer)} gemas!", show_alert=True); return
    if not _spend_gems(buyer, total_cost): return

    msg = ""
    if is_vip:
        plan = PREMIUM_PLANS_FOR_SALE[base_id]
        new_tier = plan["tier"]
        days = plan.get("days", 30)
        now = datetime.now(timezone.utc)
        
        # Define Expiração
        curr_iso = buyer.get("premium_expires_at")
        start_time = now
        if buyer.get("premium_tier") == new_tier and curr_iso:
            try:
                curr_dt = datetime.fromisoformat(curr_iso)
                if curr_dt > now: start_time = curr_dt
            except: pass
            
        new_exp = start_time + timedelta(days=days)
        buyer["premium_tier"] = new_tier
        buyer["premium_expires_at"] = new_exp.isoformat()
        
        # SYNC MANUAL COM BANCO (Users Collection)
        try:
            from modules.database import db
            # Converte buyer_id string para ObjectId
            query = {"_id": ObjectId(buyer_id)} if ObjectId.is_valid(buyer_id) else {"_id": buyer_id}
            db["users"].update_one(query, {"$set": {"premium_tier": new_tier, "premium_expires_at": new_exp.isoformat()}})
        except Exception as e:
            logger.error(f"Erro sync vip: {e}")

        msg = f"✅ <b>Assinatura VIP Ativa!</b>\n👑 {plan['name']}\n📅 Até: {new_exp.strftime('%d/%m/%Y')}"
        
        # Notificação Grupo
        try:
            char_name = buyer.get("character_name", "Aventureiro")
            await context.bot.send_message(
                chat_id=NOTIFICATION_GROUP_ID, message_thread_id=NOTIFICATION_TOPIC_ID,
                text=f"🎉 <b>{char_name}</b> agora é 🌟 <b>{plan['name']}</b>!", parse_mode="HTML"
            )
        except: pass
    else:
        player_manager.add_item_to_inventory(buyer, base_id, qty)
        msg = f"✅ <b>Compra Confirmada!</b>\n💎 -{total_cost}"

    await player_manager.save_player_data(buyer_id, buyer)
    st.update({"base_id": None, "qty": 1})
    
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_shop")]])
    try: await q.edit_message_caption(caption=msg, reply_markup=kb, parse_mode="HTML")
    except: await q.edit_message_text(text=msg, reply_markup=kb, parse_mode="HTML")

# Exports
gem_shop_open_handler = CallbackQueryHandler(gem_shop_open, pattern=r'^gem_shop$')
gem_tab_handler = CallbackQueryHandler(gem_switch_tab, pattern=r'^gem_tab_')
gem_page_handler = CallbackQueryHandler(gem_change_page, pattern=r'^gem_page_')
gem_pick_handler = CallbackQueryHandler(gem_pick_item, pattern=r'^gem_pick_')
gem_qty_minus_handler = CallbackQueryHandler(gem_change_qty, pattern=r'^gem_qty_minus$')
gem_qty_plus_handler = CallbackQueryHandler(gem_change_qty, pattern=r'^gem_qty_plus$')
gem_buy_handler = CallbackQueryHandler(gem_buy, pattern=r'^gem_buy$')
gem_shop_command_handler = CommandHandler("gemas", gem_shop_open)