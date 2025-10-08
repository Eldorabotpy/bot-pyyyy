# handlers/adventurer_market_handler.py

import logging
from typing import List, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules import mission_manager, player_manager, game_data, file_id_manager, market_manager, clan_manager
from modules.market_manager import render_listing_line as _mm_render_listing_line

# --- DISPLAY UTILS opcional (fallback consistente) ---
try:
    from modules import display_utils  # deve ter: formatar_item_para_exibicao(dict) -> str
except Exception:
    class _DisplayFallback:
        @staticmethod
        def formatar_item_para_exibicao(item_criado: dict) -> str:
            emoji = item_criado.get("emoji", "🛠")
            name = item_criado.get("display_name", item_criado.get("name", "Item"))
            rarity = item_criado.get("rarity", "")
            if rarity:
                name = f"{name} [{rarity}]"
            return f"{emoji} {name}"
    display_utils = _DisplayFallback()

logger = logging.getLogger(__name__)

# ==============================
#  BLOQUEIO: Itens de evolução de classe
# ==============================
EVOLUTION_ITEMS: set[str] = {
    "emblema_guerreiro", "essencia_guardia", "essencia_furia", "selo_sagrado", "essencia_luz",
    "emblema_berserker", "totem_ancestral", "emblema_cacador", "essencia_precisao",
    "marca_predador", "essencia_fera", "emblema_monge", "reliquia_mistica", "essencia_ki",
    "emblema_mago", "essencia_arcana", "essencia_elemental", "grimorio_arcano",
    "emblema_bardo", "essencia_harmonia", "essencia_encanto", "batuta_maestria",
    "emblema_assassino", "essencia_sombra", "essencia_letal", "manto_eterno",
    "emblema_samurai", "essencia_corte", "essencia_disciplina", "lamina_sagrada",
}

EVOL_BLOCK_MSG = (
    "🚫 Este é um <b>item de evolução de classe</b> e não pode ser vendido no "
    "<b>Mercado do Aventureiro</b> por ouro.\n"
    "Use a <b>Loja de Gemas</b> (moeda premium) para negociar esse tipo de item."
)

# ==============================
#  Utils básicos
# ==============================
def _gold(pdata: dict) -> int:
    return int(pdata.get("gold", 0))

def _set_gold(pdata: dict, value: int):
    pdata["gold"] = max(0, int(value))

def _item_label_from_base(base_id: str) -> str:
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}).get("display_name", base_id)

def _get_item_info(base_id: str) -> dict:
    try:
        info = game_data.get_item_info(base_id)
        if info:
            return dict(info)
    except Exception:
        pass
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

def _player_class_key(pdata: dict, fallback="guerreiro") -> str:
    for c in [
        (pdata.get("class") or pdata.get("classe")),
        pdata.get("class_type"), pdata.get("classe_tipo"),
        pdata.get("class_key"), pdata.get("classe"),
    ]:
        if isinstance(c, dict):
            t = c.get("type")
            if isinstance(t, str) and t.strip():
                return t.strip().lower()
        if isinstance(c, str) and c.strip():
            return c.strip().lower()
    return fallback

