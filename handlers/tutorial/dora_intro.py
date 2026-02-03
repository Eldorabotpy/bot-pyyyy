# handlers/tutorial/dora_intro.py

from __future__ import annotations
import re

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from modules import player_manager
from modules.auth_utils import get_current_player_id

CB_DORA_NAME_START = "dora_name_start"
CB_DORA_NAME_WHY = "dora_name_why"
CB_DORA_CANCEL = "dora_cancel_name"

NAME_MIN = 3
NAME_MAX = 18
NAME_RE = re.compile(r"^[A-Za-zÀ-ÿ0-9 ]+$")  # letras, números e espaço


def _extract_message(update: Update):
    # funciona tanto por /start (message) quanto por callback
    if update.message:
        return update.message
    if update.callback_query and update.callback_query.message:
        return update.callback_query.message
    return None


async def show_intro(update: Update, context: ContextTypes.DEFAULT_TYPE, player_data: dict):
    msg = _extract_message(update)
    if not msg:
        return

    text = (
        "🧭 <b>PORTO DE ELDORA</b>\n"
        "👩‍✈️ <b>Dora:</b> Bem-vindo(a) a Eldora.\n\n"
        "Antes de seguir para o Reino, preciso registrar seu <b>nome de personagem</b>.\n"
        "Ele aparecerá em batalhas, ranking e clãs."
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Escolher nome", callback_data=CB_DORA_NAME_START)],
        [InlineKeyboardButton("❓ Por que isso é necessário?", callback_data=CB_DORA_NAME_WHY)],
    ])

    await msg.reply_text(text, reply_markup=kb, parse_mode="HTML")


async def dora_intro_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q or not q.message:
        return
    await q.answer()

    uid = get_current_player_id(update, context)
    if not uid:
        return

    data = q.data or ""

    if data == CB_DORA_NAME_WHY:
        text = (
            "👩‍✈️ <b>Dora:</b> O login é sua <b>conta</b>.\n"
            "O nome do personagem é sua <b>identidade no mundo</b>.\n\n"
            f"📌 Regras: {NAME_MIN}-{NAME_MAX} caracteres, letras/números e espaço."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✍️ Escolher nome", callback_data=CB_DORA_NAME_START)],
        ])
        await q.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
        return

    if data == CB_DORA_NAME_START:
        context.user_data["awaiting_dora_character_name"] = True
        await q.message.reply_text(
            "✍️ <b>Digite o nome do seu personagem</b> (ex: Ana, Kael, Lobo do Norte):",
            parse_mode="HTML",
        )
        return


async def dora_name_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Captura a próxima mensagem do usuário como nome, se estiver no modo 'awaiting'.
    """
    if not update.message or not update.message.text:
        return
    
    print(">>> DORA_NAME_MESSAGE:", update.message.text)
    print(">>> awaiting:", context.user_data.get("awaiting_dora_character_name"))
    print(">>> logged_player_id:", context.user_data.get("logged_player_id"))

    if not context.user_data.get("awaiting_dora_character_name"):
        return

    uid = context.user_data.get("logged_player_id")
    if not uid:
        return
   
    raw = update.message.text.strip()
    # encerra o modo awaiting de qualquer forma (para não travar)
    context.user_data["awaiting_dora_character_name"] = False

    # validações
    if len(raw) < NAME_MIN or len(raw) > NAME_MAX:
        context.user_data["awaiting_dora_character_name"] = True
        await update.message.reply_text(
            f"❌ Nome inválido. Use {NAME_MIN}-{NAME_MAX} caracteres.\nTente novamente:",
            parse_mode="HTML",
        )
        return

    if not NAME_RE.match(raw):
        context.user_data["awaiting_dora_character_name"] = True
        await update.message.reply_text(
            "❌ Use apenas letras, números e espaços.\nTente novamente:",
            parse_mode="HTML",
        )
        return

    # salva no player
    player_data = await player_manager.get_player_data(uid)
    if not player_data:
        await update.message.reply_text("❌ Erro: personagem não encontrado.")
        return

    player_data["character_name"] = raw
    player_data.setdefault("tutorial_flags", {})
    player_data.setdefault("onboarding_stage", "name")
    player_data["onboarding_stage"] = "profession"

    await player_manager.save_player_data(player_data["_id"], player_data)

    await update.message.reply_text(
        f"✅ Registrado, <b>{raw}</b>.\n\nAgora vamos escolher sua <b>profissão</b>.",
        parse_mode="HTML",
    )

    # chama a próxima tela (profissão) sem depender do /start
    from handlers.tutorial import dora_profession
    await dora_profession.show_profession_menu(update, context, player_data)
