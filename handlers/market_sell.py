# handlers/adventurer_market_handler.py
import logging
from typing import List, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

# --- SEUS MÓDULOS ---
from modules import player_manager, game_data, file_ids, market_manager
from modules.market_manager import render_listing_line as _mm_render_listing_line
from modules import market_utils

# Importa os dados reais de classes e atributos
try:
    from modules.game_data.attributes import STAT_EMOJI
except ImportError:
    STAT_EMOJI = {} # Fallback vazio, será preenchido na função se falhar

try:
    from modules.game_data.classes import CLASSES_DATA
except ImportError:
    CLASSES_DATA = {}

logger = logging.getLogger(__name__)

# Fallback para Display Utils
try:
    from modules import display_utils
except ImportError:
    display_utils = None

# ==============================
#  BLOQUEIO: Itens de evolução e especiais
# ==============================
EVOLUTION_ITEMS: set[str] = {
    "emblema_guerreiro", "essencia_guardia", "selo_sagrado", "essencia_luz", 
    "emblema_berserker", "essencia_furia", "totem_ancestral", 
    "emblema_cacador", "essencia_precisao", "marca_predador", 
    "emblema_monge", "essencia_ki", "reliquia_mistica", 
    "emblema_mago", "essencia_elemental", "grimorio_arcano", 
    "emblema_bardo", "essencia_harmonia", "batuta_maestria", 
    "emblema_assassino", "essencia_sombra", "manto_eterno", 
    "emblema_samurai", "essencia_corte", "lamina_sagrada",
    "gems", "gemas", "chave_dungeon", "ticket_arena"
}

# ==============================
#  HELPERS VISUAIS (Cards & Classes)
# ==============================
def _get_item_info(base_id: str) -> dict:
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

def _rarity_to_int(rarity):
    order = {"comum": 1, "incomum": 2, "bom": 3, "raro": 4, "epico": 5, "lendario": 6, "mitico": 7, "divino": 8}
    return order.get(str(rarity).lower(), 0)

def _detect_class_display(inst: dict, base_id: str) -> str:
    """
    Detecta a classe do item usando:
    1. A propriedade 'class_lock' ou 'classe' no item.
    2. Se não tiver, procura o nome da classe dentro do ID do item (ex: 'espada_guerreiro').
    3. Usa o arquivo classes.py para pegar o Emoji e Nome corretos.
    """
    # 1. Tenta pegar a chave da classe direta do item
    raw_class = inst.get("class_lock") or inst.get("class") or inst.get("classe") or inst.get("required_class")
    
    # 2. Se não tem trava explícita, tenta achar o nome de alguma classe no ID do item
    if not raw_class:
        base_id_lower = base_id.lower()
        # Varre todas as classes cadastradas no classes.py
        for c_key in CLASSES_DATA.keys():
            if c_key in base_id_lower:
                raw_class = c_key
                break

    # 3. Verifica se é Universal
    if not raw_class or str(raw_class).lower() in ["none", "universal", "todos", "all", "any"]:
        return "🌎 Universal"

    # 4. Formata usando os dados do classes.py
    ckey = str(raw_class).lower().strip()
    
    if ckey in CLASSES_DATA:
        c_info = CLASSES_DATA[ckey]
        emoji = c_info.get("emoji", "🛡️")
        name = c_info.get("display_name", ckey.capitalize())
        return f"{emoji} {name}"
    
    # Fallback se a classe existir no item mas não no arquivo (raro)
    return f"🛡️ {ckey.capitalize()}"

def _get_stat_emoji(key: str) -> str:
    """Retorna o emoji do atributo usando attributes.py"""
    key_lower = key.lower()
    
    # Busca direta
    if key_lower in STAT_EMOJI:
        return STAT_EMOJI[key_lower]
        
    # Alias comuns
    if "hp" in key_lower or "vida" in key_lower: return "❤️"
    if "atk" in key_lower or "dmg" in key_lower: return "⚔️"
    if "def" in key_lower: return "🛡️"
    if "int" in key_lower: return "🧠"
    if "str" in key_lower: return "💪"
    if "agi" in key_lower: return "🏃"
    if "luc" in key_lower or "sorte" in key_lower: return "🍀"
    
    return "✨"

