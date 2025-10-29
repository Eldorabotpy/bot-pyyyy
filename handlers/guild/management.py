# handlers/guild/management.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, ConversationHandler,
    MessageHandler, filters, CommandHandler
)

from modules import player_manager, clan_manager
from handlers.guild_handler import (
    ASKING_LEADER_TARGET, CONFIRM_LEADER_TRANSFER,
    ASKING_CLAN_LOGO, ASKING_INVITEE
)

from ..utils import safe_edit_message

# --- Menu Principal de Gestão ---

async def show_clan_management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o menu de gestão para o líder do clã."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # <<< CORREÇÃO 1: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")
    
    # <<< CORREÇÃO 2: Adiciona await >>>
    clan_data = await clan_manager.get_clan(clan_id)

    if not clan_data or clan_data.get("leader_id") != user_id:
        await query.answer("Apenas o líder do clã pode aceder a este menu.", show_alert=True)
        return
        
    await query.answer()
    caption = "👑 <b>Painel de Gestão do Clã</b> 👑\n\nSelecione uma opção:"
    keyboard = [
        [InlineKeyboardButton("🖼️ Alterar Logo", callback_data='clan_logo_start')],
        [InlineKeyboardButton("👟 Expulsar Membro", callback_data='clan_kick_menu')],
        [InlineKeyboardButton("👑 Transferir Liderança", callback_data='clan_transfer_leader_start')],
        [InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data='clan_menu')]
    ]
    await safe_edit_message(query, text=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def start_invite_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia a conversa para convidar um novo membro."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_caption(
        caption="Por favor, envie o `@username` do jogador que você deseja convidar. (Use /cancelar para desistir)"
    )
    return ASKING_INVITEE

# --- Lógica de Expulsar Membro ---

