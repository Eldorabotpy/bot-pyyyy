# modules/events/catacumbas/entry_handler.py

import logging
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters, CommandHandler
from modules import player_manager
from modules.auth_utils import get_current_player_id


try:
    from modules import file_id_manager as media_ids
except ImportError:
    media_ids = None

from . import config, raid_manager 

logger = logging.getLogger(__name__)

# ==============================================================================
# 🛠️ HELPERS VISUAIS E DE TEXTO
# ==============================================================================

def escape_markdown(text: str) -> str:
    if not text: return ""
    return text.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")

async def send_event_interface(update, context, text, keyboard, media_key=None):
    chat_id = update.effective_chat.id
    
    # Tenta apagar msg anterior para evitar flood
    if update.callback_query:
        try: await update.callback_query.delete_message()
        except: pass

    reply_markup = InlineKeyboardMarkup(keyboard)
    file_data = None
    
    if media_ids and media_key:
        try: file_data = media_ids.get_file_data(media_key)
        except: pass

    sent_msg = None
    try:
        if file_data and file_data.get("id"):
            media_type = (file_data.get("type") or "photo").lower()
            if media_type == "video":
                sent_msg = await context.bot.send_video(chat_id, file_data["id"], caption=text, reply_markup=reply_markup, parse_mode="Markdown")
            else:
                sent_msg = await context.bot.send_photo(chat_id, file_data["id"], caption=text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            sent_msg = await context.bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="Markdown")
        return sent_msg
    except Exception as e:
        logger.error(f"Erro UI Evento: {e}")
        try: 
            return await context.bot.send_message(chat_id, text.replace("*", ""), reply_markup=reply_markup)
        except: return None

# ==============================================================================
# 🏰 LÓGICA VISUAL DO LOBBY (SALA DE ESPERA)
# ==============================================================================

def _format_lobby_status(lobby: dict) -> str:
    """Gera o texto com a lista de jogadores na sala."""
    code = lobby['code']
    players = lobby['players'] # dict {id: name}
    leader_id = lobby['leader_id']
    
    count = len(players)
    min_p = config.MIN_PLAYERS
    max_p = config.MAX_PLAYERS
    
    status_emoji = "✅" if count >= min_p else "⚠️"
    
    txt = (
        f"🏰 **SALA DE REUNIÃO**\n"
        f"🔑 Código: `{code}`\n"
        f"Compartilhe este código para recrutar aliados.\n\n"
        f"👥 **Grupo ({count}/{max_p}):**\n"
    )
    
    for pid, name in players.items():
        role = "👑 Líder" if pid == leader_id else "🛡️ Membro"
        safe_name = escape_markdown(name)
        txt += f" - {role}: {safe_name}\n"

    txt += "\n"
    if count < min_p:
        txt += f"{status_emoji} Aguardando +{min_p - count} guerreiros (Mín: {min_p})..."
    else:
        txt += f"{status_emoji} O grupo está pronto para a batalha!"
        
    return txt

def _lobby_keyboard(is_leader: bool):
    kb = []
    if is_leader:
        kb.append([InlineKeyboardButton("⚔️ INICIAR RAID", callback_data="cat_start_run")])
        kb.append([InlineKeyboardButton("❌ Desmanchar Sala", callback_data="cat_leave_lobby")])
    else:
        # Botão de atualizar para o membro ver se o líder começou
        kb.append([InlineKeyboardButton("🔄 Atualizar Status", callback_data="cat_refresh_lobby")])
        kb.append([InlineKeyboardButton("🚪 Sair do Grupo", callback_data="cat_leave_lobby")])
    return kb

