# handlers/adventurer_market_handler.py
import logging
from typing import List, Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters

# --- MÓDULOS PRINCIPAIS ---
from modules import player_manager, game_data, file_ids, market_manager
from modules.market_manager import render_listing_line as _mm_render_listing_line
from modules import market_utils
from modules.player import queries

# --- DADOS DE JOGO PARA FILTROS PRECISOS ---
try:
    from modules.game_data.items_evolution import EVOLUTION_ITEMS_DATA
except ImportError:
    EVOLUTION_ITEMS_DATA = {}

try:
    from modules.game_data.items_consumables import CONSUMABLES_DATA
except ImportError:
    CONSUMABLES_DATA = {}

try:
    from modules.game_data.attributes import STAT_EMOJI
except ImportError:
    STAT_EMOJI = {} 

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
#  HELPERS VISUAIS
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
    """Renderiza um card de listagem do mercado com indicador de PRIVADO."""
    icons = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    icon_num = icons[idx] if idx < len(icons) else f"{idx}️⃣"
    
    price = int(listing.get("unit_price", 0))
    seller_name = listing.get("seller_name") or f"Vendedor {listing.get('seller_id')}"
    item_payload = listing.get("item", {})
    
    # --- LÓGICA DE IDENTIFICAÇÃO PRIVADA ---
    tid = listing.get("target_buyer_id") or listing.get("target_id")
    tname = listing.get("target_buyer_name") or listing.get("target_name") or "Alguém"
    
    # Se tiver ID de destino, define os visuais
    if tid:
        # Adiciona cadeado no início e linha de reserva
        lock_emoji = "🔒 " 
        lock_status = f"🔐 <b>Reservado:</b> {tname}"
    else:
        lock_emoji = ""
        lock_status = ""
    # ---------------------------------------

    if item_payload.get("type") == "stack":
        base_id = item_payload.get("base_id")
        qty = item_payload.get("qty", 1)
        info = _get_item_info(base_id)
        name = info.get("display_name") or base_id.replace("_", " ").title()
        emoji = info.get("emoji", "📦")
        
        # Linha final condicional (com ou sem reserva)
        footer = f"╰┈➤ 💸 <b>{price:,} 🪙</b>  👤 {seller_name}"
        if lock_status:
            footer += f"\n╰┈➤ {lock_status}"

        return (
            f"{icon_num}┈➤ {lock_emoji}{emoji} <b>{name}</b> x{qty}\n"
            f"├┈➤ 📦 Lote de {qty} un.\n"
            f"{footer}"
        )
        
    else: # Unique
        inst = item_payload.get("item", {})
        base_id = item_payload.get("base_id") or inst.get("base_id")
        info = _get_item_info(base_id)
        name = inst.get("display_name") or info.get("display_name") or base_id
        emoji = inst.get("emoji") or info.get("emoji") or "⚔️"
        rarity = str(inst.get("rarity", "comum")).upper()
        
        cur_d, max_d = inst.get("durability", [20, 20]) if isinstance(inst.get("durability"), list) else [20,20]
        dura_str = f"[{int(cur_d)}/{int(max_d)}]"
        
        # Stats
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
            
        stats_str = ", ".join(stats_found[:3]) if stats_found else "---"
        class_str = _detect_class_display(inst, base_id)

        # Linha final condicional
        footer = f"╰┈➤ 💸 <b>{price:,} 🪙</b>  👤 {seller_name}"
        if lock_status:
            footer += f"\n╰┈➤ {lock_status}"

        return (
            f"{icon_num}┈➤ {lock_emoji}{emoji} <b>{name}</b> [{rarity}] {dura_str}\n"
            f"├┈➤ {class_str} │ {stats_str}\n"
            f"{footer}"
        )

