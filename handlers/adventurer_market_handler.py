# handlers/adventurer_market_handler.py
# (VERSÃO FINAL LIMPA: Auth Híbrida Padronizada - Sem código legado)

import logging
import asyncio
from typing import List, Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram.error import BadRequest
from telegram.constants import ParseMode

# --- IMPORTAÇÕES BSON (CRÍTICO PARA OBJECTID) ---
from bson import ObjectId, errors as bson_errors

# --- MÓDULOS PRINCIPAIS ---
from modules import player_manager, game_data, file_ids, market_utils
from modules.player import queries
from modules.auth_utils import get_current_player_id

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
    from modules.game_data.items_evolution import EVOLUTION_ITEMS_DATA
except ImportError:
    game_data = None
    EVOLUTION_ITEMS_DATA = {}

logger = logging.getLogger(__name__)

# --- CONFIGURAÇÃO DE LOGS DO MERCADO ---
MARKET_LOG_GROUP_ID = -1002881364171
MARKET_LOG_TOPIC_ID = 24475

# ==============================================================================
# 🛠️ HELPER: CONVERSÃO SEGURA DE ID
# ==============================================================================
def ensure_object_id(uid):
    if isinstance(uid, ObjectId):
        return uid
    if isinstance(uid, str) and ObjectId.is_valid(uid):
        return ObjectId(uid)
    return None

def short_id(oid):
    """Retorna os últimos 4 dígitos do ObjectId para exibição visual limpa"""
    s = str(oid)
    return f"...{s[-4:]}" if len(s) > 4 else s

async def _send_market_log(context: ContextTypes.DEFAULT_TYPE, text: str):
    """Envia notificação RPG para o canal de logs."""
    try:
        await context.bot.send_message(
            chat_id=MARKET_LOG_GROUP_ID,
            message_thread_id=MARKET_LOG_TOPIC_ID,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_notification=False
        )
    except Exception as e:
        logger.error(f"Falha ao enviar log de mercado: {e}")

async def _send_smart(query, context, chat_id, text, kb, img_key):
    try: await query.delete_message()
    except: pass
    
    fd = file_ids.get_file_data(img_key) if file_ids else None
    
    if fd and fd.get("id"):
        try:
            if fd.get("type") == "video":
                await context.bot.send_video(chat_id, fd["id"], caption=text, reply_markup=kb, parse_mode="HTML")
            else:
                await context.bot.send_photo(chat_id, fd["id"], caption=text, reply_markup=kb, parse_mode="HTML")
            return
        except: pass

    await context.bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")


# ==============================================================================
# 🔍 FUNÇÕES DE RENDERIZAÇÃO
# ==============================================================================
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
    seller_name = listing.get("seller_name") or f"Vendedor"
    item_payload = listing.get("item", {})
    qty_stock = listing.get("quantity", 0)

    # Tratamento de ID visual
    lid = listing.get("_id") or listing.get("id")
    visual_id = short_id(lid)

    tid = listing.get("target_buyer_id")
    tname = listing.get("target_buyer_name") or "Alguém"
    lock_status = f"🔐 <b>Reservado:</b> {tname}" if tid else ""
    lock_emoji = "🔒 " if tid else ""

    if item_payload.get("type") == "stack":
        base_id = item_payload.get("base_id")
        lot_size = item_payload.get("qty", 1)
        info = _get_item_info(base_id)
        name = info.get("display_name") or base_id.replace("_", " ").title()
        emoji = info.get("emoji", "📦")
        
        footer = f"╰┈➤ 💸 <b>{price:,} 🪙</b>  👤 {seller_name}"
        if lock_status: footer += f"\n╰┈➤ {lock_status}"

        return (
            f"{icon_num}┈➤ {lock_emoji}{emoji} <b>{name}</b> x{lot_size}\n"
            f"├┈➤ 📦 Estoque: {qty_stock} lotes\n"
            f"{footer} 🆔 <pre>{visual_id}</pre>"
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
        
        # Renderização de stats omitida para brevidade (igual ao original)
        class_str = _detect_class_display(inst, base_id)

        footer = f"╰┈➤ 💸 <b>{price:,} 🪙</b>  👤 {seller_name}"
        if lock_status: footer += f"\n╰┈➤ {lock_status}"

        return (
            f"{icon_num}┈➤ {lock_emoji}{emoji} <b>{name}</b> [{rarity}] {dura_str}\n"
            f"├┈➤ {class_str}\n"
            f"{footer} 🆔 <pre>{visual_id}</pre>"
        )

def _render_sell_card(idx: int, item_wrapper: dict) -> str:
    icons = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    icon_num = icons[idx] if idx < len(icons) else f"{idx}️⃣"
    
    if item_wrapper["type"] == "stack":
        base_id = item_wrapper["base_id"]
        qty = item_wrapper["qty"]
        info = _get_item_info(base_id)
        name = info.get("display_name") or base_id.replace("_", " ").title()
        emoji = info.get("emoji", "📦")
        return f"{icon_num}┈➤ {emoji} <b>{name}</b>\n╰┈➤ 📦 Lote de {qty} un."
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
        return f"{icon_num}┈➤ {emoji} <b>{name}{plus_str}</b> [{rarity}]\n├┈➤ {dura_str} {stats_str}\n╰┈➤ {class_str}"

def _render_my_sale_card(idx: int, listing: dict) -> str:
    icons = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    icon_num = icons[idx] if idx < len(icons) else f"{idx}️⃣"
    
    lid = listing.get("_id") or listing.get("id")
    visual_id = short_id(lid)

    price = int(listing.get("unit_price", 0))
    item_payload = listing.get("item", {})
    qty_stock = listing.get("quantity", 0)
    target_id = listing.get("target_buyer_id")
    target_name = listing.get("target_buyer_name") or "Alguém"
    status_icon = "🔐" if target_id else "📢"
    status_text = f"Reservado: {target_name}" if target_id else "Público"

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

    return f"{icon_num}┈➤ {header}\n├┈➤ {details} │ 🆔 <b>...{visual_id}</b>\n╰┈➤ {status_icon} <b>{status_text}</b>"

# ==============================
#  HANDLERS PRINCIPAIS
# ==============================

async def market_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    user_id = ensure_object_id(get_current_player_id(update, context))

    try:
        pdata = await player_manager.get_player_data(user_id)
        gold = int(pdata.get("gold", 0))
        gems = int(pdata.get("gems", 0))
    except:
        gold, gems = 0, 0

    text = (
        f"🏰 <b>CENTRO COMERCIAL DE ELDORA</b>\n"
        f"╭┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤\n"
        f"│ 🎒 <b>SEUS RECURSOS:</b>\n"
        f"│ 💰 <b>{gold:,}</b> Ouro\n"
        f"│ 💎 <b>{gems:,}</b> Gemas\n"
        f"╰┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤\n\n"
        f"<i>Mercadores gritam ofertas e aventureiros negociam itens raros.</i>"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎒 Mercado )", callback_data="market_adventurer"), InlineKeyboardButton("🏰 Loja do Reino", callback_data="market_kingdom")],
        [InlineKeyboardButton("🏛️ Leilões ", callback_data="gem_market_main"), InlineKeyboardButton("💎 Loja Premium", callback_data="gem_shop")],
        [InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data="show_kingdom_menu")]
    ])
    await _send_smart(query, context, update.effective_chat.id, text, kb, "market")

