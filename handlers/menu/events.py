# handlers/menu/events.py
# (VERSÃO CORRIGIDA: Hub de Eventos + Correção do Erro de Imagem)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes
import logging

# Tenta importar o manager da defesa
try:
    from kingdom_defense.engine import event_manager
    DEFENSE_AVAILABLE = True
except ImportError:
    DEFENSE_AVAILABLE = False
    event_manager = None

logger = logging.getLogger(__name__)

async def show_events_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Exibe o Hub de Eventos (Defesa do Reino, Raids, etc).
    CORREÇÃO: Deleta a mensagem anterior (se for foto) para evitar erro de edição.
    """
    query = update.callback_query
    if query:
        try: await query.answer()
        except: pass

    # --- 1. PREPARAÇÃO DO TEXTO E BOTÕES ---
    text = (
        "🌌 **HUB DE EVENTOS DE ELDORA** 🌌\n\n"
        "Os ventos da magia trazem desafios temporários para o reino.\n"
        "Escolha um evento para participar:"
    )

    keyboard = []

    # [BOTÃO 1] Catacumbas (Seu sistema de Raid antigo/atual)
    keyboard.append([
        InlineKeyboardButton("💀 Catacumbas (Raid)", callback_data="evt_cat_menu")
    ])

    # [BOTÃO 2] Defesa do Reino
    defense_status = "Inativo"
    defense_btn_text = "🛡️ Defesa do Reino"
    
    if DEFENSE_AVAILABLE and event_manager:
        if event_manager.is_active:
            status = event_manager.get_queue_status_text()
            defense_status = "🔥 EM ANDAMENTO 🔥"
            defense_btn_text = f"🔥 DEFESA DO REINO ({event_manager.current_wave}ª Onda)"
            text += f"\n\n🚨 **ALERTA DE INVASÃO:**\n{status}"

    # O callback deve ser 'defesa_reino_main' para abrir o menu do kingdom_defense/handler.py
    keyboard.append([
        InlineKeyboardButton(defense_btn_text, callback_data="defesa_reino_main")
    ])

    # [BOTÃO VOLTAR]
    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data="show_kingdom_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    # --- 2. CORREÇÃO DO ERRO DE EDIÇÃO (FOTO -> TEXTO) ---
    # O menu do reino geralmente tem uma foto. Não podemos usar edit_message_text.
    # A solução segura é apagar a anterior e mandar uma nova.
    
    try:
        # Tenta apagar a mensagem anterior (seja foto, vídeo ou texto)
        if query and query.message:
            await query.message.delete()
    except Exception as e:
        logger.warning(f"Não foi possível apagar mensagem anterior: {e}")

    # Envia o novo menu como uma mensagem limpa
    if update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )