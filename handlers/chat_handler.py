# Em handlers/chat_handler.py

import random
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from modules.chat_responses import CHAT_RESPONSES
from modules import player_manager

async def chat_interaction_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Verifica cada mensagem de texto e responde com texto, GIF ou sticker
    se encontrar uma palavra-chave.
    """
    print(f"[DEBUG] chat_handler foi ativado pela mensagem: '{update.message.text}'")
    if not update.message or not update.message.text:
        return

    message_text = update.message.text.lower()

    for keywords, responses in CHAT_RESPONSES.items():
        if any(keyword in message_text for keyword in keywords):
            # Escolhe uma das opções de resposta aleatoriamente
            response_data = random.choice(responses)
            
            response_type = response_data.get("type")
            content = response_data.get("content")

            try:
                # Decide qual função do bot usar com base no tipo
                if response_type == "text":
                    await update.message.reply_text(content)
                elif response_type == "gif":
                    # GIFs são enviados como "animações"
                    await update.message.reply_animation(animation=content)
                elif response_type == "sticker":
                    await update.message.reply_sticker(sticker=content)
            except Exception as e:
                print(f"Erro ao enviar resposta do chat: {e}")

            # Para o loop após encontrar a primeira correspondência
            break

async def debug_inv_cmd(update, context):
    """Comando secreto para ver IDs do inventário."""
    user_id = update.effective_user.id
    pdata = await player_manager.get_player_data(user_id)
    
    inv = pdata.get("inventory", {})
    msg = "🕵️‍♂️ **RAIO-X DO INVENTÁRIO** 🕵️‍♂️\n\n"
    
    if not inv:
        msg += "Inventário vazio."
    else:
        for item_id, qtd in inv.items():
            # Mostra o ID cru e a quantidade
            msg += f"📦 ID: <code>{item_id}</code> | Qtd: {qtd}\n"
            
    await update.message.reply_text(msg, parse_mode="HTML")

# O handler em si não muda
chat_interaction_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, chat_interaction_callback)

