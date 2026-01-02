# handlers/class_gate.py
# (VERSÃO FINAL: COMPATÍVEL COM SISTEMA DE ID STRING)

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from modules import player_manager

# Callback de abertura: ajuste para o que seu class_selection_handler espera.
CLASS_OPEN_CALLBACK = "class_open"

async def maybe_offer_class_choice(user_id: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Se o jogador precisar escolher classe, envia uma mensagem com o botão para abrir o menu de classes.
    Garante que só envia uma vez (marca flag no save).
    
    Args:
        user_id (str): O ID interno do jogador (ObjectId string).
        chat_id (int): O ID do chat para enviar a mensagem.
        context (ContextTypes.DEFAULT_TYPE): Contexto do bot.
    """
    # Garante que user_id seja string para o banco de dados
    user_id = str(user_id)
    
    # Busca dados do jogador (Async)
    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        return # Se não encontrar dados, sai silenciosamente

    # Verifica se precisa escolher classe (Síncrono na lógica, mas depende dos dados carregados)
    if not player_manager.needs_class_choice(pdata):
        return

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Escolher Classe", callback_data=CLASS_OPEN_CALLBACK)]
    ])

    txt = (
        "🎉 <b>Nível 5 alcançado!</b>\n"
        "Você desbloqueou a <b>escolha de classe</b>. Toque no botão abaixo para escolher."
    )
    
    # Envia a notificação
    try:
        await context.bot.send_message(chat_id=chat_id, text=txt, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        # Evita crash se o bot não conseguir enviar msg (ex: bloqueado)
        return

    # Marca que já oferecemos para não spamar (Async)
    await player_manager.mark_class_choice_offered(user_id)