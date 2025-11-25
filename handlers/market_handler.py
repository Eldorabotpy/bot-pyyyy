# handlers/market_handler.py
import logging
from typing import List, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from modules import mission_manager, player_manager, game_data, file_id_manager, market_manager, clan_manager
from modules.market_manager import render_listing_line as _mm_render_listing_line
# Adicione este import junto com os outros de modules
from modules.player import inventory

LOG_GROUP_ID = -1002881364171
LOG_TOPIC_ID = 24475

# --- DISPLAY UTILS opcional ---
try:
    from modules import display_utils
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
#  BLOQUEIO: Itens Premium (Não vendáveis por Ouro)
# ==============================
EVOLUTION_ITEMS = {
    "emblema_guerreiro", "essencia_guardia", "essencia_furia", "selo_sagrado", "essencia_luz",
    "emblema_berserker", "totem_ancestral", "emblema_cacador", "essencia_precisao",
    "marca_predador", "essencia_fera", "emblema_monge", "reliquia_mistica", "essencia_ki",
    "emblema_mago", "essencia_arcana", "essencia_elemental", "grimorio_arcano",
    "emblema_bardo", "essencia_harmonia", "essencia_encanto", "batuta_maestria",
    "emblema_assassino", "essencia_sombra", "essencia_letal", "manto_eterno",
    "emblema_samurai", "essencia_corte", "essencia_disciplina", "lamina_sagrada",
}

SKILL_BOOK_ITEMS = {
    "tomo_passive_bulwark", "tomo_active_whirlwind", "tomo_active_holy_blessing", "tomo_passive_unstoppable",
    "tomo_active_unbreakable_charge", "tomo_passive_last_stand", "tomo_passive_animal_companion",
    "tomo_active_deadeye_shot", "tomo_passive_apex_predator", "tomo_active_iron_skin",
    "tomo_passive_elemental_strikes", "tomo_active_transcendence", "tomo_active_curse_of_weakness", 
    "tomo_passive_elemental_attunement", "tomo_active_meteor_swarm", "tomo_active_song_of_valor",
    "tomo_active_dissonant_melody", "tomo_passive_symphony_of_power", "tomo_active_shadow_strike", 
    "tomo_passive_potent_toxins", "tomo_active_dance_of_a_thousand_cuts", "tomo_passive_iai_stance",
    "tomo_active_parry_and_riposte", "tomo_active_banner_of_command", 
    "tomo_guerreiro_corte_perfurante", "tomo_berserker_golpe_selvagem", "tomo_cacador_flecha_precisa",
    "tomo_monge_rajada_de_punhos", "tomo_mago_bola_de_fogo", "tomo_bardo_melodia_restauradora",
    "tomo_assassino_ataque_furtivo", "tomo_samurai_corte_iaijutsu",
}

SKIN_BOX_ITEMS = {
    'caixa_guerreiro_armadura_negra', 'caixa_guerreiro_placas_douradas',
    'caixa_mago_traje_arcano', 'caixa_assassino_manto_espectral', 'caixa_cacador_patrulheiro_elfico',
    'caixa_berserker_pele_urso', 'caixa_monge_quimono_dragao', 'caixa_bardo_traje_maestro',
    'caixa_samurai_armadura_shogun', 'caixa_samurai_armadura_demoniaca', 'caixa_samurai_encarnacao_sangrenta',
    'caixa_samurai_guardiao_celestial', 'caixa_samurai_chama_aniquiladora', 
}

PREMIUM_BLOCK_LIST = EVOLUTION_ITEMS.union(SKILL_BOOK_ITEMS).union(SKIN_BOX_ITEMS)

PREMIUM_BLOCK_MSG = (
    "🚫 Este é um item premium (Evolução, Skill ou Skin) e não pode ser vendido "
    "no Mercado do Aventureiro (Ouro).\n\n"
    "Use a <b>🏛️ Casa de Leilões</b> (Diamantes) para negociar este item."
)

# ==============================
#  UTILS BÁSICOS
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
        if info: return dict(info)
    except Exception: pass
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