async def market_adventurer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Garante ObjectId para buscar no banco corretamente
    user_id = ensure_object_id(get_current_player_id(update, context))

    try:
        pdata = await player_manager.get_player_data(user_id)
        gold = int(pdata.get("gold", 0))
    except: 
        gold = 0

    text = (f"🎒 𝐌𝐄𝐑𝐂𝐀𝐃𝐎 𝐃𝐎 𝐀𝐕𝐄𝐍𝐓𝐔𝐑𝐄𝐈𝐑𝐎\n╭┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤\n│ 💰 𝙎𝙚𝙪 𝙎𝙖𝙡𝙙𝙤: {gold:,} 🪙\n╰┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 𝐂𝐨𝐦𝐩𝐫𝐚𝐫", callback_data="market_list"), InlineKeyboardButton("➕ 𝐕𝐞𝐧𝐝𝐞𝐫", callback_data="market_sell_menu")],
        [InlineKeyboardButton("👤 𝐌𝐢𝐧𝐡𝐚𝐬 𝐕𝐞𝐧𝐝𝐚𝐬", callback_data="market_my")],
        [InlineKeyboardButton("⬅️ 𝑽𝒐𝒍𝒕𝒂𝒓 ", callback_data="market")]
    ])
    await _send_smart(query, context, update.effective_chat.id, text, kb, "mercado_aventureiro")

async def market_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    user_id = ensure_object_id(get_current_player_id(update, context))
    chat_id = update.effective_chat.id
    
    from modules import market_manager
    try: page = int(q.data.split(":")[1]) if ":" in q.data else 1
    except: page = 1

    try:
        pdata = await player_manager.get_player_data(user_id) or {}
        gold = pdata.get("gold", 0)
        all_listings = market_manager.list_active(viewer_id=user_id)
    except Exception as e: 
        logger.error(f"Erro ao listar mercado: {e}")
        all_listings = []
    
    if not all_listings:
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

    header = (f"╭┈┈┈┈┈➤ 🛒 <b>MERCADO ({page}/{total_pages})</b> ┈┈┈┈┈╮\n │ 💰 <b>Seu Saldo:</b> {gold:,} 🪙\n╰┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤\n\n")
    body_lines = []
    selection_buttons = []

    if not listings_page: body_lines.append("<i>Página vazia.</i>")
    else:
        for idx, listing in enumerate(listings_page, start=1):
            try:
                if "seller_name" not in listing:
                    sid = listing.get("seller_id")
                    try:
                        s_data = await player_manager.get_player_data(sid)
                        s_name = s_data.get("character_name", f"Vendedor")
                        listing["seller_name"] = s_name
                    except: listing["seller_name"] = f"Vendedor"

                card_text = _render_listing_card(idx, listing)
                body_lines.append(card_text)
                body_lines.append("") 
                
                seller_id = listing.get("seller_id")
                
                # --- CORREÇÃO IMPORTANTE AQUI ---
                # Prioriza o _id (ObjectId) e converte pra string
                raw_lid = listing.get("_id") or listing.get("id")
                lid = str(raw_lid) 
                # --------------------------------

                if str(seller_id) != str(user_id):
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
    await _send_smart(q, context, chat_id, full_text, InlineKeyboardMarkup(keyboard), "mercado_aventureiro")

