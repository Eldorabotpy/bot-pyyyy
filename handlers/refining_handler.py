# handlers/refining_handler.py
# (VERSÃO BLINDADA OBJECTID: Refino e Desmonte Estritos)

import logging 
import math
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import ContextTypes, CallbackQueryHandler

# --- Módulos Internos ---
from modules.auth_utils import get_current_player_id
from modules import game_data, player_manager, file_ids, crafting_registry
from modules import refining_engine, dismantle_engine

ITEMS_PER_PAGE = 5
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. JOB HANDLERS (O CORAÇÃO DA CORREÇÃO)
# Estes jobs agora exigem que 'user_id' venha dentro do 'job.data' como String
# ==============================================================================

async def finish_refine_job(context: ContextTypes.DEFAULT_TYPE):
    """Finaliza Refino Único ou Lote."""
    job = context.job
    if not job: return

    # --- CORREÇÃO CRÍTICA: ID OBJECTID ---
    user_id = job.data.get("user_id") # Tem que vir do DATA, não do context
    chat_id = job.chat_id
    mid = job.data.get("message_id_to_delete")

    if not user_id or isinstance(user_id, int):
        logger.error(f"❌ [Refino Job] ID inválido ou legado detectado: {user_id}")
        return

    # 1. Limpeza visual
    if mid:
        try: await context.bot.delete_message(chat_id, mid)
        except Exception: pass

    # 2. Carrega dados via ObjectId
    pdata = await player_manager.get_player_data(user_id)
    if not pdata: 
        logger.warning(f"⚠️ [Refino Job] PlayerData não encontrado para: {user_id}")
        return

    # 3. Executa Engine
    res = await refining_engine.finish_refine(pdata)
    
    if isinstance(res, str):
        await context.bot.send_message(chat_id, f"❗ {res}")
        return
    if not res: return

    # 4. Resultado Visual
    outs = res.get("outputs") or {}
    xp = res.get("xp_gained", 0)
    
    lines = [
        "✅ <b>PROCESSO CONCLUÍDO!</b>",
        "──────────────────────",
        "🎒 <b>VOCÊ RECEBEU:</b>"
    ]
    for k, v in outs.items():
        lines.append(f" ╰┈➤ {_fmt_item_line(k, v)}")
    
    if xp > 0:
        lines.append(f" ╰┈➤ ✨ <b>XP Profissão:</b> <code>+{xp}</code>")
        
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Refino", callback_data="ref_main")]])
    await _safe_send_with_media(context, chat_id, "\n".join(lines), kb)


async def finish_dismantle_job(context: ContextTypes.DEFAULT_TYPE):
    """Finaliza Desmonte Único."""
    job = context.job
    if not job: return
    
    user_id = job.data.get("user_id")
    chat_id = job.chat_id
    mid = job.data.get("message_id_to_delete")
    
    if not user_id or isinstance(user_id, int):
        logger.error(f"❌ [Desmonte Job] ID inválido: {user_id}")
        return

    if mid:
        try: await context.bot.delete_message(chat_id, mid)
        except: pass

    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return

    # A Engine espera o 'details' que está no job.data
    res = await dismantle_engine.finish_dismantle(pdata, job.data)

    if isinstance(res, str):
        await context.bot.send_message(chat_id, f"❗ {res}")
        return

    item_name, returned_materials = res
    lines = [f"♻️ <b>{item_name}</b> desmontado!", "\n📉 <b>Recuperado:</b>"]
    
    if not returned_materials: lines.append(" ╰┈➤ <i>Nada (Item sem receita?)</i>")
    else:
        for k, v in returned_materials.items():
            lines.append(f" ╰┈➤ {_fmt_item_line(k, v)}")

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="ref_dismantle_list")]])
    await context.bot.send_message(chat_id, "\n".join(lines), parse_mode="HTML", reply_markup=kb)


