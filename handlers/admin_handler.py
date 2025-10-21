# handlers/admin_handler.py

from __future__ import annotations
import os
import io
import logging
import json
from typing import Optional

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

# --- Imports dos Módulos do Bot ---
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
)
from modules import game_data
from handlers.admin.utils import ensure_admin 
from kingdom_defense.engine import event_manager
# No topo de admin_handler.py
from modules.player.core import _player_cache, players_collection
# No topo de admin_handler.py
from modules.player.queries import _normalize_char_name
# --- Constantes ---
ADMIN_ID = int(os.getenv("ADMIN_ID"))
logger = logging.getLogger(__name__)
HTML = "HTML"

(SELECT_CACHE_ACTION, ASK_USER_FOR_CACHE_CLEAR) = range(2)
(SELECT_TEST_ACTION, ASK_WAVE_NUMBER) = range(2, 4)

# =========================================================
# MENUS E TECLADOS (Keyboards)
# =========================================================

async def debug_player_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_to_check = None
    try:
        user_id_to_check = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Por favor, fornece um ID de utilizador. Uso: /debug_player <user_id>")
        return
        
    report = [f"🕵️ **Relatório de Diagnóstico para o Jogador `{user_id_to_check}`** 🕵️\n"]

    # 1. Verifica a Cache em Memória
    if user_id_to_check in _player_cache:
        player_cache_data = _player_cache[user_id_to_check]
        char_name = player_cache_data.get('character_name', 'Nome não encontrado')
        report.append(f"✅ **Cache em Memória:** Encontrado! (Nome: `{char_name}`)")
    else:
        report.append("❌ **Cache em Memória:** Vazio.")

    # 2. Verifica a Base de Dados MongoDB
    if players_collection is not None:
        try:
            player_doc = players_collection.find_one({"_id": user_id_to_check})
            if player_doc:
                char_name = player_doc.get('character_name', 'Nome não encontrado')
                report.append(f"✅ **MongoDB:** Encontrado! (Nome: `{char_name}`)")
            else:
                report.append("❌ **MongoDB:** Não encontrado.")
        except Exception as e:
            report.append(f"⚠️ **MongoDB:** Erro ao aceder à base de dados: {e}")
    else:
        report.append("🚫 **MongoDB:** Conexão com a base de dados não existe (está a `None`).")

    await update.message.reply_text("\n".join(report), parse_mode="HTML")

# Em handlers/admin_handler.py

async def find_player_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando de admin para encontrar um jogador pelo nome do personagem.
    Uso: /find_player <nome do personagem>
    """
    user_id = update.effective_user.id
    # if user_id not in ADMIN_IDS: return

    if not context.args:
        await update.message.reply_text("Por favor, especifica um nome. Uso: /find_player <nome>")
        return

    char_name_to_find = " ".join(context.args)
    normalized_name = _normalize_char_name(char_name_to_find)

    # --- CORREÇÃO APLICADA AQUI ---
    if players_collection is None:
        await update.message.reply_text("Erro: Conexão com a base de dados não disponível.")
        return

    player_doc = players_collection.find_one({"character_name_normalized": normalized_name})

    if player_doc:
        found_id = player_doc.get('_id')
        found_name = player_doc.get('character_name', 'Nome não encontrado')
        report = (
            f"✅ **Jogador Encontrado!**\n\n"
            f"👤 **Nome:** `{found_name}`\n"
            f"🆔 **User ID:** `{found_id}`"
        )
        await update.message.reply_text(report, parse_mode="HTML")
    else:
        await update.message.reply_text(f"❌ Nenhum jogador encontrado com o nome '{char_name_to_find}'.")


async def get_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    thread_id = update.effective_message.message_thread_id

    # Usando formatação HTML com a tag <code> para um visual similar
    text = (
        f"<b>INFORMAÇÕES DE ID:</b>\n"
        f"--------------------------\n"
        f"ID do Grupo (chat_id): <code>{chat_id}</code>\n"
        f"ID do Tópico (thread_id): <code>{thread_id}</code>"
    )
    # Trocando o parse_mode para HTML
    await update.message.reply_text(text, parse_mode="HTML")

def _admin_test_menu_kb() -> InlineKeyboardMarkup:
    """O submenu de teste para o evento de defesa."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Iniciar em Wave Específica", callback_data="test_start_at_wave")],
        # Você pode adicionar mais botões de teste aqui no futuro
        # [InlineKeyboardButton("👻 Adicionar Jogadores-Fantasma", callback_data="test_add_dummies")],
        [InlineKeyboardButton("⬅️ Voltar ao Painel Principal", callback_data="admin_main")],
    ])

