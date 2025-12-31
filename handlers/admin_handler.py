# handlers/admin_handler.py
# (VERSÃO FINAL UNIFICADA: Comandos Corrigidos + Conversations Restauradas)

from __future__ import annotations
import os
import io
import logging 
import json
import sys
import asyncio 
from typing import Optional

# --- Imports do Telegram ---
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler
)
from telegram.error import BadRequest
from telegram.constants import ParseMode

# --- Imports de Banco de Dados e Utils ---
from bson import ObjectId
from modules.auth_utils import get_current_player_id
from handlers.admin.utils import parse_hybrid_id, ensure_admin, ADMIN_LIST
from modules.player.queries import _normalize_char_name

# --- Imports de Funcionalidades Administrativas ---
from handlers.jobs import distribute_kingdom_defense_ticket_job
from handlers.admin.grant_item import grant_item_conv_handler 
from handlers.admin.generate_equip import generate_equip_conv_handler 
from handlers.admin.file_id_conv import file_id_conv_handler 
from handlers.admin.premium_panel import premium_panel_handler 
from handlers.admin.reset_panel import reset_panel_conversation_handler 
from handlers.admin.grant_skill import grant_skill_conv_handler
from handlers.admin.grant_skin import grant_skin_conv_handler
from handlers.admin.player_management_handler import player_management_conv_handler
from handlers.admin.debug_skill import debug_skill_handler

# (Opcional: Se você tiver o arquivo, descomente. Se não, mantenha comentado para evitar erro)
# from handlers.admin.sell_gems import sell_gems_conv_handler 

# --- Imports do Core do Jogo ---
from modules.player_manager import (
    delete_player, 
    clear_player_cache, 
    clear_all_player_cache,
    get_player_data, 
    add_item_to_inventory, 
    save_player_data, 
    find_player_by_name, 
    allowed_points_for_level, 
    compute_spent_status_points,
    reset_stats_and_refund_points,
    iter_players,
    iter_player_ids,
    corrigir_bug_tomos_duplicados # Certifique-se que isso existe no player_manager
)

from modules import game_data
from handlers.jobs import reset_pvp_season, force_grant_daily_crystals 
from kingdom_defense.engine import event_manager
from modules.player.core import _player_cache, players_collection

logger = logging.getLogger(__name__) 
HTML = "HTML" 

# --- CONSTANTES DE ESTADO (CONVERSATIONS) ---
(SELECT_CACHE_ACTION, ASK_USER_FOR_CACHE_CLEAR) = range(2)
(SELECT_TEST_ACTION, ASK_WAVE_NUMBER) = range(2, 4)
(ASK_DELETE_ID, CONFIRM_DELETE_ACTION) = range(4, 6)
ASK_GHOST_CLAN_ID = 6
(ASK_OLD_ID_CHANGE, ASK_NEW_ID_CHANGE, CONFIRM_ID_CHANGE) = range(7, 10)

# =========================================================
# HELPERS VISUAIS
# =========================================================

async def _safe_answer(update: Update):
    if q := update.callback_query:
        try: await q.answer()
        except: pass

async def _safe_edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup=None):
    if q := update.callback_query:
        try: await q.edit_message_text(text, parse_mode=HTML, reply_markup=reply_markup)
        except: pass
    else:
        chat_id = update.effective_chat.id
        await context.bot.send_message(chat_id, text, parse_mode=HTML, reply_markup=reply_markup)

async def _send_admin_menu(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text="🎛️ <b>Painel do Admin</b>\nEscolha uma opção:",
            reply_markup=_admin_menu_kb(),
            parse_mode=HTML,
        )
    except Exception as e:
        logger.error(f"Falha ao enviar menu admin para chat {chat_id}: {e}")

# =========================================================
# MENUS (KEYBOARDS)
# =========================================================

