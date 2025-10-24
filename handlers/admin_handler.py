# handlers/admin_handler.py

from __future__ import annotations
import os
import io
import logging # <- O import já estava
import json
from typing import Optional
from handlers.admin.grant_item import grant_item_conv_handler # Já estava
from handlers.admin.sell_gems import sell_gems_conv_handler # Já estava
from handlers.admin.generate_equip import generate_equip_conv_handler # <<< ADICIONADO (Assumindo que existe)
from handlers.admin.file_id_conv import file_id_conv_handler # <<< ADICIONADO (Assumindo que existe)
from handlers.admin.premium_panel import premium_panel_handler # <<< ADICIONADO (Assumindo que existe)
from handlers.admin.reset_panel import reset_panel_conversation_handler # <<< ADICIONADO (Assumindo que existe)

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
from telegram.constants import ParseMode # <<< ADICIONADO >>>

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
from handlers.jobs import reset_pvp_season, force_grant_daily_crystals # <<< CORRIGIDO >>> Importa force_grant_daily_crystals
from handlers.admin.utils import ensure_admin
from kingdom_defense.engine import event_manager
# No topo de admin_handler.py
from modules.player.core import _player_cache, players_collection
# No topo de admin_handler.py
from modules.player.queries import _normalize_char_name
# <<< ADICIONADO >>> Importa a função de início da conversa de edição

logger = logging.getLogger(__name__) 

try:
    from config import ADMIN_LIST
except ImportError:
    logger.warning("ADMIN_LIST não encontrada em config.py, usando apenas ADMIN_ID.")
    try:
        ADMIN_ID = int(os.getenv("ADMIN_ID"))
        ADMIN_LIST = [ADMIN_ID]
    except (TypeError, ValueError):
        logger.error("ADMIN_ID não definido nas variáveis de ambiente! Painel admin pode não funcionar.")
        ADMIN_LIST = [] # Lista vazia se nada for encontrado

HTML = "HTML" # Já estava, mas confirmado

(SELECT_CACHE_ACTION, ASK_USER_FOR_CACHE_CLEAR) = range(2)
(SELECT_TEST_ACTION, ASK_WAVE_NUMBER) = range(2, 4)

# =========================================================
# MENUS E TECLADOS (Keyboards)
# =========================================================

async def _reset_pvp_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de admin para resetar imediatamente os pontos PvP."""
    if not await ensure_admin(update): # Verifica se é admin
        return

    await update.message.reply_text("⏳ <b>Iniciando reset manual da temporada PvP...</b>\nIsso pode levar um momento.", parse_mode=HTML) # Corrigido para HTML

    try:
        # Chama a função de reset que já existe em jobs.py
        await reset_pvp_season(context)
        await update.message.reply_text("✅ Reset da temporada PvP concluído com sucesso!")
    except Exception as e:
        logger.error(f"Erro ao executar reset manual de PvP: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Ocorreu um erro durante o reset manual: {e}")

async def debug_player_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de admin para diagnosticar cache e DB para um jogador."""
    if not await ensure_admin(update): return # Adicionado filtro

    user_id_to_check = None
    try:
        user_id_to_check = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Por favor, fornece um ID de utilizador. Uso: /debug_player <user_id>")
        return

    report = [f"🕵️ <b>Relatório de Diagnóstico para o Jogador</b> <code>{user_id_to_check}</code> 🕵️\n"] # Corrigido para HTML

    # 1. Verifica a Cache em Memória
    if user_id_to_check in _player_cache:
        player_cache_data = _player_cache[user_id_to_check]
        char_name = player_cache_data.get('character_name', 'Nome não encontrado')
        report.append(f"✅ <b>Cache em Memória:</b> Encontrado! (Nome: <code>{char_name}</code>)") # Corrigido para HTML
    else:
        report.append("❌ <b>Cache em Memória:</b> Vazio.") # Corrigido para HTML

    # 2. Verifica a Base de Dados MongoDB
    if players_collection is not None:
        try:
            player_doc = players_collection.find_one({"_id": user_id_to_check})
            if player_doc:
                char_name = player_doc.get('character_name', 'Nome não encontrado')
                report.append(f"✅ <b>MongoDB:</b> Encontrado! (Nome: <code>{char_name}</code>)") # Corrigido para HTML
            else:
                report.append("❌ <b>MongoDB:</b> Não encontrado.") # Corrigido para HTML
        except Exception as e:
            report.append(f"⚠️ <b>MongoDB:</b> Erro ao aceder à base de dados: {e}") # Corrigido para HTML
    else:
        report.append("🚫 <b>MongoDB:</b> Conexão com a base de dados não existe (está a <code>None</code>).") # Corrigido para HTML

    await update.message.reply_text("\n".join(report), parse_mode=HTML) # Corrigido para HTML

