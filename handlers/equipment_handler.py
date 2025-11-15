# handlers/equipment_handler.py
# (VERSÃO CORRIGIDA - 'await' ADICIONADOS E '_item_slot_from_base' MELHORADO)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, game_data
from modules import display_utils  # usa formatar_item_para_exibicao para a linha bonita

# Preferimos as constantes globais dos slots (mesma ordem/emoji do inventário)
try:
    from modules.game_data.equipment import SLOT_EMOJI as _SLOT_EMOJI, SLOT_ORDER as _SLOT_ORDER
    SLOT_EMOJIS = dict(_SLOT_EMOJI)
    SLOTS_ORDER = list(_SLOT_ORDER)
except Exception:
    # fallback seguro
    SLOTS_ORDER = ["arma", "elmo", "armadura", "calca", "luvas", "botas", "anel", "colar", "brinco"]
    SLOT_EMOJIS = {
        "arma": "⚔️",
        "elmo": "🪖",
        "armadura": "👕",
        "calca": "👖",
        "luvas": "🧤",
        "botas": "🥾",
        "colar": "📿",
        "anel": "💍",
        "brinco": "🧿",
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
    except Exception:
        pass
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception:
        pass
    try:
        await query.delete_message()
    except Exception:
        pass
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)


# =============================================================
# --- INÍCIO DA CORREÇÃO DO BUG DA ARMADURA ---
# (Função _item_slot_from_base tornada mais inteligente)
# =============================================================
def _item_slot_from_base(base_id: str) -> str | None:
    """
    Descobre o slot do item base. Tenta "slot" primeiro, depois "type" como fallback.
    """
    if not base_id:
        return None
    
    info = {}
    try:
        # Tenta a função moderna primeiro (se existir em game_data/__init__.py)
        info = game_data.get_item_info(base_id) or {}
    except Exception:
        # Tenta o acesso legado direto ao ITEMS_DATA
        info = getattr(game_data, "ITEMS_DATA", {}).get(base_id) or {}

    # 1. Tenta a chave "slot" (ex: "slot": "armadura")
    slot = info.get("slot")
    if slot and isinstance(slot, str):
        slot_lower = slot.lower()
        if slot_lower in SLOTS_ORDER:
            return slot_lower
            
    # 2. Fallback: Tenta a chave "type" (ex: "type": "armadura")
    #    Isso corrige o bug dos itens T2 (Caçador, Mago, etc.)
    slot_type = info.get("type")
    if slot_type and isinstance(slot_type, str):
        slot_type_lower = slot_type.lower()
        # Verifica se o 'type' é um nome de slot válido
        if slot_type_lower in SLOTS_ORDER:
            return slot_type_lower
            
    return None # Não encontrou
# =============================================================
# --- FIM DA CORREÇÃO DO BUG DA ARMADURA ---
# =============================================================


def _render_item_line_full(inst: dict) -> str:
    """
    Usa o formato unificado:
      『[20/20] ⚔️ Katana Laminada [1][Bom]: 🥷 +1, 🍀 +1 』
    """
    try:
        return display_utils.formatar_item_para_exibicao(inst)
    except Exception:
        # fallback simples
        base_id = inst.get("base_id", "")
        info = (getattr(game_data, "ITEM_BASES", {}).get(base_id) or
                getattr(game_data, "ITEMS_DATA", {}).get(base_id) or {})
        name = info.get("display_name") or base_id.replace("_", " ").title()
        rar = (inst.get("rarity") or "").capitalize()
        return f"{name} [{rar}]" if rar else name


def _list_equippable_items_for_slot(player_data: dict, slot: str) -> list[tuple[str, str]]:
    """
    Retorna [(unique_id, label)] para o slot escolhido.
    """
    inv = player_data.get("inventory", {}) or {}
    out: list[tuple[str, str]] = []
    for uid, val in inv.items():
        if not isinstance(val, dict):
            continue
        # (Agora usa a função corrigida)
        if _item_slot_from_base(val.get("base_id")) != slot:
            continue
        pretty = _render_item_line_full(val)
        out.append((uid, pretty))
    out.sort(key=lambda t: t[1])  # estável
    return out