def _admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 𓂀 𝔼𝕟𝕥𝕣𝕖𝕘𝕒𝕣 𝕀𝕥𝕖𝕟𝕤 (Stackable) 𓂀", callback_data="admin_grant_item")],
        [InlineKeyboardButton("💎 𓂀 𝕍𝕖𝕟𝕕𝕖𝕣 𝔾𝕖𝕞𝕒𝕤 𓂀", callback_data="admin_sell_gems")],
        [InlineKeyboardButton("🛠️ 𓂀 𝔾𝕖𝕣𝕒𝕣 𝔼𝕢𝕦𝕚𝕡𝕒𝕞𝕖𝕟𝕥𝕠 𓂀", callback_data="admin_generate_equip")],
        [InlineKeyboardButton("📚 𓂀 𝔼𝕟𝕤𝕚𝕟𝕒𝕣 ℍ𝕒𝕓𝕚𝕝𝕚𝕕𝕒𝕕𝕖 (Skill) 𓂀", callback_data="admin_grant_skill")],
        [InlineKeyboardButton("🎨 𓂀 𝔼𝕟𝕥𝕣𝕖𝕘𝕒𝕣 𝔸𝕡𝕒𝕣𝕖̂𝕟𝕔𝕚𝕒 (Skin) 𓂀", callback_data="admin_grant_skin")],
        [InlineKeyboardButton("👥 𓂀 𝔾𝕖𝕣𝕖𝕟𝕔𝕚𝕒𝕣 𝕁𝕠𝕘𝕒𝕕𝕠𝕣𝕖𝕤 𓂀", callback_data="admin_pmanage_main")],
        [InlineKeyboardButton("👤 𓂀 𝔼𝕕𝕚𝕥𝕒𝕣 𝕁𝕠𝕘𝕒𝕕𝕠𝕣 𓂀", callback_data="admin_edit_player")], 
        [InlineKeyboardButton("🆔 𓂀 𝐓𝐑𝐎𝐂𝐀𝐑 𝐈𝐃 (𝐌𝐢𝐠𝐫𝐚𝐫) 𓂀", callback_data="admin_change_id_start")],
        [InlineKeyboardButton("🏚️ Limpar Clã Fantasma", callback_data="admin_fix_clan_start")],
        [InlineKeyboardButton("💀 𝐃𝐄𝐋𝐄𝐓𝐀𝐑 𝐂𝐎𝐍𝐓𝐀 (Perigo)", callback_data="admin_delete_start")],
        [InlineKeyboardButton("🔁 𓂀 𝔽𝕠𝕣ç𝕒𝕣 𝕕𝕚á𝕣𝕚𝕠𝕤 (ℂ𝕣𝕚𝕤𝕥𝕒𝕚𝕤) 𓂀", callback_data="admin_force_daily")],
        [InlineKeyboardButton("👑 𓂀 ℙ𝕣𝕖𝕞𝕚𝕦𝕞 𓂀", callback_data="admin_premium")],
        [InlineKeyboardButton("⚔️ Painel PvP", callback_data="admin_pvp_menu")],
        [InlineKeyboardButton("🎉 𓂀 𝔾𝕖𝕣𝕖𝕟𝕔𝕚𝕒𝕣 𝔼𝕧𝕖𝕟𝕥𝕠𝕤 𓂀 🎉", callback_data="admin_event_menu")],
        [InlineKeyboardButton("🔬 𓂀 Painel de Teste de Evento 𓂀 🔬", callback_data="admin_test_menu")],
        [InlineKeyboardButton("📁 𓂀 𝔾𝕖𝕣𝕖𝕟𝕔𝕚𝕒𝕣 𝔽𝕚𝕝𝕖 𝕀𝔻𝕤 𓂀", callback_data="admin_file_ids")],
        [InlineKeyboardButton("🧹 𓂀 ℝ𝕖𝕤𝕖𝕥/ℝ𝕖𝕤𝕡𝕖𝕔 𓂀", callback_data="admin_reset_menu")],
        [InlineKeyboardButton("🧽 𓂀 𝕃𝕚𝕞𝕡𝕒𝕣 ℂ𝕒𝕔𝕙𝕖 𓂀", callback_data="admin_clear_cache")],
        [InlineKeyboardButton("🔄 𝐑𝐞𝐬𝐞𝐭𝐚𝐫 𝐄𝐬𝐭𝐚𝐝𝐨 (/𝐫𝐞𝐬𝐞𝐭_𝐬𝐭𝐚𝐭𝐞)", callback_data="admin_reset_state_hint")], 
        [InlineKeyboardButton("ℹ️ 𝐀𝐣𝐮𝐝𝐚 𝐝𝐨𝐬 𝐂𝐨𝐦𝐚𝐧𝐝𝐨𝐬", callback_data="admin_help")]
    ])