async def find_player_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando de admin para encontrar um jogador pelo nome do personagem.
    Uso: /find_player <nome do personagem>
    """
    if not await ensure_admin(update): return # Adicionado filtro

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
        ) # Corrigido para HTML
        await update.message.reply_text(report, parse_mode=HTML) # Corrigido para HTML
    else:
        await update.message.reply_text(f"❌ Nenhum jogador encontrado com o nome '{char_name_to_find}'.")


async def get_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de admin para obter IDs de chat e tópico."""
    if not await ensure_admin(update): return # Adicionado filtro

    chat_id = update.effective_chat.id
    # Verifica se a mensagem tem um message_thread_id
    thread_id = getattr(update.effective_message, 'message_thread_id', None)

    text = (
        f"<b>INFORMAÇÕES DE ID:</b>\n"
        f"--------------------------\n"
        f"ID do Chat Atual (chat_id): <code>{chat_id}</code>\n"
    )
    if thread_id:
        text += f"ID do Tópico Atual (thread_id): <code>{thread_id}</code>"
    else:
        text += "<i>Esta mensagem não está num tópico.</i>"

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
        [InlineKeyboardButton("👤 𓂀 𝔼𝕕𝕚𝕥𝕒𝕣 𝕁𝕠𝕘𝕒𝕕𝕠𝕣 𓂀", callback_data="admin_edit_player")], # <<< ADICIONADO >>>
        [InlineKeyboardButton("🔁 𓂀 𝔽𝕠𝕣ç𝕒𝕣 𝕕𝕚á𝕣𝕚𝕠𝕤 (ℂ𝕣𝕚𝕤𝕥𝕒𝕚𝕤) 𓂀", callback_data="admin_force_daily")],
        [InlineKeyboardButton("👑 𓂀 ℙ𝕣𝕖𝕞𝕚𝕦𝕞 𓂀", callback_data="admin_premium")],
        [InlineKeyboardButton("🎉 𓂀 𝔾𝕖𝕣𝕖𝕟𝕔𝕚𝕒𝕣 𝔼𝕧𝕖𝕟𝕥𝕠𝕤 𓂀 🎉", callback_data="admin_event_menu")],
        [InlineKeyboardButton("🔬 𓂀 Painel de Teste de Evento 𓂀 🔬", callback_data="admin_test_menu")],
        [InlineKeyboardButton("📁 𓂀 𝔾𝕖𝕣𝕖𝕟𝕔𝕚𝕒𝕣 𝔽𝕚𝕝𝕖 𝕀𝔻𝕤 𓂀", callback_data="admin_file_ids")],
        [InlineKeyboardButton("🧹 𓂀 ℝ𝕖𝕤𝕖𝕥/ℝ𝕖𝕤𝕡𝕖𝕔 𓂀", callback_data="admin_reset_menu")],
        [InlineKeyboardButton("🧽 𓂀 𝕃𝕚𝕞𝕡𝕒𝕣 ℂ𝕒𝕔𝕙𝕖 𓂀", callback_data="admin_clear_cache")],
        [InlineKeyboardButton("🔄 𝐑𝐞𝐬𝐞𝐭𝐚𝐫 𝐄𝐬𝐭𝐚𝐝𝐨 (/𝐫𝐞𝐬𝐞𝐭_𝐬𝐭𝐚𝐭𝐞)", callback_data="admin_reset_state_hint")], # Assume que este botão apenas mostra uma dica
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
            pass # A mensagem é a mesma ou a query expirou

    # Se edit falhar, envia uma nova mensagem
    chat_id = update.effective_chat.id
    # <<< CORREÇÃO >>> Garante que chat_id existe antes de enviar
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
    if not await ensure_admin(update): return ConversationHandler.END # Adicionado filtro
    await _safe_answer(update)
    await _safe_edit_text(update, context, "🔬 <b>Painel de Teste de Evento</b>\n\nO que você gostaria de fazer?", _admin_test_menu_kb()) # Corrigido para HTML
    return SELECT_TEST_ACTION