async def show_kick_member_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a lista de membros para expulsar."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # <<< CORREÇÃO 3: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")
    
    # <<< CORREÇÃO 4: Adiciona await >>>
    clan_data = await clan_manager.get_clan(clan_id)

    if not clan_data or clan_data.get("leader_id") != user_id:
        await query.answer("Apenas o líder pode expulsar membros.", show_alert=True)
        return
        
    await query.answer()
    caption = "👟 <b>Expulsar Membro</b>\n\nSelecione o membro para remover:"
    keyboard = []
    
    for member_id in clan_data.get("members", []):
        if member_id != user_id:
            # <<< CORREÇÃO 5: Adiciona await >>>
            member_data = await player_manager.get_player_data(member_id)
            if member_data: 
                member_name = member_data.get("character_name", f"ID: {member_id}")
                keyboard.append([InlineKeyboardButton(f"❌ {member_name}", callback_data=f'clan_kick_confirm:{member_id}')])

    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data='clan_manage_menu')])
    await safe_edit_message(query, text=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def show_kick_confirm_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pede a confirmação final antes de expulsar."""
    query = update.callback_query
    await query.answer()
    member_id_to_kick = int(query.data.split(':')[1])
    
    # <<< CORREÇÃO 6: Adiciona await >>>
    member_data = await player_manager.get_player_data(member_id_to_kick)
    
    if not member_data:
        await query.answer("Este jogador não foi encontrado.", show_alert=True)
        return

    member_name = member_data.get("character_name", "este membro")
    caption = f"Tem a certeza que deseja expulsar <b>{member_name}</b> do clã? Esta ação é irreversível."
    keyboard = [
        [
            InlineKeyboardButton("✅ Sim, expulsar", callback_data=f'clan_kick_do:{member_id_to_kick}'),
            InlineKeyboardButton("❌ Não", callback_data='clan_kick_menu')
        ]
    ]
    await safe_edit_message(query, text=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')


async def do_kick_member_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Executa a expulsão do membro."""
    query = update.callback_query
    leader_id = update.effective_user.id
    
    # <<< CORREÇÃO 7: Adiciona await >>>
    player_data = await player_manager.get_player_data(leader_id)
    clan_id = player_data.get("clan_id")
    member_id_to_kick = int(query.data.split(':')[1])
    
    try:
        # <<< CORREÇÃO 8: Adiciona await >>>
        kicked_player_data = await player_manager.get_player_data(member_id_to_kick)
        if not kicked_player_data:
            raise ValueError("Jogador a ser expulso não encontrado.")

        member_name = kicked_player_data.get("character_name", "O jogador")
        
        # <<< CORREÇÃO 9: Adiciona await >>>
        await clan_manager.remove_member(clan_id, member_id_to_kick)

        kicked_player_data["clan_id"] = None
        
        # <<< CORREÇÃO 10: Adiciona await >>>
        await player_manager.save_player_data(member_id_to_kick, kicked_player_data)
        
        await query.answer(f"{member_name} foi expulso do clã.", show_alert=True)
        
        # <<< CORREÇÃO 11: Adiciona await >>>
        clan_name = (await clan_manager.get_clan(clan_id)).get("display_name")
        try:
            await context.bot.send_message(chat_id=member_id_to_kick, text=f"Você foi expulso do clã '{clan_name}' pelo líder.")
        except Exception as e:
            print(f"Não foi possível notificar o jogador expulso {member_id_to_kick}. Erro: {e}")
            
    except ValueError as e:
        await query.answer(f"Erro: {e}", show_alert=True)
    
    # <<< CORREÇÃO 12: Adiciona await (chamada a função async) >>>
    await show_kick_member_menu(update, context)

# --- Lógica de Transferência de Liderança (Conversation) ---

async def start_transfer_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = update.effective_user.id
    
    # <<< CORREÇÃO 13: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")
    
    # <<< CORREÇÃO 14: Adiciona await >>>
    clan_data = await clan_manager.get_clan(clan_id)

    if not clan_data or clan_data.get("leader_id") != user_id:
        await query.answer("Apenas o líder pode transferir a liderança.", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    await safe_edit_message(query, text="👑 Para quem deseja transferir a liderança? Envie o nome exato do personagem. (Use /cancelar)")
    return ASKING_LEADER_TARGET

async def receive_transfer_target_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    leader_id = update.effective_user.id
    target_name = update.message.text
    
    # <<< CORREÇÃO 15: Adiciona await >>>
    target_info = await player_manager.find_player_by_character_name(target_name)
    
    if not target_info:
        await update.message.reply_text(f"Nenhum personagem com o nome '{target_name}' foi encontrado. Tente novamente.")
        return ASKING_LEADER_TARGET

    target_id = target_info['user_id']
    
    # <<< CORREÇÃO 16: Adiciona await >>>
    player_data_leader = await player_manager.get_player_data(leader_id)
    clan_id = player_data_leader.get("clan_id")
    
    # <<< CORREÇÃO 17: Adiciona await >>>
    clan_data = await clan_manager.get_clan(clan_id)

    if target_id not in clan_data.get("members", []):
        await update.message.reply_text(f"'{target_name}' não é membro do seu clã.")
        return ASKING_LEADER_TARGET
    if target_id == leader_id:
        await update.message.reply_text("Você não pode transferir a liderança para si mesmo.")
        return ASKING_LEADER_TARGET

    context.user_data['transfer_target_id'] = target_id
    caption = (
        f"Você tem certeza que quer transferir a liderança para <b>{target_name}</b>?\n\n"
        "⚠️ <b>ESTA AÇÃO É IRREVERSÍVEL!</b> ⚠️"
    )
    keyboard = [[
        InlineKeyboardButton("✅ Sim, transferir", callback_data="clan_transfer_do"),
        InlineKeyboardButton("❌ Não, cancelar", callback_data="clan_manage_menu")
    ]]
    await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    return CONFIRM_LEADER_TRANSFER

async def do_transfer_leadership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    leader_id = update.effective_user.id
    
    # <<< CORREÇÃO 18: Adiciona await >>>
    player_data_leader = await player_manager.get_player_data(leader_id)
    clan_id = player_data_leader.get("clan_id")
    target_id = context.user_data.get('transfer_target_id')

    try:
        # <<< CORREÇÃO 19: Adiciona await >>>
        await clan_manager.transfer_leadership(clan_id, leader_id, target_id)
        
        # <<< CORREÇÃO 20: Adiciona await >>>
        clan_name = (await clan_manager.get_clan(clan_id)).get("display_name")
        
        # <<< CORREÇÃO 21: Adiciona await >>>
        target_name = (await player_manager.get_player_data(target_id)).get("character_name")
        
        await query.edit_message_text(f"A liderança do clã '{clan_name}' foi transferida para {target_name}.")
        try:
            await context.bot.send_message(chat_id=target_id, text=f"👑 Você é o novo líder do clã '{clan_name}'!")
        except Exception: pass
    except ValueError as e:
        await context.bot.answer_callback_query(query.id, f"Erro: {e}", show_alert=True)
    
    context.user_data.pop('transfer_target_id', None)
    return ConversationHandler.END

async def cancel_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop('transfer_target_id', None)
    await update.message.reply_text("Transferência de liderança cancelada.")
    return ConversationHandler.END


# --- Lógica de Alterar Logo (Conversation) ---

async def start_logo_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = update.effective_user.id
    
    # <<< CORREÇÃO 22: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")
    
    # <<< CORREÇÃO 23: Adiciona await >>>
    clan_data = await clan_manager.get_clan(clan_id)

    if not clan_data or clan_data.get("leader_id") != user_id:
        await query.answer("Apenas o líder pode alterar a logo.", show_alert=True)
        return ConversationHandler.END
        
    await query.answer()
    await safe_edit_message(query, text="🖼️ Envie a foto ou o vídeo para a logo. (Use /cancelar)")
    return ASKING_CLAN_LOGO


async def receive_clan_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    
    # <<< CORREÇÃO 24: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")
    
    media_data = {}
    if update.message.photo:
        media_data["file_id"] = update.message.photo[-1].file_id
        media_data["type"] = "photo"
    elif update.message.video:
        media_data["file_id"] = update.message.video.file_id
        media_data["type"] = "video"
    else:
        await update.message.reply_text("Arquivo inválido. Por favor, envie uma foto ou um vídeo.")
        return ASKING_CLAN_LOGO

    try:
        # <<< CORREÇÃO 25: Adiciona await >>>
        await clan_manager.set_clan_media(clan_id, user_id, media_data)
        await update.message.reply_text("✅ Logo do clã atualizada com sucesso!")
    except ValueError as e:
        await update.message.reply_text(f"❌ Erro: {e}")

    return ConversationHandler.END

async def cancel_logo_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Upload da logo cancelado.")
    return ConversationHandler.END

async def receive_invitee_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Recebe o nome do personagem a ser convidado, valida e envia o convite.
    """
    inviter_id = update.effective_user.id
    target_name = update.message.text

    # <<< CORREÇÃO 26: Adiciona await >>>
    target_info = await player_manager.find_player_by_character_name(target_name)

    if not target_info:
        await update.message.reply_text(f"Nenhum personagem com o nome '{target_name}' foi encontrado. Tente novamente.")
        return ASKING_INVITEE

    target_id = target_info['user_id']
    
    # <<< CORREÇÃO 27: Adiciona await >>>
    target_data = await player_manager.get_player_data(target_id)

    if target_data.get("clan_id"):
        await update.message.reply_text(f"'{target_name}' já faz parte de um clã.")
        return ConversationHandler.END

    if target_id == inviter_id:
        await update.message.reply_text("Você não pode convidar a si mesmo.")
        return ASKING_INVITEE

    # <<< CORREÇÃO 28: Adiciona await >>>
    inviter_data = await player_manager.get_player_data(inviter_id)
    clan_id = inviter_data.get("clan_id")
    
    # <<< CORREÇÃO 29: Adiciona await >>>
    clan_name = (await clan_manager.get_clan(clan_id)).get("display_name", "um clã")
    inviter_name = inviter_data.get("character_name", "um líder")

    invite_text = (
        f"📩 Você recebeu um convite de <b>{inviter_name}</b> para se juntar ao clã <b>{clan_name}</b>!\n\n"
        "Deseja aceitar?"
    )
    keyboard = [[
        InlineKeyboardButton("✅ Aceitar", callback_data=f"clan_invite_accept:{clan_id}"),
        InlineKeyboardButton("❌ Recusar", callback_data=f"clan_invite_decline:{target_id}")
    ]]
    
    try:
        await context.bot.send_message(
            chat_id=target_id, 
            text=invite_text, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        await update.message.reply_text(f"✅ Convite enviado com sucesso para {target_name}!")
    except Exception as e:
        await update.message.reply_text(f"❌ Não foi possível enviar o convite. O jogador pode ter bloqueado o bot. Erro: {e}")

    return ConversationHandler.END


async def cancel_invite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancela o processo de convite.
    """
    await update.message.reply_text("Processo de convite cancelado.")
    # Opcional: Voltar para o menu de gestão
    # await show_clan_management_menu(update, context) 
    return ConversationHandler.END

# --- Definição dos Handlers ---

clan_manage_menu_handler = CallbackQueryHandler(show_clan_management_menu, pattern=r'^clan_manage_menu$')

clan_kick_menu_handler = CallbackQueryHandler(show_kick_member_menu, pattern=r'^clan_kick_menu$')
clan_kick_confirm_handler = CallbackQueryHandler(show_kick_confirm_menu, pattern=r'^clan_kick_confirm:\d+$')
clan_kick_do_handler = CallbackQueryHandler(do_kick_member_callback, pattern=r'^clan_kick_do:\d+$')

# O seu ConversationHandler para transferência está ótimo
# Apenas certifique-se que o resto das funções (receive_transfer_target_name, etc.) estejam definidas
clan_transfer_leader_conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(start_transfer_conversation, pattern=r'^clan_transfer_leader_start$')
    ],
    states={
        # Passo 1: Esperando o nome do personagem
        ASKING_LEADER_TARGET: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_transfer_target_name)
        ],
        # Passo 2: Esperando a confirmação do botão "Sim" ou "Não"
        CONFIRM_LEADER_TRANSFER: [
            CallbackQueryHandler(do_transfer_leadership, pattern=r'^clan_transfer_do$'),
            # Se o usuário clicar em "Não", volta para o menu de gestão
            CallbackQueryHandler(show_clan_management_menu, pattern=r'^clan_manage_menu$')
        ],
    },
    fallbacks=[
        # Se o usuário digitar /cancelar em qualquer passo
        CommandHandler('cancelar', cancel_transfer)
    ],
    # Garante que, ao terminar, o controle volte para os handlers principais do bot
    per_user=True,
    per_chat=True,
    map_to_parent={
        ConversationHandler.END: ConversationHandler.END
    }
)

clan_logo_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_logo_upload, pattern=r'^clan_logo_start$')],
    states={
        # ✅ 4. CORREÇÃO DO FILTRO DE MÍDIA
        ASKING_CLAN_LOGO: [MessageHandler((filters.PHOTO | filters.VIDEO) & ~filters.COMMAND, receive_clan_media)],
    },
    fallbacks=[CommandHandler('cancelar', cancel_logo_upload)],
)

# ✅ 5. HANDLER PARA A FUNÇÃO DE CONVITE (Exemplo, se quiser usá-la)
invite_conv_handler = ConversationHandler(
     entry_points=[CallbackQueryHandler(start_invite_conversation, pattern=r'^clan_invite_start$')],
     states={ ASKING_INVITEE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_invitee_name)] },
     fallbacks=[CommandHandler('cancelar', cancel_invite)],
 )