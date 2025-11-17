# handlers/gem_shop.py
import logging
from typing import Dict, List
from telegram.error import BadRequest
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

from modules import player_manager, game_data

logger = logging.getLogger(__name__)

# -------------------------------
# Helpers de Gemas (locais)
# -------------------------------
def _gems(pdata: dict) -> int:
    try:
        return max(0, int(pdata.get("gems", 0)))
    except Exception:
        return 0

def _set_gems(pdata: dict, value: int) -> None:
    pdata["gems"] = max(0, int(value))

def _add_gems(pdata: dict, amount: int) -> None:
    _set_gems(pdata, _gems(pdata) + int(amount))

def _spend_gems(pdata: dict, amount: int) -> bool:
    amount = max(0, int(amount))
    if _gems(pdata) < amount:
        return False
    _set_gems(pdata, _gems(pdata) - amount)
    return True

# -------------------------------
# Catálogo da Loja de Gemas
# (ajuste os preços à vontade)
# -------------------------------
EVOLUTION_ITEMS = [
    "cristal_de_abertura",
    "emblema_guerreiro",
    "essencia_guardia",
    "essencia_furia",
    "selo_sagrado",
    "essencia_luz",
    "emblema_berserker",
    "totem_ancestral",
    "emblema_cacador",
    "essencia_precisao",
    "marca_predador",
    "essencia_fera",
    "emblema_monge",
    "reliquia_mistica",
    "essencia_ki",
    "emblema_mago",
    "essencia_arcana",
    "essencia_elemental",
    "grimorio_arcano",
    "emblema_bardo",
    "essencia_harmonia",
    "essencia_encanto",
    "batuta_maestria",
    "emblema_assassino",
    "essencia_sombra",
    "essencia_letal",
    "manto_eterno",
    "emblema_samurai",
    "essencia_corte",
    "essencia_disciplina",
    "lamina_sagrada",
]

# preço padrão (pode personalizar item a item no dict abaixo)
DEFAULT_GEM_PRICE = 100

# Ex.: "essencia_arcana": 150,  (se não estiver no dict, cai no DEFAULT_GEM_PRICE)
GEM_SHOP: Dict[str, int] = {
    # personalize preços aqui
    # "emblema_guerreiro": 120,
}

# -------------------------------
# Utils de exibição
# -------------------------------
def _get_item_info(base_id: str) -> dict:
    try:
        info = game_data.get_item_info(base_id)
        if info:
            return dict(info)
    except Exception:
        pass
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

def _label_for(base_id: str) -> str:
    info = _get_item_info(base_id)
    name = info.get("display_name") or info.get("nome_exibicao") or base_id
    emoji = info.get("emoji", "")
    return f"{emoji}{name}" if emoji else name

def _price_for(base_id: str) -> int:
    return int(GEM_SHOP.get(base_id, DEFAULT_GEM_PRICE))