async def _test_ask_wave_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pede ao admin para enviar o número da wave."""
    if not await ensure_admin(update): return ConversationHandler.END # Adicionado filtro
    await _safe_answer(update)
    await _safe_edit_text(update, context, "🔢 Por favor, envie o número da wave que você deseja testar.\n\nUse /cancelar para voltar.")
    return ASK_WAVE_NUMBER

async def _test_start_specific_wave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o evento de teste na wave especificada pelo admin."""
    # O filtro já foi aplicado no MessageHandler que chama esta função
    try:
        wave_num = int(update.message.text)
        if wave_num <= 0: raise ValueError("Wave deve ser positiva") # Adiciona validação
    except (ValueError, TypeError):
        await update.message.reply_text("❌ Isso não é um número válido (deve ser maior que 0). Tente novamente ou use /cancelar.")
        return ASK_WAVE_NUMBER # Mantém na mesma etapa da conversa

    result = event_manager.start_event_at_wave(wave_num)

    if "error" in result:
        await update.message.reply_text(result["error"])
    else:
        await update.message.reply_text(result["success"] + "\n\nO evento está ativo. Use os comandos de jogador em um chat separado para interagir.")

    await _send_admin_menu(update.effective_chat.id, context)
    return ConversationHandler.END

async def _test_cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a operação de teste e retorna ao menu principal."""
    # O filtro já foi aplicado no CommandHandler que chama esta função
    await update.message.reply_text("Operação de teste cancelada.")
    await _send_admin_menu(update.effective_chat.id, context)
    return ConversationHandler.END

# --- Funções do Painel Principal e Comandos ---
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe o painel principal do admin."""
    if not await ensure_admin(update): return # Já tinha verificação indireta, mas explícita é melhor
    await update.message.reply_text(
        "🎛️ <b>Painel do Admin</b>\nEscolha uma opção:",
        reply_markup=_admin_menu_kb(),
        parse_mode=HTML,
    )

async def _handle_admin_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Atualiza a mensagem para mostrar o painel principal do admin."""
    if not await ensure_admin(update): return # Adicionado filtro
    await _safe_answer(update)
    await _safe_edit_text(update, context, "🎛️ <b>Painel do Admin</b>\nEscolha uma opção:", _admin_menu_kb())

async def _delete_player_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de admin para apagar um jogador."""
    if not await ensure_admin(update): return # Adicionado filtro

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
        logger.error(f"Erro ao deletar jogador {context.args[0]}: {e}", exc_info=True) # Loga o erro completo
        await update.message.reply_text(f"Ocorreu um erro ao tentar apagar o jogador.")

