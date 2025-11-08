# handlers/gem_market_handler.py
# (VERSÃO ATUALIZADA - Pronta para Skills e Skins como ITENS)

# Em: handlers/gem_market_handler.py
# (Cola isto no topo do ficheiro)

import logging
from typing import List, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

# --- Nossos Módulos ---
from modules import player_manager, game_data, file_id_manager
from modules import gem_market_manager # O "Backend"
from handlers.admin.utils import ADMIN_LIST # Para Debug (opcional)

# --- LISTAS DE ITENS VENDÁVEIS ---

# 1. Importa a lista de Itens de Evolução
try:
    from handlers.adventurer_market_handler import EVOLUTION_ITEMS
except ImportError:
    EVOLUTION_ITEMS = {"emblema_guerreiro", "essencia_guardia", "selo_sagrado"} 
    logging.warning("Lista EVOLUTION_ITEMS não encontrada, a usar fallback.")

# 2. Lista de Tomos de Skill (Itens)
# (Preenchida com base no teu skills.py. Confirma se os nomes são "tomo_")
SKILL_BOOK_ITEMS: set[str] = {
    "tomo_passive_bulwark", "tomo_active_whirlwind", "tomo_active_holy_blessing",
    "tomo_passive_unstoppable", "tomo_active_unbreakable_charge", "tomo_passive_last_stand",
    "tomo_passive_animal_companion", "tomo_active_deadeye_shot", "tomo_passive_apex_predator",
    "tomo_active_iron_skin", "tomo_passive_elemental_strikes", "tomo_active_transcendence",
    "tomo_active_curse_of_weakness", "tomo_passive_elemental_attunement", "tomo_active_meteor_swarm",
    "tomo_active_song_of_valor", "tomo_active_dissonant_melody", "tomo_passive_symphony_of_power",
    "tomo_active_shadow_strike", "tomo_passive_potent_toxins", "tomo_active_dance_of_a_thousand_cuts",
    "tomo_passive_iai_stance", "tomo_active_parry_and_riposte", "tomo_active_banner_of_command",
    "tomo_guerreiro_corte_perfurante", "tomo_berserker_golpe_selvagem",
    "tomo_cacador_flecha_precisa", "tomo_monge_rajada_de_punhos", "tomo_mago_bola_de_fogo",
    "tomo_bardo_melodia_restauradora", "tomo_assassino_ataque_furtivo", "tomo_samurai_corte_iaijutsu",
}

# 3. Lista de Caixas de Skin (Itens)
# (Preenchida com base no teu skins.py. Confirma se os nomes são "caixa_")
SKIN_BOX_ITEMS: set[str] = {
    "caixa_guerreiro_armadura_negra",
    "caixa_guerreiro_placas_douradas",
    "caixa_mago_traje_arcano",
    "caixa_assassino_manto_espectral",
    "caixa_cacador_patrulheiro_elfico",
    "caixa_berserker_pele_urso",
    "caixa_monge_quimono_dragao",
    "caixa_bardo_traje_maestro",
    "caixa_samurai_armadura_shogun",
    "caixa_samurai_armadura_demoniaca",
    "caixa_samurai_encarnacao_sangrenta",
    "caixa_samurai_guardiao_celestial",
    "caixa_samurai_chama_aniquiladora",
}

# Combina todos os itens vendáveis por gemas
ALL_GEM_SELLABLE_ITEMS = EVOLUTION_ITEMS.union(SKILL_BOOK_ITEMS).union(SKIN_BOX_ITEMS)

logger = logging.getLogger(__name__)

# ==============================
#  Utils
# ==============================

def _get_item_info(base_id: str) -> dict:
    try:
        info = game_data.get_item_info(base_id)
        if info: return dict(info)
    except Exception: pass
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

def _item_label(base_id: str) -> str:
    info = _get_item_info(base_id)
    # Define o emoji com base no tipo
    if base_id in SKILL_BOOK_ITEMS:
        emoji = "📚"
    elif base_id in SKIN_BOX_ITEMS:
        emoji = "🎨"
    elif base_id in EVOLUTION_ITEMS:
        emoji = "✨"
    else:
        emoji = info.get("emoji", "💎") # Padrão
        
    name = info.get("display_name", base_id)
    return f"{emoji} {name}"

