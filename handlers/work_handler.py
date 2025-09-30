# handlers/work_handler.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from datetime import timedelta
from modules import player_manager, game_data
from modules.profession_engine import WORK_RECIPES, preview_work, start_work, finish_work

def _humanize(seconds: int) -> str:
    if seconds >= 60:
        m = round(seconds/60)
        return f"{m} min"
    return f"{int(seconds)} s"

async def show_work_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    user_id = query.from_user.id
    pdata = player_manager.get_player_data(user_id)

    prof = pdata.get('profession', {}) or {}
    if prof.get('type') not in game_data.PROFESSIONS_DATA or game_data.PROFESSIONS_DATA[prof['type']]['category'] != 'crafting':
        await query.answer("Você não tem uma profissão de produção/forja.", show_alert=True)
        return

    text = f"<b>Trabalhos de {game_data.PROFESSIONS_DATA[prof['type']]['display_name']} (Nível {prof.get('level',1)})</b>\nSelecione:"
    kb = []

    for rid, rec in WORK_RECIPES.items():
        if rec.get('profession') != prof['type']:
            continue
        prev = preview_work(rid, pdata)
        mark = "✅" if prev['can_work'] else "❌"
        t = _humanize(prev['duration_seconds'])
        kb.append([InlineKeyboardButton(f"{mark} {rec['display_name']} (Nvl {rec['level_req']}, ~{t})", callback_data=f"work_start_{rid}")])

    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="continue_after_action")])
    rm = InlineKeyboardMarkup(kb)

    try:
        await query.edit_message_text(text=text, reply_markup=rm, parse_mode='HTML')
    except Exception:
        await context.bot.send_message(chat_id=query.message.chat_id, text=text, reply_markup=rm, parse_mode='HTML')

async def start_work_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    rid = query.data.replace("work_start_", "")
    res = start_work(user_id, rid)
    if isinstance(res, dict) and res.get("error"):
        await query.answer(res["error"], show_alert=True); return

    duration = int(res["duration_seconds"])
    # agenda o término
    context.job_queue.run_once(_finish_work_job, when=duration, user_id=user_id, chat_id=chat_id, data={"recipe_id": rid})

    try:
        await query.edit_message_text(text=f"🛠️ Trabalho iniciado! Conclusão em ~{_humanize(duration)}.", parse_mode='HTML')
    except Exception:
        await context.bot.send_message(chat_id=chat_id, text=f"🛠️ Trabalho iniciado! Conclusão em ~{_humanize(duration)}.", parse_mode='HTML')

async def _finish_work_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id, chat_id = job.user_id, job.chat_id
    out = finish_work(user_id)
    if out.get("status") == "success":
        name = game_data.ITEMS_DATA.get(out["result_base_id"], {}).get("display_name", out["result_base_id"])
        await context.bot.send_message(chat_id=chat_id, text=f"✅ Trabalho concluído! Você produziu: {name}.")
    else:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Trabalho não foi concluído: {out.get('error','erro desconhecido')}")

work_main_handler = CallbackQueryHandler(show_work_list, pattern=r'^(forge|work_show_list)$')
work_start_handler = CallbackQueryHandler(start_work_callback, pattern=r'^work_start_')
