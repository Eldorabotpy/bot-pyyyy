# handlers/kingdom_shop_handler.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

# --- IMPORTS DO SISTEMA ---
from modules import player_manager, game_data, file_ids
# Importante: Pega o ID da sessão atual (ObjectId) em vez do ID do Telegram
from modules.auth_utils import get_current_player_id 

logger = logging.getLogger(__name__)

# ==============================================================================
#  CONFIGURAÇÃO: Loja do Reino (Gold)
# ==============================================================================
KINGDOM_SHOP = {
    "pedra_do_aprimoramento": ("Pedra de Aprimoramento", 350),
    "pergaminho_durabilidade": ("Pergaminho de Reparo", 350),
    "joia_da_forja": ("Joia de Aprimoramento", 400),
    "nucleo_forja_fraco": ("Núcleo Fraco", 500),
    "nucleo_forja_comum": ("Núcleo Comum", 1000),

    # ==========================
    # Ferramentas de Coleta (T1)
    # ==========================
    "machado_pedra": ("Machado de Pedra (Lenhador)", 250),
    "picareta_pedra": ("Picareta de Pedra (Minerador)", 250),
    "foice_pedra": ("Foice de Pedra (Colhedor)", 250),
    "faca_pedra": ("Faca de Pederneira (Esfolador)", 250),
    "frasco_vidro": ("Frasco de Vidro (Alquimista)", 250),
    
        # ==========================
    # Ferramentas de CRIAÇÃO (T1)
    # ==========================
    "martelo_ferreiro_t1": ("Martelo de Ferreiro (Criação)", 600),
    "martelo_armeiro_t1": ("Martelo de Armeiro (Criação)", 600),
    "ferramentas_alfaiate_t1": ("Ferramentas de Alfaiate (Criação)", 550),
    "ferramentas_joalheiro_t1": ("Ferramentas de Joalheiro (Criação)", 550),
    "ferramentas_curtidor_t1": ("Ferramentas de Curtidor (Criação)", 550),
    "ferramentas_fundidor_t1": ("Ferramentas de Fundidor (Criação)", 550),

}


# ==============================================================================
#  FUNÇÕES AUXILIARES
# ==============================================================================
def _gold(pdata: dict) -> int:
    return int(pdata.get("gold", 0))

def _set_gold(pdata: dict, value: int):
    pdata["gold"] = max(0, int(value))

def _item_info(base_id: str) -> dict:
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {})

async def _send_with_media(chat_id, context, caption, kb, keys):
    """Envia mensagem com imagem/vídeo se disponível, ou apenas texto."""
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

