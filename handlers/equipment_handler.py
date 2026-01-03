# handlers/equipment_handler.py
# (VERSÃO BLINDADA: Compatível com Auth Híbrida)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, game_data
from modules import display_utils
from modules.player.stats import get_player_total_stats
from modules.auth_utils import get_current_player_id # ✅ IMPORT CRÍTICO

# Preferimos as constantes globais dos slots
try:
    from modules.game_data.equipment import SLOT_EMOJI as _SLOT_EMOJI, SLOT_ORDER as _SLOT_ORDER
    SLOT_EMOJIS = dict(_SLOT_EMOJI)
    SLOTS_ORDER = list(_SLOT_ORDER)
except Exception:
    # fallback seguro
    SLOTS_ORDER = ["arma", "elmo", "armadura", "calca", "luvas", "botas", "anel", "colar", "brinco"]
    SLOT_EMOJIS = {
        "arma": "⚔️", "elmo": "🪖", "armadura": "👕", "calca": "👖",
        "luvas": "🧤", "botas": "🥾", "colar": "📿", "anel": "💍", "brinco": "🧿",
    }

SLOT_LABELS = {
    "arma": "𝐀𝐫𝐦𝐚",
    "armadura": "𝐀𝐫𝐦𝐚𝐝𝐮𝐫𝐚",
    "elmo": "𝐄𝐥𝐦𝐨",
    "calca": "𝐂𝐚𝐥𝐜̧𝐚",
    "luvas": "𝐋𝐮𝐯𝐚𝐬",
    "botas": "𝐁𝐨𝐭𝐚𝐬",
    "anel": "𝐀𝐧𝐞𝐥",
    "colar": "𝐂𝐨𝐥𝐚𝐫",
    "brinco": "𝐁𝐫𝐢𝐧𝐜𝐨",
}

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception: pass
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception: pass
    try:
        await query.delete_message()
    except Exception: pass
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

# =============================================================
# --- HELPERS DE SLOT E RENDERIZAÇÃO ---
# =============================================================
def _item_slot_from_base(base_id: str) -> str | None:
    if not base_id: return None
    info = {}
    try: info = game_data.get_item_info(base_id) or {}
    except Exception: info = getattr(game_data, "ITEMS_DATA", {}).get(base_id) or {}

    slot = info.get("slot")
    if slot and isinstance(slot, str) and slot.lower() in SLOTS_ORDER:
        return slot.lower()
            
    slot_type = info.get("type")
    if slot_type and isinstance(slot_type, str) and slot_type.lower() in SLOTS_ORDER:
        return slot_type.lower()
            
    return None

def _render_item_line_full(inst: dict) -> str:
    try:
        return display_utils.formatar_item_para_exibicao(inst)
    except Exception:
        base_id = inst.get("base_id", "")
        info = (getattr(game_data, "ITEM_BASES", {}).get(base_id) or
                getattr(game_data, "ITEMS_DATA", {}).get(base_id) or {})
        name = info.get("display_name") or base_id.replace("_", " ").title()
        rar = (inst.get("rarity") or "").capitalize()
        return f"{name} [{rar}]" if rar else name

def _list_equippable_items_for_slot(player_data: dict, slot: str) -> list[tuple[str, str]]:
    inv = player_data.get("inventory", {}) or {}
    out: list[tuple[str, str]] = []
    for uid, val in inv.items():
        if not isinstance(val, dict): continue
        if _item_slot_from_base(val.get("base_id")) != slot: continue
        pretty = _render_item_line_full(val)
        out.append((uid, pretty))
    out.sort(key=lambda t: t[1])
    return out