def _admin_event_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎟️ Entregar Ticket de Defesa", callback_data="admin_event_force_ticket")],
        [InlineKeyboardButton("📨 FORÇAR JOB DE TICKETS (TODOS)", callback_data="admin_force_ticket_job")],
        [InlineKeyboardButton("▶️ Forçar Início do Evento", callback_data="admin_event_force_start")],
        [InlineKeyboardButton("⏹️ Forçar Fim do Evento", callback_data="admin_event_force_end")],
        [InlineKeyboardButton("⬅️ Voltar ao Painel Principal", callback_data="admin_main")],
    ])

def _admin_test_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Iniciar em Wave Específica", callback_data="test_start_at_wave")],
        [InlineKeyboardButton("⬅️ Voltar ao Painel Principal", callback_data="admin_main")],
    ])

# =========================================================
# COMANDOS SIMPLES E NAVEGAÇÃO
# =========================================================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe o painel principal do admin."""
    if not await ensure_admin(update): return 
    await update.message.reply_text(
        "🎛️ <b>Painel do Admin</b>\nEscolha uma opção:",
        reply_markup=_admin_menu_kb(),
        parse_mode=HTML,
    )

async def _handle_admin_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): return
    await _safe_answer(update)
    await _safe_edit_text(update, context, "🎛️ <b>Painel do Admin</b>\nEscolha uma opção:", _admin_menu_kb())

async def get_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    thread_id = getattr(update.effective_message, 'message_thread_id', None)
    topic_text = f"🆔 <b>Topic ID:</b> <code>{thread_id}</code>" if thread_id else "🆔 <b>Topic ID:</b> <i>Geral (None)</i>"
    text = (
        f"<b>🕵️ INSPETOR DE IDs</b>\n"
        f"--------------------------\n"
        f"👤 <b>Seu User ID:</b> <code>{update.effective_user.id}</code>\n"
        f"🏠 <b>Group ID:</b> <code>{chat_id}</code>\n"
        f"{topic_text}"
    )
    await update.message.reply_text(text, parse_mode=HTML)

async def _handle_admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): return
    await _safe_answer(update)
    help_text = "ℹ️ <b>Ajuda Admin</b>\nUse os botões para navegar ou os comandos:\n/fixme - Corrigir seu char\n/mydata - Baixar dados\n/find_player <nome> - Achar ID"
    await _safe_edit_text(update, context, help_text, InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_main")]]))

# =========================================================
# EVENTOS
# =========================================================

async def _handle_admin_event_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): return
    await _safe_answer(update)
    await _safe_edit_text(update, context, "🎉 <b>Painel de Gerenciamento de Eventos</b>", _admin_event_menu_kb())

async def _handle_force_start_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): return
    query = update.callback_query
    await query.answer("Iniciando...")
    result = await event_manager.start_event()
    msg = result.get("success") or result.get("error") or "Erro desconhecido"
    await query.message.reply_text(f"Event Start: {msg}")

async def _handle_force_end_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): return
    query = update.callback_query
    await query.answer("Finalizando...")
    result = await event_manager.end_event(context)
    msg = result.get("success") or result.get("error") or "Erro desconhecido"
    await query.message.reply_text(f"Event End: {msg}")

async def _handle_force_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): return
    query = update.callback_query
    uid = get_current_player_id(update, context)
    pdata = await get_player_data(uid)
    if pdata:
        add_item_to_inventory(pdata, 'ticket_defesa_reino', 1)
        await save_player_data(uid, pdata)
        await query.answer("Ticket entregue!", show_alert=True)

async def _handle_force_ticket_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): return
    query = update.callback_query
    await query.answer("Rodando job global...")
    context.job = type('Job', (object,), {'data': {"event_time": "FORCE"}, 'name': 'admin_force'})
    await distribute_kingdom_defense_ticket_job(context)
    await query.message.reply_text("Job de tickets executado.")

async def _handle_admin_force_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): return
    await _safe_answer(update)
    await force_grant_daily_crystals(context)
    await _safe_edit_text(update, context, "✅ Cristais diários entregues a todos.", InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_main")]]))

async def force_daily_crystals_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): return
    await force_grant_daily_crystals(context)
    await update.message.reply_text("Cristais entregues.")

