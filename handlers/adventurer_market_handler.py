# handlers/adventurer_market_handler.py
import logging
import asyncio
from typing import List, Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram.error import BadRequest

# --- MÓDULOS PRINCIPAIS ---
from modules import player_manager, game_data, file_ids, market_utils
from modules.market_manager import render_listing_line as _mm_render_listing_line

from modules.player import queries

# --- DADOS DE JOGO ---
try:
    from modules import market_manager
except ImportError:
    market_manager = None

try:

    from modules.game_data.items_consumables import CONSUMABLES_DATA
    from modules.game_data.attributes import STAT_EMOJI
    from modules.game_data.classes import CLASSES_DATA
except ImportError:
    EVOLUTION_ITEMS_DATA = {}
    CONSUMABLES_DATA = {}
    STAT_EMOJI = {}
    CLASSES_DATA = {}

try:
    from modules import game_data
    # Tenta importar dados, se falhar define vazios
    from modules.game_data.items_evolution import EVOLUTION_ITEMS_DATA
except ImportError:
    game_data = None
    EVOLUTION_ITEMS_DATA = {}

logger = logging.getLogger(__name__)

# Fallback
try:
    from modules import display_utils
except ImportError:
    display_utils = None



async def _refresh_ui(query, context, text, kb, img_key=None):
    """
    Função Mestra de Interface:
    - Tenta EDITAR a mídia se já existir.
    - Se falhar ou mudar o tipo, apaga e envia novo.
    """
    chat_id = query.message.chat_id
    
    # 1. Busca Mídia (Foto ou Vídeo)
    media_id = None
    media_type = "photo"
    
    if img_key and file_ids:
        fd = file_ids.get_file_data(img_key)
        if fd: 
            media_id = fd.get("id")
            media_type = fd.get("type", "photo") # 'video' ou 'photo'

    # 2. Tenta EDITAR (Para não piscar)
    try:
        # Se a mensagem atual tem mídia e queremos manter mídia
        if media_id and (query.message.photo or query.message.video):
            if media_type == "video":
                media = InputMediaVideo(media=media_id, caption=text, parse_mode="HTML")
            else:
                media = InputMediaPhoto(media=media_id, caption=text, parse_mode="HTML")
            
            await query.edit_message_media(media=media, reply_markup=kb)
            return
        
        # Se a mensagem atual é texto e queremos manter texto
        elif not media_id and query.message.text:
            await query.edit_message_text(text=text, reply_markup=kb, parse_mode="HTML")
            return

    except Exception:
        # Se falhar a edição (ex: mensagem muito antiga), ignora e vai pro reenvio
        pass

    # 3. Fallback: DELETAR E ENVIAR NOVO
    try: await query.delete_message()
    except: pass
    
    if media_id:
        if media_type == "video":
            await context.bot.send_video(chat_id=chat_id, video=media_id, caption=text, reply_markup=kb, parse_mode="HTML")
        else:
            await context.bot.send_photo(chat_id=chat_id, photo=media_id, caption=text, reply_markup=kb, parse_mode="HTML")
    else:
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=kb, parse_mode="HTML")

# ==============================
#  HELPERS VISUAIS
# ==============================
async def _send_smart(query, context, chat_id, text, kb, img_key):
    """Envia ou edita mensagem com mídia de forma segura."""
    try: await query.delete_message() # Tenta limpar msg anterior
    except: pass
    
    # Tenta pegar a imagem/video
    fd = file_ids.get_file_data(img_key) if file_ids else None
    
    if fd and fd.get("id"):
        try:
            if fd.get("type") == "video":
                await context.bot.send_video(chat_id, fd["id"], caption=text, reply_markup=kb, parse_mode="HTML")
            else:
                await context.bot.send_photo(chat_id, fd["id"], caption=text, reply_markup=kb, parse_mode="HTML")
            return
        except: pass # Se falhar midia, manda texto

    await context.bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")

def _get_item_info(base_id: str) -> dict:
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