async def market_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    
    # Garante que temos o ID do comprador corretamente tratado como ObjectId
    buyer_id = ensure_object_id(get_current_player_id(update, context))
    
    # Imports locais para evitar ciclos e garantir funcionamento
    from modules import market_manager
    from modules.player.premium import PremiumManager 
    from bson import ObjectId 

    # --- 1. PARSE DO ID (CORRIGIDO PARA OBJECTID) ---
    try: 
        lid_str = q.data.replace("market_buy_", "")
        
        # Valida se é um ObjectId válido do MongoDB (24 caracteres hex)
        if not ObjectId.is_valid(lid_str):
            await q.answer("❌ ID inválido (formato incorreto).", show_alert=True)
            return
            
        lid = ObjectId(lid_str) # Converte string do botão para ObjectId do Banco
    except Exception: 
        await q.answer("Erro ao processar ID do item.", show_alert=True)
        return

    # --- 2. TRAVA DE SEGURANÇA: APENAS VIP/LENDA/PREMIUM COMPRAM ---
    pdata = await player_manager.get_player_data(buyer_id)
    if not pdata: return

    # --- CORREÇÃO DE RECONHECIMENTO DE PLANO ---
    # Lê o tier DIRETAMENTE do banco de dados para evitar erros na classe PremiumManager
    raw_tier = pdata.get("premium_tier", "free")
    current_tier = str(raw_tier).lower().strip()
    
    # Lista configurada conforme seu premium.py
    ALLOWED_TIERS = ["premium", "vip", "lenda", "admin"]
    
    # Verifica se o plano atual está na lista permitida
    is_vip = (current_tier in ALLOWED_TIERS)

    if not is_vip:
        await q.answer(
            "🔒 Apenas Aventureiros VIP podem COMPRAR no mercado!\n\n"
            "Torne-se VIP para desbloquear compras ou venda seus itens para ganhar Ouro.",
            show_alert=True
        )
        return
    # ---------------------------------------------

    # --- 3. EXECUÇÃO DA COMPRA ---
    try:
        # Tenta comprar (suporta tanto função sync quanto async do manager)
        try: 
            listing, cost = market_manager.purchase_listing(buyer_id=buyer_id, listing_id=lid, quantity=1)
        except TypeError: 
            listing, cost = await market_manager.purchase_listing(buyer_id=buyer_id, listing_id=lid, quantity=1)
        
        # Prepara dados para o Log e UI
        buyer_name = pdata.get("character_name", f"Player")
        seller_name = listing.get("seller_name", "Desconhecido")
        item_payload = listing.get("item", {})
        item_display = "Item Misterioso"
        
        # Formata o nome do item para o Log
        if item_payload.get("type") == "stack":
            base_id = item_payload.get("base_id")
            lot_size = item_payload.get("qty", 1)
            info = _get_item_info(base_id)
            i_name = info.get("display_name") or base_id
            item_display = f"{i_name} (Lote de {lot_size})"
        else:
            inst = item_payload.get("item", {})
            base_id = inst.get("base_id")
            info = _get_item_info(base_id)
            i_name = inst.get("display_name") or info.get("display_name") or base_id
            rarity = str(inst.get('rarity','comum')).upper()
            item_display = f"{i_name} [{rarity}]"

        # Log Bonito no Canal
        rpg_log = (
            f"🤝 <b>NEGÓCIO FECHADO!</b>\n\n"
            f"╭┈➤👤 <b>Comprador:</b> {buyer_name}\n"
            f"├┈➤🛒 <b>Adquiriu:</b> {item_display}\n"
            f"├┈➤💸 <b>Pagou:</b> {cost:,} Ouro\n"
            f"╰┈➤🤝 <b>Vendedor:</b> {seller_name}\n\n"
            f"    ⚖️ <i>A economia de Eldora segue girando!</i>"
        )
        # Envia log em background
        context.application.create_task(_send_market_log(context, rpg_log))
        
        await q.answer(f"✅ Compra realizada! -{cost} ouro", show_alert=True)
        
        # Recarrega a lista para remover o item comprado da tela
        await market_list(update, context)
        
    except ValueError as ve:
        # Erros de lógica de negócio (sem saldo, item já vendido, item seu, etc)
        await q.answer(f"❌ {str(ve)}", show_alert=True)
        await market_list(update, context) # Recarrega pois o item pode ter sumido
    except Exception as e:
        logger.error(f"Erro crítico na compra de mercado: {e}")
        await q.answer("❌ Erro interno ao processar compra.", show_alert=True)
        
async def market_sell_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "➕ <b>Vender Item - Escolha a Categoria</b>\n\nSelecione o tipo de item para vender por Ouro:"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Equipamentos", callback_data="market_sell_cat:equip:1")],
        [InlineKeyboardButton("🧱 Materiais", callback_data="market_sell_cat:mat:1"), InlineKeyboardButton("🧪 Consumíveis", callback_data="market_sell_cat:cons:1")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]
    ])
    await _safe_edit(query, text, kb)