# ==============================================================================
#  GERENCIAMENTO DE ESTADO (MEMÓRIA TEMPORÁRIA)
# ==============================================================================
def _king_state(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Recupera ou inicia o estado da loja na memória do usuário."""
    st = context.user_data.get("kingdom_shop")
    if not st:
        # Seleciona o primeiro item da lista por padrão
        first = next(iter(KINGDOM_SHOP.keys()))
        st = {"base_id": first, "qty": 1}
        context.user_data["kingdom_shop"] = st
    return st

def _build_kingdom_keyboard(selected_id: str, qty: int) -> InlineKeyboardMarkup:
    """Monta o teclado visual da loja."""
    # 1. Grade de Itens (2 Colunas)
    item_rows = []
    row = []
    for base_id, (name_override, price) in KINGDOM_SHOP.items():
        # Nome curto para caber no botão
        label_name = name_override.split(" ")[0] if len(name_override) > 15 else name_override
        
        # Marcador visual se selecionado
        prefix = "✅ " if base_id == selected_id else "📦 "
        
        btn_text = f"{prefix}{label_name} ({price})"
        row.append(InlineKeyboardButton(btn_text, callback_data=f"king_set_{base_id}"))
        
        if len(row) == 2:
            item_rows.append(row)
            row = []
    if row: item_rows.append(row)

    # 2. Controles de Quantidade e Botão de Compra
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

# ==============================================================================
#  HANDLER PRINCIPAL (EXIBIR LOJA)
# ==============================================================================
async def market_kingdom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    # 🔒 SEGURANÇA: Obtém o ID da sessão (MongoDB ObjectId)
    user_id = get_current_player_id(update, context)
    chat_id = update.effective_chat.id
    
    if not user_id:
        await q.answer("❌ Sessão expirada. Digite /start para logar.", show_alert=True)
        return

    # Busca dados usando o player_manager (que lida com a conversão str -> ObjectId)
    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        await q.answer("❌ Erro ao carregar perfil.", show_alert=True)
        return

    gold = _gold(pdata)
    
    # Recupera estado visual
    st = _king_state(context)
    base_id = st["base_id"]
    qty = max(1, int(st.get("qty", 1)))

    # Monta Texto
    item_info = _item_info(base_id)
    shop_data = KINGDOM_SHOP.get(base_id, ["Item", 0])
    shop_name = shop_data[0]
    price = shop_data[1]
    desc = item_info.get("description", "Item essencial para aventureiros.")
    
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
    
    # Limpa mensagem anterior para evitar glitches visuais
    try: await q.delete_message()
    except: pass
    
    keys = ["loja_do_reino", "img_loja_reino", "market_kingdom"]
    await _send_with_media(chat_id, context, text, kb, keys)

# ==============================================================================
#  AÇÕES (SELEÇÃO, QUANTIDADE, COMPRA)
# ==============================================================================

async def kingdom_set_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    base_id = q.data.replace("king_set_", "")
    
    if base_id not in KINGDOM_SHOP:
        await q.answer("Item indisponível.", show_alert=True); return

    st = _king_state(context)
    if st["base_id"] != base_id:
        st["base_id"] = base_id
        st["qty"] = 1 # Reseta quantidade ao trocar de item
        
    context.user_data["kingdom_shop"] = st
    await market_kingdom(update, context)

async def kingdom_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try: await q.answer() 
    except: pass
    
    st = _king_state(context)
    qty = max(1, int(st.get("qty", 1)))

    if q.data == "king_q_minus": 
        qty = max(1, qty - 1)
    elif q.data == "king_q_plus": 
        qty += 1

    st["qty"] = qty
    context.user_data["kingdom_shop"] = st
    await market_kingdom(update, context)

def _is_unique_equipable(base_id: str) -> bool:
    info = _item_info(base_id)
    # Qualquer item com "slot" deve ser tratado como equipamento único
    return bool(info.get("slot"))

def _instantiate_unique_item(base_id: str) -> dict:
    info = _item_info(base_id) or {}
    inst = {"base_id": base_id}

    # Se tiver durabilidade no item base, copia como estado inicial
    dur = info.get("durability")
    if isinstance(dur, (list, tuple)) and len(dur) == 2:
        inst["durability"] = [int(dur[0]), int(dur[1])]

    return inst

async def market_kingdom_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query

    user_id = get_current_player_id(update, context)
    if not user_id:
        await q.answer("❌ Você não está logado!", show_alert=True)
        return

    st = _king_state(context)
    base_id = st["base_id"]
    qty = max(1, int(st.get("qty", 1)))

    if base_id not in KINGDOM_SHOP:
        await q.answer("Erro: Item inválido.", show_alert=True)
        return

    # ✅ Se for equipamento/ferramenta, trava quantidade ANTES do preço
    if _is_unique_equipable(base_id):
        qty = 1

    name, price = KINGDOM_SHOP[base_id]
    total_cost = price * qty

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        await q.answer("❌ Erro de dados.", show_alert=True)
        return

    if _gold(pdata) < total_cost:
        await q.answer(f"Falta Ouro! Custa {total_cost} 🪙.", show_alert=True)
        return

    _set_gold(pdata, _gold(pdata) - total_cost)

    if _is_unique_equipable(base_id):
        inst = _instantiate_unique_item(base_id)
        player_manager.add_unique_item(pdata, inst)
    else:
        player_manager.add_item_to_inventory(pdata, base_id, qty)

    await player_manager.save_player_data(user_id, pdata)

    await q.answer(f"✅ Comprou {qty}x {name}!", show_alert=False)

    st["qty"] = 1
    context.user_data["kingdom_shop"] = st

    await market_kingdom(update, context)


async def market_kingdom_buy_legacy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona chamadas antigas para a função nova de compra."""
    await market_kingdom_buy(update, context)

# ==============================================================================
#  HANDLERS EXPORTADOS
# ==============================================================================
market_kingdom_handler = CallbackQueryHandler(market_kingdom, pattern=r'^market_kingdom$')
kingdom_set_item_handler = CallbackQueryHandler(kingdom_set_item, pattern=r'^king_set_')
kingdom_qty_minus_handler = CallbackQueryHandler(kingdom_qty, pattern=r'^king_q_minus$')
kingdom_qty_plus_handler = CallbackQueryHandler(kingdom_qty, pattern=r'^king_q_plus$')
market_kingdom_buy_handler = CallbackQueryHandler(market_kingdom_buy, pattern=r'^king_buy$')
market_kingdom_buy_legacy_handler = CallbackQueryHandler(market_kingdom_buy_legacy, pattern=r'^king_buy_')