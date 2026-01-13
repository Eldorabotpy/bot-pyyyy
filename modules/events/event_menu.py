# modules/events/event_menu.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, Application
import logging
import datetime
from zoneinfo import ZoneInfo

from modules import player_manager

logger = logging.getLogger(__name__)

# Timezone do reset diário (usa config se existir)
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
    """Mostra a lista de TODOS os eventos disponíveis."""
    query = update.callback_query
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

    # --- 1) Catacumbas (Raid) ---
    keyboard.append([
        InlineKeyboardButton("💀 Catacumbas do Reino (Raid)", callback_data="evt_cat_menu")
    ])

    # --- 2) Defesa do Reino ---
    is_defense_on = False
    if DEFENSE_AVAILABLE and defense_manager:
        try:
            if getattr(defense_manager, "is_active", False):
                is_defense_on = True
        except Exception as e:
            logger.error(f"Erro ao checar status da defesa: {e}")

    if is_defense_on:
        btn_text = "🔥 DEFESA DO REINO (EM ANDAMENTO!) 🔥"
    else:
        btn_text = "🛡️ Defesa do Reino (Inativo)"

    keyboard.append([
        InlineKeyboardButton(btn_text, callback_data="defesa_reino_main")
    ])

    # --- 3) ✅ NOVO: Claim diário (tickets + cristais) ---
    keyboard.append([
        InlineKeyboardButton("🎁 Reivindicar Entradas Diárias", callback_data="evt_claim_daily_entries")
    ])

    # --- 4) Voltar ---
    keyboard.append([
        InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data="show_kingdom_menu")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Lógica de envio seguro (Apaga msg anterior se for mídia, ou edita se for texto)
    try:
        if query.message.photo or query.message.video or query.message.document:
            await query.message.delete()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
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
    Claim 1x por dia (não acumula pois o JOB da meia-noite zera).
    Entrega:
      - ticket_arena: 10
      - ticket_defesa_reino: 4
      - cristal_de_abertura: 4
    """
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    user_id = str(query.from_user.id)

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        try:
            await query.edit_message_text("❌ Jogador não encontrado.")
        except Exception:
            pass
        return

    today = _today_str()

    daily_claims = pdata.get("daily_claims") or {}
    last = str(daily_claims.get("event_entries_claim_date", ""))

    if last == today:
        # Já pegou hoje
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Voltar aos Eventos", callback_data="back_to_event_hub")],
            [InlineKeyboardButton("🏰 Voltar ao Reino", callback_data="show_kingdom_menu")],
        ])
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

    # SET (não soma) para garantir que não acumule por bug/atraso
    inv["ticket_arena"] = 10
    inv["ticket_defesa_reino"] = 4
    inv["cristal_de_abertura"] = 4

    daily_claims["event_entries_claim_date"] = today

    pdata["inventory"] = inv
    pdata["daily_claims"] = daily_claims

    # Salva
    try:
        await player_manager.save_player_data(user_id, pdata)
    except Exception as e:
        logger.error(f"Erro ao salvar claim diário: {e}")
        try:
            await query.edit_message_text("❌ Erro ao salvar no banco. Tente novamente.")
        except Exception:
            pass
        return

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar aos Eventos", callback_data="back_to_event_hub")],
        [InlineKeyboardButton("🏰 Voltar ao Reino", callback_data="show_kingdom_menu")],
    ])

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
    """Registra os handlers deste módulo."""
    # Menu de eventos (você já tinha estes)
    application.add_handler(CallbackQueryHandler(show_active_events, pattern=r"^evt_hub_principal$"))
    application.add_handler(CallbackQueryHandler(show_active_events, pattern=r"^back_to_event_hub$"))

    # ✅ Compatibilidade: em outros menus você usa este callback
    application.add_handler(CallbackQueryHandler(show_active_events, pattern=r"^abrir_hub_eventos_v2$"))

    # ✅ Claim diário
    application.add_handler(CallbackQueryHandler(evt_claim_daily_entries, pattern=r"^evt_claim_daily_entries$"))