def _admin_event_menu_kb() -> InlineKeyboardMarkup:
    """O submenu de gerenciamento de eventos."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎟️ Entregar Ticket de Defesa", callback_data="admin_event_force_ticket")],
        [InlineKeyboardButton("▶️ Forçar Início do Evento", callback_data="admin_event_force_start")],
        [InlineKeyboardButton("⏹️ Forçar Fim do Evento", callback_data="admin_event_force_end")],
        [InlineKeyboardButton("⬅️ Voltar ao Painel Principal", callback_data="admin_main")],
    ])

def _admin_menu_kb() -> InlineKeyboardMarkup:
    """Menu principal do admin, agora com o botão para o submenu de eventos."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 𓂀 𝔼𝕟𝕥𝕣𝕖𝕘𝕒𝕣 𝕀𝕥𝕖𝕟𝕤 (Stackable) 𓂀", callback_data="admin_grant_item")],
        [InlineKeyboardButton("🛠️ 𓂀 𝔾𝕖𝕣𝕒𝕣 𝔼𝕢𝕦𝕚𝕡𝕒𝕞𝕖𝕟𝕥𝕠 𓂀", callback_data="admin_generate_equip")],
        [InlineKeyboardButton("🔁 𓂀 𝔽𝕠𝕣ç𝕒𝕣 𝕕𝕚á𝕣𝕚𝕠𝕤 (ℂ𝕣𝕚𝕤𝕥𝕒𝕚𝕤) 𓂀", callback_data="admin_force_daily")],
        [InlineKeyboardButton("👑 𓂀 ℙ𝕣𝕖𝕞𝕚𝕦𝕞 𓂀", callback_data="admin_premium")],
        [InlineKeyboardButton("🎉 𓂀 𝔾𝕖𝕣𝕖𝕟𝕔𝕚𝕒𝕣 𝔼𝕧𝕖𝕟𝕥𝕠𝕤 𓂀 🎉", callback_data="admin_event_menu")],
        [InlineKeyboardButton("🔬 𓂀 Painel de Teste de Evento 𓂀 🔬", callback_data="admin_test_menu")],
        [InlineKeyboardButton("📁 𓂀 𝔾𝕖𝕣𝕖𝕟𝕔𝕚𝕒𝕣 𝔽𝕚𝕝𝕖 𝕀𝔻𝕤 𓂀", callback_data="admin_file_ids")],
        [InlineKeyboardButton("🧹 𓂀 ℝ𝕖𝕤𝕖𝕥/ℝ𝕖𝕤𝕡𝕖𝕔 𓂀", callback_data="admin_reset_menu")],
        [InlineKeyboardButton("🧽 𓂀 𝕃𝕚𝕞𝕡𝕒𝕣 ℂ𝕒𝕔𝕙𝕖 𓂀", callback_data="admin_clear_cache")],
        [InlineKeyboardButton("🔄 𝐑𝐞𝐬𝐞𝐭𝐚𝐫 𝐄𝐬𝐭𝐚𝐝𝐨 (/𝐫𝐞𝐬𝐞𝐭_𝐬𝐭𝐚𝐭𝐞)", callback_data="admin_reset_state_hint")],
    ])

# =========================================================
# FUNÇÕES DE LÓGICA DO ADMIN
# =========================================================