# --- Funções de Eventos ---
async def _handle_admin_event_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o submenu de gerenciamento de eventos."""
    if not await ensure_admin(update): return # Adicionado filtro
    await _safe_answer(update)
    await _safe_edit_text(update, context, "🎉 <b>Painel de Gerenciamento de Eventos</b>", _admin_event_menu_kb(), parse_mode=HTML) # Adicionado parse_mode

async def _handle_force_start_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia o evento e anuncia no grupo principal."""
    if not await ensure_admin(update): return # Adicionado filtro
    query = update.callback_query

    result = event_manager.start_event()

    if "error" in result:
        await query.answer(result["error"], show_alert=True)
        return

    await query.answer("✅ Evento iniciado com sucesso!", show_alert=True)

    # Tenta importar IDs do config, com fallback para None
    try:
        from config import ANNOUNCEMENT_CHAT_ID as ID_GRUPO_EVENTOS, ANNOUNCEMENT_THREAD_ID as ID_TOPICO_EVENTOS
        if not isinstance(ID_GRUPO_EVENTOS, int): ID_GRUPO_EVENTOS = None # Garante que é int ou None
        if not isinstance(ID_TOPICO_EVENTOS, int): ID_TOPICO_EVENTOS = None # Garante que é int ou None
    except ImportError:
        logger.warning("IDs de grupo/tópico de anúncios (ANNOUNCEMENT_CHAT_ID, ANNOUNCEMENT_THREAD_ID) não encontrados na config!")
        ID_GRUPO_EVENTOS = None
        ID_TOPICO_EVENTOS = None

    if ID_GRUPO_EVENTOS:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚔️ Ver Evento ⚔️", callback_data='show_events_menu')]
        ])

        try:
             await context.bot.send_message(
                chat_id=ID_GRUPO_EVENTOS,
                message_thread_id=ID_TOPICO_EVENTOS,
                text="📢 <b>ATENÇÃO, HERÓIS DE ELDORA!</b> 📢\n\nUma nova invasão ameaça nosso reino! Preparem-se para a batalha!",
                reply_markup=keyboard,
                parse_mode=HTML
            )
        except Exception as e:
             logger.error(f"Falha ao anunciar evento no grupo {ID_GRUPO_EVENTOS} (tópico: {ID_TOPICO_EVENTOS}): {e}")
    else:
        logger.warning("Não foi possível anunciar o início do evento (IDs de grupo/tópico não configurados).")


async def _handle_force_end_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Termina o evento manualmente."""
    if not await ensure_admin(update): return # Adicionado filtro
    await update.callback_query.answer()
    message = event_manager.end_event()
    await update.callback_query.answer(message, show_alert=True)

async def _handle_force_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entrega um ticket de defesa ao admin."""
    if not await ensure_admin(update): return # Adicionado filtro
    await _safe_answer(update)
    user_id = update.effective_user.id # O próprio admin
    player_data = get_player_data(user_id)
    if not player_data:
        await update.callback_query.answer("Erro: Não foi possível carregar seus dados.", show_alert=True)
        return

    item_id = 'ticket_defesa_reino'
    try:
        add_item_to_inventory(player_data, item_id, 1)
        save_player_data(user_id, player_data)
        await update.callback_query.answer(f"🎟️ Você recebeu 1x {item_id}!", show_alert=True)
    except Exception as e:
        logger.error(f"Erro ao entregar ticket para admin {user_id}: {e}", exc_info=True)
        await update.callback_query.answer(f"Erro ao entregar o item '{item_id}'.", show_alert=True)


# --- Funções de Cristais Diários ---
async def _handle_admin_force_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Força a entrega dos cristais diários (via botão)."""
    if not await ensure_admin(update): return # Adicionado filtro
    await _safe_answer(update)
    await _safe_edit_text(update, context, "⏳ Processando entrega de cristais diários...")
    try:
        granted_count = await force_grant_daily_crystals(context)
        feedback_text = f"✅ Executado! <b>{granted_count}</b> jogadores receberam os cristais diários."
    except Exception as e:
        logger.error(f"Erro ao forçar cristais diários via botão: {e}", exc_info=True)
        feedback_text = f"❌ Erro ao processar: {e}"

    await _safe_edit_text(update, context, feedback_text, InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_main")]]), parse_mode=HTML) # Adicionado parse_mode

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
    if not await ensure_admin(update): return # Adicionado filtro
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
    if not await ensure_admin(update): return ConversationHandler.END # Adicionado filtro
    keyboard = [
        [InlineKeyboardButton("👤 Limpar cache de UM jogador", callback_data="cache_clear_one")],
        [InlineKeyboardButton("🗑️ Limpar TODO o cache (Cuidado!)", callback_data="cache_clear_all_confirm")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="admin_main")], # Leva de volta ao menu principal
    ]
    text = "🧽 <b>Gerenciamento de Cache</b>\n\nEscolha uma opção:" # Corrigido para HTML
    await _safe_edit_text(update, context, text, InlineKeyboardMarkup(keyboard))
    return SELECT_CACHE_ACTION

async def _cache_ask_for_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pede o ID ou nome do jogador para limpar o cache."""
    if not await ensure_admin(update): return ConversationHandler.END # Adicionado filtro
    await _safe_answer(update)
    await _safe_edit_text(update, context, "👤 Por favor, envie o <b>User ID</b> ou o <b>nome exato do personagem</b>.\n\nUse /cancelar para voltar.", parse_mode=HTML) # Corrigido para HTML
    return ASK_USER_FOR_CACHE_CLEAR

