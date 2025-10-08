# handlers/gem_shop_handler.py

import logging
from typing import Dict, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

# Importe tudo que é necessário
from modules import player_manager, game_data
from modules.player.premium import PremiumManager

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Helpers e Configurações Gerais
# ----------------------------------------------------------------------

def _get_gems(pdata: dict) -> int:
    return int(pdata.get("gems", 0))

def _set_gems(pdata: dict, value: int):
    pdata["gems"] = max(0, int(value))

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception: pass
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

# ----------------------------------------------------------------------
# --- MENU PRINCIPAL DA LOJA DE GEMAS ---
# ----------------------------------------------------------------------

async def gem_shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe o menu principal da Loja de Gemas com as categorias."""
    q = update.callback_query
    if q:
        await q.answer()
        user_id = q.from_user.id
    else: # Se chamado via /gemas
        user_id = update.effective_user.id

    pdata = player_manager.get_player_data(user_id)
    current_gems = _get_gems(pdata)
    
    text = (
        "💎 <b>Loja de Gemas</b>\n\n"
        "Bem-vindo, aventureiro! Use suas gemas com sabedoria.\n\n"
        f"Seu saldo: <b>{current_gems}</b> 💎\n\n"
        "O que você deseja ver?"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Comprar Itens de Evolução", callback_data="gem_shop_items")],
        [InlineKeyboardButton("⭐ Comprar Planos Premium", callback_data="gem_shop_premium")],
        [InlineKeyboardButton("⬅️ Voltar ao Mercado", callback_data="market")]
    ])
    
    if q:
        await _safe_edit_or_send(q, context, q.message.chat_id, text, kb)
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

# ----------------------------------------------------------------------
# --- SEÇÃO 1: COMPRA DE ITENS DE EVOLUÇÃO (Seu código, adaptado) ---
# ----------------------------------------------------------------------

# -- Configuração dos Itens --
EVOLUTION_ITEMS = [
    "cristal_de_abertura", "emblema_guerreiro", "essencia_guardia", "essencia_furia",
    "selo_sagrado", "essencia_luz", "emblema_berserker", "totem_ancestral",
    "emblema_cacador", "essencia_precisao", "marca_predador", "essencia_fera",
    "emblema_monge", "reliquia_mistica", "essencia_ki", "emblema_mago",
    "essencia_arcana", "essencia_elemental", "grimorio_arcano", "emblema_bardo",
    "essencia_harmonia", "essencia_encanto", "batuta_maestria", "emblema_assassino",
    "essencia_sombra", "essencia_letal", "manto_eterno", "emblema_samurai",
    "essencia_corte", "essencia_disciplina", "lamina_sagrada",
]
DEFAULT_GEM_PRICE = 10
GEM_SHOP_PRICES: Dict[str, int] = { }

# -- Funções Auxiliares de Itens --
def _item_label_for(base_id: str) -> str:
    info = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}
    name = info.get("display_name", base_id)
    emoji = info.get("emoji", "")
    return f"{emoji}{name}" if emoji else name

def _item_price_for(base_id: str) -> int:
    return int(GEM_SHOP_PRICES.get(base_id, DEFAULT_GEM_PRICE))

def _item_state(context: ContextTypes.DEFAULT_TYPE) -> dict:
    st = context.user_data.get("gemshop_item", {})
    if not st:
        st = {"base_id": EVOLUTION_ITEMS[0], "qty": 1}
        context.user_data["gemshop_item"] = st
    return st

# -- Handlers da Loja de Itens --
async def gem_shop_items_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a interface de compra de itens."""
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    
    st = _item_state(context)
    base_id, qty = st["base_id"], st["qty"]
    pdata = player_manager.get_player_data(user_id)
    gems_now = _get_gems(pdata)

    text = (f"💎 <b>Loja de Itens</b>\n\n"
            f"Gemas: <b>{gems_now}</b> 💎\n\n"
            f"Selecionado: <b>{_item_label_for(base_id)}</b> — {_item_price_for(base_id)} 💎/un")

    # Construção do teclado (código que você criou)
    row: List[InlineKeyboardButton] = []
    item_buttons: List[List[InlineKeyboardButton]] = []
    for i, item_id in enumerate(EVOLUTION_ITEMS, 1):
        prefix = "✅ " if item_id == base_id else ""
        row.append(InlineKeyboardButton(f"{prefix}{_item_label_for(item_id)}", callback_data=f"gem_item_pick_{item_id}"))
        if i % 2 == 0:
            item_buttons.append(row); row = []
    if row: item_buttons.append(row)
    
    qty_row = [
        InlineKeyboardButton("➖", callback_data="gem_item_qty_minus"),
        InlineKeyboardButton(f"Qtd: {qty}", callback_data="noop"),
        InlineKeyboardButton("➕", callback_data="gem_item_qty_plus"),
    ]
    actions = [
        [InlineKeyboardButton("🛒 Comprar", callback_data="gem_item_buy")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="gem_shop")] # Volta pro menu principal da loja
    ]
    kb = InlineKeyboardMarkup(item_buttons + [qty_row] + actions)
    await _safe_edit_or_send(q, context, q.message.chat_id, text, kb)

