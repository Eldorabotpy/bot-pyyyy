# handlers/gem_shop_handler.py
import logging
from typing import Dict, List
from datetime import datetime, timezone, timedelta

from telegram.error import BadRequest
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

from modules import player_manager, game_data
# Importa o dicionário completo de itens de evolução
from modules.game_data.items_evolution import EVOLUTION_ITEMS_DATA

# Importa planos e helper de texto
try:
    from modules.game_data.premium import PREMIUM_PLANS_FOR_SALE, get_benefits_text
except ImportError:
    PREMIUM_PLANS_FOR_SALE = {}
    def get_benefits_text(t): return "Benefícios indisponíveis."

logger = logging.getLogger(__name__)

# -------------------------------
# Configuração de Listas
# -------------------------------

# 1. PREMIUM: Carrega chaves do arquivo premium
TAB_PREMIUM = list(PREMIUM_PLANS_FOR_SALE.keys())

# 2. EVOLUÇÃO: Carrega TODAS as chaves do items_evolution.py automaticamente
# Isso garante que itens Tier 5, 6 e materiais específicos apareçam.
TAB_EVOLUTION = list(EVOLUTION_ITEMS_DATA.keys())

# 3. AVULSOS: Defina aqui os itens diversos que você quer vender
# Certifique-se que esses IDs existem no seu items_data ou similar
TAB_MISC = [
    "sigilo_protecao",
    "ticket_arena",
    "cristal_de_abertura",
    "pocao_mana_grande"
]

# Combina todas as chaves para validação de segurança
ALL_SHOP_KEYS = TAB_PREMIUM + TAB_EVOLUTION + TAB_MISC

# Preços Padrão (Caso não esteja definido em GEM_SHOP, usa 10)
DEFAULT_GEM_PRICE = 10

# Dicionário de Preços Específicos (ID -> Preço em Gemas)
# DICA: Preencha aqui os preços dos itens novos
GEM_SHOP: Dict[str, int] = {
    "sigilo_protecao": 5,
    "ticket_arena": 5,
    "cristal_de_abertura": 5,
    "pocao_mana_grande": 5,
   
}

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
    # Tenta pegar info do game_data geral
    try:
        info = game_data.get_item_info(base_id)
        if info: return dict(info)
    except: pass
    
    # Tenta pegar do items_evolution especificamente
    if base_id in EVOLUTION_ITEMS_DATA:
        return EVOLUTION_ITEMS_DATA[base_id]
        
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

def _price_for(base_id: str) -> int:
    if base_id in PREMIUM_PLANS_FOR_SALE:
        return int(PREMIUM_PLANS_FOR_SALE[base_id].get("price", 999999))
    return int(GEM_SHOP.get(base_id, DEFAULT_GEM_PRICE))

def _get_button_label(base_id: str) -> str:
    price = _price_for(base_id)
    if base_id in PREMIUM_PLANS_FOR_SALE:
        plan = PREMIUM_PLANS_FOR_SALE[base_id]
        name = plan.get('name', base_id).replace("Aventureiro ", "")
        return f"👑 {name} • {price}💎"
    else:
        info = _get_item_info(base_id)
        name = info.get("display_name") or info.get("nome_exibicao") or base_id
        emoji = info.get("emoji", "")
        # Encurta nomes muito longos para caber no botão
        if len(name) > 16: name = name[:14] + ".."
        return f"{emoji} {name} • {price}💎"

