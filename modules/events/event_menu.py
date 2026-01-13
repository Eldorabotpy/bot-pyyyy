# modules/events/event_menu.py
# (VERSÃO FINAL: Hub de Eventos + Claim Diário 1x/dia + SOMENTE ObjectId via login/senha)

from __future__ import annotations

import logging
import datetime
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, Application

from modules import player_manager
from modules.auth_utils import get_current_player_id  # ✅ ID do jogador (ObjectId / sessão)

logger = logging.getLogger(__name__)

# Timezone do reset diário (usa config se existir; fallback Fortaleza)
try:
    from config import JOB_TIMEZONE
except Exception:
    JOB_TIMEZONE = "America/Fortaleza"


def _today_str() -> str:
    """Data do dia no fuso do jogo."""
    try:
        tz = ZoneInfo(JOB_TIMEZONE)
    except Exception:
        tz = ZoneInfo("America/Fortaleza")
    return datetime.datetime.now(tz).date().isoformat()


# Tenta importar o manager da defesa de forma segura
try:
    from kingdom_defense.engine import event_manager as defense_manager
    DEFENSE_AVAILABLE = True
except ImportError:
    DEFENSE_AVAILABLE = False
    defense_manager = None


async def show_active_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a lista de eventos disponíveis."""
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass

    text = (
        "🌌 **HUB DE EVENTOS DE ELDORA** 🌌\n\n"
        "Os ventos da magia trazem desafios temporários para o reino.\n"
        "Escolha um evento para participar:"
    )

    keyboard = []

    # 1) Catacumbas (Raid)
    keyboard.append([
        InlineKeyboardButton("💀 Catacumbas do Reino (Raid)", callback_data="evt_cat_menu")
    ])

    # 2) Defesa do Reino
    is_defense_on = False
    if DEFENSE_AVAILABLE and defense_manager:
        try:
            is_defense_on = bool(getattr(defense_manager, "is_active", False))
        except Exception as e:
            logger.error(f"Erro ao checar status da defesa: {e}")

    btn_text = "🔥 DEFESA DO REINO (EM ANDAMENTO!) 🔥" if is_defense_on else "🛡️ Defesa do Reino (Inativo)"
    keyboard.append([
        InlineKeyboardButton(btn_text, callback_data="defesa_reino_main")
    ])

    # 3) ✅ Claim diário
    keyboard.append([
        InlineKeyboardButton("🎁 Reivindicar Entradas Diárias", callback_data="evt_claim_daily_entries")
    ])

    # 4) Voltar
    keyboard.append([
        InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data="show_kingdom_menu")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Tenta editar a mensagem atual; se falhar (ex.: mensagem antiga era mídia), envia nova
    try:
        if query and query.message:
            # Se for mídia, delete e envia texto
            if getattr(query.message, "photo", None) or getattr(query.message, "video", None) or getattr(query.message, "document", None):
                try:
                    await query.message.delete()
                except Exception:
                    pass
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            else:
                await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.warning(f"Fallback no menu de eventos: {e}")
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception:
            pass


async def evt_claim_daily_entries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Claim 1x por dia (SOMENTE ObjectId via login/senha).
    Entrega (SET, não soma) para não acumular:
      - ticket_arena: 10
      - ticket_defesa_reino: 4
      - cristal_de_abertura: 4
    """
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass

    # ✅ Usa o ID do jogador (ObjectId / sessão autenticada), NÃO usa Telegram ID
    player_id = get_current_player_id(update, context)
    if not player_id:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Voltar aos Eventos", callback_data="back_to_event_hub")],
            [InlineKeyboardButton("🏰 Voltar ao Reino", callback_data="show_kingdom_menu")],
        ])
        try:
            await query.edit_message_text(
                "❌ Sessão inválida ou expirada.\n\n"
                "Faça login novamente e tente de novo.",
                reply_markup=kb,
                parse_mode="Markdown"
            )
        except Exception:
            pass
        return

    pdata = await player_manager.get_player_data(player_id)
    if not pdata:
        try:
            await query.edit_message_text("❌ Jogador não encontrado (ID inválido).")
        except Exception:
            pass
        return

    today = _today_str()

    daily_claims = pdata.get("daily_claims") or {}
    last = str(daily_claims.get("event_entries_claim_date", ""))

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar aos Eventos", callback_data="back_to_event_hub")],
        [InlineKeyboardButton("🏰 Voltar ao Reino", callback_data="show_kingdom_menu")],
    ])

    if last == today:
        try:
            await query.edit_message_text(
                "⏳ Você já reivindicou suas entradas de hoje.\n\n"
                "_O resete acontece à meia-noite._",
                reply_markup=kb,
                parse_mode="Markdown"
            )
        except Exception:
            pass
        return

    inv = pdata.get("inventory") or {}

    # ✅ SET (não acumula)
    inv["ticket_arena"] = 10
    inv["ticket_defesa_reino"] = 4
    inv["cristal_de_abertura"] = 4

    daily_claims["event_entries_claim_date"] = today

    pdata["inventory"] = inv
    pdata["daily_claims"] = daily_claims

    # Salva usando ObjectId
    try:
        await player_manager.save_player_data(player_id, pdata)
    except Exception as e:
        logger.error(f"Erro ao salvar claim diário: {e}")
        try:
            await query.edit_message_text("❌ Erro ao salvar no banco. Tente novamente.")
        except Exception:
            pass
        return

    msg = (
        "✅ **Entradas diárias reivindicadas!**\n\n"
        "🎟️ **Entrada da Arena:** 10\n"
        "🎟️ **Ticket de Defesa:** 4\n"
        "🔹 **Cristal de Abertura:** 4\n\n"
        "_Reseta à meia-noite (não acumula)._"
    )

    try:
        await query.edit_message_text(msg, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=msg,
                reply_markup=kb,
                parse_mode="Markdown"
            )
        except Exception:
            pass


def register_handlers(application: Application):
    """
    Registra os handlers deste módulo.
    Mantém compatibilidade com callbacks antigos/novos.
    """
    # Menu de eventos
    application.add_handler(CallbackQueryHandler(show_active_events, pattern=r"^evt_hub_principal$"))
    application.add_handler(CallbackQueryHandler(show_active_events, pattern=r"^back_to_event_hub$"))

    # Compatibilidade (outros menus podem chamar isso)
    application.add_handler(CallbackQueryHandler(show_active_events, pattern=r"^abrir_hub_eventos_v2$"))

    # Claim diário
    application.add_handler(CallbackQueryHandler(evt_claim_daily_entries, pattern=r"^evt_claim_daily_entries$"))
