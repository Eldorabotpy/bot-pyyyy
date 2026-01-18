# handlers/guild/management.py
# (VERSÃO CORRIGIDA: UI RENDERER + SEM DEPENDÊNCIA CIRCULAR + VISUAL ADMIN)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, ConversationHandler,
    MessageHandler, filters, CommandHandler
)
from bson import ObjectId
from modules import player_manager, clan_manager, file_ids
from modules.clan_manager import CLAN_RANKS, get_member_rank, check_permission, set_member_rank, get_rank_value
from modules.auth_utils import get_current_player_id
from ui.ui_renderer import render_photo_or_text

logger = logging.getLogger(__name__)

# Estados dos ConversationHandlers
ASKING_INVITEE = 0
ASKING_LOGO = 1
ASKING_TRANSFER_TARGET = 2

# ==============================================================================
# HELPERS VISUAIS & UTILS
# ==============================================================================

def _get_clans_collection():
    """Fallback para obter a coleção de clãs."""
    try:
        from modules.database import db
        if hasattr(db, "__getitem__"): return db["clans"]
        if hasattr(db, "clans"): return db.clans
    except: pass
    return None

def _to_oid(cid):
    try:
        if isinstance(cid, ObjectId): return cid
        if isinstance(cid, str) and ObjectId.is_valid(cid): return ObjectId(cid)
    except: pass
    return cid

def _pick_management_media(clan_data):
    """
    Tenta selecionar uma imagem administrativa (Trono, Escritório) 
    ou usa o Logo do Clã.
    """
    # 1. Tenta imagem de Admin/Gestão
    try:
        fid = file_ids.get_file_id("img_clan_admin")
        if fid: return fid
    except: pass

    # 2. Logo do Clã
    if clan_data and clan_data.get("logo_media_key"):
        return clan_data.get("logo_media_key")
    
    # 3. Fallback
    try:
        return file_ids.get_file_id("img_clan_default")
    except:
        return None

async def _render_admin_screen(update, context, clan_data, text, keyboard):
    """Renderiza a tela usando o sistema unificado UI Renderer."""
    media_id = _pick_management_media(clan_data)
    
    await render_photo_or_text(
        update,
        context,
        text=text,
        photo_file_id=media_id,
        reply_markup=InlineKeyboardMarkup(keyboard),
        scope="clan_manage_screen", # Scope único para manter navegação fluida na gestão
        parse_mode="HTML",
        allow_edit=True
    )

