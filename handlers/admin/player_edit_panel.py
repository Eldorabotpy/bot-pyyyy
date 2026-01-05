# handlers/admin/player_edit_panel.py
import logging
import time
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
from telegram.error import BadRequest

# Imports do Core
from handlers.admin.utils import parse_hybrid_id, ADMIN_LIST
from modules.player.core import get_player_data, save_player_data
from modules.player.queries import find_player_by_name
from modules import game_data

logger = logging.getLogger(__name__)

# Definição dos estados
(
    STATE_GET_USER_ID, 
    STATE_SHOW_MENU, 
    STATE_AWAIT_PROFESSION, 
    STATE_AWAIT_PROF_LEVEL, 
    STATE_AWAIT_CHAR_LEVEL,
    STATE_AWAIT_CLASS
) = range(6)

# --- Helpers ---
def _get_player_info_text(pdata: dict) -> str:
    """Monta o texto de status atual do jogador."""
    try:
        char_level = int(pdata.get('level', 1))
        prof_type = (pdata.get('profession', {}) or {}).get('type', 'Nenhuma')
        prof_level = int((pdata.get('profession', {}) or {}).get('level', 1))
        char_name = pdata.get('character_name', 'Sem Nome')
        user_id = pdata.get('user_id', '???')
        
        class_key = pdata.get('class_key') or pdata.get('class', 'Nenhuma')
        # Tenta pegar display name do game_data, fallback para o próprio key
        class_info = (game_data.CLASSES_DATA.get(str(class_key).lower()) or {})
        class_display = class_info.get('display_name', str(class_key).capitalize())

        prof_display = (game_data.PROFESSIONS_DATA.get(prof_type) or {}).get('display_name', prof_type)

        return (
            f"👤 <b>Editando Jogador:</b> {char_name}\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            "----------------------------------\n"
            f"👑 <b>Classe:</b> {class_display}\n"
            f"🎖️ <b>Nível de Personagem:</b> {char_level}\n"
            f"⚒️ <b>Profissão:</b> {prof_display}\n"
            f"📊 <b>Nível de Profissão:</b> {prof_level}\n"
            "----------------------------------\n"
            "O que você deseja alterar?"
        )
    except Exception as e:
        logger.error(f"Erro no _get_player_info_text: {e}")
        return "Erro ao carregar dados. O que deseja alterar?"

