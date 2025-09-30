# handlers/profession_handler.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules import player_manager, game_data

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

def _prof_label(key: str, data: dict) -> str:
    return f"{data.get('emoji','💼')} {data.get('display_name', key.capitalize())}"

async def show_profession_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a lista de profissões apenas se o jogador ainda não tem profissão."""
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = q.message.chat_id

    pdata = player_manager.get_player_data(user_id)
    if not pdata:
        await _safe_edit_or_send(q, context, chat_id, "❌ Não encontrei seus dados. Use /start.")
        return

    if (pdata.get('profession') or {}).get('type'):
        # Já tem profissão → não permite trocar, só informa
        cur = pdata['profession']['type']
        name = game_data.PROFESSIONS_DATA.get(cur, {}).get('display_name', cur)
        txt = f"💼 Você já escolheu sua profissão: <b>{name}</b>."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("👤 Voltar ao Personagem", callback_data="profile")]])
        await _safe_edit_or_send(q, context, chat_id, txt, kb)
        return

    title = "💼 <b>Escolher Profissão</b>\nSelecione uma profissão para desbloquear coletas e bônus.\n"
    kb = []
    for key, data in (game_data.PROFESSIONS_DATA or {}).items():
        # só mostre as de coleta, se quiser (ou comente essa linha para listar todas)
        # if data.get('category') != 'gathering': continue
        kb.append([InlineKeyboardButton(_prof_label(key, data), callback_data=f"job_pick_{key}")])
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="profile")])

    await _safe_edit_or_send(q, context, chat_id, title, InlineKeyboardMarkup(kb))

async def pick_profession_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Define a profissão (somente se ainda não houver uma) e volta ao Perfil."""
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = q.message.chat_id

    pdata = player_manager.get_player_data(user_id)
    if not pdata:
        await _safe_edit_or_send(q, context, chat_id, "❌ Não encontrei seus dados. Use /start.")
        return

    if (pdata.get('profession') or {}).get('type'):
        await q.answer("Você já possui uma profissão.", show_alert=True)
        return

    prefix = "job_pick_"
    data = q.data or ""
    if not data.startswith(prefix):
        return
    prof_key = data[len(prefix):]

    if prof_key not in (game_data.PROFESSIONS_DATA or {}):
        await q.answer("Profissão inválida.", show_alert=True)
        return

    pdata['profession'] = {"type": prof_key, "level": 1, "xp": 0}
    player_manager.save_player_data(user_id, pdata)

    name = game_data.PROFESSIONS_DATA[prof_key].get('display_name', prof_key.capitalize())
    txt = f"✅ Profissão definida: <b>{name}</b>!"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("👤 Voltar ao Personagem", callback_data="profile")]])
    await _safe_edit_or_send(q, context, chat_id, txt, kb)

# exports
job_menu_handler = CallbackQueryHandler(show_profession_menu, pattern=r'^job_menu$')
job_pick_handler = CallbackQueryHandler(pick_profession_callback, pattern=r'^job_pick_[A-Za-z0-9_]+$')
