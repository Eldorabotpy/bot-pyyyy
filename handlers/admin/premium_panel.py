# handlers/admin/premium_panel.py

from __future__ import annotations
import os
import logging
# --- IMPORTS CORRIGIDOS DE TEMPO ---
from datetime import datetime, timezone, timedelta 
from typing import Tuple, Optional

# --- IMPORT PARA TRATAR O ERRO 400 ---
from telegram.error import BadRequest 
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)
from modules import player_manager, game_data
from handlers.admin.utils import ensure_admin
from modules.player.premium import PremiumManager

logger = logging.getLogger(__name__)

# ---- States da conversa ----
(ASK_NAME,) = range(1)
ADMIN_ID = int(os.getenv("ADMIN_ID", "0")) # Previne erro se .env falhar

# ---------------------------------------------------------
# Utilidades
# ---------------------------------------------------------
def _fmt_date(iso: Optional[str]) -> str:
    if not iso: return "Permanente"
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    except Exception: return iso

def _get_user_target(context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    return context.user_data.get("premium_target_uid")

def _set_user_target(context: ContextTypes.DEFAULT_TYPE, uid: int, name: str) -> None:
    context.user_data["premium_target_uid"] = int(uid)
    context.user_data["premium_target_name"] = name

def _panel_text(user_id: int, pdata: dict) -> str:
    name = pdata.get("character_name") or f"Jogador {user_id}"
    
    # Lê direto do dicionário para garantir que mostre o que está no banco
    tier = pdata.get("premium_tier")
    exp_iso = pdata.get("premium_expiration")
    
    tier_disp = game_data.PREMIUM_TIERS.get(tier, {}).get("display_name", "Free") if tier else "Free"
    exp_disp = _fmt_date(exp_iso)

    return (
        "🔥 <b>Painel Premium</b>\n\n"
        f"<b>Usuário:</b> {name} <code>({user_id})</code>\n"
        f"<b>Tier Atual:</b> {tier_disp}\n"
        f"<b>Expira em:</b> {exp_disp}\n\n"
        "Selecione uma ação:"
    )

def _panel_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("🆓 Free", callback_data="prem_tier:free"),
            InlineKeyboardButton("⭐ Premium", callback_data="prem_tier:premium"),
            InlineKeyboardButton("💎 VIP", callback_data="prem_tier:vip"),
            InlineKeyboardButton("👑 Lenda", callback_data="prem_tier:lenda"),
        ],
        [
            InlineKeyboardButton("➕ 1 Dia", callback_data="prem_add:1"),
            InlineKeyboardButton("➕ 7 Dias", callback_data="prem_add:7"),
            InlineKeyboardButton("➕ 30 Dias", callback_data="prem_add:30"),
        ],
        [
             InlineKeyboardButton("🚫 Remover Premium", callback_data="prem_clear"),
        ],
        [
            InlineKeyboardButton("🔎 Trocar Usuário", callback_data="prem_change_user"),
            InlineKeyboardButton("❌ Fechar Painel", callback_data="prem_close"),
        ],
    ]
    return InlineKeyboardMarkup(rows)

