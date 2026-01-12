# handlers/events/event_menu.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, Application
import logging

logger = logging.getLogger(__name__)

# Tenta importar o manager da defesa de forma segura
try:
    from kingdom_defense.engine import event_manager as defense_manager
    DEFENSE_AVAILABLE = True
except ImportError:
    DEFENSE_AVAILABLE = False

async def show_active_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a lista de TODOS os eventos disponíveis."""
    query = update.callback_query
    # Garante resposta ao clique
    try: await query.answer()
    except: pass

    text = (
        "🌌 **HUB DE EVENTOS DE ELDORA** 🌌\n\n"
        "Os ventos da magia trazem desafios temporários para o reino.\n"
        "Escolha um evento para participar:"
    )

    keyboard = []

    # --- 1. Botão da Catacumba (Seu calabouço antigo/raid) ---
    keyboard.append([
        InlineKeyboardButton("💀 Catacumbas do Reino (Raid)", callback_data="evt_cat_menu")
    ])

    # --- 2. Botão da Defesa do Reino ---
    is_defense_on = False
    status_text = ""
    
    if DEFENSE_AVAILABLE:
        try:
            # Verifica diretamente no manager se está ativo
            if defense_manager.is_active:
                is_defense_on = True
                status_text = defense_manager.get_queue_status_text()
        except Exception as e:
            logger.error(f"Erro ao checar status da defesa: {e}")

    if is_defense_on:
        btn_text = "🔥 DEFESA DO REINO (EM ANDAMENTO!) 🔥"
    else:
        btn_text = "🛡️ Defesa do Reino (Inativo)"

    # Callback aponta para o menu principal da Defesa
    keyboard.append([
        InlineKeyboardButton(btn_text, callback_data="defesa_reino_main") 
    ])

    # --- 3. World Boss (Exemplo futuro) ---
    # keyboard.append([InlineKeyboardButton("🐉 World Boss", callback_data="wb_menu_main")])

    # --- 4. Botão de Voltar ---
    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data="show_kingdom_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Lógica de envio seguro (Apaga msg anterior se for mídia, ou edita se for texto)
    try:
        # Se a mensagem anterior tiver foto/video, é melhor apagar e mandar nova
        if query.message.photo or query.message.video or query.message.document:
            await query.message.delete()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            # Se for texto, edita (mais suave)
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.warning(f"Fallback no menu de eventos: {e}")
        # Fallback final
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except: pass

def register_handlers(application: Application):
    """Registra os handlers deste módulo."""
    # Ouve o clique do botão "💀 Eventos" do menu principal
    application.add_handler(CallbackQueryHandler(show_active_events, pattern='^evt_hub_principal$'))
    
    # Se tiver algum botão de "Voltar" dentro de sub-menus de eventos que chame este menu
    application.add_handler(CallbackQueryHandler(show_active_events, pattern='^back_to_event_hub$'))