def _render_sell_card(idx: int, item_wrapper: dict) -> str:
    """Renderiza card na tela de 'Vender Item' com detalhes completos."""
    icons = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    icon_num = icons[idx] if idx < len(icons) else f"{idx}️⃣"
    
    # === TIPO STACK (Materiais/Consumíveis) ===
    if item_wrapper["type"] == "stack":
        base_id = item_wrapper["base_id"]
        qty = item_wrapper["qty"]
        info = _get_item_info(base_id)
        name = info.get("display_name") or base_id.replace("_", " ").title()
        emoji = info.get("emoji", "📦")
        
        return (
            f"{icon_num}┈➤ {emoji} <b>{name}</b>\n"
            f"╰┈➤ 📦 Lote de {qty} un."
        )

    # === TIPO UNIQUE (Equipamentos) ===
    else:
        inst = item_wrapper["inst"]
        base_id = item_wrapper["sort_name"]
        info = _get_item_info(base_id)
        
        # 1. Cabeçalho (Nome + Upgrade + Raridade)
        name = inst.get("display_name") or info.get("display_name") or base_id
        emoji = inst.get("emoji") or info.get("emoji") or "⚔️"
        rarity = str(inst.get("rarity", "comum")).upper()
        upg = inst.get("upgrade_level", 0)
        plus_str = f" +{upg}" if upg > 0 else ""
        
        # 2. Linha do Meio (Durabilidade + Atributos)
        # Durabilidade
        cur_d, max_d = inst.get("durability", [20, 20]) if isinstance(inst.get("durability"), list) else [20,20]
        dura_str = f"[{int(cur_d)}/{int(max_d)}]"
        
        # Stats
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
            
        stats_str = ", ".join(stats_found[:4]) # Mostra até 4 status
        if not stats_str: stats_str = ""

        # 3. Rodapé (Classe)
        class_str = _detect_class_display(inst, base_id)
        
        # Montagem Final
        return (
            f"{icon_num}┈➤ {emoji} <b>{name}{plus_str}</b> [{rarity}]\n"
            f"├┈➤ {dura_str} {stats_str}\n"
            f"╰┈➤ {class_str}"
        )

def _render_my_sale_card(idx: int, listing: dict) -> str:
    """Renderiza um card estilizado para a tela 'Minhas Vendas'."""
    icons = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    icon_num = icons[idx] if idx < len(icons) else f"{idx}️⃣"
    
    lid = listing.get("id")
    price = int(listing.get("unit_price", 0))
    item_payload = listing.get("item", {})
    
    # 1. Status (Público ou Privado)
    tid = listing.get("target_buyer_id") or listing.get("target_id")
    tname = listing.get("target_buyer_name") or listing.get("target_name") or "Alguém"
    
    if tid:
        status_line = f"🔐 <b>Reservado:</b> {tname}"
    else:
        status_line = "📢 <b>Público</b>"

    # 2. Dados do Item
    if item_payload.get("type") == "stack":
        base_id = item_payload.get("base_id")
        qty = item_payload.get("qty", 1)
        info = _get_item_info(base_id)
        name = info.get("display_name") or base_id.replace("_", " ").title()
        emoji = info.get("emoji", "📦")
        
        # Formatação Lote
        header = f"{emoji} <b>{name}</b> x{qty}"
        details = f"💰 {price:,} 🪙 (Lote)"
        
    else: # Unique
        inst = item_payload.get("item", {})
        base_id = item_payload.get("base_id") or inst.get("base_id")
        info = _get_item_info(base_id)
        name = inst.get("display_name") or info.get("display_name") or base_id
        emoji = inst.get("emoji") or info.get("emoji") or "⚔️"
        rarity = str(inst.get("rarity", "comum")).upper()
        upg = inst.get("upgrade_level", 0)
        plus_str = f" +{upg}" if upg > 0 else ""

        # Formatação Unique
        header = f"{emoji} <b>{name}{plus_str}</b> [{rarity}]"
        details = f"💰 {price:,} 🪙"

    # 3. Montagem da Árvore
    return (
        f"{icon_num}┈➤ {header}\n"
        f"├┈➤ {details} │ 🆔 <b>#{lid}</b>\n"
        f"╰┈➤ {status_line}"
    )