def _state(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> dict:
    st = context.user_data.get("gemshop")
    if not st:
        st = {"tab": "premium", "base_id": None, "qty": 1}
        context.user_data["gemshop"] = st
    return st

# -------------------------------
# CONSTRUTOR DE TECLADO INTELIGENTE
# -------------------------------
def _build_shop_keyboard(current_tab: str, selected_id: str, qty: int) -> InlineKeyboardMarkup:
    
    # CENÁRIO 1: ITEM SELECIONADO (Tela de Detalhes)
    if selected_id:
        is_plan = selected_id in PREMIUM_PLANS_FOR_SALE
        actions = []
        
        # Se for item, deixa escolher quantidade
        if not is_plan:
            qty_row = [
                InlineKeyboardButton("➖", callback_data="gem_qty_minus"),
                InlineKeyboardButton(f"📦 {qty}", callback_data="noop"),
                InlineKeyboardButton("➕", callback_data="gem_qty_plus"),
            ]
            actions.append(qty_row)

        buy_text = "✅ CONFIRMAR ASSINATURA" if is_plan else "🛒 CONFIRMAR COMPRA"
        actions.append([InlineKeyboardButton(buy_text, callback_data="gem_buy")])
        actions.append([InlineKeyboardButton("⬅️ Voltar para Lista", callback_data=f"gem_pick_{selected_id}")])
        
        return InlineKeyboardMarkup(actions)

    # CENÁRIO 2: VITRINE (Nenhum item selecionado)
    p_mark = " ✅" if current_tab == "premium" else ""
    e_mark = " ✅" if current_tab == "evolution" else ""
    m_mark = " ✅" if current_tab == "misc" else "" # Avulsos
    
    # Linha de Abas (Agora com 3 opções)
    tabs_row = [
        InlineKeyboardButton(f"👑 VIP{p_mark}", callback_data="gem_tab_premium"),
        InlineKeyboardButton(f"🔮 Evo{e_mark}", callback_data="gem_tab_evolution"),
        InlineKeyboardButton(f"🎒 Avul{m_mark}", callback_data="gem_tab_misc")
    ]
    
    # Seleciona a lista correta
    items_to_show = []
    if current_tab == "premium":
        items_to_show = TAB_PREMIUM
    elif current_tab == "evolution":
        items_to_show = TAB_EVOLUTION
    elif current_tab == "misc":
        items_to_show = TAB_MISC
    
    item_buttons = []
    
    if current_tab == "premium":
        # Lista vertical para planos
        for base_id in items_to_show:
            label = _get_button_label(base_id)
            item_buttons.append([InlineKeyboardButton(label, callback_data=f"gem_pick_{base_id}")])
    else:
        # Grade (Grid) para itens (2 por linha)
        row = []
        for i, base_id in enumerate(items_to_show, start=1):
            label = _get_button_label(base_id)
            row.append(InlineKeyboardButton(label, callback_data=f"gem_pick_{base_id}"))
            if i % 2 == 0:
                item_buttons.append(row); row = []
        if row: item_buttons.append(row)

    actions = [[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="market")]]
    
    # Monta o teclado final
    return InlineKeyboardMarkup([tabs_row] + item_buttons + actions)

# -------------------------------
# Handlers
# -------------------------------
async def gem_shop_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q:
        try: await q.answer()
        except: pass
        chat_id = update.effective_chat.id
        user_id = q.from_user.id
    else:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

    st = _state(context, user_id)
    current_tab = st.get("tab", "premium")
    base_id = st.get("base_id")
    qty = max(1, int(st.get("qty", 1)))

    pdata = await player_manager.get_player_data(user_id) or {}
    gems_now = _gems(pdata)

    lines = [
        "💎 <b>LOJA DE GEMAS</b>",
        f"💳 Saldo: <code>{gems_now}</code> 💎",
        "─────────────────"
    ]
    
    # --- MODO DETALHES ---
    if base_id:
        price = _price_for(base_id)
        if base_id in PREMIUM_PLANS_FOR_SALE:
            plan = PREMIUM_PLANS_FOR_SALE[base_id]
            tier_key = plan.get("tier", "free")
            days = plan.get("days", 30)
            benefits_block = get_benefits_text(tier_key)
            
            lines.append(f"👑 <b>{plan['name']}</b>")
            lines.append(f"⏱ <b>Duração:</b> {days} Dias")
            lines.append("")
            lines.append(benefits_block)
            lines.append("")
            
            current_tier = pdata.get("premium_tier")
            if current_tier and current_tier != tier_key and current_tier != "free":
                lines.append("⚠️ <b>Atenção:</b> Isso substituirá seu plano atual.")
            lines.append("─────────────────")
            lines.append(f"💰 <b>VALOR: {price} 💎</b>")
            
        else:
            info = _get_item_info(base_id)
            name = info.get("display_name", base_id)
            desc = info.get("description", "Item especial.")
            total = price * qty
            
            lines.append(f"📦 <b>{name}</b>")
            lines.append("")
            lines.append(f"<i>{desc}</i>")
            lines.append("")
            lines.append(f"💎 Unitário: {price}")
            lines.append(f"✖️ Quantidade: {qty}")
            lines.append("─────────────────")
            lines.append(f"💰 <b>TOTAL: {total} 💎</b>")

    # --- MODO VITRINE ---
    else:
        if current_tab == "premium":
            lines.append("👑 <b>Planos VIP</b>")
            lines.append("<i>Vantagens exclusivas para apoiadores.</i>")
        elif current_tab == "evolution":
            lines.append("🔮 <b>Materiais de Evolução</b>")
            lines.append("<i>Itens essenciais para a ascensão de classe.</i>")
        elif current_tab == "misc":
            lines.append("🎒 <b>Itens Avulsos</b>")
            lines.append("<i>Consumíveis e utilitários diversos.</i>")

    text_content = "\n".join(lines)
    kb = _build_shop_keyboard(current_tab, base_id, qty)

    if q:
        reply_markup = kb
        try: await q.edit_message_caption(caption=text_content, reply_markup=reply_markup, parse_mode="HTML")
        except BadRequest:
            try: await q.edit_message_text(text=text_content, reply_markup=reply_markup, parse_mode="HTML")
            except: pass
    else:
        await context.bot.send_message(chat_id=chat_id, text=text_content, reply_markup=kb, parse_mode="HTML")

