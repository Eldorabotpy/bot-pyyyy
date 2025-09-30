# handlers/admin_handler.py
from __future__ import annotations
import os
import logging, asyncio
from typing import Dict, Optional, Callable, Awaitable
from handlers.jobs import daily_crystal_grant_job, force_grant_daily_crystals
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler, 
    CommandHandler, 
    ContextTypes, 
    MessageHandler, 
    filters,
    ConversationHandler 
)
from modules.player_manager import delete_player
from telegram.error import BadRequest
from modules.player_manager import clear_player_cache, clear_all_player_cache
from modules import player_manager
from handlers.admin.utils import ensure_admin 

ADMIN_ID = int(os.getenv("ADMIN_ID"))
(SELECT_CACHE_ACTION, ASK_USER_FOR_CACHE_CLEAR) = range(2)

logger = logging.getLogger(__name__)
HTML = "HTML"

# =========================================================
# Utils básicos
# =========================================================
def _is_admin(update: Update) -> bool:
    return bool(update.effective_user and update.effective_user.id == ADMIN_ID)

# ---- teclado cacheado (evita recriar objetos) ----
_ADMIN_KB: Optional[InlineKeyboardMarkup] = None
def _admin_menu_kb() -> InlineKeyboardMarkup:
    global _ADMIN_KB
    if _ADMIN_KB is None:
        _ADMIN_KB = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 𓂀 𝔼𝕟𝕥𝕣𝕖𝕘𝕒𝕣 𝕀𝕥𝕖𝕟𝕤 (𝔸𝕕𝕞𝕚𝕟) 𓂀", callback_data="admin:diamond_grant")],
            [InlineKeyboardButton("🔁 𓂀 𝔽𝕠𝕣ç𝕒𝕣 𝕕𝕚á𝕣𝕚𝕠𝕤 (ℂ𝕣𝕚𝕤𝕥𝕒𝕚𝕤) 𓂀", callback_data="admin_force_daily")],
            [InlineKeyboardButton("👑 𓂀 ℙ𝕣𝕖𝕞𝕚𝕦𝕞 𓂀", callback_data="admin_premium")],
            [InlineKeyboardButton("📁 𓂀 𝔾𝕖𝕣𝕖𝕟𝕔𝕚𝕒𝕣 𝔽𝕚𝕝𝕖 𝕀𝔻𝕤 𓂀", callback_data="admin_file_ids")],
            [InlineKeyboardButton("🧹 𓂀 ℝ𝕖𝕤𝕖𝕥/ℝ𝕖𝕤𝕡𝕖𝕔 𓂀", callback_data="admin_reset_menu")],
            [InlineKeyboardButton("🧽 𓂀 𝕃𝕚𝕞𝕡𝕒𝕣 ℂ𝕒𝕔𝕙𝕖 𓂀", callback_data="admin_clear_cache")],
            [InlineKeyboardButton("🔄 𝐑𝐞𝐬𝐞𝐭𝐚𝐫 𝐄𝐬𝐭𝐚𝐝𝐨 (/𝐫𝐞𝐬𝐞𝐭_𝐬𝐭𝐚𝐭𝐞)", callback_data="admin_reset_state_hint")],
        ])
    return _ADMIN_KB

async def _delete_player_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return

    if not context.args:
        await update.message.reply_text("Uso: /delete_player <user_id>")
        return

    try:
        user_id_to_delete = int(context.args[0])
        
        if delete_player(user_id_to_delete):
            await update.message.reply_text(f"✅ Jogador com ID {user_id_to_delete} foi apagado com sucesso.")
        else:
            await update.message.reply_text(f"⚠️ Jogador com ID {user_id_to_delete} não foi encontrado no banco de dados.")

    except ValueError:
        await update.message.reply_text("Por favor, forneça um ID de usuário numérico válido.")
    except Exception as e:
        await update.message.reply_text(f"Ocorreu um erro ao tentar apagar o jogador: {e}")

# Crie o handler para o novo comando
delete_player_handler = CommandHandler("delete_player", _delete_player_command)

async def _safe_answer(update: Update) -> None:
    q = update.callback_query
    if not q:
        return
    try:
        await q.answer()
    except BadRequest:
        pass
    except Exception:
        logger.debug("query.answer() ignorado", exc_info=True)

