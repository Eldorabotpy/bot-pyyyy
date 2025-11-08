# handlers/admin/grant_skin.py
import logging
import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

# --- Imports Corrigidas ---
from modules import player_manager
from modules.game_data.skins import SKIN_CATALOG # Importa o catálogo de skins
from handlers.admin.utils import (
    ADMIN_LIST,
    ensure_admin, # Precisamos disto para o entry_point
    confirmar_jogador,
    jogador_confirmado,
    cancelar_conversa,
    INPUT_TEXTO,
    CONFIRMAR_JOGADOR,
)

logger = logging.getLogger(__name__)

# --- Constantes do Catálogo ---
SKINS_PER_PAGE = 8 # Quantas skins mostrar por página

# --- Novos Estados da Conversa ---
(SHOW_CATALOG, CONFIRMAR_GRANT) = range(2, 4) 
ASK_PLAYER = INPUT_TEXTO # Renomeia para clareza

# --- PASSO 1: Ponto de Entrada (Pede o Jogador) ---
async def grant_skin_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ponto de entrada: Pede o ID ou Nome do jogador."""
    if not await ensure_admin(update): return ConversationHandler.END
    
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "🎨 <b>Entregar Aparência (Skin)</b>\n\n"
        "Envie o ID (número) ou o Nome exato do personagem que receberá a skin.\n\n"
        "Use /cancelar para sair.",
        parse_mode="HTML"
    )
    return ASK_PLAYER # Estado 0

# --- PASSO 2: Mostrar o Catálogo (Substitui o ask_skin_id) ---
async def show_skin_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1) -> int:
    """
    Jogador foi confirmado. Mostra o catálogo de skins paginado.
    """
    # Ordena todas as skins (do SKIN_CATALOG) por nome
    try:
        sorted_skins = sorted(
            SKIN_CATALOG.items(), 
            key=lambda item: item[1].get('display_name', item[0])
        )
    except Exception as e:
        logger.error(f"Erro ao ordenar SKIN_CATALOG: {e}")
        sorted_skins = list(SKIN_CATALOG.items())

    # Lógica de Paginação
    start_index = (page - 1) * SKINS_PER_PAGE
    end_index = start_index + SKINS_PER_PAGE
    paginated_skins = sorted_skins[start_index:end_index]
    
    total_pages = math.ceil(len(sorted_skins) / SKINS_PER_PAGE)

    keyboard = []
    for skin_id, skin_info in paginated_skins:
        skin_name = skin_info.get('display_name', skin_id)
        skin_class = skin_info.get('class', 'N/A').capitalize()
        
        button_text = f"[{skin_class}] {skin_name}"
        callback_data = f"admin_gskin_select:{skin_id}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    # Botões de Navegação de Página
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"admin_gskin_page:{page-1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("Próxima ➡️", callback_data=f"admin_gskin_page:{page+1}"))
    
    if nav_row:
        keyboard.append(nav_row)
        
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_admin_conv")])
    
    player_name = context.user_data['target_player_name']
    text = (
        f"Jogador: <code>{player_name}</code>\n"
        f"Selecione a Skin (Pág. {page}/{total_pages}):"
    )

    if update.callback_query and update.callback_query.data.startswith("admin_gskin_page"):
        await update.callback_query.edit_message_text(
            text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    return SHOW_CATALOG # Estado 2

# --- PASSO 2.5: Mudar de Página ---
async def skin_catalog_pager(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lida com os botões 'Anterior' e 'Próxima'."""
    await update.callback_query.answer()
    page = int(update.callback_query.data.split(':')[-1])
    await show_skin_catalog(update, context, page=page)
    return SHOW_CATALOG