async def _reset_pvp_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): return
    await reset_pvp_season(context)
    await update.message.reply_text("PvP resetado.")

# =========================================================
# COMANDOS DE JOGADOR (DEBUG/FIX) - CORRIGIDOS
# =========================================================

async def fix_my_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Corrige o estado do PRÓPRIO admin."""
    if not await ensure_admin(update): return
    user_id = get_current_player_id(update, context) # Pega o ID da Sessão
    
    player_data = await get_player_data(user_id)
    if not player_data:
        await update.message.reply_text("Erro: Dados não encontrados.")
        return

    try:
        player_data['xp'] = 0 
        allowed = allowed_points_for_level(player_data) 
        spent = compute_spent_status_points(player_data) 
        player_data['stat_points'] = max(0, allowed - spent)
        await save_player_data(user_id, player_data)
        await update.message.reply_text("✅ Personagem corrigido!")
    except Exception as e:
        await update.message.reply_text(f"Erro: {e}")

async def my_data_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envia JSON do jogador logado."""
    if not await ensure_admin(update): return
    user_id = get_current_player_id(update, context) # Pega o ID da Sessão

    player_data = await get_player_data(user_id)
    if not player_data: return

    # Trata ObjectId para JSON
    pdata_copy = player_data.copy()
    if '_id' in pdata_copy: pdata_copy['_id'] = str(pdata_copy['_id'])

    try:
        data_str = json.dumps(pdata_copy, indent=2, ensure_ascii=False)
        input_file = io.BytesIO(data_str.encode('utf-8'))
        await update.message.reply_document(document=input_file, filename=f"dados_{user_id}.json")
    except Exception as e:
        await update.message.reply_text(f"Erro: {e}")

async def inspect_item_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): return
    if not context.args: return
    item_id = context.args[0]
    info = (game_data.ITEMS_DATA or {}).get(item_id)
    await update.message.reply_text(f"INFO {item_id}: {info}")

async def debug_player_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): return 
    try:
        raw_id = context.args[0]
        uid = parse_hybrid_id(raw_id)
    except: return
    
    in_cache = uid in _player_cache
    in_db = players_collection.find_one({"_id": uid}) is not None
    await update.message.reply_text(f"Debug {uid}:\nCache: {in_cache}\nDB: {in_db}")

async def find_player_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): return 
    if not context.args: return
    name = " ".join(context.args)
    found = await find_player_by_name(name)
    if found:
        await update.message.reply_text(f"Encontrado: {found[1].get('character_name')} ID: {found[0]}")
    else:
        await update.message.reply_text("Não encontrado.")

# =========================================================
# OPERAÇÕES DE MASSA E LIMPEZA
# =========================================================

async def hard_respec_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): return
    msg = await update.message.reply_text("⏳ Iniciando Reset Total...")
    count = 0
    async for uid, _ in iter_players():
        pdata = await get_player_data(uid)
        if pdata:
            await reset_stats_and_refund_points(pdata)
            await save_player_data(uid, pdata)
            count += 1
            if count % 50 == 0: await asyncio.sleep(0.1)
    clear_all_player_cache()
    await msg.edit_text(f"✅ Reset Concluído! {count} jogadores.")

async def admin_fix_tomos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): return
    msg = await update.message.reply_text("⏳ Corrigindo Tomos...")
    fixed = 0
    
    # Coleta IDs primeiro para evitar erro de cursor
    ids = []
    async for uid, _ in iter_players():
        ids.append(uid)
        
    for pid in ids:
        if await corrigir_bug_tomos_duplicados(pid):
            fixed += 1
        await asyncio.sleep(0.01)
    await msg.edit_text(f"✅ Tomos corrigidos: {fixed}")

async def admin_clean_market_names(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): return
    await update.message.reply_text("Limpando mercado (placeholder)...")

async def clean_clan_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): return
    if not context.args: return
    uid = parse_hybrid_id(context.args[0])
    pdata = await get_player_data(uid)
    if pdata:
        pdata['clan_id'] = None
        await save_player_data(uid, pdata)
        clear_player_cache(uid)
        await update.message.reply_text("Clã limpo.")

async def fix_deleted_clan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): return
    clan_id = context.args[0]
    count = 0
    async for uid, pdata in iter_players():
        if pdata.get('clan_id') == clan_id:
            pdata['clan_id'] = None
            await save_player_data(uid, pdata)
            count += 1
    await update.message.reply_text(f"Clã fantasma removido de {count} jogadores.")