# Em handlers/adventurer_market_handler.py

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return # Sucesso
    except Exception as e:
        # <<< CORREÇÃO AQUI >>>
        if "message is not modified" in str(e).lower():
            return # Para a execução, está tudo bem.
        pass # Erro real (ex: era texto), tenta o próximo.
    
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return # Sucesso
    except Exception as e:
        # <<< CORREÇÃO AQUI >>>
        if "message is not modified" in str(e).lower():
            return # Para a execução, está tudo bem.
        pass # Erro real (ex: era media), tenta o próximo.
    
    # Se AMBOS falharam (ex: mensagem foi apagada), envia uma nova.
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

async def _send_with_media(chat_id: int, context: ContextTypes.DEFAULT_TYPE, caption: str, kb: InlineKeyboardMarkup, media_keys: List[str]):
    for key in media_keys:
        fd = file_id_manager.get_file_data(key)
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
        "🏛️ <b>✨ 𝐂𝐨𝐦𝐞́𝐫𝐜𝐢𝐨 𝐝𝐞 𝐑𝐞𝐥𝐢́𝐪𝐮𝐢𝐚𝐬</b>\n\n" # Nome que escolhemos
        "Bem-vindo ao Comercio de Relíquias! Aqui podes negociar "
        "itens raros (Itens de Evolução, Tomos de Skill, Skins) "
        "com outros aventureiros usando <b>Diamantes</b> (💎)."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Ver Listagens (Comprar)", callback_data="gem_market_list:1")],
        [InlineKeyboardButton("➕ Vender Item", callback_data="gem_market_sell:1")],
        [InlineKeyboardButton("👤 Minhas Listagens", callback_data="gem_market_my")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market")],
    ])

    keys = ["mercado_gemas", "img_mercado_gemas", "gem_market", "gem_shop", "casa_leiloes"]
    try:
        await q.delete_message()
    except Exception: pass
    await _send_with_media(chat_id, context, text, kb, keys)

# ==============================
#  Spinner de Preço (Gemas)
# ==============================

def _render_gem_price_spinner(price: int) -> InlineKeyboardMarkup:
    price = max(1, int(price))
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("−100", callback_data="gem_p_dec_100"),
            InlineKeyboardButton("−10",  callback_data="gem_p_dec_10"),
            InlineKeyboardButton("−1",   callback_data="gem_p_dec_1"),
            InlineKeyboardButton("+1",   callback_data="gem_p_inc_1"),
            InlineKeyboardButton("+10",  callback_data="gem_p_inc_10"),
            InlineKeyboardButton("+100", callback_data="gem_p_inc_100"),
        ],
        [InlineKeyboardButton(f"💎 {price} Diamantes", callback_data="noop")],
        [InlineKeyboardButton("✅ Confirmar Preço", callback_data="gem_p_confirm")],
        [InlineKeyboardButton("❌ Cancelar Venda",  callback_data="gem_market_cancel_new")]
    ])

async def gem_market_price_spin(update, context):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id

    cur = max(1, int(context.user_data.get("gem_market_price", 10)))
    action = q.data
    
    if action.startswith("gem_p_inc_"):
        step = int(action.split("_")[-1]); cur += step
    elif action.startswith("gem_p_dec_"):
        step = int(action.split("_")[-1]); cur = max(1, cur - step)
    
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
        f"Defina o <b>preço por lote</b> (em Diamantes):"
    )
    kb = _render_gem_price_spinner(cur)
    await _safe_edit_or_send(q, context, chat_id, f"{caption} <b>💎 {cur}</b>", kb)

async def gem_market_price_confirm(update, context):
    q = update.callback_query
    await q.answer()
    price = max(1, int(context.user_data.get("gem_market_price", 1)))
    await gem_market_finalize_listing(update, context, price)

# ==============================
#  Spinner de Quantidade (Lotes)
# ==============================

