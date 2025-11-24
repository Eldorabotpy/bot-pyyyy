# modules/events/event_menu.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)

# Tenta importar o manager da defesa de forma segura
try:
    from kingdom_defense import manager as defense_manager
    DEFENSE_AVAILABLE = True
except ImportError:
    DEFENSE_AVAILABLE = False

async def show_active_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a lista de TODOS os eventos disponíveis."""
    query = update.callback_query
    # Não damos query.answer() aqui se formos deletar a mensagem, 
    # mas para garantir o feedback visual, respondemos antes.
    try: await query.answer()
    except: pass

    text = (
        "🌌 **EVENTOS ESPECIAIS DE ELDORA** 🌌\n\n"
        "Os ventos da magia trazem desafios temporários para o reino.\n"
        "Escolha um evento para participar:"
    )

    keyboard = []

    # --- 1. Botão da Catacumba ---
    keyboard.append([
        InlineKeyboardButton("💀 Catacumbas do Reino (Raid)", callback_data="evt_cat_menu")
    ])

    # --- 2. Botão da Defesa do Reino ---
    is_defense_on = False
    if DEFENSE_AVAILABLE:
        try:
            if hasattr(defense_manager, 'is_event_active') and defense_manager.is_event_active():
                is_defense_on = True
        except:
            pass

    if is_defense_on:
        btn_text = "🔥 DEFESA DO REINO (EM ANDAMENTO!) 🔥"
    else:
        btn_text = "🛡️ Defesa do Reino"

    # Ajuste o callback abaixo conforme seu sistema de defesa
    keyboard.append([
        InlineKeyboardButton(btn_text, callback_data="kingdom_defense_join") 
    ])

    # --- 3. Botão de Voltar ---
    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data="back_to_kingdom")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # --- CORREÇÃO DO ERRO "NO TEXT TO EDIT" ---
    # Como o menu anterior pode ser uma foto, não usamos edit_message_text.
    # Nós apagamos a mensagem anterior e enviamos uma nova limpa.
    
    try:
        # Tenta apagar a mensagem anterior (seja foto ou texto)
        await query.message.delete()
    except Exception as e:
        logger.debug(f"Não foi possível apagar a mensagem anterior: {e}")

    # Envia o novo menu como uma mensagem nova
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )