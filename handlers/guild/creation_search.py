# handlers/guild/creation_search.py
# (VERSÃO CORRIGIDA: UI RENDERER + VISUAL DE RECRUTAMENTO)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, ConversationHandler,
    MessageHandler, filters, CommandHandler
)

from modules import player_manager, clan_manager, game_data, file_ids
from modules.auth_utils import get_current_player_id
from ui.ui_renderer import render_photo_or_text

# --- Definição de Estados ---
ASKING_NAME, ASKING_SEARCH_NAME = range(2)

# ==============================================================================
# HELPERS VISUAIS
# ==============================================================================

def _pick_creation_media():
    """
    Tenta selecionar uma imagem de 'Recrutamento' ou 'Guilda'.
    """
    try:
        # Tenta imagem específica de recrutamento/entrada
        fid = file_ids.get_file_id("img_clan_recruit")
        if fid: return fid
    except: pass

    # Fallback
    try:
        return file_ids.get_file_id("img_clan_default")
    except:
        return None

async def _render_creation_screen(update, context, text, keyboard):
    """Renderiza a tela de criação/busca."""
    media_id = _pick_creation_media()
    
    await render_photo_or_text(
        update,
        context,
        text=text,
        photo_file_id=media_id,
        reply_markup=InlineKeyboardMarkup(keyboard),
        scope="clan_create_screen", 
        parse_mode="HTML",
        allow_edit=True
    )

async def _clean_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    last_msg_id = context.user_data.get('last_bot_msg_id')
    if last_msg_id:
        try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_msg_id)
        except: pass
        context.user_data.pop('last_bot_msg_id', None)


# ==============================================================================
# FUNÇÕES DE VISUALIZAÇÃO (MENU INICIAL)
# ==============================================================================

async def show_create_clan_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()

    # 🔒 SEGURANÇA
    if not get_current_player_id(update, context):
        return

    # Busca custos no config
    creation_cost = getattr(game_data, "CLAN_CONFIG", {}).get('creation_cost', {'gold': 10000, 'dimas': 100})
    custo_ouro = creation_cost.get('gold', 10000)
    custo_dimas = creation_cost.get('dimas', 100)

    text = (
        "🛡️ <b>GUILDA DE AVENTUREIROS</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Você ainda não luta sob nenhum estandarte.\n"
        "Junte-se a um clã para desbloquear:\n\n"
        "🏦 <b>Banco Compartilhado</b>\n"
        "🏰 <b>Bônus de XP e Drop</b>\n"
        "⚔️ <b>Guerra de Territórios</b>\n\n"
        f"<b>Para fundar sua própria ordem:</b>\n"
        f"🪙 {custo_ouro:,} Ouro  |  💎 {custo_dimas} Diamantes"
    )

    keyboard = [
        [InlineKeyboardButton("🔍 Procurar Clã Existente", callback_data='clan_search_start')],
        [InlineKeyboardButton(f"🪙 Fundar (Ouro)", callback_data='clan_create_start:gold')],
        [InlineKeyboardButton(f"💎 Fundar (Dimas)", callback_data='clan_create_start:dimas')],
        [InlineKeyboardButton("🔙 Voltar ao Reino", callback_data='show_kingdom_menu')],
    ]
    
    await _render_creation_screen(update, context, text, keyboard)


# ==============================================================================
# FLUXO: CRIAÇÃO DE CLÃ
# ==============================================================================

async def start_clan_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not get_current_player_id(update, context):
        return ConversationHandler.END

    pay = query.data.split(':')[1] if ':' in query.data else 'gold'
    context.user_data['clan_payment_method'] = pay
    
    # Limpa tela anterior
    try: await query.delete_message()
    except: pass
    
    msg = await context.bot.send_message(
        query.message.chat.id, 
        "✍️ <b>NOVA ORDEM</b>\n\nDigite o <b>NOME</b> do seu novo clã (3-20 caracteres):", 
        parse_mode="HTML"
    )
    context.user_data['last_bot_msg_id'] = msg.message_id
    
    return ASKING_NAME

async def receive_clan_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_current_player_id(update, context)
    if not user_id: return ConversationHandler.END

    name = update.message.text.strip()
    await _clean_chat(update, context)
    
    if not 3 <= len(name) <= 20: 
        m = await update.message.reply_text("❌ Nome inválido (use 3 a 20 letras). Tente novamente:")
        context.user_data['last_bot_msg_id'] = m.message_id
        return ASKING_NAME
        
    pay = context.user_data.get('clan_payment_method', 'gold')
    
    try:
        # Cria o clã
        cid = await clan_manager.create_clan(user_id, name, pay)
        
        # Atualiza o player imediatamente para evitar delay
        pdata = await player_manager.get_player_data(user_id)
        pdata["clan_id"] = cid
        await player_manager.save_player_data(user_id, pdata)
        
        # Sucesso!
        await context.bot.send_message(
            update.effective_chat.id, 
            f"🎉 <b>A ordem nasceu!</b>\nO clã <b>{name}</b> foi fundado com sucesso.", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛡️ Acessar Clã", callback_data="clan_menu")]]), 
            parse_mode="HTML"
        )
    except Exception as e: 
        await context.bot.send_message(update.effective_chat.id, f"❌ Falha ao criar clã: {e}")
        
    return ConversationHandler.END

async def cancel_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _clean_chat(update, context)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Operação cancelada.")
    return ConversationHandler.END


# ==============================================================================
# FLUXO: BUSCA DE CLÃ
# ==============================================================================

