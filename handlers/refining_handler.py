# handlers/refining_handler.py
# (VERSÃO CORRIGIDA: Lote por Nível de Profissão + ObjectId Seguro)

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
from modules import game_data, player_manager, file_ids
from modules import refining_engine, dismantle_engine

ITEMS_PER_PAGE = 5
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. JOB HANDLERS (O CORAÇÃO DA CORREÇÃO)
# ==============================================================================

async def finish_refine_job(context: ContextTypes.DEFAULT_TYPE):
    """Finaliza Refino Único ou Lote."""
    job = context.job
    if not job: return

    user_id = job.data.get("user_id") 
    chat_id = job.chat_id
    mid = job.data.get("message_id_to_delete")

    if not user_id or isinstance(user_id, int):
        logger.error(f"❌ [Refino Job] ID inválido: {user_id}")
        return

    if mid:
        try: await context.bot.delete_message(chat_id, mid)
        except Exception: pass

    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return

    res = await refining_engine.finish_refine(pdata)
    
    if isinstance(res, str):
        await context.bot.send_message(chat_id, f"❗ {res}")
        return
    if not res: return

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
    # 🔔 NOTIFICA LEVEL UP DA PROFISSÃO
    xp_info = res.get("xp_info") or {}
    if xp_info.get("levels_gained", 0) > 0:
        new_lvl = xp_info.get("new_level")
        lines.append(f" ╰┈➤ 🏅 <b>Profissão subiu para Nv.{new_lvl}!</b>")
     
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Refino", callback_data="ref_main")]])
    await _safe_send_with_media(context, chat_id, "\n".join(lines), kb)


async def finish_dismantle_job(context: ContextTypes.DEFAULT_TYPE):
    """Finaliza Desmonte Único."""
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
# 2. CALLBACKS PRINCIPAIS
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
    
    kb.append([InlineKeyboardButton("🔙 Fechar", callback_data="back_to_kingdom")])


    await _safe_edit_or_send_with_media(q, context, "\n".join(lines), InlineKeyboardMarkup(kb))


async def ref_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    
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
    
    context.job_queue.run_once(
        finish_refine_job, 
        secs, 
        chat_id=q.message.chat_id,
        data={
            "user_id": uid, 
            "rid": rid, 
            "message_id_to_delete": mid 
        }, 
        name=f"refining:{uid}"
    )

# ==============================================================================
# 3. LOTE (BATCH) - COM LÓGICA 2x, 5x, 10x e NÍVEL
# ==============================================================================

