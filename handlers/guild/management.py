# handlers/guild/management.py
# (VERSÃO ATUALIZADA: COM GESTÃO DE CARGOS E ÍCONES)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, ConversationHandler,
    MessageHandler, filters, CommandHandler
)

from bson import ObjectId
from modules import player_manager, clan_manager
from modules.clan_manager import CLAN_RANKS, get_member_rank, promote_member, demote_member
from modules.database import db
from handlers.guild.dashboard import _render_clan_screen
from modules.auth_utils import get_current_player_id

logger = logging.getLogger(__name__)

ASKING_INVITEE = 0
ASKING_LOGO = 1
ASKING_TRANSFER_TARGET = 2

# --- HELPER DE LIMPEZA ---
async def _clean_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    last_id = context.user_data.get('last_bot_msg_id')
    if last_id:
        try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_id)
        except: pass
        context.user_data.pop('last_bot_msg_id', None)

async def cancel_op(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _clean_chat(update, context)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Operação cancelada.")
    return ConversationHandler.END

# ==============================================================================
# 1. MENU DE GESTÃO
# ==============================================================================
async def show_clan_management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    if not user_id: return

    try: await query.answer()
    except: pass
    
    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    
    clan_data = await clan_manager.get_clan(clan_id)
    if not clan_data: return

    leader_id_raw = clan_data.get("leader_id", "")
    is_leader = (str(leader_id_raw) == str(user_id))
    
    pending = clan_data.get("pending_applications", [])
    
    keyboard = []
    keyboard.append([InlineKeyboardButton("📜 Ver Lista de Membros", callback_data='clan_view_members')])

    if is_leader:
        text = f"👑 <b>GESTÃO DO CLÃ: {clan_data.get('display_name')}</b>"
        if pending:
            keyboard.append([InlineKeyboardButton(f"📝 Ver Pedidos ({len(pending)})", callback_data='clan_manage_apps')])
        
        keyboard.append([InlineKeyboardButton("✉️ Convidar Jogador", callback_data='clan_invite_start')])
        keyboard.append([InlineKeyboardButton("👟 Expulsar Membro", callback_data='clan_kick_menu')])
        keyboard.append([InlineKeyboardButton("🖼️ Alterar Logo", callback_data='clan_logo_start')])
        keyboard.append([InlineKeyboardButton("👑 Transferir Liderança", callback_data='clan_transfer_start')])
        keyboard.append([InlineKeyboardButton("⚠️ Dissolver Clã", callback_data='clan_delete_ask')])
    else:
        text = "👤 <b>ÁREA DO MEMBRO</b>\n\nDeseja sair do clã?"
        keyboard.append([InlineKeyboardButton("🚪 Sair do Clã", callback_data='clan_leave_ask')])

    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data='clan_menu')])

    await _render_clan_screen(update, context, clan_data, text, keyboard)

# ==============================================================================
# 2. LISTA DE MEMBROS (COM CARGOS E BOTÕES)
# ==============================================================================

