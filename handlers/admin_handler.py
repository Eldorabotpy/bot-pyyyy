# (VERSÃO CORRIGIDA DO BUG DE NOTIFICAÇÃO E DO NAMEERROR)

from __future__ import annotations
import os
import io
import logging 
import json
import sys
import asyncio # Importado para o loop de reset
from typing import Optional
from handlers.jobs import distribute_kingdom_defense_ticket_job
from handlers.admin.grant_item import grant_item_conv_handler 
from handlers.admin.sell_gems import sell_gems_conv_handler 
from handlers.admin.generate_equip import generate_equip_conv_handler 
from handlers.admin.file_id_conv import file_id_conv_handler 
from handlers.admin.premium_panel import premium_panel_handler 
from handlers.admin.reset_panel import reset_panel_conversation_handler 
from handlers.admin.grant_skill import grant_skill_conv_handler
from handlers.admin.grant_skin import grant_skin_conv_handler
from handlers.admin.player_management_handler import player_management_conv_handler
from modules.player.queries import _normalize_char_name
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

# --- BLOCO DE IMPORTAÇÃO CORRIGIDO ---
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
    reset_stats_and_refund_points,  # <--- ADICIONADO
    iter_players,                   # <--- ADICIONADO
)
# ------------------------------------

from modules import game_data
from handlers.jobs import reset_pvp_season, force_grant_daily_crystals 
from handlers.admin.utils import ensure_admin
from kingdom_defense.engine import event_manager
from modules.player.core import _player_cache, players_collection
from modules.player.queries import _normalize_char_name


logger = logging.getLogger(__name__) 

from handlers.admin.utils import ADMIN_LIST, ensure_admin

HTML = "HTML" 

(SELECT_CACHE_ACTION, ASK_USER_FOR_CACHE_CLEAR) = range(2)
(SELECT_TEST_ACTION, ASK_WAVE_NUMBER) = range(2, 4)
(ASK_DELETE_ID, CONFIRM_DELETE_ACTION) = range(4, 6)
# =========================================================
# MENUS E TECLADOS (Keyboards)
# =========================================================

async def _reset_pvp_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de admin para resetar imediatamente os pontos PvP."""
    if not await ensure_admin(update): # Verifica se é admin
        return

    await update.message.reply_text("⏳ <b>Iniciando reset manual da temporada PvP...</b>\nIsso pode levar um momento.", parse_mode=HTML) 

    try:
        # Chama a função de reset que já existe em jobs.py
        await reset_pvp_season(context)
        await update.message.reply_text("✅ Reset da temporada PvP concluído com sucesso!")
    except Exception as e:
        logger.error(f"Erro ao executar reset manual de PvP: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Ocorreu um erro durante o reset manual: {e}")

async def debug_player_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de admin para diagnosticar cache e DB para um jogador."""
    if not await ensure_admin(update): return 

    user_id_to_check = None
    try:
        user_id_to_check = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Por favor, fornece um ID de utilizador. Uso: /debug_player <user_id>")
        return

    report = [f"🕵️ <b>Relatório de Diagnóstico para o Jogador</b> <code>{user_id_to_check}</code> 🕵️\n"] 

    # 1. Verifica a Cache em Memória
    if user_id_to_check in _player_cache:
        player_cache_data = _player_cache[user_id_to_check]
        char_name = player_cache_data.get('character_name', 'Nome não encontrado')
        report.append(f"✅ <b>Cache em Memória:</b> Encontrado! (Nome: <code>{char_name}</code>)") 
    else:
        report.append("❌ <b>Cache em Memória:</b> Vazio.") 

    # 2. Verifica a Base de Dados MongoDB
    if players_collection is not None:
        try:
            player_doc = players_collection.find_one({"_id": user_id_to_check})
            if player_doc:
                char_name = player_doc.get('character_name', 'Nome não encontrado')
                report.append(f"✅ <b>MongoDB:</b> Encontrado! (Nome: <code>{char_name}</code>)") 
            else:
                report.append("❌ <b>MongoDB:</b> Não encontrado.") 
        except Exception as e:
            report.append(f"⚠️ <b>MongoDB:</b> Erro ao aceder à base de dados: {e}") 
    else:
        report.append("🚫 <b>MongoDB:</b> Conexão com a base de dados não existe (está a <code>None</code>).") 

    await update.message.reply_text("\n".join(report), parse_mode=HTML) 

