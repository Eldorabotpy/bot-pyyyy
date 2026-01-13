# handlers/guild/management.py
# (VERSÃO RPG COMPLETA: LISTA LIMPA -> PERFIL -> MENU DE AÇÕES + CONVITES/LOGO/TRANSFER + LIMPEZA DE LEGADOS)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, ConversationHandler,
    MessageHandler, filters, CommandHandler
)

from modules import player_manager, clan_manager
from modules.clan_manager import CLAN_RANKS, get_member_rank, check_permission, set_member_rank, get_rank_value
from handlers.guild.dashboard import _render_clan_screen
from modules.auth_utils import get_current_player_id

logger = logging.getLogger(__name__)

# Estados dos ConversationHandlers
ASKING_INVITEE = 0
ASKING_LOGO = 1
ASKING_TRANSFER_TARGET = 2

# --- HELPER DE LIMPEZA ---
async def _clean_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except:
        pass
    last_id = context.user_data.get('last_bot_msg_id')
    if last_id:
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_id)
        except:
            pass
        context.user_data.pop('last_bot_msg_id', None)

async def cancel_op(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _clean_chat(update, context)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Operação cancelada.")
    return ConversationHandler.END

# ==============================================================================
# 1. MENU PRINCIPAL DE GESTÃO
# ==============================================================================
async def show_clan_management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    if not user_id:
        return

    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)
    if not clan:
        return

    # Verifica permissões básicas
    is_leader = (str(clan.get("leader_id")) == str(user_id))
    can_invite = await check_permission(clan, user_id, 'invite_manage')

    text = f"⚙️ <b>GESTÃO DO CLÃ: {clan.get('display_name')}</b>"
    keyboard = []

    # Botão principal da nova lógica
    keyboard.append([InlineKeyboardButton("👥 Lista de Membros (Gerenciar)", callback_data='clan_view_members')])

    if can_invite:
        pending = len(clan.get("pending_applications", []))
        keyboard.append([InlineKeyboardButton(f"📩 Pedidos Pendentes ({pending})", callback_data='clan_manage_apps')])
        keyboard.append([InlineKeyboardButton("✉️ Convidar Jogador", callback_data='clan_invite_start')])

    if is_leader:
        keyboard.append([InlineKeyboardButton("🧹 Limpeza (Legados/Inválidos)", callback_data='clan_cleanup_menu')])
        keyboard.append([InlineKeyboardButton("🖼️ Alterar Logo", callback_data='clan_logo_start')])
        keyboard.append([InlineKeyboardButton("👑 Transferir Liderança", callback_data='clan_transfer_start')])
        keyboard.append([InlineKeyboardButton("⚠️ Dissolver Clã", callback_data='clan_delete_ask')])
    else:
        keyboard.append([InlineKeyboardButton("🚪 Sair do Clã", callback_data='clan_leave_ask')])

    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data='clan_menu')])

    await _render_clan_screen(update, context, clan, text, keyboard)

# ==============================================================================
# 1.1 LIMPEZA (LEGADOS / INVÁLIDOS) — MENU + AÇÕES
# ==============================================================================
async def show_cleanup_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    actor_id = get_current_player_id(update, context)
    if not actor_id:
        return

    pdata = await player_manager.get_player_data(actor_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)
    if not clan:
        await query.answer("Clã não encontrado.", show_alert=True)
        return

    is_leader = (str(clan.get("leader_id")) == str(actor_id))
    if not is_leader:
        await query.answer("Apenas o líder pode usar a limpeza.", show_alert=True)
        return

    text = (
        "🧹 <b>LIMPEZA DO CLÃ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Use estas opções para remover registros antigos que ocupam vaga ou geram notificações.\n\n"
        "• <b>Limpar Pedidos Pendentes</b>: remove candidaturas de contas inexistentes (não migradas).\n"
        "• <b>Remover Membros Inválidos</b>: expulsa contas inexistentes (não migradas) e limpa cargos.\n"
        "\n<i>Obs.: o líder nunca é removido.</i>"
    )

    kb = [
        [InlineKeyboardButton("📩 Limpar Pedidos Pendentes", callback_data="clan_cleanup_apps")],
        [InlineKeyboardButton("👥 Remover Membros Inválidos", callback_data="clan_cleanup_members")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="clan_manage_menu")],
    ]
    await _render_clan_screen(update, context, clan, text, kb)

