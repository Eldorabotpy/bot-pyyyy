# handlers/gem_shop.py
import logging
from typing import Dict, List
from datetime import datetime, timezone, timedelta # <--- IMPORTANTE PARA CALCULAR O TEMPO

from telegram.error import BadRequest
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

from modules import player_manager, game_data

# Importa a configuração dos planos que definimos anteriormente
try:
    from modules.game_data.premium import PREMIUM_PLANS_FOR_SALE
except ImportError:
    PREMIUM_PLANS_FOR_SALE = {}

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

def _spend_gems(pdata: dict, amount: int) -> bool:
    amount = max(0, int(amount))
    if _gems(pdata) < amount:
        return False
    _set_gems(pdata, _gems(pdata) - amount)
    return True

# -------------------------------
# Catálogo da Loja de Gemas
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

# Juntamos os Itens Normais + Chaves dos Planos VIP
# Isso faz com que os VIPs apareçam na lista de compra
SHOP_KEYS = list(PREMIUM_PLANS_FOR_SALE.keys()) + EVOLUTION_ITEMS

DEFAULT_GEM_PRICE = 100
GEM_SHOP: Dict[str, int] = {} # Pode personalizar preços de itens soltos aqui

# -------------------------------
# Utils de exibição e Preço
# -------------------------------
def _get_plan_info(plan_key: str) -> dict:
    return PREMIUM_PLANS_FOR_SALE.get(plan_key, {})

def _get_item_info(base_id: str) -> dict:
    try:
        info = game_data.get_item_info(base_id)
        if info:
            return dict(info)
    except Exception:
        pass
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

def _label_for(base_id: str) -> str:
    # 1. Verifica se é um Plano VIP
    if base_id in PREMIUM_PLANS_FOR_SALE:
        plan = PREMIUM_PLANS_FOR_SALE[base_id]
        return f"👑 {plan.get('name', base_id)}"
    
    # 2. Se não, é item normal
    info = _get_item_info(base_id)
    name = info.get("display_name") or info.get("nome_exibicao") or base_id
    emoji = info.get("emoji", "")
    return f"{emoji}{name}" if emoji else name

def _price_for(base_id: str) -> int:
    # 1. Verifica preço do Plano VIP
    if base_id in PREMIUM_PLANS_FOR_SALE:
        return int(PREMIUM_PLANS_FOR_SALE[base_id].get("price", 999999))

    # 2. Se não, é preço de item normal
    return int(GEM_SHOP.get(base_id, DEFAULT_GEM_PRICE))