async def gem_switch_tab(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    new_tab = q.data.replace("gem_tab_", "")
    st = _state(context, user_id)
    
    if st["tab"] != new_tab:
        st["tab"] = new_tab
        st["base_id"] = None 
        st["qty"] = 1
    context.user_data["gemshop"] = st
    await gem_shop_open(update, context)

async def gem_pick_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    base_id = q.data.replace("gem_pick_", "")

    if base_id not in ALL_SHOP_KEYS:
        # Tenta fallback se o item existe no sistema mas não estava na lista inicial
        info = _get_item_info(base_id)
        if not info:
            await q.answer("Item indisponível.", show_alert=True); return

    st = _state(context, user_id)
    if st["base_id"] == base_id:
        st["base_id"] = None
    else:
        st["base_id"] = base_id
        st["qty"] = 1
        
    context.user_data["gemshop"] = st
    await gem_shop_open(update, context)

async def gem_change_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    st = _state(context, user_id)
    if not st["base_id"] or st["base_id"] in PREMIUM_PLANS_FOR_SALE: return
    qty = max(1, int(st.get("qty", 1)))
    if q.data == "gem_qty_minus": qty = max(1, qty - 1)
    elif q.data == "gem_qty_plus": qty += 1
    st["qty"] = qty
    context.user_data["gemshop"] = st
    await gem_shop_open(update, context)

async def gem_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    buyer_id = q.from_user.id
    st = _state(context, buyer_id)
    base_id = st.get("base_id")
    qty = max(1, int(st.get("qty", 1)))

    if not base_id:
        await q.answer("Erro: Nenhum item selecionado.", show_alert=True); return

    unit_price = _price_for(base_id)
    total_cost = unit_price * qty
    is_vip = base_id in PREMIUM_PLANS_FOR_SALE
    
    if is_vip: 
        qty = 1
        total_cost = unit_price

    buyer = await player_manager.get_player_data(buyer_id)
    if not buyer: return

    if _gems(buyer) < total_cost:
        await q.answer(f"Faltam {total_cost - _gems(buyer)} gemas!", show_alert=True); return

    if not _spend_gems(buyer, total_cost):
        await q.answer("Erro na transação.", show_alert=True); return

    msg = ""
    if is_vip:
        plan = PREMIUM_PLANS_FOR_SALE[base_id]
        new_tier = plan["tier"]
        days = plan["days"]
        
        now = datetime.now(timezone.utc)
        curr_iso = buyer.get("premium_expires_at")
        current_active_tier = buyer.get("premium_tier")
        
        start_time = now 
        if current_active_tier == new_tier and curr_iso:
            try:
                curr_dt = datetime.fromisoformat(curr_iso)
                if curr_dt.tzinfo is None: curr_dt = curr_dt.replace(tzinfo=timezone.utc)
                if curr_dt > now: start_time = curr_dt
            except: pass
            
        new_exp = start_time + timedelta(days=days)
        buyer["premium_tier"] = new_tier
        buyer["premium_expires_at"] = new_exp.isoformat()
        
        msg = f"✅ <b>Assinatura Confirmada!</b>\n\n👑 <b>{plan['name']}</b>\n📅 Válido até: {new_exp.strftime('%d/%m/%Y')}"
    else:
        player_manager.add_item_to_inventory(buyer, base_id, qty)
        msg = f"✅ <b>Compra Confirmada!</b>\n\n💎 Custo: {total_cost}"

    await player_manager.save_player_data(buyer_id, buyer)
    st["base_id"] = None
    st["qty"] = 1
    context.user_data["gemshop"] = st

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar à Loja", callback_data="gem_shop")]])
    
    try: await q.edit_message_caption(caption=msg, reply_markup=reply_markup, parse_mode="HTML")
    except BadRequest:
        await q.edit_message_text(text=msg, reply_markup=reply_markup, parse_mode="HTML")

# -------------------------------
# Exports
# -------------------------------
gem_shop_open_handler   = CallbackQueryHandler(gem_shop_open, pattern=r'^gem_shop$')
gem_tab_handler         = CallbackQueryHandler(gem_switch_tab, pattern=r'^gem_tab_')
gem_pick_handler        = CallbackQueryHandler(gem_pick_item, pattern=r'^gem_pick_')
gem_qty_minus_handler   = CallbackQueryHandler(gem_change_qty, pattern=r'^gem_qty_minus$')
gem_qty_plus_handler    = CallbackQueryHandler(gem_change_qty, pattern=r'^gem_qty_plus$')
gem_buy_handler         = CallbackQueryHandler(gem_buy, pattern=r'^gem_buy$')
gem_shop_command_handler = CommandHandler("gemas", gem_shop_open)