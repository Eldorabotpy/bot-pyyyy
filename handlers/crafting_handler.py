# handlers/crafting_handler.py

import logging

from telegram import (
    Update,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules.auth_utils import get_current_player_id
# --- Importação da Função de Destino ---
# Importamos diretamente a função que deve ser chamada quando o jogador entra na forja.
# Esta função é responsável por mostrar as profissões (Ferreiro, Artesão, etc.).
try:
    from .forge_handler import show_forge_professions_menu
    # Definimos a variável `CRAFT_IMPL` para ser a nossa função de destino.
    # Isso torna o código mais limpo e fácil de entender.
    CRAFT_IMPL = show_forge_professions_menu
except ImportError:
    # Se a função não for encontrada, definimos como None e avisamos no log.
    logging.getLogger(__name__).error(
        "CRITICAL: A função 'show_forge_professions_menu' não foi encontrada em 'handlers/forge_handler.py'."
    )
    CRAFT_IMPL = None


# --- Módulos do Jogo ---
# Mantemos os outros imports que podem ser úteis em futuras expansões.
from modules import player_manager, mission_manager, game_data, crafting_engine, crafting_registry, file_ids, clan_manager


logger = logging.getLogger(__name__)


async def _safe_edit_or_send(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup = None,
    parse_mode: str = 'HTML'
):
    """
    Função utilitária para editar uma mensagem existente ou enviar uma nova,
    evitando erros caso a mensagem original não possa ser editada.
    """
    try:
        # Tenta editar a legenda: MANTÉM a mídia (vídeo/imagem) original.
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except Exception:
        pass  # Ignora erro de edição de legenda e tenta a próxima
    try:
        # Tenta editar o texto: REMOVE a mídia (se houver) ou edita a mensagem de texto.
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except Exception:
        pass  # Ignora erro de edição de texto e envia uma nova mensagem
    
    # Envia uma nova mensagem: Usado se nenhuma edição for possível.
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

async def craft_open_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Roteador principal para o fluxo de forja.

    Esta função é acionada por um CallbackQuery e sua única responsabilidade
    é chamar a função de implementação real da forja (`CRAFT_IMPL`).
    """
    query = update.callback_query
    logger.info(f"Roteador de Forja ativado pelo callback: '{query.data}'")
    await query.answer() # Já estava correto

    if CRAFT_IMPL:
        try:
            # <<< CORREÇÃO: Adiciona await AQUI >>>
            # CRAFT_IMPL (show_forge_professions_menu) é uma função async
            await CRAFT_IMPL(update, context)
            return # Sai se a função foi chamada com sucesso
        except Exception as e:
            logger.exception(f"Falha ao executar a implementação da forja (CRAFT_IMPL): {e}")

    # Mensagem de fallback caso CRAFT_IMPL não esteja definido ou ocorra um erro.
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar", callback_data="show_kingdom_menu")]
    ])
    error_text = "⚒️ **Erro na Forja** ⚒️\n\nNão foi possível iniciar o sistema de forja. Por favor, avise um administrador."
    # <<< CORREÇÃO: Adiciona await AQUI >>> (já estava correto na definição)
    await _safe_edit_or_send(query, context, query.message.chat.id, error_text, kb)

# --- Definição do Handler ---
# Este handler captura os diferentes callbacks que podem iniciar o fluxo de forja.
craft_open_handler = CallbackQueryHandler(
    craft_open_router,
    # O padrão regex foi atualizado para incluir 'forge:main',
    # que é o callback usado nos menus principais.
    pattern=r'^(open_crafting|craft_main|craft_open|forge_craft|forge:main)$'
)