async def show_members_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    if not user_id: return

    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    clan_data = await clan_manager.get_clan(clan_id)

    members_ids = clan_data.get("members", [])
    
    # Verifica o cargo de QUEM ESTÁ VENDO a lista
    my_rank_key = await get_member_rank(clan_data, user_id)
    is_leader = (my_rank_key == "leader")

    text = f"👥 <b>Membros de {clan_data.get('display_name')}</b>\n"
    text += f"Total: {len(members_ids)}/{clan_data.get('max_members', 10)}\n\n"
    
    keyboard = []
    
    # 1. Coleta dados de todos os membros
    members_list = []
    for mid in members_ids:
        mid_str = str(mid)
        
        # Obtém o cargo deste membro
        rank_key = await get_member_rank(clan_data, mid_str)
        rank_info = CLAN_RANKS.get(rank_key, CLAN_RANKS["member"])
        
        p = await player_manager.get_player_data(mid_str)
        if p:
            members_list.append({
                "id": mid_str,
                "name": p.get("character_name", "Desconhecido"),
                "lvl": p.get("level", 1),
                "rank_val": rank_info["lvl"],   # 4=Lider, 3=Vice...
                "rank_name": rank_info["name"],
                "emoji": rank_info["emoji"]
            })

    # 2. Ordena: Maior rank primeiro, depois maior nível
    members_list.sort(key=lambda x: (x["rank_val"], x["lvl"]), reverse=True)

    # 3. Monta visual
    for m in members_list:
        text += f"{m['emoji']} <b>{m['name']}</b> (Nv. {m['lvl']}) - <i>{m['rank_name']}</i>\n"
        
        # Botões de Promoção (Apenas para o Líder e não para si mesmo)
        if is_leader and m['id'] != str(user_id):
            row = []
            # Botão de Promover (se não for Vice já)
            if m['rank_val'] < 3: 
                row.append(InlineKeyboardButton(f"⬆️ Promover", callback_data=f"clan_promote:{m['id']}"))
            
            # Botão de Rebaixar (se não for Membro já)
            if m['rank_val'] > 1:
                row.append(InlineKeyboardButton(f"⬇️ Rebaixar", callback_data=f"clan_demote:{m['id']}"))
            
            if row:
                keyboard.append(row)

    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data='clan_menu')])
    
    await _render_clan_screen(update, context, clan_data, text, keyboard)

async def promote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    target_id = query.data.split(":")[1]
    
    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    
    success, msg = await promote_member(clan_id, user_id, target_id)
    
    if success:
        await query.answer("Promovido!")
        await show_members_list(update, context) 
    else:
        await query.answer(msg, show_alert=True)

async def demote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    target_id = query.data.split(":")[1]
    
    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    
    success, msg = await demote_member(clan_id, user_id, target_id)
    
    if success:
        await query.answer("Rebaixado!")
        await show_members_list(update, context)
    else:
        await query.answer(msg, show_alert=True)

# ==============================================================================
# 3. OUTROS HANDLERS (Convites, Logo, Transferência - Mantidos)
# ==============================================================================

async def start_invite_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    if not get_current_player_id(update, context): return ConversationHandler.END
    try: await query.delete_message()
    except: pass
    msg = await context.bot.send_message(query.message.chat.id, "✉️ <b>Nome do Personagem:</b>", parse_mode="HTML")
    context.user_data['last_bot_msg_id'] = msg.message_id
    return ASKING_INVITEE

async def receive_invitee_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_current_player_id(update, context)
    target_name = update.message.text.strip()
    await _clean_chat(update, context)

    target = await player_manager.find_player_by_character_name(target_name)
    if not target:
        msg = await update.message.reply_text(f"❌ '{target_name}' não encontrado.")
        context.user_data['last_bot_msg_id'] = msg.message_id
        return ASKING_INVITEE
    
    target_data = target[0] if isinstance(target, list) and target else target
    if target_data.get('clan_id'):
        await update.message.reply_text("❌ Jogador já possui clã.")
        return ConversationHandler.END

    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)

    kb_invite = [[InlineKeyboardButton("✅ Aceitar", callback_data=f"clan_invite_accept:{clan_id}"), InlineKeyboardButton("❌ Recusar", callback_data="clan_invite_decline")]]
    
    target_chat = target_data.get("last_chat_id") or target_data.get("telegram_id_owner")
    if target_chat:
        try:
            await context.bot.send_message(chat_id=target_chat, text=f"📜 <b>CONVITE: {clan.get('display_name')}</b>", reply_markup=InlineKeyboardMarkup(kb_invite), parse_mode="HTML")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Convite enviado.", parse_mode="HTML")
        except: pass
    return ConversationHandler.END

async def accept_invite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    clan_id = query.data.split(":")[1]
    try:
        await clan_manager.add_application(clan_id, user_id)
        await clan_manager.accept_application(clan_id, user_id)
        pdata = await player_manager.get_player_data(user_id)
        pdata["clan_id"] = clan_id
        await player_manager.save_player_data(user_id, pdata)
        await query.edit_message_text(f"🎉 <b>Você entrou no clã!</b>", parse_mode="HTML")
    except Exception as e: await query.edit_message_text(f"❌ Erro: {e}")

async def decline_invite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("❌ Convite recusado.")

