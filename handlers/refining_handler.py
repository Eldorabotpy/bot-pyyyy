# handlers/refining_handler.py
# (FINAL ROBUSTA: Refino e Desmonte com Recovery)

import logging 
import math
import telegram
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
)
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import game_data, player_manager, file_ids
from modules.refining_engine import preview_refine, start_refine, finish_refine
from modules import crafting_registry, dismantle_engine, display_utils

ITEMS_PER_PAGE = 5
logger = logging.getLogger(__name__)

# =====================================================
# 1. CORE LOGIC - REFINO (Safe for Recovery)
# =====================================================
async def execute_refine_logic(
    user_id: int, 
    chat_id: int, 
    context: ContextTypes.DEFAULT_TYPE, 
    message_id_to_delete: int = None
):
    """
    Finaliza o refino: dá os itens e notifica.
    Independente de Job.
    """
    # 1. Limpa msg de progresso
    if message_id_to_delete:
        try: await context.bot.delete_message(chat_id, message_id_to_delete)
        except: pass

    # 2. Carrega e Processa
    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return

    res = await finish_refine(pdata)
    
    if isinstance(res, str):
        # Erro de lógica (ex: não estava refinando)
        await context.bot.send_message(chat_id, f"❗ {res}")
        return
    if not res: return

    # 3. Notificação
    outs = res.get("outputs") or {}
    lines = ["✅ <b>Refino concluído!</b>", "Você obteve:"]
    for k, v in outs.items():
        lines.append(f"• {_fmt_item_line(k, v)}")
    
    caption = "\n".join(lines)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="ref_main")]])

    # Mídia do primeiro item
    mkey = None
    if outs:
        iid = list(outs.keys())[0]
        mkey = (game_data.ITEMS_DATA.get(iid) or {}).get("media_key")

    await _safe_send_with_media(context, chat_id, caption, kb, media_key=mkey)


# =====================================================
# 2. CORE LOGIC - DESMONTE (Safe for Recovery)
# =====================================================
async def execute_dismantle_logic(
    user_id: int,
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    job_details: dict, # Dados salvos no banco ou job (unique_id etc)
    message_id_to_delete: int = None
):
    """
    Finaliza o desmonte.
    """
    if message_id_to_delete:
        try: await context.bot.delete_message(chat_id, message_id_to_delete)
        except: pass

    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return

    # Chama engine
    result = await dismantle_engine.finish_dismantle(pdata, job_details)

    if isinstance(result, str):
        await context.bot.send_message(chat_id, f"❗ Erro desmonte: {result}")
        return

    item_name, returned_materials = result
    
    # Salva
    await player_manager.save_player_data(user_id, pdata)

    lines = [f"♻️ <b>{item_name}</b> desmontado!", "\nRecuperado:"]
    if not returned_materials: lines.append(" - Nada.")
    else:
        for k, v in returned_materials.items():
            lines.append(f"• {_fmt_item_line(k, v)}")

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="ref_main")]])
    await context.bot.send_message(chat_id, "\n".join(lines), parse_mode="HTML", reply_markup=kb)


# =====================================================
# 3. JOB WRAPPERS
# =====================================================
async def finish_refine_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    if not job: return
    await execute_refine_logic(
        user_id=job.user_id,
        chat_id=job.chat_id,
        context=context,
        message_id_to_delete=job.data.get("message_id_to_delete")
    )

async def finish_dismantle_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    if not job: return
    await execute_dismantle_logic(
        user_id=job.user_id,
        chat_id=job.chat_id,
        context=context,
        job_details=job.data,
        message_id_to_delete=job.data.get("message_id_to_delete")
    )

# =========================
# Helpers UI
# =========================
def _fmt_minutes_or_seconds(seconds: int) -> str:
    return f"{round(seconds/60)} min" if seconds >= 60 else f"{int(seconds)}s"

def _fmt_item_line(item_id: str, qty: int) -> str:
    info = (game_data.ITEMS_DATA or {}).get(item_id) or {}
    display = info.get("display_name") or item_id.replace("_", " ").title()
    emoji = info.get("emoji", "")
    return f"{emoji} <b>{display}</b> x{int(qty)}"

