# handlers/adventurer_market_handler.py
import logging
from typing import List, Dict, Any, Optional
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
    STAT_EMOJI = {} 

try:
    from modules.game_data.classes import CLASSES_DATA
except ImportError:
    CLASSES_DATA = {}
try:
    # Pega a lista oficial de itens de evolução para bloquear todos
    from modules.game_data.items_evolution import EVOLUTION_ITEMS_DATA
except ImportError:
    EVOLUTION_ITEMS_DATA = {}

# Tenta pegar Skins se existir
try:
    from modules.game_data.skins import SKIN_CATALOG
except ImportError:
    SKIN_CATALOG = {}

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
BLOCKED_KEYWORDS = [
    "tomo_", "livro_", "pergaminho_skill", # Skills
    "skin_", "caixa_skin", "traje_",       # Skins
    "essencia_", "emblema_", "sigilo_protecao", "ticket_arena"             # Evolução Genérica
    "ticket_", "chave_", "caixa_",                    # Premium
]
# ==============================
#  HELPERS VISUAIS (Cards & Classes)
# ==============================
def _get_item_info(base_id: str) -> dict:
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

def _rarity_to_int(rarity):
    order = {"comum": 1, "incomum": 2, "bom": 3, "raro": 4, "epico": 5, "lendario": 6, "mitico": 7, "divino": 8}
    return order.get(str(rarity).lower(), 0)

def _detect_class_display(inst: dict, base_id: str) -> str:
    raw_class = inst.get("class_lock") or inst.get("class") or inst.get("classe") or inst.get("required_class")
    
    if not raw_class:
        base_id_lower = base_id.lower()
        for c_key in CLASSES_DATA.keys():
            if c_key in base_id_lower:
                raw_class = c_key
                break

    if not raw_class or str(raw_class).lower() in ["none", "universal", "todos", "all", "any"]:
        return "🌎 Universal"

    ckey = str(raw_class).lower().strip()
    if ckey in CLASSES_DATA:
        c_info = CLASSES_DATA[ckey]
        emoji = c_info.get("emoji", "🛡️")
        name = c_info.get("display_name", ckey.capitalize())
        return f"{emoji} {name}"
    
    return f"🛡️ {ckey.capitalize()}"

def _get_stat_emoji(key: str) -> str:
    key_lower = key.lower()
    if key_lower in STAT_EMOJI: return STAT_EMOJI[key_lower]
    if "hp" in key_lower or "vida" in key_lower: return "❤️"
    if "atk" in key_lower or "dmg" in key_lower: return "⚔️"
    if "def" in key_lower: return "🛡️"
    if "int" in key_lower: return "🧠"
    if "str" in key_lower: return "💪"
    if "agi" in key_lower: return "🏃"
    if "luc" in key_lower or "sorte" in key_lower: return "🍀"
    return "✨"

