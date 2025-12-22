# handlers/gem_market_handler.py
# (VERSÃO 4.2 - COM LOG DE VENDAS NO GRUPO)

import logging
import math
import html
from typing import List, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

# --- Nossos Módulos ---
from modules import player_manager, game_data, file_ids
from modules import gem_market_manager # O "Backend"
from modules.game_data.skins import SKIN_CATALOG
from modules.game_data import skills as skills_data
from modules import market_utils

logger = logging.getLogger(__name__)

# ==============================
#  CONFIGURAÇÃO DE LOGS (Adicionado)
# ==============================
LOG_GROUP_ID = -1002881364171
LOG_TOPIC_ID = 24475

# ==============================
#  LISTAS DE ITENS VENDÁVEIS
# ==============================

# ==============================
#  LISTAS DE ITENS VENDÁVEIS (DINÂMICAS)
# ==============================

# 1. Carrega todos os dados de itens do jogo
_ALL_GAME_ITEMS = getattr(game_data, "ITEMS_DATA", {})

# 2. Gera lista de Itens de Evolução (Procura por type="evo_item")
EVOLUTION_ITEMS: set[str] = {
    item_id for item_id, data in _ALL_GAME_ITEMS.items() 
    if data.get("type") == "evo_item"
}

# 3. Gera lista de Skills (Pega chaves do SKILL_DATA e adiciona "tomo_")
SKILL_BOOK_ITEMS: set[str] = {
    f"tomo_{skill_id}" for skill_id in skills_data.SKILL_DATA.keys()
}

# 4. Gera lista de Caixas de Skin (Pega chaves do SKIN_CATALOG e adiciona "caixa_")
SKIN_BOX_ITEMS: set[str] = {
    f"caixa_{skin_id}" for skin_id in SKIN_CATALOG.keys()
}

# ==============================
#  MAPEAMENTOS (DINÂMICOS)
# ==============================

# Gera o mapa de Evolução por Classe automaticamente
# Ele lê o atributo 'class_req' ou 'class' dentro do item de evolução
EVO_ITEMS_BY_CLASS_MAP: Dict[str, set] = {}

for evo_id in EVOLUTION_ITEMS:
    info = _ALL_GAME_ITEMS.get(evo_id, {})
    # Tenta achar qual classe usa esse item
    req_class = info.get("class_req") or info.get("class") or info.get("allowed_classes")
    
    if req_class:
        # Se for uma lista de classes (ex: ['mago', 'bruxo']), pega a primeira ou itera
        if isinstance(req_class, list):
            for c in req_class:
                c_norm = c.lower()
                if c_norm not in EVO_ITEMS_BY_CLASS_MAP:
                    EVO_ITEMS_BY_CLASS_MAP[c_norm] = set()
                EVO_ITEMS_BY_CLASS_MAP[c_norm].add(evo_id)
        elif isinstance(req_class, str):
            c_norm = req_class.lower()
            if c_norm not in EVO_ITEMS_BY_CLASS_MAP:
                EVO_ITEMS_BY_CLASS_MAP[c_norm] = set()
            EVO_ITEMS_BY_CLASS_MAP[c_norm].add(evo_id)

# Mapeamento estático apenas para exibição (Labels)
CLASSES_MAP = {
    "guerreiro": "⚔️ Guerreiro",
    "mago": "✨ Mago",
    "berserker": "🪓 Berserker",
    "cacador": "🏹 Caçador",
    "assassino": "🗡️ Assassino",
    "bardo": "🎵 Bardo",
    "monge": "🧘 Monge",
    "samurai": "🥷 Samurai",
}

# ==============================
#  Utils (Helpers)
# ==============================

def _get_item_info(base_id: str) -> dict:
    try:
        info = game_data.get_item_info(base_id)
        if info: return dict(info)
    except Exception: pass
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

def _item_label(base_id: str) -> str:
    info = _get_item_info(base_id)
    if base_id in SKILL_BOOK_ITEMS: emoji = "📚"
    elif base_id in SKIN_BOX_ITEMS: emoji = "🎨"
    elif base_id in EVOLUTION_ITEMS: emoji = "✨"
    else: emoji = info.get("emoji", "💎")
    name = info.get("display_name", base_id)
    return f"{emoji} {name}"

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except Exception as e:
        if "message is not modified" in str(e).lower():
            return
        pass
    
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except Exception as e:
        if "message is not modified" in str(e).lower():
            return
        pass
    
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

async def _send_with_media(chat_id: int, context: ContextTypes.DEFAULT_TYPE, caption: str, kb: InlineKeyboardMarkup, media_keys: List[str]):
    for key in media_keys:
        fd = file_ids.get_file_data(key)
        if fd and fd.get("id"):
            fid, ftype = fd["id"], fd.get("type")
            try:
                if ftype == "video":
                    await context.bot.send_video(chat_id=chat_id, video=fid, caption=caption, reply_markup=kb, parse_mode="HTML")
                else:
                    await context.bot.send_photo(chat_id=chat_id, photo=fid, caption=caption, reply_markup=kb, parse_mode="HTML")
                return
            except Exception:
                continue
    await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=kb, parse_mode="HTML")

# ==============================
#  Menu Principal (Ponto de Entrada)
# ==============================