async def find_player_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando de admin para encontrar um jogador pelo nome do personagem.
    Uso: /find_player <nome do personagem>
    """
    if not await ensure_admin(update): return 

    if not context.args:
        await update.message.reply_text("Por favor, especifica um nome. Uso: /find_player <nome>")
        return

    char_name_to_find = " ".join(context.args)
    normalized_name = _normalize_char_name(char_name_to_find)

    if players_collection is None:
        await update.message.reply_text("Erro: Conexão com a base de dados não disponível.")
        return

    try:
        player_doc = players_collection.find_one({"character_name_normalized": normalized_name})
    except Exception as e:
        logger.error(f"Erro ao buscar jogador '{normalized_name}' no MongoDB: {e}")
        await update.message.reply_text("Erro ao consultar a base de dados.")
        return


    if player_doc:
        found_id = player_doc.get('_id')
        found_name = player_doc.get('character_name', 'Nome não encontrado')
        report = (
            f"✅ <b>Jogador Encontrado!</b>\n\n"
            f"👤 <b>Nome:</b> <code>{found_name}</code>\n"
            f"🆔 <b>User ID:</b> <code>{found_id}</code>"
        ) 
        await update.message.reply_text(report, parse_mode=HTML) 
    else:
        await update.message.reply_text(f"❌ Nenhum jogador encontrado com o nome '{char_name_to_find}'.")


async def get_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando LIBERADO para obter IDs de chat e tópico.
    (Trava de segurança removida para facilitar configuração)
    """
    # if not await ensure_admin(update): return  <-- REMOVIDO
    
    chat_id = update.effective_chat.id
    thread_id = getattr(update.effective_message, 'message_thread_id', None)

    # Monta o texto informativo
    topic_text = f"🆔 <b>Topic ID:</b> <code>{thread_id}</code>" if thread_id else "🆔 <b>Topic ID:</b> <i>Geral (None)</i>"

    text = (
        f"<b>🕵️ INSPETOR DE IDs</b>\n"
        f"--------------------------\n"
        f"👤 <b>Seu User ID:</b> <code>{update.effective_user.id}</code>\n"
        f"🏠 <b>Group ID:</b> <code>{chat_id}</code>\n"
        f"{topic_text}\n\n"
        f"<i>Copie estes IDs para configurar os logs de mercado.</i>"
    )

    await update.message.reply_text(text, parse_mode=HTML)

def _admin_test_menu_kb() -> InlineKeyboardMarkup:
    """O submenu de teste para o evento de defesa."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Iniciar em Wave Específica", callback_data="test_start_at_wave")],
        [InlineKeyboardButton("⬅️ Voltar ao Painel Principal", callback_data="admin_main")],
    ])

def _admin_event_menu_kb() -> InlineKeyboardMarkup:
    """O submenu de gerenciamento de eventos."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎟️ Entregar Ticket de Defesa", callback_data="admin_event_force_ticket")],
        [InlineKeyboardButton("📨 FORÇAR JOB DE TICKETS (TODOS)", callback_data="admin_force_ticket_job")],
        [InlineKeyboardButton("▶️ Forçar Início do Evento", callback_data="admin_event_force_start")],
        [InlineKeyboardButton("⏹️ Forçar Fim do Evento", callback_data="admin_event_force_end")],
        [InlineKeyboardButton("⬅️ Voltar ao Painel Principal", callback_data="admin_main")],
    ])

def _admin_menu_kb() -> InlineKeyboardMarkup:
    """Menu principal do admin, agora com o botão para editar jogador."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 𓂀 𝔼𝕟𝕥𝕣𝕖𝕘𝕒𝕣 𝕀𝕥𝕖𝕟𝕤 (Stackable) 𓂀", callback_data="admin_grant_item")],
        [InlineKeyboardButton("💎 𓂀 𝕍𝕖𝕟𝕕𝕖𝕣 𝔾𝕖𝕞𝕒𝕤 𓂀", callback_data="admin_sell_gems")],
        [InlineKeyboardButton("🛠️ 𓂀 𝔾𝕖𝕣𝕒𝕣 𝔼𝕢𝕦𝕚𝕡𝕒𝕞𝕖𝕟𝕥𝕠 𓂀", callback_data="admin_generate_equip")],
        [InlineKeyboardButton("📚 𓂀 𝔼𝕟𝕤𝕚𝕟𝕒𝕣 ℍ𝕒𝕓𝕚𝕝𝕚𝕕𝕒𝕕𝕖 (Skill) 𓂀", callback_data="admin_grant_skill")],
        [InlineKeyboardButton("🎨 𓂀 𝔼𝕟𝕥𝕣𝕖𝕘𝕒𝕣 𝔸𝕡𝕒𝕣𝕖̂𝕟𝕔𝕚𝕒 (Skin) 𓂀", callback_data="admin_grant_skin")],
        [InlineKeyboardButton("👥 𓂀 𝔾𝕖𝕣𝕖𝕟𝕔𝕚𝕒𝕣 𝕁𝕠𝕘𝕒𝕕𝕠𝕣𝕖𝕤 𓂀", callback_data="admin_pmanage_main")],
        [InlineKeyboardButton("👤 𓂀 𝔼𝕕𝕚𝕥𝕒𝕣 𝕁𝕠𝕘𝕒𝕕𝕠𝕣 𓂀", callback_data="admin_edit_player")], 
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

# =========================================================
# FUNÇÕES DE LÓGICA DO ADMIN
# =========================================================

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
            pass 

    # Se edit falhar, envia uma nova mensagem
    chat_id = update.effective_chat.id
    if chat_id:
        try:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=HTML, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem fallback em _safe_edit_text para chat {chat_id}: {e}")
    else:
        logger.warning("_safe_edit_text não conseguiu determinar chat_id.")


# --- Lógica do Painel de Teste (ConversationHandler) ---
async def _handle_admin_test_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entrada para o menu de teste de evento."""
    if not await ensure_admin(update): return ConversationHandler.END
    await _safe_answer(update)
    await _safe_edit_text(update, context, "🔬 <b>Painel de Teste de Evento</b>\n\nO que você gostaria de fazer?", _admin_test_menu_kb())
    return SELECT_TEST_ACTION

async def _test_ask_wave_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pede ao admin para enviar o número da wave."""
    if not await ensure_admin(update): return ConversationHandler.END
    await _safe_answer(update)
    await _safe_edit_text(update, context, "🔢 Por favor, envie o número da wave que você deseja testar.\n\nUse /cancelar para voltar.")
    return ASK_WAVE_NUMBER

async def _test_start_specific_wave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o evento de teste na wave especificada pelo admin."""
    try:
        wave_num = int(update.message.text)
        if wave_num <= 0: raise ValueError("Wave deve ser positiva")
    except (ValueError, TypeError):
        await update.message.reply_text("❌ Isso não é um número válido (deve ser maior que 0). Tente novamente ou use /cancelar.")
        return ASK_WAVE_NUMBER

    result = event_manager.start_event_at_wave(wave_num) # SÍNCRONO

    if "error" in result:
        await update.message.reply_text(result["error"])
    else:
        await update.message.reply_text(result["success"] + "\n\nO evento está ativo. Use os comandos de jogador em um chat separado para interagir.")

    await _send_admin_menu(update.effective_chat.id, context)
    return ConversationHandler.END

async def _test_cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a operação de teste e retorna ao menu principal."""
    await update.message.reply_text("Operação de teste cancelada.")
    await _send_admin_menu(update.effective_chat.id, context)
    return ConversationHandler.END

# --- Funções do Painel Principal e Comandos ---
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe o painel principal do admin."""
    if not await ensure_admin(update): return 
    await update.message.reply_text(
        "🎛️ <b>Painel do Admin</b>\nEscolha uma opção:",
        reply_markup=_admin_menu_kb(),
        parse_mode=HTML,
    )

async def _handle_admin_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Atualiza a mensagem para mostrar o painel principal do admin."""
    if not await ensure_admin(update): return
    await _safe_answer(update)
    await _safe_edit_text(update, context, "🎛️ <b>Painel do Admin</b>\nEscolha uma opção:", _admin_menu_kb())

async def _delete_player_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de admin para apagar um jogador."""
    if not await ensure_admin(update): return

    if not context.args:
        await update.message.reply_text("Uso: /delete_player <user_id>")
        return
    try:
        user_id_to_delete = int(context.args[0])
        deleted_ok = await delete_player(user_id_to_delete)
        if deleted_ok:
            await update.message.reply_text(f"✅ Jogador com ID {user_id_to_delete} foi apagado com sucesso.")
        else:
            await update.message.reply_text(f"⚠️ Jogador com ID {user_id_to_delete} não foi encontrado.")
    except (ValueError, IndexError):
        await update.message.reply_text("Por favor, forneça um ID de usuário numérico válido.")
    except Exception as e:
        logger.error(f"Erro ao deletar jogador {context.args[0]}: {e}", exc_info=True)
        await update.message.reply_text(f"Ocorreu um erro ao tentar apagar o jogador.")

# --- Funções de Eventos ---
async def _handle_admin_event_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o submenu de gerenciamento de eventos."""
    if not await ensure_admin(update): return
    await _safe_answer(update)
    await _safe_edit_text(update, context, "🎉 <b>Painel de Gerenciamento de Eventos</b>", _admin_event_menu_kb())

async def _handle_force_start_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Apenas força o início do evento Kingdom Defense internamente."""
    query = None
    if update.callback_query:
        query = update.callback_query
        user_id = query.from_user.id
        if not await ensure_admin(update): return 
        await query.answer("Processando...") 
    elif update.message:
        user_id = update.message.from_user.id
        if not await ensure_admin(update): return 
    else:
        logger.warning("Não foi possível determinar o usuário em _handle_force_start_event")
        return

    logger.info(f"Admin {user_id} forçando início do evento Kingdom Defense.")

    result = await event_manager.start_event()

    if not isinstance(result, dict):
        logger.error(f"start_event retornou um tipo inesperado: {type(result)}")
        error_msg = "❌ Ocorreu um erro inesperado ao iniciar o evento."
        if query:
            await query.edit_message_text(error_msg)
        elif update.message:
            await update.message.reply_text(error_msg)
        return

    if "error" in result:
        error_msg = f"⚠️ Erro: {result['error']}"
        if query:
            await query.answer(result["error"], show_alert=True)
        elif update.message:
            await update.message.reply_text(error_msg)
        return

    success_msg = result.get("success", "✅ Evento iniciado com sucesso!")
    if query:
        await query.answer(success_msg, show_alert=True)
    elif update.message:
        await update.message.reply_text(success_msg)
        
