# handlers/menu_handler.py
# (VERSÃO BLINDADA: AUTH HÍBRIDA + ANTI-FLOOD CORRIGIDO)

import logging
from time import monotonic
from typing import Callable, Awaitable, Optional, Dict, Union

from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

from modules import player_manager
from .menu.kingdom import show_kingdom_menu
from .menu.region import show_travel_menu, show_region_menu
from .menu.events import show_events_menu
from modules.auth_utils import requires_login

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
# Aceita ID numérico (Telegram) ou String (ObjectId)
_LAST_CLICK: Dict[Union[str, int], float] = {}
_MIN_DELTA = 0.4  # segundos

def _allow_click(user_id: Union[str, int]) -> bool:
    """Verifica se o usuário pode clicar novamente (rate limit)."""
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
    if update.callback_query:
        try: await update.callback_query.answer()
        except: pass

async def _error_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE, msg: str) -> None:
    try: await update.callback_query.edit_message_text(msg)
    except: 
        # Chat ID é sempre numérico (canal de comunicação), isso está correto
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

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
async def _go_kingdom(update, context): await show_kingdom_menu(update, context)
async def _go_travel(update, context): await show_travel_menu(update, context)
async def _go_events(update, context): await show_events_menu(update, context)
async def _go_forge(update, context):
    if show_forge_menu: await show_forge_menu(update, context)
    else: await update.callback_query.edit_message_text("⚒️ Forja indisponível.")
    
ROUTES: Dict[str, Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]] = {
    "show_kingdom_menu": _go_kingdom,
    "navigate_reino_eldora": _go_kingdom,   # compat
    "travel": _go_travel,
    "show_events_menu": _go_events,
    "forge": _go_forge,
}

@requires_login
async def continue_after_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # PEGA O ID DA SESSÃO (Garantido pelo decorator, pode ser str ou int)
    user_id = context.user_data["logged_player_id"]
    
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await query.edit_message_text("Jogador não encontrado.")
        return

    location_key = player_data.get('current_location', 'reino_eldora')
    try: await query.delete_message()
    except: pass
    
    if location_key == 'reino_eldora':
        await show_kingdom_menu(update, context)
    else:
        await show_region_menu(update, context, region_key=location_key)

# -------------------------
# Handler principal de Navegação
# -------------------------
@requires_login
async def navigation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _safe_answer(update)
    query = update.callback_query
    if not query: return

    # ✅ ID Seguro da Sessão (Str/Int)
    user_id = context.user_data["logged_player_id"]
    
    if not _allow_click(user_id): return

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await _error_fallback(update, context, "Dados não encontrados.")
        return

    player_state = player_data.get("player_state", {"action": "idle"})
    data = (query.data or "").strip()
    button = ALIASES.get(data, data)

    # Bloqueio de ação (exceto se for para continuar/voltar)
    if player_state.get("action") not in ("idle", None) and button != "continue_after_action":
        await query.answer("Conclua sua ação atual primeiro.", show_alert=True)
        return

    try:
        current_location = player_data.get("current_location", "reino_eldora")
        
        # Despacho por tabela de rotas
        handler = ROUTES.get(button)
        if handler:
            await handler(update, context)
            return

        # Fallback: volta ao menu do local atual
        logger.info("Botão desconhecido: %s -> Recarregando menu.", button)
        if current_location == "reino_eldora":
            await show_kingdom_menu(update, context)
        else:
            await show_region_menu(update, context, region_key=current_location)

    except Exception:
        logger.exception("Erro navegação: %s", button)
        await _error_fallback(update, context, "❌ Erro ao processar.")

# -------------------------
# Definição dos Handlers
# -------------------------
continue_after_action_handler = CallbackQueryHandler(continue_after_action_callback, pattern=r'^continue_after_action$')
kingdom_menu_handler = CallbackQueryHandler(show_kingdom_menu, pattern=r'^show_kingdom_menu$')
travel_handler = CallbackQueryHandler(show_travel_menu, pattern=r'^travel$')

navigation_handler = CallbackQueryHandler(
    navigation_callback,
    pattern=(
        r'^(travel|navigate_reino_eldora|continue_after_action|show_events_menu|'
        r'show_kingdom_menu|pvp_arena|arena_de_eldora|menu_navegar|open_regions|show_kingdom|'
        r'forge|forja|open_forge|show_forge)$'
    ),
)