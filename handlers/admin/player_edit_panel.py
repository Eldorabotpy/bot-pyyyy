# handlers/admin/player_edit_panel.py

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, 
    ConversationHandler, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    filters
)
from telegram.constants import ParseMode

from modules import player_manager, game_data
from config import ADMIN_LIST # Importe a sua lista de IDs de administradores

logger = logging.getLogger(__name__)

# Definição dos estados da conversa
(
    STATE_GET_USER_ID, 
    STATE_SHOW_MENU, 
    STATE_AWAIT_PROFESSION, 
    STATE_AWAIT_PROF_LEVEL, 
    STATE_AWAIT_CHAR_LEVEL
) = range(5)

# --- Funções Auxiliares (Helpers) ---

def _get_player_info_text(pdata: dict) -> str:
    """Monta o texto de status atual do jogador."""
    try:
        char_level = int(pdata.get('level', 1))
        prof_type = (pdata.get('profession', {}) or {}).get('type', 'Nenhuma')
        prof_level = int((pdata.get('profession', {}) or {}).get('level', 1))
        char_name = pdata.get('character_name', 'Sem Nome')
        user_id = pdata.get('user_id', '???')

        # Busca o nome de exibição da profissão
        prof_display = (game_data.PROFESSIONS_DATA.get(prof_type) or {}).get('display_name', prof_type)

        return (
            f"👤 <b>Editando Jogador:</b> {char_name} (ID: <code>{user_id}</code>)\n"
            "----------------------------------\n"
            f"🎖️ <b>Nível de Personagem:</b> {char_level}\n"
            f"⚒️ <b>Profissão:</b> {prof_display}\n"
            f"📊 <b>Nível de Profissão:</b> {prof_level}\n"
            "----------------------------------\n"
            "O que você deseja alterar?"
        )
    except Exception as e:
        logger.error(f"Erro ao montar _get_player_info_text: {e}")
        return "Erro ao carregar dados. O que deseja alterar?"

async def _send_or_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Envia ou edita a mensagem principal do menu de edição."""
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚒️ Alterar Profissão", callback_data="edit_prof_type")],
        [InlineKeyboardButton("📊 Definir Nível de Profissão", callback_data="edit_prof_lvl")],
        [InlineKeyboardButton("🎖️ Definir Nível de Personagem", callback_data="edit_char_lvl")],
        [InlineKeyboardButton("❌ Cancelar Edição", callback_data="edit_cancel")]
    ])
    
    query = update.callback_query
    if query:
        try:
            await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
        except Exception:
            # Fallback se a mensagem não puder ser editada (ex: foi excluída)
            await query.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        # Se for a primeira vez (via /editplayer)
        await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)

# --- Etapas da Conversa ---

async def admin_edit_player_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia a conversa para editar um jogador."""
    await update.message.reply_text(
        "Insira o <b>ID do usuário</b> que você deseja editar:",
        parse_mode=ParseMode.HTML
    )
    return STATE_GET_USER_ID

async def admin_get_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe o ID do usuário e mostra o menu de edição."""
    try:
        target_user_id = int(update.message.text)
    except ValueError:
        await update.message.reply_text("ID inválido. Deve ser um número. Tente novamente:")
        return STATE_GET_USER_ID

    pdata = player_manager.get_player_data(target_user_id)
    if not pdata:
        await update.message.reply_text(f"Jogador com ID <code>{target_user_id}</code> não encontrado. Conversa encerrada.", parse_mode=ParseMode.HTML)
        return ConversationHandler.END

    # Salva o ID do jogador-alvo no context para uso futuro
    context.user_data['edit_target_id'] = target_user_id
    
    info_text = _get_player_info_text(pdata)
    await _send_or_edit_menu(update, context, info_text)
    
    return STATE_SHOW_MENU

async def admin_show_menu_dispatch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mostra o menu principal (usado para retornar ao menu)."""
    query = update.callback_query
    if query:
        await query.answer()

    target_user_id = context.user_data.get('edit_target_id')
    if not target_user_id:
        await query.edit_message_text("Erro: ID do jogador alvo perdido. Encerrando.")
        return ConversationHandler.END

    pdata = player_manager.get_player_data(target_user_id)
    info_text = _get_player_info_text(pdata)
    await _send_or_edit_menu(update, context, info_text)
    
    return STATE_SHOW_MENU