async def _handle_force_end_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Termina o evento manualmente."""
    query = update.callback_query 
    user_id = query.from_user.id

    if not await ensure_admin(update): return 
    await query.answer("Processando...") 

    logger.info(f"Admin {user_id} forçando fim do evento Kingdom Defense.")

    result = await event_manager.end_event(context) 

    if not isinstance(result, dict):
        logger.error(f"end_event retornou um tipo inesperado: {type(result)}")
        message = "❌ Ocorreu um erro inesperado ao terminar o evento."
    elif "error" in result:
        message = f"⚠️ Erro: {result['error']}"
    else:
        message = result.get("success", "✅ Evento encerrado com sucesso!")

    await query.answer(message, show_alert=True)

    try:
        await query.edit_message_text("Evento Kingdom Defense encerrado.")
    except Exception as e:
        logger.warning(f"Não foi possível editar mensagem após forçar fim do evento: {e}")

async def _handle_force_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entrega um ticket de defesa ao admin. (VERSÃO CORRIGIDA)"""
    query = update.callback_query
    if not query:
        return 

    if not await ensure_admin(update):
        await query.answer("Você não tem permissão.", show_alert=True)
        return
    
    user_id = update.effective_user.id
    item_id = 'ticket_defesa_reino'

    try:
        player_data = await get_player_data(user_id)
        if not player_data:
            await query.answer("Erro: Não foi possível carregar seus dados de jogador.", show_alert=True)
            return

        add_item_to_inventory(player_data, item_id, 1) # Síncrono
        await save_player_data(user_id, player_data)
        
        await query.answer(f"🎟️ Você recebeu 1x {item_id}!", show_alert=True)

    except Exception as e:
        logger.error(f"Erro ao entregar ticket para admin {user_id}: {e}", exc_info=True)
        await query.answer(f"Erro ao entregar o item: {e}", show_alert=True)

# --- Funções de Cristais Diários ---
async def _handle_admin_force_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Força a entrega dos cristais diários (via botão)."""
    if not await ensure_admin(update): return
    await _safe_answer(update)
    await _safe_edit_text(update, context, "⏳ Processando entrega de cristais diários...")
    try:
        granted_count = await force_grant_daily_crystals(context) 
        feedback_text = f"✅ Executado! <b>{granted_count}</b> jogadores receberam os cristais diários."
    except Exception as e:
        logger.error(f"Erro ao forçar cristais diários via botão: {e}", exc_info=True)
        feedback_text = f"❌ Erro ao processar: {e}"

    await _safe_edit_text(update, context, feedback_text, InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_main")]]))

# --- Lógica de Deletar Jogador (Botão) ---

async def _delete_entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo de deletar conta."""
    if not await ensure_admin(update): return ConversationHandler.END
    await _safe_answer(update)
    
    msg = (
        "💀 <b>DELETAR CONTA DE JOGADOR</b> 💀\n\n"
        "Por favor, envie o <b>User ID</b> ou o <b>Nome do Personagem</b> que deseja apagar.\n\n"
        "⚠️ <i>Esta ação é irreversível.</i>\n"
        "Digite /cancelar para voltar."
    )
    await _safe_edit_text(update, context, msg)
    return ASK_DELETE_ID

async def _delete_resolve_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Busca o usuário e pede confirmação final."""
    target_input = update.message.text
    user_id, pdata = None, None
    
    # Tenta achar por ID ou Nome (Mesma lógica do Cache)
    try:
        user_id = int(target_input)
        pdata = await get_player_data(user_id)
    except ValueError:
        found = await find_player_by_name(target_input)
        if found:
            user_id, pdata = found

    if not pdata or not user_id:
        await update.message.reply_text("❌ Jogador não encontrado. Tente novamente o ID ou Nome, ou use /cancelar.")
        return ASK_DELETE_ID

    # Salva no contexto para o próximo passo
    context.user_data['delete_target_id'] = user_id
    char_name = pdata.get('character_name', 'Desconhecido')
    lvl = pdata.get('level', 0)

    # Monta teclado de confirmação
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ SIM, APAGAR PARA SEMPRE", callback_data="confirm_delete_yes")],
        [InlineKeyboardButton("❌ NÃO! CANCELAR!", callback_data="admin_main")]
    ])

    report = (
        f"⚠️ <b>CONFIRMAÇÃO DE EXCLUSÃO</b> ⚠️\n\n"
        f"👤 <b>Nome:</b> {char_name}\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"📊 <b>Nível:</b> {lvl}\n\n"
        f"Você tem certeza absoluta que deseja apagar todos os dados deste jogador?"
    )
    
    await update.message.reply_text(report, reply_markup=kb, parse_mode=HTML)
    return CONFIRM_DELETE_ACTION

async def _delete_perform(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Executa a deleção após confirmação."""
    query = update.callback_query
    if not await ensure_admin(update): return ConversationHandler.END
    await query.answer()

    target_id = context.user_data.get('delete_target_id')
    if not target_id:
        await _safe_edit_text(update, context, "❌ Erro interno: ID perdido. Operação cancelada.")
        await _send_admin_menu(update.effective_chat.id, context)
        return ConversationHandler.END

    try:
        # Chama a função de deletar importada
        deleted_ok = await delete_player(target_id)
        
        if deleted_ok:
            await _safe_edit_text(update, context, f"✅ <b>SUCESSO!</b>\nO jogador {target_id} foi apagado da base de dados.")
        else:
            await _safe_edit_text(update, context, f"⚠️ Erro: O sistema disse que não encontrou o jogador {target_id} para apagar.")
            
    except Exception as e:
        logger.error(f"Erro ao deletar via botão admin: {e}", exc_info=True)
        await _safe_edit_text(update, context, f"❌ Ocorreu um erro crítico ao apagar: {e}")

    # Retorna ao menu após 3 segundos ou mostra botão
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="admin_main")]])
    await context.bot.send_message(chat_id=update.effective_chat.id, text="...", reply_markup=kb)
    return ConversationHandler.END