def _cut_middle(s: str, maxlen: int = 56) -> str:
    s = (s or "").strip()
    return s if len(s) <= maxlen else s[:maxlen//2 - 1] + "… " + s[-maxlen//2:]

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception:
        pass
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception:
        pass
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
#  Emojis/rotulagem (usa mapa oficial + fallback)
# ==============================
RARITY_LABEL: Dict[str, str] = {
    "comum": "Comum", "bom": "Boa", "raro": "Rara",
    "epico": "Épica", "lendario": "Lendária",
}

_CLASS_DMG_EMOJI_FALLBACK = {
    "guerreiro": "⚔️", "berserker": "🪓", "cacador": "🏹", "caçador": "🏹",
    "assassino": "🗡", "bardo": "🎵", "monge": "🙏", "mago": "✨", "samurai": "🗡",
}
_STAT_EMOJI_FALLBACK = {
    "dmg": "🗡", "hp": "❤️‍🩹", "vida": "❤️‍🩹", "defense": "🛡️", "defesa": "🛡️",
    "initiative": "🏃", "agilidade": "🏃", "luck": "🍀", "sorte": "🍀",
    "forca": "💪", "força": "💪", "foco": "🧘", "carisma": "😎", "bushido": "🥷",
    "inteligencia": "🧠", "inteligência": "🧠", "precisao": "🎯", "precisão": "🎯",
    "letalidade": "☠️", "furia": "🔥", "fúria": "🔥",
}

def _class_dmg_emoji(pclass: str) -> str:
    try:
        return getattr(game_data, "CLASS_DMG_EMOJI", {}).get((pclass or "").lower(), _CLASS_DMG_EMOJI_FALLBACK.get((pclass or "").lower(), "🗡"))
    except Exception:
        return _CLASS_DMG_EMOJI_FALLBACK.get((pclass or "").lower(), "🗡")

def _stat_emoji(stat: str, pclass: str) -> str:
    s = (stat or "").lower()
    try:
        attr_mod = getattr(game_data, "attributes", None)
        if attr_mod and hasattr(attr_mod, "ATTRIBUTE_ICONS"):
            em = attr_mod.ATTRIBUTE_ICONS.get(s)
            if em:
                return _class_dmg_emoji(pclass) if s == "dmg" else em
    except Exception:
        pass
    if s == "dmg":
        return _class_dmg_emoji(pclass)
    return _STAT_EMOJI_FALLBACK.get(s, "❔")

def _stack_inv_display(base_id: str, qty: int) -> str:
    info = _get_item_info(base_id)
    name = info.get("display_name") or info.get("nome_exibicao") or base_id
    emoji = info.get("emoji", "")
    return f"{emoji}{name} ×{qty}" if emoji else f"{name} ×{qty}"

def _render_unique_line_safe(inst: dict, pclass: str) -> str:
    try:
        return display_utils.formatar_item_para_exibicao(inst)
    except Exception:
        pass

    base_id = inst.get("base_id") or inst.get("tpl") or inst.get("id") or "item"
    info = _get_item_info(base_id)
    name = inst.get("display_name") or info.get("display_name") or info.get("nome_exibicao") or base_id
    item_emoji = inst.get("emoji") or info.get("emoji") or _class_dmg_emoji(pclass)
    try:
        cur_d, max_d = inst.get("durability", [20, 20]); cur_d, max_d = int(cur_d), int(max_d)
    except Exception:
        cur_d, max_d = 20, 20
    try:
        tier = int(inst.get("tier", 1))
    except Exception:
        tier = 1
    rarity = str(inst.get("rarity", "comum")).lower()
    rarity_label = RARITY_LABEL.get(rarity, rarity.capitalize())
    ench = inst.get("enchantments") or {}
    parts = []
    primary_key, primary_val = None, 0
    if isinstance(ench, dict):
        for k, v in ench.items():
            if k == "dmg" or not isinstance(v, dict): continue
            if str(v.get("source", "")).startswith("primary"):
                primary_key = k
                try: primary_val = int(v.get("value", 0) or 0)
                except Exception: primary_val = 0
                break
        if primary_key is None:
            best = None
            for k, v in ench.items():
                if k == "dmg" or not isinstance(v, dict): continue
                try: val = int(v.get("value", 0) or 0)
                except Exception: val = 0
                if best is None or val > best[1]: best = (k, val)
            if best: primary_key, primary_val = best
    if primary_key:
        parts.append(f"{_stat_emoji(primary_key, pclass)}+{int(primary_val)}")
    if isinstance(ench, dict):
        afx = []
        for k, v in ench.items():
            if k in ("dmg", primary_key) or not isinstance(v, dict): continue
            if str(v.get("source")) != "affix": continue
            try: val = int(v.get("value", 0) or 0)
            except Exception: val = 0
            afx.append((k, val))
        afx.sort(key=lambda t: (t[0], -t[1]))
        for k, val in afx:
            parts.append(f"{_stat_emoji(k, pclass)}+{int(val)}")
    stats_str = ", ".join(parts) if parts else "—"
    return f"『[{cur_d}/{max_d}] {item_emoji}{name} [ {tier} ] [ {rarity_label} ]: {stats_str}』"


# =================================================================
#  Mercado do Aventureiro (P2P) - LÓGICA PRINCIPAL E VERIFICAÇÃO
# =================================================================
async def market_adventurer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ponto de entrada para o Mercado do Aventureiro.
    Verifica se o jogador tem o plano pago antes de mostrar o menu.
    """
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id

    # ========================================================
    # ## INÍCIO DA VERIFICAÇÃO DE PLANO PAGO (CÓDIGO NOVO) ##
    # ========================================================
    # Esta função `has_premium_plan` precisa ser criada em `player_manager`.
    if not player_manager.has_premium_plan(user_id):
        await q.answer("Acesso exclusivo para apoiadores.", show_alert=True)
        text = "🚫 O <b>Mercado do Aventureiro</b> é um benefício exclusivo para jogadores com o <b>Plano Apoiador</b> ativo."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✨ Quero Apoiar!", url="https://t.me/seu_link_de_apoio")], # Coloque seu link de apoio aqui
            [InlineKeyboardButton("⬅️ Voltar ao Mercado", callback_data="market")]
        ])
        await _safe_edit_or_send(q, context, chat_id, text, kb)
        return
    # ========================================================
    # ## FIM DA VERIFICAÇÃO ##
    # ========================================================

    # Se a verificação passar, o código continua normalmente.
    text = (
        "🎒 <b>Mercado do Aventureiro</b>\n"
        "Compre e venda itens com outros jogadores."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Listagens", callback_data="market_list")],
        [InlineKeyboardButton("➕ Vender Item", callback_data="market_sell:1")],
        [InlineKeyboardButton("👤 Minhas Listagens", callback_data="market_my")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market")],
    ])

    keys = ["mercado_aventureiro", "img_mercado_aventureiro", "market_adventurer", "market_aventurer_img"]
    try:
        await q.delete_message()
    except Exception:
        pass
    await _send_with_media(chat_id, context, text, kb, keys)

async def market_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    viewer_pdata = player_manager.get_player_data(q.from_user.id) or {}

    listings = market_manager.list_active()
    logger.info("[market_list] ativos=%d", len(listings))
    if not listings:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]])
        await _safe_edit_or_send(q, context, chat_id, "Não há listagens ativas no momento.", kb)
        return

    lines = ["📦 <b>Listagens ativas</b>\n"]
    kb_rows = []
    for l in listings[:30]:
        lines.append("• " + _mm_render_listing_line(l, viewer_player_data=viewer_pdata, show_price_per_unit=True))
        kb_rows.append([InlineKeyboardButton(f"Comprar #{l['id']}", callback_data=f"market_buy_{l['id']}")])

    kb_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])
    await _safe_edit_or_send(q, context, chat_id, "\n".join(lines), InlineKeyboardMarkup(kb_rows))

async def market_my(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id
    viewer_pdata = player_manager.get_player_data(user_id) or {}

    my = market_manager.list_by_seller(user_id)
    if not my:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]])
        await _safe_edit_or_send(q, context, chat_id, "Você não tem listagens ativas.", kb)
        return

    lines = ["👤 <b>Minhas listagens</b>\n"]
    kb_rows = []
    for l in my:
        lines.append("• " + _mm_render_listing_line(l, viewer_player_data=viewer_pdata, show_price_per_unit=True))
        kb_rows.append([InlineKeyboardButton(f"Cancelar #{l['id']}", callback_data=f"market_cancel_{l['id']}")])

    kb_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])
    await _safe_edit_or_send(q, context, chat_id, "\n".join(lines), InlineKeyboardMarkup(kb_rows))

async def market_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id
    lid = int(q.data.replace("market_cancel_", ""))

    listing = market_manager.get_listing(lid)
    if not listing or not listing.get("active"):
        await q.answer("Listagem inválida.", show_alert=True); return
    if int(listing["seller_id"]) != int(user_id):
        await q.answer("Você não pode cancelar de outro jogador.", show_alert=True); return

    pdata = player_manager.get_player_data(user_id)
    it = listing["item"]
    if it["type"] == "stack":
        base_id = it["base_id"]
        pack_qty = int(it.get("qty", 1))
        lots_left = int(listing.get("quantity", 0))
        total_return = pack_qty * max(0, lots_left)
        if total_return > 0:
            player_manager.add_item_to_inventory(pdata, base_id, total_return)
    else:
        uid = it["uid"]
        inst = it["item"]
        inv = pdata.get("inventory", {}) or {}
        new_uid = uid if uid not in inv else f"{uid}_ret"
        inv[new_uid] = inst
        pdata["inventory"] = inv

    player_manager.save_player_data(user_id, pdata)
    market_manager.delete_listing(lid)

    await _safe_edit_or_send(q, context, chat_id, f"❌ Listagem #{lid} cancelada e itens devolvidos.", InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market_my")]
    ]))

async def market_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    buyer_id = q.from_user.id
    chat_id = update.effective_chat.id
    lid = int(q.data.replace("market_buy_", ""))

    listing = market_manager.get_listing(lid)
    if not listing or not listing.get("active"):
        await q.answer("Listagem não está mais ativa.", show_alert=True); return
    if int(listing["seller_id"]) == int(buyer_id):
        await q.answer("Você não pode comprar sua própria listagem.", show_alert=True); return

    buyer = player_manager.get_player_data(buyer_id)
    seller = player_manager.get_player_data(listing["seller_id"])
    if not buyer or not seller:
        await q.answer("Jogador não encontrado.", show_alert=True); return

    try:
        updated_listing, total_price = market_manager.purchase_listing(
            buyer_id=buyer_id, listing_id=lid, quantity=1
        )
    except market_manager.MarketError as e:
        await q.answer(str(e), show_alert=True); return

    if _gold(buyer) < total_price:
        await q.answer("Você não tem gold suficiente.", show_alert=True); return

    _set_gold(buyer, _gold(buyer) - total_price)
    _set_gold(seller, _gold(seller) + total_price)

    it = listing["item"]
    if it["type"] == "stack":
        base_id = it["base_id"]
        pack_qty = int(it.get("qty", 1))
        player_manager.add_item_to_inventory(buyer, base_id, pack_qty)
    else:
        inv = buyer.get("inventory", {}) or {}
        uid = it["uid"]
        new_uid = uid if uid not in inv else f"{uid}_buy"
        inv[new_uid] = it["item"]
        buyer["inventory"] = inv

    seller["user_id"] = listing["seller_id"]
    mission_manager.update_mission_progress(
        seller,
        event_type="MARKET_SELL",
        details={"item_id": it.get("base_id") or it.get("uid"), "quantity": 1}
    )
    
    clan_id = seller.get("clan_id")
    if clan_id:
        clan_manager.update_guild_mission_progress(
            clan_id=clan_id,
            mission_type='MARKET_SELL',
            details={
                "item_id": it.get("base_id") or it.get("uid"),
                "quantity": 1,
                "gold_value": total_price
            }
        )

    player_manager.save_player_data(buyer_id, buyer)
    player_manager.save_player_data(listing["seller_id"], seller)

    remaining_lots = int(updated_listing.get("quantity", 0)) if updated_listing.get("active") else 0
    suffix = f" Restam {remaining_lots} lote(s)." if remaining_lots > 0 else " Não restam lotes."
    await _safe_edit_or_send(q, context, chat_id, f"✅ Compra concluída (#{lid}). {total_price} 🪙 transferidos.{suffix}", InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market_list")]
    ]))

async def market_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    pdata = player_manager.get_player_data(user_id) or {}

    try:
        page = int(query.data.split(':')[1])
    except (IndexError, ValueError):
        page = 1
    
    ITEMS_PER_PAGE = 8
    inv = pdata.get("inventory", {}) or {}
    pclass = _player_class_key(pdata)
    
    sellable_items = []
    for uid, inst in inv.items():
        if isinstance(inst, dict):
            base_id = inst.get("base_id") or inst.get("tpl") or inst.get("id")
            if base_id and base_id not in EVOLUTION_ITEMS:
                sellable_items.append({"type": "unique", "uid": uid, "inst": inst})
    for base_id, qty in inv.items():
        if isinstance(qty, (int, float)) and int(qty) > 0:
            if base_id not in EVOLUTION_ITEMS:
                sellable_items.append({"type": "stack", "base_id": base_id, "qty": int(qty)})

    sellable_items.sort(key=lambda x: x.get('uid', x.get('base_id')))
    
    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    items_for_page = sellable_items[start_index:end_index]
    
    caption = f"➕ <b>Vender Item</b> (Página {page})\nSelecione um item do seu inventário:\n"
    keyboard_rows = []

    if not sellable_items:
        caption = "Você não tem itens vendáveis no seu inventário."
        keyboard_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])
    elif not items_for_page:
        caption = "Não há mais itens para mostrar."
        keyboard_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])
    else:
        for item in items_for_page:
            if item["type"] == "unique":
                full_line = _render_unique_line_safe(item["inst"], pclass)
                callback_data = f"market_pick_unique_{item['uid']}"
                keyboard_rows.append([InlineKeyboardButton(_cut_middle(full_line, 56), callback_data=callback_data)])
            else:
                label = f"📦 {_item_label_from_base(item['base_id'])} ({item['qty']}x)"
                callback_data = f"market_pick_stack_{item['base_id']}"
                keyboard_rows.append([InlineKeyboardButton(label, callback_data=callback_data)])

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"market_sell:{page - 1}"))
    if end_index < len(sellable_items):
        nav_buttons.append(InlineKeyboardButton("Próxima ➡️", callback_data=f"market_sell:{page + 1}"))

    if nav_buttons:
        keyboard_rows.append(nav_buttons)
        
    keyboard_rows.append([InlineKeyboardButton("⬅️ Voltar ao Mercado", callback_data="market_adventurer")])
    await _safe_edit_or_send(query, context, chat_id, caption, InlineKeyboardMarkup(keyboard_rows))

def _render_price_spinner(price: int) -> InlineKeyboardMarkup:
    price = max(1, int(price))
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("−100", callback_data="mktp_dec_100"),
            InlineKeyboardButton("−10",  callback_data="mktp_dec_10"),
            InlineKeyboardButton("−1",   callback_data="mktp_dec_1"),
            InlineKeyboardButton(f"💰 {price} 🪙", callback_data="noop"),
            InlineKeyboardButton("+1",   callback_data="mktp_inc_1"),
            InlineKeyboardButton("+10",  callback_data="mktp_inc_10"),
            InlineKeyboardButton("+100", callback_data="mktp_inc_100"),
        ],
        [InlineKeyboardButton("✅ Confirmar", callback_data="mktp_confirm")],
        [InlineKeyboardButton("❌ Cancelar",  callback_data="market_cancel_new")]
    ])

async def _show_price_spinner(q, context, chat_id: int, caption_prefix: str = "Defina o preço:"):
    price = max(1, int(context.user_data.get("market_price", 50)))
    kb = _render_price_spinner(price)
    await _safe_edit_or_send(q, context, chat_id, f"{caption_prefix} <b>{price} 🪙</b>", kb)

async def market_price_spin(update, context):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id

    cur = max(1, int(context.user_data.get("market_price", 50)))
    action = q.data
    if action.startswith("mktp_inc_"):
        step = int(action.split("_")[-1]); cur += step
    elif action.startswith("mktp_dec_"):
        step = int(action.split("_")[-1]); cur = max(1, cur - step)
    context.user_data["market_price"] = cur

    kb = _render_price_spinner(cur)
    await _safe_edit_or_send(q, context, chat_id, f"Defina o preço: <b>{cur} 🪙</b>", kb)

async def market_price_confirm(update, context):
    q = update.callback_query
    await q.answer()
    price = max(1, int(context.user_data.get("market_price", 1)))
    await market_finalize_listing(update, context, price)

async def market_pick_unique(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id
    uid = q.data.replace("market_pick_unique_", "")

    pdata = player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {}) or {}
    inst = inv.get(uid)
    if not isinstance(inst, dict):
        await q.answer("Item não encontrado.", show_alert=True); return

    base_id = inst.get("base_id") or inst.get("tpl") or inst.get("id")
    if base_id in EVOLUTION_ITEMS:
        await q.answer(EVOL_BLOCK_MSG, show_alert=True); return

    context.user_data["market_pending"] = {"type": "unique", "uid": uid, "item": inst}
    del inv[uid]
    pdata["inventory"] = inv
    player_manager.save_player_data(user_id, pdata)

    context.user_data["market_price"] = 50
    await _show_price_spinner(q, context, chat_id, "Defina o <b>preço</b> deste item único:")

async def market_pick_stack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id
    base_id = q.data.replace("market_pick_stack_", "")

    if base_id in EVOLUTION_ITEMS:
        await q.answer(EVOL_BLOCK_MSG, show_alert=True); return

    pdata = player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {}) or {}
    qty_have = int(inv.get(base_id, 0))
    if qty_have <= 0 or not isinstance(inv.get(base_id), (int, float)):
        await q.answer("Quantidade insuficiente.", show_alert=True); return

    context.user_data["market_pending"] = {"type": "stack", "base_id": base_id, "qty_have": qty_have}

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("×1", callback_data="market_qty_1"),
         InlineKeyboardButton("×5", callback_data="market_qty_5"),
         InlineKeyboardButton("×10", callback_data="market_qty_10"),
         InlineKeyboardButton(f"×{qty_have} (Tudo)", callback_data="market_qty_all")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market_sell")]
    ])
    await _safe_edit_or_send(
        q, context, chat_id,
        f"Quanto deseja colocar por <b>lote</b> em <b>{_item_label_from_base(base_id)}</b>? Você possui {qty_have}.",
        kb
    )

async def market_choose_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    pending = context.user_data.get("market_pending") or {}
    if pending.get("type") != "stack":
        return

    qty_have = int(pending.get("qty_have", 0))
    data = q.data
    if data == "market_qty_all":
        qty = qty_have
    else:
        qty = int(data.replace("market_qty_", ""))
        if qty <= 0 or qty > qty_have:
            await q.answer("Quantidade inválida.", show_alert=True); return

    pending["qty"] = qty
    context.user_data["market_pending"] = pending
    context.user_data["market_price"] = 10
    await _show_price_spinner(q, context, chat_id, "Defina o <b>preço por lote</b>:")

async def market_cancel_new(update, context):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id

    pending = context.user_data.pop("market_pending", None)
    if pending and pending.get("type") == "unique":
        pdata = player_manager.get_player_data(user_id)
        inv = pdata.get("inventory", {}) or {}
        uid = pending["uid"]
        new_uid = uid if uid not in inv else f"{uid}_back"
        inv[new_uid] = pending["item"]
        pdata["inventory"] = inv
        player_manager.save_player_data(user_id, pdata)

    context.user_data.pop("market_price", None)
    await _safe_edit_or_send(q, context, chat_id, "Criação de listagem cancelada.", InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]
    ]))

async def market_finalize_listing(update: Update, context: ContextTypes.DEFAULT_TYPE, price: int):
    logger.info("[market_finalize_listing] start price=%s has_cb=%s",
                price, bool(update.callback_query))

    if update.callback_query:
        user_id = update.callback_query.from_user.id
        chat_id = update.effective_chat.id
    else:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

    pending = context.user_data.get("market_pending")
    if not pending:
        logger.warning("[market_finalize_listing] NADA pendente em user_data")
        await context.bot.send_message(chat_id=chat_id, text="Nada pendente para vender. Volte e selecione o item novamente.")
        return

    pdata = player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {}) or {}

    try:
        if pending["type"] == "unique":
            base_id = (pending["item"] or {}).get("base_id") or (pending["item"] or {}).get("tpl") or (pending["item"] or {}).get("id")
            if base_id in EVOLUTION_ITEMS:
                await context.bot.send_message(chat_id=chat_id, text=EVOL_BLOCK_MSG, parse_mode="HTML")
                return

            item_payload = {"type": "unique", "uid": pending["uid"], "item": pending["item"]}
            listing = market_manager.create_listing(seller_id=user_id, item_payload=item_payload, unit_price=price, quantity=1)
        else:
            base_id = pending["base_id"]
            if base_id in EVOLUTION_ITEMS:
                await context.bot.send_message(chat_id=chat_id, text=EVOL_BLOCK_MSG, parse_mode="HTML")
                return

            pack_qty = int(pending.get("qty", 0))
            have = int(inv.get(base_id, 0))
            if pack_qty <= 0 or have < pack_qty:
                logger.warning("[market_finalize_listing] qty inválida: pack=%s have=%s", pack_qty, have)
                await context.bot.send_message(chat_id=chat_id, text="Quantidade inválida ou insuficiente.")
                return

            inv[base_id] = have - pack_qty
            pdata["inventory"] = inv
            player_manager.save_player_data(user_id, pdata)

            item_payload = {"type": "stack", "base_id": base_id, "qty": pack_qty}
            listing = market_manager.create_listing(seller_id=user_id, item_payload=item_payload, unit_price=price, quantity=1)

        context.user_data.pop("market_pending", None)
        context.user_data.pop("market_price", None)

        text = f"✅ Listagem #{listing['id']} criada."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("👤 Minhas Listagens", callback_data="market_my")],
                                     [InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]])
        if update.callback_query:
            await _safe_edit_or_send(update.callback_query, context, chat_id, text, kb)
        else:
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=kb, parse_mode='HTML')

        logger.info("[market_finalize_listing] OK -> #%s", listing["id"])

    except Exception as e:
        logger.exception("[market_finalize_listing] erro: %s", e)
        await context.bot.send_message(chat_id=chat_id, text="Falha ao criar a listagem. Tente novamente.")

# ==============================
#  Handlers (exports para este arquivo)
# ==============================
market_adventurer_handler = CallbackQueryHandler(market_adventurer, pattern=r'^market_adventurer$')
market_list_handler       = CallbackQueryHandler(market_list, pattern=r'^market_list$')
market_my_handler         = CallbackQueryHandler(market_my, pattern=r'^market_my$')
market_sell_handler       = CallbackQueryHandler(market_sell, pattern=r'^market_sell(:(\d+))?$')
market_buy_handler        = CallbackQueryHandler(market_buy, pattern=r'^market_buy_\d+$')
market_cancel_handler     = CallbackQueryHandler(market_cancel, pattern=r'^market_cancel_\d+$')
market_pick_unique_handler= CallbackQueryHandler(market_pick_unique, pattern=r'^market_pick_unique_')
market_pick_stack_handler = CallbackQueryHandler(market_pick_stack,  pattern=r'^market_pick_stack_')
market_qty_handler        = CallbackQueryHandler(market_choose_qty,  pattern=r'^market_qty_')
market_price_spin_handler    = CallbackQueryHandler(market_price_spin,    pattern=r'^mktp_(inc|dec)_[0-9]+$')
market_price_confirm_handler = CallbackQueryHandler(market_price_confirm, pattern=r'^mktp_confirm$')
market_cancel_new_handler = CallbackQueryHandler(market_cancel_new, pattern=r'^market_cancel_new$')