async def finish_bulk_dismantle_job(context: ContextTypes.DEFAULT_TYPE):
    """Finaliza Desmonte em Massa."""
    job = context.job
    if not job: return
    
    user_id = job.data.get("user_id")
    chat_id = job.chat_id
    mid = job.data.get("message_id_to_delete")

    if not user_id or isinstance(user_id, int): return

    if mid:
        try: await context.bot.delete_message(chat_id, mid)
        except: pass

    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return
    
    res = await dismantle_engine.finish_dismantle_batch(pdata, job.data)
    
    if isinstance(res, str):
        await context.bot.send_message(chat_id, f"❗ {res}")
        return

    item_name, rewards = res 
    count = job.data.get("qty_dismantling", 1)
    
    lines = [
        f"♻️ <b>Desmonte em Massa Concluído!</b>", 
        f"Foram destruídos {count}x <b>{item_name}</b>.", 
        "\n📉 <b>Total Recuperado:</b>"
    ]
    
    if not rewards: 
        lines.append(" ╰┈➤ <i>Nada.</i>")
    else:
        for k, v in rewards.items():
            lines.append(f" ╰┈➤ {_fmt_item_line(k, v)}")

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="ref_dismantle_list")]])
    await context.bot.send_message(chat_id, "\n".join(lines), parse_mode="HTML", reply_markup=kb)


# ==============================================================================
# 2. CALLBACKS PRINCIPAIS (Iniciação com ObjectId)
# ==============================================================================

async def refining_main_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    uid = get_current_player_id(update, context)
    if not uid:
        await q.answer("⚠️ Sessão expirada. Digite /start.", show_alert=True)
        return
    
    pdata = await player_manager.get_player_data(uid)
    if not pdata: return

    # Paginação
    page = 1
    if "_PAGE_" in q.data: 
        try: page = int(q.data.split('_PAGE_')[-1])
        except: page = 1

    recipes = []
    refining_recipes = getattr(game_data, "REFINING_RECIPES", {}) or {}
    
    for rid, rec in refining_recipes.items():
        prev = refining_engine.preview_refine(rid, pdata)
        if prev:
            sec = int(prev.get("duration_seconds", 0))
            t_fmt = _fmt_minutes_or_seconds(sec)
            recipes.append({
                "id": rid, 
                "name": rec.get("display_name"),
                "prev": prev, 
                "time": t_fmt,
                "req_lvl": rec.get("level_req", 1)
            })

    total_p = max(1, math.ceil(len(recipes) / ITEMS_PER_PAGE))
    page = max(1, min(page, total_p))
    current = recipes[(page-1)*ITEMS_PER_PAGE : page*ITEMS_PER_PAGE]

    prof = pdata.get("profession", {})
    p_type = str(prof.get("type", "Aprendiz")).upper()
    lvl = int(prof.get("level", 1))

    lines = [
        f"⚒️ <b>OFICINA DE REFINO</b>",
        f"👷 <b>Profissão:</b> {p_type} <code>[Lv. {lvl}]</code>",
        f"──────────────────────"
    ]
    
    kb = []
    kb.append([InlineKeyboardButton("♻️ MODO DE DESMONTAGEM ♻️", callback_data="ref_dismantle_list")])

    for r in current:
        can = r["prev"].get("can_refine")
        icon = "🟢" if can else "🔴"
        status_txt = "Pronto" if can else "Falta Material"
        
        lines.append(f"\n{icon} <b>{r['name']}</b>")
        lines.append(f"   └─ ⏳ {r['time']} | {status_txt}")
        kb.append([InlineKeyboardButton(f"🔨 FORJAR: {r['name']}", callback_data=f"ref_sel_{r['id']}")])

    lines.append(f"\n📄 <b>Página {page}/{total_p}</b>")

    nav = []
    if page > 1: nav.append(InlineKeyboardButton("◀️", callback_data=f"ref_main_PAGE_{page-1}"))
    nav.append(InlineKeyboardButton("🔄", callback_data="noop_ref_page"))
    if page < total_p: nav.append(InlineKeyboardButton("▶️", callback_data=f"ref_main_PAGE_{page+1}"))
    if nav: kb.append(nav)
    
    kb.append([InlineKeyboardButton("🔙 Fechar", callback_data="continue_after_action")])

    await _safe_edit_or_send_with_media(q, context, "\n".join(lines), InlineKeyboardMarkup(kb))