def _render_item_card(idx: int, item_wrapper: dict) -> str:
    """Gera o texto visual bonito para a lista (Estilo Card RPG)."""
    # Ícones numéricos
    icons = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    icon_num = icons[idx] if idx < len(icons) else f"{idx}️⃣"
    
    if item_wrapper["type"] == "stack":
        base_id = item_wrapper["base_id"]
        qty = item_wrapper["qty"]
        info = _get_item_info(base_id)
        name = info.get("display_name") or base_id.replace("_", " ").title()
        emoji = info.get("emoji", "📦")
        
        # Layout Stack
        return (
            f"{icon_num}┈➤ {emoji} <b>{name}</b>\n"
            f" ╰┈➤ 📦 Quantidade: {qty} un."
        )
    
    else: # Unique (Equipamento)
        inst = item_wrapper["inst"]
        base_id = item_wrapper["sort_name"]
        info = _get_item_info(base_id)
        name = inst.get("display_name") or info.get("display_name") or base_id
        emoji = inst.get("emoji") or info.get("emoji") or "⚔️"
        rarity = str(inst.get("rarity", "comum")).upper()
        
        # Durabilidade
        cur_d, max_d = inst.get("durability", [20, 20]) if isinstance(inst.get("durability"), list) else [20,20]
        dura_str = f"[{int(cur_d)}/{int(max_d)}]"
        
        # Upgrade (+1, +2...)
        upg = inst.get("upgrade_level", 0)
        plus_str = f" +{upg}" if upg > 0 else ""

        # --- PROCESSAMENTO DE ATRIBUTOS ---
        stats_found = []
        all_stats = {}
        
        if isinstance(inst.get("attributes"), dict): all_stats.update(inst["attributes"])
        if isinstance(inst.get("enchantments"), dict): all_stats.update(inst["enchantments"])
        
        for key, raw_val in all_stats.items():
            val = raw_val
            if isinstance(raw_val, dict): val = raw_val.get("value", 0)
            try: val = int(float(val))
            except: continue
            
            if val > 0:
                icon = _get_stat_emoji(key)
                stats_found.append(f"{icon}+{val}")
        
        stats_str = ", ".join(stats_found[:4]) if stats_found else "Sem atributos"
        
        # --- RECONHECIMENTO DE CLASSE ---
        class_str = _detect_class_display(inst, base_id)

        # Layout Final
        return (
            f"{icon_num}┈➤{emoji} <b>{name}{plus_str}</b> [{rarity}] {dura_str}\n"
            f"├┈➤ {stats_str}\n"
            f"╰┈➤ {class_str}"
        )

# ==============================
#  HANDLERS PRINCIPAIS
# ==============================

async def market_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    text = "🏪 <b>Centro Comercial de Eldora</b>\n\nAs ruas do mercado estão agitadas. Onde você deseja ir?"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎒 Mercado de Ouro", callback_data="market_adventurer")],
        [InlineKeyboardButton("🏛️ Casa de Leilões (Gemas)", callback_data="gem_market_main")],
        [InlineKeyboardButton("💎 Loja de Gemas (Premium)", callback_data="gem_shop")],
        [InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data="show_kingdom_menu")]
    ])
    await _send_smart(query, context, chat_id, text, kb, "market")

async def market_adventurer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "🎒 <b>Mercado do Aventureiro</b>\nCompre e venda itens por Ouro."
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Comprar Itens", callback_data="market_list")],
        [InlineKeyboardButton("🛒 Vender Item", callback_data="market_sell_menu")], 
        [InlineKeyboardButton("👤 Minhas Vendas", callback_data="market_my")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market")]
    ])
    await _send_smart(query, context, update.effective_chat.id, text, kb, "mercado_aventureiro")

# ==============================
#  VENDA
# ==============================

async def market_sell_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "➕ <b>Vender Item - Escolha a Categoria</b>\n\nSelecione o tipo de item para vender por Ouro:"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Equipamentos", callback_data="market_sell_cat:equip:1")],
        [InlineKeyboardButton("🧱 Materiais", callback_data="market_sell_cat:mat:1"),
         InlineKeyboardButton("🧪 Consumíveis", callback_data="market_sell_cat:cons:1")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]
    ])
    await _safe_edit(query, text, kb)