async def do_cleanup_apps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    actor_id = get_current_player_id(update, context)
    if not actor_id:
        return

    pdata = await player_manager.get_player_data(actor_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)
    if not clan:
        await query.answer("Clã não encontrado.", show_alert=True)
        return

    is_leader = (str(clan.get("leader_id")) == str(actor_id))
    if not is_leader:
        await query.answer("Apenas o líder pode usar a limpeza.", show_alert=True)
        return

    removed_count, removed_ids = await clan_manager.cleanup_pending_applications(clan_id)

    text = (
        "📩 <b>LIMPEZA DE PEDIDOS PENDENTES</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"Removidos: <b>{removed_count}</b>\n"
    )

    if removed_ids:
        shown = removed_ids[:20]
        text += "\n<i>IDs removidos:</i>\n" + "\n".join([f"• <code>{rid}</code>" for rid in shown])
        if len(removed_ids) > 20:
            text += f"\n… e mais {len(removed_ids) - 20}"

    kb = [
        [InlineKeyboardButton("⬅️ Voltar", callback_data="clan_cleanup_menu")],
        [InlineKeyboardButton("⚙️ Gestão do Clã", callback_data="clan_manage_menu")],
    ]
    await _render_clan_screen(update, context, clan, text, kb)

async def do_cleanup_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    actor_id = get_current_player_id(update, context)
    if not actor_id:
        return

    pdata = await player_manager.get_player_data(actor_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)
    if not clan:
        await query.answer("Clã não encontrado.", show_alert=True)
        return

    is_leader = (str(clan.get("leader_id")) == str(actor_id))
    if not is_leader:
        await query.answer("Apenas o líder pode usar a limpeza.", show_alert=True)
        return

    removed_count, removed_ids = await clan_manager.cleanup_invalid_members(clan_id)

    text = (
        "👥 <b>LIMPEZA DE MEMBROS</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"Removidos: <b>{removed_count}</b>\n"
        "<i>Obs.: o líder nunca é removido.</i>\n"
    )

    if removed_ids:
        shown = removed_ids[:20]
        text += "\n<i>IDs removidos:</i>\n" + "\n".join([f"• <code>{rid}</code>" for rid in shown])
        if len(removed_ids) > 20:
            text += f"\n… e mais {len(removed_ids) - 20}"

    kb = [
        [InlineKeyboardButton("⬅️ Voltar", callback_data="clan_cleanup_menu")],
        [InlineKeyboardButton("⚙️ Gestão do Clã", callback_data="clan_manage_menu")],
    ]
    await _render_clan_screen(update, context, clan, text, kb)

# ==============================================================================
# 2. LISTA DE MEMBROS (VISUAL LIMPO)
# ==============================================================================
async def show_members_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    if not user_id:
        return

    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)
    if not clan:
        return

    members_ids = clan.get("members", [])

    text = (
        f"👥 <b>MEMBROS DO CLÃ</b>\n"
        f"🏰 <b>{clan.get('display_name')}</b>\n"
        f"Total: {len(members_ids)}/{clan.get('max_members', 10)}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Toque em um membro para ver a ficha e gerenciar cargos.</i>"
    )

    # Coleta dados para ordenação
    members_data = []
    for mid in members_ids:
        mid_str = str(mid)
        rank_key = await get_member_rank(clan, mid_str)
        rank_info = CLAN_RANKS.get(rank_key, CLAN_RANKS["member"])
        p = await player_manager.get_player_data(mid_str)

        members_data.append({
            "id": mid_str,
            "name": p.get("character_name", "Desconhecido") if p else "Desconhecido",
            "lvl": p.get("level", 1) if p else 1,
            "rank_val": rank_info["val"],
            "rank_emoji": rank_info["emoji"],
            "is_me": (mid_str == str(user_id))
        })

    # Ordena: Rank (Maior->Menor), depois Nível (Maior->Menor)
    members_data.sort(key=lambda x: (x["rank_val"], x["lvl"]), reverse=True)

    keyboard = []
    for m in members_data:
        indicator = " (Você)" if m["is_me"] else ""
        btn_text = f"{m['rank_emoji']} {m['name']} (Nv. {m['lvl']}){indicator}"
        callback = f"clan_profile:{m['id']}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback)])

    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data='clan_manage_menu')])

    await _render_clan_screen(update, context, clan, text, keyboard)