def _render_gem_lote_spinner(qty: int, max_qty: int) -> InlineKeyboardMarkup:
    qty = max(1, int(qty)); max_qty = max(1, int(max_qty))
    current_qty = max(1, min(int(qty), max_qty))
    
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("−10", callback_data="gem_lote_dec_10"),
            InlineKeyboardButton("−1",  callback_data="gem_lote_dec_1"),
            InlineKeyboardButton(f"📦 {current_qty} / {max_qty} Lotes", callback_data="noop"),
            InlineKeyboardButton("+1",  callback_data="gem_lote_inc_1"),
            InlineKeyboardButton("+10", callback_data="gem_lote_inc_10"),
        ],
        [InlineKeyboardButton("✅ Confirmar Lotes", callback_data="gem_lote_confirm")],
        [InlineKeyboardButton("❌ Cancelar Venda", callback_data="gem_market_cancel_new")]
    ])

async def _show_gem_lote_spinner(q, context, chat_id: int):
    pending = context.user_data.get("gem_market_pending")
    if not pending or pending.get("type") != "item_stack": # Mudança de nome
        await gem_market_cancel_new(q, context); return

    qty_have = int(pending.get("qty_have", 0))
    pack_qty = int(pending.get("qty", 1))
    
    max_lotes = max(1, qty_have // pack_qty)
    context.user_data["gem_market_lote_max"] = max_lotes
    
    current_lotes = max(1, int(context.user_data.get("gem_market_lotes", 1)))
    current_lotes = min(current_lotes, max_lotes)
    context.user_data["gem_market_lotes"] = current_lotes

    kb = _render_gem_lote_spinner(current_lotes, max_lotes)
    
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

    cur = max(1, int(context.user_data.get("gem_market_lotes", 1)))
    max_qty = max(1, int(context.user_data.get("gem_market_lote_max", 1)))
    
    action = q.data
    if action.startswith("gem_lote_inc_"):
        step = int(action.split("_")[-1]); cur = min(max_qty, cur + step)
    elif action.startswith("gem_lote_dec_"):
        step = int(action.split("_")[-1]); cur = max(1, cur - step)
        
    context.user_data["gem_market_lotes"] = cur
    await _show_gem_lote_spinner(q, context, chat_id)

async def gem_market_lote_confirm(update, context):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    
    context.user_data["gem_market_price"] = 10 
    
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
    kb = _render_gem_price_spinner(price)
    await _safe_edit_or_send(q, context, chat_id, f"{caption_prefix} <b>💎 {price}</b>", kb)

# ==============================
#  Spinner de Tamanho (Pack Qty)
# ==============================

def _render_gem_pack_spinner(qty: int, max_qty: int) -> InlineKeyboardMarkup:
    qty = max(1, int(qty)); max_qty = max(1, int(max_qty))
    current_qty = max(1, min(int(qty), max_qty))
    
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("−10", callback_data="gem_pack_dec_10"),
            InlineKeyboardButton("−1",  callback_data="gem_pack_dec_1"),
            InlineKeyboardButton(f"📦 {current_qty} / {max_qty} Itens", callback_data="noop"),
            InlineKeyboardButton("+1",  callback_data="gem_pack_inc_1"),
            InlineKeyboardButton("+10", callback_data="gem_pack_inc_10"),
        ],
        [InlineKeyboardButton("✅ Confirmar Tamanho", callback_data="gem_pack_confirm")],
        [InlineKeyboardButton("❌ Cancelar Venda", callback_data="gem_market_cancel_new")]
    ])

async def _show_gem_pack_spinner(q, context, chat_id: int):
    pending = context.user_data.get("gem_market_pending")
    if not pending or pending.get("type") != "item_stack":
        await gem_market_cancel_new(q, context); return

    qty_have = int(pending.get("qty_have", 0))
    current_pack_qty = max(1, int(pending.get("qty", 1)))
    current_pack_qty = min(current_pack_qty, qty_have)
    
    pending["qty"] = current_pack_qty
    context.user_data["gem_market_pending"] = pending

    kb = _render_gem_pack_spinner(current_pack_qty, qty_have)
    
    item_label = _item_label(pending["base_id"])
    caption = (
        f"Item: <b>{item_label}</b> (Você tem {qty_have} no total)\n\n"
        f"Defina quantos itens vão em <b>cada lote</b>:"
    )
    
    await _safe_edit_or_send(q, context, chat_id, caption, kb)