async def gem_item_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    st = _item_state(context)
    st["base_id"] = q.data.replace("gem_item_pick_", "")
    context.user_data["gemshop_item"] = st
    await gem_shop_items_menu(update, context)

async def gem_item_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    st = _item_state(context)
    qty = st.get("qty", 1)
    if q.data == "gem_item_qty_minus": st["qty"] = max(1, qty - 1)
    elif q.data == "gem_item_qty_plus": st["qty"] = qty + 1
    context.user_data["gemshop_item"] = st
    await gem_shop_items_menu(update, context)
    
async def gem_item_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    
    st = _item_state(context)
    base_id, qty = st["base_id"], st["qty"]
    total_price = _item_price_for(base_id) * qty
    
    pdata = player_manager.get_player_data(user_id)
    if _get_gems(pdata) < total_price:
        await q.answer("Gemas insuficientes.", show_alert=True); return
        
    _set_gems(pdata, _get_gems(pdata) - total_price)
    player_manager.add_item_to_inventory(pdata, base_id, qty)
    player_manager.save_player_data(user_id, pdata)
    
    await q.edit_message_text(
        f"✅ Você comprou {qty}× {_item_label_for(base_id)} por {total_price} 💎.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_shop_items")]])
    )

# ----------------------------------------------------------------------
# --- SEÇÃO 2: COMPRA DE PLANOS PREMIUM (Nosso código anterior) ---
# ----------------------------------------------------------------------

async def gem_shop_premium_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a interface de compra de planos premium."""
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    
    pdata = player_manager.get_player_data(user_id)
    current_gems = _get_gems(pdata)
    
    text = (f"⭐ <b>Loja de Planos Premium</b>\n\n"
            f"Seu saldo: <b>{current_gems}</b> 💎\n\n"
            "Selecione um plano para comprar:")
    
    kb_rows = []
    for plan_id, plan in game_data.PREMIUM_PLANS_FOR_SALE.items():
        btn_text = f"{plan['name']} - {plan['price']} 💎"
        kb_rows.append([InlineKeyboardButton(btn_text, callback_data=f"gem_prem_confirm:{plan_id}")])
    
    kb_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="gem_shop")])
    await _safe_edit_or_send(q, context, q.message.chat_id, text, InlineKeyboardMarkup(kb_rows))
    
async def gem_shop_premium_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tela de confirmação para compra de plano."""
    q = update.callback_query
    await q.answer()
    plan_id = q.data.split(":")[1]
    plan = game_data.PREMIUM_PLANS_FOR_SALE.get(plan_id)
    if not plan: return

    text = (f"Confirmar a compra de:\n\n<b>{plan['name']}</b>\n"
            f"<i>{plan['description']}</i>\n\nCusto: <b>{plan['price']} 💎</b>")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirmar", callback_data=f"gem_prem_execute:{plan_id}")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="gem_shop_premium")]
    ])
    await _safe_edit_or_send(q, context, q.message.chat_id, text, kb)

async def gem_shop_premium_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Executa a compra do plano."""
    q = update.callback_query
    user_id = q.from_user.id
    plan_id = q.data.split(":")[1]
    plan = game_data.PREMIUM_PLANS_FOR_SALE.get(plan_id)
    if not plan: return
    
    pdata = player_manager.get_player_data(user_id)
    if _get_gems(pdata) < plan['price']:
        await q.answer("Gemas insuficientes.", show_alert=True); return
        
    await q.answer("Processando...")
    _set_gems(pdata, _get_gems(pdata) - plan['price'])
    premium = PremiumManager(pdata)
    premium.grant_days(tier=plan['tier'], days=plan['days'])
    player_manager.save_player_data(user_id, premium.player_data)
    
    await _safe_edit_or_send(q, context, q.message.chat_id,
        f"✅ Compra concluída!\n\nVocê adquiriu o <b>{plan['name']}</b>.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_shop_premium")]])
    )

# ----------------------------------------------------------------------
# --- EXPORTS DE HANDLERS (TODOS JUNTOS) ---
# ----------------------------------------------------------------------
gem_shop_command_handler = CommandHandler("gemas", gem_shop_menu)

# Menu Principal
gem_shop_menu_handler = CallbackQueryHandler(gem_shop_menu, pattern=r'^gem_shop$')

# Handlers da Loja de Itens
gem_shop_items_handler = CallbackQueryHandler(gem_shop_items_menu, pattern=r'^gem_shop_items$')
gem_item_pick_handler = CallbackQueryHandler(gem_item_pick, pattern=r'^gem_item_pick_')
gem_item_qty_handler = CallbackQueryHandler(gem_item_qty, pattern=r'^(gem_item_qty_minus|gem_item_qty_plus)$')
gem_item_buy_handler = CallbackQueryHandler(gem_item_buy, pattern=r'^gem_item_buy$')

# Handlers da Loja de Planos Premium
gem_shop_premium_handler = CallbackQueryHandler(gem_shop_premium_menu, pattern=r'^gem_shop_premium$')
gem_prem_confirm_handler = CallbackQueryHandler(gem_shop_premium_confirm, pattern=r'^gem_prem_confirm:')
gem_prem_execute_handler = CallbackQueryHandler(gem_shop_premium_execute, pattern=r'^gem_prem_execute:')