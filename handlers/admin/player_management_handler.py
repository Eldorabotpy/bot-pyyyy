# handlers/admin/player_management_handler.py
import logging
import math
import asyncio
from datetime import datetime, timezone, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from modules import player_manager
from modules.player.core import players_collection 
from handlers.admin.utils import (
    ADMIN_LIST,
    parse_hybrid_id,
    ensure_admin, 
    find_player_from_input,
    cancelar_conversa,
    confirmar_jogador,
    jogador_confirmado,
    INPUT_TEXTO,
    CONFIRMAR_JOGADOR,
)

logger = logging.getLogger(__name__)

# --- Constantes de Paginação e Estados ---
PLAYERS_PER_PAGE = 5
INACTIVE_DAYS = 30 

(MAIN_MENU, LIST_INACTIVE, PLAYER_DETAIL, CONFIRM_DELETE) = range(2, 6)
ASK_PLAYER_TO_FIND = 7 


# ==========================================================
# PASSO 1: Menu Principal de Gestão
# ==========================================================

async def show_main_management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, pdata: dict | None = None) -> int:
    """Mostra o menu principal de gestão com estatísticas."""
    query = update.callback_query
    if query:
        await query.answer()

    try:
        total_players = players_collection.count_documents({})
        
        inactive_date_limit = datetime.now(timezone.utc) - timedelta(days=INACTIVE_DAYS)
        inactive_count = players_collection.count_documents(
            {"last_seen": {"$lt": inactive_date_limit.isoformat()}}
        )
        
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        active_today_count = players_collection.count_documents(
            {"last_seen": {"$gte": today_start.isoformat()}}
        )
        
        text = [
            "👥 <b>Gestão de Jogadores</b>\n",
            f"<b>Total de Contas:</b> {total_players}",
            f"<b>Ativos Hoje:</b> {active_today_count}",
            f"<b>Inativos (+{INACTIVE_DAYS} dias):</b> {inactive_count}",
            "\nEscolha uma opção:"
        ]
        
        keyboard = [
            [InlineKeyboardButton(f"📜 Listar Jogadores Inativos ({inactive_count})", callback_data="admin_pmanage_list:1")],
            [InlineKeyboardButton("🔍 Encontrar Jogador (Nome/ID)", callback_data="admin_pmanage_find")],
            [InlineKeyboardButton("⬅️ Voltar ao Admin", callback_data="admin_main")],
        ]
        
        if query:
            await query.edit_message_text(
                "\n".join(text), 
                reply_markup=InlineKeyboardMarkup(keyboard), 
                parse_mode="HTML"
            )
        else:
            await update.effective_message.reply_text(
                "\n".join(text), 
                reply_markup=InlineKeyboardMarkup(keyboard), 
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Erro ao carregar estatísticas de jogadores: {e}", exc_info=True)
        await update.effective_message.reply_text(f"Erro ao carregar estatísticas: {e}")
        
    return MAIN_MENU

# ==========================================================
# PASSO 2: Listar Jogadores Inativos (Paginado)
# ==========================================================

async def list_inactive_players(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1) -> int:
    """Mostra a lista paginada de jogadores inativos."""
    query = update.callback_query
    await query.answer()

    inactive_date_limit = datetime.now(timezone.utc) - timedelta(days=INACTIVE_DAYS)
    
    try:
        db_query = {
            "$or": [
                {"last_seen": {"$lt": inactive_date_limit.isoformat()}},
                {"last_seen": {"$exists": False}}
            ]
        }
        
        total_inactive = players_collection.count_documents(db_query)
        total_pages = math.ceil(total_inactive / PLAYERS_PER_PAGE)
        page = max(1, min(page, total_pages)) 
        
        start_index = (page - 1) * PLAYERS_PER_PAGE
        
        cursor = players_collection.find(db_query).sort("last_seen", 1).skip(start_index).limit(PLAYERS_PER_PAGE)
        
        inactive_list = list(cursor)
        
        text = [f"👥 <b>Jogadores Inativos (+{INACTIVE_DAYS} dias)</b> - Página {page}/{total_pages}\n"]
        keyboard = []

        if not inactive_list:
            text.append("<i>Nenhum jogador inativo encontrado.</i>")
        
        for pdata in inactive_list:
            user_id = pdata["_id"]
            name = pdata.get("character_name", f"ID {user_id}")
            
            last_seen_iso = pdata.get("last_seen", "Nunca")
            if last_seen_iso != "Nunca":
                try:
                    last_seen_dt = datetime.fromisoformat(last_seen_iso)
                    last_seen_str = last_seen_dt.strftime("%d/%m/%Y")
                except Exception:
                    last_seen_str = "Data Inválida"
            else:
                last_seen_str = "Nunca"

            button_text = f"👤 {name} (Visto em: {last_seen_str})"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"admin_pmanage_detail:{user_id}")])

        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"admin_pmanage_list:{page-1}"))
        if page < total_pages:
            nav_row.append(InlineKeyboardButton("Próxima ➡️", callback_data=f"admin_pmanage_list:{page+1}"))
        
        if nav_row:
            keyboard.append(nav_row)
            
        keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="admin_pmanage_main")])
        
        await query.edit_message_text(
            "\n".join(text), 
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Erro ao listar jogadores inativos: {e}", exc_info=True)
        await query.edit_message_text(f"Erro ao listar jogadores: {e}")

    return LIST_INACTIVE

# Callback para os botões de página
async def list_inactive_pager(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    page = int(update.callback_query.data.split(':')[-1])
    await list_inactive_players(update, context, page=page)
    return LIST_INACTIVE

# ==========================================================
# PASSO 3: Detalhes do Jogador
# ==========================================================

async def show_player_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mostra os detalhes de um jogador específico e opções de moderação."""
    query = update.callback_query
    # Tenta responder ao callback para parar o reloginho de carregamento
    try:
        await query.answer()
    except Exception:
        pass

    # --- INÍCIO DA CORREÇÃO ---
    # Pegamos o ID cru (string) do callback
    raw_id = query.data.split(':')[-1]
    
    # Usamos o parser híbrido para converter corretamente (Int ou ObjectId)
    target_user_id = parse_hybrid_id(raw_id)

    if not target_user_id:
        await query.edit_message_text("Erro: ID do jogador inválido.")
        return await show_main_management_menu(update, context) 
    # --- FIM DA CORREÇÃO ---
    
    context.user_data['target_user_id'] = target_user_id
    
    pdata = await player_manager.get_player_data(target_user_id)
    if not pdata:
        # Usa f-string com str(target_user_id) para evitar erro caso seja ObjectId na renderização
        await query.edit_message_text(f"Erro: Jogador <code>{str(target_user_id)}</code> não encontrado.")
        return MAIN_MENU

    try:
        created_at_dt = datetime.fromisoformat(pdata.get("created_at", ""))
        created_at_str = created_at_dt.strftime("%d/%m/%Y às %H:%M")
    except Exception:
        created_at_str = "Desconhecida"
        
    try:
        last_seen_dt = datetime.fromisoformat(pdata.get("last_seen", ""))
        last_seen_str = last_seen_dt.strftime("%d/%m/%Y às %H:%M")
    except Exception:
        last_seen_str = "Desconhecida"

    name = pdata.get("character_name", "N/A")
    level = pdata.get("level", 1)
    
    text = [
        f"👤 <b>Detalhes de {name}</b>",
        f"<b>ID:</b> <code>{str(target_user_id)}</code>", # Convertido para string para segurança visual
        f"<b>Nível:</b> {level}",
        f"<b>Conta Criada:</b> {created_at_str}",
        f"<b>Última Interação:</b> {last_seen_str}",
        "\nO que deseja fazer?"
    ]
    
    keyboard = [
        # O f-string lida bem com ObjectId automaticamente, convertendo pra string no callback_data
        [InlineKeyboardButton("🗑️ APAGAR ESTE JOGADOR", callback_data=f"admin_pmanage_delconf:{target_user_id}")],
        [InlineKeyboardButton("⬅️ Voltar para a Lista", callback_data="admin_pmanage_list:1")],
        [InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="admin_pmanage_main")],
    ]
    
    await query.edit_message_text(
        "\n".join(text), 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode="HTML"
    )
    return PLAYER_DETAIL

# ==========================================================
# PASSO 4: Apagar Jogador (Confirmação e Execução)
# ==========================================================

async def confirm_delete_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mostra o botão de confirmação final para apagar."""
    query = update.callback_query
    await query.answer()

    raw_id = query.data.split(':')[-1]
    target_user_id = parse_hybrid_id(raw_id)
    context.user_data['target_user_id'] = target_user_id 
    
    pdata = await player_manager.get_player_data(target_user_id)
    name = pdata.get("character_name", f"ID {target_user_id}") if pdata else f"ID {target_user_id}"

    text = (
        f"‼️ <b>ATENÇÃO: AÇÃO IRREVERSÍVEL</b> ‼️\n\n"
        f"Você tem <b>ABSOLUTA CERTEZA</b> que quer apagar o jogador <b>{name}</b> (<code>{target_user_id}</code>)?\n\n"
        f"Todos os dados (inventário, progresso, etc) serão perdidos permanentemente."
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ SIM, APAGAR PERMANENTEMENTE", callback_data=f"admin_pmanage_dodelete:{target_user_id}")],
        [InlineKeyboardButton("❌ NÃO, CANCELAR", callback_data=f"admin_pmanage_detail:{target_user_id}")],
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return CONFIRM_DELETE

async def execute_delete_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Executa a exclusão do jogador."""
    query = update.callback_query
    await query.answer("Processando exclusão...")

    raw_id = query.data.split(':')[-1]
    target_user_id = parse_hybrid_id(raw_id)
    
    try:
        deleted_ok = player_manager.delete_player(target_user_id)
        
        if deleted_ok:
            await query.edit_message_text(f"✅ Jogador <code>{target_user_id}</code> foi apagado com sucesso.")
        else:
            await query.edit_message_text(f"⚠️ Jogador <code>{target_user_id}</code> não foi encontrado na base de dados.")
            
    except Exception as e:
        logger.error(f"Erro ao tentar apagar jogador {target_user_id}: {e}", exc_info=True)
        await query.edit_message_text(f"Ocorreu um erro ao apagar o jogador: {e}")

    context.user_data.clear()
    await asyncio.sleep(3)
    return await show_main_management_menu(update, context)

# ==========================================================
# PASSO 5: Encontrar Jogador (Fluxo de Busca)
# ==========================================================

async def ask_find_player_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pede o ID ou Nome do jogador para a busca."""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "🔍 <b>Encontrar Jogador</b>\n\n"
        "Envie o ID (número) ou o Nome exato do personagem que você quer ver.\n\n"
        "Use /cancelar para sair.",
        parse_mode="HTML"
    )
    return ASK_PLAYER_TO_FIND 

async def show_player_detail_from_find(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Função intermediária. O 'confirmar_jogador' (do utils) já encontrou 
    o jogador. Agora, vamos forjar um callback para o menu de detalhes.
    """
    target_user_id = context.user_data.get('target_user_id')
    if not target_user_id:
        await update.message.reply_text("Erro ao encontrar o jogador. Tente novamente.")
        return await show_main_management_menu(update, context)

    fake_query_data = f"admin_pmanage_detail:{target_user_id}"
    
    # Cria um objeto CallbackQuery simulado para reutilizar a função show_player_detail
    fake_query = CallbackQuery(
        id="fake_query_id", 
        from_user=update.effective_user, 
        chat_instance="fake_instance", 
        data=fake_query_data, 
        message=update.effective_message,
        _bot=context.bot # Necessário para .answer() funcionar no PTB v20+
    )
    
    fake_update = Update(update_id=update.update_id, callback_query=fake_query)
    
    return await show_player_detail(fake_update, context)


# ==========================================================
# Handler da Conversa
# ==========================================================

player_management_conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(show_main_management_menu, pattern=r"^admin_pmanage_main$")
    ],
    states={
        MAIN_MENU: [
            CallbackQueryHandler(list_inactive_pager, pattern=r"^admin_pmanage_list:"),
            CallbackQueryHandler(ask_find_player_input, pattern=r"^admin_pmanage_find$"),
            CallbackQueryHandler(show_main_management_menu, pattern=r"^admin_main$"), 
        ],
        LIST_INACTIVE: [
            CallbackQueryHandler(show_player_detail, pattern=r"^admin_pmanage_detail:"),
            CallbackQueryHandler(list_inactive_pager, pattern=r"^admin_pmanage_list:"),
            CallbackQueryHandler(show_main_management_menu, pattern=r"^admin_pmanage_main$"),
        ],
        PLAYER_DETAIL: [
            CallbackQueryHandler(confirm_delete_player, pattern=r"^admin_pmanage_delconf:"),
            CallbackQueryHandler(list_inactive_pager, pattern=r"^admin_pmanage_list:"), 
            CallbackQueryHandler(show_main_management_menu, pattern=r"^admin_pmanage_main$"),
        ],
        CONFIRM_DELETE: [
            CallbackQueryHandler(execute_delete_player, pattern=r"^admin_pmanage_dodelete:"),
            CallbackQueryHandler(show_player_detail, pattern=r"^admin_pmanage_detail:"), 
        ],
        ASK_PLAYER_TO_FIND: [ 
            MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_LIST), confirmar_jogador(show_player_detail_from_find))
        ],
        CONFIRMAR_JOGADOR: [ 
             CallbackQueryHandler(jogador_confirmado(show_player_detail_from_find), pattern=r"^confirm_player_")
        ],
    },
    fallbacks=[
        CommandHandler("cancelar", cancelar_conversa, filters=filters.User(ADMIN_LIST)),
        CallbackQueryHandler(cancelar_conversa, pattern=r"^cancelar_admin_conv$"),
        CallbackQueryHandler(show_main_management_menu, pattern=r"^admin_main$"),
    ],
    name="player_management_conv",
    persistent=False,
    per_message=False
)