def _is_admin(update: Update) -> bool:
    return bool(update.effective_user and update.effective_user.id == ADMIN_ID)

# --- Funções de Ajuda (Helpers) ---
async def _safe_answer(update: Update):
    if query := update.callback_query:
        try:
            await query.answer()
        except BadRequest:
            pass 

async def _safe_edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup: InlineKeyboardMarkup | None = None):
    if query := update.callback_query:
        try:
            await query.edit_message_text(text, parse_mode=HTML, reply_markup=reply_markup)
            return
        except BadRequest:
            pass # A mensagem é a mesma ou a query expirou
    
    # Se edit falhar, envia uma nova mensagem
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=HTML, reply_markup=reply_markup)

async def _handle_admin_test_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entrada para o menu de teste de evento."""
    await _safe_answer(update)
    await _safe_edit_text(update, context, "🔬 **Painel de Teste de Evento**\n\nO que você gostaria de fazer?", _admin_test_menu_kb())
    return SELECT_TEST_ACTION

async def _test_ask_wave_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pede ao admin para enviar o número da wave."""
    await _safe_answer(update)
    await _safe_edit_text(update, context, "🔢 Por favor, envie o número da wave que você deseja testar.\n\nUse /cancelar para voltar.")
    return ASK_WAVE_NUMBER

async def _test_start_specific_wave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o evento de teste na wave especificada pelo admin (no chat privado do admin)."""
    try:
        wave_num = int(update.message.text)
    except (ValueError, TypeError):
        await update.message.reply_text("❌ Isso não é um número válido. Tente novamente ou use /cancelar.")
        return ASK_WAVE_NUMBER # Mantém na mesma etapa da conversa
    
    result = event_manager.start_event_at_wave(wave_num)

    if "error" in result:
        await update.message.reply_text(result["error"])
    else:
        await update.message.reply_text(result["success"] + "\n\nO evento está ativo. Use os comandos de jogador em um chat separado para interagir.")
    
    # Encerra a conversa e mostra o menu de admin novamente
    # (A lógica de enviar a mensagem de batalha para o admin foi removida para evitar confusão,
    # já que a batalha agora é privada para cada jogador)
    await _send_admin_menu(update.effective_chat.id, context)
    return ConversationHandler.END

async def _test_cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a operação de teste e retorna ao menu principal."""
    await update.message.reply_text("Operação de teste cancelada.")
    await _send_admin_menu(update.effective_chat.id, context)
    return ConversationHandler.END

# --- Funções do Painel Principal e Comandos ---
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎛️ <b>Painel do Admin</b>\nEscolha uma opção:",
        reply_markup=_admin_menu_kb(),
        parse_mode=HTML,
    )

async def _handle_admin_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _safe_answer(update)
    await _safe_edit_text(update, context, "🎛️ <b>Painel do Admin</b>\nEscolha uma opção:", _admin_menu_kb())

async def _delete_player_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /delete_player <user_id>")
        return
    try:
        user_id_to_delete = int(context.args[0])
        if delete_player(user_id_to_delete):
            await update.message.reply_text(f"✅ Jogador com ID {user_id_to_delete} foi apagado com sucesso.")
        else:
            await update.message.reply_text(f"⚠️ Jogador com ID {user_id_to_delete} não foi encontrado.")
    except (ValueError, IndexError):
        await update.message.reply_text("Por favor, forneça um ID de usuário numérico válido.")
    except Exception as e:
        await update.message.reply_text(f"Ocorreu um erro: {e}")

# --- Funções de Eventos ---
async def _handle_admin_event_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _safe_answer(update)
    await _safe_edit_text(update, context, "🎉 **Painel de Gerenciamento de Eventos**", _admin_event_menu_kb())