async def _cache_clear_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Limpa o cache do jogador especificado."""
    # O filtro já foi aplicado no MessageHandler que chama esta função
    target_input = update.message.text
    user_id, pdata, found_by = None, None, "ID/Nome"
    try:
        user_id = int(target_input)
        pdata = get_player_data(user_id) # Tenta carregar para obter o nome
        found_by = "ID"
    except ValueError:
        found = find_player_by_name(target_input)
        if found:
            user_id, pdata = found
            found_by = "Nome"
    except Exception as e:
        logger.error(f"Erro ao buscar jogador '{target_input}' em _cache_clear_user: {e}")
        await update.message.reply_text("Ocorreu um erro ao buscar o jogador.")
        await _send_admin_menu(update.effective_chat.id, context)
        return ConversationHandler.END

    if pdata and user_id: # Garante que temos um ID para limpar
        char_name = pdata.get('character_name', f'ID {user_id}') # Usa ID se nome não estiver disponível
        was_in_cache = clear_player_cache(user_id)
        msg = f"✅ Cache para <b>{char_name}</b> (<code>{user_id}</code>) foi limpo." if was_in_cache else f"ℹ️ Jogador <b>{char_name}</b> (<code>{user_id}</code>) encontrado, mas não estava no cache." # Corrigido para HTML
        await update.message.reply_text(msg, parse_mode=HTML) # Corrigido para HTML
    else:
        await update.message.reply_text(f"❌ Não foi possível encontrar um jogador com o {found_by} fornecido.")

    await _send_admin_menu(update.effective_chat.id, context)
    return ConversationHandler.END

async def _cache_confirm_clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pede confirmação para limpar todo o cache."""
    if not await ensure_admin(update): return ConversationHandler.END # Adicionado filtro
    await _safe_answer(update)
    keyboard = [
        [InlineKeyboardButton("✅ Sim, tenho certeza", callback_data="cache_do_clear_all")],
        [InlineKeyboardButton("❌ Não, voltar", callback_data="admin_main")], # Volta ao menu principal
    ]
    await _safe_edit_text(update, context, "⚠️ <b>ATENÇÃO!</b>\n\nIsso pode causar uma pequena lentidão temporária no bot.\n\n<b>Você tem certeza?</b>", InlineKeyboardMarkup(keyboard), parse_mode=HTML) # Corrigido para HTML
    return SELECT_CACHE_ACTION # Permanece no mesmo estado esperando a confirmação

async def _cache_do_clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Limpa todo o cache de jogadores."""
    if not await ensure_admin(update): return ConversationHandler.END # Adicionado filtro
    await _safe_answer(update)
    try:
        count = clear_all_player_cache()
        await _safe_edit_text(update, context, f"🗑️ Cache completo foi limpo.\n({count} jogadores removidos da memória).") # Mensagem de sucesso simples
    except Exception as e:
        logger.error(f"Erro ao limpar todo o cache: {e}", exc_info=True)
        await _safe_edit_text(update, context, f"❌ Erro ao limpar o cache: {e}")

    await _send_admin_menu(update.effective_chat.id, context) # Volta ao menu principal
    return ConversationHandler.END

async def _cache_cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a conversa de limpeza de cache."""
    # O filtro já foi aplicado no CommandHandler que chama esta função
    await update.message.reply_text("Operação cancelada.")
    await _send_admin_menu(update.effective_chat.id, context)
    return ConversationHandler.END

# --- Comando de Inspeção de Itens ---
async def inspect_item_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de admin para inspecionar dados de um item."""
    if not await ensure_admin(update): return # Adicionado filtro
    if not context.args:
        await update.message.reply_text("Uso: /inspect_item <item_id>")
        return
    item_id = context.args[0]
    # Usa .get() com fallback e garante que é um dict
    item_data_source = getattr(game_data, "ITEMS_DATA", {}) or {}
    item_info = item_data_source.get(item_id)
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
    """
    Corrige o estado de um jogador afetado por bugs de level up anteriores.
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_LIST:
        await update.message.reply_text("Você não tem permissão para usar este comando.")
        return

    player_data = get_player_data(user_id)
    if not player_data:
        await update.message.reply_text("Erro: Jogador não encontrado.")
        return

    try:
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
    except Exception as e:
        logger.error(f"Erro ao executar /fixme para {user_id}: {e}", exc_info=True)
        await update.message.reply_text(f"Ocorreu um erro ao corrigir o personagem: {e}")