async def gem_market_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id

    text = (
        "🏛️ <b>𝐂𝐨𝐦𝐞́𝐫𝐜𝐢𝐨 𝐝𝐞 𝐑𝐞𝐥𝐢́𝐪𝐮𝐢𝐚𝐬 ✨</b>\n\n"
        "Bem-vindo! Aqui podes negociar itens raros (Evolução, Skills, Skins) "
        "com outros aventureiros usando <b>Diamantes</b> (💎)."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Ver Listagens (Comprar)", callback_data="gem_list_cats")],
        [InlineKeyboardButton("➕ Vender Item", callback_data="gem_sell_cats")],
        [InlineKeyboardButton("👤 Minhas Listagens", callback_data="gem_market_my")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market")],
    ])

    keys = ["mercado_gemas", "img_mercado_gemas", "gem_market", "gem_shop", "casa_leiloes"]
    try: await q.delete_message()
    except Exception: pass
    await _send_with_media(chat_id, context, text, kb, keys)

# ==============================
#  Seleção de Classe (Genérico)
# ==============================

def _build_class_picker_keyboard(callback_prefix: str, back_callback: str) -> InlineKeyboardMarkup:
    """Cria o teclado de 8 classes para compra ou venda."""
    kb = []
    row = []
    for class_key, class_label in CLASSES_MAP.items():
        row.append(InlineKeyboardButton(class_label, callback_data=f"{callback_prefix}:{class_key}:1"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
        
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data=back_callback)])
    return InlineKeyboardMarkup(kb)

# ==============================
#  Fluxo de Venda (Sell Flow)
# ==============================

async def show_sell_category_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra as 3 categorias de itens para VENDER."""
    q = update.callback_query
    await q.answer()
    
    text = "➕ <b>Vender Item</b>\n\nQue tipo de item premium desejas vender?"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Itens de Evolução", callback_data="gem_sell_filter:evo")],
        [InlineKeyboardButton("📚 Tomos de Skill", callback_data="gem_sell_filter:skill")],
        [InlineKeyboardButton("🎨 Caixas de Skin", callback_data="gem_sell_filter:skin")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")],
    ])
    await _safe_edit_or_send(q, context, q.message.chat_id, text, kb)

async def show_sell_class_picker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o seletor de classe para VENDER evo, skins ou skills."""
    q = update.callback_query
    await q.answer()
    
    try:
        item_type = q.data.split(":")[1] # 'evo', 'skill' ou 'skin'
    except IndexError:
        return 

    if item_type == "skill":
        text = "📚 <b>Vender Tomos de Skill</b>\n\nDe qual classe é a skill que queres vender?"
        callback_prefix = "gem_sell_class:skill"
    elif item_type == "skin":
        text = "🎨 <b>Vender Caixas de Skin</b>\n\nDe qual classe é a skin que queres vender?"
        callback_prefix = "gem_sell_class:skin"
    else: # evo
        text = "✨ <b>Vender Itens de Evolução</b>\n\nPara qual classe é o item que queres vender?"
        callback_prefix = "gem_sell_class:evo"
        
    kb = _build_class_picker_keyboard(callback_prefix, back_callback="gem_sell_cats")
    await _safe_edit_or_send(q, context, q.message.chat_id, text, kb)