def _state(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> dict:
    st = context.user_data.get("gemshop") or {}
    if not st:
        # seleção padrão = primeiro item da lista combinada
        first_item = SHOP_KEYS[0] if SHOP_KEYS else "nenhum"
        st = {"base_id": first_item, "qty": 1}
        context.user_data["gemshop"] = st
    return st

def _build_shop_keyboard(selected_id: str, qty: int) -> InlineKeyboardMarkup:
    # grade com 2 colunas dos itens
    item_buttons: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []
    
    for i, base_id in enumerate(SHOP_KEYS, start=1):
        name = _label_for(base_id)
        price = _price_for(base_id)
        
        # Marca visualmente o selecionado
        prefix = "✅ " if base_id == selected_id else ""
        
        # Encurta nomes muito longos para caber no botão
        display_text = f"{prefix}{name}"
        if len(display_text) > 20:
             display_text = display_text[:18] + ".."
             
        row.append(InlineKeyboardButton(f"{display_text} ({price}💎)", callback_data=f"gem_pick_{base_id}"))
        
        if i % 2 == 0:
            item_buttons.append(row); row = []
    if row:
        item_buttons.append(row)

    # Se for plano VIP, não mostra controle de quantidade (só pode comprar 1 assinatura por vez)
    is_plan = selected_id in PREMIUM_PLANS_FOR_SALE
    
    actions = []
    
    if not is_plan:
        qty_row = [
            InlineKeyboardButton("➖", callback_data="gem_qty_minus"),
            InlineKeyboardButton(f"Qtd: {qty}", callback_data="noop"),
            InlineKeyboardButton("➕", callback_data="gem_qty_plus"),
        ]
        actions.append(qty_row)

    buy_btn_text = "👑 Assinar Agora" if is_plan else "🛒 Comprar Item"
    actions.append([InlineKeyboardButton(buy_btn_text, callback_data="gem_buy")])
    actions.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market")])
    
    return InlineKeyboardMarkup(item_buttons + actions)

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
    base_id = st["base_id"]
    
    # Se for plano, força quantidade 1
    if base_id in PREMIUM_PLANS_FOR_SALE:
        st["qty"] = 1
        
    qty = max(1, int(st.get("qty", 1)))

    pdata = await player_manager.get_player_data(user_id) or {}
    gems_now = _gems(pdata)

    name = _label_for(base_id)
    price = _price_for(base_id)

    lines = [
        "💎 <b>Loja de Gemas & Premium</b>",
        f"Seu saldo: <b>{gems_now}</b> 💎",
        "",
    ]
    
    if base_id in PREMIUM_PLANS_FOR_SALE:
        plan_desc = PREMIUM_PLANS_FOR_SALE[base_id].get("description", "")
        lines.append(f"👑 <b>Plano Selecionado:</b> {name}")
        lines.append(f"<i>{plan_desc}</i>")
        lines.append(f"💰 Custo: <b>{price}</b> Gemas")
        lines.append("\n⚠️ <i>A compra ativará os benefícios imediatamente.</i>")
    else:
        lines.append(f"📦 <b>Item:</b> {name}")
        lines.append(f"💰 Preço Unitário: {price} 💎")
        lines.append(f"🔢 Quantidade: {qty}")
        lines.append(f"💵 Total: <b>{price * qty}</b> 💎")

    kb = _build_shop_keyboard(base_id, qty)
    text_content = "\n".join(lines)

    if q:
        try:
            await q.edit_message_caption(caption=text_content, reply_markup=kb, parse_mode="HTML")
        except BadRequest:
            try:
                await q.edit_message_text(text=text_content, reply_markup=kb, parse_mode="HTML")
            except BadRequest:
                pass
        except Exception:
            pass
        return

    await context.bot.send_message(chat_id=chat_id, text=text_content, reply_markup=kb, parse_mode="HTML")

async def gem_pick_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id

    base_id = q.data.replace("gem_pick_", "")
    
    # Valida se está na lista de chaves (Item ou Plano)
    if base_id not in SHOP_KEYS:
        await q.answer("Item indisponível.", show_alert=True)
        return

    st = _state(context, user_id)
    st["base_id"] = base_id
    st["qty"] = 1 # Reseta qtd ao trocar item
    context.user_data["gemshop"] = st
    await gem_shop_open(update, context)

async def gem_change_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id

    st = _state(context, user_id)
    # Se for plano, ignora mudança de quantidade
    if st["base_id"] in PREMIUM_PLANS_FOR_SALE:
        return

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
    # await q.answer() # Respondemos depois com mensagem específica
    buyer_id = q.from_user.id

    st = _state(context, buyer_id)
    base_id = st["base_id"]
    qty = max(1, int(st.get("qty", 1)))

    if base_id not in SHOP_KEYS:
        await q.answer("Item inválido.", show_alert=True); return

    unit_price = _price_for(base_id)
    total_cost = unit_price * qty
    
    # Se for plano VIP, a quantidade é sempre 1 e o custo é o do plano
    is_vip_plan = base_id in PREMIUM_PLANS_FOR_SALE
    if is_vip_plan:
        qty = 1
        total_cost = unit_price

    buyer = await player_manager.get_player_data(buyer_id)
    if not buyer:
        await q.answer("Erro ao carregar dados.", show_alert=True); return

    if _gems(buyer) < total_cost:
        await q.answer(f"Você precisa de {total_cost} gemas.", show_alert=True); return

    # --- TENTA COBRAR ---
    if not _spend_gems(buyer, total_cost):
        await q.answer("Falha na transação.", show_alert=True); return

    # =================================================================
    # LÓGICA DE ENTREGA (CORREÇÃO PRINCIPAL)
    # =================================================================
    if is_vip_plan:
        # É UM PLANO VIP - Atualiza Status e Data
        plan_info = PREMIUM_PLANS_FOR_SALE[base_id]
        new_tier = plan_info["tier"]      # ex: "vip", "lenda"
        days_to_add = plan_info["days"]
        
        # Calcula nova data
        now = datetime.now(timezone.utc)
        current_expiry_iso = buyer.get("premium_expires_at")
        
        # Define o ponto de partida (Agora ou final da assinatura atual)
        start_time = now
        if current_expiry_iso:
            try:
                current_expiry = datetime.fromisoformat(current_expiry_iso)
                if current_expiry.tzinfo is None:
                    current_expiry = current_expiry.replace(tzinfo=timezone.utc)
                
                # Se ainda é válido, estende. Se já venceu, começa de agora.
                if current_expiry > now:
                    start_time = current_expiry
            except Exception:
                pass # Erro de data, usa 'now'

        new_expiry = start_time + timedelta(days=days_to_add)
        
        # Salva no Player Data
        buyer["premium_tier"] = new_tier
        buyer["premium_expires_at"] = new_expiry.isoformat()
        
        msg_sucesso = f"👑 <b>Sucesso!</b> Você ativou <b>{plan_info['name']}</b>.\n📅 Válido até: {new_expiry.strftime('%d/%m/%Y')}"

    else:
        # É UM ITEM NORMAL - Entrega no inventário
        player_manager.add_item_to_inventory(buyer, base_id, qty)
        item_label = _label_for(base_id)
        msg_sucesso = f"✅ Compra realizada!\nRecebido: {qty}x {item_label}."

    # Salva tudo no banco de dados
    await player_manager.save_player_data(buyer_id, buyer)

    # Feedback para o usuário
    await q.edit_message_text(
        text=msg_sucesso,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar à Loja", callback_data="gem_shop")]]),
        parse_mode="HTML"
    )

# -------------------------------
# Exports
# -------------------------------
gem_shop_open_handler   = CallbackQueryHandler(gem_shop_open, pattern=r'^gem_shop$')
gem_pick_handler        = CallbackQueryHandler(gem_pick_item,   pattern=r'^gem_pick_')
gem_qty_minus_handler   = CallbackQueryHandler(gem_change_qty,  pattern=r'^gem_qty_minus$')
gem_qty_plus_handler    = CallbackQueryHandler(gem_change_qty,  pattern=r'^gem_qty_plus$')
gem_buy_handler         = CallbackQueryHandler(gem_buy,         pattern=r'^gem_buy$')
gem_shop_command_handler = CommandHandler("gemas", gem_shop_open)