async def market_sell_list_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = get_current_player_id(update, context)

    try: 
        parts = query.data.split(':')
        category = parts[1]
        page = int(parts[2]) if len(parts) > 2 else 1
    except: category, page = "mat", 1

    try:
        pdata = await player_manager.get_player_data(user_id) or {}
        inv = pdata.get("inventory", {}) or {}
        gold = pdata.get("gold", 0)
        char_name = pdata.get("character_name", "Aventureiro")
    except Exception: return
    
    # --- 1. PREPARAÇÃO: Mapear o que está equipado (SEGURANÇA) ---
    equipment = pdata.get("equipment", {})
    equipped_ids = {uid for uid in equipment.values() if uid}
    # -------------------------------------------------------------

    sellable = []
    WHITELIST_GOLD = [
        "couro_de_lobo", "couro_de_lobo_alfa", "couro_lobo", "couro_curtido",
        "couro_reforcado", "couro_escamoso", 
        "rolo_de_pano_simples", "veludo_runico", "rolo_seda_sombria",
        "barra_de_ferro", "barra_de_aco", "barra_de_prata", "barra_bronze",
        "fio_de_prata",
        "presa_de_javali", "asa_de_morcego", "membrana_de_couro_fino",
        
        "minerio_de_cobre", "minerio_de_ferro", "minerio_de_ouro",
        "minerio_de_estanho", "minerio_de_prata", "carvao", "cristal_bruto",
        "pedra", "gema_bruta", "gema_polida", "fragmento_gargula",
        ]
    BLOCKED_KEYWORDS = [
        "essencia", "fragmento", "alma", "emblema", 
        "lamina", "lâmina", "poeira", "aco", "aço", "totem", 
        "reliquia", "relíquia", "foco", 
        "coracao", "coração", "selo", "calice", "cálice", 
        "espirito", "espírito", 
        "frequencia", "energia", "nevoa", 
        "névoa", "aura", "tomo", "livro", 
        "pergaminho", "grimorio", "grimório", 
        "skill", "book", "habilidade", 
        "transcendencia", "transcendência", 
        "skin", "traje", "caixa", "chave", 
        "ticket", "sigilo", "cristal", "batuta", 
        "gemas", "gems", "ouro", "gold", "xp", "experiencia"
        ]
    
    for item_id, data in inv.items():
        # --- 2. FILTRO DE SEGURANÇA ---
        if item_id in equipped_ids:
            continue
        # ------------------------------

        try:
            if isinstance(data, dict): 
                base_id = data.get("base_id") or data.get("tpl") or item_id
                qty = data.get("qty", 0) or 1; is_unique = True; inst_data = data
            else: 
                base_id = item_id; qty = int(data); is_unique = False; inst_data = {}

            info = _get_item_info(base_id)
            itype = str(info.get("type", "")).lower()
            is_equipment_type = (is_unique or itype in ["equipamento", "arma", "armadura", "acessorio", "equipment", "weapon", "armor"])

            if base_id in EVOLUTION_ITEMS_DATA and base_id not in WHITELIST_GOLD: continue
            if not is_equipment_type:
                bid_lower = str(base_id).lower()
                if any(k in bid_lower for k in BLOCKED_KEYWORDS) and base_id not in WHITELIST_GOLD: continue

            if base_id in CONSUMABLES_DATA:
                if CONSUMABLES_DATA[base_id].get("tradable") is False: continue

            should_show = False
            if category == "equip" and is_equipment_type: should_show = True
            elif category == "cons" and (not is_unique and itype in ["consumivel", "consumable", "potion", "food", "reagent"]): should_show = True
            elif category == "mat" and (not is_unique and not is_equipment_type and itype not in ["consumivel", "potion", "food", "reagent"]): should_show = True

            if should_show and qty > 0:
                rarity_rank = _rarity_to_int(inst_data.get("rarity", "comum")) if is_unique else 0
                sellable.append({"type": "unique" if is_unique else "stack", "uid": item_id, "base_id": base_id, "qty": qty, "inst": inst_data, "sort_name": base_id, "rarity_rank": rarity_rank})
        except Exception: continue

    sellable.sort(key=lambda x: (0 if x["type"] == "unique" else 1, -x["rarity_rank"], x["sort_name"]))
    ITEMS_PER_PAGE = 5
    total = len(sellable)
    total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * ITEMS_PER_PAGE
    items_page = sellable[start : start + ITEMS_PER_PAGE]
    cat_names = {"equip": "⚔️ Equipamentos", "cons": "🧪 Consumíveis", "mat": "🧱 Materiais"}
    cat_title = cat_names.get(category, "Itens")

    header = (f"╭┈┈┈➤ 🛒 <b>VENDER: {cat_title} ({page}/{total_pages})</b>\n │ 👤 <b>{char_name}</b>\n │ 💰 <b>Saldo:</b> {gold:,} 🪙\n╰┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤\n\n")
    body_lines = []
    selection_buttons = [] 

    if not sellable:
        body_lines.append("🎒 <i>Nenhum item encontrado nesta categoria.</i>")
        if category == "mat": body_lines.append("\nℹ️ <i>Materiais raros de evolução devem ser negociados por Gemas.</i>")
    elif not items_page: body_lines.append("<i>Página vazia.</i>")
    else:
        for idx, item in enumerate(items_page, start=1):
            text_block = _render_sell_card(idx, item)
            body_lines.append(text_block); body_lines.append("") 
            if item["type"] == "unique": cb = f"market_pick_unique_{item['uid']}"
            else: cb = f"market_pick_stack_{item['base_id']}"
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

async def market_pick_stack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    base_id = q.data.replace("market_pick_stack_", "")
    user_id = get_current_player_id(update, context)
    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {})
    qty_have = int(inv.get(base_id, 0))

    if qty_have <= 0: await q.answer("Você não possui este item.", show_alert=True); return
    context.user_data["market_pending"] = {"type": "stack", "base_id": base_id, "qty_have": qty_have, "lot_size": 1, "qty": 1}
    context.user_data["market_price"] = 50 
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
    lot_size = pending["lot_size"]; max_avail = pending["qty_have"]
    item_name = _get_item_name_from_context(context)
    possible_stock = max_avail // lot_size
    text = (f"📦 <b>TAMANHO DO LOTE</b>\nItem: {item_name}\nTotal na Mochila: {max_avail}\n\n🔢 <b>Itens por Pacote:</b> {lot_size}\n<i>(Isso criaria no máximo {possible_stock} pacotes)</i>")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("-10", callback_data="mkt_size_dec_10"), InlineKeyboardButton("-1", callback_data="mkt_size_dec_1"), InlineKeyboardButton(f"{lot_size}", callback_data="noop"), InlineKeyboardButton("+1", callback_data="mkt_size_inc_1"), InlineKeyboardButton("+10", callback_data="mkt_size_inc_10")],
        [InlineKeyboardButton("🚀 Tudo em 1 Lote", callback_data="mkt_size_max"), InlineKeyboardButton("⌨️ Digitar", callback_data="mkt_input_size_start")],
        [InlineKeyboardButton("✅ Confirmar Tamanho", callback_data="mkt_size_confirm"), InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]
    ])
    await _safe_edit(q, text, kb)

