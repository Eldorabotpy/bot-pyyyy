# handlers/evolution_handler.py
from __future__ import annotations
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from modules.player_manager import get_player_data
from modules.game_data.classes import CLASSES_DATA

async def open_class_evolution_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Abre o menu de Evolução de Classe (placeholder inicial)."""
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    pdata = get_player_data(user_id) or {}
    pclass = (pdata.get("class") or "guerreiro").lower()
    plevel = int(pdata.get("level") or 1)

    cinfo = CLASSES_DATA.get(pclass, {})
    cname = f"{cinfo.get('emoji','')} {cinfo.get('display_name', pclass.title())}"

    text = (
        "🧬 <b>Evolução de Classe</b>\n\n"
        f"Classe atual: <b>{cname}</b>\n"
        f"Nível atual: <b>{plevel}</b>\n\n"
        "Aqui você poderá evoluir sua classe quando atingir o nível e itens necessários.\n"
        "• Próximo passo: listar evoluções liberadas e validar itens.\n"
    )

    kb = [
        [InlineKeyboardButton("🔄 𝐀𝐭𝐮𝐚𝐥𝐢𝐳𝐚𝐫", callback_data="char_evolution")],
        [InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫 𝐚𝐨 𝐏𝐞𝐫𝐬𝐨𝐧𝐚𝐠𝐞𝐦", callback_data="status_open")],
    ]
    try:
        await q.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
    except Exception:
        await q.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

# Handler pronto para registrar no main.py
evolution_open_handler = CallbackQueryHandler(open_class_evolution_menu, pattern=r"^char_evolution$")