async def _send_or_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Envia ou edita a mensagem do menu."""
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("👑 Alterar Classe", callback_data="edit_char_class")],
        [InlineKeyboardButton("⚒️ Alterar Profissão", callback_data="edit_prof_type")],
        [InlineKeyboardButton("📊 Definir Nível Profissão", callback_data="edit_prof_lvl")],
        [InlineKeyboardButton("🎖️ Definir Nível Personagem", callback_data="edit_char_lvl")],
        [InlineKeyboardButton("❌ Sair", callback_data="edit_cancel")]
    ])

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
        except Exception:
            # Se falhar (ex: msg muito antiga), envia nova
            if update.effective_chat:
                await context.bot.send_message(update.effective_chat.id, text, reply_markup=kb, parse_mode=ParseMode.HTML)
    elif update.message:
        await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)

# --- Handlers de Início ---

async def admin_edit_player_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = "📝 <b>Modo de Edição</b>\n\nEnvie o <b>ID</b> ou <b>Nome do Personagem</b>:"
    
    if update.callback_query:
        await update.callback_query.answer()
        await _send_or_edit_menu(update, context, text) # Reutiliza lógica de envio se possível, mas aqui queremos pedir texto
        # Na verdade, como pedimos texto, melhor editar para apenas texto sem botões (ou botão cancelar)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="edit_cancel")]])
        try:
            await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
        except:
            await context.bot.send_message(update.effective_chat.id, text, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)

    return STATE_GET_USER_ID

async def admin_get_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()
    pdata = None
    target_id = None

    # 1. Tenta por ID (Híbrido)
    parsed_id = parse_hybrid_id(user_input)
    if parsed_id:
        pdata = await get_player_data(parsed_id)
        if pdata:
            target_id = parsed_id

    # 2. Se não achou, tenta por Nome
    if not pdata:
        found = await find_player_by_name(user_input) # Retorna (id, pdata)
        if found:
            target_id, pdata = found

    if not pdata or not target_id:
        await update.message.reply_text("❌ Jogador não encontrado. Tente novamente ou /cancel.")
        return STATE_GET_USER_ID

    context.user_data['edit_target_id'] = target_id
    
    # Se pdata veio sem user_id preenchido corretamente no objeto (comum em buscas raw), garante
    pdata['user_id'] = target_id
    
    info_text = _get_player_info_text(pdata)
    await _send_or_edit_menu(update, context, info_text)
    return STATE_SHOW_MENU

# --- Menu Principal ---

async def admin_show_menu_dispatch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    target_id = context.user_data.get('edit_target_id')
    if not target_id:
        await _send_error(update, "ID perdido. Reinicie.")
        return ConversationHandler.END

    pdata = await get_player_data(target_id)
    info_text = _get_player_info_text(pdata)
    await _send_or_edit_menu(update, context, info_text)
    return STATE_SHOW_MENU

async def admin_choose_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "edit_cancel":
        await query.edit_message_text("Edição finalizada.")
        context.user_data.pop('edit_target_id', None)
        return ConversationHandler.END

    if action == "edit_char_class":
        # Monta lista de classes Tier 1
        kb = []
        for cid, cdata in game_data.CLASSES_DATA.items():
            if cdata.get('tier', 1) == 1:
                emoji = cdata.get('emoji', '🔹')
                name = cdata.get('display_name', cid.capitalize())
                kb.append([InlineKeyboardButton(f"{emoji} {name}", callback_data=f"set_class:{cid}")])
        kb.append([InlineKeyboardButton("🔙 Voltar", callback_data="edit_back_menu")])
        
        await query.edit_message_text("Escolha a nova <b>Classe Base</b>:", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        return STATE_AWAIT_CLASS

    if action == "edit_prof_type":
        kb = []
        for pid, pdata in game_data.PROFESSIONS_DATA.items():
            name = pdata.get('display_name', pid)
            kb.append([InlineKeyboardButton(name, callback_data=f"set_prof:{pid}")])
        kb.append([InlineKeyboardButton("🔙 Voltar", callback_data="edit_back_menu")])
        
        await query.edit_message_text("Escolha a nova <b>Profissão</b>:", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        return STATE_AWAIT_PROFESSION

    if action == "edit_char_lvl":
        await query.edit_message_text("Digite o novo <b>Nível</b> (ex: 50):", parse_mode=ParseMode.HTML)
        return STATE_AWAIT_CHAR_LEVEL

    if action == "edit_prof_lvl":
        await query.edit_message_text("Digite o novo <b>Nível de Profissão</b> (ex: 10):", parse_mode=ParseMode.HTML)
        return STATE_AWAIT_PROF_LEVEL

    return STATE_SHOW_MENU

# --- Actions ---

async def admin_set_class(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    target_id = context.user_data.get('edit_target_id')
    new_class_key = query.data.split(":")[1]
    
    pdata = await get_player_data(target_id)
    if pdata:
        c_info = game_data.CLASSES_DATA.get(new_class_key, {})
        pdata['class'] = c_info.get('display_name', new_class_key.capitalize())
        pdata['class_key'] = new_class_key
        # Opcional: Resetar subclass se mudar a base? Por enquanto mantemos simples.
        await save_player_data(target_id, pdata)
        await query.answer("Classe atualizada!")
    
    return await admin_show_menu_dispatch(update, context)

async def admin_set_profession_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    target_id = context.user_data.get('edit_target_id')
    new_prof = query.data.split(":")[1]
    
    pdata = await get_player_data(target_id)
    if pdata:
        pdata.setdefault('profession', {})
        pdata['profession']['type'] = new_prof
        pdata['profession']['level'] = 1 # Reseta nivel ao mudar prof
        pdata['profession']['xp'] = 0
        await save_player_data(target_id, pdata)
        await query.answer("Profissão definida!")

    return await admin_show_menu_dispatch(update, context)

async def admin_set_char_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        val = int(update.message.text)
        target_id = context.user_data.get('edit_target_id')
        pdata = await get_player_data(target_id)
        if pdata:
            pdata['level'] = val
            pdata['xp'] = 0
            await save_player_data(target_id, pdata)
            await update.message.reply_text(f"✅ Nível definido para {val}.")
            # Retorna ao menu enviando nova mensagem pois estamos em MessageHandler
            info_text = _get_player_info_text(pdata)
            await _send_or_edit_menu(update, context, info_text)
            return STATE_SHOW_MENU
    except ValueError:
        await update.message.reply_text("Número inválido.")
        return STATE_AWAIT_CHAR_LEVEL

async def admin_set_prof_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        val = int(update.message.text)
        target_id = context.user_data.get('edit_target_id')
        pdata = await get_player_data(target_id)
        if pdata:
            pdata.setdefault('profession', {})
            pdata['profession']['level'] = val
            pdata['profession']['xp'] = 0
            await save_player_data(target_id, pdata)
            await update.message.reply_text(f"✅ Nível de Profissão definido para {val}.")
            
            info_text = _get_player_info_text(pdata)
            await _send_or_edit_menu(update, context, info_text)
            return STATE_SHOW_MENU
    except ValueError:
        await update.message.reply_text("Número inválido.")
        return STATE_AWAIT_PROF_LEVEL

async def admin_edit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop('edit_target_id', None)
    if update.callback_query:
        await update.callback_query.edit_message_text("Cancelado.")
    else:
        await update.message.reply_text("Cancelado.")
    return ConversationHandler.END

async def _send_error(update, msg):
    if update.callback_query: await update.callback_query.answer(msg, show_alert=True)
    elif update.message: await update.message.reply_text(msg)

# --- EXPORTAÇÃO DO HANDLER ---

admin_edit_player_handler = ConversationHandler(
    entry_points=[
        CommandHandler("editplayer", admin_edit_player_start, filters=filters.User(ADMIN_LIST)),
        CallbackQueryHandler(admin_edit_player_start, pattern=r"^admin_edit_player$")
    ],
    states={
        STATE_GET_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_get_user_id)],
        STATE_SHOW_MENU: [
            CallbackQueryHandler(admin_choose_action, pattern=r"^edit_(char_class|prof_type|prof_lvl|char_lvl|cancel)$"),
            CallbackQueryHandler(admin_show_menu_dispatch, pattern=r"^edit_back_menu$") # Caso precise recarregar
        ],
        STATE_AWAIT_CLASS: [
            CallbackQueryHandler(admin_set_class, pattern=r"^set_class:"),
            CallbackQueryHandler(admin_show_menu_dispatch, pattern=r"^edit_back_menu$")
        ],
        STATE_AWAIT_PROFESSION: [
            CallbackQueryHandler(admin_set_profession_type, pattern=r"^set_prof:"),
            CallbackQueryHandler(admin_show_menu_dispatch, pattern=r"^edit_back_menu$")
        ],
        STATE_AWAIT_CHAR_LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_set_char_level)],
        STATE_AWAIT_PROF_LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_set_prof_level)],
    },
    fallbacks=[
        CommandHandler("cancel", admin_edit_cancel),
        CallbackQueryHandler(admin_edit_cancel, pattern=r"^edit_cancel$")
    ],
    per_chat=True
)