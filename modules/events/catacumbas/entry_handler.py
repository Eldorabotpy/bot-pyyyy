# modules/events/catacumbas/entry_handler.py
# (VERSÃO CORRIGIDA: Botão Atualizar + Tratamento de Erro de Edição)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters, CommandHandler
from modules import player_manager
from modules.auth_utils import get_current_player_id
from . import combat_handler

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
        # Compara como string para garantir segurança (int vs str/ObjectId)
        role = "👑 Líder" if str(pid) == str(leader_id) else "🛡️ Membro"
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
        # Líder também pode querer atualizar se a auto-atualização falhar
        kb.append([InlineKeyboardButton("🔄 Atualizar Lista", callback_data="cat_refresh_lobby")])
        kb.append([InlineKeyboardButton("❌ Desmanchar Sala", callback_data="cat_leave_lobby")])
    else:
        # Botão ESSENCIAL para membros verem se entrou mais gente
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
    chat_id = lobby.get('chat_id') # Usa o chat_id salvo
    
    if not chat_id: chat_id = leader_id # Fallback
    
    if chat_id and msg_id:
        text = _format_lobby_status(lobby)
        kb = _lobby_keyboard(is_leader=True)
        try:
            # Tenta editar a legenda (Caption) se for foto
            await context.bot.edit_message_caption(
                chat_id=chat_id,
                message_id=msg_id,
                caption=text,
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode="Markdown"
            )
        except Exception as e:
            # logger.warning(f"Falha ao editar caption do líder: {e}")
            try:
                # Se falhar (ex: era texto puro), tenta editar texto
                await context.bot.edit_message_text(
                    chat_id=chat_id,
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
                            chat_id, 
                            f"🔔 **{new_player_name}** entrou na sala!\n(Use o botão Atualizar ou /evt_cat_menu)"
                        )
                    except: pass

# ==============================================================================
# 🎮 HANDLERS PRINCIPAIS
# ==============================================================================

async def menu_catacumba_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    from modules.auth_utils import get_current_player_id
    raw_id = get_current_player_id(update, context)
    
    # Fallback para o ID do Telegram se a auth falhar
    if not raw_id:
        raw_id = str(update.effective_user.id) if update.effective_user else None
        
    if not raw_id:
        return # Erro crítico, não consegue identificar o utilizador
        
    user_id = str(raw_id)
    
    # 🧹 LIMPEZA AUTOMÁTICA DE SEGURANÇA SEMPRE QUE ABRE O MENU
    # Se o jogador abrir o menu principal, presumimos que não quer estar numa sala antiga
    raid_manager.force_clear_player(user_id)
    
    # ... Resto da função do menu continua igual ...
    kb = [
        [InlineKeyboardButton("🔑 Criar Sala (Gasta Chave)", callback_data="cat_create_room")],
        [InlineKeyboardButton("🛡️ Entrar com Código", callback_data="cat_join_input")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="back_to_kingdom")]
    ]
    # Certifica-te que as MEDIA_KEYS usam .get() para não dar erro
    media_key = config.MEDIA_KEYS.get("menu_banner", "default_banner")
    intro_text = config.TEXTS.get("intro", "Menu das Catacumbas")
    
    await send_event_interface(update, context, intro_text, kb, media_key)
    
       
async def refresh_lobby_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback do botão ATUALIZAR STATUS."""
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    
    lobby = raid_manager.get_player_lobby(user_id)
    if not lobby:
        await query.answer("A sala foi desfeita.")
        await menu_catacumba_main(update, context)
        return
        
    text = _format_lobby_status(lobby)
    # Comparação segura
    is_leader = (str(lobby['leader_id']) == str(user_id))
    kb = _lobby_keyboard(is_leader=is_leader)
    
    try:
        # Tenta editar a legenda primeiro
        await query.edit_message_caption(caption=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        await query.answer("Lista atualizada!")
    except Exception:
        try:
            # Se falhar (não era mídia), edita texto
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
            await query.answer("Lista atualizada!")
        except:
            # Se texto e legenda forem iguais, Telegram rejeita edição
            await query.answer("Já está atualizado.")

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

# =====================================================================
# FUNÇÃO AUXILIAR DE SEGURANÇA (Podes colocar no topo do ficheiro)
# =====================================================================
async def _get_safe_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Busca o ID do jogador com fallback para a Base de Dados."""
    user_id = None
    try:
        from modules.auth_utils import get_current_player_id
        raw = get_current_player_id(update, context)
        if raw and str(raw) != "None":
            user_id = str(raw)
    except Exception:
        pass
        
    if not user_id:
        telegram_id = update.effective_user.id
        from modules.database import get_collection
        doc = await get_collection("players").find_one({"telegram_id": telegram_id})
        if doc:
            user_id = str(doc["_id"])
            
    return user_id

