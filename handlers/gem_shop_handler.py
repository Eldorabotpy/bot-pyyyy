# handlers/gem_shop_handler.py
# (VERSÃO FINAL COMPLETA: 3 Abas, Preços Manuais e Correções de Erro)

import logging
from typing import Dict, List
from datetime import datetime, timezone, timedelta

from telegram.error import BadRequest
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

from modules import player_manager, game_data
# Importa lista automática de evolução
from modules.game_data.items_evolution import EVOLUTION_ITEMS_DATA

# Importa planos e helper de texto
try:
    from modules.game_data.premium import PREMIUM_PLANS_FOR_SALE, get_benefits_text
except ImportError:
    PREMIUM_PLANS_FOR_SALE = {}
    def get_benefits_text(t): return "Benefícios indisponíveis."

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. CONFIGURAÇÃO DAS LISTAS E PREÇOS
# ==============================================================================

# A. Itens Manuais (Suprimentos / Avulsos)
# Formato: "ID_DO_ITEM": PRECO_EM_GEMAS
SUPPLIES_ITEMS = {
    "cristal_de_abertura": 5,      
    "ticket_defesa_reino": 5,
    "sigilo_protecao": 5,
    
}

# B. Definição das Listas por Aba
TAB_PREMIUM = list(PREMIUM_PLANS_FOR_SALE.keys())
TAB_EVOLUTION = list(EVOLUTION_ITEMS_DATA.keys())
TAB_SUPPLIES = list(SUPPLIES_ITEMS.keys())

# C. Lista Mestra (Para validação de segurança) -> CORREÇÃO DO ERRO ALL_SHOP_KEYS
ALL_SHOP_KEYS = TAB_PREMIUM + TAB_EVOLUTION + TAB_SUPPLIES

DEFAULT_GEM_PRICE = 10 

# ==============================================================================
# 2. HELPERS (Lógica de Gemas e Preços)
# ==============================================================================

def _gems(pdata: dict) -> int:
    return max(0, int(pdata.get("gems", 0)))

def _set_gems(pdata: dict, value: int) -> None:
    pdata["gems"] = max(0, int(value))

def _spend_gems(pdata: dict, amount: int) -> bool:
    if _gems(pdata) < amount: return False
    _set_gems(pdata, _gems(pdata) - amount)
    return True

def _get_item_info(base_id: str) -> dict:
    """Busca informações do item em qualquer banco de dados disponível."""
    try:
        info = game_data.get_item_info(base_id)
        if info: return dict(info)
    except: pass
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

def _price_for(base_id: str) -> int:
    """Calcula o preço do item dependendo da categoria."""
    # 1. Premium
    if base_id in PREMIUM_PLANS_FOR_SALE:
        return int(PREMIUM_PLANS_FOR_SALE[base_id].get("price", 999999))
    
    # 2. Suprimento (Preço Manual no dicionário acima)
    if base_id in SUPPLIES_ITEMS:
        return int(SUPPLIES_ITEMS[base_id])
    
    # 3. Evolução ou Outros (Tenta ler do item ou usa padrão)
    info = _get_item_info(base_id)
    return int(info.get("gem_price", DEFAULT_GEM_PRICE))

def _get_button_label(base_id: str) -> str:
    """Gera o texto bonito para o botão."""
    price = _price_for(base_id)
    
    if base_id in PREMIUM_PLANS_FOR_SALE:
        plan = PREMIUM_PLANS_FOR_SALE[base_id]
        name = plan.get('name', base_id).replace("Aventureiro ", "")
        return f"👑 {name} • {price}💎"
    else:
        info = _get_item_info(base_id)
        name = info.get("display_name") or info.get("nome_exibicao") or base_id.replace("_", " ").title()
        emoji = info.get("emoji", "💎")
        if len(name) > 16: name = name[:14] + ".."
        return f"{emoji} {name} • {price}💎"