async def show_sell_items_filtered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a lista de itens de Venda, filtrada por classe E categoria."""
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = q.message.chat_id

    parts = q.data.split(":")
    
    try:
        item_type = parts[1] # skill, skin, evo
        class_key = parts[2] # guerreiro, mago...
        page = int(parts[3])
    except (IndexError, ValueError):
        await q.answer("Erro de callback.", show_alert=True); return

    pdata = await player_manager.get_player_data(user_id) or {}
    inv = pdata.get("inventory", {}) or {}

    sellable_items = []
    
    # --- CORREÇÃO: Varre o inventário detectando STACKS e ITENS ÚNICOS ---
    for key, val in inv.items():
        base_id = None
        qty_have = 0

        # Caso 1: Stack simples (Ex: "essencia_furia": 10)
        if isinstance(val, (int, float)):
            if val > 0:
                base_id = key
                qty_have = int(val)
        
        # Caso 2: Item Único (Ex: "uid_123": {"base_id": "tomo_..."})
        elif isinstance(val, dict):
            base_id = val.get("base_id") or val.get("tpl")
            qty_have = 1 # Itens únicos contam como 1 unidade
            
        if not base_id or qty_have <= 0:
            continue
            
        # Filtros de Categoria e Classe
        item_class_ok = False
        
        if item_type == "evo" and base_id in EVOLUTION_ITEMS:
            if base_id in EVO_ITEMS_BY_CLASS_MAP.get(class_key, set()):
                item_class_ok = True
        
        elif item_type == "skill" and base_id in SKILL_BOOK_ITEMS:
            # Remove prefixo se necessário para checar skill data
            skill_id = base_id.replace("tomo_", "")
            allowed = skills_data.SKILL_DATA.get(skill_id, {}).get("allowed_classes", [])
            if class_key in allowed: 
                item_class_ok = True
        
        elif item_type == "skin":
            if base_id.startswith("caixa_"):
                skin_id = base_id.replace("caixa_", "")
                
                if SKIN_CATALOG.get(skin_id):
                    item_class_ok = True
            #allowed = SKIN_CATALOG.get(skin_id, {}).get("class")
            #if class_key == allowed: 
                #item_class_ok = True
        
        if item_class_ok:
            # Verifica se já não adicionamos esse base_id (para agrupar itens únicos iguais)
            found = False
            for it in sellable_items:
                if it["base_id"] == base_id:
                    it["qty_have"] += qty_have
                    it["label"] = f"{_item_label(base_id)} (x{it['qty_have']})"
                    found = True
                    break
            
            if not found:
                sellable_items.append({
                    "base_id": base_id, 
                    "qty_have": qty_have,
                    "label": f"{_item_label(base_id)} (x{qty_have})"
                })
            
    sellable_items.sort(key=lambda x: x["label"])

    # Paginação
    ITEMS_PER_PAGE = 8
    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    items_for_page = sellable_items[start_index:end_index]
    total_pages = max(1, math.ceil(len(sellable_items) / ITEMS_PER_PAGE))
    page = min(page, total_pages)

    title = f"{CLASSES_MAP.get(class_key, class_key).split(' ')[1]}"
    caption = f"💎 <b>Vender: {title}</b> (Pág. {page}/{total_pages})\nSelecione um item para vender:\n"
    keyboard_rows = []

    if not sellable_items:
        caption += f"\n<i>Você não possui itens de '{item_type}' para a classe '{title}' no inventário.</i>"
    elif not items_for_page:
        caption += "\n<i>Não há mais itens para mostrar.</i>"
    else:
        for item in items_for_page:
            callback_data = f"gem_sell_item_{item['base_id']}"
            keyboard_rows.append([InlineKeyboardButton(item["label"], callback_data=callback_data)])
            
    nav_buttons = []
    back_cb = f"gem_sell_filter:{item_type}" 

    if page > 1:
        cb = f"gem_sell_class:{item_type}:{class_key}:{page-1}"
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=cb))
        
    nav_buttons.append(InlineKeyboardButton("⬅️ Voltar", callback_data=back_cb))

    if end_index < len(sellable_items):
        cb = f"gem_sell_class:{item_type}:{class_key}:{page+1}"
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=cb))
        
    keyboard_rows.append(nav_buttons)
    await _safe_edit_or_send(q, context, chat_id, caption, InlineKeyboardMarkup(keyboard_rows))
    
# ==============================
#  Fluxo de Compra (Buy Flow)
# ==============================

async def show_buy_category_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    text = "📦 <b>Ver Listagens</b>\n\nQue tipo de item premium procuras?"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Itens de Evolução", callback_data="gem_list_filter:evo")],
        [InlineKeyboardButton("📚 Tomos de Skill", callback_data="gem_list_filter:skill")],
        [InlineKeyboardButton("🎨 Caixas de Skin", callback_data="gem_list_filter:skin")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")],
    ])
    await _safe_edit_or_send(q, context, q.message.chat_id, text, kb)

async def show_buy_class_picker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    try:
        item_type = q.data.split(":")[1] # 'evo', 'skill' ou 'skin'
    except IndexError:
        return

    if item_type == "skill":
        text = "📚 <b>Comprar Tomos de Skill</b>\n\nProcurando skills para qual classe?"
        callback_prefix = "gem_list_class:skill"
    elif item_type == "skin":
        text = "🎨 <b>Comprar Caixas de Skin</b>\n\nProcurando skins para qual classe?"
        callback_prefix = "gem_list_class:skin"
    else: # evo
        text = "✨ <b>Comprar Itens de Evolução</b>\n\nProcurando itens para qual classe?"
        callback_prefix = "gem_list_class:evo"
        
    kb = _build_class_picker_keyboard(callback_prefix, back_callback="gem_list_cats")
    await _safe_edit_or_send(q, context, q.message.chat_id, text, kb)

async def show_buy_items_filtered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra as listagens de Compra, filtradas por categoria E classe."""
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = q.message.chat_id

    # ⚠️ CORREÇÃO CRÍTICA: Limpa o cache do jogador antes de carregar as listagens.
    # Isso resolve problemas onde a listagem recém-criada não é visível devido a dados de sessão antigos.
    await player_manager.clear_player_cache(user_id) 

    parts = q.data.split(":")
    
    try:
        item_type_filter = parts[1] # evo, skill, skin
        class_key_filter = parts[2] # guerreiro, mago...
        page = int(parts[3])
    except (IndexError, ValueError):
        await q.answer("Erro de callback.", show_alert=True); return

    pdata = await player_manager.get_player_data(user_id)
    gems = player_manager.get_gems(pdata)

    # Assume list_active() está no gem_market_manager, conforme o restante do arquivo
    all_listings = gem_market_manager.list_active(page=1, page_size=500)
    
    # Adicionar o filtro defensivo após a migração para MongoDB
    if all_listings is None:
        all_listings = []
        
    filtered_listings = []
    
    # ⚠️ NORMALIZAÇÃO CRÍTICA: Garante que a chave do filtro esteja limpa
    normalized_filter_class = class_key_filter.strip().lower()

    for l in all_listings:
        item_payload = l.get("item", {})
        # item_type = item_payload.get("type") # IGNORADO
        base_id = item_payload.get("base_id")

        if not base_id:
            continue
            
        item_class_ok = False

        # --- FILTRO 1: ITENS DE EVOLUÇÃO (EVO) ---
        # Mantém a verificação de tipo "evo_item", pois é a mais limpa.
        if item_type_filter == "evo" and item_payload.get("type") == "evo_item": 
            if base_id in EVO_ITEMS_BY_CLASS_MAP.get(normalized_filter_class, set()):
                item_class_ok = True
        
        # --- FILTRO 2: SKILLS (TOMOS) ---
        # Item é elegível se tiver prefixo tomo_ E o skill_id permitir a classe_key
        elif item_type_filter == "skill" and base_id.startswith("tomo_"):
            skill_id = base_id.replace("tomo_", "")
            # Assume skills_data está importado (modules.game_data.skills)
            allowed = skills_data.SKILL_DATA.get(skill_id, {}).get("allowed_classes", [])
            if normalized_filter_class in allowed: 
                item_class_ok = True
        
        
        # --- FILTRO 3: SKINS (CAIXAS) ---
        elif item_type_filter == "skin":
            
            item_type_on_listing = item_payload.get("type")
            # Usa "item_stack" como fallback para listagens antigas que não definiram o tipo
            if item_type_on_listing not in ("skin", "item_stack"):
                continue

            # Tenta encontrar a classe do item com ou sem o prefixo 'caixa_'
            skin_id_clean = base_id.replace("caixa_", "")
            
            # Tenta encontrar a classe no catálogo com o ID limpo
            allowed_class = SKIN_CATALOG.get(skin_id_clean, {}).get("class")
            
            # Compara a classe limpa do filtro com a classe do catálogo
            if allowed_class and normalized_filter_class == allowed_class: 
                item_class_ok = True
        
        if item_class_ok:
            filtered_listings.append(l)

    ITEMS_PER_PAGE = 10
    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    items_on_page = filtered_listings[start_index:end_index]
    total_pages = max(1, math.ceil(len(filtered_listings) / ITEMS_PER_PAGE))
    page = min(page, total_pages)

    title = f"{CLASSES_MAP.get(normalized_filter_class, normalized_filter_class).split(' ')[1]}"
    lines = [f"🏛️ <b>Listagens: {title}</b> (Pág. {page}/{total_pages})\nVocê tem <b>💎 {gems}</b>\n"]
    kb_rows = []

    if not items_on_page and page == 1:
        lines.append(f"<i>Nenhuma listagem de '{item_type_filter}' encontrada para esta classe.</i>")
    
    for l in items_on_page:
        lines.append(_render_listing_line(l))
        if int(l.get("seller_id", 0)) != user_id:
            back_cb_data = f":{item_type_filter}:{class_key_filter}:{page}"
            kb_rows.append([InlineKeyboardButton(f"Comprar [#{l['id']}]", callback_data=f"gem_buy_confirm{back_cb_data}:{l['id']}")])

    nav_buttons = []
    back_cb = f"gem_list_filter:{item_type_filter}"
    page_cb_base = f"gem_list_class:{item_type_filter}:{class_key_filter}"

    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"{page_cb_base}:{page - 1}"))
    
    nav_buttons.append(InlineKeyboardButton("⬅️ Voltar", callback_data=back_cb))
    
    if end_index < len(filtered_listings):
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"{page_cb_base}:{page + 1}"))
        
    kb_rows.append(nav_buttons)
    await _safe_edit_or_send(q, context, chat_id, "\n".join(lines), InlineKeyboardMarkup(kb_rows))

