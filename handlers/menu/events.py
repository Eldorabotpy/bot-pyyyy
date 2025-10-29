# handlers/menu/events.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from modules import player_manager
from modules.dungeon_definitions import DUNGEONS

async def show_events_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o menu de eventos especiais disponíveis."""
    query = update.callback_query
    await query.answer()

    # <<< CORREÇÃO: Adiciona await >>>
    player_data = await player_manager.get_player_data(query.from_user.id)
    player_location = player_data.get("current_location")

    text = "Selecione um evento especial para ver os detalhes:"
    keyboard = []
    found_dungeon = False
    for dungeon_id, dungeon_info in DUNGEONS.items():
        # (Assumindo que DUNGEONS é um dicionário síncrono carregado na memória)
        if dungeon_info.get("entry_location") == player_location:
            found_dungeon = True
            button = InlineKeyboardButton(f"💀 {dungeon_info['display_name']}", callback_data=f"dungeon_info_{dungeon_id}")
            keyboard.append([button])

    if not found_dungeon:
        text = "Não há eventos especiais na sua localização atual."

    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="continue_after_action")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    try: # Tenta deletar a mensagem anterior
        await query.delete_message()
    except Exception:
        pass # Ignora se não conseguir deletar

    await context.bot.send_message(
        chat_id=query.message.chat_id, text=text,
        reply_markup=reply_markup, parse_mode='HTML'
    )    