async def _handle_force_start_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia o evento e anuncia no grupo principal."""
    query = update.callback_query
    
    result = event_manager.start_event()

    if "error" in result:
        await query.answer(result["error"], show_alert=True)
        return

    # Se o evento iniciou com sucesso, avisa o admin e envia o anúncio no grupo
    await query.answer("✅ Evento iniciado com sucesso!", show_alert=True)
    
    # Anuncia o início do evento no grupo para os jogadores
    # (Você precisará ter as constantes ID_GRUPO_EVENTOS e ID_TOPICO_EVENTOS definidas neste arquivo ou importá-las)
    ID_GRUPO_EVENTOS = -1002881364171  # Exemplo
    ID_TOPICO_EVENTOS = 10340 # Exemplo
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Ver Evento ⚔️", callback_data='show_events_menu')]
    ])
    
    await context.bot.send_message(
        chat_id=ID_GRUPO_EVENTOS,
        message_thread_id=ID_TOPICO_EVENTOS,
        text="📢 **ATENÇÃO, HERÓIS DE ELDORA!** 📢\n\nUma nova invasão ameaça nosso reino! Preparem-se para a batalha!",
        reply_markup=keyboard,
        parse_mode=HTML
    )

async def _handle_force_end_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    message = event_manager.end_event()
    await update.callback_query.answer(message, show_alert=True)

async def _handle_force_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _safe_answer(update)
    user_id = update.effective_user.id
    player_data = get_player_data(user_id)
    item_id = 'ticket_defesa_reino'
    add_item_to_inventory(player_data, item_id, 1)
    save_player_data(user_id, player_data)
    await update.callback_query.answer(f"🎟️ Você recebeu 1x {item_id}!", show_alert=True)

# --- Funções de Cristais Diários ---
async def _handle_admin_force_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.jobs import force_grant_daily_crystals
    await _safe_answer(update)
    await _safe_edit_text(update, context, "⏳ Processando entrega de cristais diários...")
    granted_count = await force_grant_daily_crystals(context)
    feedback_text = f"✅ Executado! <b>{granted_count}</b> jogadores receberam os cristais diários."
    await _safe_edit_text(update, context, feedback_text, InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_main")]]))

async def _send_admin_menu(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(
        chat_id=chat_id,
        text="🎛️ <b>Painel do Admin</b>\nEscolha uma opção:",
        reply_markup=_admin_menu_kb(),
        parse_mode=HTML,
    )
    
async def force_daily_crystals_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.jobs import force_grant_daily_crystals
    await update.effective_message.reply_text("⏳ Processando entrega forçada de cristais...")
    granted_count = await force_grant_daily_crystals(context)
    await update.effective_message.reply_text(f"✅ Executado! <b>{granted_count}</b> jogadores receberam os cristais.", parse_mode=HTML)

# --- Lógica da Conversa de Limpeza de Cache ---
async def _cache_entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update): return ConversationHandler.END
    keyboard = [
        [InlineKeyboardButton("👤 Limpar cache de UM jogador", callback_data="cache_clear_one")],
        [InlineKeyboardButton("🗑️ Limpar TODO o cache (Cuidado!)", callback_data="cache_clear_all_confirm")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="admin_main")],
    ]
    text = "🧽 **Gerenciamento de Cache**\n\nEscolha uma opção:"
    await _safe_edit_text(update, context, text, InlineKeyboardMarkup(keyboard))
    return SELECT_CACHE_ACTION

async def _cache_ask_for_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _safe_answer(update)
    await _safe_edit_text(update, context, "👤 Por favor, envie o **User ID** ou o **nome exato do personagem**.\n\nUse /cancelar para voltar.")
    return ASK_USER_FOR_CACHE_CLEAR

async def _cache_clear_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    target_input = update.message.text
    user_id, pdata, found_by = None, None, "ID/Nome"
    try:
        user_id = int(target_input)
        pdata = get_player_data(user_id)
        found_by = "ID"
    except ValueError:
        found = find_player_by_name(target_input)
        if found:
            user_id, pdata = found
            found_by = "Nome"
    
    if pdata:
        was_in_cache = clear_player_cache(user_id)
        msg = f"✅ Cache para **{pdata.get('character_name')}** (`{user_id}`) foi limpo." if was_in_cache else f"ℹ️ Jogador **{pdata.get('character_name')}** (`{user_id}`) encontrado, mas não estava no cache."
        await update.message.reply_text(msg, parse_mode=HTML)
    else:
        await update.message.reply_text(f"❌ Não foi possível encontrar um jogador com o {found_by} fornecido.")
    await _send_admin_menu(update.effective_chat.id, context)
    return ConversationHandler.END

async def _cache_confirm_clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _safe_answer(update)
    keyboard = [
        [InlineKeyboardButton("✅ Sim, tenho certeza", callback_data="cache_do_clear_all")],
        [InlineKeyboardButton("❌ Não, voltar", callback_data="cache_main_menu")],
    ]
    await _safe_edit_text(update, context, "⚠️ **ATENÇÃO!**\n\nIsso pode causar uma pequena lentidão temporária no bot.\n\n**Você tem certeza?**", InlineKeyboardMarkup(keyboard))
    return SELECT_CACHE_ACTION

async def _cache_do_clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _safe_answer(update)
    count = clear_all_player_cache()
    await _safe_edit_text(update, context, f"🗑️ Cache completo foi limpo.\n({count} jogadores removidos da memória).", _admin_menu_kb())
    return ConversationHandler.END

async def _cache_cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operação cancelada.")
    await _send_admin_menu(update.effective_chat.id, context)
    return ConversationHandler.END

# --- Comando de Inspeção de Itens ---
async def inspect_item_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /inspect_item <item_id>")
        return
    item_id = context.args[0]
    item_info = game_data.ITEMS_DATA.get(item_id, f"ITEM '{item_id}' NÃO ENCONTRADO.")
    info_str = json.dumps(item_info, indent=2, ensure_ascii=False)
    await update.message.reply_text(f"<b>DEBUG PARA '{item_id}':</b>\n\n<pre>{info_str}</pre>", parse_mode=HTML)

async def fix_my_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Corrige o estado de um jogador afetado por bugs de level up anteriores.
    1. Zera o XP atual para um começo limpo no nível.
    2. Recalcula os pontos de atributo disponíveis.
    """
    user_id = update.effective_user.id

    # Usa o ADMIN_ID do ficheiro em vez de um valor fixo
    if user_id != ADMIN_ID:
        await update.message.reply_text("Você não tem permissão para usar este comando.")
        return

    player_data = get_player_data(user_id)
    if not player_data:
        await update.message.reply_text("Erro: Jogador não encontrado.")
        return

    # AÇÃO 1: Zerar o XP atual
    player_data['xp'] = 0
    
    # AÇÃO 2: Recalcular os pontos de atributo
    allowed = allowed_points_for_level(player_data)
    spent = compute_spent_status_points(player_data)
    player_data['stat_points'] = max(0, allowed - spent)
    
    save_player_data(user_id, player_data)

    await update.message.reply_text(
        f"✅ Personagem corrigido!\n"
        f"XP foi zerado e os pontos de atributo foram recalculados.\n"
        f"Use o comando de perfil para ver o resultado."
    )

