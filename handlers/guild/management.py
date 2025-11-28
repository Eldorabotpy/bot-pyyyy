# handlers/guild/management.py
# (VERSÃO FINAL: COM BOTÃO DE DELETAR CLÃ)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, ConversationHandler,
    MessageHandler, filters, CommandHandler
)

from modules import player_manager, clan_manager

# --- Definição Local dos Estados ---
ASKING_INVITEE = 0
ASKING_LEADER_TARGET = 1
CONFIRM_LEADER_TRANSFER = 2
ASKING_CLAN_LOGO = 3

# --- Helper de Limpeza ---
async def _clean_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    last_id = context.user_data.get('last_bot_msg_id')
    if last_id:
        try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_id)
        except: pass
        context.user_data.pop('last_bot_msg_id', None)

# --- MENU PRINCIPAL DE GESTÃO ---

async def show_clan_management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    
    clan_data = await clan_manager.get_clan(clan_id)
    if not clan_data or clan_data.get("leader_id") != user_id:
        await query.answer("Apenas o Líder tem acesso.", show_alert=True)
        return

    text = (
        "👑 <b>GESTÃO DO CLÃ</b>\n"
        "Configure seu clã e gerencie seus membros aqui.\n"
    )

    keyboard = [
        [InlineKeyboardButton("🖼️ Alterar Logo", callback_data='clan_logo_start')],
        [InlineKeyboardButton("✉️ Convidar Jogador", callback_data='clan_invite_start')],
        [InlineKeyboardButton("👟 Expulsar Membro", callback_data='clan_kick_menu')],
        [InlineKeyboardButton("👑 Transferir Liderança", callback_data='clan_transfer_leader_start')],
        # --- BOTÃO DE DELETAR (NOVO) ---
        [InlineKeyboardButton("⚠️ Dissolver Clã", callback_data='clan_delete_warn')],
        # -------------------------------
        [InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data='clan_menu')]
    ]
    
    try:
        await query.edit_message_caption(caption=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    except:
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# --- DELETAR CLÃ (DISSOLUÇÃO) ---

async def warn_delete_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tela de aviso antes de deletar."""
    query = update.callback_query
    await query.answer()
    
    text = (
        "⚠️ <b>PERIGO: DISSOLVER CLÃ</b> ⚠️\n\n"
        "Você está prestes a apagar seu clã permanentemente.\n\n"
        "❌ O Nível e XP do clã serão perdidos.\n"
        "❌ Todo o Ouro no banco sumirá.\n"
        "❌ Todos os membros ficarão sem clã.\n\n"
        "<b>Esta ação não pode ser desfeita.</b> Tem certeza?"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Sim, Apagar Tudo", callback_data='clan_delete_confirm')],
        [InlineKeyboardButton("❌ CANCELAR", callback_data='clan_manage_menu')]
    ]
    
    try:
        await query.edit_message_caption(caption=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    except:
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def do_delete_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Executa a exclusão."""
    query = update.callback_query
    user_id = query.from_user.id
    
    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    
    try:
        # Chama a função do manager
        await clan_manager.delete_clan(clan_id, user_id)
        
        # Atualiza o líder localmente (agora sem clã)
        pdata["clan_id"] = None
        await player_manager.save_player_data(user_id, pdata)
        
        await query.answer("Clã dissolvido com sucesso!", show_alert=True)
        
        # Manda para o menu da Guilda de Aventureiros (NPC)
        from handlers.guild_menu_handler import adventurer_guild_menu
        await adventurer_guild_menu(update, context)
        
    except ValueError as e:
        await query.answer(f"Erro: {e}", show_alert=True)
        await show_clan_management_menu(update, context)


# --- CONVITES ---

async def start_invite_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    msg_text = "✉️ <b>Convidar</b>\nEnvie o <b>Nome do Personagem</b> exato:\n(Ou /cancelar)"
    
    try:
        msg = await query.edit_message_text(text=msg_text, parse_mode="HTML")
        context.user_data['last_bot_msg_id'] = msg.message_id
    except:
        await query.delete_message()
        msg = await context.bot.send_message(chat_id=query.message.chat.id, text=msg_text, parse_mode="HTML")
        context.user_data['last_bot_msg_id'] = msg.message_id
        
    return ASKING_INVITEE

async def receive_invitee_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    inviter_id = update.effective_user.id
    target_name = update.message.text.strip()
    
    await _clean_chat(update, context) 

    target_info = await player_manager.find_player_by_character_name(target_name)
    
    if not target_info:
        msg = await update.message.reply_text("❌ Personagem não encontrado.")
        context.user_data['last_bot_msg_id'] = msg.message_id
        return ASKING_INVITEE

    # Proteção de tipo (dict ou tuple)
    if isinstance(target_info, dict):
        target_id = target_info.get('user_id') or target_info.get('_id')
    elif isinstance(target_info, tuple):
        target_id = target_info[0]
    else:
        target_id = target_info

    if not target_id:
        msg = await update.message.reply_text("❌ Erro ao identificar jogador.")
        return ASKING_INVITEE

    # Envia convite
    pdata = await player_manager.get_player_data(inviter_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)
    clan_name = clan.get("display_name", "Clã")
    
    invite_text = f"📜 Você foi convidado para o clã <b>{clan_name}</b>!"
    kb = [
        [InlineKeyboardButton("✅ Aceitar", callback_data=f"clan_invite_accept:{clan_id}")],
        [InlineKeyboardButton("❌ Recusar", callback_data=f"clan_invite_decline:{target_id}")]
    ]
    try:
        await context.bot.send_message(chat_id=target_id, text=invite_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        
        kb_back = [[InlineKeyboardButton("⬅️ Voltar", callback_data="clan_manage_menu")]]
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f"✅ Convite enviado para <b>{target_name}</b>!", 
            reply_markup=InlineKeyboardMarkup(kb_back), 
            parse_mode="HTML"
        )
    except:
        await update.message.reply_text("❌ Erro ao enviar convite (usuário bloqueou o bot?).")

    return ConversationHandler.END

# --- EXPULSÃO (KICK) ---

async def show_kick_member_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    pdata = await player_manager.get_player_data(user_id)
    clan = await clan_manager.get_clan(pdata.get("clan_id"))
    
    text = "👟 <b>EXPULSAR MEMBRO</b>\nSelecione:"
    keyboard = []
    for mid in clan.get("members", [])[:10]:
        if mid == user_id: continue
        mdata = await player_manager.get_player_data(mid)
        name = mdata.get("character_name", str(mid))
        keyboard.append([InlineKeyboardButton(f"❌ {name}", callback_data=f"clan_kick_confirm:{mid}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="clan_manage_menu")])
    
    try:
        await query.edit_message_caption(caption=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    except:
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def show_kick_confirm_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    target_id = int(query.data.split(":")[1])
    
    mdata = await player_manager.get_player_data(target_id)
    name = mdata.get("character_name", "Membro")
    
    text = f"⚠️ Tem certeza que deseja expulsar <b>{name}</b>?"
    kb = [
        [InlineKeyboardButton("Sim, expulsar", callback_data=f"clan_kick_do:{target_id}")],
        [InlineKeyboardButton("Cancelar", callback_data="clan_kick_menu")]
    ]
    try:
        await query.edit_message_caption(caption=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    except:
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

async def do_kick_member_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    target_id = int(query.data.split(":")[1])
    user_id = query.from_user.id
    
    pdata = await player_manager.get_player_data(user_id)
    await clan_manager.remove_member(pdata.get("clan_id"), target_id)
    
    kicked = await player_manager.get_player_data(target_id)
    kicked["clan_id"] = None
    await player_manager.save_player_data(target_id, kicked)
    
    await query.answer("Membro expulso.")
    await show_kick_member_menu(update, context)

async def cancel_op(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _clean_chat(update, context)
    kb = [[InlineKeyboardButton("⬅️ Voltar", callback_data="clan_manage_menu")]]
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Cancelado.", reply_markup=InlineKeyboardMarkup(kb))
    return ConversationHandler.END

# --- HANDLERS ---
clan_manage_menu_handler = CallbackQueryHandler(show_clan_management_menu, pattern=r'^clan_manage_menu$')
clan_kick_menu_handler = CallbackQueryHandler(show_kick_member_menu, pattern=r'^clan_kick_menu$')
clan_kick_confirm_handler = CallbackQueryHandler(show_kick_confirm_menu, pattern=r'^clan_kick_confirm:')
clan_kick_do_handler = CallbackQueryHandler(do_kick_member_callback, pattern=r'^clan_kick_do:')

# Handlers de Deleção
clan_delete_warn_handler = CallbackQueryHandler(warn_delete_clan, pattern=r'^clan_delete_warn$')
clan_delete_do_handler = CallbackQueryHandler(do_delete_clan, pattern=r'^clan_delete_confirm$')

# Placeholders
clan_transfer_leader_conv_handler = CallbackQueryHandler(lambda u,c: u.callback_query.answer("Em breve"), pattern='^clan_transfer_leader')
clan_logo_conv_handler = CallbackQueryHandler(lambda u,c: u.callback_query.answer("Em breve"), pattern='^clan_logo')

invite_conv_handler = ConversationHandler(
     entry_points=[CallbackQueryHandler(start_invite_conversation, pattern=r'^clan_invite_start$')],
     states={ ASKING_INVITEE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_invitee_name)] },
     fallbacks=[CommandHandler('cancelar', cancel_op)],
)