def _player_class_key(pdata: dict, fallback="guerreiro") -> str:
    for c in [(pdata.get("class") or pdata.get("classe")), pdata.get("class_type"), pdata.get("classe")]:
        if isinstance(c, dict): return c.get("type", "").strip().lower()
        if isinstance(c, str): return c.strip().lower()
    return fallback

def _cut_middle(s: str, maxlen: int = 56) -> str:
    s = (s or "").strip()
    return s if len(s) <= maxlen else s[:maxlen//2 - 1] + "… " + s[-maxlen//2:]

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except Exception: pass
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except Exception: pass
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

async def _send_with_media(chat_id: int, context: ContextTypes.DEFAULT_TYPE, caption: str, kb: InlineKeyboardMarkup, media_keys: List[str]):
    for key in media_keys:
        fd = file_id_manager.get_file_data(key)
        if fd and fd.get("id"):
            try:
                if fd.get("type") == "video":
                    await context.bot.send_video(chat_id=chat_id, video=fd["id"], caption=caption, reply_markup=kb, parse_mode="HTML")
                else:
                    await context.bot.send_photo(chat_id=chat_id, photo=fd["id"], caption=caption, reply_markup=kb, parse_mode="HTML")
                return
            except Exception: continue
    await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=kb, parse_mode="HTML")

# ==============================
#  RENDERIZAÇÃO DE ITENS (UNIQUE/STACK)
# ==============================
RARITY_LABEL = {"comum": "Comum", "bom": "Boa", "raro": "Rara", "epico": "Épica", "lendario": "Lendária"}
_CLASS_DMG_EMOJI_FALLBACK = {"guerreiro": "⚔️", "berserker": "🪓", "cacador": "🏹", "assassino": "🗡", "bardo": "🎵", "monge": "🙏", "mago": "✨", "samurai": "🗡"}
_STAT_EMOJI_FALLBACK = {"dmg": "🗡", "hp": "❤️‍🩹", "defense": "🛡️", "initiative": "🏃", "luck": "🍀", "forca": "💪", "inteligencia": "🧠", "furia": "🔥"}

def _class_dmg_emoji(pclass: str) -> str:
    return getattr(game_data, "CLASS_DMG_EMOJI", {}).get((pclass or "").lower(), _CLASS_DMG_EMOJI_FALLBACK.get((pclass or "").lower(), "🗡"))

def _stat_emoji(stat: str, pclass: str) -> str:
    s = (stat or "").lower()
    if s == "dmg": return _class_dmg_emoji(pclass)
    return _STAT_EMOJI_FALLBACK.get(s, "❔")

def _render_unique_line_safe(inst: dict, pclass: str) -> str:
    try: return display_utils.formatar_item_para_exibicao(inst)
    except Exception: pass
    
    base_id = inst.get("base_id") or inst.get("tpl") or "item"
    info = _get_item_info(base_id)
    name = inst.get("display_name") or info.get("display_name") or base_id
    emoji = inst.get("emoji") or info.get("emoji") or _class_dmg_emoji(pclass)
    tier = inst.get("tier", 1)
    rarity = RARITY_LABEL.get(str(inst.get("rarity", "comum")).lower(), "Comum")
    
    stats = []
    ench = inst.get("enchantments") or {}
    if isinstance(ench, dict):
        for k, v in ench.items():
            if isinstance(v, dict) and "value" in v:
                stats.append(f"{_stat_emoji(k, pclass)}+{v['value']}")
    stats_str = ", ".join(stats[:3]) if stats else ""
    return f"{emoji} {name} [T{tier}] [{rarity}] {stats_str}"

# ==============================
#  MERCADO - MENUS PRINCIPAIS
# ==============================
async def market_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎒 𝐌𝐞𝐫𝐜𝐚𝐝𝐨 𝐝𝐨 𝐀𝐯𝐞𝐧𝐭𝐮𝐫𝐞𝐢𝐫𝐨", callback_data="market_adventurer")],
        [InlineKeyboardButton(" 🏛️ 𝐂𝐨𝐦𝐞́𝐫𝐜𝐢𝐨 𝐝𝐞 𝐑𝐞𝐥𝐢́𝐪𝐮𝐢𝐚𝐬 💎 ", callback_data="gem_market_main")],
        [InlineKeyboardButton("🏰 𝐋𝐨𝐣𝐚 𝐝𝐨 𝐑𝐞𝐢𝐧𝐨", callback_data="market_kingdom")],
        [InlineKeyboardButton("💎 𝐋𝐨𝐣𝐚 𝐝𝐞 𝐆𝐞𝐦𝐚𝐬", callback_data="gem_shop")],
        [InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="continue_after_action")],
    ])
    try: await q.delete_message()
    except Exception: pass 
    await _send_with_media(chat_id, context, "🛒 <b>Mercado</b>\nEscolha uma opção:", kb, ["market", "mercado_principal"])

