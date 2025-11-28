# handlers/guild/creation_search.py
# (VERSÃO CORRIGIDA: FUNÇÕES DE ACEITAR/RECUSAR RESTAURADAS)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, ConversationHandler,
    MessageHandler, filters, CommandHandler
)

from modules import player_manager, clan_manager, game_data, file_ids

# --- Definição de Estados ---
ASKING_NAME, ASKING_SEARCH_NAME = range(2)

# --- Helper de Limpeza ---
async def _clean_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Apaga a mensagem do usuário e a última mensagem do bot salva no contexto."""
    try: await update.message.delete()
    except: pass
    last_msg_id = context.user_data.get('last_bot_msg_id')
    if last_msg_id:
        try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_msg_id)
        except: pass
        context.user_data.pop('last_bot_msg_id', None)

# ==============================================================================
# FUNÇÕES DE VISUALIZAÇÃO (MENU)
# ==============================================================================

async def show_create_clan_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, came_from: str = 'guild_menu'):
    query = update.callback_query
    creation_cost = getattr(game_data, "CLAN_CONFIG", {}).get('creation_cost', {'gold': 10000, 'dimas': 100})
    custo_ouro = creation_cost.get('gold', 10000)
    custo_dimas = creation_cost.get('dimas', 100)

    text = (
        "🛡️ <b>SEM CLÃ? SEM PROBLEMA!</b>\n\n"
        "Você ainda não faz parte de um estandarte. Juntar-se a um clã oferece:\n"
        "• 🏦 Banco Compartilhado\n"
        "• 🏰 Buffs de XP e Drop\n"
        "• ⚔️ Raids Exclusivas\n\n"
        f"<b>Custo para fundar um clã:</b>\n"
        f"- 🪙 {custo_ouro:,} Ouro\n"
        f"- 💎 {custo_dimas} Diamantes"
    )

    keyboard = [
        [InlineKeyboardButton("🔍 Procurar Clã Existente", callback_data='clan_search_start')],
        [InlineKeyboardButton(f"🪙 Fundar (Ouro)", callback_data='clan_create_start:gold')],
        [InlineKeyboardButton(f"💎 Fundar (Diamantes)", callback_data='clan_create_start:dimas')],
        [InlineKeyboardButton("🔙 Voltar à Guilda", callback_data='adventurer_guild_main')],
    ]
    
    if query:
        try:
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        except:
            try: await query.delete_message() 
            except: pass
            await context.bot.send_message(chat_id=query.message.chat.id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ==============================================================================
# FLUXO: CRIAÇÃO DE CLÃ
# ==============================================================================

async def start_clan_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    try: payment_method = query.data.split(':')[1]
    except: payment_method = 'gold'
    context.user_data['clan_payment_method'] = payment_method

    msg_text = (
        "✍️ <b>Fundação de Clã</b>\n\n"
        "Digite o <b>NOME</b> do seu novo clã no chat:\n"
        "<i>(3 a 20 letras. Sem caracteres especiais)</i>\n\n"
        "Digite /cancelar para desistir."
    )
    
    try:
        msg = await query.edit_message_text(text=msg_text, parse_mode="HTML")
        context.user_data['last_bot_msg_id'] = msg.message_id
    except:
        await query.delete_message()
        msg = await context.bot.send_message(chat_id=query.message.chat.id, text=msg_text, parse_mode="HTML")
        context.user_data['last_bot_msg_id'] = msg.message_id
        
    return ASKING_NAME

async def receive_clan_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    clan_name = update.message.text.strip()
    await _clean_chat(update, context)

    if not 3 <= len(clan_name) <= 20:
        msg = await update.message.reply_text("❌ Nome inválido (3-20 letras). Tente novamente.")
        context.user_data['last_bot_msg_id'] = msg.message_id
        return ASKING_NAME
        
    payment_method = context.user_data.get('clan_payment_method', 'gold')
    
    try:
        clan_id = await clan_manager.create_clan(leader_id=user_id, clan_name=clan_name, payment_method=payment_method)
        
        # Atualiza jogador
        pdata = await player_manager.get_player_data(user_id)
        pdata["clan_id"] = clan_id
        await player_manager.save_player_data(user_id, pdata)
        
        # Botões de Sucesso
        kb = [
            [InlineKeyboardButton("🛡️ Acessar Meu Clã", callback_data="clan_menu")],
            [InlineKeyboardButton("🔙 Voltar à Guilda", callback_data="adventurer_guild_main")]
        ]
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🎉 <b>Parabéns!</b>\nO clã <b>'{clan_name}'</b> foi fundado com sucesso!",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="HTML"
        )
        
    except ValueError as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ Erro: {e}")
    except Exception:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Erro interno.")

    return ConversationHandler.END

async def cancel_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _clean_chat(update, context)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Cancelado.")
    return ConversationHandler.END

# ==============================================================================
# FLUXO: BUSCA DE CLÃ
# ==============================================================================

async def start_clan_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    msg = "🔍 <b>Busca de Clã</b>\n\nDigite o nome do clã que procura:\n(Ou /cancelar)"
    try:
        msg = await query.edit_message_text(text=msg, parse_mode="HTML")
        context.user_data['last_bot_msg_id'] = msg.message_id
    except:
        await query.delete_message()
        msg = await context.bot.send_message(chat_id=query.message.chat.id, text=msg, parse_mode="HTML")
        context.user_data['last_bot_msg_id'] = msg.message_id
        
    return ASKING_SEARCH_NAME

async def receive_clan_search_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    search = update.message.text.strip()
    await _clean_chat(update, context)
    
    clan_data = await clan_manager.find_clan_by_display_name(search)
    
    if not clan_data:
        msg = await update.message.reply_text(f"❌ Clã '{search}' não encontrado.")
        context.user_data['last_bot_msg_id'] = msg.message_id
        return ASKING_SEARCH_NAME

    clan_id = clan_data.get("_id")
    clan_name = clan_data.get("display_name")
    count = len(clan_data.get("members", []))
    
    caption = f"🛡️ <b>Clã Encontrado:</b> {clan_name}\n👥 <b>Membros:</b> {count}\n\nDeseja enviar pedido?"
    kb = [[
        InlineKeyboardButton("✅ Enviar Pedido", callback_data=f'clan_apply:{clan_id}'),
        InlineKeyboardButton("⬅️ Cancelar", callback_data='adventurer_guild_main'),
    ]]
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    return ConversationHandler.END

async def apply_to_clan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    try:
        clan_id = query.data.split(':')[1]
        await clan_manager.add_application(clan_id, user_id)
        await query.edit_message_text("✅ Pedido enviado ao líder!")
    except ValueError as e:
        await context.bot.answer_callback_query(query.id, str(e), show_alert=True)
    except Exception:
        await query.edit_message_text("❌ Erro ao enviar pedido.")

# ==============================================================================
# GESTÃO DE CANDIDATURAS (LÍDER) - RESTAURADO!
# ==============================================================================

async def show_applications_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a lista de jogadores que querem entrar no clã."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    if not clan_id: return
    
    clan_data = await clan_manager.get_clan(clan_id)
    if not clan_data or clan_data.get("leader_id") != user_id:
        await query.answer("Apenas o líder vê isso.", show_alert=True)
        return

    apps = clan_data.get("pending_applications", [])
    text = "<b>📩 Candidaturas Pendentes</b>\n\n"
    kb = []

    if not apps:
        text += "Nenhuma candidatura pendente."
    else:
        for applicant_id in apps:
            adata = await player_manager.get_player_data(applicant_id)
            aname = adata.get("character_name", f"ID: {applicant_id}") if adata else f"ID: {applicant_id}"
            
            kb.append([
                InlineKeyboardButton(f"👤 {aname}", callback_data="noop"),
                InlineKeyboardButton("✅ Aceitar", callback_data=f'clan_app_accept:{applicant_id}'),
                InlineKeyboardButton("❌ Recusar", callback_data=f'clan_app_decline:{applicant_id}'),
            ])

    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data='clan_manage_menu')])
    
    try:
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    except:
        await query.delete_message()
        await context.bot.send_message(chat_id=query.message.chat.id, text=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def accept_application_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aceita um jogador no clã."""
    query = update.callback_query
    leader_id = update.effective_user.id
    
    pdata = await player_manager.get_player_data(leader_id)
    clan_id = pdata.get("clan_id")
    try: applicant_id = int(query.data.split(':')[1])
    except: return

    try:
        await clan_manager.accept_application(clan_id, applicant_id)
        
        # Atualiza o novato
        app_data = await player_manager.get_player_data(applicant_id)
        if app_data:
            app_data["clan_id"] = clan_id
            await player_manager.save_player_data(applicant_id, app_data)
            
            # Notifica
            cdata = await clan_manager.get_clan(clan_id)
            try: await context.bot.send_message(chat_id=applicant_id, text=f"🎉 Você entrou no clã <b>{cdata.get('display_name')}</b>!", parse_mode="HTML")
            except: pass
        
        await query.answer("Membro aceito!")
    except ValueError as e:
        await context.bot.answer_callback_query(query.id, str(e), show_alert=True)
    
    await show_applications_menu(update, context)

async def decline_application_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recusa um jogador."""
    query = update.callback_query
    leader_id = update.effective_user.id
    pdata = await player_manager.get_player_data(leader_id)
    clan_id = pdata.get("clan_id")
    try: applicant_id = int(query.data.split(':')[1])
    except: return

    await clan_manager.decline_application(clan_id, applicant_id)
    await query.answer("Recusado.")
    
    # Notifica (Opcional)
    try: await context.bot.send_message(chat_id=applicant_id, text="Sua candidatura ao clã foi recusada.")
    except: pass

    await show_applications_menu(update, context)

# ==============================================================================
# HANDLERS EXPORTADOS
# ==============================================================================

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

clan_apply_handler = CallbackQueryHandler(apply_to_clan_callback, pattern=r'^clan_apply:')
clan_manage_apps_handler = CallbackQueryHandler(show_applications_menu, pattern=r'^clan_manage_apps$')
clan_app_accept_handler = CallbackQueryHandler(accept_application_callback, pattern=r'^clan_app_accept:')
clan_app_decline_handler = CallbackQueryHandler(decline_application_callback, pattern=r'^clan_app_decline:')