def _render_listing_card(idx: int, listing: dict) -> str:
    """Renderiza um card de listagem do mercado (Compra) com detalhes."""
    icons = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    icon_num = icons[idx] if idx < len(icons) else f"{idx}️⃣"
    
    # Dados da listagem
    price = int(listing.get("unit_price", 0))
    seller_name = listing.get("seller_name", "Desconhecido")
    item_payload = listing.get("item", {})
    
    # Cabeçalho do Card
    if item_payload.get("type") == "stack":
        base_id = item_payload.get("base_id")
        qty = item_payload.get("qty", 1)
        info = _get_item_info(base_id)
        name = info.get("display_name") or base_id.replace("_", " ").title()
        emoji = info.get("emoji", "📦")
        
        return (
            f"{icon_num}┈➤ {emoji} <b>{name}</b> (x{qty})\n"
            f" ├┈➤ 💰 Preço: <b>{price:,} Ouro</b>\n"
            f" ╰┈➤ 👤 Vendedor: {seller_name}"
        )
        
    else: # Item Único (Equipamento)
        inst = item_payload.get("item", {})
        base_id = item_payload.get("base_id") or inst.get("base_id")
        info = _get_item_info(base_id)
        name = inst.get("display_name") or info.get("display_name") or base_id
        emoji = inst.get("emoji") or info.get("emoji") or "⚔️"
        rarity = str(inst.get("rarity", "comum")).upper()
        
        # Durabilidade e Upgrade
        cur_d, max_d = inst.get("durability", [20, 20]) if isinstance(inst.get("durability"), list) else [20,20]
        upg = inst.get("upgrade_level", 0)
        plus_str = f" +{upg}" if upg > 0 else ""
        
        # Atributos
        stats_found = []
        all_stats = {}
        if isinstance(inst.get("attributes"), dict): all_stats.update(inst["attributes"])
        if isinstance(inst.get("enchantments"), dict): all_stats.update(inst["enchantments"])
        
        for key, raw_val in all_stats.items():
            val = raw_val.get("value", 0) if isinstance(raw_val, dict) else raw_val
            try: 
                if int(float(val)) > 0:
                    icon = _get_stat_emoji(key)
                    stats_found.append(f"{icon}+{int(val)}")
            except: continue
            
        stats_str = ", ".join(stats_found[:4]) if stats_found else "Sem atributos"
        class_str = _detect_class_display(inst, base_id)

        return (
            f"{icon_num}┈➤{emoji} <b>{name}{plus_str}</b> [{rarity}]\n"
            f" ├┈➤ {stats_str}\n"
            f" ├┈➤ {class_str} | ⚒️ [{int(cur_d)}/{int(max_d)}]\n"
            f" ╰┈➤ 💰 <b>{price:,} Ouro</b>"
        )
    
def _render_item_card(idx: int, item_wrapper: dict) -> str:
    """Gera o texto visual bonito para a lista (Estilo Card RPG)."""
    icons = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    icon_num = icons[idx] if idx < len(icons) else f"{idx}️⃣"
    
    if item_wrapper["type"] == "stack":
        base_id = item_wrapper["base_id"]
        qty = item_wrapper["qty"]
        info = _get_item_info(base_id)
        name = info.get("display_name") or base_id.replace("_", " ").title()
        emoji = info.get("emoji", "📦")
        return f"{icon_num}┈➤ {emoji} <b>{name}</b>\n ╰┈➤ 📦 Quantidade: {qty} un."
    
    else: # Unique
        inst = item_wrapper["inst"]
        base_id = item_wrapper["sort_name"]
        info = _get_item_info(base_id)
        name = inst.get("display_name") or info.get("display_name") or base_id
        emoji = inst.get("emoji") or info.get("emoji") or "⚔️"
        rarity = str(inst.get("rarity", "comum")).upper()
        
        cur_d, max_d = inst.get("durability", [20, 20]) if isinstance(inst.get("durability"), list) else [20,20]
        dura_str = f"[{int(cur_d)}/{int(max_d)}]"
        upg = inst.get("upgrade_level", 0)
        plus_str = f" +{upg}" if upg > 0 else ""

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
        class_str = _detect_class_display(inst, base_id)

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
        [InlineKeyboardButton("➕ Vender Item", callback_data="market_sell_menu")], 
        [InlineKeyboardButton("👤 Minhas Vendas", callback_data="market_my")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market")]
    ])
    await _send_smart(query, context, update.effective_chat.id, text, kb, "mercado_aventureiro")

