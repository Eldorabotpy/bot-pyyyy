# handlers/enhance_handler.py
# (VERSÃO BLINDADA: Auth Híbrida + Reparo em Massa)

import math
from typing import Dict, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, game_data, crafting_registry
from modules.profession_engine import enhance_item, restore_durability, restore_all_equipped_durability
from modules.auth_utils import get_current_player_id  # ✅ IMPORT CRÍTICO

# --- DISPLAY UTILS opcional (fallback simples) ---
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

# =========================
# Config / Fallbacks
# =========================

RARITY_CAPS_FALLBACK = {
    "comum": 5,
    "bom": 7,
    "raro": 9,
    "epico": 11,
    "lendario": 13,
}

# Ids dos itens especiais
JOIA_FORJA_ID     = "joia_da_forja"       
SIGILO_PROTEC_ID  = "sigilo_protecao"     
PARCHMENT_ID      = "pergaminho_durabilidade"

# =========================
# Helpers de regras
# =========================

def _get_caps_table() -> Dict[str, int]:
    try:
        from modules.game_data import rarity as rarity_tables
        tb = getattr(rarity_tables, "UPGRADE_CAP_BY_RARITY", None)
        if isinstance(tb, dict) and tb:
            return {str(k).lower(): int(v) for k, v in tb.items()}
    except Exception:
        pass
    return dict(RARITY_CAPS_FALLBACK)

def _durability_tuple(raw) -> Tuple[int, int]:
    cur, mx = 20, 20
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        try:
            cur = int(raw[0]); mx = int(raw[1])
        except Exception:
            cur, mx = 20, 20
    elif isinstance(raw, dict):
        try:
            cur = int(raw.get("current", 20)); mx = int(raw.get("max", 20))
        except Exception:
            cur, mx = 20, 20
    cur = max(0, min(cur, mx))
    mx = max(1, mx)
    return cur, mx

def _inv_qty(pdata: dict, item_id: str) -> int:
    inv = (pdata or {}).get("inventory", {}) or {}
    val = inv.get(item_id, 0)
    if isinstance(val, dict):
        return 0
    try:
        return int(val)
    except Exception:
        return 0

def _resolve_recipe_for_inst(inst: dict) -> dict | None:
    if not isinstance(inst, dict):
        return None
    rid = inst.get("crafted_recipe_id")
    if rid:
        rec = crafting_registry.get_recipe(rid)
        if rec:
            return rec
    base_id = inst.get("base_id")
    if not base_id:
        return None
    for r_id, rec in (crafting_registry.all_recipes().items()
                      if hasattr(crafting_registry, "all_recipes") else []):
        try:
            if rec.get("result_base_id") == base_id:
                return rec
        except Exception:
            continue
    return None

def _format_cost_line(pdata: dict, item_id: str, need: int) -> str:
    have = _inv_qty(pdata, item_id)
    mark = "✅" if have >= need else "❌"
    info = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(item_id, {}) or {}
    disp = info.get("display_name") or item_id.replace("_", " ").title()
    return f"{mark} <code>{have}/{need}</code> {disp}"

def _can_pay(pdata: dict, costs: Dict[str, int]) -> bool:
    for k, need in (costs or {}).items():
        if _inv_qty(pdata, k) < int(need):
            return False
    return True

def _compute_upgrade_costs_from_recipe(inst: dict, include_joia_forja: bool, include_sigilo: bool) -> Dict[str, int]:
    rec = _resolve_recipe_for_inst(inst)
    if not rec:
        return {}
    base_inputs = dict(rec.get("inputs", {}) or {})
    costs = {k: int(v) for k, v in base_inputs.items()}
    if include_joia_forja:
        costs[JOIA_FORJA_ID] = costs.get(JOIA_FORJA_ID, 0) + 1
    if include_sigilo:
        costs[SIGILO_PROTEC_ID] = costs.get(SIGILO_PROTEC_ID, 0) + 1
    return costs

# =========================
# Helpers de UI
# =========================
async def _edit_caption_or_text(query, text: str, reply_markup: InlineKeyboardMarkup | None = None, context: ContextTypes.DEFAULT_TYPE = None):
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="HTML"); return
    except Exception: pass
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="HTML"); return
    except Exception: pass
    
    if context:
        try:
            await context.bot.send_message(
                chat_id=query.message.chat.id, text=text, reply_markup=reply_markup, parse_mode="HTML"
            )
        except: pass

def _equip_list(pdata: dict):
    equip = pdata.get('equipment', {}) or {}
    inv = pdata.get('inventory', {}) or {}
    out = []
    for slot, uid in (equip.items() if isinstance(equip, dict) else []):
        if not uid: continue
        inst = inv.get(uid)
        if isinstance(inst, dict) and inst.get('base_id'):
            try:
                label = display_utils.formatar_item_para_exibicao(inst)
            except Exception:
                base = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(inst['base_id'], {})
                name = base.get('display_name', inst['base_id'])
                up = int(inst.get('upgrade_level', 1))
                cur, mx = _durability_tuple(inst.get('durability'))
                label = f"{name} +{up} [{cur}/{mx}]"
            out.append((slot, uid, label, inst))
    return out