async def ref_batch_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o menu para escolher a quantidade do lote."""
    q = update.callback_query
    try: await q.delete_message()
    except: pass
    
    rid = q.data.replace("ref_batch_menu_", "")
    
    uid = get_current_player_id(update, context)
    if not uid: return

    pdata = await player_manager.get_player_data(uid)
    rec = game_data.REFINING_RECIPES.get(rid)
    if not rec:
         await context.bot.send_message(q.message.chat_id, "❌ Receita inválida.")
         return
    
    # Quantidade máxima baseada APENAS nos materiais
    materials_limit = refining_engine.get_max_refine_quantity(pdata, rec)
    
    # Nível da Profissão do Jogador
    prof = pdata.get("profession", {})
    prof_lvl = int(prof.get("level", 1))
    prof_lvl = max(1, prof_lvl)

    rec_name = rec.get("display_name", "Item").upper()
    
    txt = (
        f"📚 <b>LOTE: {rec_name}</b>\n"
        f"──────────────────────\n"
        f" ╰┈➤ 📦 <b>Materiais para:</b> <code>{materials_limit}</code> un.\n"
        f" ╰┈➤ 👷 <b>Seu Nível:</b> <code>{prof_lvl}</code>\n"
        f" ╰┈➤ ⏳ <b>Tempo:</b> <code>Acumulativo</code>\n"
        f" ╰┈➤ ⚖️ <b>XP:</b> <code>-50%</code> (Penalidade)\n"
        f"──────────────────────\n"
        f"<i>Quantas unidades deseja forjar?</i>"
    )
    
    kb = []
    
    # Opções desejadas: 2, 5, 10 e Nível do Jogador
    options_to_check = [2, 5, 10]
    valid_options = []

    # 1. Verifica as opções fixas (2, 5, 10)
    for opt in options_to_check:
        if materials_limit >= opt:
            valid_options.append(opt)

    # 2. Adiciona o Nível do Jogador se tiver material suficiente
    # (Evita duplicata se o nível for 2, 5 ou 10)
    has_lvl_option = False
    if materials_limit >= prof_lvl and prof_lvl > 1:
        if prof_lvl not in valid_options:
            valid_options.append(prof_lvl)
        has_lvl_option = True
    
    # Ordena para ficar bonito
    valid_options = sorted(list(set(valid_options)))

    row = []
    for val in valid_options:
        # Texto personalizado para o botão de Nível
        if val == prof_lvl and has_lvl_option:
            label = f"🎓 Nv. {val}"
        else:
            label = f"⚡ {val}x"
            
        row.append(InlineKeyboardButton(label, callback_data=f"ref_batch_go_{rid}_{val}"))
        
        if len(row) >= 3:
            kb.append(row); row = []
            
    if row: kb.append(row)
    
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data=f"ref_sel_{rid}")])
    
    mkey = rec.get("media_key")
    await _safe_send_with_media(context, q.message.chat_id, txt, InlineKeyboardMarkup(kb), media_key=mkey)


async def ref_batch_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Executa o refino em lote."""
    q = update.callback_query
    try: await q.delete_message()
    except Exception: pass
    
    payload = q.data.replace("ref_batch_go_", "")
    try:
        rid, qty_str = payload.rsplit("_", 1)
        qty = int(qty_str)
    except ValueError:
        return

    uid = get_current_player_id(update, context)
    if not uid: return

    pdata = await player_manager.get_player_data(uid)
    
    if pdata.get("player_state", {}).get("action") not in (None, "idle"):
        await context.bot.send_message(q.message.chat_id, "⚠️ Você já está ocupado!")
        return

    res = await refining_engine.start_batch_refine(pdata, rid, qty)
    
    if isinstance(res, str): 
        await context.bot.send_message(q.message.chat_id, f"❌ {res}")
        return

    seconds = int(res["duration_seconds"])
    xp = res["xp_reward"]
    rec = game_data.REFINING_RECIPES.get(rid, {})
    name = rec.get("display_name") or rid.replace("_", " ").title()
    
    txt = (
        f"⚙️ <b>LOTE INICIADO\n"
        f" ╰┈➤ {qty}x {name}</b>\n"
        f"──────────────────────\n"
        f" ╰┈➤ ⏳ <b>Tempo Total:</b> <code>{_fmt_minutes_or_seconds(seconds)}</code>\n"
        f" ╰┈➤ ✨ <b>XP Previsto:</b> <code>{xp}</code>\n"
    )
    
    sent = await _safe_send_with_media(context, q.message.chat_id, txt)
    mid = sent.message_id if sent else None
    
    context.job_queue.run_once(
        finish_refine_job, 
        seconds, 
        chat_id=q.message.chat_id,
        data={
            "user_id": uid, 
            "rid": rid, 
            "message_id_to_delete": mid
        }, 
        name=f"refining:{uid}"
    )

# ==============================================================================
# 4. DESMONTE HANDLERS
# ==============================================================================