# ---------------------------------------------------------
# Entrada e Gestão da Conversa
# ---------------------------------------------------------
async def _entry_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update): return ConversationHandler.END
    query = update.callback_query
    try: await query.answer()
    except: pass

    prompt = (
        "🔥 <b>Painel Premium</b>\n\n"
        "Envie o <b>User ID</b> ou o <b>nome exato do personagem</b>.\n"
        "Use /cancelar para sair."
    )
    keyboard = [[InlineKeyboardButton("❌ Fechar", callback_data="prem_close")]]
    
    try:
        await query.edit_message_text(prompt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    except BadRequest:
        if query.message:
             await context.bot.send_message(chat_id=query.message.chat.id, text=prompt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    context.user_data.pop("premium_target_uid", None)
    context.user_data.pop("premium_target_name", None)
    return ASK_NAME

async def _receive_name_or_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update): return ConversationHandler.END

    target_input = (update.message.text or "").strip()
    user_id, pdata = None, None

    try:
        user_id_int = int(target_input)
        pdata_found = await player_manager.get_player_data(user_id_int)
        if pdata_found:
            user_id = user_id_int
            pdata = pdata_found
    except ValueError:
        found_by_name = await player_manager.find_player_by_name(target_input)
        if found_by_name:
            user_id, pdata = found_by_name

    if not pdata:
        await update.message.reply_text(
            "❌ Jogador não encontrado. Tente novamente com o <b>User ID</b> ou o <b>nome exato</b>.\n"
            "Use /cancelar para sair.", parse_mode="HTML"
        )
        return ASK_NAME

    player_name = pdata.get("character_name", f"ID: {user_id}")
    _set_user_target(context, user_id, player_name)

    text = _panel_text(user_id, pdata)
    await update.message.reply_text(text, reply_markup=_panel_keyboard(), parse_mode="HTML")

    return ASK_NAME

# ---------------------------------------------------------
# Ações do painel (Callbacks)
# ---------------------------------------------------------

async def _safe_edit(query, text, keyboard):
    """Tenta editar a mensagem ignorando erro de 'não modificado'."""
    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
    except BadRequest as e:
        if "not modified" in str(e) or "Message is not modified" in str(e):
            pass 
        else:
            logger.error(f"Erro no _safe_edit: {e}")
            # Não damos raise para não quebrar o fluxo, apenas logamos
    except Exception as e:
        logger.error(f"Erro genérico ao editar mensagem: {e}")

async def _action_set_tier(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update): return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    target_uid = _get_user_target(context)
    if not target_uid:
        await query.answer("Erro: Alvo perdido.", show_alert=True)
        return ASK_NAME

    new_tier = (query.data or "prem_tier:free").split(":", 1)[1]

    try:
        pdata = await player_manager.get_player_data(target_uid)
        if not pdata: raise ValueError("Dados não encontrados.")

        # Define direto
        pdata["premium_tier"] = new_tier
        # Se virou Free, remove a data. Se virou outro, mantem a data (ou deixa permanente se não tiver)
        if new_tier == "free":
            pdata["premium_expiration"] = None
        
        await player_manager.save_player_data(target_uid, pdata)

        updated_pdata = await player_manager.get_player_data(target_uid)
        text = _panel_text(target_uid, updated_pdata)
        
        await _safe_edit(query, text, _panel_keyboard())

    except Exception as e:
        logger.error(f"Erro set tier: {e}")
        await query.answer(f"❌ Erro: {e}", show_alert=True)

    return ASK_NAME

async def _action_add_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Força bruta: Calcula a data manualmente e insere no dicionário do jogador.
    Resolve o problema de não adicionar dias em contas Permanentes ou bugadas.
    """
    if not await ensure_admin(update): return ConversationHandler.END
    query = update.callback_query
    target_uid = _get_user_target(context)
    
    if not target_uid:
        await query.answer("Erro: Alvo perdido.", show_alert=True)
        return ASK_NAME

    try:
        days_str = (query.data or "prem_add:1").split(":", 1)[1]
        days = int(days_str)
    except:
        return ASK_NAME

    await query.answer(f"Adicionando +{days} dias...")

    try:
        # 1. Pega os dados
        pdata = await player_manager.get_player_data(target_uid)
        if not pdata: raise ValueError("Jogador não encontrado.")

        # 2. Lógica Manual de Data
        now = datetime.now(timezone.utc)
        current_exp_iso = pdata.get("premium_expiration")
        
        new_date = None

        if not current_exp_iso:
            # Se é Permanente (None) ou Free (None), começa de AGORA + Dias
            new_date = now + timedelta(days=days)
        else:
            try:
                current_date = datetime.fromisoformat(current_exp_iso)
                if current_date.tzinfo is None: current_date = current_date.replace(tzinfo=timezone.utc)
                
                if current_date > now:
                    # Soma na data existente
                    new_date = current_date + timedelta(days=days)
                else:
                    # Se já venceu, começa de agora
                    new_date = now + timedelta(days=days)
            except Exception:
                new_date = now + timedelta(days=days)

        # 3. Grava e Garante Tier
        pdata["premium_expiration"] = new_date.isoformat()
        
        tier_atual = pdata.get("premium_tier")
        if not tier_atual or tier_atual == "free":
             pdata["premium_tier"] = "premium"

        # 4. Salva
        await player_manager.save_player_data(target_uid, pdata)

        # 5. Atualiza Tela
        updated_pdata = await player_manager.get_player_data(target_uid)
        text = _panel_text(target_uid, updated_pdata)
        
        await _safe_edit(query, text, _panel_keyboard())

    except Exception as e:
        logger.error(f"Erro add days força bruta: {e}", exc_info=True)
        await query.answer(f"❌ Erro: {e}", show_alert=True)

    return ASK_NAME

async def _action_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update): return ConversationHandler.END
    query = update.callback_query
    target_uid = _get_user_target(context)
    if not target_uid:
        await query.answer("Erro: Alvo perdido.", show_alert=True)
        return ASK_NAME

    await query.answer("Removendo Premium...")

    try:
        pdata = await player_manager.get_player_data(target_uid)
        if not pdata: raise ValueError("Dados não encontrados.")

        pdata["premium_tier"] = "free"
        pdata["premium_expiration"] = None
        
        await player_manager.save_player_data(target_uid, pdata)

        updated_pdata = await player_manager.get_player_data(target_uid)
        text = _panel_text(target_uid, updated_pdata)
        
        await _safe_edit(query, text, _panel_keyboard())

    except Exception as e:
        logger.error(f"Erro clear: {e}")
        await query.answer(f"❌ Erro: {e}", show_alert=True)

    return ASK_NAME

async def _action_change_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update): return ConversationHandler.END
    return await _entry_from_callback(update, context)

async def _action_close(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    try: await query.answer()
    except: pass
    try: await query.delete_message()
    except: pass
    context.user_data.clear()
    return ConversationHandler.END

async def _cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operação cancelada.")
    context.user_data.clear()
    return ConversationHandler.END

async def _premium_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): return
    if not context.args:
        await update.message.reply_text("Uso: /premium_user <user_id>")
        return
    try: uid = int(context.args[0])
    except: return

    pdata = await player_manager.get_player_data(uid)
    if not pdata:
        await update.message.reply_text("Não encontrado.")
        return

    player_name = pdata.get("character_name", f"ID: {uid}")
    _set_user_target(context, uid, player_name)
    await update.message.reply_text(_panel_text(uid, pdata), parse_mode="HTML", reply_markup=_panel_keyboard())

# ---------------------------------------------------------
# Exports
# ---------------------------------------------------------
premium_panel_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(_entry_from_callback, pattern=r'^admin_premium$'),
    ],
    states={
        ASK_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, _receive_name_or_id),
            CallbackQueryHandler(_action_set_tier, pattern=r"^prem_tier:(free|premium|vip|lenda)$"),
            CallbackQueryHandler(_action_add_days, pattern=r"^prem_add:(\d+)$"),
            CallbackQueryHandler(_action_clear, pattern=r"^prem_clear$"),
            CallbackQueryHandler(_action_change_user, pattern=r"^prem_change_user$"),
            CallbackQueryHandler(_action_close, pattern=r"^prem_close$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancelar", _cmd_cancel),
        CallbackQueryHandler(_action_close, pattern=r"^prem_close$"),
    ],
    name="premium_panel_conv",
    persistent=False,
)

premium_command_handler = CommandHandler("premium_user", _premium_user_cmd, filters=filters.User(ADMIN_ID))
