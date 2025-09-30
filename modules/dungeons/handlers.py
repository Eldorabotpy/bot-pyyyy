# modules/dungeons/handlers.py
from __future__ import annotations
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

logger = logging.getLogger(__name__)

# nomes/dificuldades padronizados (pode mudar depois)
DIFFICULTIES = {
    "iniciante":    {"label": " 🥉Normal"},
    "calamidade":   {"label": " 🥈Calamidade"},
    "infernal": {"label": " 🥇Infernal"},
}

# ------------- UI: abrir seletor de dificuldade -------------
async def open_dungeon_selector(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = (q.data or "")
    # esperado: dgn_open:<region_key>
    try:
        _, region_key = data.split(":", 1)
    except Exception:
        region_key = "desconhecida"

    title = f"🏰 Calabouço — Região: <b>{region_key}</b>\nEscolha a dificuldade:"
    rows = []
    for diff_key, meta in DIFFICULTIES.items():
        rows.append([InlineKeyboardButton(meta["label"], callback_data=f"dgn_diff:{region_key}:{diff_key}")])

    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="continue_after_action")])
    markup = InlineKeyboardMarkup(rows)

    # tenta editar a legenda da mídia; se falhar, manda como texto
    try:
        await q.edit_message_caption(caption=title, reply_markup=markup, parse_mode="HTML")
    except Exception:
        await q.edit_message_text(text=title, reply_markup=markup, parse_mode="HTML")

# ------------- UI: clique em dificuldade -------------
async def pick_difficulty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = (q.data or "")
    # esperado: dgn_diff:<region_key>:<difficulty>
    try:
        _, region_key, difficulty = data.split(":", 2)
    except Exception:
        region_key, difficulty = "desconhecida", "facil"

    # por enquanto só confirma; depois chamaremos a rotina de setup da dungeon
    text = (
        f"🏰 Calabouço selecionado!\n"
        f"• Região: <b>{region_key}</b>\n"
        f"• Dificuldade: <b>{difficulty}</b>\n\n"
        f"(placeholder) Em breve iniciamos a instância da dungeon com mobs e boss."
    )
    rows = [[InlineKeyboardButton("⬅️ Voltar", callback_data="continue_after_action")]]
    markup = InlineKeyboardMarkup(rows)

    try:
        await q.edit_message_caption(caption=text, reply_markup=markup, parse_mode="HTML")
    except Exception:
        await q.edit_message_text(text=text, reply_markup=markup, parse_mode="HTML")

# ------------- Exports (registre no main) -------------
dungeon_open_handler      = CallbackQueryHandler(open_dungeon_selector, pattern=r"^dgn_open:[A-Za-z0-9_]+$")
dungeon_pick_diff_handler = CallbackQueryHandler(pick_difficulty,     pattern=r"^dgn_diff:[A-Za-z0-9_]+:(facil|normal|infernal)$")
