# handlers/guild/creation_search.py
# (VERSÃO ZERO LEGADO: CLÃS + AUTH SEGURA + STRING IDs)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, ConversationHandler,
    MessageHandler, filters, CommandHandler
)

from modules import player_manager, clan_manager, game_data
from modules.auth_utils import get_current_player_id

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
    # 🔒 SEGURANÇA: Checagem rápida de sessão
    if not get_current_player_id(update, context):
        if query: await query.answer("Sessão inválida.", show_alert=True)
        return

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
    q = u.callback_query
    
    if not get_current_player_id(u, c):
        await q.answer("Erro de sessão.")
        return ConversationHandler.END

    await q.answer()
    pay = q.data.split(':')[1] if ':' in q.data else 'gold'
    c.user_data['clan_payment_method'] = pay
    
    msg = await c.bot.send_message(q.message.chat.id, "✍️ Digite o <b>NOME</b> do novo clã (3-20 caracteres):", parse_mode="HTML")
    c.user_data['last_bot_msg_id'] = msg.message_id
    
    try: await q.delete_message()
    except: pass
    return ASKING_NAME

async def receive_clan_name(u, c):
    # 🔒 SEGURANÇA: Identificação via Auth Central
    uid = get_current_player_id(u, c)
    if not uid:
        return ConversationHandler.END

    name = u.message.text.strip()
    await _clean_chat(u, c)
    
    if not 3 <= len(name) <= 20: 
        m = await u.message.reply_text("❌ Nome inválido (3-20 letras).")
        c.user_data['last_bot_msg_id'] = m.message_id
        return ASKING_NAME
        
    pay = c.user_data.get('clan_payment_method', 'gold')
    try:
        # clan_manager.create_clan deve suportar String ID
        cid = await clan_manager.create_clan(uid, name, pay)
        
        # Atualiza player
        pdata = await player_manager.get_player_data(uid)
        pdata["clan_id"] = cid
        await player_manager.save_player_data(uid, pdata)
        
        await c.bot.send_message(
            u.effective_chat.id, 
            f"🎉 Clã <b>{name}</b> criado com sucesso!", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛡️ Acessar Clã", callback_data="clan_menu")]]), 
            parse_mode="HTML"
        )
    except Exception as e: 
        await c.bot.send_message(u.effective_chat.id, f"❌ Falha ao criar clã: {e}")
        
    return ConversationHandler.END

async def cancel_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _clean_chat(update, context)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Operação cancelada.")
    return ConversationHandler.END

# ==============================================================================
# FLUXO: BUSCA DE CLÃ
# ==============================================================================

async def start_clan_search(u, c):
    q = u.callback_query
    if not get_current_player_id(u, c):
        await q.answer("Sessão inválida.")
        return ConversationHandler.END
        
    await q.answer()
    msg = await c.bot.send_message(q.message.chat.id, "🔍 Digite o nome (ou parte do nome) do clã:", parse_mode="HTML")
    c.user_data['last_bot_msg_id'] = msg.message_id
    try: await q.delete_message()
    except: pass
    return ASKING_SEARCH_NAME

async def receive_clan_search_name(u, c):
    search = u.message.text.strip()
    await _clean_chat(u, c)
    
    clan = await clan_manager.find_clan_by_display_name(search)
    if not clan: 
        m = await u.message.reply_text("❌ Clã não encontrado. Tente outro nome:")
        c.user_data['last_bot_msg_id'] = m.message_id
        return ASKING_SEARCH_NAME
        
    clan_id_str = str(clan.get('_id'))
    kb = [
        [InlineKeyboardButton("✅ Enviar Pedido", callback_data=f"clan_apply:{clan_id_str}")],
        [InlineKeyboardButton("⬅️ Cancelar", callback_data='clan_create_menu_start')]
    ]
    
    await c.bot.send_message(
        u.effective_chat.id, 
        f"🛡️ <b>{clan.get('display_name', 'Clã')}</b>\n👥 Membros: {len(clan.get('members', []))}\n🏆 Nível: {clan.get('level', 1)}", 
        reply_markup=InlineKeyboardMarkup(kb), 
        parse_mode="HTML"
    )
    return ConversationHandler.END