# ==============================
#  HANDLERS PRINCIPAIS
# ==============================

async def market_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    user_id = query.from_user.id

    # 1. Recupera dados para mostrar saldo atualizado
    try:
        pdata = await player_manager.get_player_data(user_id)
        gold = int(pdata.get("gold", 0))
        gems = int(pdata.get("gems", 0))
    except:
        gold = 0
        gems = 0

    # 2. Texto Imersivo com Status
    text = (
        f"🏰 <b>CENTRO COMERCIAL DE ELDORA</b>\n"
        f"╭┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤\n"
        f"│ 🌞 <b>Clima:</b> Ensolarado\n"
        f"│ 👥 <b>Movimento:</b> Intenso\n"
        f"╰┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤\n\n"
        f"<i>Você caminha pelas ruas de paralelepípedos. Mercadores gritam ofertas, ferreiros batem metal e aventureiros negociam relíquias raras.</i>\n\n"
        f"🎒 <b>SEUS RECURSOS:</b>\n"
        f"├┈➤ 💰 <b>{gold:,}</b> Ouro\n"
        f"╰┈➤ 💎 <b>{gems:,}</b> Gemas"
    )

    # 3. Botões em Grade (Lado a Lado)
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎒 𝐌𝐞𝐫𝐜𝐚𝐝𝐨 𝐀𝐯𝐞𝐧𝐭𝐮𝐫𝐞𝐢𝐫𝐨", callback_data="market_adventurer"),
            InlineKeyboardButton("🏛️ 𝐑𝐞𝐥𝐢𝐪𝐮𝐢𝐚𝐬", callback_data="gem_market_main")
        ],
        [InlineKeyboardButton("💎 𝐋𝐨𝐣𝐚 𝐏𝐫𝐞𝐦𝐢𝐮𝐦", callback_data="gem_shop")],
        [InlineKeyboardButton("⬅️ 𝑽𝒐𝒍𝒕𝒂𝒓 𝒂𝒐 𝑹𝒆𝒊𝒏𝒐", callback_data="show_kingdom_menu")]
    ])

    await _send_smart(query, context, chat_id, text, kb, "market")

async def market_adventurer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # 1. Busca o saldo atual do jogador para exibir no topo
    try:
        pdata = await player_manager.get_player_data(user_id)
        gold = int(pdata.get("gold", 0))
    except:
        gold = 0

    # 2. Texto Estilizado com Saldo
    text = (
        f"🎒 𝐌𝐄𝐑𝐂𝐀𝐃𝐎 𝐃𝐎 𝐀𝐕𝐄𝐍𝐓𝐔𝐑𝐄𝐈𝐑𝐎\n"
        f"╭┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤\n"
        f"│ 💰 𝙎𝙚𝙪 𝙎𝙖𝙡𝙙𝙤: {gold:,} 🪙\n"
        f"╰┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤\n\n"
        f"<i>O burburinho dos comerciantes preenche o ar. Aqui você pode negociar itens com outros viajantes.</i>"
    )

    # 3. Botões Organizados (Comprar e Vender lado a lado)
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛒 𝐂𝐨𝐦𝐩𝐫𝐚𝐫", callback_data="market_list"),
            InlineKeyboardButton("➕ 𝐕𝐞𝐧𝐝𝐞𝐫", callback_data="market_sell_menu")
        ],
        [InlineKeyboardButton("👤 𝐌𝐢𝐧𝐡𝐚𝐬 𝐕𝐞𝐧𝐝𝐚𝐬", callback_data="market_my")],
        [InlineKeyboardButton("⬅️ 𝑽𝒐𝒍𝒕𝒂𝒓 ", callback_data="market")]
    ])

    # Mantém a imagem se houver, ou edita o texto
    await _send_smart(query, context, update.effective_chat.id, text, kb, "mercado_aventureiro")

# ==============================
#  LISTAGEM DE COMPRA
# ==============================