# ==============================
#  LISTAGEM DE COMPRA (CORRIGIDO)
# ==============================
async def market_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    
    # Tenta pegar a página da callback_data (ex: market_list:2)
    try: 
        page = int(q.data.split(":")[1])
    except: 
        page = 1

    # 1. Dados do jogador (para mostrar o saldo)
    pdata = await player_manager.get_player_data(user_id) or {}
    gold = pdata.get("gold", 0)

    # 2. Carrega listagens
    try:
        all_listings = market_manager.list_active()
    except:
        all_listings = []
    
    # 3. Paginação
    ITEMS_PER_PAGE = 5
    total = len(all_listings)
    total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    page = max(1, min(page, total_pages))
    
    start = (page - 1) * ITEMS_PER_PAGE
    listings_page = all_listings[start : start + ITEMS_PER_PAGE]

    # 4. Monta o Texto
    header = (
        f"╭┈┈┈➤ 🏪 <b>MERCADO GLOBAL ({page}/{total_pages})</b>\n"
        f" │ 💰 <b>Seu Saldo:</b> {gold:,} 🪙\n"
        f"╰┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤\n\n"
    )

    body_lines = []
    selection_buttons = []

    if not all_listings:
        body_lines.append("📭 <i>O mercado está vazio no momento.</i>")
    elif not listings_page:
        body_lines.append("<i>Página vazia.</i>")
    else:
        for idx, listing in enumerate(listings_page, start=1):
            # Renderiza o Card
            card_text = _render_listing_card(idx, listing)
            body_lines.append(card_text)
            body_lines.append("") # Espaço
            
            # Botão de Compra (Se não for o próprio dono)
            seller_id = int(listing.get("seller_id", 0))
            lid = listing.get("id")
            
            if seller_id != user_id:
                selection_buttons.append(
                    InlineKeyboardButton(f"{idx} 🛒", callback_data=f"market_buy_{lid}")
                )
            else:
                # Se for item do próprio user, botão desativado ou diferente
                selection_buttons.append(
                    InlineKeyboardButton(f"{idx} 👤", callback_data="noop")
                )

    full_text = header + "\n".join(body_lines)

    # 5. Monta o Teclado
    keyboard = []
    if selection_buttons:
        keyboard.append(selection_buttons) # Botões 1🛒 2🛒 na mesma linha

    # Navegação
    nav_row = []
    if page > 1: 
        nav_row.append(InlineKeyboardButton("⬅️ Ant.", callback_data=f"market_list:{page-1}"))
    
    nav_row.append(InlineKeyboardButton("🔄 Atualizar", callback_data=f"market_list:{page}"))
    
    if page < total_pages: 
        nav_row.append(InlineKeyboardButton("Prox. ➡️", callback_data=f"market_list:{page+1}"))
    
    if nav_row: keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="market_adventurer")])

    await _safe_edit(q, full_text, InlineKeyboardMarkup(keyboard))

async def market_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    # Não usamos await q.answer() aqui ainda, pois pode demorar
    buyer_id = q.from_user.id
    
    try:
        lid = int(q.data.replace("market_buy_", ""))
    except:
        await q.answer("ID inválido.", show_alert=True)
        return

    try:
        # Tenta comprar. Nota: removemos 'await' caso o market_manager seja síncrono.
        # Se for assíncrono, o try/except captura e tentamos com await.
        try:
            # Tentativa Síncrona (Padrão do projeto em modules)
            listing, cost = market_manager.purchase_listing(buyer_id=buyer_id, listing_id=lid, quantity=1)
        except TypeError:
            # Se falhar dizendo que é coroutine, usa await
            listing, cost = await market_manager.purchase_listing(buyer_id=buyer_id, listing_id=lid, quantity=1)
            
        await q.answer(f"✅ Compra realizada! Custo: {cost} ouro", show_alert=True)
        await market_list(update, context)
        
    except ValueError as ve:
        # Erro de lógica (saldo insuficiente, item vendido)
        await q.answer(f"❌ {str(ve)}", show_alert=True)
        await market_list(update, context) # Recarrega para sumir o item se foi vendido
    except Exception as e:
        logger.error(f"Erro na compra: {e}")
        await q.answer(f"Erro: {str(e)}", show_alert=True)