async def market_sell_list_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try: _, category, page_str = query.data.split(':')
    except: category, page_str = "mat", "1"
    page = int(page_str)

    pdata = await player_manager.get_player_data(user_id) or {}
    inv = pdata.get("inventory", {}) or {}
    gold = pdata.get("gold", 0)
    
    sellable = []
    
    # 1. Filtra itens
    for item_id, data in inv.items():
        if isinstance(data, dict): # Unique
            base_id = data.get("base_id") or data.get("tpl") or item_id
            qty = data.get("qty", 0) or 1
            is_unique = True
            inst_data = data
        else: # Stack
            base_id = item_id
            qty = int(data)
            is_unique = False
            inst_data = {}

        # Bloqueios
        if base_id in EVOLUTION_ITEMS: continue
        if any(x in str(base_id) for x in ["tomo_", "livro_", "skin_", "caixa_", "pergaminho_skill"]): continue

        # Categoria
        info = _get_item_info(base_id)
        itype = str(info.get("type", "")).lower()
        should_show = False

        if category == "equip" and (is_unique or itype in ["equipamento", "arma", "armadura", "acessorio"]):
            should_show = True
        elif category == "cons" and (not is_unique and itype in ["consumivel", "consumable", "potion", "food"]):
            should_show = True
        elif category == "mat" and (not is_unique and itype not in ["consumivel", "potion", "equipamento"]):
            should_show = True

        if should_show and qty > 0:
            rarity_rank = _rarity_to_int(inst_data.get("rarity", "comum")) if is_unique else 0
            sellable.append({
                "type": "unique" if is_unique else "stack",
                "uid": item_id, 
                "base_id": base_id, 
                "qty": qty, 
                "inst": inst_data,
                "sort_name": base_id,
                "rarity_rank": rarity_rank
            })

    # 2. Ordenação (Raridade -> Nome)
    sellable.sort(key=lambda x: (0 if x["type"] == "unique" else 1, -x["rarity_rank"], x["sort_name"]))

    # 3. Paginação
    ITEMS_PER_PAGE = 5
    total = len(sellable)
    total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    page = max(1, min(page, total_pages))
    
    start = (page - 1) * ITEMS_PER_PAGE
    items_page = sellable[start : start + ITEMS_PER_PAGE]

    # 4. Renderização do Texto (Card Style)
    cat_names = {"equip": "⚔️ Equipamentos", "cons": "🧪 Consumíveis", "mat": "🧱 Materiais"}
    cat_title = cat_names.get(category, "Itens")

    header = (
        f"╭┈┈┈➤ 🛒 <b>VENDER: {cat_title} ({page}/{total_pages})</b>\n"
        f" │ 💰 <b>Saldo:</b> {gold:,} 🪙\n"
        f"╰┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤\n\n"
    )
    
    body_lines = []
    selection_buttons = [] 

    if not sellable:
        body_lines.append("🎒 <i>Nenhum item encontrado nesta categoria.</i>")
    elif not items_page:
        body_lines.append("<i>Página vazia.</i>")
    else:
        for idx, item in enumerate(items_page, start=1):
            text_block = _render_item_card(idx, item)
            body_lines.append(text_block)
            body_lines.append("") 
            
            if item["type"] == "unique":
                cb = f"market_pick_unique_{item['uid']}"
            else:
                cb = f"market_pick_stack_{item['base_id']}"
            
            selection_buttons.append(InlineKeyboardButton(f"{idx} 🛒", callback_data=cb))

    full_text = header + "\n".join(body_lines)

    # 5. Montagem do Teclado
    keyboard = []
    if selection_buttons:
        keyboard.append(selection_buttons)

    # Navegação
    nav_row = []
    if page > 1: nav_row.append(InlineKeyboardButton("⬅️ Ant.", callback_data=f"market_sell_cat:{category}:{page-1}"))
    nav_row.append(InlineKeyboardButton("📂 Categorias", callback_data="market_sell_menu"))
    if total > start + ITEMS_PER_PAGE: nav_row.append(InlineKeyboardButton("Prox. ➡️", callback_data=f"market_sell_cat:{category}:{page+1}"))
    
    if nav_row: keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Mercado", callback_data="market_adventurer")])

    await _safe_edit(query, full_text, InlineKeyboardMarkup(keyboard))

# ==============================
#  RESTO DO FLUXO (PREÇO/QTD)
# ==============================

async def market_pick_stack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    base_id = q.data.replace("market_pick_stack_", "")
    user_id = q.from_user.id
    
    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {})
    qty_have = int(inv.get(base_id, 0))

    if qty_have <= 0:
        await q.answer("Você não possui este item.", show_alert=True); return

    context.user_data["market_pending"] = {"type": "stack", "base_id": base_id, "qty_have": qty_have, "qty": 1}
    context.user_data["market_price"] = 50 
    await _show_qty_spinner(q, context)