def _state(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Gerencia o estado da navegação na loja (aba atual, item selecionado)."""
    st = context.user_data.get("gemshop")
    if not st:
        st = {"tab": "premium", "base_id": None, "qty": 1}
        context.user_data["gemshop"] = st
    return st

# ==============================================================================
# 3. CONSTRUTOR DE INTERFACE (Teclados)
# ==============================================================================

def _build_shop_keyboard(current_tab: str, selected_id: str, qty: int) -> InlineKeyboardMarkup:
    
    # --- TELA DE DETALHES (Item Selecionado) ---
    if selected_id:
        is_plan = selected_id in PREMIUM_PLANS_FOR_SALE
        actions = []
        
        # Seletor de Quantidade (apenas para itens)
        if not is_plan:
            qty_row = [
                InlineKeyboardButton("➖", callback_data="gem_qty_minus"),
                InlineKeyboardButton(f"📦 {qty}", callback_data="noop"),
                InlineKeyboardButton("➕", callback_data="gem_qty_plus"),
            ]
            actions.append(qty_row)

        # Botão de Compra
        buy_text = "✅ ASSINAR" if is_plan else "🛒 COMPRAR"
        actions.append([InlineKeyboardButton(buy_text, callback_data="gem_buy")])
        
        # Botão Voltar
        actions.append([InlineKeyboardButton("⬅️ Voltar para Lista", callback_data="gem_back_list")])
        
        return InlineKeyboardMarkup(actions)

    # --- TELA VITRINE (Listagem) ---
    
    # Marcadores visuais da aba atual
    p_mark = " ✅" if current_tab == "premium" else ""
    e_mark = " ✅" if current_tab == "evolution" else ""
    s_mark = " ✅" if current_tab == "supplies" else ""
    
    # Linha de Abas (3 opções)
    tabs_row_1 = [
        InlineKeyboardButton(f"👑 Premium{p_mark}", callback_data="gem_tab_premium"),
        InlineKeyboardButton(f"⛩️ Evolução{e_mark}", callback_data="gem_tab_evolution")
    ]
    tabs_row_2 = [
        InlineKeyboardButton(f"📦 Suprimentos{s_mark}", callback_data="gem_tab_supplies")
    ]
    
    # Seleciona a lista de itens
    items_to_show = []
    if current_tab == "premium": items_to_show = TAB_PREMIUM
    elif current_tab == "evolution": items_to_show = TAB_EVOLUTION
    elif current_tab == "supplies": items_to_show = TAB_SUPPLIES
    
    item_buttons = []
    
    # Renderiza lista
    if current_tab == "premium":
        # Lista vertical (Planos)
        for base_id in items_to_show:
            label = _get_button_label(base_id)
            item_buttons.append([InlineKeyboardButton(label, callback_data=f"gem_pick:{base_id}")])
    else:
        # Grade 2 colunas (Itens)
        row = []
        for i, base_id in enumerate(items_to_show, start=1):
            label = _get_button_label(base_id)
            row.append(InlineKeyboardButton(label, callback_data=f"gem_pick:{base_id}"))
            if i % 2 == 0:
                item_buttons.append(row); row = []
        if row: item_buttons.append(row)

    actions = [[InlineKeyboardButton("⬅️ Sair da Loja", callback_data="region_city")]]
    
    return InlineKeyboardMarkup([tabs_row_1, tabs_row_2] + item_buttons + actions)

# ==============================================================================
# 4. HANDLERS (Lógica de Interação)
# ==============================================================================

# CORREÇÃO DO ERRO "gem_shop_open não definido": A função está aqui agora.
async def gem_shop_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Abre o menu principal da loja de gemas."""
    query = update.callback_query
    if query: await query.answer()
    
    user_id = update.effective_user.id
    st = _state(context)
    
    # Reseta seleção ao abrir
    st["base_id"] = None
    st["qty"] = 1
    # Mantém a aba anterior ou volta para premium
    if st["tab"] not in ["premium", "evolution", "supplies"]:
        st["tab"] = "premium"

    pdata = await player_manager.get_player_data(user_id)
    gems = _gems(pdata)
    
    text = (
        f"💎 <b>LOJA DE GEMAS</b> 💎\n"
        f"Você possui: <b>{gems}</b> 💎\n\n"
        f"Selecione uma categoria abaixo:"
    )
    
    kb = _build_shop_keyboard(st["tab"], None, 1)
    
    if query:
        try: await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
        except BadRequest: 
            await query.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

async def gem_switch_tab(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muda a aba (Premium / Evolução / Suprimentos)."""
    query = update.callback_query
    await query.answer()
    
    data = query.data.replace("gem_tab_", "")
    st = _state(context)
    st["tab"] = data
    st["base_id"] = None # Limpa seleção ao mudar aba
    st["qty"] = 1
    
    # Atualiza visual
    pdata = await player_manager.get_player_data(query.from_user.id)
    gems = _gems(pdata)
    text = f"💎 <b>LOJA DE GEMAS</b> 💎\nVocê possui: <b>{gems}</b> 💎\n\nCategoria: <b>{data.upper()}</b>"
    
    kb = _build_shop_keyboard(st["tab"], None, 1)
    try: await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
    except BadRequest: pass

async def gem_pick_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Seleciona um item para ver detalhes."""
    query = update.callback_query
    await query.answer()
    
    try: item_id = query.data.split(":")[1]
    except: return

    st = _state(context)
    st["base_id"] = item_id
    st["qty"] = 1
    
    info = _get_item_info(item_id)
    price = _price_for(item_id)
    name = info.get("display_name", item_id)
    desc = info.get("description", "Sem descrição.")
    
    text = (
        f"🛒 <b>{name}</b>\n\n"
        f"<i>{desc}</i>\n\n"
        f"💎 Preço Unitário: <b>{price}</b>\n"
        f"📦 Quantidade: <b>1</b>\n"
        f"💰 Total: <b>{price}</b> 💎"
    )
    
    # Se for plano premium, exibe benefícios
    if item_id in PREMIUM_PLANS_FOR_SALE:
        plan = PREMIUM_PLANS_FOR_SALE[item_id]
        bnf = get_benefits_text(item_id)
        text = (
            f"👑 <b>{plan['name']}</b>\n\n"
            f"{bnf}\n\n"
            f"💎 Valor: <b>{price}</b>"
        )

    kb = _build_shop_keyboard(st["tab"], item_id, 1)
    try: await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
    except BadRequest: pass

async def gem_qty_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Altera quantidade (+/-)."""
    query = update.callback_query
    await query.answer()
    
    st = _state(context)
    if not st["base_id"]: return # Segurança
    
    is_plus = "plus" in query.data
    if is_plus: st["qty"] = min(st["qty"] + 1, 99)
    else: st["qty"] = max(1, st["qty"] - 1)
    
    # Atualiza texto de preço total
    item_id = st["base_id"]
    info = _get_item_info(item_id)
    price = _price_for(item_id)
    total = price * st["qty"]
    name = info.get("display_name", item_id)
    desc = info.get("description", "Sem descrição.")
    
    text = (
        f"🛒 <b>{name}</b>\n\n"
        f"<i>{desc}</i>\n\n"
        f"💎 Preço Unitário: <b>{price}</b>\n"
        f"📦 Quantidade: <b>{st['qty']}</b>\n"
        f"💰 Total: <b>{total}</b> 💎"
    )
    
    kb = _build_shop_keyboard(st["tab"], item_id, st["qty"])
    try: await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
    except BadRequest: pass

async def gem_back_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botão Voltar (sai do item e volta pra lista)."""
    query = update.callback_query
    await query.answer()
    st = _state(context)
    st["base_id"] = None # Limpa seleção
    
    # Reabre menu principal
    await gem_shop_open(update, context)

async def gem_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finaliza a compra."""
    query = update.callback_query
    user_id = query.from_user.id
    st = _state(context)
    item_id = st.get("base_id")
    qty = st.get("qty", 1)
    
    if not item_id:
        await query.answer("Nenhum item selecionado!", show_alert=True)
        return

    pdata = await player_manager.get_player_data(user_id)
    
    unit_price = _price_for(item_id)
    total_cost = unit_price * qty
    
    # Verifica saldo
    if _gems(pdata) < total_cost:
        await query.answer(f"❌ Gemas insuficientes! Precisa de {total_cost}.", show_alert=True)
        return

    # Efetua Gasto
    _spend_gems(pdata, total_cost)
    
    # Entrega
    msg = ""
    if item_id in PREMIUM_PLANS_FOR_SALE:
        # Lógica Premium (Simplificada)
        from modules.player.premium import PremiumManager
        pm = PremiumManager(pdata)
        pm.set_tier(item_id)
        # Define expiração para 30 dias
        new_exp = datetime.now(timezone.utc) + timedelta(days=30)
        pdata["premium_expires_at"] = new_exp.isoformat()
        msg = f"✅ <b>Assinatura Ativada!</b>\nAgora você é VIP."
    else:
        # Lógica Item Comum
        player_manager.add_item_to_inventory(pdata, item_id, qty)
        info = _get_item_info(item_id)
        name = info.get("display_name", item_id)
        msg = f"✅ <b>Compra realizada!</b>\nRecebido: {qty}x {name}\n💎 Gasto: {total_cost}"

    await player_manager.save_player_data(user_id, pdata)
    await query.answer("Sucesso!", show_alert=False)
    
    # Volta para a loja
    st["base_id"] = None
    st["qty"] = 1
    
    # Exibe confirmação na tela substituindo o menu
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Continuar Comprando", callback_data="gem_back_list")]])
    await query.edit_message_text(msg, reply_markup=kb, parse_mode="HTML")

# ==============================================================================
# 5. EXPORTS (Registro dos Handlers)
# ==============================================================================
gem_shop_open_handler   = CallbackQueryHandler(gem_shop_open, pattern=r'^gem_shop$')
gem_tab_handler         = CallbackQueryHandler(gem_switch_tab, pattern=r'^gem_tab_')
gem_pick_handler        = CallbackQueryHandler(gem_pick_callback, pattern=r'^gem_pick:')
gem_qty_handler         = CallbackQueryHandler(gem_qty_callback, pattern=r'^gem_qty_')
gem_back_handler        = CallbackQueryHandler(gem_back_list, pattern=r'^gem_back_list$')
gem_buy_handler         = CallbackQueryHandler(gem_buy_callback, pattern=r'^gem_buy$')