# =========================
# HUB (sem boneco)
# =========================
async def equipment_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Mostra:
      - lista do que está equipado (1 linha por slot), já no formato 『[...] …』
      - botões por slot para abrir a listagem (Escolher para {slot})
      - botões ❌ {ícone} para desequipar, apenas onde houver item
    """
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = q.message.chat.id 

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        await _safe_edit_or_send(q, context, chat_id, "❌ 𝑵𝒂̃𝒐 𝒆𝒏𝒄𝒐𝒏𝒕𝒓𝒆𝒊 𝒔𝒆𝒖𝒔 𝒅𝒂𝒅𝒐𝒔. 𝑼𝒔𝒆 /𝒔𝒕𝒂𝒓𝒕.")
        return

    inv = pdata.get("inventory", {}) or {}
    eq = pdata.get("equipment", {}) or {}

    lines = ["<b>𝑶 𝒒𝒖𝒆 𝒆𝒔𝒕𝒂́ 𝒆𝒒𝒖𝒊𝒑𝒂𝒅𝒐:</b>"]
    for slot in SLOTS_ORDER:
        uid = eq.get(slot)
        if uid and isinstance(inv.get(uid), dict):
            line = _render_item_line_full(inv[uid])
        else:
            line = "—"
        lines.append(f"{SLOT_EMOJIS.get(slot,'❓')} <b>{SLOT_LABELS.get(slot, slot.title())}:</b> {line}")

    text = "\n".join(lines)

    keyboard: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for slot in SLOTS_ORDER:
        if eq.get(slot):
            row.append(InlineKeyboardButton(f"❌ {SLOT_EMOJIS.get(slot,'❓')}", callback_data=f"equip_unequip_{slot}"))
            if len(row) == 3:
                keyboard.append(row); row = []
    if row:
        keyboard.append(row)

    row = []
    for slot in SLOTS_ORDER:
        row.append(InlineKeyboardButton(f"{SLOT_EMOJIS.get(slot,'❓')} {SLOT_LABELS.get(slot, slot.title())}",
                                          callback_data=f"equip_slot_{slot}"))
        if len(row) == 3:
            keyboard.append(row); row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("📦 𝐀𝐛𝐫𝐢𝐫 𝐈𝐧𝐯𝐞𝐧𝐭𝐚́𝐫𝐢𝐨", callback_data="inventory_CAT_especial_PAGE_1")]) 
    keyboard.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="profile")]) 

    await _safe_edit_or_send(q, context, chat_id, text, InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# =========================
# Listagem/Equipar/Remover
# =========================
async def equip_slot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista os itens equipáveis para o slot escolhido."""
    q = update.callback_query
    await q.answer()
    slot = q.data.replace("equip_slot_", "")
    user_id = q.from_user.id
    chat_id = q.message.chat.id

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        await _safe_edit_or_send(q, context, chat_id, "❌ 𝑵𝒂̃𝒐 𝒆𝒏𝒄𝒐𝒏𝒕𝒓𝒆𝒊 𝒔𝒆𝒖𝒔 𝒅𝒂𝒅𝒐𝒔. 𝑼𝒔𝒆 /𝒔𝒕𝒂𝒓𝒕.")
        return

    st = (pdata.get("player_state") or {}).get("action")
    if st not in (None, "idle"):
        await q.answer("𝑽𝒐𝒄𝒆̂ 𝒆𝒔𝒕𝒂́ 𝒐𝒄𝒖𝒑𝒂𝒅𝒐 𝒄𝒐𝒎 𝒐𝒖𝒕𝒓𝒂 𝒂𝒄̧𝒂̃𝒐 𝒂𝒈𝒐𝒓𝒂.", show_alert=True)
        return

    slot_label = SLOT_LABELS.get(slot, slot.capitalize() or "Equipamento")
    items = _list_equippable_items_for_slot(pdata, slot) # Síncrono

    if not items:
        kb = [[InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="equipment_menu")]]
        await _safe_edit_or_send(
            q, context, chat_id,
            f"𝑵𝒂̃𝒐 𝒉𝒂́ 𝒊𝒕𝒆𝒏𝒔 𝒆𝒒𝒖𝒊𝒑𝒂́𝒗𝒆𝒊𝒔 𝒑𝒂𝒓𝒂 <b>{slot_label}</b>.",
            InlineKeyboardMarkup(kb)
        )
        return

    lines = [f"<b>𝑬𝒔𝒄𝒐𝒍𝒉𝒆𝒓 𝒑𝒂𝒓𝒂 {slot_label}</b>"]
    kb: list[list[InlineKeyboardButton]] = []
    for uid, pretty in items:
        txt = pretty if len(pretty) <= 60 else (pretty[:57] + "…")
        kb.append([InlineKeyboardButton(txt, callback_data=f"equip_pick_{uid}")])

    kb.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="equipment_menu")])
    await _safe_edit_or_send(q, context, chat_id, "\n".join(lines), InlineKeyboardMarkup(kb))