async def fix_premium_dates_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): return
    await update.message.reply_text("Corrigindo VIPs...")
    # Lógica simplificada para placeholder, usar a completa se necessário
    pass 

async def _delete_player_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): return
    uid = parse_hybrid_id(context.args[0])
    if delete_player(uid):
        await update.message.reply_text("Deletado.")
    else:
        await update.message.reply_text("Não encontrado.")

# =========================================================
# CONVERSATIONS HANDLERS (DEFINIÇÕES)
# =========================================================

# --- 1. Cache ---
async def _cache_entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update): return ConversationHandler.END
    await _safe_edit_text(update, context, "Opções de Cache:", InlineKeyboardMarkup([
        [InlineKeyboardButton("Limpar UM", callback_data="cache_clear_one")],
        [InlineKeyboardButton("Limpar TUDO", callback_data="cache_clear_all_confirm")],
        [InlineKeyboardButton("Cancelar", callback_data="admin_main")]
    ]))
    return SELECT_CACHE_ACTION

async def _cache_ask_for_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _safe_edit_text(update, context, "Envie o ID/Nome:")
    return ASK_USER_FOR_CACHE_CLEAR

async def _cache_clear_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    txt = update.message.text
    uid = parse_hybrid_id(txt)
    # Lógica simplificada de busca
    if uid: clear_player_cache(uid)
    await update.message.reply_text("Cache limpo se existia.")
    await _send_admin_menu(update.effective_chat.id, context)
    return ConversationHandler.END

async def _cache_confirm_clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _safe_edit_text(update, context, "Confirmar limpar TUDO?", InlineKeyboardMarkup([
        [InlineKeyboardButton("Sim", callback_data="cache_do_clear_all")],
        [InlineKeyboardButton("Não", callback_data="admin_main")]
    ]))
    return SELECT_CACHE_ACTION

async def _cache_do_clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    clear_all_player_cache()
    await _safe_edit_text(update, context, "Cache global limpo.")
    await _send_admin_menu(update.effective_chat.id, context)
    return ConversationHandler.END

async def _cache_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _send_admin_menu(update.effective_chat.id, context)
    return ConversationHandler.END

clear_cache_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(_cache_entry_point, pattern=r"^admin_clear_cache$")],
    states={
        SELECT_CACHE_ACTION: [
            CallbackQueryHandler(_cache_ask_for_user, pattern="^cache_clear_one$"),
            CallbackQueryHandler(_cache_confirm_clear_all, pattern="^cache_clear_all_confirm$"),
            CallbackQueryHandler(_cache_do_clear_all, pattern="^cache_do_clear_all$"),
            CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$"), 
        ],
        ASK_USER_FOR_CACHE_CLEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_LIST), _cache_clear_user)],
    },
    fallbacks=[
        CommandHandler("cancelar", _cache_cancel, filters=filters.User(ADMIN_LIST)),
        CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$")
    ],
    per_message=False
)

# --- 2. Test Event ---
async def _handle_admin_test_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update): return ConversationHandler.END
    await _safe_edit_text(update, context, "Painel de Teste", _admin_test_menu_kb())
    return SELECT_TEST_ACTION

async def _test_ask_wave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _safe_edit_text(update, context, "Digite a Wave:")
    return ASK_WAVE_NUMBER

async def _test_start_wave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try: wave = int(update.message.text)
    except: wave = 1
    event_manager.start_event_at_wave(wave)
    await update.message.reply_text(f"Iniciado na wave {wave}")
    return ConversationHandler.END

async def _test_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _send_admin_menu(update.effective_chat.id, context)
    return ConversationHandler.END

test_event_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(_handle_admin_test_menu, pattern=r"^admin_test_menu$")],
    states={
        SELECT_TEST_ACTION: [CallbackQueryHandler(_test_ask_wave, pattern="^test_start_at_wave$"), CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$")],
        ASK_WAVE_NUMBER: [MessageHandler(filters.TEXT & filters.User(ADMIN_LIST), _test_start_wave)],
    },
    fallbacks=[CommandHandler("cancelar", _test_cancel), CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$")],
    per_message=False
)

# --- 3. Delete Player ---
async def _delete_entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update): return ConversationHandler.END
    await _safe_edit_text(update, context, "Envie ID para DELETAR:")
    return ASK_DELETE_ID

