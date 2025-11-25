# handlers/menu/events.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from modules import player_manager
from modules.dungeon_definitions import DUNGEONS

async def show_events_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Mostra o menu de eventos (HUB).
    Lista tanto a Defesa do Reino quanto as Dungeons (Catacumbas).
    """
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    player_data = await player_manager.get_player_data(user_id)
    
    # Normaliza a localização (alguns salvam como 'reino_eldora', outros 'cidade_inicial')
    # Se quiser que apareça em qualquer lugar do reino, verifique só se não é nulo.
    player_location = player_data.get("current_location", "reino_eldora")

    text = "💀 <b>HUB DE EVENTOS ESPECIAIS</b> 💀\n\nEscolha seu desafio:"
    keyboard = []
    
    # ==================================================================
    # 1. BOTÃO DA DEFESA DO REINO (ADICIONADO MANUALMENTE)
    # ==================================================================
    # Verifica se o jogador está no reino (ajuste 'reino_eldora' conforme seu DB)
    if player_location == 'reino_eldora':
        keyboard.append([
            InlineKeyboardButton("🛡️ Defesa do Reino (Ondas)", callback_data="defesa_reino_main")
        ])
    else:
        # Se quiser que o botão apareça sempre, mesmo fora da cidade (opcional):
        # keyboard.append([InlineKeyboardButton("🛡️ Defesa do Reino", callback_data="defesa_reino_main")])
        pass

    # ==================================================================
    # 2. BOTÕES DAS DUNGEONS (CATACUMBAS, ETC)
    # ==================================================================
    event_found = False
    for dungeon_id, dungeon_info in DUNGEONS.items():
        # Verifica se a dungeon pertence ao local atual do jogador
        if dungeon_info.get("entry_location") == player_location:
            event_found = True
            display_name = dungeon_info.get('display_name', 'Masmorra')
            keyboard.append([
                InlineKeyboardButton(f"💀 {display_name}", callback_data=f"dungeon_info_{dungeon_id}")
            ])

    # ==================================================================
    # 3. NAVEGAÇÃO
    # ==================================================================
    
    if not keyboard:
        text += "\n\n🚫 <i>Nenhum evento disponível nesta localização.</i>"

    # Define para onde o botão "Voltar" leva
    back_callback = "back_to_kingdom" if player_location == 'reino_eldora' else "continue_after_action"
    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data=back_callback)])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Tenta apagar mensagem anterior para limpar a tela ou edita se for possível
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode='HTML')
    except Exception:
        # Se falhar (ex: mensagem anterior era só texto e agora tentou editar caption), envia nova
        try:
            await query.delete_message()
        except: 
            pass
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )