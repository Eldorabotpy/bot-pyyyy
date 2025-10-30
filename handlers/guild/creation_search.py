# handlers/guild/creation_search.py (Versão Refinada)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, ConversationHandler,
    MessageHandler, filters, CommandHandler
)

from modules import player_manager, clan_manager, game_data
from ..guild_handler import ASKING_NAME, ASKING_SEARCH_NAME

# --- Funções de Menu ---

async def show_create_clan_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, came_from: str = 'guild_menu'):
    """Mostra o menu para jogadores sem clã."""
    query = update.callback_query
    
    custo_ouro = game_data.CLAN_CONFIG['creation_cost']['gold']
    custo_dimas = game_data.CLAN_CONFIG['creation_cost']['dimas']

    caption = (
        "Você ainda não faz parte de um clã.\n\n"
        "Criar um novo clã une aventureiros sob um mesmo estandarte, "
        "permitindo o acesso a benefícios e missões exclusivas.\n\n"
        f"<b>Custo para fundar um clã:</b>\n"
        f"- 🪙 {custo_ouro:,} Ouro\n"
        f"- 💎 {custo_dimas} Diamantes"
    )

    keyboard = [
        [InlineKeyboardButton("🔎 Procurar Clã", callback_data='clan_search_start')],
        [InlineKeyboardButton(f"🪙 Fundar com Ouro", callback_data='clan_create_start:gold')],
        [InlineKeyboardButton(f"💎 Fundar com Diamantes", callback_data='clan_create_start:dimas')],
        [InlineKeyboardButton("⬅️ Voltar", callback_data='show_kingdom_menu')],
    ]
    
    await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# --- Lógica de Criação de Clã (Conversation) ---

async def start_clan_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia a conversa para criar um clã."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    # <<< CORREÇÃO 1: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)
    payment_method = query.data.split(':')[1]
    cost = game_data.CLAN_CONFIG["creation_cost"][payment_method]
    
    currency = "gold" if payment_method == "gold" else "dimas"
    if player_data.get(currency, 0) < cost:
        await context.bot.answer_callback_query(query.id, f"Você não tem recursos suficientes.", show_alert=True)
        return ConversationHandler.END

    context.user_data['clan_payment_method'] = payment_method
    await query.edit_message_caption(caption="Excelente! Por favor, envie o nome que deseja para o seu clã. (Use /cancelar para desistir)")
    return ASKING_NAME

async def receive_clan_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe o nome do clã e finaliza a criação."""
    user_id = update.effective_user.id
    clan_name = update.message.text
    
    if not 3 <= len(clan_name) <= 20:
        await update.message.reply_text("Nome inválido. Por favor, escolha um nome entre 3 e 20 caracteres.")
        return ASKING_NAME
        
    payment_method = context.user_data.get('clan_payment_method')
    
    try:
        # <<< CORREÇÃO 2: Adiciona await >>>
        clan_id = await clan_manager.create_clan(leader_id=user_id, clan_name=clan_name, payment_method=payment_method)
        
        # <<< CORREÇÃO 3: Adiciona await >>>
        player_data = await player_manager.get_player_data(user_id)
        player_data["clan_id"] = clan_id
        
        # <<< CORREÇÃO 4: Adiciona await >>>
        await player_manager.save_player_data(user_id, player_data)
        await update.message.reply_text(f"Parabéns! O clã '{clan_name}' foi fundado com sucesso!")
    except ValueError as e:
        await update.message.reply_text(f"Erro: {e}")

    context.user_data.pop('clan_payment_method', None)
    return ConversationHandler.END

async def cancel_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela o processo de criação de clã."""
    context.user_data.pop('clan_payment_method', None)
    await update.message.reply_text("Criação de clã cancelada.")
    return ConversationHandler.END

# --- Lógica de Busca e Aplicação (Conversation) ---

async def start_clan_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia a conversa para procurar um clã."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_caption(caption="Qual o nome do clã que você procura? (Use /cancelar para desistir)")
    return ASKING_SEARCH_NAME

