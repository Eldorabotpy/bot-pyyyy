# handlers/menu/events.py
# (VERSÃO FINAL: Hub de Eventos + Claim Diário 1x por dia + sem acúmulo)
# (OBJETIVO: 100% ObjectId — sem dependência de Telegram ID)

from __future__ import annotations

import logging
import datetime
from zoneinfo import ZoneInfo

from bson import ObjectId
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager

# Identificação do jogador via sessão/login (ObjectId)
try:
    from modules.auth_utils import get_current_player_id_async
except Exception:  # pragma: no cover
    get_current_player_id_async = None  # type: ignore

# Tenta importar o manager da defesa
try:
    from kingdom_defense.engine import event_manager
    DEFENSE_AVAILABLE = True
except ImportError:
    DEFENSE_AVAILABLE = False
    event_manager = None

logger = logging.getLogger(__name__)

# Usa o mesmo timezone do bot (JOB_TIMEZONE). Se falhar, usa Fortaleza.
try:
    from config import JOB_TIMEZONE
except Exception:
    JOB_TIMEZONE = "America/Fortaleza"


def _today_str() -> str:
    try:
        tz = ZoneInfo(JOB_TIMEZONE)
    except Exception:
        tz = ZoneInfo("America/Fortaleza")
    return datetime.datetime.now(tz).date().isoformat()


async def show_events_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Exibe o Hub de Eventos (Defesa do Reino, Raids, etc).
    CORREÇÃO: Deleta a mensagem anterior para evitar erro de edição (foto -> texto).
    """
    callback = update.callback_query
    if callback:
        try:
            await callback.answer()
        except Exception:
            pass

    text = (
        "🌌 **HUB DE EVENTOS DE ELDORA** 🌌\n\n"
        "Os ventos da magia trazem desafios temporários para o reino.\n"
        "Escolha um evento para participar:\n\n"
        "🎁 **Entradas Diárias:** pegue 1x por dia (reseta à meia-noite)."
    )

    keyboard = []

    # Catacumbas (Raid)
    keyboard.append([InlineKeyboardButton("💀 Catacumbas (Raid)", callback_data="evt_cat_menu")])

    # Defesa do Reino (se disponível)
    defense_btn_text = "🛡️ Defesa do Reino"
    if DEFENSE_AVAILABLE and event_manager:
        if getattr(event_manager, "is_active", False):
            try:
                status = event_manager.get_queue_status_text()
            except Exception:
                status = "Evento em andamento!"
            defense_btn_text = f"🔥 DEFESA DO REINO ({getattr(event_manager, 'current_wave', 1)}ª Onda)"
            text += f"\n\n🚨 **ALERTA DE INVASÃO:**\n{status}"

    keyboard.append([InlineKeyboardButton(defense_btn_text, callback_data="defesa_reino_main")])

    # Claim diário
    keyboard.append([InlineKeyboardButton("🎁 Reivindicar Entradas Diárias", callback_data="evt_claim_daily_entries")])

    # Voltar ao Reino
    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data="show_kingdom_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Deleta a mensagem anterior para não dar erro quando a anterior era foto/vídeo
    try:
        if callback and callback.message:
            await callback.message.delete()
    except Exception as e:
        logger.warning(f"Não foi possível apagar mensagem anterior: {e}")

    if update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )


async def evt_claim_daily_entries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Claim 1x por dia:
      - 10 ticket_arena
      - 4 ticket_defesa_reino
      - 4 cristal_de_abertura
    Não acumula porque o JOB da meia-noite zera tudo.
    """
    callback = update.callback_query
    if callback:
        try:
            await callback.answer()
        except Exception:
            pass

    if not get_current_player_id_async:
        msg = (
            "❌ Sistema de autenticação indisponível.\n\n"
            "get_current_player_id_async não pôde ser importado. Verifique modules/auth_utils.py."
        )
        if callback:
            try:
                await callback.edit_message_text(msg)
            except Exception:
                pass
        return

    player_id = await get_current_player_id_async(update, context)
    if not player_id:
        msg = "❌ Não foi possível identificar seu jogador. Faça login novamente."
        if callback:
            try:
                await callback.edit_message_text(msg)
            except Exception:
                pass
        return

    # Normalização defensiva: garante ObjectId
    if isinstance(player_id, str):
        if ObjectId.is_valid(player_id):
            player_id = ObjectId(player_id)
        else:
            msg = "❌ Sessão inválida (player_id não é ObjectId). Faça login novamente."
            if callback:
                try:
                    await callback.edit_message_text(msg)
                except Exception:
                    pass
            return
    elif not isinstance(player_id, ObjectId):
        msg = "❌ Sessão inválida (player_id não é ObjectId). Faça login novamente."
        if callback:
            try:
                await callback.edit_message_text(msg)
            except Exception:
                pass
        return

    pdata = await player_manager.get_player_data(player_id)
    if not pdata:
        if callback:
            await callback.edit_message_text("❌ Jogador não encontrado.")
        return

    today = _today_str()

    daily_claims = pdata.get("daily_claims") or {}
    last_date = str(daily_claims.get("event_entries_claim_date", ""))

    if last_date == today:
        if callback:
            await callback.edit_message_text(
                "⏳ Você já reivindicou suas entradas de hoje.\n\n"
                "O resete acontece à meia-noite."
            )
        return

    inv = pdata.get("inventory") or {}

    # Define (SET) para impedir acumular por qualquer motivo
    inv["ticket_arena"] = 10
    inv["ticket_defesa_reino"] = 4
    inv["cristal_de_abertura"] = 4

    daily_claims["event_entries_claim_date"] = today

    pdata["inventory"] = inv
    pdata["daily_claims"] = daily_claims

    await player_manager.save_player_data(player_id, pdata)

    text = (
        "✅ **Entradas diárias reivindicadas!**\n\n"
        "🎟️ **Entrada da Arena:** 10\n"
        "🎟️ **Ticket de Defesa:** 4\n"
        "🔹 **Cristal de Abertura:** 4\n\n"
        "_Reseta à meia-noite (não acumula)._\n"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar aos Eventos", callback_data="abrir_hub_eventos_v2")],
        [InlineKeyboardButton("🏰 Voltar ao Reino", callback_data="show_kingdom_menu")],
    ])

    try:
        if callback:
            await callback.edit_message_text(text=text, reply_markup=kb, parse_mode="Markdown")
        else:
            raise RuntimeError("callback_query ausente")
    except Exception:
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=kb,
                parse_mode="Markdown"
            )


# ------------------------------------------------------------------------------
# HANDLERS EXPORTADOS
# ------------------------------------------------------------------------------
events_menu_handler = CallbackQueryHandler(show_events_menu, pattern=r"^abrir_hub_eventos_v2$")
evt_claim_daily_entries_handler = CallbackQueryHandler(evt_claim_daily_entries, pattern=r"^evt_claim_daily_entries$")