# --- Comando MyData ---
async def my_data_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Envia os dados do jogador como um ficheiro JSON para diagnóstico.
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_LIST:
        return # Sem mensagem para não alertar não-admins

    player_data = get_player_data(user_id)
    if not player_data:
        await update.message.reply_text("Não foi possível carregar os seus dados.")
        return

    player_data_copy = player_data.copy() # Trabalha com uma cópia
    player_data_copy.pop('_id', None)

    # Converte os dados para uma string formatada
    try:
        data_str = json.dumps(player_data_copy, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Erro ao serializar dados do jogador {user_id}: {e}")
        await update.message.reply_text("Erro ao formatar seus dados.")
        return

    # Prepara a string para ser enviada como um ficheiro em memória
    json_bytes = data_str.encode('utf-8')
    input_file = io.BytesIO(json_bytes)

    # Envia o ficheiro como um documento
    try:
        await update.message.reply_document(
            document=input_file,
            filename=f"dados_{user_id}.json", # Nome de ficheiro mais específico
            caption="Aqui estão os seus dados brutos para diagnóstico."
        )
    except Exception as e:
        logger.error(f"Erro ao enviar documento mydata para {user_id}: {e}")
        await update.message.reply_text("Erro ao enviar o ficheiro de dados.")


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
get_id_command_handler = CommandHandler("get_id", get_id_command, filters=filters.User(ADMIN_LIST))
fixme_handler = CommandHandler("fixme", fix_my_character, filters=filters.User(ADMIN_LIST))

# Handlers de CallbackQuery (Botões) - Filtros são aplicados dentro das funções
admin_main_handler = CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$")
admin_force_daily_callback_handler = CallbackQueryHandler(_handle_admin_force_daily, pattern="^admin_force_daily$")
admin_event_menu_handler = CallbackQueryHandler(_handle_admin_event_menu, pattern="^admin_event_menu$")
admin_force_start_handler = CallbackQueryHandler(_handle_force_start_event, pattern="^admin_event_force_start$")
admin_force_end_handler = CallbackQueryHandler(_handle_force_end_event, pattern="^admin_event_force_end$")
admin_force_ticket_handler = CallbackQueryHandler(_handle_force_ticket, pattern="^admin_event_force_ticket$")


# Handler de Conversa para Limpeza de Cache (filtros aplicados nos entry points e message handlers)
clear_cache_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(_cache_entry_point, pattern=r"^admin_clear_cache$")],
    states={
        SELECT_CACHE_ACTION: [
            CallbackQueryHandler(_cache_ask_for_user, pattern="^cache_clear_one$"),
            CallbackQueryHandler(_cache_confirm_clear_all, pattern="^cache_clear_all_confirm$"),
            CallbackQueryHandler(_cache_do_clear_all, pattern="^cache_do_clear_all$"),
            CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$"), # Usa admin_main como fallback
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
            CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$"), # Fallback para voltar
        ],
        ASK_WAVE_NUMBER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_LIST), _test_start_specific_wave)
        ],
    },
    fallbacks=[
        CommandHandler("cancelar", _test_cancel_conv, filters=filters.User(ADMIN_LIST)),
        CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$") # Voltar ao menu
    ],
    per_message=False,
    block=False
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
    clear_cache_conv_handler, # A conversa de cache
    test_event_conv_handler, # A conversa de teste
    grant_item_conv_handler, # A conversa de dar item
    sell_gems_conv_handler, # A conversa de vender gemas
    my_data_handler,
    reset_pvp_now_handler,
    # <<< ADICIONADO >>> Os outros handlers de conversa que você tinha importado
    generate_equip_conv_handler,
    file_id_conv_handler,
    premium_panel_handler,
    reset_panel_conversation_handler,
]