async def market_pick_unique(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    unique_id = q.data.replace("market_pick_unique_", "")
    context.user_data["market_pending"] = {"type": "unique", "uid": unique_id, "qty": 1}
    context.user_data["market_price"] = 500 
    await _show_price_spinner(q, context)

# --- Spinners ---
async def market_qty_spin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    pending = context.user_data.get("market_pending")
    if not pending: return
    action = q.data
    cur = pending["qty"]
    max_q = pending.get("qty_have", 1)
    
    if "inc" in action: cur += 1
    elif "dec" in action: cur -= 1
    if cur < 1: cur = 1
    if cur > max_q: cur = max_q
    
    pending["qty"] = cur
    await _show_qty_spinner(q, context)

async def market_price_spin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cur = context.user_data.get("market_price", 50)
    action = q.data
    if "inc_1000" in action: cur += 1000
    elif "inc_100" in action: cur += 100
    elif "inc_10" in action: cur += 10
    elif "dec_1000" in action: cur -= 1000
    elif "dec_100" in action: cur -= 100
    elif "dec_10" in action: cur -= 10
    if cur < 1: cur = 1
    context.user_data["market_price"] = cur
    await _show_price_spinner(q, context)

# --- Helpers de Spinner ---
async def _show_qty_spinner(q, context):
    pending = context.user_data.get("market_pending")
    cur = pending["qty"]
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("-1", callback_data="mkt_pack_dec_1"), InlineKeyboardButton(f"{cur}", callback_data="noop"), InlineKeyboardButton("+1", callback_data="mkt_pack_inc_1")],
        [InlineKeyboardButton("✅ Confirmar Quantidade", callback_data="mkt_pack_confirm"), InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]
    ])
    await _safe_edit(q, f"Quantos itens deseja vender?", kb)

async def _show_price_spinner(q, context):
    cur = context.user_data.get("market_price", 50)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("-100", callback_data="mktp_dec_100"), InlineKeyboardButton("-10", callback_data="mktp_dec_10")],
        [InlineKeyboardButton(f"💰 {cur} Ouro", callback_data="noop")],
        [InlineKeyboardButton("+10", callback_data="mktp_inc_10"), InlineKeyboardButton("+100", callback_data="mktp_inc_100")],
        [InlineKeyboardButton("✅ Confirmar Preço", callback_data="mktp_confirm"), InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]
    ])
    await _safe_edit(q, f"Defina o preço total em Ouro:", kb)

# --- Confirmações ---
async def market_qty_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await _show_price_spinner(q, context)

async def market_finalize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    pending = context.user_data.get("market_pending")
    if not pending: await q.answer("Sessão expirada.", show_alert=True); return

    price = context.user_data.get("market_price", 50)
    pdata = await player_manager.get_player_data(user_id)
    
    if pending["type"] == "stack":
        base_id = pending["base_id"]
        qty = pending["qty"]
        if not player_manager.remove_item_from_inventory(pdata, base_id, qty):
            await q.answer("Erro: Item insuficiente.", show_alert=True); return
        item_payload = {"type": "stack", "base_id": base_id, "qty": qty}
        
    elif pending["type"] == "unique":
        uid = pending["uid"]
        inv = pdata.get("inventory", {})
        item_data = inv.get(uid)
        if not item_data: await q.answer("Item não encontrado.", show_alert=True); return
        del inv[uid]
        await player_manager.save_player_data(user_id, pdata)
        item_payload = {"type": "unique", "item": item_data, "uid": uid}

    market_manager.create_listing(seller_id=user_id, item_payload=item_payload, unit_price=price, quantity=1)
    await q.edit_message_text(f"✅ <b>Venda Criada!</b>\nPreço: {price} ouro.", 
                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar", callback_data="market_adventurer")]]),
                              parse_mode="HTML")
    context.user_data.pop("market_pending", None)

async def market_cancel_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer("Cancelado.")
    context.user_data.pop("market_pending", None)
    await market_adventurer(update, context)

# ==============================
#  LISTAGEM E COMPRA
# ==============================
async def market_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    user_id = q.from_user.id
    listings = market_manager.list_active()
    
    if not listings:
        await _safe_edit(q, "📭 O mercado está vazio.", InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]]))
        return

    lines = ["📦 <b>Ofertas</b>\n"]
    rows = []
    for l in listings[:15]: 
        lines.append("• " + _mm_render_listing_line(l, show_price_per_unit=True))
        if int(l.get("seller_id", 0)) != user_id:
            rows.append([InlineKeyboardButton(f"Comprar #{l['id']}", callback_data=f"market_buy_{l['id']}")])
    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])
    await _safe_edit(q, "\n".join(lines), InlineKeyboardMarkup(rows))