async def apply_to_clan_callback(u, c):
    q = u.callback_query
    
    uid = get_current_player_id(u, c)
    if not uid:
        await q.answer("Erro de sessão.", show_alert=True)
        return

    await q.answer()
    
    try:
        target_clan_id = q.data.split(':')[1]
        await clan_manager.add_application(target_clan_id, uid)
        await q.edit_message_text("✅ Pedido enviado! Aguarde aprovação do líder.")
    except Exception as e:
        await q.edit_message_text(f"❌ Não foi possível enviar pedido: {e}")

# ==============================================================================
# GESTÃO DE CANDIDATURAS (LÍDER)
# ==============================================================================

async def show_applications_menu(u, c):
    q = u.callback_query
    
    uid = get_current_player_id(u, c)
    if not uid:
        await q.answer("Sessão inválida.", show_alert=True)
        return

    await q.answer()
    
    p = await player_manager.get_player_data(uid)
    c_id = p.get("clan_id")
    if not c_id:
        await q.edit_message_text("Você não tem clã.")
        return

    clan = await clan_manager.get_clan(c_id)
    if not clan: 
        return
        
    apps = clan.get("pending_applications", [])
    
    if not apps:
        await q.edit_message_text("<b>📩 Nenhuma candidatura pendente.</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="clan_manage_menu")]]), parse_mode="HTML")
        return

    kb = []
    for aid in apps:
        # aid pode ser String/ObjectId
        ap = await player_manager.get_player_data(aid)
        aname = ap.get("character_name", f"Jogador") if ap else "Desconhecido"
        
        # Callback carrega o ID do candidato como string
        kb.append([
            InlineKeyboardButton(aname, callback_data="noop"), 
            InlineKeyboardButton("✅", callback_data=f"clan_app_accept:{aid}"), 
            InlineKeyboardButton("❌", callback_data=f"clan_app_decline:{aid}")
        ])
        
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="clan_manage_menu")])
    
    msg_txt = "<b>📩 Candidaturas Pendentes</b>"
    try: await q.edit_message_text(msg_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    except: await c.bot.send_message(q.message.chat.id, msg_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def accept_application_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aceita um jogador no clã."""
    query = update.callback_query
    
    leader_id = get_current_player_id(update, context)
    if not leader_id:
        await query.answer("Sessão inválida.", show_alert=True)
        return
    
    pdata = await player_manager.get_player_data(leader_id)
    clan_id = pdata.get("clan_id")
    if not clan_id: return

    try:
        # ID do candidato vem como String na callback
        applicant_id = query.data.split(':')[1]
        
        # Executa lógica de aceitar (clan_manager deve suportar str)
        await clan_manager.accept_application(clan_id, applicant_id)
        
        # Atualiza o novato (vincula ao clã)
        app_data = await player_manager.get_player_data(applicant_id)
        if app_data:
            app_data["clan_id"] = clan_id
            await player_manager.save_player_data(applicant_id, app_data)
            
            # Notifica o usuário (precisa do chat_id real)
            cdata = await clan_manager.get_clan(clan_id)
            target_chat = app_data.get("last_chat_id") or app_data.get("telegram_id_owner")
            
            if target_chat:
                try: 
                    await context.bot.send_message(
                        chat_id=target_chat, 
                        text=f"🎉 <b>Parabéns!</b> Você foi aceito no clã <b>{cdata.get('display_name', 'Clã')}</b>!", 
                        parse_mode="HTML"
                    )
                except: pass
        
        await query.answer("Membro aceito com sucesso!")
        
    except Exception as e:
        await query.answer(f"Erro: {e}", show_alert=True)
    
    await show_applications_menu(update, context)

async def decline_application_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recusa um jogador."""
    query = update.callback_query
    
    leader_id = get_current_player_id(update, context)
    if not leader_id: return

    pdata = await player_manager.get_player_data(leader_id)
    clan_id = pdata.get("clan_id")
    
    try:
        applicant_id = query.data.split(':')[1]
        await clan_manager.decline_application(clan_id, applicant_id)
        
        # Notifica recusa (opcional)
        app_data = await player_manager.get_player_data(applicant_id)
        if app_data:
            target_chat = app_data.get("last_chat_id") or app_data.get("telegram_id_owner")
            if target_chat:
                try: 
                    await context.bot.send_message(
                        chat_id=target_chat, 
                        text=f"❌ Sua candidatura para o clã foi recusada."
                    )
                except: pass

        await query.answer("Candidatura recusada.")
        
    except Exception:
        pass

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