# =========================
# HUB PRINCIPAL (Estilizado)
# =========================
async def equipment_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    # ✅ ID DA SESSÃO
    user_id = get_current_player_id(update, context)
    chat_id = q.message.chat.id 

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        await _safe_edit_or_send(q, context, chat_id, "❌ 𝑵𝒂̃𝒐 𝒆𝒏𝒄𝒐𝒏𝒕𝒓𝒆𝒊 𝒔𝒆𝒖𝒔 𝒅𝒂𝒅𝒐𝒔. 𝑼𝒔𝒆 /𝒔𝒕𝒂𝒓𝒕.")
        return

    # --- 1. BLOCO DE STATUS ---
    total_stats = await get_player_total_stats(pdata)
    
    hp_total = int(total_stats.get('max_hp', 0))
    atk_total = int(total_stats.get('attack', 0))
    def_total = int(total_stats.get('defense', 0))
    ini_total = int(total_stats.get('initiative', 0))
    luck_total = int(total_stats.get('luck', 0))

    stats_block = (
        f"📊 <b>RESUMO DE ATRIBUTOS</b>\n"
        f"├─ 🧡 <b>HP....</b> <code>{hp_total}</code>\n"
        f"├─ ⚔️ <b>ATK...</b> <code>{atk_total}</code>\n"
        f"├─ 🛡 <b>DEF...</b> <code>{def_total}</code>\n"
        f"├─ 🏃 <b>INI...</b> <code>{ini_total}</code>\n"
        f"└─ 🍀 <b>LUK...</b> <code>{luck_total}</code>"
    )

    # --- 2. LISTA DE EQUIPAMENTOS ---
    inv = pdata.get("inventory", {}) or {}
    eq = pdata.get("equipment", {}) or {}

    equip_lines = ["\n🛡 <b>SET DE EQUIPAMENTOS</b>"]
    
    for slot in SLOTS_ORDER:
        uid = eq.get(slot)
        slot_label = SLOT_LABELS.get(slot, slot.title()).upper() 
        slot_emoji = SLOT_EMOJIS.get(slot, '❓')
        
        header = f"<b>[ {slot_emoji} {slot_label} ]</b> ──────────────"

        if uid and isinstance(inv.get(uid), dict):
            item_line = _render_item_line_full(inv[uid])
            block = f"{header}\n ╰┈➤ {item_line}"
        else:
            block = f"{header}\n ╰┈➤ <code>— Vazio —</code>"
            
        equip_lines.append(block)

    text = stats_block + "\n".join(equip_lines)

    # --- 3. TECLADO ---
    keyboard: list[list[InlineKeyboardButton]] = []
    
    # Botões de Desequipar (❌)
    row: list[InlineKeyboardButton] = []
    for slot in SLOTS_ORDER:
        if eq.get(slot):
            row.append(InlineKeyboardButton(f"❌ {SLOT_EMOJIS.get(slot,'')}", callback_data=f"equip_unequip_{slot}"))
            if len(row) == 3:
                keyboard.append(row); row = []
    if row: keyboard.append(row)

    # Botões de Escolher Slot
    row = []
    for slot in SLOTS_ORDER:
        row.append(InlineKeyboardButton(f"{SLOT_EMOJIS.get(slot,'')} {SLOT_LABELS.get(slot, slot.title())}",
                                          callback_data=f"equip_slot_{slot}"))
        if len(row) == 3:
            keyboard.append(row); row = []
    if row: keyboard.append(row)

    keyboard.append([InlineKeyboardButton("📦 𝐀𝐛𝐫𝐢𝐫 𝐈𝐧𝐯𝐞𝐧𝐭𝐚́𝐫𝐢𝐨", callback_data="inventory_CAT_especial_PAGE_1")]) 
    keyboard.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="profile")]) 

    await _safe_edit_or_send(q, context, chat_id, text, InlineKeyboardMarkup(keyboard), parse_mode="HTML")