# Expulsar, Sair, Deletar, Transferir e Logo (Funções Helper)
async def warn_leave_clan(u, c):
    q = u.callback_query; await q.answer()
    kb = [[InlineKeyboardButton("✅ Sair", callback_data='clan_leave_perform'), InlineKeyboardButton("❌ Ficar", callback_data='clan_manage_menu')]]
    await q.edit_message_text("⚠️ Sair do clã?", reply_markup=InlineKeyboardMarkup(kb))

async def do_leave_clan(u, c):
    q = u.callback_query
    uid = get_current_player_id(u, c)
    p = await player_manager.get_player_data(uid)
    try:
        await clan_manager.remove_member(p.get("clan_id"), uid)
        p["clan_id"] = None
        await player_manager.save_player_data(uid, p)
        await q.answer("Saiu do clã.")
        from handlers.guild_menu_handler import adventurer_guild_menu
        await adventurer_guild_menu(u, c)
    except Exception as e: await q.answer(f"Erro: {e}")

async def show_kick_member_menu(u, c):
    q = u.callback_query
    uid = get_current_player_id(u, c)
    p = await player_manager.get_player_data(uid)
    clan = await clan_manager.get_clan(p.get("clan_id"))
    if str(clan.get("leader_id")) != str(uid): await q.answer("Apenas o líder.", show_alert=True); return
    await q.answer()
    kb = []
    for mid in clan.get("members", []):
        if str(mid) == str(uid): continue
        m = await player_manager.get_player_data(str(mid))
        if m: kb.append([InlineKeyboardButton(f"🚫 {m.get('character_name')}", callback_data=f'clan_kick_ask:{mid}')])
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data='clan_manage_menu')])
    await q.edit_message_text("<b>👟 EXPULSAR MEMBRO</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def warn_kick_member(u, c):
    q = u.callback_query; await q.answer()
    tid = q.data.split(":")[1]
    kb = [[InlineKeyboardButton("✅ Sim", callback_data=f'clan_kick_do:{tid}'), InlineKeyboardButton("❌ Não", callback_data='clan_kick_menu')]]
    await q.edit_message_text(f"⚠️ Expulsar membro?", reply_markup=InlineKeyboardMarkup(kb))

async def do_kick_member(u, c):
    q = u.callback_query
    uid = get_current_player_id(u, c)
    tid = q.data.split(":")[1]
    p = await player_manager.get_player_data(uid)
    try:
        await clan_manager.remove_member(p.get("clan_id"), tid)
        t = await player_manager.get_player_data(tid)
        if t: 
            t["clan_id"] = None
            await player_manager.save_player_data(tid, t)
        await q.answer("Expulso!")
        await show_kick_member_menu(u, c)
    except Exception as e: await q.answer(f"Erro: {e}")

async def start_transfer_leadership(u, c) -> int:
    q = u.callback_query; await q.answer()
    try: await q.delete_message()
    except: pass
    msg = await c.bot.send_message(q.message.chat.id, "👑 <b>Nome do Membro:</b>", parse_mode="HTML")
    c.user_data['last_bot_msg_id'] = msg.message_id
    return ASKING_TRANSFER_TARGET

async def receive_transfer_name(u, c) -> int:
    uid = get_current_player_id(u, c)
    tname = u.message.text.strip()
    await _clean_chat(u, c)
    target = await player_manager.find_player_by_character_name(tname)
    if not target: return ASKING_TRANSFER_TARGET
    target_data = target[0] if isinstance(target, list) and target else target
    target_id = str(target_data.get('user_id') or target_data.get('_id'))
    p = await player_manager.get_player_data(uid)
    await clan_manager.transfer_leadership(p.get("clan_id"), uid, target_id)
    await c.bot.send_message(u.effective_chat.id, f"✅ Liderança transferida para {tname}.")
    return ConversationHandler.END

async def warn_delete_clan(u, c):
    q = u.callback_query; await q.answer()
    kb = [[InlineKeyboardButton("🔥 APAGAR TUDO", callback_data='clan_delete_confirm'), InlineKeyboardButton("🔙 Cancelar", callback_data='clan_manage_menu')]]
    await q.edit_message_text("⚠️ <b>DISSOLVER CLÃ?</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def perform_delete_clan(u, c):
    q = u.callback_query
    uid = get_current_player_id(u, c)
    p = await player_manager.get_player_data(uid)
    await clan_manager.delete_clan(p.get("clan_id"), uid)
    p["clan_id"] = None
    await player_manager.save_player_data(uid, p)
    await q.edit_message_text("🚫 Clã dissolvido.")

async def start_logo_conversation(u, c) -> int:
    q = u.callback_query; await q.answer()
    try: await q.delete_message()
    except: pass
    msg = await c.bot.send_message(q.message.chat.id, "🖼️ Envie FOTO/GIF:", parse_mode="HTML")
    c.user_data['last_bot_msg_id'] = msg.message_id
    return ASKING_LOGO

async def receive_logo_image(u, c) -> int:
    uid = get_current_player_id(u, c)
    msg = u.message
    fid, ftype = None, "photo"
    if msg.photo: fid = msg.photo[-1].file_id
    elif msg.video: fid = msg.video.file_id; ftype = "video"
    elif msg.animation: fid = msg.animation.file_id; ftype = "animation"
    elif msg.document: fid = msg.document.file_id; ftype = "video" if "video" in msg.document.mime_type else "photo"
    await _clean_chat(u, c)
    if not fid: return ASKING_LOGO
    p = await player_manager.get_player_data(uid)
    await clan_manager.set_clan_media(p.get("clan_id"), uid, {"file_id": fid, "type": ftype})
    await c.bot.send_message(u.effective_chat.id, "✅ Logo atualizado!")
    return ConversationHandler.END

# ==============================================================================
# HANDLERS EXPORTADOS
# ==============================================================================

clan_manage_menu_handler = CallbackQueryHandler(show_clan_management_menu, pattern=r'^clan_manage_menu$')
clan_view_members_handler = CallbackQueryHandler(show_members_list, pattern=r'^clan_view_members$')

# Promoção/Rebaixamento (Novos)
clan_promote_handler = CallbackQueryHandler(promote_callback, pattern=r'^clan_promote:')
clan_demote_handler = CallbackQueryHandler(demote_callback, pattern=r'^clan_demote:')

# Sair
clan_leave_warn_handler = CallbackQueryHandler(warn_leave_clan, pattern=r'^clan_leave_ask$')
clan_leave_do_handler = CallbackQueryHandler(do_leave_clan, pattern=r'^clan_leave_perform$')

# Expulsar
clan_kick_menu_handler = CallbackQueryHandler(show_kick_member_menu, pattern=r'^clan_kick_menu$')
clan_kick_ask_handler = CallbackQueryHandler(warn_kick_member, pattern=r'^clan_kick_ask:')
clan_kick_do_handler = CallbackQueryHandler(do_kick_member, pattern=r'^clan_kick_do:')

# Deletar
clan_delete_warn_handler = CallbackQueryHandler(warn_delete_clan, pattern=r'^clan_delete_ask$')
clan_delete_do_handler = CallbackQueryHandler(perform_delete_clan, pattern=r'^clan_delete_confirm$')

# Convites
clan_invite_accept_handler = CallbackQueryHandler(accept_invite_callback, pattern=r'^clan_invite_accept:')
clan_invite_decline_handler = CallbackQueryHandler(decline_invite_callback, pattern=r'^clan_invite_decline')

invite_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_invite_conversation, pattern=r'^clan_invite_start$')], 
    states={ ASKING_INVITEE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_invitee_name)] }, 
    fallbacks=[CommandHandler('cancelar', cancel_op)]
)

clan_transfer_leader_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_transfer_leadership, pattern=r'^clan_transfer_start$')], 
    states={ ASKING_TRANSFER_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_transfer_name)] }, 
    fallbacks=[CommandHandler('cancelar', cancel_op)]
)

clan_logo_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_logo_conversation, pattern='^clan_logo_start$')], 
    states={ASKING_LOGO: [MessageHandler(filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.Document.ALL, receive_logo_image)]}, 
    fallbacks=[CommandHandler('cancelar', cancel_op)]
)