# ==============================================================================
# 3. PERFIL DO MEMBRO (FICHA RPG)
# ==============================================================================
async def show_member_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    actor_id = get_current_player_id(update, context)
    target_id = query.data.split(":")[1]

    pdata_actor = await player_manager.get_player_data(actor_id)
    clan_id = pdata_actor.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)
    if not clan:
        return

    pdata_target = await player_manager.get_player_data(target_id)
    if not pdata_target:
        await query.answer("Jogador não encontrado.", show_alert=True)
        return

    target_rank_key = await get_member_rank(clan, target_id)
    target_rank_info = CLAN_RANKS.get(target_rank_key, CLAN_RANKS["member"])

    can_promote = await check_permission(clan, actor_id, 'change_rank', target_id)
    can_kick = await check_permission(clan, actor_id, 'kick', target_id)

    text = (
        f"👤 <b>FICHA DO MEMBRO</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏷️ <b>Nome:</b> {pdata_target.get('character_name')}\n"
        f"🛡️ <b>Classe:</b> {str(pdata_target.get('class', 'Aventureiro')).title()}\n"
        f"🆙 <b>Nível:</b> {pdata_target.get('level', 1)}\n"
        f"🎖️ <b>Cargo Atual:</b> {target_rank_info['emoji']} {target_rank_info['name'].upper()}\n\n"
        f"⚔️ <b>Poder:</b>\n"
        f"   🗡️ Atk: {pdata_target.get('stats', {}).get('attack', 0)}\n"
        f"   🛡️ Def: {pdata_target.get('stats', {}).get('defense', 0)}\n"
    )

    keyboard = []

    if can_promote:
        keyboard.append([InlineKeyboardButton("🎖️ Alterar Cargo", callback_data=f"clan_setrank_menu:{target_id}")])

    if can_kick:
        keyboard.append([InlineKeyboardButton("👢 Expulsar do Clã", callback_data=f"clan_kick_ask:{target_id}")])

    if str(actor_id) == str(target_id):
        text += "\n<i>Este é o seu perfil.</i>"

    keyboard.append([InlineKeyboardButton("⬅️ Voltar à Lista", callback_data='clan_view_members')])

    await _render_clan_screen(update, context, clan, text, keyboard)

# ==============================================================================
# 4. MENU DE SELEÇÃO DE CARGO
# ==============================================================================
async def show_rank_selection_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    actor_id = get_current_player_id(update, context)
    target_id = query.data.split(":")[1]

    pdata_actor = await player_manager.get_player_data(actor_id)
    clan = await clan_manager.get_clan(pdata_actor.get("clan_id"))
    if not clan:
        return

    actor_rank_key = await get_member_rank(clan, actor_id)
    actor_val = await get_rank_value(actor_rank_key)

    pdata_target = await player_manager.get_player_data(target_id)
    target_name = pdata_target.get("character_name") if pdata_target else "Desconhecido"

    text = (
        f"🎖️ <b>DESIGNAR CARGO</b>\n"
        f"Membro: <b>{target_name}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Escolha a nova patente para este membro.\n"
        f"<i>Você só pode designar cargos inferiores ao seu.</i>\n"
    )

    keyboard = []

    # Mostrar opções abaixo do rank do ator
    if actor_val > 3:
        keyboard.append([InlineKeyboardButton("⚔️ General (Vice)", callback_data=f"clan_do_rank:{target_id}:vice")])
    if actor_val > 2:
        keyboard.append([InlineKeyboardButton("📜 Ancião", callback_data=f"clan_do_rank:{target_id}:elder")])
    if actor_val > 1:
        keyboard.append([InlineKeyboardButton("👤 Membro Comum", callback_data=f"clan_do_rank:{target_id}:member")])

    keyboard.append([InlineKeyboardButton("⬅️ Cancelar", callback_data=f"clan_profile:{target_id}")])

    await _render_clan_screen(update, context, clan, text, keyboard)

async def perform_rank_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    actor_id = get_current_player_id(update, context)

    _, target_id, new_rank = query.data.split(":")

    pdata = await player_manager.get_player_data(actor_id)
    clan_id = pdata.get("clan_id")

    success, msg = await set_member_rank(clan_id, actor_id, target_id, new_rank)

    if success:
        await query.answer("Cargo atualizado!", show_alert=True)
        query.data = f"clan_profile:{target_id}"
        await show_member_profile(update, context)
    else:
        await query.answer(f"❌ {msg}", show_alert=True)

