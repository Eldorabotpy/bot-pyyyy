# modules/events/event_menu.py
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, Application

# ✅ TROCA: importar também a versão async robusta
from modules.auth_utils import get_current_player_id, get_current_player_id_async, requires_login
from modules import player_manager

logger = logging.getLogger(__name__)

# Tenta importar o manager da defesa de forma segura
try:
    from kingdom_defense.engine import event_manager as defense_manager
    DEFENSE_AVAILABLE = True
except ImportError:
    defense_manager = None
    DEFENSE_AVAILABLE = False


# =============================================================================
# CONFIG: RECOMPENSAS DIÁRIAS (1x por dia, não acumula)
# =============================================================================
DAILY_REWARDS = {
    "ticket_defesa_reino": 4,
    "ticket_arena": 10,
    "cristal_de_abertura": 4,
}

# Campo salvo no player para travar 1 resgate por dia
DAILY_CLAIM_FIELD = "daily_event_entries_claim_date"

# “Meia-noite” local: ajuste se seu servidor estiver em outro fuso.
# Se você roda no Brasil (-03:00), isso atende o seu requisito.
LOCAL_TZ = timezone(timedelta(hours=-3))


def _today_local_str() -> str:
    """Data local (YYYY-MM-DD) para reset diário por 'meia-noite' local."""
    return datetime.now(LOCAL_TZ).date().isoformat()


async def _safe_answer(query, text: str | None = None, alert: bool = False):
    try:
        if text is None:
            await query.answer()
        else:
            await query.answer(text, show_alert=alert)
    except Exception:
        pass


async def _edit_or_resend(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup: InlineKeyboardMarkup):
    """Edita a mensagem quando possível; se falhar, envia uma nova."""
    query = update.callback_query
    try:
        if query and query.message and (query.message.photo or query.message.video or query.message.document or query.message.animation):
            # Se tinha mídia, é mais seguro apagar e reenviar texto
            try:
                await query.message.delete()
            except Exception:
                pass
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )
        else:
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )
    except Exception as e:
        logger.warning(f"[EVENT_MENU] Fallback edit/send: {e}")
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )
        except Exception:
            pass


# =============================================================================
# MENU PRINCIPAL DE EVENTOS
# =============================================================================
async def show_active_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a lista de eventos disponíveis + botão de reivindicar entradas diárias."""
    query = update.callback_query
    if not query:
        return

    await _safe_answer(query)

    text = (
        "🌌 **HUB DE EVENTOS DE ELDORA** 🌌\n\n"
        "Os eventos da magia trazem desafios temporários para o reino.\n"
        "Escolha um evento para participar:"
    )

    keyboard: list[list[InlineKeyboardButton]] = []

    # 1) Catacumbas / Raid
    keyboard.append([
        InlineKeyboardButton("💀 Catacumbas do Reino (Raid)", callback_data="evt_cat_menu")
    ])

    # 2) Defesa do Reino
    is_defense_on = False
    if DEFENSE_AVAILABLE and defense_manager is not None:
        try:
            if getattr(defense_manager, "is_active", False):
                is_defense_on = True
        except Exception as e:
            logger.error(f"[EVENT_MENU] Erro ao checar defesa: {e}")

    btn_text = "🔥 DEFESA DO REINO (EM ANDAMENTO!) 🔥" if is_defense_on else "🛡️ Defesa do Reino (Inativo)"
    keyboard.append([
        InlineKeyboardButton(btn_text, callback_data="defesa_reino_main")
    ])

    # 3) Reivindicar entradas diárias
    keyboard.append([
        InlineKeyboardButton("🎁 Reivindicar Entradas Diárias", callback_data="evt_claim_daily_entries")
    ])

    # 4) Voltar
    keyboard.append([
        InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data="show_kingdom_menu")
    ])

    await _edit_or_resend(update, context, text, InlineKeyboardMarkup(keyboard))


# =============================================================================
# REIVINDICAR ENTRADAS DIÁRIAS
# =============================================================================
@requires_login
async def claim_daily_entries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    # ✅ CORREÇÃO: pega ObjectId de forma robusta (RAM -> sessão persistente)
    player_id = await get_current_player_id_async(update, context)

    # (fallback extra de segurança: se algo estranho acontecer)
    if not player_id:
        # tenta a versão síncrona só por compatibilidade (não costuma ser necessário)
        player_id = get_current_player_id(update, context)

    if not player_id:
        await _safe_answer(query, "❌ Sessão inválida. Use /start para reconectar.", alert=True)
        return

    pdata = await player_manager.get_player_data(player_id)
    if not pdata:
        await _safe_answer(query, "❌ Jogador não encontrado. Use /start para reconectar.", alert=True)
        return

    today = _today_local_str()
    last_claim = str(pdata.get(DAILY_CLAIM_FIELD) or "")

    if last_claim == today:
        await _safe_answer(query, "⏳ Você já reivindicou hoje. Volte amanhã!", alert=True)
        return

    # Entrega itens (1x/dia)
    try:
        for item_id, qty in DAILY_REWARDS.items():
            player_manager.add_item_to_inventory(pdata, item_id, int(qty))
    except Exception as e:
        logger.error(f"[EVENT_MENU] Erro ao adicionar itens diários: {e}")
        await _safe_answer(query, "❌ Erro ao conceder recompensas. Tente novamente.", alert=True)
        return

    pdata[DAILY_CLAIM_FIELD] = today
    await player_manager.save_player_data(player_id, pdata)

    msg = (
        "🎁 **ENTRADAS DIÁRIAS REIVINDICADAS!**\n\n"
        f"🛡️ **Ticket Defesa do Reino:** +{DAILY_REWARDS['ticket_defesa_reino']}\n"
        f"🎟️ **Entrada da Arena:** +{DAILY_REWARDS['ticket_arena']}\n"
        f"🔹 **Cristal de Abertura:** +{DAILY_REWARDS['cristal_de_abertura']}\n\n"
        "⏱️ *Você só pode reivindicar 1 vez por dia. O resgate reseta à meia-noite.*"
    )

    await _safe_answer(query)
    try:
        await query.edit_message_text(
            text=msg,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Voltar ao Hub de Eventos", callback_data="back_to_event_hub")],
                [InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data="show_kingdom_menu")],
            ]),
            parse_mode="Markdown",
        )
    except Exception:
        # fallback: manda separado
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=msg,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Voltar ao Hub de Eventos", callback_data="back_to_event_hub")],
                    [InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data="show_kingdom_menu")],
                ])
            )
        except Exception:
            pass


# =============================================================================
# REGISTRO
# =============================================================================
def register_handlers(application: Application):
    # Entrada do HUB — seu kingdom.py usa abrir_hub_eventos_v2
    application.add_handler(CallbackQueryHandler(show_active_events, pattern=r"^abrir_hub_eventos_v2$"))

    # Compatibilidade (caso você ainda tenha botões antigos)
    application.add_handler(CallbackQueryHandler(show_active_events, pattern=r"^evt_hub_principal$"))
    application.add_handler(CallbackQueryHandler(show_active_events, pattern=r"^back_to_event_hub$"))

    # Reivindicar diários
    application.add_handler(CallbackQueryHandler(claim_daily_entries, pattern=r"^evt_claim_daily_entries$"))