async def market_lot_size_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q: await q.answer()
    pending = context.user_data.get("market_pending")
    lot_size = pending["lot_size"]; max_avail = pending["qty_have"]
    if (max_avail // lot_size) < 1:
        if q: await q.edit_message_caption("⚠️ Tamanho de lote maior que inventário!")
        return
    pending["qty"] = 1 
    await _show_stock_spinner(q or update.message, context)

async def _show_stock_spinner(q, context):
    pending = context.user_data.get("market_pending")
    stock = pending["qty"]; lot_size = pending["lot_size"]; max_avail = pending["qty_have"]
    total_items_selling = stock * lot_size
    text = (f"📊 <b>DEFINIR ESTOQUE</b>\n📦 Lote: {lot_size} itens\n\n🔢 <b>Quantos Lotes vender?</b> {stock}\n<i>Total de itens a vender: {total_items_selling} / {max_avail}</i>")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("-10", callback_data="mkt_pack_dec_10"), InlineKeyboardButton("-1", callback_data="mkt_pack_dec_1"), InlineKeyboardButton(f"{stock}", callback_data="noop"), InlineKeyboardButton("+1", callback_data="mkt_pack_inc_1"), InlineKeyboardButton("+10", callback_data="mkt_pack_inc_10")],
        [InlineKeyboardButton("🚀 Vender Todos os Lotes", callback_data="mkt_pack_max"), InlineKeyboardButton("✅ Confirmar Estoque", callback_data="mkt_pack_confirm")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]
    ])
    await _safe_edit(q, text, kb)

async def market_lot_size_spin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    pending = context.user_data.get("market_pending")
    if not pending: return
    action = q.data; cur = pending["lot_size"]; max_avail = pending["qty_have"]
    if "max" in action: cur = max_avail
    else:
        try: delta = int(action.split("_")[-1])
        except: delta = 1
        if "inc" in action: cur += delta
        elif "dec" in action: cur -= delta
    if cur < 1: cur = 1
    if cur > max_avail: cur = max_avail
    pending["lot_size"] = cur
    await _show_lot_size_spinner(q, context)

async def _show_qty_spinner(q, context):
    pending = context.user_data.get("market_pending")
    cur = pending["qty"]; max_q = pending.get("qty_have", 1)
    text = (f"⚖️ <b>QUANTIDADE</b>\n🎒 Disponível: {max_q}\n\n📦 <b>Vender:</b> {cur}")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("-10", callback_data="mkt_pack_dec_10"), InlineKeyboardButton("-1", callback_data="mkt_pack_dec_1"), InlineKeyboardButton(f"{cur}", callback_data="noop"), InlineKeyboardButton("+1", callback_data="mkt_pack_inc_1"), InlineKeyboardButton("+10", callback_data="mkt_pack_inc_10")],[InlineKeyboardButton("⌨️ Digitar", callback_data="mkt_input_qty_start"), InlineKeyboardButton("✅ Confirmar", callback_data="mkt_pack_confirm")],[InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]])
    await _safe_edit(q, text, kb)

async def _show_price_spinner(q, context):
    cur = context.user_data.get("market_price", 50)
    qty = context.user_data.get("market_pending", {}).get("qty", 1)
    total = cur * qty
    text = (f"💰 <b>DEFINIR PREÇO</b>\n📦 Quantidade: {qty}\n\n🏷️ <b>Preço por Unidade:</b> {cur:,} 🪙\n💵 <b>Valor Total da Venda:</b> {total:,} 🪙\n")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("-1000", callback_data="mktp_dec_1000"), InlineKeyboardButton("-100", callback_data="mktp_dec_100")],[InlineKeyboardButton(f"Unid: {cur}", callback_data="noop")],[InlineKeyboardButton("+100", callback_data="mktp_inc_100"), InlineKeyboardButton("+1000", callback_data="mktp_inc_1000")],[InlineKeyboardButton("⌨️ Digitar Valor Unitário", callback_data="mkt_input_price_start")],[InlineKeyboardButton("✅ Confirmar", callback_data="mktp_confirm"), InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]])
    await _safe_edit(q, text, kb)

async def market_qty_spin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    pending = context.user_data.get("market_pending")
    action = q.data; cur = pending["qty"]; lot_size = pending["lot_size"]; max_avail = pending["qty_have"]
    max_stock = max_avail // lot_size
    if "max" in action: cur = max_stock
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
    cur = context.user_data.get("market_price", 50); action = q.data
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
    if update.callback_query:
        q = update.callback_query; await q.answer(); await _show_price_spinner(q, context)
    else: await _show_price_spinner(update.message, context)

async def market_start_input_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data["market_awaiting_qty_input"] = True
    try: await q.edit_message_caption("⌨️ <b>MODO DE TEXTO</b>\n\nDigite a quantidade desejada no chat agora:", parse_mode="HTML")
    except: await q.edit_message_text("⌨️ <b>MODO DE TEXTO</b>\n\nDigite a quantidade desejada no chat agora:", parse_mode="HTML")

async def market_start_input_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data["market_awaiting_price_input"] = True
    try: await q.edit_message_caption("⌨️ <b>MODO DE TEXTO</b>\n\nDigite o preço total (em Ouro) no chat agora:", parse_mode="HTML")
    except: await q.edit_message_text("⌨️ <b>MODO DE TEXTO</b>\n\nDigite o preço total (em Ouro) no chat agora:", parse_mode="HTML")