async def market_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    
    try: 
        if ":" in q.data: page = int(q.data.split(":")[1])
        else: page = 1
    except: page = 1

    try:
        pdata = await player_manager.get_player_data(user_id) or {}
        gold = pdata.get("gold", 0)
        all_listings = market_manager.list_active(viewer_id=user_id)
    except Exception as e: 
        logger.error(f"Erro ao listar mercado: {e}")
        all_listings = []
    
    if not all_listings:
        await _safe_edit(q, "📭 <i>O mercado está vazio no momento.</i>", 
                         InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]]))
        return

    ITEMS_PER_PAGE = 5
    total = len(all_listings)
    total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    page = max(1, min(page, total_pages))
    
    start = (page - 1) * ITEMS_PER_PAGE
    listings_page = all_listings[start : start + ITEMS_PER_PAGE]

    header = (
        f"╭┈┈┈┈┈➤ 🛒 <b>MERCADO ({page}/{total_pages})</b> ┈┈┈┈┈╮\n"
        f" │ 💰 <b>Seu Saldo:</b> {gold:,} 🪙\n"
        f"╰┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤\n\n"
    )

    body_lines = []
    selection_buttons = []

    if not listings_page:
        body_lines.append("<i>Página vazia.</i>")
    else:
        for idx, listing in enumerate(listings_page, start=1):
            try:
                # Busca nome do vendedor se faltar
                if "seller_name" not in listing:
                    sid = listing.get("seller_id")
                    try:
                        s_data = await player_manager.get_player_data(sid)
                        s_name = s_data.get("character_name", f"Vendedor {sid}")
                        listing["seller_name"] = s_name
                    except: listing["seller_name"] = f"ID: {sid}"

                card_text = _render_listing_card(idx, listing)
                body_lines.append(card_text)
                body_lines.append("") 
                
                seller_id = int(listing.get("seller_id", 0))
                lid = listing.get("id")
                
                if seller_id != user_id:
                    selection_buttons.append(InlineKeyboardButton(f"{idx} 🛒", callback_data=f"market_buy_{lid}"))
                else:
                    selection_buttons.append(InlineKeyboardButton(f"{idx} 👤", callback_data="noop"))
            except Exception as e:
                logger.error(f"Erro ao renderizar item {idx}: {e}")

    full_text = header + "\n".join(body_lines)

    keyboard = []
    if selection_buttons: keyboard.append(selection_buttons)

    nav_row = []
    if page > 1: nav_row.append(InlineKeyboardButton("⬅️ Ant.", callback_data=f"market_list:{page-1}"))
    nav_row.append(InlineKeyboardButton("🔄 Atualizar", callback_data=f"market_list:{page}"))
    if page < total_pages: nav_row.append(InlineKeyboardButton("Prox. ➡️", callback_data=f"market_list:{page+1}"))
    
    if nav_row: keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="market_adventurer")])

    await _safe_edit(q, full_text, InlineKeyboardMarkup(keyboard))

async def market_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    buyer_id = q.from_user.id
    try: lid = int(q.data.replace("market_buy_", ""))
    except: await q.answer("ID inválido.", show_alert=True); return

    try:
        try:
            listing, cost = market_manager.purchase_listing(buyer_id=buyer_id, listing_id=lid, quantity=1)
        except TypeError:
            listing, cost = await market_manager.purchase_listing(buyer_id=buyer_id, listing_id=lid, quantity=1)
            
        await q.answer(f"✅ Compra realizada! Custo: {cost} ouro", show_alert=True)
        await market_list(update, context)
        
    except ValueError as ve:
        await q.answer(f"❌ {str(ve)}", show_alert=True)
        await market_list(update, context)
    except Exception as e:
        logger.error(f"Erro na compra: {e}")
        await q.answer(f"Erro: {str(e)}", show_alert=True)