async def _safe_send_with_media(context, chat_id, caption, reply_markup=None, media_key=None, fallback_key="refino_universal"):
    keys = [k for k in [media_key, fallback_key] if k]
    for key in keys:
        fd = file_ids.get_file_data(key)
        if fd and fd.get("id"):
            try:
                if fd.get("type") == "video":
                    await context.bot.send_video(chat_id, fd["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
                else:
                    await context.bot.send_photo(chat_id, fd["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
                return
            except: pass
    await context.bot.send_message(chat_id, caption, reply_markup=reply_markup, parse_mode="HTML")

async def _safe_edit_or_send_with_media(query, context, caption, reply_markup=None, media_key="refino_universal"):
    try: await query.delete_message()
    except: pass
    return await _safe_send_with_media(context, query.message.chat_id, caption, reply_markup, media_key=media_key)

# =========================
# Handlers Callbacks
# =========================

async def refining_main_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    
    page = 1
    if "_PAGE_" in q.data: page = int(q.data.split('_PAGE_')[-1])

    pdata = await player_manager.get_player_data(uid)
    recipes = []
    for rid, rec in game_data.REFINING_RECIPES.items():
        prev = preview_refine(rid, pdata)
        if prev:
            t = _fmt_minutes_or_seconds(int(prev.get("duration_seconds", 0)))
            recipes.append({"id": rid, "data": rec, "prev": prev, "time": t})

    total_p = max(1, math.ceil(len(recipes) / 8))
    page = max(1, min(page, total_p))
    current = recipes[(page-1)*8 : page*8]

    lines = ["🛠️ <b>Refino & Desmontagem</b>\n", f"Pág {page}/{total_p}"]
    kb = [[InlineKeyboardButton("♻️ Desmontar Equipamento", callback_data="ref_dismantle_list")]]
    
    for r in current:
        tag = "✅" if r["prev"].get("can_refine") else "⛔"
        lines.append(f"{tag} {r['data'].get('display_name')} | ⏳ {r['time']}")
        kb.append([InlineKeyboardButton(r['data'].get('display_name'), callback_data=f"ref_sel_{r['id']}")])

    nav = []
    if page > 1: nav.append(InlineKeyboardButton("◀️", callback_data=f"ref_main_PAGE_{page-1}"))
    nav.append(InlineKeyboardButton("⟳", callback_data="noop_ref_page"))
    if page < total_p: nav.append(InlineKeyboardButton("▶️", callback_data=f"ref_main_PAGE_{page+1}"))
    if nav: kb.append(nav)
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="continue_after_action")])

    await _safe_edit_or_send_with_media(q, context, "\n".join(lines), InlineKeyboardMarkup(kb))

async def ref_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    rid = q.data.replace("ref_sel_", "", 1)
    pdata = await player_manager.get_player_data(q.from_user.id)
    prev = preview_refine(rid, pdata)
    
    if not prev: return
    
    ins = "\n".join(_fmt_item_line(k, v) for k, v in (prev.get("inputs") or {}).items())
    outs = "\n".join(_fmt_item_line(k, v) for k, v in (prev.get("outputs") or {}).items())
    t = _fmt_minutes_or_seconds(int(prev.get("duration_seconds", 0)))
    
    txt = f"🛠️ <b>{game_data.REFINING_RECIPES.get(rid,{}).get('display_name')}</b>\n⏳ {t}\n\n📥 <b>Entrada:</b>\n{ins}\n\n📦 <b>Saída:</b>\n{outs}"
    
    kb = []
    if prev.get("can_refine"): kb.append([InlineKeyboardButton("✅ Refinar", callback_data=f"ref_confirm_{rid}")])
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="ref_main")])
    
    await _safe_edit_or_send_with_media(q, context, txt, InlineKeyboardMarkup(kb))

async def ref_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    rid = q.data.replace("ref_confirm_", "", 1)
    
    pdata = await player_manager.get_player_data(uid)
    if pdata.get("player_state", {}).get("action") not in (None, "idle"):
        await q.answer("Ocupado!", show_alert=True); return

    res = await start_refine(pdata, rid)
    if isinstance(res, str):
        await q.answer(res, show_alert=True); return

    secs = int(res.get("duration_seconds", 60))
    t = _fmt_minutes_or_seconds(secs)
    title = game_data.REFINING_RECIPES.get(rid, {}).get("display_name", rid)
    
    sent = await _safe_edit_or_send_with_media(q, context, f"🔧 Refinando <b>{title}</b>... (~{t})")
    mid = sent.message_id if sent else None
    
    context.job_queue.run_once(finish_refine_job, secs, user_id=uid, chat_id=q.message.chat_id,
                               data={"rid": rid, "message_id_to_delete": mid}, name=f"refining:{uid}")
    await q.answer()