async def receive_clan_search_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe o nome do clã para busca e mostra o resultado."""
    clan_name_searched = update.message.text
    
    # <<< CORREÇÃO 5: Adiciona await >>>
    clan_data = await clan_manager.find_clan_by_display_name(clan_name_searched)
    
    if not clan_data:
        await update.message.reply_text(f"Nenhum clã com o nome '{clan_name_searched}' foi encontrado. Tente de novo.")
        return ASKING_SEARCH_NAME

    clan_id = clan_data.get("id")
    clan_name = clan_data.get("display_name")
    
    # <<< CORREÇÃO 6: Adiciona await >>>
    leader_data = await player_manager.get_player_data(clan_data.get("leader_id"))
    leader_name = leader_data.get("character_name", "Desconhecido") if leader_data else "Desconhecido"
    
    member_count = len(clan_data.get("members", []))
    
    caption = (
        f"<b>Clã Encontrado:</b> {clan_name}\n"
        f"<b>Líder:</b> {leader_name}\n"
        f"<b>Membros:</b> {member_count}\n\n"
        f"Deseja enviar um pedido para se juntar?"
    )
    keyboard = [[
        InlineKeyboardButton("✅ Sim, enviar pedido", callback_data=f'clan_apply:{clan_id}'),
        InlineKeyboardButton("⬅️ Voltar", callback_data='guild_menu'),
    ]]
    await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    return ConversationHandler.END

async def apply_to_clan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa o pedido de um jogador para entrar num clã."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    clan_id_to_join = query.data.split(':')[1]
    
    try:
        # <<< CORREÇÃO 7: Adiciona await >>>
        await clan_manager.add_application(clan_id_to_join, user_id)
        await query.edit_message_text("Seu pedido foi enviado com sucesso!")
    except ValueError as e:
        await context.bot.answer_callback_query(query.id, f"Erro: {e}", show_alert=True)

async def show_applications_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o menu para o líder aceitar ou recusar candidaturas."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    # <<< CORREÇÃO 8: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")
    
    # <<< CORREÇÃO 9: Adiciona await >>>
    clan_data = await clan_manager.get_clan(clan_id)

    if not clan_data or clan_data.get("leader_id") != user_id:
        return

    applications = clan_data.get("pending_applications", [])
    caption = "<b>📩 Candidaturas Pendentes</b>\n\n"
    keyboard = []

    if not applications:
        caption += "Não há nenhuma candidatura pendente no momento."
    else:
        for applicant_id in applications:
            # <<< CORREÇÃO 10: Adiciona await >>>
            applicant_data = await player_manager.get_player_data(applicant_id)
            applicant_name = applicant_data.get("character_name", f"ID: {applicant_id}")
            
            keyboard.append([
                InlineKeyboardButton(f"{applicant_name}", callback_data="noop"),
                InlineKeyboardButton("✅ Aceitar", callback_data=f'clan_app_accept:{applicant_id}'),
                InlineKeyboardButton("❌ Recusar", callback_data=f'clan_app_decline:{applicant_id}'),
            ])

    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data='clan_menu')])
    await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def accept_application_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa a aceitação de um novo membro."""
    query = update.callback_query
    leader_id = update.effective_user.id
    
    # <<< CORREÇÃO 11: Adiciona await >>>
    player_data = await player_manager.get_player_data(leader_id)
    clan_id = player_data.get("clan_id")
    applicant_id = int(query.data.split(':')[1])

    try:
        # <<< CORREÇÃO 12: Adiciona await >>>
        await clan_manager.accept_application(clan_id, applicant_id)
        
        # <<< CORREÇÃO 13: Adiciona await >>>
        applicant_data = await player_manager.get_player_data(applicant_id)
        applicant_data["clan_id"] = clan_id
        
        # <<< CORREÇÃO 14: Adiciona await >>>
        await player_manager.save_player_data(applicant_id, applicant_data)

        # <<< CORREÇÃO 15: Adiciona await >>>
        clan_name = (await clan_manager.get_clan(clan_id)).get("display_name")
        await context.bot.send_message(chat_id=applicant_id, text=f"🎉 Parabéns! A sua candidatura ao clã '{clan_name}' foi aceite!")
        
        await query.answer("Candidatura aceite com sucesso!")

    except ValueError as e:
        await context.bot.answer_callback_query(query.id, f"Erro: {e}", show_alert=True)
    
    await show_applications_menu(update, context)

async def decline_application_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa a recusa de um candidato."""
    query = update.callback_query
    leader_id = update.effective_user.id
    
    # <<< CORREÇÃO 16: Adiciona await >>>
    player_data = await player_manager.get_player_data(leader_id)
    clan_id = player_data.get("clan_id")
    applicant_id = int(query.data.split(':')[1])

    # <<< CORREÇÃO 17: Adiciona await >>>
    await clan_manager.decline_application(clan_id, applicant_id)
    
    # <<< CORREÇÃO 18: Adiciona await >>>
    clan_name = (await clan_manager.get_clan(clan_id)).get("display_name")
    await context.bot.send_message(chat_id=applicant_id, text=f"A sua candidatura ao clã '{clan_name}' foi recusada.")

    await query.answer("Candidatura recusada.")

    await show_applications_menu(update, context)

# --- Definição dos Handlers ---
clan_creation_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_clan_creation, pattern=r'^clan_create_start:(gold|dimas)$')],
    states={ASKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_clan_name)]},
    fallbacks=[CommandHandler('cancelar', cancel_creation)],
    map_to_parent={ConversationHandler.END: ConversationHandler.END}
)

clan_search_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_clan_search, pattern=r'^clan_search_start$')],
    states={ASKING_SEARCH_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_clan_search_name)]},
    fallbacks=[CommandHandler('cancelar', cancel_creation)],
)

clan_apply_handler = CallbackQueryHandler(apply_to_clan_callback, pattern=r'^clan_apply:[a-z0-9_]+$')
clan_manage_apps_handler = CallbackQueryHandler(show_applications_menu, pattern=r'^clan_manage_apps$')
clan_app_accept_handler = CallbackQueryHandler(accept_application_callback, pattern=r'^clan_app_accept:\d+$')
clan_app_decline_handler = CallbackQueryHandler(decline_application_callback, pattern=r'^clan_app_decline:\d+$')