# =========================
# Menus
# =========================

async def show_enhance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    # ✅ ID DA SESSÃO
    user_id = get_current_player_id(update, context)
    
    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return

    text = "<b>✨ 𝐀𝐩𝐫𝐢𝐦𝐨𝐫𝐚𝐦𝐞𝐧𝐭𝐨 & 𝐃𝐮𝐫𝐚𝐛𝐢𝐥𝐢𝐝𝐚𝐝𝐞</b>\n𝑺𝒆𝒍𝒆𝒄𝒊𝒐𝒏𝒆 𝒖𝒎 𝒊𝒕𝒆𝒎 <u>equipado</u>:\n"
    kb = []
    found_any = False
    
    for _, uid, label, _inst in _equip_list(pdata):
        found_any = True
        btn_text = label if len(label) <= 64 else (label[:61] + "…")
        kb.append([InlineKeyboardButton(btn_text, callback_data=f"enh_sel_{uid}")])

    if not found_any:
        text += "\n<i>𝑵𝒆𝒏𝒉𝒖𝒎 𝒆𝒒𝒖𝒊𝒑𝒂𝒎𝒆𝒏𝒕𝒐 𝒖́𝒏𝒊𝒄𝒐 𝒆𝒔𝒕𝒂́ 𝒆𝒒𝒖𝒊𝒑𝒂𝒅𝒐.</i>\n"
    else:
        kb.append([InlineKeyboardButton("📜 Restaurar Todos (1x 📜)", callback_data="enh_rest_all")])

    kb.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="continue_after_action")])
    
    await _edit_caption_or_text(q, text, InlineKeyboardMarkup(kb), context=context)

async def enhance_item_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    # ✅ ID DA SESSÃO
    user_id = get_current_player_id(update, context)
    
    uid = q.data.replace("enh_sel_", "")
    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get('inventory', {}) or {}
    inst = inv.get(uid)
    
    if not isinstance(inst, dict) or not inst.get('base_id'):
        await q.answer("Item inválido.", show_alert=True)
        await show_enhance_menu(update, context)
        return

    base = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(inst.get('base_id'), {})
    name = base.get('display_name', inst.get('base_id'))
    rarity = str(inst.get('rarity', 'comum')).lower()
    up = int(inst.get('upgrade_level', 1))
    cur, mx = _durability_tuple(inst.get('durability'))

    caps = _get_caps_table()
    cap = int(caps.get(rarity, 5))
    at_cap = (up >= cap)

    costs_simple = _compute_upgrade_costs_from_recipe(inst, include_joia_forja=True, include_sigilo=False)
    costs_with_sigilo = _compute_upgrade_costs_from_recipe(inst, include_joia_forja=True, include_sigilo=True)

    needs_text_simple  = "\n".join(_format_cost_line(pdata, k, v) for k, v in costs_simple.items()) if costs_simple else "—"
    needs_text_sigilo  = "\n".join(_format_cost_line(pdata, k, v) for k, v in costs_with_sigilo.items()) if costs_with_sigilo else "—"

    can_pay_simple = (not at_cap) and _can_pay(pdata, costs_simple)
    can_pay_sigilo = (not at_cap) and _can_pay(pdata, costs_with_sigilo)

    simple_ok = "✅" if can_pay_simple else "❌"
    sigilo_ok = "✅" if can_pay_sigilo else "❌"

    text_lines = [
        f"<b>{name}</b>",
        f"𝑹𝒂𝒓𝒊𝒅𝒂𝒅𝒆: <b>{rarity.capitalize()}</b>",
        f"𝑵𝒊́𝒗𝒆𝒍 𝒂𝒕𝒖𝒂𝒍: <b>+{up}</b>   →   𝑷𝒓𝒐́𝒙𝒊𝒎𝒐: <b>+{up+1}</b>   (Cap: <b>+{cap}</b>)", 
        f"𝑫𝒖𝒓𝒂𝒃𝒊𝒍𝒊𝒅𝒂𝒅𝒆: <b>{cur}/{mx}</b>",
        "",
    ]

    if at_cap:
        text_lines.append("<i>𝑬𝒔𝒕𝒆 𝒊𝒕𝒆𝒎 𝒆𝒔𝒕𝒂́ 𝒏𝒐 𝒍𝒊𝒎𝒊𝒕𝒆 𝒅𝒆 𝒂𝒑𝒓𝒊𝒎𝒐𝒓𝒂𝒎𝒆𝒏𝒕𝒐 𝒅𝒂 𝒓𝒂𝒓𝒊𝒅𝒂𝒅𝒆.</i>")
    else:
        text_lines += [
            "<b>𝑪𝒖𝒔𝒕𝒐 (𝑨𝒑𝒓𝒊𝒎𝒐𝒓𝒂𝒓 𝒔𝒊𝒎𝒑𝒍𝒆𝒔):</b>",
            needs_text_simple,
            "",
            "<b>𝑪𝒖𝒔𝒕𝒐 (𝑨𝒑𝒓𝒊𝒎𝒐𝒓𝒂𝒓 𝒄𝒐𝒎 ✨ 𝑺𝒊𝒈𝒊𝒍𝒐 𝒅𝒆 𝑷𝒓𝒐𝒕𝒆𝒄̧𝒂̃𝒐 — 𝒑𝒓𝒐𝒕𝒆𝒈𝒆 𝒐 𝒏𝒊́𝒗𝒆𝒍 𝒆𝒎 𝒇𝒂𝒍𝒉𝒂):</b>",
            needs_text_sigilo,
        ]

    kb = []
    if not at_cap:
        kb.append([InlineKeyboardButton(f"{simple_ok} 𝑨𝒑𝒓𝒊𝒎𝒐𝒓𝒂𝒓 (𝒔𝒊𝒎𝒑𝒍𝒆𝒔)", callback_data=f"enh_go_{uid}_nojoia")])
        kb.append([InlineKeyboardButton(f"{sigilo_ok} 𝑨𝒑𝒓𝒊𝒎𝒐𝒓𝒂𝒓 (𝒄𝒐𝒎 𝑺𝒊𝒈𝒊𝒍𝒐)", callback_data=f"enh_go_{uid}_joia")])
    kb.append([InlineKeyboardButton("📜 𝑹𝒆𝒔𝒕𝒂𝒖𝒓𝒂𝒓 𝑫𝒖𝒓𝒂𝒃𝒊𝒍𝒊𝒅𝒂𝒅𝒆", callback_data=f"enh_rest_{uid}")])
    kb.append([InlineKeyboardButton("⬅️ 𝑽𝒐𝒍𝒕𝒂𝒓", callback_data="enhance_menu")])

    await _edit_caption_or_text(q, "\n".join(text_lines), InlineKeyboardMarkup(kb), context=context)