async def _clean_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Helper para limpar mensagens de input em ConversationHandlers."""
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
# 1. MENU PRINCIPAL DE GESTÃO
# ==============================================================================
async def show_clan_management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()

    user_id = get_current_player_id(update, context)
    if not user_id: return

    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)
    if not clan:
        await render_photo_or_text(update, context, "Clã não encontrado.", None)
        return

    # Verifica permissões básicas
    is_leader = (str(clan.get("leader_id")) == str(user_id))
    can_invite = await check_permission(clan, user_id, 'invite_manage')

    text = f"⚙️ <b>GESTÃO DO CLÃ: {clan.get('display_name')}</b>\n━━━━━━━━━━━━━━━━━━━\n\nSelecione uma categoria administrativa:"
    keyboard = []

    # Botão principal da nova lógica
    keyboard.append([InlineKeyboardButton("👥 Membros & Cargos", callback_data='clan_view_members')])

    if can_invite:
        pending = len(clan.get("pending_applications", []))
        # Se houver pendências, destaca o botão
        btn_txt = f"📩 Pedidos Pendentes ({pending})" if pending > 0 else "📩 Pedidos Pendentes"
        keyboard.append([InlineKeyboardButton(btn_txt, callback_data='clan_manage_apps')])
        keyboard.append([InlineKeyboardButton("✉️ Convidar Jogador", callback_data='clan_invite_start')])

    if is_leader:
        keyboard.append([InlineKeyboardButton("🧹 Limpeza de Registro", callback_data='clan_cleanup_menu')])
        keyboard.append([InlineKeyboardButton("🖼️ Alterar Logo/Bandeira", callback_data='clan_logo_start')])
        keyboard.append([InlineKeyboardButton("👑 Transferir Liderança", callback_data='clan_transfer_start')])
        keyboard.append([InlineKeyboardButton("⚠️ Dissolver Clã", callback_data='clan_delete_ask')])
    else:
        keyboard.append([InlineKeyboardButton("🚪 Sair do Clã", callback_data='clan_leave_ask')])

    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data='clan_menu')])

    await _render_admin_screen(update, context, clan, text, keyboard)


# ==============================================================================
# 1.1 LIMPEZA (LEGADOS / INVÁLIDOS)
# ==============================================================================
async def show_cleanup_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    actor_id = get_current_player_id(update, context)
    if not actor_id: return

    pdata = await player_manager.get_player_data(actor_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)
    
    if not clan: return

    # Apenas Líder
    if str(clan.get("leader_id")) != str(actor_id):
        await query.answer("Acesso restrito ao Líder.", show_alert=True)
        return

    text = (
        "🧹 <b>LIMPEZA DE REGISTROS</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Ferramentas para manter a saúde do banco de dados do clã:\n\n"
        "• <b>Limpar Pedidos:</b> Remove solicitações de contas deletadas.\n"
        "• <b>Remover Fantasmas:</b> Remove membros que não existem mais no jogo.\n"
        "\n<i>O líder nunca é removido.</i>"
    )

    kb = [
        [InlineKeyboardButton("📩 Limpar Pedidos Pendentes", callback_data="clan_cleanup_apps")],
        [InlineKeyboardButton("👥 Remover Membros Fantasmas", callback_data="clan_cleanup_members")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="clan_manage_menu")],
    ]
    await _render_admin_screen(update, context, clan, text, kb)

async def do_cleanup_apps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Processando...")
    
    actor_id = get_current_player_id(update, context)
    pdata = await player_manager.get_player_data(actor_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)

    apps = clan.get("pending_applications", []) or []
    members = set(str(x) for x in (clan.get("members", []) or []))

    kept = []
    removed_count = 0

    for aid in apps:
        aid_str = str(aid)
        # Se já é membro, remove da pendência
        if aid_str in members:
            removed_count += 1
            continue
        
        # Se player não existe, remove
        ap = await player_manager.get_player_data(aid_str)
        if not ap:
            removed_count += 1
            continue
            
        kept.append(aid_str)

    # Atualiza DB
    col = _get_clans_collection()
    if col is not None:
        await col.update_one({"_id": _to_oid(clan_id)}, {"$set": {"pending_applications": kept}})

    # Feedback
    text = (
        "📩 <b>RESULTADO DA LIMPEZA</b>\n"
        f"Registros removidos: <b>{removed_count}</b>\n"
        f"Pendências válidas restantes: <b>{len(kept)}</b>"
    )
    # Recarrega objeto clan atualizado para renderizar
    clan["pending_applications"] = kept
    
    kb = [[InlineKeyboardButton("⬅️ Voltar", callback_data="clan_cleanup_menu")]]
    await _render_admin_screen(update, context, clan, text, kb)

async def do_cleanup_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Processando...")
    
    actor_id = get_current_player_id(update, context)
    pdata = await player_manager.get_player_data(actor_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)
    
    leader_id = str(clan.get("leader_id"))
    members = [str(x) for x in (clan.get("members", []) or [])]

    kept_members = []
    removed_count = 0

    for mid in members:
        mid_str = str(mid)
        # Líder imune
        if mid_str == leader_id:
            kept_members.append(mid_str)
            continue

        p = await player_manager.get_player_data(mid_str)
        
        # Se não existe OU se o clan_id no perfil dele é outro/nulo
        if not p:
            removed_count += 1
            continue
            
        if str(p.get("clan_id")) != str(clan_id):
            removed_count += 1
            # Corrige o player também se necessário (limpa id fantasma)
            if p:
                p["clan_id"] = None
                await player_manager.save_player_data(mid_str, p)
            continue

        kept_members.append(mid_str)

    col = _get_clans_collection()
    if col is not None:
        await col.update_one({"_id": _to_oid(clan_id)}, {"$set": {"members": kept_members}})

    text = (
        "👥 <b>LIMPEZA DE MEMBROS</b>\n"
        f"Fantasmas removidos: <b>{removed_count}</b>\n"
        f"Membros ativos: <b>{len(kept_members)}</b>"
    )
    
    clan["members"] = kept_members
    kb = [[InlineKeyboardButton("⬅️ Voltar", callback_data="clan_cleanup_menu")]]
    await _render_admin_screen(update, context, clan, text, kb)

# ==============================================================================
# 2. LISTA DE MEMBROS & PERFIL
# ==============================================================================
async def show_members_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()

    user_id = get_current_player_id(update, context)
    if not user_id: return

    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)
    if not clan: return

    members_ids = clan.get("members", [])
    max_members = clan.get("max_members", 10) # Pega do upgrade se tiver, ou default

    text = (
        f"👥 <b>LISTA DE MEMBROS</b>\n"
        f"Lotação: {len(members_ids)}/{max_members}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Toque em um nome para gerenciar cargos ou expulsar.</i>"
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
            "name": p.get("character_name", "Desconhecido") if p else "FANTASMA",
            "lvl": p.get("level", 1) if p else 0,
            "rank_val": rank_info["val"],
            "rank_emoji": rank_info["emoji"],
            "is_me": (mid_str == str(user_id))
        })

    # Ordena: Rank (Maior->Menor), depois Nível
    members_data.sort(key=lambda x: (x["rank_val"], x["lvl"]), reverse=True)

    keyboard = []
    for m in members_data:
        indicator = " (Você)" if m["is_me"] else ""
        btn_text = f"{m['rank_emoji']} {m['name']} (Nv. {m['lvl']}){indicator}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"clan_profile:{m['id']}")])

    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data='clan_manage_menu')])

    await _render_admin_screen(update, context, clan, text, keyboard)

async def show_member_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    actor_id = get_current_player_id(update, context)
    try:
        target_id = query.data.split(":")[1]
    except:
        return

    pdata_actor = await player_manager.get_player_data(actor_id)
    clan_id = pdata_actor.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)

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
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ <b>Nome:</b> {pdata_target.get('character_name')}\n"
        f"🛡️ <b>Classe:</b> {str(pdata_target.get('class', 'Aventureiro')).title()}\n"
        f"🆙 <b>Nível:</b> {pdata_target.get('level', 1)}\n"
        f"🎖️ <b>Cargo:</b> {target_rank_info['emoji']} {target_rank_info['name'].upper()}\n"
        f"⚔️ <b>Poder:</b> Atk {pdata_target.get('stats', {}).get('attack', 0)} | Def {pdata_target.get('stats', {}).get('defense', 0)}\n"
    )

    keyboard = []

    if can_promote:
        keyboard.append([InlineKeyboardButton("🎖️ Alterar Cargo", callback_data=f"clan_setrank_menu:{target_id}")])

    if can_kick:
        keyboard.append([InlineKeyboardButton("👢 Expulsar do Clã", callback_data=f"clan_kick_ask:{target_id}")])

    if str(actor_id) == str(target_id):
        text += "\n<i>(Este é o seu perfil)</i>"

    keyboard.append([InlineKeyboardButton("⬅️ Voltar à Lista", callback_data='clan_view_members')])

    await _render_admin_screen(update, context, clan, text, keyboard)


# ==============================================================================
# 3. ALTERAÇÃO DE CARGOS
# ==============================================================================
async def show_rank_selection_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    actor_id = get_current_player_id(update, context)
    target_id = query.data.split(":")[1]

    pdata_actor = await player_manager.get_player_data(actor_id)
    clan = await clan_manager.get_clan(pdata_actor.get("clan_id"))
    
    # Valida hierarquia
    actor_rank_key = await get_member_rank(clan, actor_id)
    actor_val = await get_rank_value(actor_rank_key)

    pdata_target = await player_manager.get_player_data(target_id)
    target_name = pdata_target.get("character_name", "Membro")

    text = (
        f"🎖️ <b>DESIGNAR PATENTE</b>\n"
        f"Membro: <b>{target_name}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Selecione o novo cargo.\n"
        f"<i>Você só pode promover até um nível abaixo do seu.</i>"
    )

    keyboard = []
    # Mostra apenas cargos que o ator pode dar (inferiores ao dele)
    if actor_val > 3: # Líder pode dar General
        keyboard.append([InlineKeyboardButton("⚔️ General (Vice)", callback_data=f"clan_do_rank:{target_id}:vice")])
    if actor_val > 2: # General pode dar Elder
        keyboard.append([InlineKeyboardButton("📜 Ancião", callback_data=f"clan_do_rank:{target_id}:elder")])
    if actor_val > 1: # Elder pode dar Membro
        keyboard.append([InlineKeyboardButton("👤 Membro Comum", callback_data=f"clan_do_rank:{target_id}:member")])

    keyboard.append([InlineKeyboardButton("⬅️ Cancelar", callback_data=f"clan_profile:{target_id}")])

    await _render_admin_screen(update, context, clan, text, keyboard)

async def perform_rank_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    actor_id = get_current_player_id(update, context)

    _, target_id, new_rank = query.data.split(":")
    pdata = await player_manager.get_player_data(actor_id)
    clan_id = pdata.get("clan_id")

    success, msg = await set_member_rank(clan_id, actor_id, target_id, new_rank)

    if success:
        await query.answer("Cargo atualizado com sucesso!", show_alert=True)
        # Retorna ao perfil atualizado
        query.data = f"clan_profile:{target_id}"
        await show_member_profile(update, context)
    else:
        await query.answer(f"❌ {msg}", show_alert=True)


# ==============================================================================
# 4. EXPULSÃO E SAÍDA
# ==============================================================================
async def warn_kick_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    actor_id = get_current_player_id(update, context)
    target_id = query.data.split(":")[1]

    pdata_actor = await player_manager.get_player_data(actor_id)
    clan = await clan_manager.get_clan(pdata_actor.get("clan_id"))
    
    pdata_target = await player_manager.get_player_data(target_id)
    name = pdata_target.get("character_name", "Membro") if pdata_target else "Desconhecido"

    text = (
        f"⚠️ <b>CONFIRMAR EXPULSÃO</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"Você tem certeza que deseja remover <b>{name}</b> do clã?\n"
        f"<i>Esta ação é irreversível e o jogador perderá todos os bônus.</i>"
    )

    kb = [
        [InlineKeyboardButton("✅ SIM, Expulsar", callback_data=f"clan_kick_do:{target_id}")],
        [InlineKeyboardButton("❌ NÃO, Cancelar", callback_data=f"clan_profile:{target_id}")]
    ]
    await _render_admin_screen(update, context, clan, text, kb)

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
        InlineKeyboardButton("✅ CONFIRMAR SAÍDA", callback_data='clan_leave_perform'),
        InlineKeyboardButton("❌ CANCELAR", callback_data='clan_menu')
    ]]
    
    # Usa render text simples para o aviso
    await render_photo_or_text(
        update, context,
        "⚠️ <b>SAIR DO CLÃ?</b>\n\nVocê perderá acesso ao banco, bônus e missões imediatamente.\nTem certeza?",
        InlineKeyboardMarkup(kb)
    )

async def do_leave_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = get_current_player_id(update, context)
    
    p = await player_manager.get_player_data(uid)
    clan_id = p.get("clan_id")
    
    try:
        await clan_manager.remove_member(clan_id, uid)
        p["clan_id"] = None
        await player_manager.save_player_data(uid, p)
        
        await query.answer("Você saiu do clã.")
        # Redireciona para o menu principal da guilda (que vai mostrar 'criar/entrar')
        from handlers.guild.dashboard import adventurer_guild_menu
        await adventurer_guild_menu(update, context)
        
    except Exception as e:
        await query.answer(f"Erro: {e}", show_alert=True)


# ==============================================================================
# 5. CONVERSATION HANDLERS (CONVITE, LOGO, TRANSFER, DELETE)
# ==============================================================================

# --- CONVITES ---
async def start_invite_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    # Limpa a tela anterior (menu)
    try: await query.delete_message()
    except: pass
    
    msg = await context.bot.send_message(
        query.message.chat.id,
        "✉️ <b>CONVITE DE CLÃ</b>\n\nDigite o <b>NOME EXATO</b> do personagem que deseja convidar:",
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
        m = await update.message.reply_text(f"❌ Jogador '{target_name}' não encontrado.")
        context.user_data['last_bot_msg_id'] = m.message_id
        return ASKING_INVITEE

    target_id, target_data = target

    if target_data.get('clan_id'):
        await update.message.reply_text(f"❌ {target_name} já possui um clã.")
        return ConversationHandler.END

    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)

    # Prepara o convite
    kb_invite = [[
        InlineKeyboardButton("✅ Aceitar Convite", callback_data=f"clan_invite_accept:{clan_id}"),
        InlineKeyboardButton("❌ Recusar", callback_data="clan_invite_decline")
    ]]

    # Tenta enviar DM para o alvo
    target_chat = target_data.get("last_chat_id") or target_data.get("telegram_id_owner")
    
    if target_chat:
        try:
            await context.bot.send_message(
                chat_id=target_chat,
                text=f"📜 <b>CONVITE REAL: {clan.get('display_name')}</b>\n\nVocê foi convidado formalmente para se juntar a este clã.",
                reply_markup=InlineKeyboardMarkup(kb_invite),
                parse_mode="HTML"
            )
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ Convite enviado com sucesso para <b>{target_name}</b>.",
                parse_mode="HTML"
            )
        except Exception as e:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ Erro ao contatar {target_name}. O jogador bloqueou o bot ou não iniciou conversa."
            )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"⚠️ Não foi possível encontrar o chat de {target_name}."
        )
        
    return ConversationHandler.END

async def accept_invite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    clan_id = query.data.split(":")[1]
    
    try:
        # Entra direto
        await clan_manager.accept_application(clan_id, user_id)
        
        # Atualiza player
        pdata = await player_manager.get_player_data(user_id)
        pdata["clan_id"] = clan_id
        await player_manager.save_player_data(user_id, pdata)

        await query.edit_message_text("🎉 <b>Convite Aceito!</b>\nBem-vindo ao clã.", parse_mode="HTML")
    except Exception as e:
        await query.edit_message_text(f"❌ Erro ao aceitar: {e}")

async def decline_invite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("❌ Convite recusado.")


# --- TRANSFERÊNCIA DE LIDERANÇA ---
async def start_transfer_leadership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    try: await query.delete_message()
    except: pass
    
    msg = await context.bot.send_message(
        query.message.chat.id,
        "👑 <b>TRANSFERIR COROA</b>\n\nDigite o <b>NOME</b> do membro para torná-lo Líder:\n(Você se tornará General)",
        parse_mode="HTML"
    )
    context.user_data['last_bot_msg_id'] = msg.message_id
    return ASKING_TRANSFER_TARGET

async def receive_transfer_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_current_player_id(update, context)
    tname = update.message.text.strip()
    await _clean_chat(update, context)

    target = await player_manager.find_player_by_name(tname)
    if not target:
        m = await update.message.reply_text("❌ Membro não encontrado.")
        context.user_data['last_bot_msg_id'] = m.message_id
        return ASKING_TRANSFER_TARGET

    target_id, target_data = target
    p = await player_manager.get_player_data(user_id)

    try:
        await clan_manager.transfer_leadership(p.get("clan_id"), user_id, target_id)
        await context.bot.send_message(
            update.effective_chat.id, 
            f"✅ Liderança transferida para <b>{tname}</b> com sucesso.",
            parse_mode="HTML"
        )
    except Exception as e:
        await context.bot.send_message(update.effective_chat.id, f"❌ Erro: {e}")

    return ConversationHandler.END


# --- LOGO DO CLÃ ---
async def start_logo_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    try: await query.delete_message()
    except: pass
    
    msg = await context.bot.send_message(
        query.message.chat.id,
        "🖼️ <b>ALTERAR ESTANDARTE</b>\n\nEnvie uma <b>FOTO</b> ou <b>GIF</b> para ser o novo logo do clã:",
        parse_mode="HTML"
    )
    context.user_data['last_bot_msg_id'] = msg.message_id
    return ASKING_LOGO

async def receive_logo_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_current_player_id(update, context)
    msg = update.message
    
    fid, ftype = None, "photo"
    if msg.photo:
        fid = msg.photo[-1].file_id
    elif msg.video:
        fid = msg.video.file_id
        ftype = "video"
    elif msg.animation:
        fid = msg.animation.file_id
        ftype = "animation"
    elif msg.document: # Suporte a envio como arquivo
        fid = msg.document.file_id
        ftype = "video" if (msg.document.mime_type and "video" in msg.document.mime_type) else "photo"

    await _clean_chat(update, context)
    if not fid:
        m = await update.message.reply_text("❌ Formato inválido. Envie uma imagem.")
        context.user_data['last_bot_msg_id'] = m.message_id
        return ASKING_LOGO

    p = await player_manager.get_player_data(user_id)
    
    # Salva no DB
    await clan_manager.set_clan_media(p.get("clan_id"), user_id, {"file_id": fid, "type": ftype})

    # Mostra o resultado
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=fid,
        caption="✅ <b>Novo Estandarte Definido!</b>",
        parse_mode="HTML"
    )
    return ConversationHandler.END


# --- DISSOLVER CLÃ ---
async def warn_delete_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    kb = [[
        InlineKeyboardButton("🔥 DELETAR TUDO", callback_data='clan_delete_confirm'),
        InlineKeyboardButton("🔙 Cancelar", callback_data='clan_manage_menu')
    ]]
    await render_photo_or_text(
        update, context,
        "⚠️ <b>DISSOLVER CLÃ?</b>\n\nIsso apagará o clã, o banco e todos os registros permanentemente.\nEssa ação não pode ser desfeita.",
        InlineKeyboardMarkup(kb)
    )

async def perform_delete_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = get_current_player_id(update, context)
    p = await player_manager.get_player_data(uid)
    
    try:
        await clan_manager.delete_clan(p.get("clan_id"), uid)
        p["clan_id"] = None
        await player_manager.save_player_data(uid, p)
        
        await query.answer("Clã dissolvido.")
        await query.edit_message_text("🚫 <b>O Clã foi dissolvido.</b>", parse_mode="HTML")
    except Exception as e:
        await query.edit_message_text(f"Erro: {e}")


# ==============================================================================
# HANDLERS EXPORTADOS
# ==============================================================================
clan_manage_menu_handler = CallbackQueryHandler(show_clan_management_menu, pattern=r'^clan_manage_menu$')

# Listas
clan_view_members_handler = CallbackQueryHandler(show_members_list, pattern=r'^clan_view_members$')
clan_profile_handler = CallbackQueryHandler(show_member_profile, pattern=r'^clan_profile:')
clan_setrank_menu_handler = CallbackQueryHandler(show_rank_selection_menu, pattern=r'^clan_setrank_menu:')
clan_do_rank_handler = CallbackQueryHandler(perform_rank_change, pattern=r'^clan_do_rank:')

# Limpeza
clan_cleanup_menu_handler = CallbackQueryHandler(show_cleanup_menu, pattern=r'^clan_cleanup_menu$')
clan_cleanup_apps_handler = CallbackQueryHandler(do_cleanup_apps, pattern=r'^clan_cleanup_apps$')
clan_cleanup_members_handler = CallbackQueryHandler(do_cleanup_members, pattern=r'^clan_cleanup_members$')

# Ações Membros
clan_kick_ask_handler = CallbackQueryHandler(warn_kick_member, pattern=r'^clan_kick_ask:')
clan_kick_do_handler = CallbackQueryHandler(do_kick_member, pattern=r'^clan_kick_do:')
clan_kick_menu_handler = CallbackQueryHandler(show_members_list, pattern=r'^clan_kick_menu$')

# Ações Gerais
clan_leave_warn_handler = CallbackQueryHandler(warn_leave_clan, pattern=r'^clan_leave_ask$')
clan_leave_do_handler = CallbackQueryHandler(do_leave_clan, pattern=r'^clan_leave_perform$')
clan_delete_warn_handler = CallbackQueryHandler(warn_delete_clan, pattern=r'^clan_delete_ask$')
clan_delete_do_handler = CallbackQueryHandler(perform_delete_clan, pattern=r'^clan_delete_confirm$')

# Convites (Callbacks de Aceite)
clan_invite_accept_handler = CallbackQueryHandler(accept_invite_callback, pattern=r'^clan_invite_accept:')
clan_invite_decline_handler = CallbackQueryHandler(decline_invite_callback, pattern=r'^clan_invite_decline$')

# Conversations
invite_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_invite_conversation, pattern=r'^clan_invite_start$')],
    states={ASKING_INVITEE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_invitee_name)]},
    fallbacks=[CommandHandler('cancelar', cancel_op)],
    per_chat=True
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
clan_promote_handler = CallbackQueryHandler(
    lambda u, c: u.callback_query.answer("Use a opção 'Alterar Cargo' no perfil."),
    pattern=r'^clan_promote:'
)

clan_demote_handler = CallbackQueryHandler(
    lambda u, c: u.callback_query.answer("Use a opção 'Alterar Cargo' no perfil."),
    pattern=r'^clan_demote:'
)