async def _update_leader_interface(context, code: str, new_player_name: str = None):
    """
    Tenta atualizar a mensagem do Líder.
    Se falhar, envia uma mensagem de texto avisando da entrada.
    """
    lobby = raid_manager.LOBBIES.get(code)
    if not lobby: return
    
    leader_id = lobby.get('leader_id')
    msg_id = lobby.get('ui_message_id')
    
    if leader_id and msg_id:
        text = _format_lobby_status(lobby)
        kb = _lobby_keyboard(is_leader=True)
        try:
            # Tenta editar a legenda (Caption) se for foto
            await context.bot.edit_message_caption(
                chat_id=leader_id,
                message_id=msg_id,
                caption=text,
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Falha ao editar caption do líder: {e}")
            try:
                # Se falhar (ex: era texto puro), tenta editar texto
                await context.bot.edit_message_text(
                    chat_id=leader_id,
                    message_id=msg_id,
                    text=text,
                    reply_markup=InlineKeyboardMarkup(kb),
                    parse_mode="Markdown"
                )
            except Exception as e2:
                # Se tudo falhar, avisa o líder com uma nova mensagem
                if new_player_name:
                    try:
                        await context.bot.send_message(
                            leader_id, 
                            f"🔔 **{new_player_name}** entrou na sala!\n(Use /evt_cat_menu para ver o lobby atualizado)"
                        )
                    except: pass

# ==============================================================================
# 🎮 HANDLERS PRINCIPAIS
# ==============================================================================

async def menu_catacumba_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    existing_lobby = raid_manager.get_player_lobby(update.effective_user.id)
    if existing_lobby:
        text = _format_lobby_status(existing_lobby)
        kb = _lobby_keyboard(is_leader=(existing_lobby['leader_id'] == update.effective_user.id))
        
        msg = await send_event_interface(update, context, text, kb, config.MEDIA_KEYS["lobby_screen"])
        if msg:
            raid_manager.register_lobby_message(existing_lobby['code'], msg.message_id)
        return

    kb = [
        [InlineKeyboardButton("🔑 Criar Sala (Gasta Chave)", callback_data="cat_create_room")],
        [InlineKeyboardButton("🛡️ Entrar com Código", callback_data="cat_join_input")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="back_to_kingdom")]
    ]
    await send_event_interface(update, context, config.TEXTS["intro"], kb, config.MEDIA_KEYS["menu_banner"])

async def create_room_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    
    # Checagem de Chave
    pdata = await player_manager.get_player_data(user.id)
    inv = pdata.get("inventory", {})
    
    # Verifica chave (comente se estiver testando sem chave)
    if inv.get(config.REQUIRED_KEY_ITEM, 0) < 1:
        await query.answer("Sem chaves! Use /debug_key para testar.", show_alert=True)
        return

    code = raid_manager.create_lobby(user.id, user.first_name)
    if code:
        # Consome chave
        inv[config.REQUIRED_KEY_ITEM] = inv.get(config.REQUIRED_KEY_ITEM, 1) - 1
        await player_manager.save_player_data(user.id, pdata)
        
        lobby = raid_manager.LOBBIES[code]
        text = _format_lobby_status(lobby)
        kb = _lobby_keyboard(is_leader=True)
        
        msg = await send_event_interface(update, context, text, kb, config.MEDIA_KEYS["lobby_screen"])
        if msg:
            raid_manager.register_lobby_message(code, msg.message_id)
    else:
        await query.answer("Erro ao criar sala.", show_alert=True)