async def _delete_resolve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = parse_hybrid_id(update.message.text)
    if not uid: 
        await update.message.reply_text("ID Inválido.")
        return ConversationHandler.END
    context.user_data['del_id'] = uid
    await update.message.reply_text(f"Confirmar deletar {uid}?", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("SIM", callback_data="confirm_delete_yes")]]))
    return CONFIRM_DELETE_ACTION

async def _delete_perform_btn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = context.user_data.get('del_id')
    delete_player(uid)
    await _safe_edit_text(update, context, "Deletado.")
    return ConversationHandler.END

async def _delete_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _send_admin_menu(update.effective_chat.id, context)
    return ConversationHandler.END

delete_player_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(_delete_entry_point, pattern=r"^admin_delete_start$")],
    states={
        ASK_DELETE_ID: [MessageHandler(filters.TEXT & filters.User(ADMIN_LIST), _delete_resolve)],
        CONFIRM_DELETE_ACTION: [CallbackQueryHandler(_delete_perform_btn, pattern="^confirm_delete_yes$"), CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$")]
    },
    fallbacks=[CommandHandler("cancelar", _delete_cancel), CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$")]
)

# --- 4. Fix Clan ---
async def _fix_clan_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update): return ConversationHandler.END
    await _safe_edit_text(update, context, "Digite o ID do Clã para limpar:")
    return ASK_GHOST_CLAN_ID

async def _fix_clan_perform(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    clan_id = update.message.text
    count = 0
    async for uid, pdata in iter_players():
        if pdata.get('clan_id') == clan_id:
            pdata['clan_id'] = None
            await save_player_data(uid, pdata)
            count += 1
    await update.message.reply_text(f"Limpo de {count} jogadores.")
    return ConversationHandler.END

fix_clan_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(_fix_clan_entry, pattern=r"^admin_fix_clan_start$")],
    states={ASK_GHOST_CLAN_ID: [MessageHandler(filters.TEXT & filters.User(ADMIN_LIST), _fix_clan_perform)]},
    fallbacks=[CommandHandler("cancelar", _delete_cancel), CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$")]
)

# --- 5. Change ID ---
async def _change_id_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update): return ConversationHandler.END
    await _safe_edit_text(update, context, "Digite ID VELHO:")
    return ASK_OLD_ID_CHANGE

async def _change_id_ask_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['old_id'] = parse_hybrid_id(update.message.text)
    await update.message.reply_text("Digite ID NOVO:")
    return ASK_NEW_ID_CHANGE

async def _change_id_confirm_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['new_id'] = parse_hybrid_id(update.message.text)
    await update.message.reply_text("Confirmar troca?", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("SIM", callback_data="do_change_id_yes")]]))
    return CONFIRM_ID_CHANGE

async def _change_id_perform(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    old = context.user_data['old_id']
    new = context.user_data['new_id']
    
    pdata = await get_player_data(old)
    if pdata:
        pdata['_id'] = new
        # Insere novo
        if isinstance(new, int): players_collection.insert_one(pdata)
        else: players_collection.database['users'].insert_one(pdata)
        # Deleta velho
        delete_player(old)
        await _safe_edit_text(update, context, "ID Trocado.")
    else:
        await _safe_edit_text(update, context, "Erro: Jogador original não achado.")
    return ConversationHandler.END

change_id_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(_change_id_entry, pattern=r"^admin_change_id_start$")],
    states={
        ASK_OLD_ID_CHANGE: [MessageHandler(filters.TEXT & filters.User(ADMIN_LIST), _change_id_ask_new)],
        ASK_NEW_ID_CHANGE: [MessageHandler(filters.TEXT & filters.User(ADMIN_LIST), _change_id_confirm_step)],
        CONFIRM_ID_CHANGE: [CallbackQueryHandler(_change_id_perform, pattern="^do_change_id_yes$"), CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$")]
    },
    fallbacks=[CommandHandler("cancelar", _delete_cancel)]
)

# =========================================================
# REGISTRO DOS HANDLERS (LISTA FINAL)
# =========================================================