async def market_process_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    if not user_data.get("market_awaiting_qty_input") and not user_data.get("market_awaiting_price_input"): return
    text = update.message.text.strip()
    if not text.isdigit(): await update.message.reply_text("🔢 Por favor, digite apenas números inteiros."); return
    value = int(text)
    if user_data.get("market_awaiting_qty_input"):
        pending = user_data.get("market_pending")
        if not pending: return
        max_q = pending.get("qty_have", 1)
        if value < 1: value = 1
        if value > max_q: value = max_q; await update.message.reply_text(f"⚠️ Ajustado para o máximo que você tem: {max_q}")
        else: await update.message.reply_text(f"✅ Quantidade definida: {value}")
        pending["qty"] = value
        user_data.pop("market_awaiting_qty_input", None)
        await market_qty_confirm(update, context)
    elif user_data.get("market_awaiting_price_input"):
        if value < 1: value = 1
        user_data["market_price"] = value
        user_data.pop("market_awaiting_price_input", None)
        await update.message.reply_text(f"✅ Preço definido: {value:,} Ouro")
        await _show_type_selection(update.message, context)

async def _show_type_selection(q, context):
    price = context.user_data.get("market_price", 0)
    text = f"💰 <b>Preço Definido:</b> {price:,} Ouro\n\nComo deseja anunciar?"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📢 Público", callback_data="mkt_finish_public"), InlineKeyboardButton("🔒 Privado (ID)", callback_data="mkt_ask_private")], [InlineKeyboardButton("⬅️ Voltar", callback_data="market_sell_menu")]])
    if hasattr(q, "edit_message_caption") or hasattr(q, "edit_message_text"): await _safe_edit(q, text, kb)
    else: await q.reply_text(text, reply_markup=kb, parse_mode="HTML")

async def market_ask_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer(); await _show_type_selection(q, context)

async def market_ask_private_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer(); context.user_data["market_awaiting_id"] = True
    text = ("🔒 <b>Venda Privada</b>\n\nEnvie o <b>Nome do Personagem</b> (ex: <i>Aragorn</i>) ou o <b>@usuario</b> do Telegram do comprador.\n<i>Você também pode encaminhar uma mensagem dele.</i>")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]])
    await _safe_edit(q, text, kb)

async def market_finalize_listing(update: Update, context: ContextTypes.DEFAULT_TYPE, target_id=None, target_name=None):
    from modules import market_manager
    user_id = get_current_player_id(update, context)
    q = update.callback_query
    pending = context.user_data.get("market_pending")
    price = context.user_data.get("market_price")

    if not pending or not price:
        msg = "⚠️ Sessão expirada. Inicie a venda novamente."
        if q: await q.answer(msg, show_alert=True)
        else: await update.effective_message.reply_text(msg)
        return

    item_removed_successfully = False
    pdata = None; item_payload = {}; seller_name = "Vendedor"; log_item_name = "Item Misterioso"; log_qty = 1

    try:
        pdata = await player_manager.get_player_data(user_id)
        seller_name = pdata.get("character_name", f"Player {user_id}")
        item_payload = {}; stock_to_create = 1
        
        if pending["type"] == "stack":
            base_id = pending["base_id"]; lot_size = pending["lot_size"]; stock = pending["qty"]
            info = _get_item_info(base_id); i_name = info.get("display_name") or base_id
            log_item_name = f"{i_name} (Lote de {lot_size})"; log_qty = stock
            total_items_to_remove = stock * lot_size 
            if player_manager.remove_item_from_inventory(pdata, base_id, total_items_to_remove):
                item_payload = {"type": "stack", "base_id": base_id, "qty": lot_size}; stock_to_create = stock
            else:
                if q: await q.answer("❌ Itens insuficientes.", show_alert=True)
                return
        elif pending["type"] == "unique":
            uid = pending["uid"]; inv = pdata.get("inventory", {})
            if uid in inv:
                item_data = inv[uid]; base_id = item_data.get("base_id")
                info = _get_item_info(base_id); i_name = item_data.get("display_name") or info.get("display_name") or base_id
                log_item_name = f"{i_name} [{str(item_data.get('rarity','comum')).upper()}]"
                del inv[uid]; item_payload = {"type": "unique", "item": item_data, "uid": uid}; item_removed_successfully = True; qty = 1 
            else:
                if q: await q.answer("❌ Item não encontrado.", show_alert=True)
                return

        await player_manager.save_player_data(user_id, pdata)
        market_manager.create_listing(seller_id=user_id, item_payload=item_payload, unit_price=price, quantity=stock_to_create, target_buyer_id=target_id, target_buyer_name=target_name, seller_name=seller_name)
        context.user_data.pop("market_pending", None); context.user_data.pop("market_awaiting_id", None); context.user_data.pop("market_price", None)
        msg_text = f"✅ <b>Anúncio Criado!</b>\n💰 {price:,} Ouro"
        if target_id: msg_text += f"\n🔒 <b>Reservado para:</b> {target_name}"
        else: msg_text += "\n📢 <b>Público</b>"
        rpg_log = (f"📜 <b>NOVA OFERTA NA PRAÇA!</b>\n\n🗣️ <b>Mercador:</b> {seller_name}\n📦 <b>Produto:</b> {log_item_name}\n🔢 <b>Estoque:</b> {stock_to_create} unidade(s)\n💰 <b>Preço:</b> {price:,} Ouro\n")
        if target_id: rpg_log += f"🔐 <b>Status:</b> Reservado para {target_name}"
        else: rpg_log += f"📢 <b>Status:</b> Disponível para todos!"
        rpg_log += f"\n\n📍 <i>Mercado de Eldora</i>"
        context.application.create_task(_send_market_log(context, rpg_log))
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🎒 Voltar", callback_data="market_adventurer")]])
        if q: await _safe_edit(q, msg_text, kb)
        else: await update.effective_message.reply_text(msg_text, reply_markup=kb, parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"ERRO CRÍTICO NA VENDA (USER {user_id}): {e}")
        if item_removed_successfully and pdata:
            try:
                if pending["type"] == "stack": inv = pdata.setdefault("inventory", {}); base_id = pending["base_id"]; qty = pending["qty"]; inv[base_id] = int(inv.get(base_id, 0)) + qty
                elif pending["type"] == "unique": uid = pending["uid"]; 
                if "item" in item_payload: pdata.setdefault("inventory", {})[uid] = item_payload["item"]
                await player_manager.save_player_data(user_id, pdata)
                err_msg = "⚠️ <b>Erro no Mercado!</b>\nO sistema detectou uma falha, mas seu item foi <b>DEVOLVIDO</b> ao inventário."
            except Exception as e_rollback: logger.critical(f"FALHA NO ROLLBACK DO JOGADOR {user_id}: {e_rollback}"); err_msg = "❌ <b>Erro Crítico!</b> Contate o suporte. (Cod: ROLLBACK_FAIL)"
        else: err_msg = "❌ Erro ao processar. Nenhum item removido."
        if q: await _safe_edit(q, err_msg, InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]]))
        else: await update.effective_message.reply_text(err_msg, parse_mode="HTML")