async def market_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    buyer_id = q.from_user.id
    lid = int(q.data.replace("market_buy_", ""))
    try:
        _, cost = await market_manager.purchase_listing(buyer_id=buyer_id, listing_id=lid, quantity=1)
        await q.answer(f"✅ Compra realizada! Custo: {cost}", show_alert=True)
        await market_list(update, context)
    except Exception as e:
        await q.answer(f"Erro: {str(e)}", show_alert=True)

async def market_my(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    user_id = q.from_user.id
    listings = market_manager.list_by_seller(user_id)
    if not listings:
        await _safe_edit(q, "Sem vendas ativas.", InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]]))
        return
    lines = ["👤 <b>Minhas Vendas</b>\n"]
    rows = []
    for l in listings:
        lines.append("• " + _mm_render_listing_line(l, show_price_per_unit=True))
        rows.append([InlineKeyboardButton(f"❌ Cancelar #{l['id']}", callback_data=f"market_cancel_{l['id']}")])
    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])
    await _safe_edit(q, "\n".join(lines), InlineKeyboardMarkup(rows))

async def market_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    try:
        lid = int(q.data.replace("market_cancel_", ""))
        market_manager.delete_listing(lid)
        await q.answer("Cancelado.", show_alert=True)
        await market_my(update, context)
    except: await q.answer("Erro.", show_alert=True)

# ==============================
#  UTILS
# ==============================
async def _send_smart(query, context, chat_id, text, kb, img_key):
    try: await query.delete_message(); 
    except: pass
    fd = file_ids.get_file_data(img_key)
    if fd and fd.get("id"):
        try:
            if fd.get("type") == "video":
                await context.bot.send_video(chat_id, fd["id"], caption=text, reply_markup=kb, parse_mode="HTML")
            else:
                await context.bot.send_photo(chat_id, fd["id"], caption=text, reply_markup=kb, parse_mode="HTML")
            return
        except: pass
    await context.bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")

async def _safe_edit(query, text, kb):
    try: await query.edit_message_caption(caption=text, reply_markup=kb, parse_mode='HTML')
    except: 
        try: await query.edit_message_text(text=text, reply_markup=kb, parse_mode='HTML')
        except: pass

# ==============================
#  EXPORTS
# ==============================
market_open_handler = CallbackQueryHandler(market_open, pattern=r'^market$')
market_adventurer_handler = CallbackQueryHandler(market_adventurer, pattern=r'^market_adventurer$')
market_list_handler = CallbackQueryHandler(market_list, pattern=r'^market_list$')
market_buy_handler = CallbackQueryHandler(market_buy, pattern=r'^market_buy_')
market_sell_menu_handler = CallbackQueryHandler(market_sell_menu, pattern=r'^market_sell_menu$')
market_sell_cat_handler = CallbackQueryHandler(market_sell_list_category, pattern=r'^market_sell_cat:')
market_sell_legacy_handler = CallbackQueryHandler(market_sell_menu, pattern=r'^market_sell(:\d+)?$')
market_cancel_handler = CallbackQueryHandler(market_cancel, pattern=r'^market_cancel_\d+$')
market_pick_unique_handler= CallbackQueryHandler(market_pick_unique, pattern=r'^market_pick_unique_')
market_pick_stack_handler = CallbackQueryHandler(market_pick_stack, pattern=r'^market_pick_stack_')
market_pack_qty_spin_handler = CallbackQueryHandler(market_qty_spin, pattern=r'^mkt_pack_(inc|dec)_[0-9]+$')
market_pack_qty_confirm_handler = CallbackQueryHandler(market_qty_confirm, pattern=r'^mkt_pack_confirm$')
market_price_spin_handler = CallbackQueryHandler(market_price_spin,    pattern=r'^mktp_(inc|dec)_[0-9]+$')
market_price_confirm_handler = CallbackQueryHandler(market_finalize, pattern=r'^mktp_confirm$')
market_cancel_new_handler = CallbackQueryHandler(market_cancel_new, pattern=r'^market_cancel_new$')
market_lote_qty_spin_handler = CallbackQueryHandler(market_qty_spin, pattern=r'^mkt_lote_.*')
market_lote_qty_confirm_handler = CallbackQueryHandler(market_qty_confirm, pattern=r'^mkt_lote_confirm$')
market_finalize_handler = CallbackQueryHandler(market_finalize, pattern=r'^mkt_finalize$')
market_my_handler = CallbackQueryHandler(market_my, pattern=r'^market_my$')