# ==============================
#  VENDA (AQUI MANTEMOS O VISUAL BONITO)
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
        # Normaliza dados do item
        if isinstance(data, dict): # Item Único (Equipamento)
            base_id = data.get("base_id") or data.get("tpl") or item_id
            qty = data.get("qty", 0) or 1
            is_unique = True
            inst_data = data
        else: # Stack (Material)
            base_id = item_id
            qty = int(data)
            is_unique = False
            inst_data = {}

        # Carrega informações completas do item (Game Data)
        info = _get_item_info(base_id)
        bid_str = str(base_id).lower()

        # ========================================================
        # 🛡️ BLOQUEIO DE SEGURANÇA (FILTRO RIGOROSO)
        # ========================================================
        
        # 1. Bloqueio Dinâmico de Evolução (Pega tudo do arquivo items_evolution.py)
        if base_id in EVOLUTION_ITEMS_DATA:
            continue

        # 2. Bloqueio por Propriedades do Item (Configurado nos arquivos .py)
        # Se o item tiver "tradable": False ou for moeda premium
        if info.get("tradable") is False: 
            continue
        if info.get("market_currency") in ["gems", "gemas", "premium"]:
            continue
        if info.get("type") in ["divino", "especial", "currency"]:
            continue

        # 3. Bloqueio por Palavras-Chave (Segurança extra para nomes)
        # Bloqueia Skins, Skills (Tomos/Livros/Pergaminhos), Chaves, Tickets
        blocked_keywords = [
            "skin_", "traje_", "visual_", "caixa_skin", # Skins
            "tomo_", "livro_", "pergaminho_", "grimorio", # Skills
            "chave_", "ticket_", "passe_", # Acesso
            "emblema_", "essencia_", "fragmento_", # Evolução Genérica
            "gems", "gemas", "diamante" # Moedas
        ]
        if any(k in bid_str for k in blocked_keywords):
            continue
            
        # 4. Bloqueio de Skins (Pelo catálogo de skins)
        if base_id in SKIN_CATALOG:
            continue

        # ========================================================
        # FIM DO BLOQUEIO
        # ========================================================

        # Verifica Categoria para Exibição
        itype = str(info.get("type", "")).lower()
        should_show = False

        if category == "equip" and (is_unique or itype in ["equipamento", "arma", "armadura", "acessorio"]):
            should_show = True
        elif category == "cons" and (not is_unique and itype in ["consumivel", "consumable", "potion", "food", "reagent"]):
            should_show = True
        elif category == "mat" and (not is_unique and itype not in ["consumivel", "potion", "equipamento", "arma", "armadura"]):
            # Materiais gerais caem aqui
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

    # 4. Renderização
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
        if category == "mat":
             body_lines.append("\nℹ️ <i>Itens Raros, Skins e Evoluções devem ser vendidos no Leilão de Gemas.</i>")
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
    if not pending:
        await q.answer("Sessão expirada.", show_alert=True)
        return

    price = context.user_data.get("market_price", 50)
    pdata = await player_manager.get_player_data(user_id)
    
    # 1. Processa a remoção do item do inventário
    if pending["type"] == "stack":
        base_id = pending["base_id"]
        qty = pending["qty"]
        if not player_manager.remove_item_from_inventory(pdata, base_id, qty):
            await q.answer("Erro: Item insuficiente.", show_alert=True)
            return
        item_payload = {"type": "stack", "base_id": base_id, "qty": qty}
        
    elif pending["type"] == "unique":
        uid = pending["uid"]
        inv = pdata.get("inventory", {})
        item_data = inv.get(uid)
        if not item_data:
            await q.answer("Item não encontrado.", show_alert=True)
            return
        del inv[uid] # Remove item único
        await player_manager.save_player_data(user_id, pdata)
        item_payload = {"type": "unique", "item": item_data, "uid": uid}

    # 2. Cria a listagem no banco de dados
    market_manager.create_listing(seller_id=user_id, item_payload=item_payload, unit_price=price, quantity=1)
    
    # 3. Limpa sessão
    context.user_data.pop("market_pending", None)
    
    # 4. Feedback Visual (CORRIGIDO: Usa _safe_edit para evitar erro em mensagens com foto)
    msg_text = f"✅ <b>Venda Criada!</b>\n\n💰 Preço definido: <b>{price} ouro</b>."
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar ao Mercado", callback_data="market_adventurer")]])
    
    await _safe_edit(q, msg_text, kb)

async def market_cancel_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer("Cancelado.")
    context.user_data.pop("market_pending", None)
    await market_adventurer(update, context)

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
# Permite "market_list" ou "market_list:2"
market_list_handler = CallbackQueryHandler(market_list, pattern=r'^market_list(:?\d+)?$')
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