async def market_adventurer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Listagens (Ver Itens)", callback_data="market_list")],
        [InlineKeyboardButton("➕ Vender Item", callback_data="market_sell:1")],
        [InlineKeyboardButton("👤 Minhas Listagens", callback_data="market_my")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market")],
    ])
    text = "🎒 <b>Mercado do Aventureiro</b>\nCompre e venda itens com outros jogadores."
    try: await q.delete_message()
    except Exception: pass
    await _send_with_media(update.effective_chat.id, context, text, kb, ["mercado_aventureiro", "market_adventurer"])

async def market_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    pdata = await player_manager.get_player_data(user_id)
    is_premium = player_manager.has_premium_plan(pdata)

    listings = market_manager.list_active(viewer_id=user_id, page=1, page_size=20)
    if not listings:
        await _safe_edit_or_send(q, context, update.effective_chat.id, "Não há listagens ativas.", 
                                 InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]]))
        return

    lines = ["📦 <b>Listagens ativas</b>\n"]
    if not is_premium: lines.append("<i>Apenas Apoiadores podem comprar.</i>\n")
    
    kb = []
    for l in listings[:30]:
        lines.append("• " + _mm_render_listing_line(l, viewer_player_data=pdata, show_price_per_unit=True))
        if is_premium and int(l.get("seller_id", 0)) != user_id:
            btn_txt = f"🔒 Comprar #{l['id']}" if l.get("target_buyer_id") else f"Comprar #{l['id']}"
            kb.append([InlineKeyboardButton(btn_txt, callback_data=f"market_buy_{l['id']}")])
    
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])
    await _safe_edit_or_send(q, context, update.effective_chat.id, "\n".join(lines), InlineKeyboardMarkup(kb))

async def market_my(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    pdata = await player_manager.get_player_data(user_id)
    
    my = market_manager.list_by_seller(user_id)
    if not my:
        await _safe_edit_or_send(q, context, update.effective_chat.id, "Você não tem listagens.", 
                                 InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]]))
        return

    lines = ["👤 <b>Minhas listagens</b>\n"]
    kb = []
    for l in my:
        lines.append("• " + _mm_render_listing_line(l, viewer_player_data=pdata, show_price_per_unit=True))
        kb.append([InlineKeyboardButton(f"Cancelar #{l['id']}", callback_data=f"market_cancel_{l['id']}")])
    
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])
    await _safe_edit_or_send(q, context, update.effective_chat.id, "\n".join(lines), InlineKeyboardMarkup(kb))