async def admin_choose_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa o botão de ação escolhido pelo admin."""
    query = update.callback_query
    await query.answer()
    
    action = query.data

    if action == "edit_prof_type":
        # Monta o teclado com todas as profissões disponíveis
        kb_rows = []
        for prof_id, prof_data in game_data.PROFESSIONS_DATA.items():
            kb_rows.append([InlineKeyboardButton(
                f"{prof_data.get('display_name', prof_id)} ({prof_data.get('category', 'N/A')})",
                callback_data=f"set_prof:{prof_id}"
            )])
        kb_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="edit_back_menu")])
        
        await query.edit_message_text(
            "Escolha a <b>nova profissão</b> para o jogador:",
            reply_markup=InlineKeyboardMarkup(kb_rows),
            parse_mode=ParseMode.HTML
        )
        return STATE_AWAIT_PROFESSION

    elif action == "edit_prof_lvl":
        await query.edit_message_text("Digite o <b>novo Nível de Profissão</b> (ex: 10):", parse_mode=ParseMode.HTML)
        return STATE_AWAIT_PROF_LEVEL
        
    elif action == "edit_char_lvl":
        await query.edit_message_text("Digite o <b>novo Nível de Personagem</b> (ex: 50):", parse_mode=ParseMode.HTML)
        return STATE_AWAIT_CHAR_LEVEL
        
    elif action == "edit_cancel":
        await query.edit_message_text("Edição cancelada.")
        context.user_data.pop('edit_target_id', None)
        return ConversationHandler.END

    return STATE_SHOW_MENU

async def admin_set_profession_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Define a nova profissão do jogador."""
    query = update.callback_query
    await query.answer()
    
    target_user_id = context.user_data.get('edit_target_id')
    if not target_user_id:
        await query.edit_message_text("Erro: ID do jogador alvo perdido. Encerrando.")
        return ConversationHandler.END

    new_prof_id = query.data.replace("set_prof:", "")
    if new_prof_id not in game_data.PROFESSIONS_DATA:
        await query.answer("Profissão inválida.", show_alert=True)
        return STATE_AWAIT_PROFESSION

    pdata = player_manager.get_player_data(target_user_id)
    
    # Define a profissão, resetando nível e XP
    pdata.setdefault('profession', {})
    pdata['profession']['type'] = new_prof_id
    pdata['profession']['level'] = 1
    pdata['profession']['xp'] = 0
    
    player_manager.save_player_data(target_user_id, pdata)
    
    await query.answer("Profissão alterada!")
    
    # Volta ao menu principal
    info_text = _get_player_info_text(pdata)
    await _send_or_edit_menu(update, context, info_text)
    return STATE_SHOW_MENU

async def admin_set_char_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Define o novo nível de personagem."""
    try:
        new_level = int(update.message.text)
        if new_level <= 0:
            raise ValueError("Nível deve ser positivo")
    except ValueError:
        await update.message.reply_text("Valor inválido. Digite um número (ex: 50).")
        return STATE_AWAIT_CHAR_LEVEL

    target_user_id = context.user_data.get('edit_target_id')
    if not target_user_id:
        await update.message.reply_text("Erro: ID do jogador alvo perdido. Encerrando.")
        return ConversationHandler.END

    pdata = player_manager.get_player_data(target_user_id)
    
    # Define o nível e reseta o XP
    pdata['level'] = new_level
    pdata['xp'] = 0
    
    player_manager.save_player_data(target_user_id, pdata)
    
    info_text = _get_player_info_text(pdata)
    await update.message.reply_text(f"✅ Nível de personagem atualizado para <b>{new_level}</b>.", parse_mode=ParseMode.HTML)
    await _send_or_edit_menu(update, context, info_text)
    return STATE_SHOW_MENU

async def admin_set_prof_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Define o novo nível de profissão."""
    try:
        new_level = int(update.message.text)
        if new_level <= 0:
            raise ValueError("Nível deve ser positivo")
    except ValueError:
        await update.message.reply_text("Valor inválido. Digite um número (ex: 10).")
        return STATE_AWAIT_PROF_LEVEL

    target_user_id = context.user_data.get('edit_target_id')
    if not target_user_id:
        await update.message.reply_text("Erro: ID do jogador alvo perdido. Encerrando.")
        return ConversationHandler.END

    pdata = player_manager.get_player_data(target_user_id)
    
    # Define o nível e reseta o XP da profissão
    pdata.setdefault('profession', {})
    if not pdata['profession'].get('type'):
        await update.message.reply_text("Erro: O jogador não tem uma profissão definida. Altere a profissão primeiro.")
    else:
        pdata['profession']['level'] = new_level
        pdata['profession']['xp'] = 0
        player_manager.save_player_data(target_user_id, pdata)
        await update.message.reply_text(f"✅ Nível de profissão atualizado para <b>{new_level}</b>.", parse_mode=ParseMode.HTML)

    info_text = _get_player_info_text(pdata)
    await _send_or_edit_menu(update, context, info_text)
    return STATE_SHOW_MENU

async def admin_edit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a conversa."""
    query = update.callback_query
    if query:
        await query.edit_message_text("Edição cancelada.")
    else:
        await update.message.reply_text("Edição cancelada.")
        
    context.user_data.pop('edit_target_id', None)
    return ConversationHandler.END

# --- Montagem do Handler ---

def create_admin_edit_player_handler() -> ConversationHandler:
    """Cria o ConversationHandler para o painel de edição de jogador."""
    
    admin_filter = filters.User(ADMIN_LIST)
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("editplayer", admin_edit_player_start, filters=admin_filter)],
        states={
            STATE_GET_USER_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, admin_get_user_id)
            ],
            STATE_SHOW_MENU: [
                CallbackQueryHandler(admin_choose_action, pattern=r"^edit_(prof_type|prof_lvl|char_lvl|cancel)$")
            ],
            STATE_AWAIT_PROFESSION: [
                CallbackQueryHandler(admin_set_profession_type, pattern=r"^set_prof:"),
                CallbackQueryHandler(admin_show_menu_dispatch, pattern=r"^edit_back_menu$")
            ],
            STATE_AWAIT_CHAR_LEVEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, admin_set_char_level)
            ],
            STATE_AWAIT_PROF_LEVEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, admin_set_prof_level)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(admin_edit_cancel, pattern=r"^edit_cancel$"),
            CommandHandler("cancel", admin_edit_cancel, filters=admin_filter)
        ],
        per_message=False
    )
    return conv_handler