async def refresh_lobby_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Membros podem atualizar manualmente para ver se entrou gente."""
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    
    lobby = raid_manager.get_player_lobby(user_id)
    if not lobby:
        await query.answer("A sala foi desfeita.")
        await menu_catacumba_main(update, context)
        return
        
    text = _format_lobby_status(lobby)
    kb = _lobby_keyboard(is_leader=(lobby['leader_id'] == user_id))
    
    try:
        await query.edit_message_caption(caption=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        await query.answer("Atualizado!")
    except Exception:
        try:
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except:
            await query.answer("Sem mudanças visuais.")

async def leave_lobby_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    
    lobby = raid_manager.get_player_lobby(user_id)
    code = lobby['code'] if lobby else None
    
    raid_manager.leave_lobby(user_id)
    
    await query.answer("Você saiu.")
    await menu_catacumba_main(update, context)
    
    # Atualiza o líder que alguém saiu
    if code and code in raid_manager.LOBBIES:
        await _update_leader_interface(context, code)

async def start_raid_run_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from . import combat_handler 
    query = update.callback_query
    user = update.effective_user
    
    session = raid_manager.start_raid_from_lobby(user.id)
    if not session:
        await query.answer(f"Erro: Mínimo {config.MIN_PLAYERS} jogadores ou você não é líder.", show_alert=True)
        return

    await query.answer("🚀 INICIANDO!")
    
    # 1. Atualiza tela do Líder
    await combat_handler.refresh_battle_interface(update, context, session, user.id)
    
    # 2. Notifica todos os outros
    for pid in session["players"]:
        if pid != user.id:
            try:
                await context.bot.send_message(
                    pid, 
                    "⚔️ **O LÍDER ENTROU NA CATACUMBA!**\nAperte abaixo para entrar no combate.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏃‍♂️ ENTRAR AGORA", callback_data="cat_combat_refresh")]])
                )
            except: pass

# ==============================================================================
# ⌨️ INPUT DE CÓDIGO
# ==============================================================================

async def ask_for_code_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text(
        "✍️ **Digite o Código da Sala (5 Letras):**",
        reply_markup=ForceReply(selective=True)
    )

async def process_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    user = update.effective_user
    
    if len(text) != 5: return 

    # Tenta entrar na sala
    res = raid_manager.join_lobby_by_code(user.id, user.first_name, text)
    
    try: await update.message.delete() # Limpa o código digitado
    except: pass
    
    if res == "success":
        # 1. Tenta atualizar a tela do Líder IMEDIATAMENTE
        # Passamos o nome do user para notificação de fallback
        await _update_leader_interface(context, text, new_player_name=user.first_name)
        
        # 2. Mostra a sala para quem acabou de entrar
        lobby = raid_manager.LOBBIES[text]
        formatted_text = _format_lobby_status(lobby)
        kb = _lobby_keyboard(is_leader=False)
        
        await send_event_interface(update, context, formatted_text, kb, config.MEDIA_KEYS["lobby_screen"])
        
    elif res == "not_found":
        await context.bot.send_message(user.id, "🚫 Sala não encontrada.")
    elif res == "full":
        await context.bot.send_message(user.id, "🚫 Sala cheia!")
    elif res == "started":
        await context.bot.send_message(user.id, "🚫 A Raid já começou.")
    elif res == "already_in":
        await context.bot.send_message(user.id, "⚠️ Você já está nesta sala.")

# ==============================================================================
# 🔧 DEBUG
# ==============================================================================
async def debug_give_key_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_current_player_id(update, context)
    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.setdefault("inventory", {})
    inv[config.REQUIRED_KEY_ITEM] = inv.get(config.REQUIRED_KEY_ITEM, 0) + 10
    await player_manager.save_player_data(user_id, pdata)
    await update.message.reply_text(f"🔧 +10 {config.REQUIRED_KEY_ITEM}")

handlers = [
    CallbackQueryHandler(menu_catacumba_main, pattern="^evt_cat_menu$"),
    CallbackQueryHandler(create_room_cb, pattern="^cat_create_room$"),
    CallbackQueryHandler(refresh_lobby_cb, pattern="^cat_refresh_lobby$"),
    CallbackQueryHandler(leave_lobby_cb, pattern="^cat_leave_lobby$"),
    CallbackQueryHandler(start_raid_run_cb, pattern="^cat_start_run$"),
    CallbackQueryHandler(ask_for_code_cb, pattern="^cat_join_input$"),
    MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, process_code_input),
    CommandHandler("debug_key", debug_give_key_cb)
]