# ==============================
#  VENDA (FILTRADA E BLINDADA)
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

    try: 
        parts = query.data.split(':')
        category = parts[1]
        page = int(parts[2]) if len(parts) > 2 else 1
    except: 
        category, page = "mat", 1

    try:
        pdata = await player_manager.get_player_data(user_id) or {}
        inv = pdata.get("inventory", {}) or {}
        gold = pdata.get("gold", 0)
        char_name = pdata.get("character_name", "Aventureiro")
    except Exception: return
    
    sellable = []
    
    # --- 🛡️ LISTA NEGRA AGRESSIVA (Sem "_" para pegar tudo) ---
    # Adicionei 'tomo', 'livro', 'skill', 'book' sem traços para bloquear qualquer variação.
    BLOCKED_KEYWORDS = [
        # Evolução e Materiais Raros
        "essencia", "fragmento", "alma", "emblema", "lamina", "lâmina",
        "poeira", "aco", "aço", "totem", "reliquia", "relíquia", "foco",
        "coracao", "coração", "selo", "calice", "cálice", "espirito", "espírito",
        "frequencia", "energia", "nevoa", "névoa", "aura", "batuta", 
        
        # Skills, Tomos e Livros (O foco do problema)
        "tomo", "livro", "pergaminho", "grimorio", "grimório", 
        "skill", "book", "habilidade", "transcendencia", "transcendência",
        
        # Cosméticos e Eventos
        "skin", "traje", "caixa", "chave", "ticket", "sigilo", "cristal", "presente",
        
        # Moedas e Recursos
        "gemas", "gems", "ouro", "gold", "xp", "experiencia"
    ]
    # ----------------------------------------------------

    for item_id, data in inv.items():
        try:
            # Normalização dos dados do item
            if isinstance(data, dict): 
                base_id = data.get("base_id") or data.get("tpl") or item_id
                qty = data.get("qty", 0) or 1
                is_unique = True
                inst_data = data
            else: 
                base_id = item_id
                qty = int(data)
                is_unique = False
                inst_data = {}

            # ================================================================
            # 🛡️ SISTEMA DE FILTRO (HÍBRIDO & AGRESSIVO)
            # ================================================================
            
            # 1. Filtro Oficial (Arquivo items_evolution.py)
            if base_id in EVOLUTION_ITEMS_DATA: 
                continue

            # 2. Filtro de Texto (Varredura no ID)
            # Converte para minúsculo e verifica se contém QUALQUER palavra proibida
            bid_lower = str(base_id).lower()
            if any(k in bid_lower for k in BLOCKED_KEYWORDS): 
                continue

            # 3. Filtro de Consumíveis Intransferíveis (Poções vinculadas)
            if base_id in CONSUMABLES_DATA:
                if CONSUMABLES_DATA[base_id].get("tradable") is False: continue

            # ================================================================
            
            info = _get_item_info(base_id)
            itype = str(info.get("type", "")).lower()
            should_show = False

            # Lógica de Categorias
            if category == "equip" and (is_unique or itype in ["equipamento", "arma", "armadura", "acessorio"]): 
                should_show = True
            elif category == "cons" and (not is_unique and itype in ["consumivel", "consumable", "potion", "food", "reagent"]): 
                should_show = True
            elif category == "mat" and (not is_unique and itype not in ["consumivel", "potion", "equipamento", "arma", "armadura"]): 
                should_show = True

            if should_show and qty > 0:
                rarity_rank = _rarity_to_int(inst_data.get("rarity", "comum")) if is_unique else 0
                sellable.append({
                    "type": "unique" if is_unique else "stack",
                    "uid": item_id, "base_id": base_id, "qty": qty, 
                    "inst": inst_data, "sort_name": base_id, "rarity_rank": rarity_rank
                })
        except Exception: 
            continue

    # Ordenação e Paginação
    sellable.sort(key=lambda x: (0 if x["type"] == "unique" else 1, -x["rarity_rank"], x["sort_name"]))

    ITEMS_PER_PAGE = 5
    total = len(sellable)
    total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    page = max(1, min(page, total_pages))
    
    start = (page - 1) * ITEMS_PER_PAGE
    items_page = sellable[start : start + ITEMS_PER_PAGE]

    cat_names = {"equip": "⚔️ Equipamentos", "cons": "🧪 Consumíveis", "mat": "🧱 Materiais"}
    cat_title = cat_names.get(category, "Itens")

    header = (
        f"╭┈┈┈➤ 🛒 <b>VENDER: {cat_title} ({page}/{total_pages})</b>\n"
        f" │ 👤 <b>{char_name}</b>\n"
        f" │ 💰 <b>Saldo:</b> {gold:,} 🪙\n"
        f"╰┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤\n\n"
    )
    
    body_lines = []
    selection_buttons = [] 

    if not sellable:
        body_lines.append("🎒 <i>Nenhum item encontrado nesta categoria.</i>")
        if category == "mat": 
            body_lines.append("\nℹ️ <i>Tomos, Essências e itens raros foram movidos para o Leilão de Gemas.</i>")
    elif not items_page:
        body_lines.append("<i>Página vazia.</i>")
    else:
        for idx, item in enumerate(items_page, start=1):
            text_block = _render_sell_card(idx, item)
            body_lines.append(text_block)
            body_lines.append("") 
            
            if item["type"] == "unique":
                cb = f"market_pick_unique_{item['uid']}"
            else:
                cb = f"market_pick_stack_{item['base_id']}"
            
            selection_buttons.append(InlineKeyboardButton(f"{idx} 🏷️", callback_data=cb))

    full_text = header + "\n".join(body_lines)

    keyboard = []
    if selection_buttons: keyboard.append(selection_buttons)

    nav_row = []
    if page > 1: nav_row.append(InlineKeyboardButton("⬅️ Ant.", callback_data=f"market_sell_cat:{category}:{page-1}"))
    nav_row.append(InlineKeyboardButton("📂 Categorias", callback_data="market_sell_menu"))
    if total > start + ITEMS_PER_PAGE: nav_row.append(InlineKeyboardButton("Prox. ➡️", callback_data=f"market_sell_cat:{category}:{page+1}"))
    
    if nav_row: keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Mercado", callback_data="market_adventurer")])

    await _safe_edit(query, full_text, InlineKeyboardMarkup(keyboard))