async def _delete_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a deleção."""
    context.user_data.pop('delete_target_id', None)
    await update.message.reply_text("Operação de deleção cancelada.")
    await _send_admin_menu(update.effective_chat.id, context)
    return ConversationHandler.END

async def _send_admin_menu(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia o menu principal do admin (usado como fallback)."""
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text="🎛️ <b>Painel do Admin</b>\nEscolha uma opção:",
            reply_markup=_admin_menu_kb(),
            parse_mode=HTML,
        )
    except Exception as e:
        logger.error(f"Falha ao enviar menu admin para chat {chat_id}: {e}")

async def force_daily_crystals_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Força a entrega dos cristais diários (via comando)."""
    if not await ensure_admin(update): return
    await update.effective_message.reply_text("⏳ Processando entrega forçada de cristais...")
    try:
        granted_count = await force_grant_daily_crystals(context) 
        await update.effective_message.reply_text(f"✅ Executado! <b>{granted_count}</b> jogadores receberam os cristais.", parse_mode=HTML)
    except Exception as e:
        logger.error(f"Erro ao forçar cristais diários via comando: {e}", exc_info=True)
        await update.effective_message.reply_text(f"❌ Erro ao processar: {e}")

# --- Lógica da Conversa de Limpeza de Cache ---
async def _cache_entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entrada para o menu de limpeza de cache."""
    if not await ensure_admin(update): return ConversationHandler.END
    keyboard = [
        [InlineKeyboardButton("👤 Limpar cache de UM jogador", callback_data="cache_clear_one")],
        [InlineKeyboardButton("🗑️ Limpar TODO o cache (Cuidado!)", callback_data="cache_clear_all_confirm")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="admin_main")],
    ]
    text = "🧽 <b>Gerenciamento de Cache</b>\n\nEscolha uma opção:"
    await _safe_edit_text(update, context, text, InlineKeyboardMarkup(keyboard))
    return SELECT_CACHE_ACTION

async def _cache_ask_for_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pede o ID ou nome do jogador para limpar o cache."""
    if not await ensure_admin(update): return ConversationHandler.END
    await _safe_answer(update)
    await _safe_edit_text(update, context, "👤 Por favor, envie o <b>User ID</b> ou o <b>nome exato do personagem</b>.\n\nUse /cancelar para voltar.")
    return ASK_USER_FOR_CACHE_CLEAR

async def _cache_clear_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Limpa o cache do jogador especificado."""
    target_input = update.message.text
    user_id, pdata, found_by = None, None, "ID/Nome"
    try:
        user_id = int(target_input)
        pdata = await get_player_data(user_id)
        found_by = "ID"
    except ValueError:
        try:
            found = await find_player_by_name(target_input)
            if found:
                user_id, pdata = found
                found_by = "Nome"
        except Exception as e:
            logger.error(f"Erro ao buscar jogador '{target_input}' em _cache_clear_user: {e}")
            await update.message.reply_text("Ocorreu um erro ao buscar o jogador.")
            await _send_admin_menu(update.effective_chat.id, context) 
            return ConversationHandler.END

    if pdata and user_id:
        char_name = pdata.get('character_name', f'ID {user_id}')
        was_in_cache = clear_player_cache(user_id) # SÍNCRONO
        msg = f"✅ Cache para <b>{char_name}</b> (<code>{user_id}</code>) foi limpo." if was_in_cache else f"ℹ️ Jogador <b>{char_name}</b> (<code>{user_id}</code>) encontrado, mas não estava no cache."
        await update.message.reply_text(msg, parse_mode=HTML)
    else:
        await update.message.reply_text(f"❌ Não foi possível encontrar um jogador com o {found_by} fornecido.")

    await _send_admin_menu(update.effective_chat.id, context)
    return ConversationHandler.END