# ==============================================================================
# 5. EXPULSÃO E SAÍDA
# ==============================================================================
async def warn_kick_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    actor_id = get_current_player_id(update, context)
    target_id = query.data.split(":")[1]

    pdata_actor = await player_manager.get_player_data(actor_id)
    clan_id = pdata_actor.get("clan_id") if pdata_actor else None
    clan = await clan_manager.get_clan(clan_id) if clan_id else None
    if not clan:
        await query.answer("Clã não encontrado.", show_alert=True)
        return

    pdata = await player_manager.get_player_data(target_id)
    name = pdata.get("character_name", "Membro") if pdata else "Membro"

    text = (
        f"⚠️ <b>EXPULSAR MEMBRO?</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"Você tem certeza que deseja remover <b>{name}</b> do clã?\n"
        f"<i>Esta ação não pode ser desfeita.</i>"
    )

    kb = [
        [InlineKeyboardButton("✅ SIM, Expulsar", callback_data=f"clan_kick_do:{target_id}")],
        [InlineKeyboardButton("❌ NÃO, Cancelar", callback_data=f"clan_profile:{target_id}")]
    ]

    # CORREÇÃO: não usar edit_message_caption (quebra em mensagens sem mídia)
    await _render_clan_screen(update, context, clan, text, kb)

async def do_kick_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    actor_id = get_current_player_id(update, context)
    target_id = query.data.split(":")[1]

    pdata = await player_manager.get_player_data(actor_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)

    if await check_permission(clan, actor_id, 'kick', target_id):
        await clan_manager.remove_member(clan_id, target_id)

        # Limpa o jogador removido
        t_data = await player_manager.get_player_data(target_id)
        if t_data:
            t_data["clan_id"] = None
            await player_manager.save_player_data(target_id, t_data)

        await query.answer("Membro expulso.")
        await show_members_list(update, context)
    else:
        await query.answer("❌ Permissão negada.", show_alert=True)

async def warn_leave_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = [[
        InlineKeyboardButton("✅ Sair", callback_data='clan_leave_perform'),
        InlineKeyboardButton("❌ Ficar", callback_data='clan_menu')
    ]]
    await query.edit_message_text(
        "⚠️ <b>SAIR DO CLÃ?</b>\nVocê perderá os benefícios imediatamente.",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="HTML"
    )

async def do_leave_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = get_current_player_id(update, context)
    p = await player_manager.get_player_data(uid)
    try:
        await clan_manager.remove_member(p.get("clan_id"), uid)
        p["clan_id"] = None
        await player_manager.save_player_data(uid, p)
        await query.answer("Você saiu do clã.")
        from handlers.guild_menu_handler import adventurer_guild_menu
        await adventurer_guild_menu(update, context)
    except Exception as e:
        await query.answer(f"Erro: {e}")

# ==============================================================================
# 6. CONVITES, LOGO, TRANSFERÊNCIA E DELETE (MANTIDOS E INTEGRADOS)
# ==============================================================================
# --- CONVITES ---
async def start_invite_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not get_current_player_id(update, context):
        return ConversationHandler.END
    try:
        await query.delete_message()
    except:
        pass
    msg = await context.bot.send_message(
        query.message.chat.id,
        "✉️ <b>CONVITE DE CLÃ</b>\n\nDigite o <b>Nome do Personagem</b> que deseja convidar:",
        parse_mode="HTML"
    )
    context.user_data['last_bot_msg_id'] = msg.message_id
    return ASKING_INVITEE