# =========================
# HANDLERS DE AÇÃO
# =========================
async def equip_slot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    slot = q.data.replace("equip_slot_", "")
    
    # ✅ ID DA SESSÃO
    user_id = get_current_player_id(update, context)
    chat_id = q.message.chat.id

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        await _safe_edit_or_send(q, context, chat_id, "❌ 𝑵𝒂̃𝒐 𝒆𝒏𝒄𝒐𝒏𝒕𝒓𝒆𝒊 𝒔𝒆𝒖𝒔 𝒅𝒂𝒅𝒐𝒔. 𝑼𝒔𝒆 /𝒔𝒕𝒂𝒓𝒕.")
        return

    st = (pdata.get("player_state") or {}).get("action")
    if st not in (None, "idle"):
        await q.answer("𝑽𝒐𝒄𝒆̂ 𝒆𝒔𝒕𝒂́ 𝒐𝒄𝒖𝒑𝒂𝒅𝒐 𝒄𝒐𝒎 𝒐𝒖𝒕𝒓𝒂 𝒂𝒄̧𝒂̃𝒐 𝒂𝒈𝒐𝒓𝒂.", show_alert=True); return

    slot_label = SLOT_LABELS.get(slot, slot.capitalize())
    items = _list_equippable_items_for_slot(pdata, slot)

    if not items:
        kb = [[InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="equipment_menu")]]
        await _safe_edit_or_send(q, context, chat_id, f"𝑵𝒂̃𝒐 𝒉𝒂́ 𝒊𝒕𝒆𝒏𝒔 𝒆𝒒𝒖𝒊𝒑𝒂́𝒗𝒆𝒊𝒔 𝒑𝒂𝒓𝒂 <b>{slot_label}</b>.", InlineKeyboardMarkup(kb))
        return

    lines = [f"<b>𝑬𝒔𝒄𝒐𝒍𝒉𝒆𝒓 𝒑𝒂𝒓𝒂 {slot_label}</b>"]
    kb: list[list[InlineKeyboardButton]] = []
    for uid, pretty in items:
        txt = pretty if len(pretty) <= 60 else (pretty[:57] + "…")
        kb.append([InlineKeyboardButton(txt, callback_data=f"equip_pick_{uid}")])

    kb.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="equipment_menu")])
    await _safe_edit_or_send(q, context, chat_id, "\n".join(lines), InlineKeyboardMarkup(kb))

async def equip_pick_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.data.replace("equip_pick_", "")
    
    # ✅ ID DA SESSÃO
    user_id = get_current_player_id(update, context)
    chat_id = q.message.chat.id

    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return

    st = (pdata.get("player_state") or {}).get("action")
    if st not in (None, "idle"):
        await q.answer("𝑽𝒐𝒄𝒆̂ 𝒆𝒔𝒕𝒂́ 𝒐𝒄𝒖𝒑𝒂𝒅𝒐 𝒄𝒐𝒎 𝒐𝒖𝒕𝒓𝒂 𝒂𝒄̧𝒂̃𝒐 𝒂𝒈𝒐𝒓𝒂.", show_alert=True); return

    # O manager já deve estar preparado para aceitar ID str. Se não, avise.
    success, message = await player_manager.equip_unique_item_for_user(user_id, uid)
    if not success:
        await q.answer(message, show_alert=True); return

    await q.answer("𝑬𝒒𝒖𝒊𝒑𝒂𝒅𝒐!", show_alert=False)
    await equipment_menu(update, context)
    
async def equip_unequip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    slot = q.data.replace("equip_unequip_", "")
    
    user_id = get_current_player_id(update, context)
    
    # ✅ USA A FUNÇÃO CENTRALIZADA (unequip_item_for_user)
    # Note: Importamos de player_manager que agora deve expor unequip_item_for_user
    success, message = await player_manager.unequip_item_for_user(user_id, slot)
    
    if success:
        await q.answer("Removido e status atualizados!")
        await equipment_menu(update, context) # Recarrega o HUD com stats novos
    else:
        await q.answer(message, show_alert=True)

    

# ---------- Exporta handlers ----------
equipment_menu_handler   = CallbackQueryHandler(equipment_menu, pattern=r'^equipment_menu$')
equip_slot_handler       = CallbackQueryHandler(equip_slot_callback, pattern=r'^equip_slot_[A-Za-z_]+$')
equip_pick_handler       = CallbackQueryHandler(equip_pick_callback, pattern=r'^equip_pick_')
equip_unequip_handler    = CallbackQueryHandler(equip_unequip_callback, pattern=r'^equip_unequip_')