async def _cache_confirm_clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pede confirmação para limpar todo o cache."""
    if not await ensure_admin(update): return ConversationHandler.END 
    await _safe_answer(update)
    keyboard = [
        [InlineKeyboardButton("✅ Sim, tenho certeza", callback_data="cache_do_clear_all")],
        [InlineKeyboardButton("❌ Não, voltar", callback_data="admin_main")], 
    ]
    await _safe_edit_text(update, context, "⚠️ <b>ATENÇÃO!</b>\n\nIsso pode causar uma pequena lentidão temporária no bot.\n\n<b>Você tem certeza?</b>", InlineKeyboardMarkup(keyboard), parse_mode=HTML) 
    return SELECT_CACHE_ACTION 

async def _cache_do_clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Limpa todo o cache de jogadores."""
    if not await ensure_admin(update): return ConversationHandler.END
    await _safe_answer(update)
    try:
        count = clear_all_player_cache() # SÍNCRONO
        await _safe_edit_text(update, context, f"🗑️ Cache completo foi limpo.\n({count} jogadores removidos da memória).")
    except Exception as e:
        logger.error(f"Erro ao limpar todo o cache: {e}", exc_info=True)
        await _safe_edit_text(update, context, f"❌ Erro ao limpar o cache: {e}")

    await _send_admin_menu(update.effective_chat.id, context)
    return ConversationHandler.END