# ==============================
#  RESTO DO FLUXO (PREÇO/QTD/PRIVADO)
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

async def market_qty_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await _show_price_spinner(q, context)

# --- PUBLICO / PRIVADO ---

async def market_ask_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    price = context.user_data.get("market_price", 0)
    text = f"💰 <b>Preço Definido:</b> {price:,} Ouro\n\nComo deseja anunciar?"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Público", callback_data="mkt_finish_public"), InlineKeyboardButton("🔒 Privado (ID)", callback_data="mkt_ask_private")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market_sell_menu")]
    ])
    await _safe_edit(q, text, kb)

async def market_ask_private_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["market_awaiting_id"] = True
    
    # Texto alterado para pedir NOME
    text = (
        "🔒 <b>Venda Privada</b>\n\n"
        "Envie o <b>Nome do Personagem</b> (ex: <i>Aragorn</i>) ou o <b>@usuario</b> do Telegram do comprador.\n"
        "<i>Você também pode encaminhar uma mensagem dele.</i>"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]])
    await _safe_edit(q, text, kb)

async def market_finalize_listing(update: Update, context: ContextTypes.DEFAULT_TYPE, target_id=None, target_name=None):
    user_id = update.effective_user.id
    q = update.callback_query
    
    pending = context.user_data.get("market_pending")
    price = context.user_data.get("market_price")

    if not pending or not price:
        msg = "⚠️ Sessão expirada. Inicie a venda novamente."
        if q: await q.answer(msg, show_alert=True)
        else: await update.effective_message.reply_text(msg)
        return

    # Variáveis para controle de Rollback
    item_removed_successfully = False
    pdata = None
    item_payload = {}

    try:
        pdata = await player_manager.get_player_data(user_id)
        
        # --- 1. TENTA REMOVER O ITEM (Memória) ---
        if pending["type"] == "stack":
            base_id = pending["base_id"]
            qty = pending["qty"]
            if player_manager.remove_item_from_inventory(pdata, base_id, qty):
                item_payload = {"type": "stack", "base_id": base_id, "qty": qty}
                item_removed_successfully = True
            else:
                if q: await q.answer("❌ Você não possui itens suficientes.", show_alert=True)
                return

        elif pending["type"] == "unique":
            uid = pending["uid"]
            inv = pdata.get("inventory", {})
            if uid in inv:
                item_data = inv[uid]
                del inv[uid]
                item_payload = {"type": "unique", "item": item_data, "uid": uid}
                item_removed_successfully = True
            else:
                if q: await q.answer("❌ Item não encontrado.", show_alert=True)
                return

        # --- 2. SALVA A REMOÇÃO (Persistência) ---
        # Aqui o item sai da conta. Se o código parasse aqui sem criar o anúncio, seria perdido.
        await player_manager.save_player_data(user_id, pdata)

        # --- 3. CRIA O ANÚNCIO NO MERCADO ---
        market_manager.create_listing(
            seller_id=user_id, 
            item_payload=item_payload, 
            unit_price=price, 
            target_buyer_id=target_id, 
            target_buyer_name=target_name
        )
        
        # --- SUCESSO ---
        context.user_data.pop("market_pending", None)
        context.user_data.pop("market_awaiting_id", None)
        context.user_data.pop("market_price", None)
        
        msg_text = f"✅ <b>Anúncio Criado!</b>\n💰 {price:,} Ouro"
        if target_id: msg_text += f"\n🔒 <b>Reservado para:</b> {target_name}"
        else: msg_text += "\n📢 <b>Público</b>"

        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🎒 Voltar", callback_data="market_adventurer")]])
        
        if q: await _safe_edit(q, msg_text, kb)
        else: await update.effective_message.reply_text(msg_text, reply_markup=kb, parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"ERRO CRÍTICO NA VENDA (USER {user_id}): {e}")
        
        # --- 4. SISTEMA DE SEGURANÇA (ROLLBACK) ---
        if item_removed_successfully and pdata:
            logger.warning(f"Iniciando devolução de item para {user_id} devido a erro no mercado...")
            try:
                # Devolve Stack
                if pending["type"] == "stack":
                    inv = pdata.setdefault("inventory", {})
                    base_id = pending["base_id"]
                    qty = pending["qty"]
                    inv[base_id] = int(inv.get(base_id, 0)) + qty
                
                # Devolve Unique
                elif pending["type"] == "unique":
                    uid = pending["uid"]
                    # Recupera os dados do item que estavam no payload ou no cache local
                    if "item" in item_payload:
                        pdata.setdefault("inventory", {})[uid] = item_payload["item"]
                
                # Salva a devolução
                await player_manager.save_player_data(user_id, pdata)
                
                err_msg = "⚠️ <b>Erro no Mercado!</b>\nO sistema detectou uma falha ao criar o anúncio, mas seu item foi <b>DEVOLVIDO</b> ao inventário com segurança."
            except Exception as e_rollback:
                logger.critical(f"FALHA NO ROLLBACK DO JOGADOR {user_id}: {e_rollback}")
                err_msg = "❌ <b>Erro Crítico!</b> Contate o suporte imediatamente. (Cod: ROLLBACK_FAIL)"
        else:
            err_msg = "❌ Erro ao processar. Nenhum item foi removido."

        if q: await _safe_edit(q, err_msg, InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]]))
        else: await update.effective_message.reply_text(err_msg, parse_mode="HTML")