async def gem_market_pack_spin(update, context):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    
    pending = context.user_data.get("gem_market_pending")
    if not pending: await gem_market_cancel_new(update, context); return

    cur = max(1, int(pending.get("qty", 1)))
    max_qty = max(1, int(pending.get("qty_have", 1)))
    
    action = q.data
    if action.startswith("gem_pack_inc_"):
        step = int(action.split("_")[-1]); cur = min(max_qty, cur + step)
    elif action.startswith("gem_pack_dec_"):
        step = int(action.split("_")[-1]); cur = max(1, cur - step)
        
    pending["qty"] = cur
    context.user_data["gem_market_pending"] = pending
    await _show_gem_pack_spinner(q, context, chat_id)

async def gem_market_pack_confirm(update, context):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    context.user_data["gem_market_lotes"] = 1
    await _show_gem_lote_spinner(q, context, chat_id)

# ==============================
#  Fluxo de Venda (Sell Flow)
# ==============================

async def gem_market_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id

    try: page = int(q.data.split(':')[1])
    except: page = 1
    
    pdata = await player_manager.get_player_data(user_id) or {}
    inv = pdata.get("inventory", {}) or {}

    sellable_items = []
    
    # (NOVO) Itera sobre o inventário e filtra pelos itens das 3 listas
    for base_id, qty in inv.items():
        if isinstance(qty, int) and qty > 0 and base_id in ALL_GEM_SELLABLE_ITEMS:
            sellable_items.append({
                "type": "item_stack", # Tipo genérico para todos
                "base_id": base_id, 
                "qty_have": qty,
                "label": f"{_item_label(base_id)} (x{qty})"
            })
            
    sellable_items.sort(key=lambda x: x["label"])

    ITEMS_PER_PAGE = 8
    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    items_for_page = sellable_items[start_index:end_index]

    caption = f"💎 <b>Vender Item (Gemas)</b> (Pág. {page})\nSelecione um item para vender:\n"
    keyboard_rows = []

    if not sellable_items:
        caption = "Você não tem itens premium (Itens de Evolução, Tomos de Skill, Skins) para vender."
    elif not items_for_page:
        caption = "Não há mais itens para mostrar."
    else:
        for item in items_for_page:
            callback_data = f"gem_sell_item_{item['base_id']}"
            keyboard_rows.append([InlineKeyboardButton(item["label"], callback_data=callback_data)])
            
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"gem_market_sell:{page - 1}"))
    if end_index < len(sellable_items):
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"gem_market_sell:{page + 1}"))
    if nav_buttons:
        keyboard_rows.append(nav_buttons)

    keyboard_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")])
    await _safe_edit_or_send(q, context, chat_id, caption, InlineKeyboardMarkup(keyboard_rows))