# =====================================================================
# FUNÇÕES ATUALIZADAS
# =====================================================================

async def create_room_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    
    # Usa a nossa nova busca blindada
    user_id = await _get_safe_id(update, context)
    
    if not user_id:
        await query.answer("Erro crítico: Conta não localizada na Base de Dados.", show_alert=True)
        return
        
    # Limpeza forçada de Raids Ativas
    for code, session in list(raid_manager.ACTIVE_RAIDS.items()):
        if user_id in session.get("players", {}):
            del session["players"][user_id]
            if len(session["players"]) == 0:
                del raid_manager.ACTIVE_RAIDS[code]
            break

    code = raid_manager.create_lobby(user_id, user.first_name)
    
    if code:
        lobby = raid_manager.LOBBIES[code]
        text = _format_lobby_status(lobby)
        kb = _lobby_keyboard(is_leader=True)
        
        msg = await send_event_interface(update, context, text, kb, config.MEDIA_KEYS.get("lobby_screen"))
        if msg:
            raid_manager.register_lobby_message(code, msg.message_id, msg.chat.id)
    else:
        await query.answer("Erro inesperado ao criar sala.", show_alert=True)


async def start_raid_run_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Usa a nossa nova busca blindada
    user_id = await _get_safe_id(update, context)
    
    if not user_id:
        await query.answer("Erro de autenticação.", show_alert=True)
        return

    # Tenta iniciar a raid
    session = await raid_manager.start_raid_from_lobby(user_id)
    if not session:
        await query.answer("Apenas o líder pode iniciar, ou a sala não tem jogadores suficientes.", show_alert=True)
        return
        
    await query.answer("⚔️ Raid Iniciada!")
    
    try: await update.effective_message.delete()
    except: pass
    
    from . import combat_handler
    await combat_handler.refresh_battle_interface(update, context, session, user_id)
    
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

    # ==========================================================
    # 🔐 BUSCA BLINDADA DE ID DO JOGADOR
    # ==========================================================
    user_id = None
    
    # 1. Tenta a via normal (auth_utils)
    try:
        from modules.auth_utils import get_current_player_id
        raw_id = get_current_player_id(update, context)
        if raw_id and str(raw_id) != "None":
            user_id = str(raw_id)
    except ImportError:
        pass
        
    # 2. SE FALHAR: Faz uma busca direta na Base de Dados pelo Telegram ID
    if not user_id:
        telegram_id = update.effective_user.id
        from modules.database import get_collection
        players_col = get_collection("players")
        
        # Procura um jogador que tenha este telegram_id
        player_doc = await players_col.find_one({"telegram_id": telegram_id})
        if player_doc:
            user_id = str(player_doc["_id"])
            print(f"[DEBUG-CATACUMBAS] Recuperação de ID bem sucedida via Telegram ID: {user_id}")
        else:
            # Fallback final (se o sistema não usar ObjectID mas sim o Telegram ID direto)
            user_id = str(telegram_id)
            print(f"[DEBUG-CATACUMBAS] Fallback para Telegram ID direto: {user_id}")

    # ==========================================================
    
    # Limpa forçadamente o estado antigo
    raid_manager.force_clear_player(user_id)

    # Tenta entrar
    res = raid_manager.join_lobby_by_code(user_id, user.first_name, text)
    
    try: await update.message.delete()
    except: pass
    
    chat_id = update.effective_chat.id

    if res == "success":
        await _update_leader_interface(context, text, new_player_name=user.first_name)
        
        lobby = raid_manager.LOBBIES.get(text)
        if lobby:
            formatted_text = _format_lobby_status(lobby)
            kb = _lobby_keyboard(is_leader=False)
            media_key = config.MEDIA_KEYS.get("lobby_screen", "default_media")
            await send_event_interface(update, context, formatted_text, kb, media_key)
        
    elif res == "not_found":
        await context.bot.send_message(chat_id, "🚫 Sala não encontrada.")
    elif res == "full":
        await context.bot.send_message(chat_id, "🚫 Sala cheia!")
    elif res == "started":
        await context.bot.send_message(chat_id, "🚫 A Raid já começou.")
    elif res == "already_in":
        await context.bot.send_message(chat_id, "⚠️ Você já está nesta sala.")
               
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
    CommandHandler("debug_key", debug_give_key_cb),
    CallbackQueryHandler(combat_handler.process_player_attack, pattern="^cat_act_attack$"),
    CallbackQueryHandler(combat_handler.refresh_combat_cb, pattern="^cat_combat_refresh$"), # <-- ADICIONE ESTA LINHA
    CallbackQueryHandler(combat_handler.leave_active_raid_cb, pattern="^cat_leave_active$"),
    
]