async def market_catch_input_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Só processa se o bot estiver esperando um ID para venda privada
    if not context.user_data.get("market_awaiting_id"): 
        return

    user_id = update.effective_user.id
    target_id = None
    target_name = "Desconhecido"
    text = update.message.text.strip()

    try:
        # 1. Tenta pegar ID de encaminhamento
        if update.message.forward_from:
            target_id = update.message.forward_from.id
            target_name = update.message.forward_from.first_name
        
        # 2. Se for número direto (ID)
        elif text.isdigit():
            target_id = int(text)
            # Tenta achar o nome só pra ficar bonito
            try:
                pdata = await player_manager.get_player_data(target_id)
                if pdata: target_name = pdata.get("character_name", "Jogador")
            except: pass

        # 3. Se for Texto (Nome ou @Username) - AQUI ESTÁ A CORREÇÃO
        else:
            pdata = None
            # Tenta por username
            if text.startswith("@"):
                from modules.player import queries
                pdata = await queries.find_by_username(text)
            # Tenta por nome do personagem
            else:
                from modules.player import queries
                res = await queries.find_player_by_name(text)
                if not res:
                    res = await queries.find_player_by_name_norm(text)
                if res:
                    target_id, pdata = res

            if pdata:
                target_id = pdata.get("user_id") or pdata.get("_id")
                target_name = pdata.get("character_name", text)

        # Validações Finais
        if not target_id:
            await update.message.reply_text("❌ Jogador não encontrado. Verifique o nome exato ou use o ID.")
            return

        if target_id == user_id:
            await update.message.reply_text("❌ Você não pode vender para si mesmo.")
            return
        
        # Finaliza a venda
        await market_finalize_listing(update, context, target_id=target_id, target_name=target_name)

    except Exception as e:
        logger.error(f"Erro input ID: {e}")
        await update.message.reply_text("❌ Erro ao buscar jogador.")

