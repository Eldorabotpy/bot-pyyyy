# handlers/admin/common.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancela a conversa atual de forma limpa e segura.
    Oferece um botão para retornar ao menu principal de admin.
    """
    message_text = "Operação cancelada."
    
    # É importante limpar apenas os dados temporários da conversa.
    # Como esta é uma função genérica, a limpeza específica das chaves
    # deve ser feita no último passo de cada conversa ou aqui, se houver um padrão.
    # Por segurança, vamos evitar o .clear() e deixar a limpeza para cada handler específico
    # ou adotar um padrão como context.user_data['temp_data'].
    
    # Oferece ao usuário uma forma clara de voltar ao menu
    keyboard = [
        [InlineKeyboardButton("⬅️ Voltar ao Menu de Admin", callback_data='admin_main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Verifica se a chamada veio de um comando ou de um botão
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=message_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text=message_text, reply_markup=reply_markup)
    
    # Encerra a conversa. O bot agora está em um estado neutro.
    return ConversationHandler.END