async def receive_invitee_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_current_player_id(update, context)
    target_name = update.message.text.strip()
    await _clean_chat(update, context)

    target = await player_manager.find_player_by_name(target_name)
    if not target:
        msg = await update.message.reply_text(f"❌ '{target_name}' não encontrado.")
        context.user_data['last_bot_msg_id'] = msg.message_id
        return ASKING_INVITEE

    target_id, target_data = target

    if target_data.get('clan_id'):
        await update.message.reply_text("❌ Jogador já possui clã.")
        return ConversationHandler.END

    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)

    kb_invite = [[
        InlineKeyboardButton("✅ Aceitar", callback_data=f"clan_invite_accept:{clan_id}"),
        InlineKeyboardButton("❌ Recusar", callback_data="clan_invite_decline")
    ]]

    target_chat = target_data.get("last_chat_id")
    if target_chat:
        try:
            await context.bot.send_message(
                chat_id=target_chat,
                text=f"📜 <b>CONVITE REAL: {clan.get('display_name')}</b>\n\nVocê foi convidado para se juntar a este clã.",
                reply_markup=InlineKeyboardMarkup(kb_invite),
                parse_mode="HTML"
            )
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ Convite enviado para {target_name}.",
                parse_mode="HTML"
            )
        except:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ Não foi possível contatar {target_name} (chat privado fechado?)."
            )
    return ConversationHandler.END

async def accept_invite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    clan_id = query.data.split(":")[1]
    try:
        # CORREÇÃO: convite não precisa criar application; entra direto
        await clan_manager.accept_application(clan_id, user_id)

        pdata = await player_manager.get_player_data(user_id)
        pdata["clan_id"] = clan_id
        await player_manager.save_player_data(user_id, pdata)

        await query.edit_message_text("🎉 <b>Você entrou no clã!</b>", parse_mode="HTML")
    except Exception as e:
        await query.edit_message_text(f"❌ Erro: {e}")

async def decline_invite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("❌ Convite recusado.")

# --- TRANSFERÊNCIA DE LIDERANÇA ---
async def start_transfer_leadership(u, c) -> int:
    q = u.callback_query
    await q.answer()
    try:
        await q.delete_message()
    except:
        pass
    msg = await c.bot.send_message(
        q.message.chat.id,
        "👑 <b>NOVO LÍDER</b>\n\nDigite o <b>Nome do Personagem</b> do membro para passar a coroa:",
        parse_mode="HTML"
    )
    c.user_data['last_bot_msg_id'] = msg.message_id
    return ASKING_TRANSFER_TARGET

async def receive_transfer_name(u, c) -> int:
    uid = get_current_player_id(u, c)
    tname = u.message.text.strip()
    await _clean_chat(u, c)

    target = await player_manager.find_player_by_name(tname)
    if not target:
        m = await u.message.reply_text("❌ Membro não encontrado.")
        c.user_data['last_bot_msg_id'] = m.message_id
        return ASKING_TRANSFER_TARGET

    target_id, target_data = target
    p = await player_manager.get_player_data(uid)

    try:
        await clan_manager.transfer_leadership(p.get("clan_id"), uid, target_id)
        await c.bot.send_message(u.effective_chat.id, f"✅ Liderança transferida para {tname}. Você agora é General.")
    except Exception as e:
        await c.bot.send_message(u.effective_chat.id, f"❌ Erro: {e}")

    return ConversationHandler.END

# --- DISSOLVER CLÃ ---
async def warn_delete_clan(u, c):
    q = u.callback_query
    await q.answer()
    kb = [[
        InlineKeyboardButton("🔥 DELETAR TUDO", callback_data='clan_delete_confirm'),
        InlineKeyboardButton("🔙 Cancelar", callback_data='clan_manage_menu')
    ]]
    await q.edit_message_text(
        "⚠️ <b>DISSOLVER CLÃ?</b>\n\nIsso apagará o clã, o banco e todos os registros permanentemente.",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="HTML"
    )

async def perform_delete_clan(u, c):
    q = u.callback_query
    uid = get_current_player_id(u, c)
    p = await player_manager.get_player_data(uid)
    try:
        await clan_manager.delete_clan(p.get("clan_id"), uid)
        p["clan_id"] = None
        await player_manager.save_player_data(uid, p)
        await q.edit_message_text("🚫 Clã dissolvido com sucesso.")
    except Exception as e:
        await q.edit_message_text(f"Erro: {e}")

# --- LOGO DO CLÃ ---
async def start_logo_conversation(u, c) -> int:
    q = u.callback_query
    await q.answer()
    try:
        await q.delete_message()
    except:
        pass
    msg = await c.bot.send_message(
        q.message.chat.id,
        "🖼️ <b>NOVO LOGO</b>\n\nEnvie uma <b>FOTO</b> ou <b>GIF</b> para ser o estandarte do clã:",
        parse_mode="HTML"
    )
    c.user_data['last_bot_msg_id'] = msg.message_id
    return ASKING_LOGO