async def _cache_cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a conversa de limpeza de cache."""
    await update.message.reply_text("Operação cancelada.")
    await _send_admin_menu(update.effective_chat.id, context)
    return ConversationHandler.END

# --- Comando de Inspeção de Itens ---
async def inspect_item_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de admin para inspecionar dados de um item."""
    if not await ensure_admin(update): return
    if not context.args:
        await update.message.reply_text("Uso: /inspect_item <item_id>")
        return
    item_id = context.args[0]
    item_data_source = getattr(game_data, "ITEMS_DATA", {}) or {}
    item_info = item_data_source.get(item_id) # SÍNCRONO
    if item_info is None:
        info_str = f"ITEM '{item_id}' NÃO ENCONTRADO."
    else:
        try:
            info_str = json.dumps(item_info, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erro ao serializar item '{item_id}': {e}")
            info_str = f"Erro ao formatar dados do item: {e}"

    await update.message.reply_text(f"<b>DEBUG PARA '{item_id}':</b>\n\n<pre>{info_str}</pre>", parse_mode=HTML)

# --- Comando FixMe ---
async def fix_my_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Corrige o estado de um jogador afetado por bugs de level up anteriores."""
    user_id = update.effective_user.id
    if user_id not in ADMIN_LIST:
        await update.message.reply_text("Você não tem permissão para usar este comando.")
        return

    player_data = await get_player_data(user_id)
    if not player_data:
        await update.message.reply_text("Erro: Jogador não encontrado.")
        return

    try:
        player_data['xp'] = 0 # SÍNCRONO
        allowed = allowed_points_for_level(player_data) # SÍNCRONO
        spent = compute_spent_status_points(player_data) # SÍNCRONO
        player_data['stat_points'] = max(0, allowed - spent) # SÍNCRONO

        await save_player_data(user_id, player_data)

        await update.message.reply_text(
            f"✅ Personagem corrigido!\n"
            f"XP foi zerado e os pontos de atributo foram recalculados.\n"
            f"Use o comando de perfil para ver o resultado."
        )
    except Exception as e:
        logger.error(f"Erro ao executar /fixme para {user_id}: {e}", exc_info=True)
        await update.message.reply_text(f"Ocorreu um erro ao corrigir o personagem: {e}")

# --- Comando MyData ---
async def my_data_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envia os dados do jogador como um ficheiro JSON para diagnóstico."""
    user_id = update.effective_user.id
    if user_id not in ADMIN_LIST: return

    player_data = await get_player_data(user_id)
    if not player_data:
        await update.message.reply_text("Não foi possível carregar os seus dados.")
        return

    player_data_copy = player_data.copy()
    player_data_copy.pop('_id', None)

    try:
        data_str = json.dumps(player_data_copy, indent=2, ensure_ascii=False) # SÍNCRONO
    except Exception as e:
        logger.error(f"Erro ao serializar dados do jogador {user_id}: {e}")
        await update.message.reply_text("Erro ao formatar seus dados.")
        return

    json_bytes = data_str.encode('utf-8')
    input_file = io.BytesIO(json_bytes)

    try:
        await update.message.reply_document( 
            document=input_file,
            filename=f"dados_{user_id}.json",
            caption="Aqui estão os seus dados brutos para diagnóstico."
        )
    except Exception as e:
        logger.error(f"Erro ao enviar documento mydata para {user_id}: {e}")
        await update.message.reply_text("Erro ao enviar o ficheiro de dados.")

async def _handle_force_ticket_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Força a execução do JOB de distribuição de tickets para TODOS os jogadores."""
    query = update.callback_query
    if not await ensure_admin(update):
        await query.answer("Você não tem permissão.", show_alert=True)
        return

    await query.answer("Iniciando job de entrega de tickets para TODOS os jogadores...", show_alert=True)

    # Simula os dados do job (para a mensagem de notificação)
    context.job = type('Job', (object,), {
        'data': {"event_time": "TESTE DE ADMIN"},
        'name': 'admin_force_ticket_job'
    })

    try:
        total_entregue = await distribute_kingdom_defense_ticket_job(context)
        await query.message.reply_text(f"✅ Job de tickets concluído. {total_entregue} jogadores receberam o ticket.")
    except Exception as e:
        await query.message.reply_text(f"❌ Erro ao executar o job de tickets: {e}")

# ==================================
# <<< FUNÇÃO DE RESET GERAL (HARD RESPEC) CORRIGIDA >>>
# ==================================

# Em: handlers/admin_handler.py
#
# SUBSTITUA A FUNÇÃO INTEIRA POR ESTA VERSÃO FINAL:

async def hard_respec_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    [ADMIN] Comando /hard_respec_all.
    (VERSÃO CORRIGIDA DO 'bypass_cache')
    """
    # 1. Verifica se é admin
    if not await ensure_admin(update):
        try:
            await update.message.reply_text("Você não tem permissão para este comando.")
        except Exception:
            pass
        return

    chat_id = update.effective_chat.id
    if not chat_id:
        return

    # 2. Envia mensagem de "iniciando"
    try:
        await context.bot.send_message(
            chat_id,
            "⏳ <b>Iniciando o reset total de status (hard respec)...</b>\n\n"
            "Isso pode demorar alguns minutos. O bot pode ficar lento durante o processo. "
            "Aguarde a mensagem de conclusão.",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logging.warning(f"Falha ao enviar mensagem de 'iniciando respec' para {chat_id}: {e}")

    logging.info("[ADMIN] /hard_respec_all iniciado por %s", update.effective_user.name)

    total = 0
    changed = 0
    
    player_ids = []
    try:
        # (Isto já estava correto da última vez)
        async for uid, _ in iter_players():
            player_ids.append(uid)
            
    except Exception as e:
        logging.error(f"Erro ao COLETAR IDs para /hard_respec_all: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Erro ao coletar a lista de jogadores: {e}")
        return
    
    logging.info(f"[ADMIN] /hard_respec_all - {len(player_ids)} jogadores encontrados. Iniciando o loop de reset.")
    
    # 3. Itera sobre todos os jogadores
    for uid in player_ids:
        total += 1
        try:
            pdata = await get_player_data(uid)
            if not pdata:
                continue
            
            spent_before = await reset_stats_and_refund_points(pdata)
            
            # --- AQUI ESTÁ A CORREÇÃO ---
            # Removemos o argumento 'bypass_cache=True'
            await save_player_data(uid, pdata)
            # --- FIM DA CORREÇÃO ---
            
            changed += 1
            
            logging.info(f"[Respec] Jogador {uid} resetado. Pontos reembolsados (aprox): {spent_before}")

            if total % 20 == 0:
                await asyncio.sleep(0.1) 
                
        except Exception as e:
            # Agora os logs de erro serão mais úteis se algo mais falhar
            logging.error(f"Falha grave ao resetar stats do jogador {uid}: {e}", exc_info=True) 

    # 4. Limpa o cache todo de uma vez
    clear_all_player_cache()

    # 5. Envia mensagem de conclusão
    await context.bot.send_message(
        chat_id,
        f"✅ <b>Reset total de status concluído!</b>\n\n"
        f"Jogadores varridos: {total}\n"
        f"Jogadores resetados: {changed}\n\n"
        "Avise os jogadores para usarem /status e redistribuir seus pontos.",
        parse_mode=ParseMode.HTML
    )
    logging.info("[ADMIN] /hard_respec_all concluído.")

# Texto de ajuda com a descrição dos comandos
ADMIN_HELP_TEXT = """ℹ️ <b>Ajuda dos Comandos de Admin</b> ℹ️

<b>Gerenciamento Básico:</b>
<code>/admin</code> - Abre o painel de admin principal.
<code>/get_id</code> - Mostra o ID do chat e do tópico (para configurar anúncios, etc.).
<code>/mydata</code> - Envia um arquivo .json com os seus dados de jogador (para debug).

<b>Gerenciamento de Jogadores:</b>
<code>/find_player [nome]</code> - Encontra o User ID de um jogador (necessário para os botões de "Dar Item", "Editar Jogador", etc.).
<code>/debug_player [user_id]</code> - Verifica o status do cache e do DB para um jogador (vê se ele está "preso").
<code>/delete_player [user_id]</code> - <b>[PERIGOSO]</b> Apaga permanentemente um jogador da base de dados.
<code>/fixme</code> - (Apenas Admin) Recalcula os seus pontos de stats com base no nível (corrige bugs de level up).
<code>/hard_respec_all</code> - <b>[RESET GERAL]</b> Reseta os stats de TODOS os jogadores e reembolsa os pontos (usar após balanceamento).

<b>Recursos e Eventos:</b>
<code>/forcar_cristais</code> - Executa o job diário de entrega de cristais para todos os jogadores.
<code>/resetpvpnow</code> - Reseta a temporada PvP e os pontos de todos imediatamente.

<b>Debug de Jogo:</b>
<code>/inspect_item [item_id]</code> - Mostra os dados brutos (JSON) de um item (ex: 'espada_longa') para ver os seus stats base.
"""

async def _handle_admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a ajuda dos comandos de admin."""
    if not await ensure_admin(update): return
    await _safe_answer(update)
    
    # Cria um teclado simples apenas com o botão "Voltar"
    kb = [[InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="admin_main")]]
    reply_markup = InlineKeyboardMarkup(kb)
    
    # Edita a mensagem para mostrar o texto de ajuda
    await _safe_edit_text(update, context, ADMIN_HELP_TEXT, reply_markup)
# =========================================================
# EXPORTAÇÃO DE HANDLERS PARA O REGISTRY
# =========================================================

# Handlers de Comando (já filtrados acima)
admin_command_handler = CommandHandler("admin", admin_command, filters=filters.User(ADMIN_LIST))
delete_player_handler = CommandHandler("delete_player", _delete_player_command, filters=filters.User(ADMIN_LIST))
inspect_item_handler = CommandHandler("inspect_item", inspect_item_command, filters=filters.User(ADMIN_LIST))
force_daily_handler = CommandHandler("forcar_cristais", force_daily_crystals_cmd, filters=filters.User(ADMIN_LIST))
my_data_handler = CommandHandler("mydata", my_data_command, filters=filters.User(ADMIN_LIST))
reset_pvp_now_handler = CommandHandler("resetpvpnow", _reset_pvp_now_command, filters=filters.User(ADMIN_LIST))
find_player_handler = CommandHandler("find_player", find_player_command, filters=filters.User(ADMIN_LIST))
debug_player_handler = CommandHandler("debug_player", debug_player_data, filters=filters.User(ADMIN_LIST))
# Removemos o filtro de usuário. Agora qualquer um pode usar /get_id
get_id_command_handler = CommandHandler("get_id", get_id_command)
fixme_handler = CommandHandler("fixme", fix_my_character, filters=filters.User(ADMIN_LIST))
hard_respec_all_handler = CommandHandler("hard_respec_all", hard_respec_all_command, filters=filters.User(ADMIN_LIST))


# Handlers de CallbackQuery (Botões) - Filtros são aplicados dentro das funções
admin_main_handler = CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$")
admin_force_daily_callback_handler = CallbackQueryHandler(_handle_admin_force_daily, pattern="^admin_force_daily$")
admin_event_menu_handler = CallbackQueryHandler(_handle_admin_event_menu, pattern="^admin_event_menu$")
admin_force_start_handler = CallbackQueryHandler(_handle_force_start_event, pattern="^admin_event_force_start$")
admin_force_end_handler = CallbackQueryHandler(_handle_force_end_event, pattern="^admin_event_force_end$")
admin_force_ticket_handler = CallbackQueryHandler(_handle_force_ticket, pattern="^admin_event_force_ticket$")
admin_force_ticket_job_handler = CallbackQueryHandler(_handle_force_ticket_job, pattern="^admin_force_ticket_job$")
admin_help_handler = CallbackQueryHandler(_handle_admin_help, pattern="^admin_help$")

# Handler de Conversa para Limpeza de Cache (filtros aplicados nos entry points e message handlers)
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
        CommandHandler("cancelar", _cache_cancel_conv, filters=filters.User(ADMIN_LIST)),
        CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$")
    ],
    per_message=False
)


# Handler de Conversa para Teste de Evento (filtros aplicados nos entry points e message handlers)
test_event_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(_handle_admin_test_menu, pattern=r"^admin_test_menu$")],
    states={
        SELECT_TEST_ACTION: [
            CallbackQueryHandler(_test_ask_wave_number, pattern="^test_start_at_wave$"),
            CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$"), 
        ],
        ASK_WAVE_NUMBER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_LIST), _test_start_specific_wave)
        ],
    },
    fallbacks=[
        CommandHandler("cancelar", _test_cancel_conv, filters=filters.User(ADMIN_LIST)),
        CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$") 
    ],
    per_message=False,
    block=False
)

# Handler de Conversa para Deletar Jogador
delete_player_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(_delete_entry_point, pattern=r"^admin_delete_start$")],
    states={
        ASK_DELETE_ID: [
            MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_LIST), _delete_resolve_user)
        ],
        CONFIRM_DELETE_ACTION: [
            CallbackQueryHandler(_delete_perform, pattern="^confirm_delete_yes$"),
            CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$") # Cancelar pelo botão
        ]
    },
    fallbacks=[
        CommandHandler("cancelar", _delete_cancel, filters=filters.User(ADMIN_LIST)),
        CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$")
    ],
    per_message=False
)

# Lista final de handlers para exportar (certifique-se que todos os handlers importados existem)
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
    clear_cache_conv_handler, # A conversa de cache
    test_event_conv_handler, # A conversa de teste
    grant_item_conv_handler, # A conversa de dar item
    sell_gems_conv_handler, # A conversa de vender gemas
    my_data_handler,
    reset_pvp_now_handler,
    generate_equip_conv_handler,
    file_id_conv_handler,
    premium_panel_handler,
    reset_panel_conversation_handler,
    grant_skill_conv_handler,
    grant_skin_conv_handler,
    player_management_conv_handler, # <--- O 'a' FOI REMOVIDO DAQUI
    admin_help_handler,
    delete_player_conv_handler,
    hard_respec_all_handler, # <<< COMANDO DE RESET ADICIONADO
]