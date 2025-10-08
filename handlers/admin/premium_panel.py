# handlers/admin/premium_panel.py

from __future__ import annotations
import os
import logging
from datetime import datetime, timezone
from typing import Tuple, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)
from modules import player_manager
from handlers.admin.utils import ensure_admin

logger = logging.getLogger(__name__)

# ---- States da conversa ----
ASK_NAME = 1
ADMIN_ID = int(os.getenv("ADMIN_ID"))
# ---------------------------------------------------------
# Utilidades
# ---------------------------------------------------------
def _fmt_date(iso: Optional[str]) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # Mostra em DD/MM/YYYY HH:MM (UTC)
        return dt.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    except Exception:
        return iso

def _capfirst(s: Optional[str]) -> str:
    if not s:
        return "—"
    s = str(s)
    return s[0:1].upper() + s[1:]

def _get_user_target(context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    return context.user_data.get("premium_target_uid")

def _set_user_target(context: ContextTypes.DEFAULT_TYPE, uid: int) -> None:
    context.user_data["premium_target_uid"] = int(uid)

def _panel_text(user_id: int, pdata: dict) -> str:
    name = pdata.get("character_name") or f"Jogador {user_id}"
    tier = pdata.get("premium_tier")
    tier_disp = _capfirst(tier) if tier else "Free"

    exp = pdata.get("premium_expires_at")
    exp_disp = _fmt_date(exp) if tier else "—"

    return (
        "🔥 <b>Painel Premium</b>\n\n"
        f"<b>Usuário:</b> {name} <code>({user_id})</code>\n"
        f"<b>Tier:</b> {tier_disp}\n"
        f"<b>Expira:</b> {exp_disp}\n\n"
        "Escolha o <b>Tier</b> e/ou adicione dias:"
    )

def _panel_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("Free", callback_data="prem_tier:free"),
            InlineKeyboardButton("Premium", callback_data="prem_tier:premium"),
            InlineKeyboardButton("VIP", callback_data="prem_tier:vip"),
            InlineKeyboardButton("Lenda", callback_data="prem_tier:lenda"),
        ],
        [
            InlineKeyboardButton("+1d", callback_data="prem_add:1"),
            InlineKeyboardButton("+10d", callback_data="prem_add:10"),
            InlineKeyboardButton("+30d", callback_data="prem_add:30"),
        ],
        [
            InlineKeyboardButton("Remover Premium", callback_data="prem_clear"),
        ],
        [
            InlineKeyboardButton("🔎 Trocar Usuário", callback_data="prem_change_user"),
            InlineKeyboardButton("❌ Fechar", callback_data="prem_close"),
        ],
    ]
    return InlineKeyboardMarkup(rows)

# ---------------------------------------------------------
# Entrada do painel (via botão Premium do /admin)
# ---------------------------------------------------------
async def _entry_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update):
        return ConversationHandler.END

    q = update.callback_query
    await q.answer()

    # pede o nome do personagem
    prompt = (
        "🔥 <b>Painel Premium</b>\n\n"
        "Envie o <b>nome exato do personagem</b> para gerenciar o Premium.\n"
        "• Dica: sensível a acentos/maiúsculas.\n\n"
        "Ou toque em ❌ Fechar."
    )
    try:
        await q.edit_message_text(prompt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Fechar", callback_data="prem_close")]
        ]))
    except Exception:
        await context.bot.send_message(chat_id=q.message.chat.id, text=prompt, parse_mode="HTML")

    return ASK_NAME

# ---------------------------------------------------------
# Também exposto para o fallback do main (caso a Conversation não carregue)
# ---------------------------------------------------------
async def open_premium_panel_for_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # reutiliza a mesma entrada
    await _entry_from_callback(update, context)

# ---------------------------------------------------------
# Recebe o nome e mostra o painel
# ---------------------------------------------------------
async def _receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update):
        return ConversationHandler.END

    name = (update.message.text or "").strip()
    found: Optional[Tuple[int, dict]] = player_manager.find_player_by_name(name)

    if not found:
        await update.message.reply_text(
            "Não encontrei esse personagem. Tente novamente.\n"
            "Envie o <b>nome exato</b> (com acentos) ou /cancel.",
            parse_mode="HTML"
        )
        return ASK_NAME

    user_id, pdata = found
    _set_user_target(context, user_id)

    text = _panel_text(user_id, pdata)
    await update.message.reply_text(text, reply_markup=_panel_keyboard(), parse_mode="HTML")
    # Agora ficamos no "estado de painéis" controlado só por callbacks.
    return ASK_NAME

