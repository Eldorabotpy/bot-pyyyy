# handlers/guild/management.py
# (VERSÃO FINAL LIMPA E BLINDADA)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, ConversationHandler,
    MessageHandler, filters, CommandHandler
)

from bson import ObjectId
from modules import player_manager, clan_manager
from modules.database import db
from modules import file_ids
from handlers.guild.dashboard import _render_clan_screen

logger = logging.getLogger(__name__)

ASKING_INVITEE = 0
ASKING_LOGO = 1

# --- HELPER DE LIMPEZA ---
async def _clean_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    last_id = context.user_data.get('last_bot_msg_id')
    if last_id:
        try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_id)
        except: pass
        context.user_data.pop('last_bot_msg_id', None)

# --- FUNÇÃO DE CANCELAR (Global para este arquivo) ---
async def cancel_op(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a operação atual e retorna ao menu."""
    await _clean_chat(update, context)
    kb = [[InlineKeyboardButton("⬅️ Voltar", callback_data='clan_manage_menu')]]
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="❌ Operação cancelada.", 
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return ConversationHandler.END

# ==============================================================================
# 1. MENU DE GESTÃO (BLINDADO: APAGA E ENVIA NOVO)
# ==============================================================================
async def show_clan_management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # 1. Tenta parar o loading do botão
    try: await query.answer()
    except: pass
    
    # NOTA: Removemos o 'delete_message' para usar a transição suave
    
    user_id = query.from_user.id
    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    
    # 2. Busca dados do Clã
    clan_data = None
    try:
        result = clan_manager.get_clan(clan_id)
        if hasattr(result, '__await__'): clan_data = await result
        else: clan_data = result
    except Exception as e:
        logger.error(f"Erro leitura clã: {e}")

    if not clan_data:
        # Fallback apenas se não achar o clã
        await context.bot.send_message(chat_id=query.message.chat.id, text="⚠️ Erro: Clã não encontrado.")
        return

    # 3. MONTA TEXTO E BOTÕES
    leader_id_raw = clan_data.get("leader_id", 0)
    is_leader = (int(leader_id_raw) == user_id)
    pending = clan_data.get("pending_applications", [])
    
    keyboard = []
    keyboard.append([InlineKeyboardButton("📜 Ver Lista de Membros", callback_data='clan_view_members')])

    if is_leader:
        # Adicionei o nome do clã no título para ficar mais bonito
        text = f"👑 <b>GESTÃO DO CLÃ: {clan_data.get('display_name')}</b>\nConfigure seu clã e gerencie membros."
        
        if pending:
            keyboard.append([InlineKeyboardButton(f"📝 Ver Pedidos ({len(pending)})", callback_data='clan_manage_apps')])
        
        keyboard.append([InlineKeyboardButton("✉️ Convidar Jogador", callback_data='clan_invite_start')])
        keyboard.append([InlineKeyboardButton("👟 Expulsar Membro", callback_data='clan_kick_menu')])
        keyboard.append([InlineKeyboardButton("🖼️ Alterar Logo", callback_data='clan_logo_start')])
        keyboard.append([InlineKeyboardButton("👑 Transferir Liderança", callback_data='clan_transfer_leader_start')])
        keyboard.append([InlineKeyboardButton("⚠️ Dissolver Clã", callback_data='clan_delete_warn')])
    else:
        text = "👤 <b>ÁREA DO MEMBRO</b>\n\nDeseja sair do clã?"
        keyboard.append([InlineKeyboardButton("🚪 Sair do Clã", callback_data='clan_leave_ask')])

    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data='clan_menu')])

    # 4. ENVIO IMERSIVO (Substitui o bloco antigo de delete/send)
    # Essa função detecta a mídia atual e edita suavemente
    await _render_clan_screen(update, context, clan_data, text, keyboard)

# ==============================================================================
# 2. LISTA DE MEMBROS
# ==============================================================================
async def show_members_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    clan_data = await clan_manager.get_clan(clan_id)

    members_ids = clan_data.get("members", [])
    leader_id = int(clan_data.get("leader_id", 0))
    
    text = f"👥 <b>Membros de {clan_data.get('display_name')}</b>\n"
    text += f"Total: {len(members_ids)}/{clan_data.get('max_members', 10)}\n\n"
    
    for mid in members_ids:
        mdata = await player_manager.get_player_data(mid)
        if mdata:
            name = mdata.get("character_name", "Desconhecido")
            lvl = mdata.get("level", 1)
            role = "👑 Líder" if mid == leader_id else "👤 Membro"
            text += f"• <b>{name}</b> (Nv. {lvl}) - {role}\n"

    kb = [[InlineKeyboardButton("⬅️ Voltar", callback_data='clan_menu')]]
    
    # USA O RENDERIZADOR COM A MÍDIA (Isso mantém a imersão!)
    await _render_clan_screen(update, context, clan_data, text, kb)

# ==============================================================================
# 3. AÇÕES (Sair, Expulsar, Logo)
# ==============================================================================

async def warn_leave_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "⚠️ <b>Tem certeza que deseja sair do clã?</b>\n\nVocê perderá os bônus e o acesso ao banco."
    kb = [[InlineKeyboardButton("✅ Sim, Sair", callback_data='clan_leave_perform'), InlineKeyboardButton("❌ Cancelar", callback_data='clan_manage_menu')]]
    try: await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    except: 
        await query.delete_message()
        await context.bot.send_message(query.message.chat.id, text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

async def do_leave_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    pdata = await player_manager.get_player_data(user_id)
    try:
        # Tenta remover (Sync ou Async)
        if hasattr(clan_manager.remove_member, '__await__') or callable(clan_manager.remove_member):
             try: clan_manager.remove_member(pdata.get("clan_id"), user_id)
             except: await clan_manager.remove_member(pdata.get("clan_id"), user_id)
        
        pdata["clan_id"] = None
        await player_manager.save_player_data(user_id, pdata)
        
        await query.answer("Você saiu do clã.", show_alert=True)
        # Retorna para menu da guilda
        from handlers.guild_menu_handler import adventurer_guild_menu
        await adventurer_guild_menu(update, context)
    except Exception as e:
        logger.error(f"Erro ao sair: {e}")
        await query.answer("Erro ao sair.", show_alert=True)
        await show_clan_management_menu(update, context)

async def show_kick_member_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    pdata = await player_manager.get_player_data(user_id)
    try:
        res = clan_manager.get_clan(pdata.get("clan_id"))
        clan_data = await res if hasattr(res, '__await__') else res
    except: clan_data = None

    if not clan_data or int(clan_data.get("leader_id")) != user_id:
        await query.answer("Apenas o líder pode expulsar.", show_alert=True)
        return

    members_ids = clan_data.get("members", [])
    keyboard = []
    for mid in members_ids:
        if mid == user_id: continue 
        mdata = await player_manager.get_player_data(mid)
        if mdata:
            name = mdata.get("character_name", f"ID: {mid}")
            keyboard.append([InlineKeyboardButton(f"🚫 Expulsar {name}", callback_data=f'clan_kick_ask:{mid}')])
            
    text = "<b>👟 EXPULSAR MEMBRO</b>\nSelecione quem deseja remover:" if keyboard else "Não há membros para expulsar."
    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data='clan_manage_menu')])
    
    try: await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    except: 
        await query.delete_message()
        await context.bot.send_message(query.message.chat.id, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def warn_kick_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    tid = int(query.data.split(":")[1])
    td = await player_manager.get_player_data(tid)
    tn = td.get("character_name", "o jogador") if td else "o jogador"
    text = f"⚠️ <b>Expulsar {tn}?</b>"
    kb = [[InlineKeyboardButton("✅ Sim", callback_data=f'clan_kick_do:{tid}'), InlineKeyboardButton("❌ Cancelar", callback_data='clan_kick_menu')]]
    try: await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    except: 
        await query.delete_message()
        await context.bot.send_message(query.message.chat.id, text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

async def do_kick_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    target_id = int(query.data.split(":")[1])
    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    
    try:
        # FORÇA REMOÇÃO NO BANCO
        db.clans.update_one({"_id": clan_id}, {"$pull": {"members": target_id}})
        target_data = await player_manager.get_player_data(target_id)
        if target_data:
            target_data["clan_id"] = None
            await player_manager.save_player_data(target_id, target_data)
            try: await context.bot.send_message(target_id, "🚫 Você foi expulso do clã.")
            except: pass

        await query.answer("Expulso com sucesso!", show_alert=True)
        await show_kick_member_menu(update, context)
    except Exception as e:
        logger.error(f"Erro ao expulsar: {e}")
        await query.answer("Erro ao expulsar.", show_alert=True)

# ==============================================================================
# 4. UPLOAD DE LOGO (CORRIGIDO PARA VÍDEO)
# ==============================================================================
async def start_logo_conversation(u, c) -> int:
    q = u.callback_query
    await q.answer()
    
    msg_text = "🖼️ <b>ALTERAR LOGO DO CLÃ</b>\n\nEnvie agora a <b>FOTO</b>, <b>VÍDEO</b> (curto) ou <b>GIF</b> que deseja usar."
    
    # Envia nova mensagem e salva o ID para apagar depois
    # (Não editamos a anterior para garantir que o _clean_chat funcione bem com mídias)
    try: await q.delete_message()
    except: pass
    
    msg = await c.bot.send_message(q.message.chat.id, msg_text, parse_mode="HTML")
    c.user_data['last_bot_msg_id'] = msg.message_id # <--- ISSO É CRUCIAL PARA APAGAR DEPOIS
    
    return ASKING_LOGO

async def receive_logo_image(u: Update, c: ContextTypes.DEFAULT_TYPE) -> int:
    uid = u.effective_user.id
    msg = u.message
    
    # 1. Detecta Mídia
    fid = None
    ftype = "photo"

    if msg.photo:
        fid = msg.photo[-1].file_id
        ftype = "photo"
    elif msg.video:
        fid = msg.video.file_id
        ftype = "video"
    elif msg.animation:
        fid = msg.animation.file_id
        ftype = "animation"
    elif msg.document:
        # Fallback para caso enviem como arquivo
        fid = msg.document.file_id
        if "video" in msg.document.mime_type: ftype = "video"
        elif "image" in msg.document.mime_type: ftype = "photo"
        else: ftype = "animation" # GIF costuma ser animation ou video
    
    # 2. Limpa a mensagem "Envie a foto..." e a foto enviada
    await _clean_chat(u, c)
    try: await msg.delete() # Tenta apagar a foto que o usuário enviou
    except: pass
    
    if not fid:
        await c.bot.send_message(u.effective_chat.id, "❌ Formato inválido. Envie Foto, Vídeo ou GIF.")
        return ASKING_LOGO

    # 3. Prepara os dados
    pdata = await player_manager.get_player_data(uid)
    cid = pdata.get("clan_id")
    
    # --- CORREÇÃO DO ID (STRING vs OBJECTID) ---
    try:
        # Tenta converter string para ObjectId do Mongo
        clan_db_id = ObjectId(cid)
    except:
        # Se falhar (já for objectid ou string custom), usa como está
        clan_db_id = cid
        
    print(f"DEBUG LOGO: Tentando salvar para ClanID: {clan_db_id} | Mídia: {ftype}")

    try:
        # 4. SALVA NO BANCO
        result = db.clans.update_one(
            {"_id": clan_db_id}, 
            {
                "$set": {
                    "logo_media_key": fid,
                    "logo_type": ftype
                }
            }
        )
        
        # Debug para saber se achou o clã
        print(f"DEBUG LOGO: Encontrados: {result.matched_count} | Modificados: {result.modified_count}")

        if result.matched_count == 0:
            await c.bot.send_message(u.effective_chat.id, "❌ Erro: Clã não encontrado no banco (ID incorreto).")
            return ConversationHandler.END

        # 5. Confirmação
        kb = [[InlineKeyboardButton("⬅️ Voltar", callback_data='clan_manage_menu')]]
        
        if ftype == "photo":
            await c.bot.send_photo(u.effective_chat.id, fid, caption="✅ Logo atualizado com sucesso!", reply_markup=InlineKeyboardMarkup(kb))
        else:
            await c.bot.send_animation(u.effective_chat.id, fid, caption="✅ Logo animado atualizado!", reply_markup=InlineKeyboardMarkup(kb))
            
    except Exception as e:
        logger.error(f"Erro ao salvar logo: {e}")
        await c.bot.send_message(u.effective_chat.id, f"Erro técnico: {e}")
        
    return ConversationHandler.END

async def start_invite_conversation(u,c):
    q = u.callback_query; await q.answer(); msg = await q.edit_message_text("✉️ Nome do Personagem:", parse_mode="HTML"); c.user_data['last_bot_msg_id'] = msg.message_id; return ASKING_INVITEE
async def receive_invitee_name(u,c):
    target_name = u.message.text.strip(); await _clean_chat(u, c)
    target = await player_manager.find_player_by_character_name(target_name)
    if not target: msg = await u.message.reply_text("❌ Personagem não encontrado."); c.user_data['last_bot_msg_id'] = msg.message_id; return ASKING_INVITEE
    tid = target.get('user_id') if isinstance(target, dict) else target[0]
    kb = [[InlineKeyboardButton("✅ Aceitar", callback_data=f"clan_invite_accept:{u.effective_user.id}")], [InlineKeyboardButton("❌ Recusar", callback_data="clan_invite_decline")]]
    try: await c.bot.send_message(tid, "📜 Convite de Clã recebido!", reply_markup=InlineKeyboardMarkup(kb)); await c.bot.send_message(u.effective_chat.id, "✅ Enviado!")
    except: await u.message.reply_text("❌ Erro ao enviar.")
    return ConversationHandler.END

async def accept_invite_callback(u,c): await u.callback_query.answer("Aceito!")
async def decline_invite_callback(u,c): await u.callback_query.answer("Recusado."); await u.callback_query.delete_message()
async def warn_delete_clan(u,c): await u.callback_query.answer("Em breve")
async def clan_transfer_leader_placeholder(u,c): await u.callback_query.answer("Em breve")

# ==============================================================================
# 5. EXPORTAÇÃO (HANDLERS)
# ==============================================================================
clan_manage_menu_handler = CallbackQueryHandler(show_clan_management_menu, pattern=r'^clan_manage_menu$')
clan_view_members_handler = CallbackQueryHandler(show_members_list, pattern=r'^clan_view_members$')
clan_leave_warn_handler = CallbackQueryHandler(warn_leave_clan, pattern=r'^clan_leave_ask$')
clan_leave_do_handler = CallbackQueryHandler(do_leave_clan, pattern=r'^clan_leave_perform$')
clan_kick_menu_handler = CallbackQueryHandler(show_kick_member_menu, pattern=r'^clan_kick_menu$')
clan_kick_ask_handler = CallbackQueryHandler(warn_kick_member, pattern=r'^clan_kick_ask:')
clan_kick_do_handler = CallbackQueryHandler(do_kick_member, pattern=r'^clan_kick_do:')
clan_delete_warn_handler = CallbackQueryHandler(warn_delete_clan, pattern=r'^clan_delete_warn$')
clan_delete_do_handler = None 
clan_transfer_leader_conv_handler = CallbackQueryHandler(clan_transfer_leader_placeholder, pattern='^clan_transfer')
clan_invite_accept_handler = CallbackQueryHandler(accept_invite_callback, pattern=r'^clan_invite_accept:')
clan_invite_decline_handler = CallbackQueryHandler(decline_invite_callback, pattern=r'^clan_invite_decline')

clan_logo_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_logo_conversation, pattern='^clan_logo_start$')], 
    states={ASKING_LOGO: [MessageHandler(filters.PHOTO | filters.VIDEO | filters.ANIMATION, receive_logo_image)]}, 
    fallbacks=[CommandHandler('cancelar', cancel_op)]
)
invite_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_invite_conversation, pattern=r'^clan_invite_start$')], 
    states={ ASKING_INVITEE: [MessageHandler(filters.TEXT, receive_invitee_name)] }, 
    fallbacks=[CommandHandler('cancelar', cancel_op)]
)