async def start_clan_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not get_current_player_id(update, context):
        return ConversationHandler.END
        
    try: await query.delete_message()
    except: pass
    
    msg = await context.bot.send_message(
        query.message.chat.id, 
        "🔍 <b>PROCURAR CLÃ</b>\n\nDigite o nome (ou parte do nome) do clã que deseja encontrar:", 
        parse_mode="HTML"
    )
    context.user_data['last_bot_msg_id'] = msg.message_id
    return ASKING_SEARCH_NAME

async def receive_clan_search_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    search = update.message.text.strip()
    await _clean_chat(update, context)
    
    clan = await clan_manager.find_clan_by_display_name(search)
    
    if not clan: 
        m = await update.message.reply_text("❌ Clã não encontrado. Tente outro nome:")
        context.user_data['last_bot_msg_id'] = m.message_id
        return ASKING_SEARCH_NAME
        
    clan_id_str = str(clan.get('_id'))
    members_count = len(clan.get('members', []))
    
    # Monta visualização do resultado
    text = (
        f"🛡️ <b>{clan.get('display_name', 'Clã')}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 Nível: {clan.get('prestige_level', 1)}\n"
        f"👥 Membros: {members_count}\n\n"
        f"<i>Deseja enviar um pedido de entrada?</i>"
    )
    
    kb = [
        [InlineKeyboardButton("✅ Enviar Pedido", callback_data=f"clan_apply:{clan_id_str}")],
        [InlineKeyboardButton("⬅️ Cancelar", callback_data='clan_create_menu_start')]
    ]
    
    # Se o clã tiver logo, tenta mostrar. Senão, mostra texto.
    # Como estamos num ConversationHandler e a msg anterior foi deletada, usamos send_photo/msg
    media_fid = clan.get("logo_media_key")
    
    if media_fid:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=media_fid,
            caption=text,
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="HTML"
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="HTML"
        )

    return ConversationHandler.END

async def apply_to_clan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    user_id = get_current_player_id(update, context)
    if not user_id: return

    await query.answer()
    
    try:
        target_clan_id = query.data.split(':')[1]
        await clan_manager.add_application(target_clan_id, user_id)
        
        # Feedback visual sem apagar a mensagem, apenas editando o botão ou texto
        await query.edit_message_caption(
            caption="✅ <b>Pedido enviado!</b>\n\nO líder do clã receberá sua notificação. Aguarde a aprovação.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data='clan_create_menu_start')]])
        )
    except Exception as e:
        await query.edit_message_caption(f"❌ Não foi possível enviar pedido: {e}")


# ==============================================================================
# GESTÃO DE CANDIDATURAS (Visão do Líder)
# ==============================================================================

async def show_applications_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    user_id = get_current_player_id(update, context)
    if not user_id: return

    p = await player_manager.get_player_data(user_id)
    c_id = p.get("clan_id")
    if not c_id: return

    clan = await clan_manager.get_clan(c_id)
    if not clan: return
        
    apps = clan.get("pending_applications", [])
    
    if not apps:
        await render_photo_or_text(
            update, context, 
            "<b>📩 Nenhuma candidatura pendente no momento.</b>", 
            InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="clan_manage_menu")]]),
            scope="clan_apps_screen"
        )
        return

    kb = []
    for aid in apps:
        # aid pode ser String/ObjectId
        ap = await player_manager.get_player_data(str(aid))
        aname = ap.get("character_name", f"Jogador") if ap else "Desconhecido"
        lvl = ap.get("level", 1) if ap else 0
        
        kb.append([
            InlineKeyboardButton(f"{aname} (Nv.{lvl})", callback_data="noop"), 
            InlineKeyboardButton("✅", callback_data=f"clan_app_accept:{aid}"), 
            InlineKeyboardButton("❌", callback_data=f"clan_app_decline:{aid}")
        ])
        
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="clan_manage_menu")])
    
    msg_txt = f"<b>📩 CANDIDATURAS ({len(apps)})</b>\n\nAceite ou recuse os pedidos de entrada:"
    
    await render_photo_or_text(
        update, context, 
        msg_txt, 
        InlineKeyboardMarkup(kb),
        scope="clan_apps_screen"
    )

async def accept_application_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aceita um jogador no clã."""
    query = update.callback_query
    
    leader_id = get_current_player_id(update, context)
    if not leader_id: return
    
    pdata = await player_manager.get_player_data(leader_id)
    clan_id = pdata.get("clan_id")
    if not clan_id: return

    try:
        applicant_id = query.data.split(':')[1]
        
        # Lógica de Aceite
        await clan_manager.accept_application(clan_id, applicant_id)
        
        # Atualiza dados do novato
        app_data = await player_manager.get_player_data(applicant_id)
        if app_data:
            app_data["clan_id"] = clan_id
            await player_manager.save_player_data(applicant_id, app_data)
            
            # Notifica o usuário
            cdata = await clan_manager.get_clan(clan_id)
            target_chat = app_data.get("last_chat_id") or app_data.get("telegram_id_owner")
            
            if target_chat:
                try: 
                    await context.bot.send_message(
                        chat_id=target_chat, 
                        text=f"🎉 <b>Parabéns!</b>\nVocê foi aceito no clã <b>{cdata.get('display_name', 'Clã')}</b>!", 
                        parse_mode="HTML"
                    )
                except: pass
        
        await query.answer("Membro aceito!")
        
    except Exception as e:
        await query.answer(f"Erro: {e}", show_alert=True)
    
    # Recarrega a lista
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