# Handlers de Comando (Filtrados)
admin_command_handler = CommandHandler("admin", admin_command, filters=filters.User(ADMIN_LIST))
delete_player_handler = CommandHandler("delete_player", _delete_player_command, filters=filters.User(ADMIN_LIST))
inspect_item_handler = CommandHandler("inspect_item", inspect_item_command, filters=filters.User(ADMIN_LIST))
force_daily_handler = CommandHandler("forcar_cristais", force_daily_crystals_cmd, filters=filters.User(ADMIN_LIST))
my_data_handler = CommandHandler("mydata", my_data_command, filters=filters.User(ADMIN_LIST))
reset_pvp_now_handler = CommandHandler("resetpvpnow", _reset_pvp_now_command, filters=filters.User(ADMIN_LIST))
find_player_handler = CommandHandler("find_player", find_player_command, filters=filters.User(ADMIN_LIST))
debug_player_handler = CommandHandler("debug_player", debug_player_data, filters=filters.User(ADMIN_LIST))
get_id_command_handler = CommandHandler("get_id", get_id_command) # Sem filtro
fixme_handler = CommandHandler("fixme", fix_my_character, filters=filters.User(ADMIN_LIST))
hard_respec_all_handler = CommandHandler("hard_respec_all", hard_respec_all_command, filters=filters.User(ADMIN_LIST))
fix_tomos_handler = CommandHandler("fix_tomos", admin_fix_tomos_command, filters=filters.User(ADMIN_LIST))
clean_market_handler = CommandHandler("limpar_mercado", admin_clean_market_names, filters=filters.User(ADMIN_LIST))
clean_clan_handler = CommandHandler("limpar_cla", clean_clan_status_command, filters=filters.User(ADMIN_LIST))
fix_ghost_clan_handler = CommandHandler("fix_cla_fantasma", fix_deleted_clan_command, filters=filters.User(ADMIN_LIST))
fix_premium_handler = CommandHandler("fix_premium", fix_premium_dates_command, filters=filters.User(ADMIN_LIST))

# Handlers de Callback (Navegação Simples)
admin_main_handler = CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$")
admin_force_daily_callback_handler = CallbackQueryHandler(_handle_admin_force_daily, pattern="^admin_force_daily$")
admin_event_menu_handler = CallbackQueryHandler(_handle_admin_event_menu, pattern="^admin_event_menu$")
admin_force_start_handler = CallbackQueryHandler(_handle_force_start_event, pattern="^admin_event_force_start$")
admin_force_end_handler = CallbackQueryHandler(_handle_force_end_event, pattern="^admin_event_force_end$")
admin_force_ticket_handler = CallbackQueryHandler(_handle_force_ticket, pattern="^admin_event_force_ticket$")
admin_force_ticket_job_handler = CallbackQueryHandler(_handle_force_ticket_job, pattern="^admin_force_ticket_job$")
admin_help_handler = CallbackQueryHandler(_handle_admin_help, pattern="^admin_help$")

# Lista Final para Exportação
all_admin_handlers = [
    admin_command_handler,
    delete_player_handler,
    inspect_item_handler,
    force_daily_handler,
    find_player_handler,
    debug_player_handler,
    get_id_command_handler,
    fixme_handler,
    admin_main_handler,
    admin_force_daily_callback_handler,
    admin_event_menu_handler,
    admin_force_start_handler,
    admin_force_end_handler,
    admin_force_ticket_handler,
    admin_force_ticket_job_handler,
    clear_cache_conv_handler, # ✅ Restaurado
    test_event_conv_handler,  # ✅ Restaurado
    grant_item_conv_handler, 
    # sell_gems_conv_handler, # Mantido comentado
    my_data_handler,
    reset_pvp_now_handler,
    generate_equip_conv_handler,
    file_id_conv_handler,
    premium_panel_handler,
    reset_panel_conversation_handler,
    grant_skill_conv_handler,
    grant_skin_conv_handler,
    player_management_conv_handler, 
    admin_help_handler,
    delete_player_conv_handler, # ✅ Restaurado
    hard_respec_all_handler, 
    clean_clan_handler, 
    change_id_conv_handler,     # ✅ Restaurado
    fix_ghost_clan_handler,
    fix_clan_conv_handler,      # ✅ Restaurado
    debug_skill_handler,
    fix_tomos_handler,
    clean_market_handler,
    fix_premium_handler
]