async def gem_market_pick_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Jogador selecionou um item (Evo, Skill ou Skin) para vender."""
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id
    
    base_id = q.data.replace("gem_sell_item_", "")
    
    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {}) or {}
    qty_have = int(inv.get(base_id, 0))
    
    if qty_have <= 0:
        await q.answer("Você não tem mais esse item.", show_alert=True)
        await gem_market_sell(update, context) # Recarrega lista
        return

    context.user_data["gem_market_pending"] = {
        "type": "item_stack", # Tipo genérico
        "base_id": base_id, 
        "qty_have": qty_have,
        "qty": 1  # 'qty' é o "tamanho do lote", começa em 1
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

    base_id = pending["base_id"]
    pack_qty = int(pending.get("qty", 1))
    lote_qty = max(1, int(context.user_data.get("gem_market_lotes", 1)))
    total_to_remove = pack_qty * lote_qty
    item_label = _item_label(base_id) # Pega o label

    if not player_manager.has_item(pdata, base_id, total_to_remove):
        await q.answer(f"Você não tem {total_to_remove}x {item_label}.", show_alert=True)
        await gem_market_cancel_new(update, context)
        return

    player_manager.remove_item_from_inventory(pdata, base_id, total_to_remove)
    await player_manager.save_player_data(user_id, pdata)
    
    # Define o 'type' correto para o backend
    item_type_for_backend = "item_stack" # Padrão
    if base_id in EVOLUTION_ITEMS:
        item_type_for_backend = "evo_item"
    elif base_id in SKILL_BOOK_ITEMS:
        item_type_for_backend = "skill"
    elif base_id in SKIN_BOX_ITEMS:
        item_type_for_backend = "skin"

    item_payload = {
        "type": item_type_for_backend,
        "base_id": base_id,
        "qty": pack_qty
    }

    try:
        listing = gem_market_manager.create_listing(
            seller_id=user_id,
            item_payload=item_payload,
            unit_price=price_gems,
            quantity=lote_qty
        )
    except Exception as e:
        logger.error(f"[GemMarket] Falha ao criar listagem para {user_id}: {e}", exc_info=True)
        player_manager.add_item_to_inventory(pdata, base_id, total_to_remove)
        await player_manager.save_player_data(user_id, pdata)
        await _safe_edit_or_send(q, context, chat_id, f"⚠️ Ocorreu um erro: {e}\nSeus itens foram devolvidos.", InlineKeyboardMarkup([
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

# ==============================
#  Fluxo de Compra (Buy Flow)
# ==============================

def _render_listing_line(listing: dict) -> str:
    """Formata uma linha de listagem para exibição."""
    item = listing.get("item", {})
    price = listing.get("unit_price_gems", 0)
    lotes = listing.get("quantity", 1)
    lid = listing.get("id")
    
    base_id = item.get("base_id")
    pack_qty = item.get("qty", 1)
    label = _item_label(base_id) # Usa o label unificado
    
    return f"• {label} (x{pack_qty}) — <b>💎 {price}</b> (Lotes: {lotes}) [#{lid}]"


async def gem_market_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    user_id = q.from_user.id
    
    try: page = int(q.data.split(':')[1])
    except: page = 1
        
    pdata = await player_manager.get_player_data(user_id)
    gems = player_manager.get_gems(pdata)

    listings = gem_market_manager.list_active(page=page, page_size=10)

    if not listings and page == 1:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")]])
        await _safe_edit_or_send(q, context, chat_id, "Não há nenhuma listagem ativa no momento.", kb)
        return

    lines = [f"🏛️ <b>Listagens Ativas</b> (Pág. {page})\nVocê tem <b>💎 {gems}</b>\n"]
    kb_rows = []
    
    for l in listings:
        lines.append(_render_listing_line(l))
        if int(l.get("seller_id", 0)) != user_id:
            kb_rows.append([InlineKeyboardButton(f"Comprar [#{l['id']}]", callback_data=f"gem_buy_confirm_{l['id']}")])

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"gem_market_list:{page - 1}"))
    if len(listings) == 10: # Assume que há mais se a página estiver cheia
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"gem_market_list:{page + 1}"))
    kb_rows.append(nav_buttons)

    kb_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")])
    await _safe_edit_or_send(q, context, chat_id, "\n".join(lines), InlineKeyboardMarkup(kb_rows))


async def gem_market_buy_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    
    try: lid = int(q.data.replace("gem_buy_confirm_", ""))
    except: await q.answer("ID inválido.", show_alert=True); return

    listing = gem_market_manager.get_listing(lid)
    if not listing or not listing.get("active"):
        await q.answer("Esta listagem não está mais disponível.", show_alert=True)
        await gem_market_list(update, context); return
        
    line = _render_listing_line(listing)
    price = listing.get("unit_price_gems", 0)
    
    text = f"Você confirma a compra de 1 lote deste item?\n\n{line}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ Sim, comprar por 💎 {price}", callback_data=f"gem_buy_execute_{lid}")],
        [InlineKeyboardButton("❌ Não, voltar", callback_data="gem_market_list:1")]
    ])
    await _safe_edit_or_send(q, context, chat_id, text, kb)


async def gem_market_buy_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("A processar compra...")
    chat_id = update.effective_chat.id
    buyer_id = q.from_user.id
    
    try: lid = int(q.data.replace("gem_buy_execute_", ""))
    except: await q.answer("ID inválido.", show_alert=True); return
        
    listing = gem_market_manager.get_listing(lid)
    if not listing or not listing.get("active"):
        await q.answer("Esta listagem não está mais disponível.", show_alert=True)
        await gem_market_list(update, context); return
        
    seller_id = listing.get("seller_id")
    if buyer_id == seller_id:
        await q.answer("Você não pode comprar de si mesmo.", show_alert=True); return

    buyer_pdata = await player_manager.get_player_data(buyer_id)
    seller_pdata = await player_manager.get_player_data(seller_id)
    
    if not buyer_pdata or not seller_pdata:
        await q.answer("Erro ao carregar dados do comprador ou vendedor.", show_alert=True)
        return

    try:
        updated_listing, total_price = gem_market_manager.purchase_listing( # Removido Await
            buyer_pdata=buyer_pdata,
            seller_pdata=seller_pdata,
            listing_id=lid,
            quantity=1
        )
    except gem_market_manager.GemMarketError as e:
        await q.answer(f"Falha na compra: {e}", show_alert=True)
        return
    except Exception as e:
        logger.error(f"[GemMarket] Erro crítico na compra L{lid} por B{buyer_id}: {e}", exc_info=True)
        await q.answer("Ocorreu um erro inesperado.", show_alert=True)
        return

    item_payload = listing.get("item", {})
    base_id = item_payload.get("base_id")
    pack_qty = item_payload.get("qty", 1)
    item_label = _item_label(base_id)
    
    if base_id:
        player_manager.add_item_to_inventory(buyer_pdata, base_id, pack_qty)
    else:
        logger.error(f"[GemMarket] Compra L{lid} por B{buyer_id} não tinha base_id no payload!")

    await player_manager.save_player_data(buyer_id, buyer_pdata)
    await player_manager.save_player_data(seller_id, seller_pdata)

    text = f"✅ Compra concluída! Você comprou 1 lote de {item_label} por 💎 {total_price}."
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar às Listagens", callback_data="gem_market_list:1")]])
    await _safe_edit_or_send(q, context, chat_id, text, kb)

# ==============================
#  Minhas Listagens (Gemas)
# ==============================

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
    lotes_left = listing.get("quantity", 0) # Lotes que sobraram
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
gem_market_list_handler = CallbackQueryHandler(gem_market_list, pattern=r'^gem_market_list:(\d+)$')

# Venda
gem_market_sell_handler = CallbackQueryHandler(gem_market_sell, pattern=r'^gem_market_sell:(\d+)$')
gem_market_pick_item_handler = CallbackQueryHandler(gem_market_pick_item, pattern=r'^gem_sell_item_')
gem_market_cancel_new_handler = CallbackQueryHandler(gem_market_cancel_new, pattern=r'^gem_market_cancel_new$')

# Spinners de Venda (Pack, Lote, Preço)
gem_market_pack_spin_handler = CallbackQueryHandler(gem_market_pack_spin, pattern=r'^gem_pack_(inc|dec)_[0-9]+$')
gem_market_pack_confirm_handler = CallbackQueryHandler(gem_market_pack_confirm, pattern=r'^gem_pack_confirm$')

gem_market_lote_spin_handler = CallbackQueryHandler(gem_market_lote_spin, pattern=r'^gem_lote_(inc|dec)_[0-9]+$')
gem_market_lote_confirm_handler = CallbackQueryHandler(gem_market_lote_confirm, pattern=r'^gem_lote_confirm$')

gem_market_price_spin_handler = CallbackQueryHandler(gem_market_price_spin, pattern=r'^gem_p_(inc|dec)_[0-9]+$')
gem_market_price_confirm_handler = CallbackQueryHandler(gem_market_price_confirm, pattern=r'^gem_p_confirm$')

# Compra
gem_market_buy_confirm_handler = CallbackQueryHandler(gem_market_buy_confirm, pattern=r'^gem_buy_confirm_')
gem_market_buy_execute_handler = CallbackQueryHandler(gem_market_buy_execute, pattern=r'^gem_buy_execute_')

# Minhas Listagens
gem_market_my_handler = CallbackQueryHandler(gem_market_my, pattern=r'^gem_market_my$')
gem_market_cancel_execute_handler = CallbackQueryHandler(gem_market_cancel_execute, pattern=r'^gem_cancel_')