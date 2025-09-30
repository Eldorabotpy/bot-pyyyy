# handlers/class_gate.py

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from modules import player_manager

# Callback de abertura: ajuste para o que seu class_selection_handler espera.
# Se o seu handler escuta outro pattern, troque "class_open" por ele.
CLASS_OPEN_CALLBACK = "class_open"

async def maybe_offer_class_choice(user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Se o jogador precisar escolher classe, envia uma mensagem com o botão para abrir o menu de classes.
    Garante que só envia uma vez (marca flag no save).
    """
    pdata = player_manager.get_player_data(user_id)
    if not pdata:
        return

    if not player_manager.needs_class_choice(pdata):
        return

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Escolher Classe", callback_data=CLASS_OPEN_CALLBACK)]
    ])

    txt = (
        "🎉 <b>Nível 10 alcançado!</b>\n"
        "Você desbloqueou a <b>escolha de classe</b>. Toque no botão abaixo para escolher."
    )
    await context.bot.send_message(chat_id=chat_id, text=txt, reply_markup=kb, parse_mode="HTML")

    # Marca que já oferecemos
    player_manager.mark_class_choice_offered(user_id)