async def my_data_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Envia os dados do jogador como um ficheiro JSON para diagnóstico,
    evitando o limite de caracteres da mensagem.
    """
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    player_data = get_player_data(user_id)
    if not player_data:
        await update.message.reply_text("Não foi possível carregar os seus dados.")
        return
        
    player_data.pop('_id', None)
    
    # Converte os dados para uma string formatada
    data_str = json.dumps(player_data, indent=2, ensure_ascii=False)
    
    # Prepara a string para ser enviada como um ficheiro em memória
    json_bytes = data_str.encode('utf-8')
    input_file = io.BytesIO(json_bytes)
    
    # Envia o ficheiro como um documento
    await update.message.reply_document(
        document=input_file,
        filename="seus_dados.json",
        caption="Aqui estão os seus dados brutos. Por favor, partilhe o conteúdo deste ficheiro."
    )

# =========================================================
# EXPORTAÇÃO DE HANDLERS PARA O REGISTRY
# =========================================================

from kingdom_defense.handler import _get_battle_keyboard

# Handlers de Comando
admin_command_handler = CommandHandler("admin", admin_command, filters=filters.User(ADMIN_ID))
delete_player_handler = CommandHandler("delete_player", _delete_player_command, filters=filters.User(ADMIN_ID))
inspect_item_handler = CommandHandler("inspect_item", inspect_item_command, filters=filters.User(ADMIN_ID))
force_daily_handler = CommandHandler("forcar_cristais", force_daily_crystals_cmd, filters=filters.User(ADMIN_ID))
my_data_handler = CommandHandler("mydata", my_data_command, filters=filters.User(ADMIN_ID))
# Handlers de CallbackQuery (Botões)
admin_main_handler = CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$")
admin_force_daily_callback_handler = CallbackQueryHandler(_handle_admin_force_daily, pattern="^admin_force_daily$")

# Handlers para os botões do submenu de eventos
find_player_handler = CommandHandler("find_player", find_player_command)
debug_player_handler = CommandHandler("debug_player", debug_player_data)
admin_event_menu_handler = CallbackQueryHandler(_handle_admin_event_menu, pattern="^admin_event_menu$")
admin_force_start_handler = CallbackQueryHandler(_handle_force_start_event, pattern="^admin_event_force_start$") 
admin_force_end_handler = CallbackQueryHandler(_handle_force_end_event, pattern="^admin_event_force_end$")
admin_force_ticket_handler = CallbackQueryHandler(_handle_force_ticket, pattern="^admin_event_force_ticket$")
get_id_command_handler = CommandHandler("get_id", get_id_command, filters=filters.User(ADMIN_ID))
#get_id_command_handler = CommandHandler("get_id", get_id_command)
fixme_handler = CommandHandler("fixme", fix_my_character, filters=filters.User(ADMIN_ID))

# Handler de Conversa para Limpeza de Cache
clear_cache_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(_cache_entry_point, pattern=r"^admin_clear_cache$")],
    states={
        SELECT_CACHE_ACTION: [
            CallbackQueryHandler(_cache_ask_for_user, pattern="^cache_clear_one$"),
            CallbackQueryHandler(_cache_confirm_clear_all, pattern="^cache_clear_all_confirm$"),
            CallbackQueryHandler(_cache_do_clear_all, pattern="^cache_do_clear_all$"),
            CallbackQueryHandler(_handle_admin_main, pattern="^cache_cancel$"), # Volta ao menu principal
        ],
        ASK_USER_FOR_CACHE_CLEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, _cache_clear_user)],
    },
    fallbacks=[
        CommandHandler("cancelar", _cache_cancel_conv),
        CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$")
    ],
    per_message=False
)

test_event_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(_handle_admin_test_menu, pattern=r"^admin_test_menu$")],
    states={
        SELECT_TEST_ACTION: [
            CallbackQueryHandler(_test_ask_wave_number, pattern="^test_start_at_wave$"),
        ],
        ASK_WAVE_NUMBER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, _test_start_specific_wave)
        ],
    },
    fallbacks=[
        CommandHandler("cancelar", _test_cancel_conv),
        CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$") # Voltar ao menu
    ],
    per_message=False,
    # Permite que outros handlers funcionem enquanto a conversa está ativa
    block=False 
)

all_admin_handlers = [
    admin_command_handler,
    delete_player_handler,
    inspect_item_handler,
    force_daily_handler,
    find_player_handler,
    debug_player_handler,
    get_id_command_handler,
    fixme_handler, # Novo
    admin_main_handler,
    admin_force_daily_callback_handler,
    admin_event_menu_handler,
    admin_force_start_handler,
    admin_force_end_handler,
    admin_force_ticket_handler,
    clear_cache_conv_handler,
    test_event_conv_handler,
    my_data_handler,
]