async def ref_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    # Não deleta a mensagem se der erro aqui pra evitar flash branco
    
    rid = q.data.replace("ref_sel_", "", 1)
    uid = get_current_player_id(update, context)
    if not uid: 
        await q.answer("Sessão expirada", show_alert=True)
        return

    pdata = await player_manager.get_player_data(uid)
    prev = refining_engine.preview_refine(rid, pdata)
    if not prev: 
        await q.answer("Erro na receita", show_alert=True)
        return
    
    rec = game_data.REFINING_RECIPES.get(rid) or {}
    
    # ... (Lógica de exibição visual mantida igual, só o core mudou) ...
    # [Omitindo detalhes puramente visuais para focar na correção]
    
    t_fmt = _fmt_minutes_or_seconds(int(prev.get("duration_seconds", 0)))
    
    txt = f"⚒️ <b>FORJA: {rec.get('display_name', rid).upper()}</b>\n"
    txt += f" ╰┈➤ ⏳ <b>Tempo:</b> <code>{t_fmt}</code>\n"
    txt += "\n📥 <b>INGREDIENTES:</b>\n"
    
    for k, qty in prev.get("inputs", {}).items():
        inv_item = pdata.get("inventory", {}).get(k)
        has = int(inv_item.get("quantity", 0)) if isinstance(inv_item, dict) else int(inv_item or 0)
        check = "✅" if has >= qty else "❌"
        txt += f" ╰┈➤ {_fmt_item_line(k, qty)}  <code>({has})</code> {check}\n"

    kb = []
    if prev.get("can_refine"):
        kb.append([InlineKeyboardButton("✅ CONFIRMAR REFINO", callback_data=f"ref_confirm_{rid}")])
        max_qty = refining_engine.get_max_refine_quantity(pdata, rec)
        if max_qty > 1:
            kb.append([InlineKeyboardButton(f"📚 Lote (Max: {max_qty})", callback_data=f"ref_batch_menu_{rid}")])
    
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="ref_main")])
    
    # Agora sim deleta/edita
    try: await q.delete_message()
    except: pass
    
    mkey = rec.get("media_key")
    await _safe_send_with_media(context, q.message.chat_id, txt, InlineKeyboardMarkup(kb), media_key=mkey)


async def ref_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try: await q.delete_message()
    except: pass
    
    uid = get_current_player_id(update, context)
    if not uid: return

    rid = q.data.replace("ref_confirm_", "", 1)
    pdata = await player_manager.get_player_data(uid)
    
    if pdata.get("player_state", {}).get("action") not in (None, "idle"):
        await context.bot.send_message(q.message.chat_id, "⚠️ <b>Ocupado!</b>", parse_mode="HTML")
        return

    # Inicia Engine
    res = await refining_engine.start_refine(pdata, rid)
    if isinstance(res, str):
        await context.bot.send_message(q.message.chat_id, f"❌ {res}")
        return

    secs = int(res.get("duration_seconds", 60))
    recipe_info = game_data.REFINING_RECIPES.get(rid, {})
    title = recipe_info.get("display_name", rid)
    
    txt = (
        f"🔨 <b>FORJA INICIADA: {title.upper()}</b>\n"
        f"──────────────────────\n"
        f" ╰┈➤⏳ <b>Tempo:</b> <code>{_fmt_minutes_or_seconds(secs)}</code>\n"
        f"<i>Você pode fechar esta janela.</i>"
    )
    
    sent = await _safe_send_with_media(context, q.message.chat_id, txt)
    mid = sent.message_id if sent else None
    
    # 🔒 AGENDA JOB COM ID OBJECTID SEGURO
    context.job_queue.run_once(
        finish_refine_job, 
        secs, 
        chat_id=q.message.chat_id,
        data={
            "user_id": uid, # <--- AQUI ESTÁ A CORREÇÃO
            "rid": rid, 
            "message_id_to_delete": mid 
        }, 
        name=f"refining:{uid}"
    )


