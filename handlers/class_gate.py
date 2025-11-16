# handlers/class_gate.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from modules import player_manager

# Callback de abertura: ajuste para o que seu class_selection_handler espera.
CLASS_OPEN_CALLBACK = "class_open"

async def maybe_offer_class_choice(user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Se o jogador precisar escolher classe, envia uma mensagem com o botão para abrir o menu de classes.
    Garante que só envia uma vez (marca flag no save).
    """
    # <<< CORREÇÃO 1: Adiciona await >>>
    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        return # Se não encontrar dados, sai silenciosamente

    # Assumindo que needs_class_choice é síncrono (apenas verifica o dicionário pdata)
    if not player_manager.needs_class_choice(pdata):
        return

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Escolher Classe", callback_data=CLASS_OPEN_CALLBACK)]
    ])

    txt = (
        "🎉 <b>Nível 5 alcançado!</b>\n"
        "Você desbloqueou a <b>escolha de classe</b>. Toque no botão abaixo para escolher."
    )
    # <<< CORREÇÃO 2: Adiciona await (já estava correto) >>>
    await context.bot.send_message(chat_id=chat_id, text=txt, reply_markup=kb, parse_mode="HTML")

    # Marca que já oferecemos
    # <<< CORREÇÃO 3: Adiciona await >>>
    # (Assumindo que mark_class_choice_offered é async porque salva os dados)
    await player_manager.mark_class_choice_offered(user_id)