# ==============================
#  FLUXO DE VENDA (SELEÇÃO -> LOTES -> PREÇO -> TIPO)
# ==============================
async def market_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    
    try: page = int(q.data.split(':')[1])
    except: page = 1
    
    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {}) or {}
    pclass = _player_class_key(pdata)
    
    sellable = []
    # COLETA ITENS (Com proteção)
    for uid, inst in inv.items():
        if isinstance(inst, dict):
            if inst.get("base_id") not in PREMIUM_BLOCK_LIST:
                # --- PROTEÇÃO DE ITEM BUGADO ---
                # Simula o tamanho do callback
                cb_len = len(f"market_pick_unique_{uid}")
                if cb_len > 60:
                    print(f"⚠️ ITEM BLOQUEANDO O MENU: {inst.get('name')} (ID muito longo: {uid})")
                    # Pula este item para não travar o bot
                    continue
                
                sellable.append({"type": "unique", "uid": uid, "inst": inst, "sort": inst.get("base_id")})
                
    for bid, qty in inv.items():
        if isinstance(qty, (int, float)) and qty > 0 and bid not in PREMIUM_BLOCK_LIST:
            sellable.append({"type": "stack", "base_id": bid, "qty": int(qty), "sort": bid})
    
    sellable.sort(key=lambda x: x["sort"] or "")
    
    ITEMS_PER_PAGE = 8
    total = len(sellable)
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    items_page = sellable[start:end]
    
    if not sellable:
        await _safe_edit_or_send(q, context, update.effective_chat.id, 
            "🎒 <b>Inventário vazio ou itens não listáveis.</b>\n\n"
            "<i>Nota: Itens com IDs corrompidos (muito longos) foram ocultados por segurança.</i>", 
            InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]]))
        return

    kb = []
    for it in items_page:
        if it["type"] == "unique":
            txt = _render_unique_line_safe(it["inst"], pclass)
            kb.append([InlineKeyboardButton(_cut_middle(txt, 56), callback_data=f"market_pick_unique_{it['uid']}")])
        else:
            name = _item_label_from_base(it["base_id"])
            kb.append([InlineKeyboardButton(f"📦 {name} ({it['qty']}x)", callback_data=f"market_pick_stack_{it['base_id']}")])
            
    nav = []
    if page > 1: nav.append(InlineKeyboardButton("⬅️ Ant", callback_data=f"market_sell:{page-1}"))
    if end < total: nav.append(InlineKeyboardButton("Prox ➡️", callback_data=f"market_sell:{page+1}"))
    if nav: kb.append(nav)
    kb.append([InlineKeyboardButton("⬅️ Voltar ao Mercado", callback_data="market_adventurer")])
    
    await _safe_edit_or_send(q, context, update.effective_chat.id, f"➕ <b>Vender Item</b> (Página {page})", InlineKeyboardMarkup(kb))

# --- SELEÇÃO DE ITEM ---
async def market_pick_unique(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.data.replace("market_pick_unique_", "")
    user_id = q.from_user.id
    
    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {}) or {}
    if uid not in inv:
        await q.answer("Item não encontrado.", show_alert=True); return
    
    inst = inv[uid]
    if inst.get("base_id") in PREMIUM_BLOCK_LIST:
        await q.answer(PREMIUM_BLOCK_MSG, show_alert=True, parse_mode="HTML"); return

    # Remove item do inventário para pendência
    del inv[uid]
    pdata["inventory"] = inv
    await player_manager.save_player_data(user_id, pdata)
    
    context.user_data["market_pending"] = {"type": "unique", "uid": uid, "item": inst}
    context.user_data["market_price"] = 50
    await _show_price_spinner(q, context, update.effective_chat.id, "Defina o <b>preço</b> deste item:")

async def market_pick_stack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    base_id = q.data.replace("market_pick_stack_", "")
    user_id = q.from_user.id
    
    if base_id in PREMIUM_BLOCK_LIST:
        await q.answer(PREMIUM_BLOCK_MSG, show_alert=True, parse_mode="HTML"); return

    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {}) or {}
    qty = int(inv.get(base_id, 0))
    
    if qty <= 0:
        await q.answer("Quantidade insuficiente.", show_alert=True); return
        
    context.user_data["market_pending"] = {"type": "stack", "base_id": base_id, "qty_have": qty, "qty": 1} # qty = pack_size
    await _show_pack_qty_spinner(q, context, update.effective_chat.id)

# --- SPINNERS (Pack, Lote, Preço) ---
def _render_spinner_kb(value, prefix_inc, prefix_dec, label, confirm_cb):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("-100", callback_data=f"{prefix_dec}100"),
            InlineKeyboardButton("-10", callback_data=f"{prefix_dec}10"),
            InlineKeyboardButton("-1", callback_data=f"{prefix_dec}1"),
            InlineKeyboardButton("+1", callback_data=f"{prefix_inc}1"),
            InlineKeyboardButton("+10", callback_data=f"{prefix_inc}10"),
            InlineKeyboardButton("+100", callback_data=f"{prefix_inc}100")
        ],
        [InlineKeyboardButton(f"{label}: {value}", callback_data="noop")],
        [InlineKeyboardButton("✅ Confirmar", callback_data=confirm_cb), InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]
    ])