async def market_catch_input_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Verifica se estamos esperando um ID (Safety check)
    if not context.user_data.get("market_awaiting_id"): 
        return

    user_id = get_current_player_id(update, context)
    target_id = None
    target_name = "Desconhecido"
    text = update.message.text.strip()

    try:
        # Lógica de busca (Forward, ID Numérico ou Nome)
        if update.message.forward_from:
            # Em modo Sistema Único, forward pode não funcionar se não tivermos mapeamento
            # Mas tentamos buscar pelo ID do Telegram na coleção 'users' (caso tenha sido importado assim)
            target_id = str(update.message.forward_from.id)
            target_name = update.message.forward_from.first_name
        elif text.isdigit():
            # ID Numérico (Telegram Legacy ou novo numérico)
            target_id = text
        else:
            # Busca por nome/username
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
                    # res[0] é o ID, res[1] são os dados
                    target_id = str(res[0])
                    pdata = res[1]

            if pdata:
                target_id = str(pdata.get("user_id") or pdata.get("_id"))
                target_name = pdata.get("character_name", text)

        # --- VALIDAÇÃO FINAL DO ALVO ---
        if not target_id:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]])
            await update.message.reply_text("❌ <b>Jogador não encontrado.</b>\nTente o nome exato ou ID.", reply_markup=kb, parse_mode="HTML")
            return

        # Verifica se o alvo existe mesmo
        target_pdata = await player_manager.get_player_data(target_id)
        if not target_pdata:
             kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]])
             await update.message.reply_text("❌ <b>Jogador inválido.</b>\nID não existe no banco.", reply_markup=kb, parse_mode="HTML")
             return
             
        target_name = target_pdata.get("character_name", target_name)

        if str(target_id) == str(user_id):
            await update.message.reply_text("❌ Você não pode vender para si mesmo.")
            return

        # Se achou, finaliza
        await market_finalize_listing(update, context, target_id=target_id, target_name=target_name)

    except Exception as e:
        logger.error(f"Erro input ID: {e}")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]])
        await update.message.reply_text("❌ Erro ao buscar. Tente novamente.", reply_markup=kb)

async def market_cancel_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer("Cancelado.")
    context.user_data.pop("market_pending", None)
    await market_adventurer(update, context)

async def market_my(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    user_id = ensure_object_id(get_current_player_id(update, context))
    from modules import market_manager
    listings = market_manager.list_by_seller(user_id) # Passa ObjectId
    
    if not listings:
        msg = "👤 𝐌𝐢𝐧𝐡𝐚𝐬 𝐕𝐞𝐧𝐝𝐚𝐬 \n\n<i>Você não tem itens à venda.</i>"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]])
        await _safe_edit(q, msg, kb)
        return

    lines = ["👤 𝐌𝐢𝐧𝐡𝐚𝐬 𝐕𝐞𝐧𝐝𝐚𝐬 𝐀𝐭𝐢𝐯𝐚𝐬\n"]; rows = []
    for idx, l in enumerate(listings, start=1):
        card_text = _render_my_sale_card(idx, l)
        lines.append(card_text); lines.append("") 
        
        # Pega ID (ObjectId ou Str)
        lid = str(l.get("_id") or l.get("id"))
        rows.append([InlineKeyboardButton(f"❌ Cancelar (ID: ...{lid[-4:]})", callback_data=f"market_cancel_{lid}")])

    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])
    full_text = "\n".join(lines)
    await _safe_edit(q, full_text, InlineKeyboardMarkup(rows))