async def receive_logo_image(u, c) -> int:
    uid = get_current_player_id(u, c)
    msg = u.message
    fid, ftype = None, "photo"
    if msg.photo:
        fid = msg.photo[-1].file_id
    elif msg.video:
        fid = msg.video.file_id
        ftype = "video"
    elif msg.animation:
        fid = msg.animation.file_id
        ftype = "animation"
    elif msg.document:
        fid = msg.document.file_id
        ftype = "video" if (msg.document.mime_type and "video" in msg.document.mime_type) else "photo"

    await _clean_chat(u, c)
    if not fid:
        return ASKING_LOGO

    p = await player_manager.get_player_data(uid)
    await clan_manager.set_clan_media(p.get("clan_id"), uid, {"file_id": fid, "type": ftype})

    await c.bot.send_message(u.effective_chat.id, "✅ Logo atualizado! Veja no painel principal.")
    return ConversationHandler.END

# ==============================================================================
# HANDLERS EXPORTADOS
# ==============================================================================
clan_manage_menu_handler = CallbackQueryHandler(show_clan_management_menu, pattern=r'^clan_manage_menu$')

# Lista e Perfil (Novo Fluxo)
clan_view_members_handler = CallbackQueryHandler(show_members_list, pattern=r'^clan_view_members$')
clan_profile_handler = CallbackQueryHandler(show_member_profile, pattern=r'^clan_profile:')
clan_setrank_menu_handler = CallbackQueryHandler(show_rank_selection_menu, pattern=r'^clan_setrank_menu:')
clan_do_rank_handler = CallbackQueryHandler(perform_rank_change, pattern=r'^clan_do_rank:')

# Limpeza
clan_cleanup_menu_handler = CallbackQueryHandler(show_cleanup_menu, pattern=r'^clan_cleanup_menu$')
clan_cleanup_apps_handler = CallbackQueryHandler(do_cleanup_apps, pattern=r'^clan_cleanup_apps$')
clan_cleanup_members_handler = CallbackQueryHandler(do_cleanup_members, pattern=r'^clan_cleanup_members$')

# Ações
clan_kick_menu_handler = CallbackQueryHandler(show_members_list, pattern=r'^clan_kick_menu$')  # Redireciona para lista
clan_kick_ask_handler = CallbackQueryHandler(warn_kick_member, pattern=r'^clan_kick_ask:')
clan_kick_do_handler = CallbackQueryHandler(do_kick_member, pattern=r'^clan_kick_do:')

clan_leave_warn_handler = CallbackQueryHandler(warn_leave_clan, pattern=r'^clan_leave_ask$')
clan_leave_do_handler = CallbackQueryHandler(do_leave_clan, pattern=r'^clan_leave_perform$')
clan_delete_warn_handler = CallbackQueryHandler(warn_delete_clan, pattern=r'^clan_delete_ask$')
clan_delete_do_handler = CallbackQueryHandler(perform_delete_clan, pattern=r'^clan_delete_confirm$')

# Convites (Callbacks)
clan_invite_accept_handler = CallbackQueryHandler(accept_invite_callback, pattern=r'^clan_invite_accept:')
clan_invite_decline_handler = CallbackQueryHandler(decline_invite_callback, pattern=r'^clan_invite_decline$')

# Compatibilidade (Legacy Buttons, se existirem em algum lugar)
clan_promote_handler = CallbackQueryHandler(lambda u, c: u.callback_query.answer("Use o perfil."), pattern=r'^clan_promote:')
clan_demote_handler = CallbackQueryHandler(lambda u, c: u.callback_query.answer("Use o perfil."), pattern=r'^clan_demote:')

# Conversations
invite_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_invite_conversation, pattern=r'^clan_invite_start$')],
    states={ASKING_INVITEE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_invitee_name)]},
    fallbacks=[CommandHandler('cancelar', cancel_op)]
)

clan_transfer_leader_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_transfer_leadership, pattern=r'^clan_transfer_start$')],
    states={ASKING_TRANSFER_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_transfer_name)]},
    fallbacks=[CommandHandler('cancelar', cancel_op)]
)

clan_logo_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_logo_conversation, pattern=r'^clan_logo_start$')],
    states={ASKING_LOGO: [MessageHandler(filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.Document.ALL, receive_logo_image)]},
    fallbacks=[CommandHandler('cancelar', cancel_op)]
)