def _get_item_name_from_context(context):
    pending = context.user_data.get("market_pending", {})
    if pending.get("type") == "stack":
        info = _get_item_info(pending["base_id"])
        return f"{info.get('emoji', '📦')} {info.get('display_name', pending['base_id'])}"
    return "⚔️ Equipamento"

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
    icons = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    icon_num = icons[idx] if idx < len(icons) else f"{idx}️⃣"
    
    price = int(listing.get("unit_price", 0))
    seller_name = listing.get("seller_name") or f"Vendedor {listing.get('seller_id')}"
    item_payload = listing.get("item", {})
    qty_stock = listing.get("quantity", 0) # Estoque de pacotes

    tid = listing.get("target_buyer_id") or listing.get("target_id")
    tname = listing.get("target_buyer_name") or listing.get("target_name") or "Alguém"
    lock_status = f"🔐 <b>Reservado:</b> {tname}" if tid else ""
    lock_emoji = "🔒 " if tid else ""

    if item_payload.get("type") == "stack":
        base_id = item_payload.get("base_id")
        
        # Tamanho do lote definido na criação
        lot_size = item_payload.get("qty", 1)
        
        info = _get_item_info(base_id)
        name = info.get("display_name") or base_id.replace("_", " ").title()
        emoji = info.get("emoji", "📦")
        
        footer = f"╰┈➤ 💸 <b>{price:,} 🪙</b>  👤 {seller_name}"
        if lock_status: footer += f"\n╰┈➤ {lock_status}"

        # Exibe: Ferro x100 (Estoque: 5 lotes)
        return (
            f"{icon_num}┈➤ {lock_emoji}{emoji} <b>{name}</b> x{lot_size}\n"
            f"├┈➤ 📦 Estoque: {qty_stock} lotes\n"
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

    else:
        inst = item_wrapper["inst"]
        base_id = item_wrapper["sort_name"]
        info = _get_item_info(base_id)
        
        name = inst.get("display_name") or info.get("display_name") or base_id
        emoji = inst.get("emoji") or info.get("emoji") or "⚔️"
        rarity = str(inst.get("rarity", "comum")).upper()
        upg = inst.get("upgrade_level", 0)
        plus_str = f" +{upg}" if upg > 0 else ""
        
        cur_d, max_d = inst.get("durability", [20, 20]) if isinstance(inst.get("durability"), list) else [20,20]
        dura_str = f"[{int(cur_d)}/{int(max_d)}]"
        
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
            
        stats_str = ", ".join(stats_found[:4]) 
        if not stats_str: stats_str = ""

        class_str = _detect_class_display(inst, base_id)
        
        return (
            f"{icon_num}┈➤ {emoji} <b>{name}{plus_str}</b> [{rarity}]\n"
            f"├┈➤ {dura_str} {stats_str}\n"
            f"╰┈➤ {class_str}"
        )

def _render_my_sale_card(idx: int, listing: dict) -> str:
    icons = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    icon_num = icons[idx] if idx < len(icons) else f"{idx}️⃣"
    lid = listing.get("id")
    price = int(listing.get("unit_price", 0))
    item_payload = listing.get("item", {})
    qty_stock = listing.get("quantity", 0)

    # --- LÓGICA DE PRIVADO ADICIONADA AQUI ---
    target_id = listing.get("target_buyer_id")
    target_name = listing.get("target_buyer_name") or "Alguém"
    
    status_icon = "🔐" if target_id else "📢"
    status_text = f"Reservado: {target_name}" if target_id else "Público"
    # -----------------------------------------

    if item_payload.get("type") == "stack":
        base_id = item_payload.get("base_id")
        lot_size = item_payload.get("qty", 1)
        info = _get_item_info(base_id)
        name = info.get("display_name") or base_id
        emoji = info.get("emoji", "📦")
        
        header = f"{emoji} <b>{name}</b> (Lote de {lot_size})"
        details = f"💰 {price:,} 🪙 | Restam: {qty_stock} lotes"
    else:
        header = "⚔️ Item Único"
        details = f"💰 {price:,} 🪙"

    return (
        f"{icon_num}┈➤ {header}\n"
        f"├┈➤ {details} │ 🆔 <b>#{lid}</b>\n"
        f"╰┈➤ {status_icon} <b>{status_text}</b>"
    )

# ==============================
#  HANDLERS PRINCIPAIS
# ==============================

async def market_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Abre o menu principal do Centro Comercial."""
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    user_id = query.from_user.id

    try:
        pdata = await player_manager.get_player_data(user_id)
        gold = int(pdata.get("gold", 0))
        gems = int(pdata.get("gems", 0))
    except:
        gold, gems = 0, 0

    text = (
        f"🏰 <b>CENTRO COMERCIAL DE ELDORA</b>\n"
        f"╭┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤\n"
        f"│ 🎒 <b>SEUS RECURSOS:</b>\n"
        f"│ 💰 <b>{gold:,}</b> Ouro\n"
        f"│ 💎 <b>{gems:,}</b> Gemas\n"
        f"╰┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤\n\n"
        f"<i>Mercadores gritam ofertas e aventureiros negociam itens raros.</i>"
    )

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎒 𝐌𝐞𝐫𝐜𝐚𝐝𝐨 𝐀𝐯𝐞𝐧𝐭𝐮𝐫𝐞𝐢𝐫𝐨", callback_data="market_adventurer"),
            InlineKeyboardButton("🏛️ 𝐑𝐞𝐥𝐢𝐪𝐮𝐢𝐚𝐬", callback_data="gem_market_main")
        ],
        [InlineKeyboardButton("💎 𝐋𝐨𝐣𝐚 𝐏𝐫𝐞𝐦𝐢𝐮𝐦", callback_data="gem_shop")],
        [InlineKeyboardButton("⬅️ 𝑽𝒐𝒍𝒕𝒂𝒓 𝒂𝒐 𝑹𝒆𝒊𝒏𝒐", callback_data="show_kingdom_menu")]
    ])

    # Chama o helper restaurado acima
    await _send_smart(query, context, chat_id, text, kb, "market")

async def market_adventurer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        pdata = await player_manager.get_player_data(user_id)
        gold = int(pdata.get("gold", 0))
    except:
        gold = 0

    text = (
        f"🎒 𝐌𝐄𝐑𝐂𝐀𝐃𝐎 𝐃𝐎 𝐀𝐕𝐄𝐍𝐓𝐔𝐑𝐄𝐈𝐑𝐎\n"
        f"╭┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤\n"
        f"│ 💰 𝙎𝙚𝙪 𝙎𝙖𝙡𝙙𝙤: {gold:,} 🪙\n"
        f"╰┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤\n\n"
        f"<i>O burburinho dos comerciantes preenche o ar. Aqui você pode negociar itens com outros viajantes.</i>"
    )

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛒 𝐂𝐨𝐦𝐩𝐫𝐚𝐫", callback_data="market_list"),
            InlineKeyboardButton("➕ 𝐕𝐞𝐧𝐝𝐞𝐫", callback_data="market_sell_menu")
        ],
        [InlineKeyboardButton("👤 𝐌𝐢𝐧𝐡𝐚𝐬 𝐕𝐞𝐧𝐝𝐚𝐬", callback_data="market_my")],
        [InlineKeyboardButton("⬅️ 𝑽𝒐𝒍𝒕𝒂𝒓 ", callback_data="market")]
    ])

    await _send_smart(query, context, update.effective_chat.id, text, kb, "mercado_aventureiro")

# ==============================
#  LISTAGEM DE COMPRA
# ==============================

async def market_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id # Necessário para o _send_smart
    
    # --- IMPORT SEGURO AQUI ---
    from modules import market_manager
    
    try: 
        if ":" in q.data: page = int(q.data.split(":")[1])
        else: page = 1
    except: page = 1

    try:
        pdata = await player_manager.get_player_data(user_id) or {}
        gold = pdata.get("gold", 0)
        # Agora usa a importação local garantida
        all_listings = market_manager.list_active(viewer_id=user_id)
    except Exception as e: 
        logger.error(f"Erro ao listar mercado: {e}")
        all_listings = []
    
    # Se vazio, usa _send_smart também para manter consistência visual (opcional)
    if not all_listings:
        # Usa a imagem do mercado mesmo vazio, para ficar bonito
        text_vazio = "📭 <b>O Mercado está vazio no momento.</b>\n\nSeja o primeiro a vender algo!"
        kb_vazio = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]])
        
        await _send_smart(q, context, chat_id, text_vazio, kb_vazio, "mercado_aventureiro")
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
    
    # O botão atualizar agora recarregará a imagem
    nav_row.append(InlineKeyboardButton("🔄 Atualizar", callback_data=f"market_list:{page}"))
    
    if page < total_pages: nav_row.append(InlineKeyboardButton("Prox. ➡️", callback_data=f"market_list:{page+1}"))
    
    if nav_row: keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="market_adventurer")])

    # ====================================================================
    await _send_smart(q, context, chat_id, full_text, InlineKeyboardMarkup(keyboard), "mercado_aventureiro")

async def market_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    buyer_id = q.from_user.id
    
    # --- IMPORT SEGURO ---
    from modules import market_manager

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
    
    # LISTA DE BLOQUEIO (Materiais Raros)
    BLOCKED_KEYWORDS = [
        "essencia", "fragmento", "alma", "emblema", "lamina", "lâmina",
        "poeira", "aco", "aço", "totem", "reliquia", "relíquia", "foco",
        "coracao", "coração", "selo", "calice", "cálice", "espirito", "espírito",
        "frequencia", "energia", "nevoa", "névoa", "aura", 
        "tomo", "livro", "pergaminho", "grimorio", "grimório", 
        "skill", "book", "habilidade", "transcendencia", "transcendência",
        "skin", "traje", "caixa", "chave", "ticket", "sigilo", "cristal", "batuta",
        "gemas", "gems", "ouro", "gold", "xp", "experiencia"
    ]
    
    for item_id, data in inv.items():
        try:
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

            info = _get_item_info(base_id)
            itype = str(info.get("type", "")).lower()
            
            is_equipment_type = (is_unique or itype in ["equipamento", "arma", "armadura", "acessorio", "equipment", "weapon", "armor"])

            if base_id in EVOLUTION_ITEMS_DATA: 
                continue

            if not is_equipment_type:
                bid_lower = str(base_id).lower()
                if any(k in bid_lower for k in BLOCKED_KEYWORDS): 
                    continue

            if base_id in CONSUMABLES_DATA:
                if CONSUMABLES_DATA[base_id].get("tradable") is False: continue

            should_show = False

            if category == "equip" and is_equipment_type: 
                should_show = True
            elif category == "cons" and (not is_unique and itype in ["consumivel", "consumable", "potion", "food", "reagent"]): 
                should_show = True
            elif category == "mat" and (not is_unique and not is_equipment_type and itype not in ["consumivel", "potion", "food", "reagent"]): 
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
            body_lines.append("\nℹ️ <i>Materiais raros de evolução devem ser negociados por Gemas.</i>")
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
#  LÓGICA DE VENDA (PREÇO/QTD/PRIVADO) - ATUALIZADA
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

    # Inicializa: Lote de 1, Estoque de 1
    context.user_data["market_pending"] = {
        "type": "stack", 
        "base_id": base_id, 
        "qty_have": qty_have, 
        "lot_size": 1, 
        "qty": 1  # Este 'qty' agora representa o ESTOQUE (Número de lotes)
    }
    context.user_data["market_price"] = 50 
    
    # 1º Passo: Definir Tamanho do Lote
    await _show_lot_size_spinner(q, context)

async def market_pick_unique(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    unique_id = q.data.replace("market_pick_unique_", "")
    context.user_data["market_pending"] = {"type": "unique", "uid": unique_id, "qty": 1, "lot_size": 1}
    context.user_data["market_price"] = 500 
    await _show_price_spinner(q, context)

async def _show_lot_size_spinner(q, context):
    pending = context.user_data.get("market_pending")
    lot_size = pending["lot_size"]
    max_avail = pending["qty_have"]
    item_name = _get_item_name_from_context(context)
    
    # Calcula quantos lotes seriam possíveis com esse tamanho
    possible_stock = max_avail // lot_size

    text = (
        f"📦 <b>TAMANHO DO LOTE</b>\n"
        f"Item: {item_name}\n"
        f"Total na Mochila: {max_avail}\n\n"
        f"🔢 <b>Itens por Pacote:</b> {lot_size}\n"
        f"<i>(Isso criaria no máximo {possible_stock} pacotes)</i>"
    )

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("-10", callback_data="mkt_size_dec_10"),
            InlineKeyboardButton("-1", callback_data="mkt_size_dec_1"),
            InlineKeyboardButton(f"{lot_size}", callback_data="noop"),
            InlineKeyboardButton("+1", callback_data="mkt_size_inc_1"),
            InlineKeyboardButton("+10", callback_data="mkt_size_inc_10")
        ],
        [
            InlineKeyboardButton("🚀 Tudo em 1 Lote", callback_data="mkt_size_max"),
            InlineKeyboardButton("⌨️ Digitar", callback_data="mkt_input_size_start")
        ],
        [
            InlineKeyboardButton("✅ Confirmar Tamanho", callback_data="mkt_size_confirm"),
            InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")
        ]
    ])
    
    await _safe_edit(q, text, kb)

async def market_lot_size_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Avança para o passo 2: Estoque
    q = update.callback_query
    if q: await q.answer()
    
    pending = context.user_data.get("market_pending")
    lot_size = pending["lot_size"]
    max_avail = pending["qty_have"]
    
    max_stock = max_avail // lot_size
    if max_stock < 1:
        # Se editou texto e colocou valor inválido
        if q: await q.edit_message_caption("⚠️ Tamanho de lote maior que inventário!")
        return

    # Reseta o estoque para 1 (ou max se for menor que 1, mas já checamos)
    pending["qty"] = 1 
    await _show_stock_spinner(q or update.message, context)

async def _show_stock_spinner(q, context):
    pending = context.user_data.get("market_pending")
    stock = pending["qty"] # Aqui 'qty' significa QUANTIDADE DE LOTES
    lot_size = pending["lot_size"]
    max_avail = pending["qty_have"]
    
    max_stock = max_avail // lot_size
    total_items_selling = stock * lot_size
    
    text = (
        f"📊 <b>DEFINIR ESTOQUE</b>\n"
        f"📦 Lote: {lot_size} itens\n\n"
        f"🔢 <b>Quantos Lotes vender?</b> {stock}\n"
        f"<i>Total de itens a vender: {total_items_selling} / {max_avail}</i>"
    )

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("-10", callback_data="mkt_pack_dec_10"),
            InlineKeyboardButton("-1", callback_data="mkt_pack_dec_1"),
            InlineKeyboardButton(f"{stock}", callback_data="noop"),
            InlineKeyboardButton("+1", callback_data="mkt_pack_inc_1"),
            InlineKeyboardButton("+10", callback_data="mkt_pack_inc_10")
        ],
        [
            InlineKeyboardButton("🚀 Vender Todos os Lotes", callback_data="mkt_pack_max"),
            InlineKeyboardButton("✅ Confirmar Estoque", callback_data="mkt_pack_confirm")
        ],
        [InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]
    ])
    
    await _safe_edit(q, text, kb)

async def market_lot_size_spin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    pending = context.user_data.get("market_pending")
    if not pending: return
    
    action = q.data
    cur = pending["lot_size"]
    max_avail = pending["qty_have"]
    
    if "max" in action:
        cur = max_avail
    else:
        try: delta = int(action.split("_")[-1])
        except: delta = 1
        
        if "inc" in action: cur += delta
        elif "dec" in action: cur -= delta
    
    if cur < 1: cur = 1
    if cur > max_avail: cur = max_avail
    
    pending["lot_size"] = cur
    await _show_lot_size_spinner(q, context)

# --- SPINNERS E HELPERS (ATUALIZADOS) ---

async def _show_qty_spinner(q, context):
    pending = context.user_data.get("market_pending")
    cur = pending["qty"]
    max_q = pending.get("qty_have", 1) # Mostra quanto tem na mochila
    
    text = (
        f"⚖️ <b>QUANTIDADE</b>\n"
        f"🎒 Disponível: {max_q}\n\n"
        f"📦 <b>Vender:</b> {cur}"
    )

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("-10", callback_data="mkt_pack_dec_10"), 
            InlineKeyboardButton("-1", callback_data="mkt_pack_dec_1"),
            InlineKeyboardButton(f"{cur}", callback_data="noop"),
            InlineKeyboardButton("+1", callback_data="mkt_pack_inc_1"),
            InlineKeyboardButton("+10", callback_data="mkt_pack_inc_10")
        ],
        [
            InlineKeyboardButton("⌨️ Digitar", callback_data="mkt_input_qty_start"),
            InlineKeyboardButton("✅ Confirmar", callback_data="mkt_pack_confirm")
        ],
        [InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]
    ])
    await _safe_edit(q, text, kb)

async def _show_price_spinner(q, context):
    cur = context.user_data.get("market_price", 50)
    qty = context.user_data.get("market_pending", {}).get("qty", 1)
    total = cur * qty

    # --- CORREÇÃO 2: CLAREZA NO PREÇO ---
    # Deixamos claro que o input é UNITÁRIO e mostramos o total calculado
    text = (
        f"💰 <b>DEFINIR PREÇO</b>\n"
        f"📦 Quantidade: {qty}\n\n"
        f"🏷️ <b>Preço por Unidade:</b> {cur:,} 🪙\n"
        f"💵 <b>Valor Total da Venda:</b> {total:,} 🪙\n"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("-1000", callback_data="mktp_dec_1000"), InlineKeyboardButton("-100", callback_data="mktp_dec_100")],
        [InlineKeyboardButton(f"Unid: {cur}", callback_data="noop")],
        [InlineKeyboardButton("+100", callback_data="mktp_inc_100"), InlineKeyboardButton("+1000", callback_data="mktp_inc_1000")],
        [InlineKeyboardButton("⌨️ Digitar Valor Unitário", callback_data="mkt_input_price_start")],
        [InlineKeyboardButton("✅ Confirmar", callback_data="mktp_confirm"), InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]
    ])
    
    await _safe_edit(q, text, kb)

# --- HANDLERS DE AÇÃO ---

async def market_qty_spin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Lógica de spin para o ESTOQUE
    q = update.callback_query; await q.answer()
    pending = context.user_data.get("market_pending")
    
    action = q.data
    cur = pending["qty"] # Estoque
    lot_size = pending["lot_size"]
    max_avail = pending["qty_have"]
    max_stock = max_avail // lot_size
    
    if "max" in action:
        cur = max_stock
    else:
        try: delta = int(action.split("_")[-1])
        except: delta = 1
        if "inc" in action: cur += delta
        elif "dec" in action: cur -= delta
    
    if cur < 1: cur = 1
    if cur > max_stock: cur = max_stock
    
    pending["qty"] = cur
    await _show_stock_spinner(q, context)

async def market_start_input_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data["market_awaiting_size_input"] = True
    await _safe_edit(q, "⌨️ Digite o <b>tamanho do lote</b> (itens por pacote):", None)

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

async def market_qty_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Pode vir de botão (CallbackQuery) ou de texto (Message)
    if update.callback_query:
        q = update.callback_query
        await q.answer()
        await _show_price_spinner(q, context)
    else:
        # Se vier de texto, passamos o message como 'q'
        await _show_price_spinner(update.message, context)

# --- HANDLERS DE INPUT DE TEXTO ---

async def market_start_input_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data["market_awaiting_qty_input"] = True
    # Edita a legenda para dar feedback
    try:
        await q.edit_message_caption("⌨️ <b>MODO DE TEXTO</b>\n\nDigite a quantidade desejada no chat agora:", parse_mode="HTML")
    except:
        await q.edit_message_text("⌨️ <b>MODO DE TEXTO</b>\n\nDigite a quantidade desejada no chat agora:", parse_mode="HTML")

async def market_start_input_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data["market_awaiting_price_input"] = True
    try:
        await q.edit_message_caption("⌨️ <b>MODO DE TEXTO</b>\n\nDigite o preço total (em Ouro) no chat agora:", parse_mode="HTML")
    except:
        await q.edit_message_text("⌨️ <b>MODO DE TEXTO</b>\n\nDigite o preço total (em Ouro) no chat agora:", parse_mode="HTML")

async def market_process_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    # Só processa se o bot estiver esperando QTD ou PREÇO
    if not user_data.get("market_awaiting_qty_input") and not user_data.get("market_awaiting_price_input"):
        return

    text = update.message.text.strip()
    
    # Verifica se é número
    if not text.isdigit():
        await update.message.reply_text("🔢 Por favor, digite apenas números inteiros.")
        return

    value = int(text)
    
    # 1. Processando QUANTIDADE
    if user_data.get("market_awaiting_qty_input"):
        pending = user_data.get("market_pending")
        if not pending: return

        max_q = pending.get("qty_have", 1)
        # Ajusta se passou do limite
        if value < 1: value = 1
        if value > max_q: 
            value = max_q
            await update.message.reply_text(f"⚠️ Ajustado para o máximo que você tem: {max_q}")
        else:
            await update.message.reply_text(f"✅ Quantidade definida: {value}")

        pending["qty"] = value
        user_data.pop("market_awaiting_qty_input", None)
        
        # Avança para o próximo passo (Preço)
        await market_qty_confirm(update, context)

    # 2. Processando PREÇO
    elif user_data.get("market_awaiting_price_input"):
        if value < 1: value = 1
        
        user_data["market_price"] = value
        user_data.pop("market_awaiting_price_input", None)
        
        await update.message.reply_text(f"✅ Preço definido: {value:,} Ouro")
        # Avança para a pergunta de Público/Privado (usando Message como 'q')
        await _show_type_selection(update.message, context)

async def _show_type_selection(q, context):
    """Helper para mostrar a seleção de tipo (Público/Privado)."""
    price = context.user_data.get("market_price", 0)
    text = f"💰 <b>Preço Definido:</b> {price:,} Ouro\n\nComo deseja anunciar?"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Público", callback_data="mkt_finish_public"), InlineKeyboardButton("🔒 Privado (ID)", callback_data="mkt_ask_private")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market_sell_menu")]
    ])
    
    if hasattr(q, "edit_message_caption") or hasattr(q, "edit_message_text"):
        await _safe_edit(q, text, kb)
    else:
        await q.reply_text(text, reply_markup=kb, parse_mode="HTML")

# --- PUBLICO / PRIVADO ---

async def market_ask_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await _show_type_selection(q, context)

async def market_ask_private_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["market_awaiting_id"] = True
    
    text = (
        "🔒 <b>Venda Privada</b>\n\n"
        "Envie o <b>Nome do Personagem</b> (ex: <i>Aragorn</i>) ou o <b>@usuario</b> do Telegram do comprador.\n"
        "<i>Você também pode encaminhar uma mensagem dele.</i>"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]])
    await _safe_edit(q, text, kb)

async def market_finalize_listing(update: Update, context: ContextTypes.DEFAULT_TYPE, target_id=None, target_name=None):
    # --- IMPORT SEGURO ---
    from modules import market_manager
    
    user_id = update.effective_user.id
    q = update.callback_query
    
    pending = context.user_data.get("market_pending")
    price = context.user_data.get("market_price")

    if not pending or not price:
        msg = "⚠️ Sessão expirada. Inicie a venda novamente."
        if q: await q.answer(msg, show_alert=True)
        else: await update.effective_message.reply_text(msg)
        return

    item_removed_successfully = False
    pdata = None
    item_payload = {}
    seller_name = "Vendedor"

    try:
        pdata = await player_manager.get_player_data(user_id)
        seller_name = pdata.get("character_name", f"Player {user_id}")
        
        item_payload = {}
        stock_to_create = 1
        
        if pending["type"] == "stack":
            base_id = pending["base_id"]
            lot_size = pending["lot_size"] # 100
            stock = pending["qty"]         # 10 lotes
            
            total_items_to_remove = stock * lot_size # 1000 itens
            
            if player_manager.remove_item_from_inventory(pdata, base_id, total_items_to_remove):
                # O payload do item diz que CADA UNIDADE contém 'lot_size' itens
                item_payload = {"type": "stack", "base_id": base_id, "qty": lot_size}
                stock_to_create = stock
            else:
                if q: await q.answer("❌ Itens insuficientes.", show_alert=True)
                return

        elif pending["type"] == "unique":
            # ... (código unique mantém igual) ...
            uid = pending["uid"]
            inv = pdata.get("inventory", {})
            if uid in inv:
                item_data = inv[uid]
                del inv[uid]
                item_payload = {"type": "unique", "item": item_data, "uid": uid}
                item_removed_successfully = True
                qty = 1 # Unique é sempre 1
            else:
                if q: await q.answer("❌ Item não encontrado.", show_alert=True)
                return

        # --- 2. SALVA A REMOÇÃO ---
        await player_manager.save_player_data(user_id, pdata)

        market_manager.create_listing(
            seller_id=user_id,
            item_payload=item_payload,
            unit_price=price,
            quantity=stock_to_create, # Passa o estoque de lotes
            target_buyer_id=target_id,
            target_buyer_name=target_name,
            seller_name=seller_name
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
                if pending["type"] == "stack":
                    inv = pdata.setdefault("inventory", {})
                    base_id = pending["base_id"]
                    qty = pending["qty"]
                    inv[base_id] = int(inv.get(base_id, 0)) + qty
                
                elif pending["type"] == "unique":
                    uid = pending["uid"]
                    if "item" in item_payload:
                        pdata.setdefault("inventory", {})[uid] = item_payload["item"]
                
                await player_manager.save_player_data(user_id, pdata)
                err_msg = "⚠️ <b>Erro no Mercado!</b>\nO sistema detectou uma falha, mas seu item foi <b>DEVOLVIDO</b> ao inventário."
            except Exception as e_rollback:
                logger.critical(f"FALHA NO ROLLBACK DO JOGADOR {user_id}: {e_rollback}")
                err_msg = "❌ <b>Erro Crítico!</b> Contate o suporte. (Cod: ROLLBACK_FAIL)"
        else:
            err_msg = "❌ Erro ao processar. Nenhum item removido."

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
        if update.message.forward_from:
            target_id = update.message.forward_from.id
            target_name = update.message.forward_from.first_name
        
        elif text.isdigit():
            target_id = int(text)
            try:
                pdata = await player_manager.get_player_data(target_id)
                if pdata: target_name = pdata.get("character_name", "Jogador")
            except: pass

        else:
            pdata = None
            if text.startswith("@"):
                from modules.player import queries
                pdata = await queries.find_by_username(text)
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

        if not target_id:
            await update.message.reply_text("❌ Jogador não encontrado. Verifique o nome exato ou use o ID.")
            return

        if target_id == user_id:
            await update.message.reply_text("❌ Você não pode vender para si mesmo.")
            return
        
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
    
    # --- IMPORT SEGURO ---
    from modules import market_manager
    
    listings = market_manager.list_by_seller(user_id)
    
    if not listings:
        msg = "👤 <b>Minhas Vendas</b>\n\n<i>Você não tem itens à venda no momento.</i>"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]])
        await _safe_edit(q, msg, kb)
        return

    lines = ["👤 𝐌𝐢𝐧𝐡𝐚𝐬 𝐕𝐞𝐧𝐝𝐚𝐬 𝐀𝐭𝐢𝐯𝐚𝐬\n"]
    rows = []
    
    for idx, l in enumerate(listings, start=1):
        card_text = _render_my_sale_card(idx, l)
        lines.append(card_text)
        lines.append("") 
        
        lid = l['id']
        rows.append([InlineKeyboardButton(f"❌ Cancelar Item #{lid}", callback_data=f"market_cancel_{lid}")])

    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])
    
    full_text = "\n".join(lines)
    await _safe_edit(q, full_text, InlineKeyboardMarkup(rows))

async def market_cancel_listing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela uma venda ativa."""
    q = update.callback_query
    await q.answer()
    
    # --- IMPORT SEGURO ---
    from modules import market_manager

    try:
        # Extrai o ID do callback "market_cancel_123"
        lid = int(q.data.replace("market_cancel_", ""))
        market_manager.delete_listing(lid)
        await q.answer("✅ Anúncio cancelado.", show_alert=True)
        # Atualiza a lista
        await market_my(update, context)
    except Exception as e:
        await q.answer(f"Erro ao cancelar: {e}", show_alert=True)

async def market_start_input_triggers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prepara o bot para receber texto digitado (Lote, Qtd ou Preço)."""
    q = update.callback_query
    await q.answer()
    data = q.data

    msg = ""
    if "size" in data:
        context.user_data["market_awaiting_size_input"] = True
        msg = "o TAMANHO DO LOTE (itens por pacote)"
    elif "qty" in data:
        context.user_data["market_awaiting_qty_input"] = True
        msg = "a QUANTIDADE de lotes"
    elif "price" in data:
        context.user_data["market_awaiting_price_input"] = True
        msg = "o PREÇO TOTAL"

    try:
        await q.edit_message_caption(f"⌨️ <b>MODO DE TEXTO</b>\n\nDigite {msg} no chat agora:")
    except:
        await q.message.reply_text(f"⌨️ <b>MODO DE TEXTO</b>\n\nDigite {msg} no chat agora:", parse_mode="HTML")

async def market_input_handlers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Roteador central de inputs de texto do mercado."""
    ud = context.user_data
    text = update.message.text.strip()
    
    # --- 1. Input de Tamanho do Lote ---
    if ud.get("market_awaiting_size_input"):
        if not text.isdigit(): return await update.message.reply_text("🔢 Digite apenas números.")
        val = int(text)
        
        pending = ud.get("market_pending", {})
        max_avail = pending.get("qty_have", 1)
        val = max(1, min(val, max_avail)) # Trava entre 1 e o máx que tem
        
        pending["lot_size"] = val
        ud.pop("market_awaiting_size_input", None) # Limpa estado
        
        await update.message.reply_text(f"✅ Tamanho do lote: {val}")
        await market_lot_size_confirm(update, context)

    # --- 2. Input de Quantidade (Estoque) ---
    elif ud.get("market_awaiting_qty_input"):
        if not text.isdigit(): return await update.message.reply_text("🔢 Digite apenas números.")
        val = int(text)
        
        pending = ud.get("market_pending", {})
        lot_size = pending.get("lot_size", 1)
        max_avail = pending.get("qty_have", 1)
        max_stock = max(1, max_avail // lot_size)
        
        val = max(1, min(val, max_stock))
        pending["qty"] = val
        ud.pop("market_awaiting_qty_input", None)
        
        await update.message.reply_text(f"✅ Estoque definido: {val} lotes")
        await market_qty_confirm(update, context)

    # --- 3. Input de Preço ---
    elif ud.get("market_awaiting_price_input"):
        if not text.isdigit(): return await update.message.reply_text("🔢 Digite apenas números.")
        val = int(text)
        ud["market_price"] = max(1, val)
        ud.pop("market_awaiting_price_input", None)
        
        await update.message.reply_text(f"✅ Preço definido: {val:,} Ouro")
        await _show_type_selection(update.message, context)

    # --- 4. Input de ID (Venda Privada) ---
    elif ud.get("market_awaiting_id"):
        target_id = None
        target_name = "Desconhecido"

        # Tenta pegar por encaminhamento, ID numérico ou busca de nome
        if update.message.forward_from:
            target_id = update.message.forward_from.id
            target_name = update.message.forward_from.first_name
        elif text.isdigit():
            target_id = int(text)
        else:
            # Tenta buscar pelo nome no banco
            try:
                from modules.player import queries
                res = await queries.find_player_by_name(text)
                if not res: res = await queries.find_player_by_name_norm(text)
                if res:
                    target_id, pdata = res
                    target_name = pdata.get("character_name", text)
            except: pass

        if target_id:
            if target_id == update.effective_user.id:
                await update.message.reply_text("❌ Você não pode vender para si mesmo.")
            else:
                await market_finalize_listing(update, context, target_id=target_id, target_name=target_name)
        else:
            await update.message.reply_text("❌ Jogador não encontrado. Tente o ID numérico ou encaminhar uma mensagem dele.")

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

async def _safe_edit(query, text, kb):
    if hasattr(query, "edit_message_caption"):
        try: await query.edit_message_caption(caption=text, reply_markup=kb, parse_mode='HTML'); return
        except: pass
        try: await query.edit_message_text(text=text, reply_markup=kb, parse_mode='HTML'); return
        except: pass
    if hasattr(query, "reply_text"):
        await query.reply_text(text, reply_markup=kb, parse_mode='HTML')
        return
    try: await query.message.reply_text(text, reply_markup=kb, parse_mode='HTML')
    except: pass

async def market_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ud = context.user_data
    # Roteamento inteligente
    if ud.get("market_awaiting_size_input"):
        await market_process_size_input(update, context)
    elif ud.get("market_awaiting_qty_input") or ud.get("market_awaiting_price_input"):
        await market_process_text_input(update, context) # (Função existente renomeada ou mantida)
    elif ud.get("market_awaiting_id"):
        await market_catch_input_id(update, context)

async def market_process_size_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text.isdigit(): return
    val = int(text)
    
    pending = context.user_data.get("market_pending")
    max_avail = pending["qty_have"]
    
    if val < 1: val = 1
    if val > max_avail: val = max_avail
    
    pending["lot_size"] = val
    context.user_data.pop("market_awaiting_size_input", None)
    
    # Confirma e vai pro próximo passo
    await update.message.reply_text(f"✅ Tamanho do lote: {val}")
    await market_lot_size_confirm(update, context)

# ==============================
#  EXPORTS
# ==============================
# ==============================
#  EXPORTS (HANDLERS CORRIGIDOS)
# ==============================
market_open_handler = CallbackQueryHandler(market_open, pattern=r'^market$')
market_adventurer_handler = CallbackQueryHandler(market_adventurer, pattern=r'^market_adventurer$')
market_list_handler = CallbackQueryHandler(market_list, pattern=r'^market_list')
market_buy_handler = CallbackQueryHandler(market_buy, pattern=r'^market_buy_')
market_sell_menu_handler = CallbackQueryHandler(market_sell_menu, pattern=r'^market_sell_menu$')
market_sell_cat_handler = CallbackQueryHandler(market_sell_list_category, pattern=r'^market_sell_cat:')
market_pick_unique_handler = CallbackQueryHandler(market_pick_unique, pattern=r'^market_pick_unique_')
market_pick_stack_handler = CallbackQueryHandler(market_pick_stack, pattern=r'^market_pick_stack_')

# --- CORREÇÃO DO TRAVAMENTO AQUI ---
# O regex anterior '.*' engolia o 'confirm'. Agora usamos (inc|dec|max) especificamente.

# 1. Spinner de Tamanho (Lote)
market_size_spin_handler = CallbackQueryHandler(market_lot_size_spin, pattern=r'^mkt_size_(inc|dec|max)')
market_size_confirm_handler = CallbackQueryHandler(market_lot_size_confirm, pattern=r'^mkt_size_confirm$')

# 2. Spinner de Estoque (Pack) - ESTE ERA O ERRO DO PRINT
market_pack_spin_handler = CallbackQueryHandler(market_qty_spin, pattern=r'^mkt_pack_(inc|dec|max)')
market_pack_confirm_handler = CallbackQueryHandler(market_qty_confirm, pattern=r'^mkt_pack_confirm$')

# 3. Spinner de Preço
market_price_spin_handler = CallbackQueryHandler(market_price_spin, pattern=r'^mktp_(inc|dec)')
market_price_confirm_handler = CallbackQueryHandler(market_ask_type, pattern=r'^mktp_confirm$')

# 4. Finalização e Outros
market_finish_public_handler = CallbackQueryHandler(market_finalize_listing, pattern=r'^mkt_finish_public$')
market_ask_private_handler = CallbackQueryHandler(market_ask_private_id, pattern=r'^mkt_ask_private$')
market_cancel_new_handler = CallbackQueryHandler(market_cancel_new, pattern=r'^market_cancel_new$')
market_my_handler = CallbackQueryHandler(market_my, pattern=r'^market_my$')
market_cancel_listing_handler = CallbackQueryHandler(market_cancel_listing, pattern=r'^market_cancel_\d+$')

# Inputs de Texto
market_input_triggers_handler = CallbackQueryHandler(market_start_input_triggers, pattern=r'^mkt_input_.*')
market_text_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, market_input_handlers)
market_input_id_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, market_input_handlers) # Redundância segura