# =========================
# Ações
# =========================

async def do_enhance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    # ✅ ID DA SESSÃO (Essencial para o sistema novo)
    user_id = get_current_player_id(update, context)
    
    pdata = await player_manager.get_player_data(user_id)
    data = q.data

    # === REPARAR TUDO ===
    if data == "enh_rest_all":
        # CORREÇÃO: Passando user_id para garantir o salvamento no banco correto
        res = await restore_all_equipped_durability(user_id, pdata)
        
        if res.get("error"):
            await q.answer(res["error"], show_alert=True)
            await show_enhance_menu(update, context) 
            return

        # O engine já salva, mas por segurança mantemos aqui ou removemos se o engine duplicar. 
        # No padrão novo, o engine costuma salvar. Se não, o handler salva.
        # Vou manter para garantir.
        await player_manager.save_player_data(user_id, pdata)
        
        count = res.get("count", 0)
        text = (
            f"✨ <b>Reparo Completo!</b>\n"
            f"Foram restaurados <b>{count}</b> equipamentos equipados.\n"
            f"Foi consumido <b>1x Pergaminho de Durabilidade</b>."
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="enhance_menu")]])
        await _edit_caption_or_text(q, text, kb, context=context)
        return
    
    # === APRIMORAR ===
    if data.startswith("enh_go_"):
        try:
            _, _, uid, flag = data.split("_", 3)
        except ValueError:
            await q.answer("𝑨𝒄̧𝒂̃𝒐 𝒊𝒏𝒗𝒂́𝒍𝒊𝒅𝒂.", show_alert=True)
            return

        use_joia = (flag == "joia")
        
        # CORREÇÃO CRÍTICA: user_id como primeiro argumento
        res = await enhance_item(user_id, pdata, uid, use_joia=use_joia)
        
        if isinstance(res, dict) and res.get("error"):
            await q.answer(res["error"], show_alert=True)
            await enhance_item_menu(update, context) 
            return

        await player_manager.save_player_data(user_id, pdata)

        # Prepara mensagem de resultado (síncrono)
        inv = pdata.get("inventory", {}) or {}
        inst = inv.get(uid)
        base = (getattr(game_data, "ITEMS_DATA", {}) or {}).get((inst or {}).get('base_id', ''), {})
        name = base.get('display_name', (inst or {}).get('base_id', 'Item'))
        up = int((inst or {}).get('upgrade_level', res.get("new_level", 0)))
        cur, mx = _durability_tuple((inst or {}).get('durability'))

        if res.get("success"):
            header = "✅ <b>𝐀𝐩𝐫𝐢𝐦𝐨𝐫𝐚𝐦𝐞𝐧𝐭𝐨 𝐛𝐞𝐦-𝐬𝐮𝐜𝐞𝐝𝐢𝐝𝐨!</b>"
            body = f"{name} 𝒂𝒈𝒐𝒓𝒂 𝒆𝒔𝒕𝒂́ 𝒆𝒎 <b>+{up}</b>."
        else: # Falhou
            if res.get("protected"):
                header = "⚠️ <b>𝑭𝒂𝒍𝒉𝒐𝒖, 𝒎𝒂𝒔 𝒑𝒓𝒐𝒕𝒆𝒈𝒊𝒅𝒐.</b>"
                body = f"𝐎 ✨ 𝐒𝐢𝐠𝐢𝐥𝐨 𝐝𝐞 𝐏𝐫𝐨𝐭𝐞𝐜̧𝐚̃𝒐 𝐦𝐚𝐧𝐭𝐞𝐯𝐞 𝐨 𝐧𝐢́𝐯𝐞𝒍 𝐞𝐦 <b>+{up}</b>."
            else: # Falhou e não estava protegido
                header = "❌⚠️ <b>𝑨𝒑𝒓𝒊𝒎𝒐𝒓𝒂𝒎𝒆𝒏𝒕𝒐 𝒇𝒂𝒍𝒉𝒐𝒖.</b>"
                body = f"𝑶 𝒏𝒊́𝒗𝒆𝒍 𝒄𝒂𝒊𝒖 𝒑𝒂𝒓𝒂 <b>+{up}</b>." 

        text = "\n".join([
            header, body, f"𝐃𝐮𝐫𝐚𝐛𝐢𝐥𝐢𝐝𝐚𝐝𝐞: <b>{cur}/{mx}</b>", "", "<i>𝑫𝒆𝒔𝒆𝒋𝒂 𝒕𝒆𝒏𝒕𝒂𝒓 𝒏𝒐𝒗𝒂𝒎𝒆𝒏𝒕𝒆?</i>",
        ])

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 𝐕𝐨𝐥𝐭𝐚𝐫 a 𝐦𝐞𝐥𝐡𝐨𝐫𝐚𝐫 𝐞𝐬𝐭𝐞 𝐢𝐭𝐞𝐦", callback_data=f"enh_sel_{uid}")],
            [InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫 𝐚𝐨𝐬 𝐞𝐪𝐮𝐢𝐩𝐚𝐝𝐨𝐬", callback_data="enhance_menu")],
        ])
        await _edit_caption_or_text(q, text, kb, context=context)
        return

    # === RESTAURAR DURABILIDADE (ÚNICO) ===
    if data.startswith("enh_rest_"):
        uid = data.replace("enh_rest_", "")
        
        # CORREÇÃO: Passando user_id
        res = await restore_durability(user_id, pdata, uid)
        
        if isinstance(res, dict) and res.get("error"):
            await q.answer(res["error"], show_alert=True)
            await enhance_item_menu(update, context) 
            return

        await player_manager.save_player_data(user_id, pdata)

        inv = pdata.get("inventory", {}) or {}
        inst = inv.get(uid, {})
        base = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(inst.get('base_id', ''), {})
        name = base.get('display_name', inst.get('base_id', 'Item'))
        cur, mx = _durability_tuple(inst.get('durability'))
        text = (
            "📜 <b>𝑫𝒖𝒓𝒂𝒃𝒊𝒍𝒊𝒅𝒂𝒅𝒆 𝒓𝒆𝒔𝒕𝒂𝒖𝒓𝒂𝒅𝒂!</b>\n"
            f"{name} 𝒂𝒈𝒐𝒓𝒂 𝒆𝒔𝒕𝒂́ 𝒄𝒐𝒎 <b>{cur}/{mx}</b>."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔧 𝐕𝐨𝐥𝐭𝐚𝐫 𝐚 𝐦𝐞𝐥𝐡𝐨𝐫𝐚𝐫 𝐞𝐬𝐭𝐞 𝐢𝐭𝐞𝐦", callback_data=f"enh_sel_{uid}")],
            [InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫 𝐚𝐨𝐬 𝐞𝐪𝐮𝐢𝐩𝐚𝐝𝐨𝐬", callback_data="enhance_menu")],
        ])
        await _edit_caption_or_text(q, text, kb, context=context)        
enhance_menu_handler   = CallbackQueryHandler(show_enhance_menu, pattern=r'^enhance_menu$')
enhance_select_handler = CallbackQueryHandler(enhance_item_menu, pattern=r'^enh_sel_')
enhance_action_handler = CallbackQueryHandler(do_enhance, pattern=r'^enh_(go|rest)_')