# ---------------------------------------------------------
# Ações do painel
# ---------------------------------------------------------
async def _action_set_tier(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ✅ 1. IMPORTAÇÃO LOCAL CORRETA
    # Importamos 'utcnow' diretamente do seu local de origem
    from modules.player.actions import utcnow

    if not await ensure_admin(update):
        return ConversationHandler.END

    q = update.callback_query
    await q.answer()
    target_uid = _get_user_target(context)
    if not target_uid:
        await q.answer("Escolha primeiro um usuário (Trocar Usuário).", show_alert=True)
        return ASK_NAME

    tier = (q.data or "prem_tier:free").split(":", 1)[1]
    pdata = player_manager.get_player_data(target_uid) or {}
    
    pdata["premium_tier"] = None if tier == "free" else tier
    
    if tier == "free":
        pdata["premium_expires_at"] = None
        
    max_e = player_manager.get_player_max_energy(pdata)
    if int(pdata.get("energy", 0)) < max_e:
        pdata["energy"] = max_e
        
    # ✅ 2. CHAMADA CORRIGIDA
    # Usamos a função 'utcnow' que acabámos de importar
    pdata['energy_last_ts'] = utcnow().isoformat()
    
    player_manager.save_player_data(target_uid, pdata)

    text = _panel_text(target_uid, pdata)
    try:
        await q.edit_message_text(text, parse_mode="HTML", reply_markup=_panel_keyboard())
    except Exception:
        await context.bot.send_message(chat_id=q.message.chat.id, text=text, parse_mode="HTML", reply_markup=_panel_keyboard())
        
    return ASK_NAME

async def _action_add_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update):
        return ConversationHandler.END

    q = update.callback_query
    await q.answer()
    target_uid = _get_user_target(context)
    if not target_uid:
        await q.answer("Escolha primeiro um usuário (Trocar Usuário).", show_alert=True)
        return ASK_NAME

    try:
        days = int((q.data or "prem_add:1").split(":", 1)[1])
    except Exception:
        days = 1

    pdata = player_manager.get_player_data(target_uid) or {}
    current_tier = pdata.get("premium_tier") or "premium"  # se não tiver, assume premium
    # Usa a API oficial para aplicar os dias (ela define expiração e perks).
    player_manager.grant_premium_status(target_uid, current_tier, days)
    pdata = player_manager.get_player_data(target_uid) or {}

    text = _panel_text(target_uid, pdata)
    try:
        await q.edit_message_text(text, parse_mode="HTML", reply_markup=_panel_keyboard())
    except Exception:
        await context.bot.send_message(chat_id=q.message.chat.id, text=text, parse_mode="HTML", reply_markup=_panel_keyboard())
    return ASK_NAME

async def _action_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update):
        return ConversationHandler.END

    q = update.callback_query
    await q.answer()
    target_uid = _get_user_target(context)
    if not target_uid:
        await q.answer("Escolha primeiro um usuário (Trocar Usuário).", show_alert=True)
        return ASK_NAME

    player_manager.grant_premium_status(target_uid, None, 0)
    pdata = player_manager.get_player_data(target_uid) or {}
    text = _panel_text(target_uid, pdata)
    try:
        await q.edit_message_text(text, parse_mode="HTML", reply_markup=_panel_keyboard())
    except Exception:
        await context.bot.send_message(chat_id=q.message.chat.id, text=text, parse_mode="HTML", reply_markup=_panel_keyboard())
    return ASK_NAME

async def _action_change_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update):
        return ConversationHandler.END
    q = update.callback_query
    await q.answer()
    prompt = (
        "🔎 Envie o <b>nome exato</b> do personagem que você quer gerenciar.\n"
        "Você pode /cancel para sair."
    )
    try:
        await q.edit_message_text(prompt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Fechar", callback_data="prem_close")]
        ]))
    except Exception:
        await context.bot.send_message(chat_id=q.message.chat.id, text=prompt, parse_mode="HTML")
    # limpa alvo atual
    context.user_data.pop("premium_target_uid", None)
    return ASK_NAME

async def _action_close(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    try:
        await q.delete_message()
    except Exception:
        pass
    return ConversationHandler.END

async def _cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        await update.message.reply_text("Painel Premium fechado.")
    except Exception:
        pass
    return ConversationHandler.END

# ---------------------------------------------------------
# /premium_user <user_id> (opcional – mantém compat se você quiser)
# ---------------------------------------------------------
async def _premium_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/premium_user <user_id> – atalho opcional para abrir direto no alvo."""
    if not await ensure_admin(update):
        return
    if not context.args:
        await update.message.reply_text("Uso: /premium_user <user_id>")
        return
    try:
        uid = int(context.args[0])
    except Exception:
        await update.message.reply_text("ID inválido.")
        return

    pdata = player_manager.get_player_data(uid)
    if not pdata:
        await update.message.reply_text("Jogador não encontrado.")
        return

    _set_user_target(context, uid)
    await update.message.reply_text(_panel_text(uid, pdata), parse_mode="HTML", reply_markup=_panel_keyboard())

# ---------------------------------------------------------
# Exports
# ---------------------------------------------------------
premium_panel_handler = ConversationHandler(
    entry_points=[
        # casa com o botão "👑 Premium" do painel admin
        CallbackQueryHandler(_entry_from_callback, pattern=r'^admin_premium$'),
        # compat opcional com outros botões/atalhos se existirem
        CallbackQueryHandler(_entry_from_callback, pattern=r'^(?:admin_)?premium(?:_panel|_menu)?$|^premium$'),
    ],
    states={
        ASK_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, _receive_name),
            CallbackQueryHandler(_action_set_tier, pattern=r"^prem_tier:(free|premium|vip|lenda)$"),
            CallbackQueryHandler(_action_add_days, pattern=r"^prem_add:(\d+)$"),
            CallbackQueryHandler(_action_clear, pattern=r"^prem_clear$"),
            CallbackQueryHandler(_action_change_user, pattern=r"^prem_change_user$"),
            CallbackQueryHandler(_action_close, pattern=r"^prem_close$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", _cmd_cancel),
    ],
    name="premium_panel_conv",
    persistent=False,
)

# Mantém o comando opcional
premium_command_handler = CommandHandler("premium_user", _premium_user_cmd)