async def market_cancel_listing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try: await q.answer()
    except: pass

    # Garante que temos o ID do usuário corretamente tratado como ObjectId
    user_id = ensure_object_id(get_current_player_id(update, context))
    
    from modules import market_manager
    from bson import ObjectId

    try:
        # --- 1. PARSE DO ID (CORRIGIDO PARA OBJECTID) ---
        lid_str = q.data.replace("market_cancel_", "")
        
        # Valida se é um ObjectId válido
        if not ObjectId.is_valid(lid_str):
            await q.answer("❌ ID inválido (formato incorreto).", show_alert=True)
            return
            
        lid = ObjectId(lid_str)

        # --- 2. EXECUTA O CANCELAMENTO ---
        # Tenta cancelar (suporta manager sync ou async)
        try:
            canceled_listing = await market_manager.cancel_listing(lid)
        except TypeError:
            # Fallback caso o manager não seja async
            canceled_listing = market_manager.cancel_listing(lid)

        if canceled_listing:
            # Prepara dados para o Log
            seller_name = canceled_listing.get("seller_name", "Mercador")
            item_payload = canceled_listing.get("item", {})
            qty_returned = canceled_listing.get("quantity", 0)
            
            item_display_name = "Item"
            if item_payload.get("type") == "stack":
                base_id = item_payload.get("base_id")
                info = _get_item_info(base_id)
                item_display_name = f"{info.get('display_name') or base_id}"
            elif item_payload.get("type") == "unique":
                inst = item_payload.get("item", {})
                item_display_name = inst.get("display_name") or "Equipamento"

            # Log RPG Bonito
            rpg_log_text = (
                f"🚫 <b>OFERTA RETIRADA!</b>\n\n"
                f"🗣️ <b>Mercador:</b> {seller_name}\n"
                f"📦 <b>Recolheu:</b> {item_display_name}\n"
                f"🔙 <b>Estoque Devolvido:</b> {qty_returned} lote(s)"
            )
            
            # Envia o log em background
            context.application.create_task(_send_market_log(context, rpg_log_text))
            
            try: await q.answer("✅ Anúncio removido!", show_alert=True)
            except: pass
            
            # Atualiza a lista de 'Minhas Vendas'
            await market_my(update, context)
        else:
            await q.answer("❌ Oferta não encontrada ou já vendida.", show_alert=True)
            await market_my(update, context)

    except Exception as e:
        logger.error(f"Erro ao cancelar venda (User {user_id}): {e}")
        try: await q.answer(f"Erro: {str(e)}", show_alert=True)
        except: pass
        
async def market_start_input_triggers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer(); data = q.data
    msg = ""
    if "size" in data: context.user_data["market_awaiting_size_input"] = True; msg = "o TAMANHO DO LOTE (itens por pacote)"
    elif "qty" in data: context.user_data["market_awaiting_qty_input"] = True; msg = "a QUANTIDADE de lotes"
    elif "price" in data: context.user_data["market_awaiting_price_input"] = True; msg = "o PREÇO TOTAL"
    try: await q.edit_message_caption(f"⌨️ <b>MODO DE TEXTO</b>\n\nDigite {msg} no chat agora:")
    except: await q.message.reply_text(f"⌨️ <b>MODO DE TEXTO</b>\n\nDigite {msg} no chat agora:", parse_mode="HTML")

async def market_input_handlers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ud = context.user_data; text = update.message.text.strip()
    if ud.get("market_awaiting_size_input"):
        await market_process_size_input(update, context)
    elif ud.get("market_awaiting_qty_input") or ud.get("market_awaiting_price_input"):
        await market_process_text_input(update, context)
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
    await update.message.reply_text(f"✅ Tamanho do lote: {val}")
    await market_lot_size_confirm(update, context)

async def _safe_edit(query, text, kb):
    if hasattr(query, "edit_message_caption"):
        try: await query.edit_message_caption(caption=text, reply_markup=kb, parse_mode='HTML'); return
        except: pass
        try: await query.edit_message_text(text=text, reply_markup=kb, parse_mode='HTML'); return
        except: pass
    if hasattr(query, "reply_text"):
        await query.reply_text(text, reply_markup=kb, parse_mode='HTML'); return
    try: await query.message.reply_text(text, reply_markup=kb, parse_mode='HTML')
    except: pass

market_open_handler = CallbackQueryHandler(market_open, pattern=r'^market$')
market_adventurer_handler = CallbackQueryHandler(market_adventurer, pattern=r'^market_adventurer$')
market_list_handler = CallbackQueryHandler(market_list, pattern=r'^market_list')
market_buy_handler = CallbackQueryHandler(market_buy, pattern=r'^market_buy_')
market_sell_menu_handler = CallbackQueryHandler(market_sell_menu, pattern=r'^market_sell_menu$')
market_sell_cat_handler = CallbackQueryHandler(market_sell_list_category, pattern=r'^market_sell_cat:')
market_pick_unique_handler = CallbackQueryHandler(market_pick_unique, pattern=r'^market_pick_unique_')
market_pick_stack_handler = CallbackQueryHandler(market_pick_stack, pattern=r'^market_pick_stack_')
market_size_spin_handler = CallbackQueryHandler(market_lot_size_spin, pattern=r'^mkt_size_(inc|dec|max)')
market_size_confirm_handler = CallbackQueryHandler(market_lot_size_confirm, pattern=r'^mkt_size_confirm$')
market_pack_spin_handler = CallbackQueryHandler(market_qty_spin, pattern=r'^mkt_pack_(inc|dec|max)')
market_pack_confirm_handler = CallbackQueryHandler(market_qty_confirm, pattern=r'^mkt_pack_confirm$')
market_price_spin_handler = CallbackQueryHandler(market_price_spin, pattern=r'^mktp_(inc|dec)')
market_price_confirm_handler = CallbackQueryHandler(market_ask_type, pattern=r'^mktp_confirm$')
market_finish_public_handler = CallbackQueryHandler(market_finalize_listing, pattern=r'^mkt_finish_public$')
market_ask_private_handler = CallbackQueryHandler(market_ask_private_id, pattern=r'^mkt_ask_private$')
market_cancel_new_handler = CallbackQueryHandler(market_cancel_new, pattern=r'^market_cancel_new$')
market_my_handler = CallbackQueryHandler(market_my, pattern=r'^market_my$')
market_cancel_listing_handler = CallbackQueryHandler(market_cancel_listing, pattern=r'^market_cancel_.*')
market_input_triggers_handler = CallbackQueryHandler(market_start_input_triggers, pattern=r'^mkt_input_.*')
market_text_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, market_input_handlers)
market_input_id_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, market_input_handlers)