async def show_dismantle_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    pdata = await player_manager.get_player_data(uid)
    
    page = 0
    if ":page:" in q.data: page = int(q.data.split(':page:')[1])
    
    inv = pdata.get("inventory", {})
    equip = set(pdata.get("equipment", {}).values())
    
    items = []
    for uid, d in inv.items():
        if isinstance(d, dict) and uid not in equip:
            if crafting_registry.get_recipe_by_item_id(d.get("base_id")):
                items.append((uid, d))
    
    items.sort(key=lambda x: x[1].get("display_name", ""))
    
    total = (len(items) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    cur_items = items[page*ITEMS_PER_PAGE : (page+1)*ITEMS_PER_PAGE]
    
    kb = []
    for iuid, idata in cur_items:
        kb.append([InlineKeyboardButton(f"🔩 {idata.get('display_name')}", callback_data=f"ref_dismantle_preview:{iuid}")])
        
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("⬅️", callback_data=f"ref_dismantle_list:page:{page-1}"))
    if (page+1)*ITEMS_PER_PAGE < len(items): nav.append(InlineKeyboardButton("➡️", callback_data=f"ref_dismantle_list:page:{page+1}"))
    if nav: kb.append(nav)
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="ref_main")])
    
    msg = "♻️ <b>Desmontar</b>\nEscolha um item:"
    if not items: msg += "\n\n(Vazio)"
    
    await _safe_edit_or_send_with_media(q, context, msg, InlineKeyboardMarkup(kb), media_key='desmontagem_menu_image')

async def show_dismantle_preview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid, iuid = q.from_user.id, q.data.split(':')[1]
    pdata = await player_manager.get_player_data(uid)
    
    item = pdata.get("inventory", {}).get(iuid)
    if not item: 
        await show_dismantle_list_callback(update, context); return

    rec = crafting_registry.get_recipe_by_item_id(item.get("base_id"))
    inputs = rec.get("inputs", {})
    ret = {}
    for k, v in inputs.items():
        if k != "nucleo_forja_fraco":
            amt = v // 2
            if amt > 0: ret[k] = amt
            
    txt = f"♻️ <b>Desmontar {item.get('display_name')}?</b>\n\nRetorno estimado:"
    for k, v in ret.items(): txt += f"\n• {_fmt_item_line(k, v)}"
    txt += "\n\n⚠️ Irreversível!"
    
    kb = [[InlineKeyboardButton("✅ 𝐂𝐨𝐧𝐟𝐢𝐫𝐦𝐚𝐫", callback_data=f"ref_dismantle_confirm:{iuid}")],
          [InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="ref_dismantle_list")]]
          
    mkey = (game_data.ITEMS_DATA.get(item.get("base_id")) or {}).get("media_key")
    await _safe_edit_or_send_with_media(q, context, txt, InlineKeyboardMarkup(kb), media_key=mkey)

async def confirm_dismantle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid, iuid = q.from_user.id, q.data.split(':')[1]
    pdata = await player_manager.get_player_data(uid)
    
    res = await dismantle_engine.start_dismantle(pdata, iuid)
    if isinstance(res, str):
        await q.answer(res, show_alert=True); return
        
    dur = res.get("duration_seconds", 60)
    sent = await _safe_edit_or_send_with_media(q, context, f"♻️ Desmontando... (~{_fmt_minutes_or_seconds(dur)})")
    
    mid = sent.message_id if sent else None
    
    # IMPORTANTE: Salva os dados necessários para o Recovery/Engine
    job_data = {
        "unique_item_id": iuid, 
        "item_name": res.get("item_name"),
        "base_id": res.get("base_id"),
        "message_id_to_delete": mid
    }
    
    # Atualiza o 'details' no banco com esses dados, pois o engine só salvou o básico
    pdata['player_state']['details'] = job_data
    await player_manager.save_player_data(uid, pdata)

    context.job_queue.run_once(finish_dismantle_job, dur, user_id=uid, chat_id=q.message.chat_id,
                               data=job_data, name=f"dismantle_{uid}")
    await q.answer()

async def noop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

# Registros
refining_main_handler = CallbackQueryHandler(refining_main_callback, pattern=r"^(refining_main|ref_main|ref_main_PAGE_\d+)$")
noop_handler = CallbackQueryHandler(noop_callback, pattern=r"^noop_ref_page$")
ref_select_handler  = CallbackQueryHandler(ref_select_callback,  pattern=r"^ref_sel_[A-Za-z0-9_]+$")
ref_confirm_handler = CallbackQueryHandler(ref_confirm_callback,  pattern=r"^ref_confirm_[A-Za-z0-9_]+$")
dismantle_list_handler = CallbackQueryHandler(show_dismantle_list_callback, pattern=r"^ref_dismantle_list(:page:\d+)?$")
dismantle_preview_handler = CallbackQueryHandler(show_dismantle_preview_callback, pattern=r"^ref_dismantle_preview:[a-f0-9-]+$")
dismantle_confirm_handler = CallbackQueryHandler(confirm_dismantle_callback, pattern=r"^ref_dismantle_confirm:[a-f0-9-]+$")