async def market_cancel_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer("Cancelado.")
    context.user_data.pop("market_pending", None)
    await market_adventurer(update, context)

async def market_my(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    
    # Busca as vendas do jogador
    listings = market_manager.list_by_seller(user_id)
    
    if not listings:
        msg = "👤 <b>Minhas Vendas</b>\n\n<i>Você não tem itens à venda no momento.</i>"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]])
        await _safe_edit(q, msg, kb)
        return

    # Cabeçalho
    lines = ["👤 𝐌𝐢𝐧𝐡𝐚𝐬 𝐕𝐞𝐧𝐝𝐚𝐬 𝐀𝐭𝐢𝐯𝐚𝐬\n"]
    rows = []
    
    # Gera a lista com o novo visual
    for idx, l in enumerate(listings, start=1):
        # Gera o texto do card
        card_text = _render_my_sale_card(idx, l)
        lines.append(card_text)
        lines.append("") # Linha em branco para separar
        
        # Botão de Cancelar correspondente ao ID
        lid = l['id']
        rows.append([InlineKeyboardButton(f"❌ Cancelar Item #{lid}", callback_data=f"market_cancel_{lid}")])

    # Adiciona botão de voltar no final
    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])
    
    full_text = "\n".join(lines)
    await _safe_edit(q, full_text, InlineKeyboardMarkup(rows))

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
market_price_confirm_handler = CallbackQueryHandler(market_ask_type, pattern=r'^mktp_confirm$')
market_cancel_new_handler = CallbackQueryHandler(market_cancel_new, pattern=r'^market_cancel_new$')
market_lote_qty_spin_handler = CallbackQueryHandler(market_qty_spin, pattern=r'^mkt_lote_.*')
market_lote_qty_confirm_handler = CallbackQueryHandler(market_qty_confirm, pattern=r'^mkt_lote_confirm$')
market_finalize_handler = CallbackQueryHandler(market_finalize_listing, pattern=r'^mkt_finalize$')
market_my_handler = CallbackQueryHandler(market_my, pattern=r'^market_my$')
market_finish_public_handler = CallbackQueryHandler(market_finalize_listing, pattern=r'^mkt_finish_public$')
market_ask_private_handler = CallbackQueryHandler(market_ask_private_id, pattern=r'^mkt_ask_private$')
market_input_id_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, market_catch_input_id)