async def _safe_edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str,
                          reply_markup: InlineKeyboardMarkup | None = None) -> None:
    q = update.callback_query
    try:
        if q and q.message:
            await q.edit_message_text(text, parse_mode=HTML, reply_markup=reply_markup)
            return
    except Exception:
        pass
    # fallback
    chat_id = (q.message.chat.id if q and q.message else update.effective_chat.id)
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=HTML, reply_markup=reply_markup)

# =========================================================
# /admin (abre painel)
# =========================================================
async def _send_admin_menu(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(
        chat_id=chat_id,
        text="🎛️ <b>Painel do Admin</b>\nEscolha uma opção:",
        reply_markup=_admin_menu_kb(),
        parse_mode=HTML,
    )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        if update.effective_message:
            await update.effective_message.reply_text("Sem permissão.")
        return
    await _send_admin_menu(update.effective_chat.id, context)

admin_command_handler = CommandHandler("admin", admin_command, filters=filters.User(ADMIN_ID))

# =========================================================
# Submenus simples
# =========================================================


async def _handle_admin_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _safe_answer(update)
    await _safe_edit_text(update, context, "🎛️ <b>Painel do Admin</b>\nEscolha uma opção:", _admin_menu_kb())



async def _handle_admin_force_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _safe_answer(update)
    if not _is_admin(update):
        return
    
    # Edita a mensagem para dar um feedback de que está processando
    await _safe_edit_text(update, context, "⏳ Processando entrega de cristais diários...")
    
    # Executa o job e CAPTURA o resultado
    granted_count = await force_grant_daily_crystals(context)
    
    # Monta a nova mensagem com o resultado
    feedback_text = f"✅ Executado! <b>{granted_count}</b> jogadores receberam os cristais diários."
    
    await _safe_edit_text(
        update, context,
        feedback_text,
        InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ 𓂀 𝕍𝕠𝕝𝕥𝕒𝕣 𓂀", callback_data="admin_main")]])
    )

async def force_daily_crystals_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        if update.effective_message:
            await update.effective_message.reply_text("Sem permissão.")
        return
    
    # Adiciona um feedback imediato para o admin saber que o comando foi recebido
    await update.effective_message.reply_text("⏳ Processando entrega forçada de cristais para todos os jogadores...")
    
    # Chama a NOVA função "superpoderosa" e captura a contagem de jogadores
    granted_count = await force_grant_daily_crystals(context)
    
    # Envia o feedback final com o resultado exato
    await update.effective_message.reply_text(
        f"✅ Executado! <b>{granted_count}</b> jogadores receberam os cristais diários.",
        parse_mode="HTML"
    )

# A linha abaixo não muda, mas a incluo para você substituir o bloco todo
force_daily_handler = CommandHandler("forcar_cristais", force_daily_crystals_cmd, filters=filters.User(ADMIN_ID))

# =========================================================
# Roteador do painel admin
# =========================================================
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not _is_admin(update):
        if query:
            await query.answer("Sem permissão.", show_alert=True)
        return

    data = (query.data or "") if query else ""

    # Esta seção ignora os cliques que serão tratados pelas nossas novas conversas
    # (Premium, File ID, e o novo Painel de Reset), deixando-os passar.
    if data.startswith("admin:") or data in ["admin_file_ids", "admin_reset_menu", "admin_premium"]:
        return

    # Ações que ainda são tratadas diretamente neste arquivo
    if data == "admin_force_daily":
        await _handle_admin_force_daily(update, context)
        return
    
    if data == "admin_main":
        await _handle_admin_main(update, context)
        return
    
    # Se o clique não corresponder a nada, apenas confirma o recebimento sem fazer nada
    await _safe_answer(update)

admin_callback_handler = CallbackQueryHandler(
    admin_callback,
    pattern=r"^admin_.*$|^admin:.*$"
)

async def _cache_entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update): # <--- Correção aqui
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("👤 Limpar cache de UM jogador", callback_data="cache_clear_one")],
        [InlineKeyboardButton("🗑️ Limpar TODO o cache (Cuidado!)", callback_data="cache_clear_all_confirm")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cache_cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🧽 **Gerenciamento de Cache**\n\nEscolha uma opção:"

    query = update.callback_query
    # Se foi iniciado por um botão (CallbackQuery)
    if query:
        await query.answer()
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
    # Se foi iniciado por um comando (/clear_cache)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")
        
    return SELECT_CACHE_ACTION

async def _cache_ask_for_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pede ao admin o ID do usuário para limpar o cache."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("👤 Por favor, envie o **User ID** ou o **nome exato do personagem** para limpar o cache.\n\nVocê pode usar /cancelar a qualquer momento.")
    return ASK_USER_FOR_CACHE_CLEAR

async def _cache_clear_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe o ID/nome, limpa o cache e encerra."""
    target_input = update.message.text
    
    # Tenta encontrar por ID primeiro
    try:
        user_id = int(target_input)
        pdata = player_manager.get_player_data(user_id)
        found_by = "ID"
    except ValueError:
        # Se não for ID, tenta por nome
        found = player_manager.find_player_by_name(target_input)
        if found:
            user_id, pdata = found
            found_by = "Nome"
        else:
            user_id, pdata = None, None

    if pdata:
        was_in_cache = clear_player_cache(user_id)
        if was_in_cache:
            await update.message.reply_text(f"✅ Cache para o jogador **{pdata.get('character_name')}** (ID: `{user_id}`) foi limpo com sucesso.")
        else:
            await update.message.reply_text(f"ℹ️ O jogador **{pdata.get('character_name')}** (ID: `{user_id}`) foi encontrado, mas não estava no cache no momento.")
    else:
        await update.message.reply_text(f"❌ Não foi possível encontrar um jogador com o {found_by if 'found_by' in locals() else 'ID/Nome'} fornecido.")
        
    return ConversationHandler.END

async def _cache_confirm_clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mostra um aviso de confirmação antes de limpar todo o cache."""
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("✅ Sim, tenho certeza", callback_data="cache_do_clear_all")],
        [InlineKeyboardButton("❌ Não, voltar", callback_data="cache_main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "⚠️ **ATENÇÃO!**\n\nLimpar todo o cache fará com que o bot precise buscar os dados de **todos** os jogadores no MongoDB na próxima vez que interagirem. Isso pode causar uma pequena lentidão temporária.\n\n**Você tem certeza que quer continuar?**",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    return SELECT_CACHE_ACTION

async def _cache_do_clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Limpa todo o cache e encerra."""
    query = update.callback_query
    await query.answer()
    count = clear_all_player_cache()
    await query.edit_message_text(f"🗑️ Cache completo foi limpo com sucesso.\n\n({count} jogadores removidos da memória).")
    return ConversationHandler.END

async def _cache_back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Volta para o menu principal do cache."""
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("👤 Limpar cache de UM jogador", callback_data="cache_clear_one")],
        [InlineKeyboardButton("🗑️ Limpar TODO o cache (Cuidado!)", callback_data="cache_clear_all_confirm")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cache_cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("🧽 **Gerenciamento de Cache**\n\nEscolha uma opção:", reply_markup=reply_markup, parse_mode="HTML")
    return SELECT_CACHE_ACTION
    
async def _cache_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a operação."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("Operação de cache cancelada.")
    else:
        await update.message.reply_text("Operação de cache cancelada.")
    return ConversationHandler.END

# --- O Handler da Conversa ---
clear_cache_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("clear_cache", _cache_entry_point),
        # 👇 ADICIONE ESTE GATILHO PARA O BOTÃO 👇
        CallbackQueryHandler(_cache_entry_point, pattern=r"^admin_clear_cache$"),
    ],
    states={
        SELECT_CACHE_ACTION: [
            CallbackQueryHandler(_cache_ask_for_user, pattern="^cache_clear_one$"),
            CallbackQueryHandler(_cache_confirm_clear_all, pattern="^cache_clear_all_confirm$"),
            CallbackQueryHandler(_cache_do_clear_all, pattern="^cache_do_clear_all$"),
            CallbackQueryHandler(_cache_back_to_main, pattern="^cache_main_menu$"),
            CallbackQueryHandler(_cache_cancel, pattern="^cache_cancel$"),
        ],
        ASK_USER_FOR_CACHE_CLEAR: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, _cache_clear_user)
        ],
    },
    fallbacks=[CommandHandler("cancelar", _cache_cancel)],
)