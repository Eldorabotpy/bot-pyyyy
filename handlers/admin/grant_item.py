# handlers/admin/grant_item.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    CommandHandler,
)
from modules import player_manager, game_data
from handlers.admin.utils import ensure_admin

# --- Estados da Conversa ---
(SELECT_CATEGORY, BROWSE_ITEMS, ASK_QUANTITY, ASK_TARGET_PLAYER, CONFIRM_GRANT) = range(5)
ITEMS_PER_PAGE = 10

# --- Funções da Conversa ---

async def start_grant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mostra o menu de categorias de itens."""
    if not await ensure_admin(update):
        return ConversationHandler.END
    
    query = update.callback_query
    await query.answer()
    
    # Extrai todas as categorias únicas do ITEMS_DATA
    categories = sorted(list(set(item.get("category", "outros") for item in game_data.ITEMS_DATA.values())))
    
    keyboard = []
    # Cria um botão para cada categoria
    for category in categories:
        keyboard.append([InlineKeyboardButton(category.capitalize(), callback_data=f"grant_cat:{category}:1")])
    
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="grant_cancel")])
    
    text = "🎁 **Biblioteca de Itens**\n\nSelecione uma categoria para começar:"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    
    return SELECT_CATEGORY

async def browse_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mostra uma página de itens de uma categoria específica."""
    query = update.callback_query
    await query.answer()
    
    # Extrai a categoria e a página do callback_data (ex: "grant_cat:coletavel:1")
    _, category, page_str = query.data.split(":")
    page = int(page_str)
    
    # Filtra os itens que pertencem à categoria escolhida
    items_in_category = [
        (item_id, item_data) for item_id, item_data in game_data.ITEMS_DATA.items() 
        if item_data.get("category") == category
    ]
    
    # Lógica de paginação
    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    items_on_page = items_in_category[start_index:end_index]
    
    keyboard = []
    # Cria um botão para cada item na página
    for item_id, item_data in items_on_page:
        emoji = item_data.get("emoji", "▫️")
        display_name = item_data.get("display_name", item_id)
        keyboard.append([InlineKeyboardButton(f"{emoji} {display_name}", callback_data=f"grant_pick:{item_id}")])
        
    # Lógica dos botões de navegação
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"grant_cat:{category}:{page-1}"))
    
    total_pages = (len(items_in_category) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Próximo ➡️", callback_data=f"grant_cat:{category}:{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
        
    keyboard.append([InlineKeyboardButton("↩️ Voltar às Categorias", callback_data="admin_grant_item")])

    text = f"**Categoria: {category.capitalize()}** (Página {page}/{total_pages})\n\nEscolha um item:"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    return BROWSE_ITEMS

async def receive_item_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe o item escolhido e pede a quantidade."""
    query = update.callback_query
    await query.answer()
    
    item_id = query.data.split(":")[1]
    
    context.user_data['grant_item_id'] = item_id
    item_name = game_data.ITEMS_DATA[item_id].get('display_name', item_id)
    
    await query.edit_message_text(f"Item selecionado: `{item_name}`.\n\nAgora, envie a **quantidade**.", parse_mode="Markdown")
    
    return ASK_QUANTITY
        

async def receive_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe a quantidade e pede o jogador alvo."""
    try:
        quantity = int(update.message.text.strip())
        if quantity <= 0:
            raise ValueError("A quantidade deve ser positiva.")
    except ValueError:
        await update.message.reply_text("❌ Quantidade inválida. Por favor, envie um número inteiro e positivo.")
        return ASK_QUANTITY
        
    context.user_data['grant_quantity'] = quantity
    
    await update.message.reply_text(f"Quantidade: {quantity}.\n\nAgora, envie o **User ID** ou o **nome exato do personagem** que vai receber os itens.")
    
    return ASK_TARGET_PLAYER

async def receive_target_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe o jogador, mostra a confirmação e finaliza."""
    target_input = update.message.text.strip()
    
    # Tenta encontrar por ID primeiro
    try:
        user_id = int(target_input)
        pdata = player_manager.get_player_data(user_id)
    except ValueError:
        # Se não for ID, tenta por nome
        found = player_manager.find_player_by_name(target_input)
        if found:
            user_id, pdata = found
        else:
            user_id, pdata = None, None

    if not pdata:
        await update.message.reply_text("❌ Jogador não encontrado. Tente novamente.")
        return ASK_TARGET_PLAYER
    
    # Guarda os dados para a confirmação final
    context.user_data['grant_target_id'] = user_id
    context.user_data['grant_target_name'] = pdata.get('character_name', f"ID: {user_id}")
    
    item_id = context.user_data['grant_item_id']
    quantity = context.user_data['grant_quantity']
    item_name = game_data.ITEMS_DATA[item_id].get('display_name', item_id)
    
    summary_text = (
        f"**Resumo da Entrega:**\n\n"
        f"🔹 **Item:** {item_name} (`{item_id}`)\n"
        f"🔹 **Quantidade:** {quantity}\n"
        f"🔹 **Para:** {context.user_data['grant_target_name']} (`{user_id}`)\n\n"
        f"Você confirma a entrega?"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Sim, entregar", callback_data="grant_confirm_yes"),
            InlineKeyboardButton("❌ Não, cancelar", callback_data="grant_confirm_no")
        ]
    ]
    
    await update.message.reply_text(summary_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    return CONFIRM_GRANT

async def dispatch_grant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Executa a entrega do item após a confirmação."""
    query = update.callback_query
    await query.answer()

    user_id = context.user_data['grant_target_id']
    item_id = context.user_data['grant_item_id']
    quantity = context.user_data['grant_quantity']
    
    pdata = player_manager.get_player_data(user_id)
    
    # Usa a função do player_manager para adicionar o item
    player_manager.add_item_to_inventory(pdata, item_id, quantity)
    player_manager.save_player_data(user_id, pdata)
    
    item_name = game_data.ITEMS_DATA[item_id].get('display_name', item_id)
    target_name = context.user_data['grant_target_name']
    
    await query.edit_message_text(f"✅ Sucesso! {quantity}x '{item_name}' foram entregues a {target_name}.")
    
    # Limpa os dados da conversa
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a conversa a qualquer momento."""
    # Descobre se foi um comando (/cancel) ou um botão (grant_confirm_no)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Operação cancelada.")
    else:
        await update.message.reply_text("Operação cancelada.")
        
    context.user_data.clear()
    return ConversationHandler.END

# --- O Handler da Conversa ---
grant_item_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_grant, pattern=r"^admin_grant_item$")],
    states={
        SELECT_CATEGORY: [CallbackQueryHandler(browse_category, pattern=r"^grant_cat:.*")],
        BROWSE_ITEMS: [
            CallbackQueryHandler(receive_item_id, pattern=r"^grant_pick:.*"),
            CallbackQueryHandler(browse_category, pattern=r"^grant_cat:.*"), # Para navegação
            CallbackQueryHandler(start_grant, pattern=r"^admin_grant_item$"), # Para voltar
        ],
        ASK_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_quantity)],
        ASK_TARGET_PLAYER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_target_player)],
        CONFIRM_GRANT: [
            CallbackQueryHandler(dispatch_grant, pattern=r"^grant_confirm_yes$"),
            CallbackQueryHandler(cancel, pattern=r"^grant_confirm_no$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancelar", cancel),
        CallbackQueryHandler(cancel, pattern=r"^grant_cancel$")
    ],
)