async def show_dismantle_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    uid = get_current_player_id(update, context)
    if not uid: return

    pdata = await player_manager.get_player_data(uid)
    
    page = 0
    if ":page:" in q.data: page = int(q.data.split(':page:')[1])
    
    inv = pdata.get("inventory", {})
    equip = set(pdata.get("equipment", {}).values())
    
    items = []
    from modules import crafting_registry
    
    for uid_item, d in inv.items():
        if isinstance(d, dict) and uid_item not in equip:
            if crafting_registry.get_recipe_by_item_id(d.get("base_id")):
                items.append((uid_item, d))
    
    items.sort(key=lambda x: x[1].get("display_name", ""))
    
    total_items = len(items)
    total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    cur_items = items[page*ITEMS_PER_PAGE : (page+1)*ITEMS_PER_PAGE]
    
    kb = []
    for iuid, idata in cur_items:
        plus = idata.get("enhancement", idata.get("level", 0))
        plus_txt = f" +{plus}" if plus > 0 else ""
        base_id = idata.get("base_id")
        static_data = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {})
        emoji = idata.get("emoji") or static_data.get("emoji", "📦")
        rarity = (idata.get("rarity") or "comum").upper()
        
        btn_text = f"{emoji} {idata.get('display_name')}{plus_txt} [{rarity}]"
        kb.append([InlineKeyboardButton(btn_text, callback_data=f"ref_dismantle_preview:{iuid}")])
        
    nav_row = []
    if page > 0: 
        nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"ref_dismantle_list:page:{page-1}"))
    nav_row.append(InlineKeyboardButton("🔙 Voltar", callback_data="ref_main"))
    if (page+1)*ITEMS_PER_PAGE < total_items: 
        nav_row.append(InlineKeyboardButton("➡️", callback_data=f"ref_dismantle_list:page:{page+1}"))
    
    kb.append(nav_row)
    
    msg = f"♻️ <b>Desmontar</b> (Pág {page+1}/{max(1, total_pages)})\nEscolha um item para reciclar:"
    if not items: msg += "\n\n<i>(Nenhum item desmontável encontrado)</i>"
    
    await _safe_edit_or_send_with_media(q, context, msg, InlineKeyboardMarkup(kb), media_key='desmontagem_menu_image')

async def show_dismantle_preview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    uid = get_current_player_id(update, context)
    if not uid: return

    try: iuid = q.data.split(':')[1]
    except: return
    
    pdata = await player_manager.get_player_data(uid)
    item = pdata.get("inventory", {}).get(iuid)
    if not item: return await show_dismantle_list_callback(update, context)

    base_id = item.get("base_id")
    target_rarity = item.get("rarity", "comum")
    
    count_dupes = 0
    inv = pdata.get("inventory", {})
    equip = set(pdata.get("equipment", {}).values())
    for u, d in inv.items():
        if isinstance(d, dict) and u not in equip:
            if d.get("base_id") == base_id and d.get("rarity", "comum") == target_rarity:
                count_dupes += 1

    item_line = _fmt_item_details_styled(item)
    txt = (f"<b>CONFIRMAÇÃO DE DESMONTE</b>\n"
           f" ╰┈➤ {item_line}\n\n"
           f"⚠️ <i>O item será destruído.</i>")
    
    kb = []
    kb.append([InlineKeyboardButton("✅ 𝐂𝐨𝐧𝐟𝐢𝐫𝐦𝐚𝐫 (1 Unid)", callback_data=f"ref_dismantle_confirm:{iuid}")])
    
    if count_dupes > 1:
        kb.append([InlineKeyboardButton(f"♻️ 𝐃𝐞𝐬𝐦𝐨𝐧𝐭𝐚𝐫 𝐓𝐨𝐝𝐨𝐬 ({count_dupes}x)", 
                                        callback_data=f"ref_dismantle_bulk:{base_id}:{target_rarity}")])

    kb.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="ref_dismantle_list")])
    
    await _safe_edit_or_send_with_media(q, context, txt, InlineKeyboardMarkup(kb))

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
    
    job_data = {
        "user_id": uid,
        "unique_item_id": iuid, 
        "item_name": res.get("item_name"),
        "base_id": res.get("base_id"),
        "rarity": pdata.get("player_state", {}).get("details", {}).get("rarity"), 
        "message_id_to_delete": mid
    }
    context.job_queue.run_once(finish_dismantle_job, dur, chat_id=q.message.chat_id, data=job_data, name=f"dismantle_{uid}")

async def confirm_bulk_dismantle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try: await q.delete_message()
    except: pass
    
    uid = get_current_player_id(update, context)
    if not uid: return
    
    parts = q.data.split(':') 
    base_id = parts[1]
    rarity_filter = parts[2] if len(parts) > 2 else "comum"
    
    pdata = await player_manager.get_player_data(uid)
    if pdata.get("player_state", {}).get("action") not in (None, "idle"):
        await context.bot.send_message(q.message.chat_id, "Ocupado!")
        return

    inv = pdata.get("inventory", {})
    equip = set(pdata.get("equipment", {}).values())
    count_available = 0
    for uniq, data in inv.items():
        if uniq not in equip and isinstance(data, dict):
            if data.get("base_id") == base_id and data.get("rarity", "comum") == rarity_filter:
                count_available += 1
    
    if count_available < 2:
        await context.bot.send_message(q.message.chat_id, "Quantidade insuficiente.")
        return

    res = await dismantle_engine.start_batch_dismantle(pdata, base_id, rarity_filter, count_available)
    if isinstance(res, str):
        await context.bot.send_message(q.message.chat_id, res)
        return

    qty = res.get("qty")
    name = res.get("item_name")
    dur = res.get("duration_seconds", 60)
    
    txt = f"♻️ Desmontando {qty}x <b>{name} [{rarity_filter.title()}]</b>... (~{_fmt_minutes_or_seconds(dur)})"
    sent = await _safe_send_with_media(context, q.message.chat_id, txt)
    mid = sent.message_id if sent else None
    
    details = pdata.get("player_state", {}).get("details", {})
    details["message_id_to_delete"] = mid
    details["user_id"] = uid
    
    context.job_queue.run_once(finish_bulk_dismantle_job, dur, chat_id=q.message.chat_id, data=details, name=f"dismantle_bulk_{uid}")

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

def _fmt_item_details_styled(item_data: dict) -> str:
    name = item_data.get("display_name", "Item")
    rarity = (item_data.get("rarity") or "comum").title()
    lvl = item_data.get("enhancement", item_data.get("level", 0))
    lvl_str = f" [+ {lvl}]" if lvl > 0 else ""
    return f"『 {name}{lvl_str} [{rarity}] 』"

async def _safe_send_with_media(context, chat_id, caption, reply_markup=None, media_key=None, fallback_key="refino_universal"):
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
    try: await query.message.delete()
    except: pass
    return await _safe_send_with_media(context, query.message.chat_id, caption, reply_markup, media_key)

# =========================
# REGISTROS DE HANDLERS
# =========================

refining_main_handler = CallbackQueryHandler(refining_main_callback, pattern="^refining_main$|^ref_main$|^ref_main_PAGE_")
ref_select_handler  = CallbackQueryHandler(ref_select_callback,  pattern=r"^ref_sel_[A-Za-z0-9_]+$")
ref_confirm_handler = CallbackQueryHandler(ref_confirm_callback,  pattern=r"^ref_confirm_[A-Za-z0-9_]+$")

ref_batch_menu_handler = CallbackQueryHandler(ref_batch_menu_callback, pattern=r"^ref_batch_menu_")
ref_batch_go_handler = CallbackQueryHandler(ref_batch_confirm_callback, pattern=r"^ref_batch_go_")

dismantle_list_handler = CallbackQueryHandler(show_dismantle_list_callback, pattern=r"^ref_dismantle_list(:page:\d+)?$")
dismantle_preview_handler = CallbackQueryHandler(show_dismantle_preview_callback, pattern=r"^ref_dismantle_preview:[a-f0-9-]+$")
dismantle_confirm_handler = CallbackQueryHandler(confirm_dismantle_callback, pattern=r"^ref_dismantle_confirm:[a-f0-9-]+$")
dismantle_bulk_handler = CallbackQueryHandler(confirm_bulk_dismantle_callback, pattern=r"^ref_dismantle_bulk:.+$")

noop_handler = CallbackQueryHandler(lambda u,c: u.callback_query.answer(), pattern=r"^noop")