async def equip_pick_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Equipa o unique_id escolhido usando a lógica central do player_manager."""
    q = update.callback_query
    await q.answer()
    uid = q.data.replace("equip_pick_", "")
    user_id = q.from_user.id
    chat_id = q.message.chat_id

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        await _safe_edit_or_send(q, context, chat_id, "❌ 𝑵𝒂̃𝒐 𝒆𝒏𝒄𝒐𝒏𝒕𝒓𝒆𝒊 𝒔𝒆𝒖𝒔 𝒅𝒂𝒅𝒐𝒔. 𝑼𝒔𝒆 /𝒔𝒕𝒂𝒓𝒕.")
        return

    st = (pdata.get("player_state") or {}).get("action")
    if st not in (None, "idle"):
        await q.answer("𝑽𝒐𝒄𝒆̂ 𝒆𝒔𝒕𝒂́ 𝒐𝒄𝒖𝒑𝒂𝒅𝒐 𝒄𝒐𝒎 𝒐𝒖𝒕𝒓𝒂 𝒂𝒄̧𝒂̃𝒐 𝒂𝒈𝒐𝒓𝒂.", show_alert=True); return

    inv = pdata.get("inventory", {}) or {}
    inst = inv.get(uid)
    if not isinstance(inst, dict):
        await q.answer("𝑰𝒕𝒆𝒎 𝒊𝒏𝒗𝒂́ʟ𝒊𝒅𝒐 𝒐𝒖 𝒏𝒂̃𝒐 𝒆𝒏𝒄𝒐𝒏𝒕𝒓𝒂𝒅𝒐.", show_alert=True); return

    tpl = (getattr(game_data, "ITEMS_DATA", {}).get(inst.get("base_id")) or
           getattr(game_data, "ITEM_BASES", {}).get(inst.get("base_id")) or {})

    lvl_req = int(tpl.get("level_req", 0))
    try:
        player_level = int(pdata.get("level") or pdata.get("𝐥𝐞𝐯𝐞𝐥") or 1)
    except Exception:
        player_level = 1
    if lvl_req and player_level < lvl_req:
        await q.answer(f"𝑹𝒆𝒒𝒖𝒆𝒓 𝒏𝒊́ᴠᴇʟ {lvl_req}.", show_alert=True); return

    success, message = await player_manager.equip_unique_item_for_user(user_id, uid)

    if not success:
        await q.answer(message, show_alert=True)
        return

    await q.answer("𝑬𝒒𝒖𝒊𝒑𝒂𝒅𝒐!", show_alert=False)
    await equipment_menu(update, context) # Chama função async
    
async def equip_unequip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Desequipa o item do slot (se houver)."""
    q = update.callback_query
    await q.answer()
    slot = q.data.replace("equip_unequip_", "")
    user_id = q.from_user.id
    chat_id = q.message.chat.id

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        await _safe_edit_or_send(q, context, chat_id, "❌ 𝑵𝒂̃𝒐 𝒆𝒏𝒄𝒐𝒏𝒕𝒓𝒆𝒊 𝒔𝒆𝒖𝒔 𝒅𝒂𝒅𝒐𝒔. 𝑼𝒔𝒆 /𝒔𝒕𝒂𝒓𝒕.")
        return

    st = (pdata.get("player_state") or {}).get("action")
    if st not in (None, "idle"):
        await q.answer("𝑽𝒐𝒄𝒆̂ 𝒆𝒔𝒕𝒂́ 𝒐𝒄𝒖𝒑𝒂𝒅𝒐 𝒄𝒐𝒎 𝒐𝒖𝒕𝒓𝒂 𝒂𝒄̧𝒂̃𝒐 𝒂𝒈𝒐𝒓𝒂.", show_alert=True); return

    eq = pdata.get("equipment", {}) or {}
    if not eq.get(slot):
        await q.answer("𝑵𝒂𝒅𝒂 𝒆𝒒𝒖𝒊𝒑𝒂𝒅𝒐 𝒏𝒆𝒔𝒔𝒆 𝒔𝒍𝒐𝒕.", show_alert=False); return

    eq[slot] = None
    pdata["equipment"] = eq

    await player_manager.save_player_data(user_id, pdata)

    await q.answer("𝑹𝒆𝒎𝒐𝒗𝒊𝒅𝒐.", show_alert=False)
    await equipment_menu(update, context) # Chama função async
    

# ---------- Exporta handlers ----------
equipment_menu_handler   = CallbackQueryHandler(equipment_menu, pattern=r'^equipment_menu$')
equip_slot_handler       = CallbackQueryHandler(equip_slot_callback, pattern=r'^equip_slot_[A-Za-z_]+$')
equip_pick_handler       = CallbackQueryHandler(equip_pick_callback, pattern=r'^equip_pick_')
equip_unequip_handler    = CallbackQueryHandler(equip_unequip_callback, pattern=r'^equip_unequip_')