async def confirm_dismantle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try: await q.delete_message()
    except: pass
    
    uid = get_current_player_id(update, context)
    if not uid: return

    iuid = q.data.split(':')[1]
    pdata = await player_manager.get_player_data(uid)
    
    res = await dismantle_engine.start_dismantle(pdata, iuid)
    if isinstance(res, str):
        await context.bot.send_message(q.message.chat_id, res)
        return
        
    dur = res.get("duration_seconds", 60)
    sent = await _safe_send_with_media(context, q.message.chat_id, f"♻️ Desmontando... (~{_fmt_minutes_or_seconds(dur)})")
    mid = sent.message_id if sent else None
    
    # 🔒 AGENDA JOB COM ID OBJECTID SEGURO
    # Recriamos o data que o job precisa
    job_data = {
        "user_id": uid, # <--- AQUI ESTÁ A CORREÇÃO
        "unique_item_id": iuid, 
        "item_name": res.get("item_name"),
        "base_id": res.get("base_id"),
        "rarity": pdata.get("player_state", {}).get("details", {}).get("rarity"), 
        "message_id_to_delete": mid
    }
    
    context.job_queue.run_once(
        finish_dismantle_job, 
        dur, 
        chat_id=q.message.chat_id,
        data=job_data, 
        name=f"dismantle_{uid}"
    )

# ... (Outras funções de Batch/Lote seguem a mesma lógica, garantindo user_id no job.data) ...

# =========================
# HELPERS
# =========================
def _fmt_minutes_or_seconds(seconds: int) -> str:
    if seconds < 60: return f"{int(seconds)}s"
    mins = seconds // 60
    secs = seconds % 60
    if secs > 0: return f"{mins}m {secs}s"
    return f"{mins} min"

def _fmt_item_line(item_id: str, qty: int) -> str:
    info = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(item_id) or {}
    display = info.get("display_name") or item_id.replace("_", " ").title()
    emoji = info.get("emoji", "📦")
    return f"{emoji} <b>{display}</b> x<code>{int(qty)}</code>"

async def _safe_send_with_media(context, chat_id, caption, reply_markup=None, media_key=None, fallback_key="refino_universal"):
    # (Mesma lógica visual do seu arquivo original)
    keys = [k for k in [media_key, fallback_key] if k]
    for key in keys:
        fd = file_ids.get_file_data(key)
        if fd and fd.get("id"):
            try:
                if fd.get("type") == "video":
                    return await context.bot.send_video(chat_id, fd["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
                else:
                    return await context.bot.send_photo(chat_id, fd["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            except: pass
    return await context.bot.send_message(chat_id, caption, reply_markup=reply_markup, parse_mode="HTML")

async def _safe_edit_or_send_with_media(query, context, caption, reply_markup=None, media_key="refino_universal"):
    # (Mesma lógica visual do seu arquivo original)
    try: await query.message.delete()
    except: pass
    return await _safe_send_with_media(context, query.message.chat_id, caption, reply_markup, media_key)

# =========================
# REGISTROS
# =========================
# Você precisa das mesmas regex de antes, mas agora apontando para as novas funções blindadas
refining_main_handler = CallbackQueryHandler(refining_main_callback, pattern="^refining_main$|^ref_main$|^ref_main_PAGE_")
ref_select_handler  = CallbackQueryHandler(ref_select_callback,  pattern=r"^ref_sel_[A-Za-z0-9_]+$")
ref_confirm_handler = CallbackQueryHandler(ref_confirm_callback,  pattern=r"^ref_confirm_[A-Za-z0-9_]+$")

# (Adicione aqui os handlers de desmonte e batch que já existiam, mas usando as funções acima)
dismantle_confirm_handler = CallbackQueryHandler(confirm_dismantle_callback, pattern=r"^ref_dismantle_confirm:[a-f0-9-]+$")
noop_handler = CallbackQueryHandler(lambda u,c: u.callback_query.answer(), pattern=r"^noop")