async def _show_pack_qty_spinner(q, context, chat_id):
    pending = context.user_data.get("market_pending")
    cur = pending["qty"]
    max_val = pending["qty_have"]
    item_name = _item_label_from_base(pending["base_id"])
    kb = _render_spinner_kb(cur, "mkt_pack_inc_", "mkt_pack_dec_", "Itens/Lote", "mkt_pack_confirm")
    await _safe_edit_or_send(q, context, chat_id, f"Item: <b>{item_name}</b> (Total: {max_val})\n\nDefina o tamanho do lote:", kb)

async def market_pack_qty_spin(update, context):
    q = update.callback_query; await q.answer()
    pending = context.user_data.get("market_pending")
    if not pending: await market_cancel_new(update, context); return
    
    action = q.data
    step = int(action.split("_")[-1])
    if "_inc_" in action: pending["qty"] = min(pending["qty_have"], pending["qty"] + step)
    else: pending["qty"] = max(1, pending["qty"] - step)
    
    context.user_data["market_pending"] = pending
    await _show_pack_qty_spinner(q, context, update.effective_chat.id)

async def market_pack_qty_confirm(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["market_lote_qty"] = 1
    await _show_lote_qty_spinner(q, context, update.effective_chat.id)

async def _show_lote_qty_spinner(q, context, chat_id):
    pending = context.user_data.get("market_pending")
    pack_size = pending["qty"]
    max_lotes = max(1, pending["qty_have"] // pack_size)
    context.user_data["market_lote_max"] = max_lotes
    cur_lotes = min(context.user_data.get("market_lote_qty", 1), max_lotes)
    context.user_data["market_lote_qty"] = cur_lotes
    
    kb = _render_spinner_kb(cur_lotes, "mkt_lote_inc_", "mkt_lote_dec_", "Qtd Lotes", "mkt_lote_confirm")
    await _safe_edit_or_send(q, context, chat_id, f"Tamanho do Lote: {pack_size}\n\nDefina quantos lotes vender:", kb)

async def market_lote_qty_spin(update, context):
    q = update.callback_query; await q.answer()
    max_lotes = context.user_data.get("market_lote_max", 1)
    cur = context.user_data.get("market_lote_qty", 1)
    
    action = q.data
    step = int(action.split("_")[-1])
    if "_inc_" in action: cur = min(max_lotes, cur + step)
    else: cur = max(1, cur - step)
    
    context.user_data["market_lote_qty"] = cur
    await _show_lote_qty_spinner(q, context, update.effective_chat.id)

async def market_lote_qty_confirm(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["market_price"] = 10
    await _show_price_spinner(q, context, update.effective_chat.id)

async def _show_price_spinner(q, context, chat_id, text="Defina o preço:"):
    price = context.user_data.get("market_price", 10)
    kb = _render_spinner_kb(price, "mktp_inc_", "mktp_dec_", "Preço", "mktp_confirm")
    await _safe_edit_or_send(q, context, chat_id, f"{text} <b>{price} 🪙</b>", kb)

async def market_price_spin(update, context):
    q = update.callback_query; await q.answer()
    cur = context.user_data.get("market_price", 10)
    action = q.data
    step = int(action.split("_")[-1])
    if "_inc_" in action: cur += step
    else: cur = max(1, cur - step)
    context.user_data["market_price"] = cur
    await _show_price_spinner(q, context, update.effective_chat.id)

# ==============================
#  DECISÃO DE VENDA (PÚBLICA / PRIVADA)
# ==============================
async def market_price_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ao confirmar o preço, pergunta se é Venda Pública ou Privada."""
    q = update.callback_query
    await q.answer()
    price = context.user_data.get("market_price", 1)
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 Venda Pública (Todos)", callback_data="mkt_type_public")],
        [InlineKeyboardButton("🔒 Venda Privada (VIP)", callback_data="mkt_type_private")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]
    ])
    await _safe_edit_or_send(q, context, update.effective_chat.id, 
                             f"💰 Preço: <b>{price} 🪙</b>\n\nComo deseja anunciar?", kb)

async def market_type_public(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data.pop("market_target_id", None)
    context.user_data.pop("market_target_name", None)
    price = context.user_data.get("market_price", 1)
    await market_finalize_listing(update, context, price)

async def market_type_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    pdata = await player_manager.get_player_data(user_id)
    
    if not player_manager.has_premium_plan(pdata):
        await q.answer("🔒 Recurso VIP!", show_alert=True); return
        
    await q.answer()
    context.user_data["awaiting_market_name"] = True
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]])
    await _safe_edit_or_send(q, context, update.effective_chat.id, 
                             "🔒 <b>VENDA PRIVADA</b>\n\nDigite o <b>nome exato</b> do jogador no chat:", kb)

async def market_catch_input_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.user_data.get("awaiting_market_name"): return 

    context.user_data.pop("awaiting_market_name", None)
    target_name = update.message.text.strip()
    
    found = await player_manager.find_player_by_name(target_name)
    if not found:
        await update.message.reply_text(f"❌ Jogador <b>{target_name}</b> não encontrado. Venda cancelada.", parse_mode="HTML")
        return

    target_id, target_pdata = found
    if target_id == user_id:
        await update.message.reply_text("❌ Não pode vender para si mesmo.")
        return

    context.user_data["market_target_id"] = target_id
    context.user_data["market_target_name"] = target_pdata.get("character_name", target_name)
    
    price = context.user_data.get("market_price", 1)
    await market_finalize_listing(update, context, price)

# ==============================
#  FINALIZAÇÃO E CANCELAMENTO
# ==============================
async def market_finalize_listing(update: Update, context: ContextTypes.DEFAULT_TYPE, price: int):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    pending = context.user_data.get("market_pending")
    
    if not pending:
        await context.bot.send_message(chat_id, "Erro: Nenhuma venda pendente.")
        return

    target_id = context.user_data.get("market_target_id")
    target_name = context.user_data.get("market_target_name")
    
    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {}) or {}

    try:
        if pending["type"] == "unique":
            item_payload = {"type": "unique", "uid": pending["uid"], "item": pending["item"]}
            listing = market_manager.create_listing(
                seller_id=user_id, item_payload=item_payload, unit_price=price, quantity=1,
                target_buyer_id=target_id, target_buyer_name=target_name
            )
        else: # Stack
            base_id = pending["base_id"]
            pack_size = pending["qty"]
            lote_qty = context.user_data.get("market_lote_qty", 1)
            total_remove = pack_size * lote_qty
            
            # Remove do inventário
            have = int(inv.get(base_id, 0))
            if have < total_remove:
                await context.bot.send_message(chat_id, "Quantidade insuficiente no inventário.")
                return
                
            inv[base_id] = have - total_remove
            if inv[base_id] <= 0: del inv[base_id]
            pdata["inventory"] = inv
            await player_manager.save_player_data(user_id, pdata)
            
            item_payload = {"type": "stack", "base_id": base_id, "qty": pack_size}
            listing = market_manager.create_listing(
                seller_id=user_id, item_payload=item_payload, unit_price=price, quantity=lote_qty,
                target_buyer_id=target_id, target_buyer_name=target_name
            )

        # Limpa tudo
        context.user_data.pop("market_pending", None)
        context.user_data.pop("market_price", None)
        context.user_data.pop("market_lote_qty", None)
        context.user_data.pop("market_lote_max", None)
        context.user_data.pop("market_target_id", None)
        context.user_data.pop("market_target_name", None)

        msg = f"✅ <b>Venda Privada!</b>\nReservado para: <b>{target_name}</b>" if target_name else f"✅ Listagem #{listing['id']} criada!"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("👤 Minhas Listagens", callback_data="market_my")]])
        await context.bot.send_message(chat_id, msg, reply_markup=kb, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Erro ao criar listing: {e}")
        await context.bot.send_message(chat_id, "Erro ao criar listagem. Item devolvido (verifique logs).")
        # Lógica de devolução de emergência simplificada:
        if pending["type"] == "unique":
            new_uid = f"{pending['uid']}_ret"
            inv[new_uid] = pending["item"]
            pdata["inventory"] = inv
            await player_manager.save_player_data(user_id, pdata)

async def market_cancel_new(update, context):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id # Importante: Pega o ID do chat
    
    # --- 1. Devolve o item pendente (Segurança) ---
    pending = context.user_data.pop("market_pending", None)
    if pending and pending.get("type") == "unique":
        pdata = await player_manager.get_player_data(user_id)
        inv = pdata.get("inventory", {}) or {}
        uid = pending["uid"]
        # Evita sobrescrever se algo estranho aconteceu
        new_uid = uid if uid not in inv else f"{uid}_back"
        inv[new_uid] = pending["item"]
        pdata["inventory"] = inv
        await player_manager.save_player_data(user_id, pdata)

    # --- 2. Limpa os estados temporários ---
    context.user_data.pop("market_price", None)
    context.user_data.pop("awaiting_market_name", None)
    context.user_data.pop("market_lote_qty", None)
    context.user_data.pop("market_lote_max", None)
    
    # --- 3. CORREÇÃO DO ERRO VISUAL ---
    # Em vez de tentar editar (que falha em fotos), nós DELETAMOS a mensagem da foto.
    try:
        await q.delete_message()
    except Exception:
        pass # Se não der pra deletar, ignora e só manda a msg nova
        
    # Envia a mensagem de cancelado limpa
    await context.bot.send_message(
        chat_id=chat_id,
        text="❌ Operação cancelada.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Voltar ao Mercado", callback_data="market_adventurer")]
        ])
    )

async def market_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try: await q.answer()
    except: pass

    buyer_id = q.from_user.id
    chat_id = update.effective_chat.id
    
    try:
        lid = int(q.data.replace("market_buy_", ""))
    except ValueError:
        return

    try:
        # 1. Carrega Comprador
        buyer = await player_manager.get_player_data(buyer_id)
        if not player_manager.has_premium_plan(buyer):
            await q.answer("Apenas VIPs podem comprar.", show_alert=True)
            return

        # 2. Compra no DB
        updated_listing, cost = market_manager.purchase_listing(
            buyer_id=buyer_id, listing_id=lid, quantity=1
        )
        
        # 3. Processa Entrega
        item_data = updated_listing.get("item", {})
        item_type = item_data.get("type")
        item_name_display = "Item"

        if item_type == "stack":
            base_id = item_data.get("base_id")
            qty_per_lote = int(item_data.get("qty", 1))
            inventory.add_item_to_inventory(buyer, base_id, qty_per_lote)
            name = _item_label_from_base(base_id)
            item_name_display = f"{name} x{qty_per_lote}"

        elif item_type == "unique":
            real_item = item_data.get("item")
            if real_item:
                inventory.add_unique_item(buyer, real_item)
                item_name_display = real_item.get("display_name") or "Equipamento"
            else:
                raise Exception("Dados vazios.")

        # 4. Salva Jogador
        await player_manager.save_player_data(buyer_id, buyer)

        # 5. Feedback (Sucesso)
        await _safe_edit_or_send(q, context, chat_id, 
            f"✅ <b>Compra realizada!</b>\n\n"
            f"📦 <b>Recebido:</b> {item_name_display}\n"
            f"💰 <b>Pago:</b> {cost} 🪙",
            InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_list")]])
        )

        # === 6. LOG COM DEBUG DE ERRO ===
        try:
            buyer_name = buyer.get("character_name") or q.from_user.first_name
            seller_id = updated_listing.get("seller_id")
            seller_name = "Alguém"
            
            if seller_id:
                seller_data = await player_manager.get_player_data(seller_id)
                if seller_data:
                    seller_name = seller_data.get("character_name", "Vendedor")

            log_text = (
                f"💸 <b>NOVA TRANSAÇÃO!</b>\n\n"
                f"👤 <b>Comprador:</b> {buyer_name}\n"
                f"📦 <b>Item:</b> {item_name_display}\n"
                f"💰 <b>Valor:</b> {cost} 🪙\n"
                f"🤝 <b>Vendedor:</b> {seller_name}"
            )
            
            # Tenta enviar com os IDs configurados no topo do arquivo
            await context.bot.send_message(
                chat_id=LOG_GROUP_ID, 
                message_thread_id=LOG_TOPIC_ID, 
                text=log_text, 
                parse_mode="HTML"
            )
            
        except Exception as e_log:
            # --- AQUI ESTÁ O DEBUG ---
            logger.error(f"Erro Log: {e_log}")
            # Avisa você no chat privado qual foi o erro
            await context.bot.send_message(
                chat_id=chat_id, 
                text=f"⚠️ <b>Aviso de Admin:</b> O log não foi enviado.\nErro: <code>{e_log}</code>",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Erro compra {lid}: {e}")
        await context.bot.send_message(chat_id, f"❌ Erro: {e}")

async def market_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    lid = int(q.data.replace("market_cancel_", ""))
    user_id = q.from_user.id
    
    try:
        # Lógica simplificada de cancelamento: valida dono, remove listing, devolve item
        listing = market_manager.get_listing(lid)
        if not listing or int(listing["seller_id"]) != user_id:
            await q.answer("Erro ao cancelar.", show_alert=True); return
            
        market_manager.delete_listing(lid) # Marca como inativo
        
        # Devolve item (simplificado, assume que market_manager não devolve auto, fazemos manual)
        pdata = await player_manager.get_player_data(user_id)
        it = listing["item"]
        if it["type"] == "stack":
            player_manager.add_item_to_inventory(pdata, it["base_id"], int(it["qty"]) * int(listing["quantity"]))
        else:
            inv = pdata.get("inventory", {})
            inv[it["uid"]] = it["item"]
            pdata["inventory"] = inv
        await player_manager.save_player_data(user_id, pdata)
        
        await _safe_edit_or_send(q, context, update.effective_chat.id, "✅ Anúncio cancelado e item devolvido.", 
                                 InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_my")]]))
    except Exception as e:
        logger.error(f"Erro cancel: {e}")
        await q.answer("Erro ao cancelar.", show_alert=True)

# ==============================
#  EXPORTS
# ==============================
market_open_handler = CallbackQueryHandler(market_open, pattern=r'^market$')
market_adventurer_handler = CallbackQueryHandler(market_adventurer, pattern=r'^market_adventurer$')
market_list_handler = CallbackQueryHandler(market_list, pattern=r'^market_list$')
market_my_handler = CallbackQueryHandler(market_my, pattern=r'^market_my$')
market_sell_handler = CallbackQueryHandler(market_sell, pattern=r'^market_sell(:(\d+))?$')
market_buy_handler = CallbackQueryHandler(market_buy, pattern=r'^market_buy_\d+$')
market_cancel_handler = CallbackQueryHandler(market_cancel, pattern=r'^market_cancel_\d+$')
market_pick_unique_handler = CallbackQueryHandler(market_pick_unique, pattern=r'^market_pick_unique_')
market_pick_stack_handler = CallbackQueryHandler(market_pick_stack, pattern=r'^market_pick_stack_')

market_pack_qty_spin_handler = CallbackQueryHandler(market_pack_qty_spin, pattern=r'^mkt_pack_(inc|dec)_[0-9]+$')
market_pack_qty_confirm_handler = CallbackQueryHandler(market_pack_qty_confirm, pattern=r'^mkt_pack_confirm$')
market_lote_qty_spin_handler = CallbackQueryHandler(market_lote_qty_spin, pattern=r'^mkt_lote_(inc|dec)_[0-9]+$')
market_lote_qty_confirm_handler = CallbackQueryHandler(market_lote_qty_confirm, pattern=r'^mkt_lote_confirm$')
market_price_spin_handler = CallbackQueryHandler(market_price_spin, pattern=r'^mktp_(inc|dec)_[0-9]+$')
market_price_confirm_handler = CallbackQueryHandler(market_price_confirm, pattern=r'^mktp_confirm$')
market_cancel_new_handler = CallbackQueryHandler(market_cancel_new, pattern=r'^market_cancel_new$')

# Handlers de Venda Privada (Botão + Texto)
from handlers.market_handler import market_type_public, market_type_private, market_catch_input_text
# Nota: Ao importar dentro do próprio arquivo para exportar, o Python entende.
# Se der erro circular, defina os handlers diretamente no registry usando as funções acima.