# --- PASSO 3: Selecionar a Skin (Substitui o confirm_skin) ---
async def select_skin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin clicou numa skin. Valida e pede confirmação."""
    await update.callback_query.answer()
    skin_id = update.callback_query.data.split(':')[-1]

    skin_info = SKIN_CATALOG.get(skin_id)
    if not skin_info:
        await update.callback_query.answer("Erro: Skin não encontrada.", show_alert=True)
        return SHOW_CATALOG

    context.user_data['target_skin_id'] = skin_id
    
    target_player_name = context.user_data['target_player_name']
    skin_name = skin_info.get('display_name', skin_id)

    text = (
        f"<b>Confirmação Final</b>\n\n"
        f"Jogador: <code>{target_player_name}</code>\n"
        f"Aparência: <code>{skin_name}</code>\n\n"
        f"Você confirma?"
    )
    keyboard = [
        [InlineKeyboardButton("✅ Sim, entregar", callback_data="confirm_grant_skin")],
        [InlineKeyboardButton("⬅️ Voltar ao Catálogo", callback_data="back_to_skin_catalog")],
    ]
    await update.callback_query.edit_message_text(
        text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRMAR_GRANT # Estado 3

# --- PASSO 4: Confirmação Final ---
async def grant_skin_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """O admin confirmou. Adiciona a skin ao jogador."""
    await update.callback_query.answer()
    
    user_id = context.user_data['target_user_id']
    skin_id = context.user_data['target_skin_id']
    target_player_name = context.user_data['target_player_name']
    
    try:
        player_data = await player_manager.get_player_data(user_id)
        if not player_data:
            await update.callback_query.edit_message_text("Erro: O jogador alvo desapareceu. Ação cancelada.")
            return ConversationHandler.END

        player_skins = player_data.setdefault("unlocked_skins", [])
        
        if not isinstance(player_skins, list):
             player_skins = []
             player_data["unlocked_skins"] = player_skins

        if skin_id not in player_skins:
            player_skins.append(skin_id)
        else:
            await update.callback_query.edit_message_text(
                f"Aviso: <code>{target_player_name}</code> já possuía a skin <code>{skin_id}</code>.",
                parse_mode="HTML"
            )
            return ConversationHandler.END

        await player_manager.save_player_data(user_id, player_data)
        skin_name = SKIN_CATALOG.get(skin_id, {}).get('display_name', skin_id)
        
        await update.callback_query.edit_message_text(
            f"✅ Sucesso!\n\n"
            f"O jogador <code>{target_player_name}</code> recebeu a aparência <b>{skin_name}</b>!",
            parse_mode="HTML"
        )
        
        if user_id != update.effective_user.id:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🎨 Você recebeu uma nova aparência: <b>{skin_name}</b>!",
                    parse_mode="HTML"
                )
            except Exception:
                pass 

    except Exception as e:
        await update.callback_query.edit_message_text(f"Ocorreu um erro grave: {e}")

    context.user_data.clear()
    return ConversationHandler.END

# --- PASSO 5: Handler de "Voltar" ---
async def back_to_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Volta da confirmação para o catálogo."""
    await update.callback_query.answer()
    await show_skin_catalog(update, context, page=1)
    return SHOW_CATALOG

# --- Handler da Conversa (Atualizado) ---
grant_skin_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(grant_skin_entry, pattern=r"^admin_grant_skin$")],
    states={
        ASK_PLAYER: [ # Estado 0 (INPUT_TEXTO)
            MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_LIST), confirmar_jogador(show_skin_catalog))
        ],
        CONFIRMAR_JOGADOR: [ # Estado 1
             CallbackQueryHandler(jogador_confirmado(show_skin_catalog), pattern=r"^confirm_player_")
        ],
        SHOW_CATALOG: [ # Estado 2
            CallbackQueryHandler(select_skin_callback, pattern=r"^admin_gskin_select:"),
            CallbackQueryHandler(skin_catalog_pager, pattern=r"^admin_gskin_page:"),
        ],
        CONFIRMAR_GRANT: [ # Estado 3
            CallbackQueryHandler(grant_skin_confirmed, pattern=r"^confirm_grant_skin$"),
            CallbackQueryHandler(back_to_catalog, pattern=r"^back_to_skin_catalog$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancelar", cancelar_conversa, filters=filters.User(ADMIN_LIST)),
        CallbackQueryHandler(cancelar_conversa, pattern=r"^cancelar_admin_conv$"),
    ],
    per_message=False
)