def _state(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> dict:
    st = context.user_data.get("gemshop") or {}
    if not st:
        # seleção padrão = primeiro item
        st = {"base_id": EVOLUTION_ITEMS[0], "qty": 1}
        context.user_data["gemshop"] = st
    return st

def _build_shop_keyboard(selected_id: str, qty: int) -> InlineKeyboardMarkup:
    # grade com 2 colunas dos itens
    item_buttons: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []
    for i, base_id in enumerate(EVOLUTION_ITEMS, start=1):
        name = _label_for(base_id)
        price = _price_for(base_id)
        prefix = "✅ " if base_id == selected_id else ""
        row.append(InlineKeyboardButton(f"{prefix}{name} ({price} 💎)", callback_data=f"gem_pick_{base_id}"))
        if i % 2 == 0:
            item_buttons.append(row); row = []
    if row:
        item_buttons.append(row)

    qty_row = [
        InlineKeyboardButton("➖", callback_data="gem_qty_minus"),
        InlineKeyboardButton(f"Qtd: {qty}", callback_data="noop"),
        InlineKeyboardButton("➕", callback_data="gem_qty_plus"),
    ]

    actions = [
        [InlineKeyboardButton("🛒 Comprar", callback_data="gem_buy")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market")]  # volta pro Mercado principal
    ]
    return InlineKeyboardMarkup(item_buttons + [qty_row] + actions)

# -------------------------------
# Handlers
# -------------------------------
async def gem_shop_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # pode ser chamado por callback ou por comando /gemas
    q = update.callback_query
    if q:
        # Não usamos await q.answer() aqui se formos editar logo em seguida, 
        # mas para garantir feedback visual imediato, pode manter.
        try:
            await q.answer()
        except:
            pass
        chat_id = update.effective_chat.id
        user_id = q.from_user.id
    else:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

    st = _state(context, user_id)
    base_id = st["base_id"]
    qty = max(1, int(st.get("qty", 1)))

    pdata = await player_manager.get_player_data(user_id) or {}
    gems_now = _gems(pdata)

    name = _label_for(base_id)
    price = _price_for(base_id)

    lines = [
        "💎 <b>Loja de Gemas</b>",
        f"Gemas: <b>{gems_now}</b> 💎",
        "",
        "Selecione um item para comprar por gemas:",
        "",
    ]
    lines.append(f"Selecionado: <b>{name}</b> — {price} 💎/un")

    kb = _build_shop_keyboard(base_id, qty)
    text_content = "\n".join(lines)

    if q:
        # --- CORREÇÃO DO ERRO "MESSAGE NOT MODIFIED" ---
        try:
            # Tenta editar se for uma mensagem com foto (caption)
            await q.edit_message_caption(caption=text_content, reply_markup=kb, parse_mode="HTML")
        except BadRequest as e:
            # Se o erro for "não modificado", ignoramos
            if "not modified" in str(e):
                return
            
            # Se falhar porque não tem caption (é texto puro), tentamos editar texto
            try:
                await q.edit_message_text(text=text_content, reply_markup=kb, parse_mode="HTML")
            except BadRequest as e2:
                if "not modified" in str(e2):
                    return
                # Se for outro erro, pode ser útil logar ou ignorar
                pass
        except Exception:
            # Fallback genérico
            pass
        return

    # Se não for callback (foi comando /gemas), envia nova mensagem
    await context.bot.send_message(chat_id=chat_id, text=text_content, reply_markup=kb, parse_mode="HTML")

async def gem_pick_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id

    base_id = q.data.replace("gem_pick_", "")
    if base_id not in EVOLUTION_ITEMS:
        await q.answer("Item indisponível na loja de gemas.", show_alert=True)
        return

    st = _state(context, user_id)
    st["base_id"] = base_id
    context.user_data["gemshop"] = st
    await gem_shop_open(update, context)

async def gem_change_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id

    st = _state(context, user_id)
    qty = max(1, int(st.get("qty", 1)))
    if q.data == "gem_qty_minus":
        qty = max(1, qty - 1)
    elif q.data == "gem_qty_plus":
        qty = qty + 1
    st["qty"] = qty
    context.user_data["gemshop"] = st
    await gem_shop_open(update, context)

async def gem_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    buyer_id = q.from_user.id
    chat_id = update.effective_chat.id # Pega chat_id aqui

    st = _state(context, buyer_id) # Síncrono
    base_id = st["base_id"]
    qty = max(1, int(st.get("qty", 1)))

    # Verificação síncrona
    if base_id not in EVOLUTION_ITEMS:
        await q.answer("Item indisponível na loja de gemas.", show_alert=True); return

    unit_price = _price_for(base_id) # Síncrono
    total = unit_price * qty

    # <<< CORREÇÃO 4: Adiciona await >>>
    buyer = await player_manager.get_player_data(buyer_id)
    if not buyer:
        await q.answer("Jogador não encontrado.", show_alert=True); return

    # Verificação síncrona
    if _gems(buyer) < total:
        await q.answer("Gemas insuficientes.", show_alert=True); return

    # cobra e entrega (síncrono localmente)
    if not _spend_gems(buyer, total):
        await q.answer("Falha ao cobrar gemas.", show_alert=True); return

    player_manager.add_item_to_inventory(buyer, base_id, qty) # Síncrono

    # <<< CORREÇÃO 5: Adiciona await >>>
    await player_manager.save_player_data(buyer_id, buyer)

    # Usa edit_message_text diretamente
    await q.edit_message_text(
        text=f"✅ Você comprou {qty}× {_label_for(base_id)} por {total} 💎.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_shop")]]),
        parse_mode="HTML"
    )
    
# -------------------------------
# Exports de handlers
# -------------------------------
gem_shop_open_handler   = CallbackQueryHandler(gem_shop_open, pattern=r'^gem_shop$')
gem_pick_handler        = CallbackQueryHandler(gem_pick_item,   pattern=r'^gem_pick_[A-Za-z0-9_]+$')
gem_qty_minus_handler   = CallbackQueryHandler(gem_change_qty,  pattern=r'^gem_qty_minus$')
gem_qty_plus_handler    = CallbackQueryHandler(gem_change_qty,  pattern=r'^gem_qty_plus$')
gem_buy_handler         = CallbackQueryHandler(gem_buy,         pattern=r'^gem_buy$')

# comando opcional: /gemas abre a loja
gem_shop_command_handler = CommandHandler("gemas", gem_shop_open)
