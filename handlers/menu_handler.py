# handlers/menu_handler.py
import logging
from time import monotonic
from typing import Callable, Awaitable, Optional, Dict

from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

from modules import player_manager
from .menu.kingdom import show_kingdom_menu
from .menu.region import show_travel_menu, show_region_menu
from .menu.events import show_events_menu


# ---- IMPORT FORGE OPCIONAL / COM FALLBACK ----
try:
    from .menu.forge import show_forge_menu  # type: ignore
except Exception:
    show_forge_menu = None  # type: ignore
# ----------------------------------------------

logger = logging.getLogger(__name__)

# -------------------------
# Anti-flood (simples)
# -------------------------
_LAST_CLICK: Dict[int, float] = {}
_MIN_DELTA = 0.4  # segundos

def _allow_click(user_id: int) -> bool:
    t = monotonic()
    last = _LAST_CLICK.get(user_id, 0.0)
    if t - last < _MIN_DELTA:
        return False
    _LAST_CLICK[user_id] = t
    return True

# -------------------------
# Helpers de segurança
# -------------------------
async def _safe_answer(update: Update) -> None:
    """Responde ao callback sem estourar exceção se já foi respondido."""
    query = update.callback_query
    if not query:
        return
    try:
        await query.answer()
    except BadRequest:
        pass
    except Exception:
        logger.debug("Falha silenciosa em query.answer()", exc_info=True)

async def _error_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE, msg: str) -> None:
    q = update.callback_query
    try:
        await q.edit_message_text(msg)
    except Exception:
        await context.bot.send_message(chat_id=q.message.chat.id, text=msg)

# -------------------------
# Aliases (compat antiga)
# -------------------------
ALIASES = {
    "menu_navegar": "show_kingdom_menu",
    "open_regions": "travel",
    "show_kingdom": "show_kingdom_menu",
    "arena_de_eldora": "pvp_arena",
    # Forja
    "forja": "forge",
    "open_forge": "forge",
    "show_forge": "forge",
}

# -------------------------
# Router (nome -> função)
# -------------------------
async def _go_kingdom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_kingdom_menu(update, context)

async def _go_travel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_travel_menu(update, context)

async def _go_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_events_menu(update, context)


async def _go_forge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if show_forge_menu:
        await show_forge_menu(update, context)  # type: ignore
    else:
        await q.edit_message_text("⚒️ Forja ainda não está disponível.")

ROUTES: Dict[str, Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]] = {
    "show_kingdom_menu": _go_kingdom,
    "navigate_reino_eldora": _go_kingdom,   # compat
    "travel": _go_travel,
    "show_events_menu": _go_events,
    "forge": _go_forge,
}

async def continue_after_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    player_data = player_manager.get_player_data(user_id)
    if not player_data:
        await query.edit_message_text("Jogador não encontrado. Use /start.")
        return

    # 1. Pega a localização atual salva nos dados do jogador
    location_key = player_data.get('current_location', 'reino_eldora')
    
    try:
        await query.delete_message()
    except Exception:
        pass # Ignora se não conseguir apagar a mensagem anterior
    
    # 2. Chama a função de menu para a localização CORRETA
    if location_key == 'reino_eldora':
        await show_kingdom_menu(update, context)
    else:
        # AQUI ESTÁ A CORREÇÃO: passamos a location_key para a função
        await show_region_menu(update, context, region_key=location_key)

# --- EXPORT DOS HANDLERS ---
# Em vez de um handler gigante, exportamos handlers específicos e limpos.

# Handler inteligente para voltar à aventura
continue_after_action_handler = CallbackQueryHandler(
    continue_after_action_callback, pattern=r'^continue_after_action$'
)

# Handler para o menu principal do reino (se chamado por um botão)
kingdom_menu_handler = CallbackQueryHandler(
    show_kingdom_menu, pattern=r'^show_kingdom_menu$'
)

# Handler dedicado para o botão "Viajar"
travel_handler = CallbackQueryHandler(
    show_travel_menu, pattern=r'^travel$'
)

# -------------------------
# Handler principal
# -------------------------
async def navigation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("\n>>> RASTREAMENTO: Entrou em navigation_callback")
    await _safe_answer(update)
    query = update.callback_query
    if not query:
        return

    user_id = query.from_user.id
    if not _allow_click(user_id):
        # silêncio em flood curto
        return

    # --- estado do jogador ---
    player_data = player_manager.get_player_data(user_id)
    if not player_data:
        await _error_fallback(update, context, "Não encontrei seus dados. Use /start para começar.")
        return

    # Evita quebrar ações com tempo
    player_state = player_data.get("player_state", {"action": "idle"})
    data = (query.data or "").strip()
    if not data:
        await _error_fallback(update, context, "Botão inválido.")
        return

    # normaliza alias
    button = ALIASES.get(data, data)

    if player_state.get("action") not in ("idle", None) and button != "continue_after_action":
        await query.answer("Você está em uma ação no momento. Conclua antes de navegar.", show_alert=True)
        return

    try:
        # rota especial: retomar após ação
        if button == "continue_after_action":
            current_location = player_data.get("current_location", "reino_eldora")
            if current_location == "reino_eldora":
                await show_kingdom_menu(update, context)
            else:
                await show_region_menu(update, context)
            return

        # despacho por tabela
        handler = ROUTES.get(button)
        if handler:
            await handler(update, context)
            return

        # Fallback: desconhecido -> volta ao menu do local atual
        logger.info("Botão de navegação desconhecido: %s", button)
        current_location = player_data.get("current_location", "reino_eldora")
        if current_location == "reino_eldora":
            await show_kingdom_menu(update, context)
        else:
            await show_region_menu(update, context)

    except Exception:
        logger.exception("Erro ao processar botão de navegação: %s", button)
        await _error_fallback(update, context, "❌ Ocorreu um erro ao processar o menu. Tente novamente.")

navigation_handler = CallbackQueryHandler(
    navigation_callback,
    pattern=(
        r'^(travel|navigate_reino_eldora|continue_after_action|show_events_menu|'
        r'show_kingdom_menu|pvp_arena|arena_de_eldora|menu_navegar|open_regions|show_kingdom|'
        r'forge|forja|open_forge|show_forge)$'
    ),
)
