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

async def show_create_clan_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    # Busca custos no config
    creation_cost = getattr(game_data, "CLAN_CONFIG", {}).get('creation_cost', {'gold': 10000, 'dimas': 100})
    custo_ouro = creation_cost.get('gold', 10000)
    custo_dimas = creation_cost.get('dimas', 100)

    text = (
        "🛡️ <b>SEM CLÃ? SEM PROBLEMA!</b>\n\n"
        "Você ainda não faz parte de um estandarte. Juntar-se a um clã oferece:\n"
        "• 🏦 Banco Compartilhado\n"
        "• 🏰 Buffs de XP e Drop\n"
        "• ⚔️ Missões e Defesa do Reino\n\n"
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
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        try:
            await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='HTML')
        except:
            try: await query.delete_message() 
            except: pass
            await context.bot.send_message(chat_id=query.message.chat.id, text=text, reply_markup=reply_markup, parse_mode='HTML')

# ==============================================================================
# FLUXO: CRIAÇÃO DE CLÃ
# ==============================================================================

async def start_clan_creation(u, c):
    q = u.callback_query; await q.answer()
    pay = q.data.split(':')[1] if ':' in q.data else 'gold'
    c.user_data['clan_payment_method'] = pay
    msg = await c.bot.send_message(q.message.chat.id, "✍️ Digite o <b>NOME</b> do novo clã:", parse_mode="HTML")
    c.user_data['last_bot_msg_id'] = msg.message_id
    try: await q.delete_message()
    except: pass
    return ASKING_NAME

async def receive_clan_name(u, c):
    uid = u.effective_user.id; name = u.message.text.strip(); await _clean_chat(u, c)
    if not 3 <= len(name) <= 20: 
        m = await u.message.reply_text("❌ Nome inválido (3-20 letras)."); c.user_data['last_bot_msg_id'] = m.message_id; return ASKING_NAME
    pay = c.user_data.get('clan_payment_method', 'gold')
    try:
        cid = await clan_manager.create_clan(uid, name, pay)
        pdata = await player_manager.get_player_data(uid); pdata["clan_id"] = cid; await player_manager.save_player_data(uid, pdata)
        await c.bot.send_message(u.effective_chat.id, f"🎉 Clã <b>{name}</b> criado!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛡️ Acessar", callback_data="clan_menu")]]), parse_mode="HTML")
    except Exception as e: await c.bot.send_message(u.effective_chat.id, f"❌ Erro: {e}")
    return ConversationHandler.END

async def cancel_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _clean_chat(update, context)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Cancelado.")
    return ConversationHandler.END

# ==============================================================================
# FLUXO: BUSCA DE CLÃ
# ==============================================================================

async def start_clan_search(u, c):
    q = u.callback_query; await q.answer()
    msg = await c.bot.send_message(q.message.chat.id, "🔍 Digite o nome do clã:", parse_mode="HTML")
    c.user_data['last_bot_msg_id'] = msg.message_id
    try: await q.delete_message()
    except: pass
    return ASKING_SEARCH_NAME

async def receive_clan_search_name(u, c):
    search = u.message.text.strip(); await _clean_chat(u, c)
    clan = await clan_manager.find_clan_by_display_name(search)
    if not clan: m = await u.message.reply_text("❌ Não encontrado."); c.user_data['last_bot_msg_id'] = m.message_id; return ASKING_SEARCH_NAME
    kb = [[InlineKeyboardButton("✅ Enviar Pedido", callback_data=f"clan_apply:{clan['_id']}"), InlineKeyboardButton("⬅️ Cancelar", callback_data='clan_create_menu_start')]]
    await c.bot.send_message(u.effective_chat.id, f"🛡️ <b>{clan['display_name']}</b>\n👥 Membros: {len(clan['members'])}", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    return ConversationHandler.END

async def cancel_creation(u, c):
    await _clean_chat(u, c); await u.message.reply_text("Cancelado.")
    return ConversationHandler.END

async def apply_to_clan_callback(u, c):
    q = u.callback_query; await q.answer()
    try: await clan_manager.add_application(q.data.split(':')[1], u.effective_user.id); await q.edit_message_text("✅ Pedido enviado!")
    except Exception as e: await q.edit_message_text(f"❌ {e}")

# ==============================================================================
# GESTÃO DE CANDIDATURAS (LÍDER) - RESTAURADO!
# ==============================================================================

async def show_applications_menu(u, c):
    q = u.callback_query; await q.answer(); uid = u.effective_user.id
    p = await player_manager.get_player_data(uid); c_id = p.get("clan_id")
    clan = await clan_manager.get_clan(c_id)
    if not clan: return
    apps = clan.get("pending_applications", [])
    kb = []
    for aid in apps:
        ap = await player_manager.get_player_data(aid)
        aname = ap.get("character_name", f"ID {aid}") if ap else f"ID {aid}"
        kb.append([InlineKeyboardButton(aname, callback_data="noop"), InlineKeyboardButton("✅", callback_data=f"clan_app_accept:{aid}"), InlineKeyboardButton("❌", callback_data=f"clan_app_decline:{aid}")])
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="clan_manage_menu")])
    try: await q.edit_message_text("<b>📩 Candidaturas</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    except: await c.bot.send_message(q.message.chat.id, "<b>📩 Candidaturas</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

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

clan_create_menu_handler = CallbackQueryHandler(show_create_clan_menu, pattern=r'^clan_create_menu_start$')

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