# ==============================
#  SPINNERS E FUNÇÕES DE FINALIZAÇÃO
# ==============================


async def gem_market_price_spin(update, context):
    q = update.callback_query; await q.answer()
    chat_id = update.effective_chat.id
    
    # MUDANÇA AQUI: Usa a função de cálculo centralizada
    cur = market_utils.calculate_spin_value(
        current_value=context.user_data.get("gem_market_price", market_utils.MIN_GEM_PRICE),
        action_data=q.data,
        prefix_inc="gem_p_inc_",
        prefix_dec="gem_p_dec_",
        min_value=market_utils.MIN_GEM_PRICE # Usa a constante de Gemas
    )
    
    context.user_data["gem_market_price"] = cur
    
    pending = context.user_data.get("gem_market_pending")
    if not pending:
        await gem_market_cancel_new(update, context); return
        
    item_label = _item_label(pending["base_id"])
    pack_qty = int(pending.get("qty", 1))
    lote_qty = int(context.user_data.get("gem_market_lotes", 1))

    caption = (
        f"Item: <b>{item_label} ×{pack_qty}</b>\n"
        f"Lotes: <b>{lote_qty}</b>\n\n"
        f"Defina o <b>preço por lote</b> (Mínimo: 10 💎):"
    )
    kb = market_utils.render_spinner_kb(
        value=cur,
        prefix_inc="gem_p_inc_",
        prefix_dec="gem_p_dec_",
        label="Preço por lote",
        confirm_cb="gem_p_confirm",
        currency_emoji="💎",
        allow_large_steps=False # Não precisamos de passos grandes de 1k/5k para gemas
    )
    await _safe_edit_or_send(q, context, chat_id, f"{caption} <b>💎 {cur}</b>", kb)

async def gem_market_price_confirm(update, context):
    q = update.callback_query
    # AQUI: Se por algum milagre o valor for menor que 10, força subir para 10
    price = max(10, int(context.user_data.get("gem_market_price", 10)))
    
    # Validação visual (opcional, mas bom pra feedback)
    if price < 10:
        await q.answer("O preço mínimo é 10 Gemas!", show_alert=True)
        return

    await q.answer()
    await gem_market_finalize_listing(update, context, price)

async def _show_gem_lote_spinner(q, context, chat_id: int):
    pending = context.user_data.get("gem_market_pending")
    if not pending or pending.get("type") != "item_stack":
        await gem_market_cancel_new(q, context); return

    qty_have = int(pending.get("qty_have", 0))
    pack_qty = int(pending.get("qty", 1))
    
    max_lotes = max(1, qty_have // pack_qty)
    context.user_data["gem_market_lote_max"] = max_lotes
    
    current_lotes = max(1, int(context.user_data.get("gem_market_lotes", 1)))
    current_lotes = min(current_lotes, max_lotes)
    context.user_data["gem_market_lotes"] = current_lotes

    kb = market_utils.render_spinner_kb(
        value=current_lotes, 
        prefix_inc="gem_lote_inc_", 
        prefix_dec="gem_lote_dec_", 
        label=f"📦 {current_lotes} / {max_lotes} Lotes", # Ajusta o label para incluir a info Max/Cur
        confirm_cb="gem_lote_confirm",
        allow_large_steps=False
    )
    
    item_label = _item_label(pending["base_id"])
    caption = (
        f"Item: <b>{item_label} ×{pack_qty}</b> (Você tem {qty_have} no total)\n\n"
        f"Defina a <b>quantidade de lotes</b> que deseja vender:"
    )
    
    await _safe_edit_or_send(q, context, chat_id, caption, kb)

async def gem_market_lote_spin(update, context):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id

    # CORREÇÃO: Carregar o valor máximo de lotes (que foi definido em _show_gem_lote_spinner)
    max_qty = max(1, int(context.user_data.get("gem_market_lote_max", 1))) 

    cur = market_utils.calculate_spin_value(
        current_value=context.user_data.get("gem_market_lotes", 1),
        action_data=q.data,
        prefix_inc="gem_lote_inc_",
        prefix_dec="gem_lote_dec_",
        min_value=1,
        max_value=max_qty # Agora max_qty está definido
    )
    
    context.user_data["gem_market_lotes"] = cur
    await _show_gem_lote_spinner(q, context, chat_id)

async def gem_market_lote_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    
    # Inicializa o preço mínimo para 10 (constante em market_utils)
    context.user_data["gem_market_price"] = market_utils.MIN_GEM_PRICE 
    
    pending = context.user_data.get("gem_market_pending")
    item_label = _item_label(pending["base_id"])
    pack_qty = int(pending.get("qty", 1))
    lote_qty = int(context.user_data.get("gem_market_lotes", 1))

    caption_prefix = (
        f"Item: <b>{item_label} ×{pack_qty}</b>\n"
        f"Lotes: <b>{lote_qty}</b>\n\n"
        f"Defina o <b>preço por lote</b> (em Diamantes):"
    )
    
    price = context.user_data["gem_market_price"]
    
    # CORREÇÃO AQUI: Usa a função genérica de renderização
    kb = market_utils.render_spinner_kb(
        value=price, 
        prefix_inc="gem_p_inc_", 
        prefix_dec="gem_p_dec_", 
        label="Preço por lote", 
        confirm_cb="gem_p_confirm",
        currency_emoji="💎",
        allow_large_steps=False # Não permite passos de 1k/5k para gemas
    )
    
    await _safe_edit_or_send(q, context, chat_id, f"{caption_prefix} <b>💎 {price}</b>", kb)

async def _show_gem_pack_spinner(q, context, chat_id: int):
    pending = context.user_data.get("gem_market_pending")
    if not pending or pending.get("type") != "item_stack":
        await gem_market_cancel_new(q, context); return

    qty_have = int(pending.get("qty_have", 0))
    current_pack_qty = max(1, int(pending.get("qty", 1)))
    current_pack_qty = min(current_pack_qty, qty_have)
    
    pending["qty"] = current_pack_qty
    context.user_data["gem_market_pending"] = pending

    kb = market_utils.render_spinner_kb(
        value=current_pack_qty, 
        prefix_inc="gem_pack_inc_", 
        prefix_dec="gem_pack_dec_", 
        label=f"📦 {current_pack_qty} / {qty_have} Itens",
        confirm_cb="gem_pack_confirm",
        allow_large_steps=False
    )
    
    item_label = _item_label(pending["base_id"])
    caption = (
        f"Item: <b>{item_label}</b> (Você tem {qty_have} no total)\n\n"
        f"Defina quantos itens vão em <b>cada lote</b>:"
    )
    
    await _safe_edit_or_send(q, context, chat_id, caption, kb)

async def gem_market_pack_spin(update, context):
    q = update.callback_query; await q.answer()
    # CORREÇÃO: Define chat_id explicitamente
    chat_id = update.effective_chat.id 
    
    pending = context.user_data.get("gem_market_pending")
    if not pending: await gem_market_cancel_new(update, context); return
    
    max_qty = max(1, int(pending.get("qty_have", 1)))
    
    # MUDANÇA AQUI: Usa a função de cálculo centralizada
    cur = market_utils.calculate_spin_value(
        current_value=pending.get("qty", 1),
        action_data=q.data,
        prefix_inc="gem_pack_inc_",
        prefix_dec="gem_pack_dec_",
        min_value=1,
        max_value=max_qty
    )
        
    pending["qty"] = cur
    context.user_data["gem_market_pending"] = pending
    
    # CORREÇÃO: Agora chat_id está definido
    await _show_gem_pack_spinner(q, context, chat_id)

async def gem_market_pack_confirm(update, context):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    context.user_data["gem_market_lotes"] = 1
    await _show_gem_lote_spinner(q, context, chat_id)

async def gem_market_pick_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Jogador selecionou um item (Evo, Skill ou Skin) para vender."""
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id
    
    base_id = q.data.replace("gem_sell_item_", "")
    
    pdata = await player_manager.get_player_data(user_id)
    
    if not pdata:
        logger.warning(f"[GemMarket] Falha ao carregar pdata para {user_id} em gem_market_pick_item.")
        await q.answer("Erro: Não foi possível carregar os seus dados. Tente novamente.", show_alert=True)
        try:
            await gem_market_main(update, context) 
        except Exception:
            pass 
        return

    inv = pdata.get("inventory", {}) or {}
    qty_have = int(inv.get(base_id, 0))
    
    if qty_have <= 0:
        await q.answer("Você não tem mais esse item.", show_alert=True)
        try:
            await gem_market_main(update, context) 
        except Exception:
            pass
        return

    context.user_data["gem_market_pending"] = {
        "type": "item_stack", 
        "base_id": base_id, 
        "qty_have": qty_have,
        "qty": 1  
    }
    
    await _show_gem_pack_spinner(q, context, chat_id)

async def gem_market_cancel_new(update, context):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    
    context.user_data.pop("gem_market_pending", None)
    context.user_data.pop("gem_market_price", None)
    context.user_data.pop("gem_market_lotes", None)
    context.user_data.pop("gem_market_lote_max", None)
    
    await _safe_edit_or_send(q, context, chat_id, "Criação de listagem cancelada.", InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")]
    ]))

async def gem_market_finalize_listing(update: Update, context: ContextTypes.DEFAULT_TYPE, price_gems: int):
    q = update.callback_query
    user_id = q.from_user.id
    chat_id = q.message.chat_id

    pending = context.user_data.get("gem_market_pending")
    if not pending or pending.get("type") != "item_stack":
        await q.answer("Erro: Estado de venda inválido. Tente novamente.", show_alert=True)
        await gem_market_cancel_new(update, context)
        return
        
    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        await q.answer("Erro ao carregar seus dados.", show_alert=True)
        return

    # Usamos o base_id original do pending, que pode ser 'caixa_monge_...'
    base_id_original = pending["base_id"]
    base_id_to_save = base_id_original # Inicializa com o original
    
    pack_qty = int(pending.get("qty", 1))
    lote_qty = max(1, int(context.user_data.get("gem_market_lotes", 1)))
    total_to_remove = pack_qty * lote_qty
    item_label = _item_label(base_id_original) 

    if not player_manager.has_item(pdata, base_id_original, total_to_remove):
        await q.answer(f"Você não tem {total_to_remove}x {item_label}.", show_alert=True)
        await gem_market_cancel_new(update, context)
        return

    # Remove o item original (ex: caixa_monge_aspecto_asura) do inventário
    player_manager.remove_item_from_inventory(pdata, base_id_original, total_to_remove)
    await player_manager.save_player_data(user_id, pdata)
    
    # --- LÓGICA CORRIGIDA: Forçar o item.type correto E limpar o base_id ---
    item_type_for_backend = "item_stack" 
    
    # 1. VERIFICAÇÃO DE SKIN (Prioridade: caixas devem ser 'skin')
    if base_id_original.startswith("caixa_"):
        item_type_for_backend = "skin"
        # ⚠️ CORREÇÃO AQUI: Remove o prefixo 'caixa_' para que o filtro de compra funcione
        # Salva apenas o ID da skin para consulta no catálogo (monge_aspecto_asura)
        base_id_to_save = base_id_original.replace("caixa_", "")
        
    # 2. VERIFICAÇÃO DE SKILL
    elif base_id_original.startswith("tomo_") and base_id_original in SKILL_BOOK_ITEMS:
        item_type_for_backend = "skill"
        
        # --- CORREÇÃO: Remove o prefixo 'tomo_' para salvar limpo no banco ---
        base_id_to_save = base_id_original.replace("tomo_", "")
        
    # 3. VERIFICAÇÃO DE EVO
    elif base_id_original in EVOLUTION_ITEMS:
        item_type_for_backend = "evo_item"
    
    # Se não cair em nenhum dos 'if/elif', item_type_for_backend permanece 'item_stack'
    
    item_payload = {
        "type": item_type_for_backend, 
        "base_id": base_id_to_save, # <--- Usa o ID limpo para skins (ex: monge_aspecto_asura)
        "qty": pack_qty
    }
    # --- FIM DA LÓGICA CORRIGIDA ---

    try:
        listing = gem_market_manager.create_listing(
            seller_id=user_id,
            item_payload=item_payload,
            unit_price=price_gems,
            quantity=lote_qty
        )
    except Exception as e:
        logger.error(f"[GemMarket] Falha ao criar listagem para {user_id}: {e}", exc_info=True)
        
        # Lógica de devolução de item (devolve o item original: base_id_original)
        player_manager.add_item_to_inventory(pdata, base_id_original, total_to_remove)
        await player_manager.save_player_data(user_id, pdata)
        
        # CORREÇÃO: Escapar a mensagem de erro antes de enviar
        safe_error_text = html.escape(str(e))
        
        await _safe_edit_or_send(q, context, chat_id, f"⚠️ Ocorreu um erro: {safe_error_text}\nSeus itens foram devolvidos.", InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")]
        ]))
        return
        
    
    context.user_data.pop("gem_market_pending", None)
    context.user_data.pop("gem_market_price", None)
    context.user_data.pop("gem_market_lotes", None)
    context.user_data.pop("gem_market_lote_max", None)
    
    text = f"✅ Listagem #{listing['id']} criada!\n\n{lote_qty}x lote(s) de {item_label} (x{pack_qty}) por 💎 {price_gems} cada."
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Minhas Listagens", callback_data="gem_market_my")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")]
    ])
    await _safe_edit_or_send(q, context, chat_id, text, kb)

def _render_listing_line(listing: dict) -> str:
    item = listing.get("item", {})
    price = listing.get("unit_price_gems", 0)
    lotes = listing.get("quantity", 1)
    lid = listing.get("id")
    
    base_id = item.get("base_id")
    pack_qty = item.get("qty", 1)
    label = _item_label(base_id) 
    
    return f"• {label} (x{pack_qty}) — <b>💎 {price}</b> (Lotes: {lotes}) [#{lid}]"

async def gem_market_buy_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    
    try:
        parts = q.data.split(":") 
        lid = int(parts[-1])
        filter_parts = ":".join(parts[1:-1]) 
        
        if filter_parts:
            back_cb = f"gem_list_class:{filter_parts}"
        else:
            back_cb = "gem_list_cats"
            
    except (IndexError, ValueError):
        await q.answer("ID ou callback inválido.", show_alert=True); return

    listing = gem_market_manager.get_listing(lid)
    if not listing or not listing.get("active"):
        await q.answer("Esta listagem não está mais disponível.", show_alert=True)
        await gem_market_main(update, context); return
        
    line = _render_listing_line(listing)
    price = listing.get("unit_price_gems", 0)
    
    text = f"Você confirma a compra de 1 lote deste item?\n\n{line}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ Sim, comprar por 💎 {price}", callback_data=f"gem_buy_execute_{lid}")],
        [InlineKeyboardButton("❌ Não, voltar", callback_data=back_cb)]
    ])
    await _safe_edit_or_send(q, context, chat_id, text, kb)

async def gem_market_buy_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    CORREÇÃO DE PAGAMENTO: Fluxo finalizado para usar MongoDB/Cache.
    O Manager lida com o pagamento do vendedor e a limpeza de cache.
    O Handler lida apenas com o débito do comprador e a entrega do item.
    """
    q = update.callback_query
    await q.answer("Processando compra...")
    
    chat_id = update.effective_chat.id 
    buyer_id = q.from_user.id
    
    try: lid = int(q.data.replace("gem_buy_execute_", ""))
    except: await q.answer("ID inválido.", show_alert=True); return
        
    # --- 1. Carrega a Listagem e Valida ---
    listing = gem_market_manager.get_listing(lid)
    if not listing or not listing.get("active"):
        await q.answer("Item já vendido ou removido!", show_alert=True)
        await gem_market_main(update, context) 
        return
        
    seller_id = int(listing.get("seller_id", 0))
    if buyer_id == seller_id:
        await q.answer("Você não pode comprar de si mesmo.", show_alert=True); return

    # --- 2. Carrega Dados dos Jogadores ---
    buyer_pdata = await player_manager.get_player_data(buyer_id)
    seller_pdata = await player_manager.get_player_data(seller_id) # Carregar apenas para notificação
    
    if not buyer_pdata:
        await q.answer("Erro ao carregar seus dados.", show_alert=True); return

    # --- 3. Verifica Saldo (GEMAS) ---
    total_cost = int(listing.get("unit_price_gems", 0)) 
    buyer_gems = int(buyer_pdata.get("gems", 0))
    if buyer_gems < total_cost:
        await q.answer(f"Gemas insuficientes! Você precisa de {total_cost} 💎.", show_alert=True)
        return

    # --- 4. Executa a Baixa no Gerenciador de Mercado (MongoDB) ---
    try:
        # 1. DÉBITO DO COMPRADOR NA MEMÓRIA
        buyer_pdata["gems"] = max(0, buyer_gems - total_cost)
        
        # 2. PROCESSO DE VENDA NO MANAGER (Atualiza Listagem + PAGA VENDEDOR NO DB + LIMPA CACHE)
        updated_listing, _ = await gem_market_manager.purchase_listing( 
            buyer_pdata=buyer_pdata, 
            seller_pdata=seller_pdata, 
            listing_id=lid,
            quantity=1
        )
    except Exception as e:
        logger.error(f"[GemMarket] Erro ao processar listing: {e}")
        
        # ⚠️ TRATAMENTO DE CONCORRÊNCIA: Mensagem customizada para o erro.
        error_msg = str(e)
        if "Falha na baixa do estoque" in error_msg or "Anúncio não ativo" in error_msg:
             error_msg = "⚠️ Alguém comprou este item primeiro ou o estoque acabou! Atualize a lista."
        
        await q.answer(error_msg, show_alert=True)
        return

    # --- 5. OPERAÇÃO ATÔMICA (Entrega do Item CORRIGIDA) ---
    
    item_payload = listing.get("item", {})
    base_id_limpo = item_payload.get("base_id") # Ex: 'monge_aspecto_asura' (Vem limpo do DB)
    item_type = item_payload.get("type")       # Ex: 'skin' ou 'skill'
    pack_qty = int(item_payload.get("qty", 1))
    
    # Determina o ID do item real que o jogador deve receber (A CAIXA/TOMO)
    base_id_final = base_id_limpo
    
    if item_type == "skin":
        # --- PROTEÇÃO PARA SKINS ---
        # Se já tiver "caixa_", mantém. Se não, adiciona.
        if base_id_limpo.startswith("caixa_"):
            base_id_final = base_id_limpo
        else:
            base_id_final = f"caixa_{base_id_limpo}" 
            
    elif item_type == "skill":
        # --- PROTEÇÃO PARA SKILLS ---
        # Se já tiver "tomo_", mantém. Se não, adiciona.
        if base_id_limpo.startswith("tomo_"):
            base_id_final = base_id_limpo
        else:
            base_id_final = f"tomo_{base_id_limpo}" 
        
    item_label = _item_label(base_id_final)
    
    if not (base_id_final and pack_qty > 0):
        logger.error(f"[GemMarket] Item sem base_id/pack_qty na listagem {lid}!")
        await q.answer("Erro crítico: Item inválido.", show_alert=True)
        return
    
    # A) Entrega o Item (no pdata já debitado)
    player_manager.add_item_to_inventory(buyer_pdata, base_id_final, pack_qty) 
    
    # B) Notifica vendedor (Mantido no handler)
    if seller_id and seller_pdata:
        try:
            await context.bot.send_message(
                seller_id,
                f"💎 <b>Venda Realizada!</b>\nVocê vendeu <b>{item_label}</b> por <b>{total_cost} Gemas</b>.",
                parse_mode="HTML"
            )
        except: pass

    # --- 6. Salva o Comprador (Agora com Item + Saldo Novo) ---
    # Este save finaliza a transação para o comprador (débito + item)
    await player_manager.save_player_data(buyer_id, buyer_pdata)

    # --- 7. Logs e Feedback ---
    try:
        buyer_name = buyer_pdata.get("character_name", q.from_user.first_name)
        seller_name = seller_pdata.get("character_name", "Vendedor") if seller_pdata else "Desconhecido"
        
        log_text = (
            f"💎 <b>CASA DE LEILÕES (VENDA)</b>\n\n"
            f"👤 <b>Comprador:</b> {buyer_name}\n"
            f"📦 <b>Item:</b> {item_label} x{pack_qty}\n"
            f"💰 <b>Valor:</b> {total_cost} Gemas\n"
            f"🤝 <b>Vendedor:</b> {seller_name}"
        )
        
        await context.bot.send_message(
            chat_id=LOG_GROUP_ID, 
            message_thread_id=LOG_TOPIC_ID, 
            text=log_text, 
            parse_mode="HTML"
        )
    except Exception as e_log:
        logger.warning(f"Log error: {e_log}")

    text = f"✅ Compra concluída! Recebeste <b>{item_label} (x{pack_qty})</b> por 💎 {total_cost}."
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_list_cats")]])
    await _safe_edit_or_send(q, context, chat_id, text, kb)
    
async def gem_market_my(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id
    
    my_listings = gem_market_manager.list_by_seller(user_id) 

    if not my_listings:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")]])
        await _safe_edit_or_send(q, context, chat_id, "Você não tem listagens ativas na Casa de Leilões.", kb)
        return

    lines = ["👤 <b>Minhas Listagens (Gemas)</b>\n"]
    kb_rows = []
    for l in my_listings:
        lines.append(_render_listing_line(l))
        kb_rows.append([InlineKeyboardButton(f"Cancelar [#{l['id']}]", callback_data=f"gem_cancel_{l['id']}")])

    kb_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")])
    await _safe_edit_or_send(q, context, chat_id, "\n".join(lines), InlineKeyboardMarkup(kb_rows))

async def gem_market_cancel_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("A cancelar...")
    user_id = q.from_user.id
    chat_id = update.effective_chat.id
    
    try: lid = int(q.data.replace("gem_cancel_", ""))
    except: await q.answer("ID inválido.", show_alert=True); return

    try:
        listing = gem_market_manager.cancel_listing(seller_id=user_id, listing_id=lid)
    except gem_market_manager.GemMarketError as e:
        await q.answer(f"Erro: {e}", show_alert=True)
        await gem_market_my(update, context); return
        
    pdata = await player_manager.get_player_data(user_id)
    
    item_payload = listing.get("item", {})
    base_id = item_payload.get("base_id")
    pack_qty = item_payload.get("qty", 1)
    lotes_left = listing.get("quantity", 0) 
    total_return = pack_qty * lotes_left
    item_label = _item_label(base_id)
    
    if base_id and total_return > 0:
        player_manager.add_item_to_inventory(pdata, base_id, total_return)
            
    await player_manager.save_player_data(user_id, pdata)
    
    text = f"✅ Listagem #{lid} ({item_label}) cancelada. Os {total_return} itens foram devolvidos."
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_my")]])
    await _safe_edit_or_send(q, context, chat_id, text, kb)

# ==============================
#  Handlers (Exports)
# ==============================

gem_market_main_handler = CallbackQueryHandler(gem_market_main, pattern=r'^gem_market_main$')

gem_list_cats_handler = CallbackQueryHandler(show_buy_category_menu, pattern=r'^gem_list_cats$')
gem_sell_cats_handler = CallbackQueryHandler(show_sell_category_menu, pattern=r'^gem_sell_cats$')

gem_list_filter_handler = CallbackQueryHandler(show_buy_class_picker, pattern=r'^gem_list_filter:(skin|skill|evo)$')
gem_list_class_handler = CallbackQueryHandler(show_buy_items_filtered, pattern=r'^gem_list_class:(skin|skill|evo):([a-z_]+):(\d+)$')

gem_sell_filter_handler = CallbackQueryHandler(show_sell_class_picker, pattern=r'^gem_sell_filter:(skin|skill|evo)$')
gem_sell_class_handler = CallbackQueryHandler(show_sell_items_filtered, pattern=r'^gem_sell_class:(skin|skill|evo):([a-z_]+):(\d+)$')

gem_market_pick_item_handler = CallbackQueryHandler(gem_market_pick_item, pattern=r'^gem_sell_item_')
gem_market_cancel_new_handler = CallbackQueryHandler(gem_market_cancel_new, pattern=r'^gem_market_cancel_new$')

gem_market_pack_spin_handler = CallbackQueryHandler(gem_market_pack_spin, pattern=r'^gem_pack_(inc|dec)_[0-9]+$')
gem_market_pack_confirm_handler = CallbackQueryHandler(gem_market_pack_confirm, pattern=r'^gem_pack_confirm$')

gem_market_lote_spin_handler = CallbackQueryHandler(gem_market_lote_spin, pattern=r'^gem_lote_(inc|dec)_[0-9]+$')
gem_market_lote_confirm_handler = CallbackQueryHandler(gem_market_lote_confirm, pattern=r'^gem_lote_confirm$')

gem_market_price_spin_handler = CallbackQueryHandler(gem_market_price_spin, pattern=r'^gem_p_(inc|dec)_[0-9]+$')
gem_market_price_confirm_handler = CallbackQueryHandler(gem_market_price_confirm, pattern=r'^gem_p_confirm$')

gem_market_buy_confirm_handler = CallbackQueryHandler(gem_market_buy_confirm, pattern=r'^gem_buy_confirm:.*:(\d+)$')
gem_market_buy_execute_handler = CallbackQueryHandler(gem_market_buy_execute, pattern=r'^gem_buy_execute_(\d+)$')

gem_market_my_handler = CallbackQueryHandler(gem_market_my, pattern=r'^gem_market_my$')
gem_market_cancel_execute_handler = CallbackQueryHandler(gem_market_cancel_execute, pattern=r'^gem_cancel_(\d+)$')