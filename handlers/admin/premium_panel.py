# handlers/admin/premium_panel.py
# (FORMATO ORIGINAL MANTIDO - CORREÇÃO DE SINCRONIA USERS/PLAYERS APLICADA)

from __future__ import annotations
import os
import logging
from datetime import datetime, timezone, timedelta 
from typing import Tuple, Optional
from bson import ObjectId

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
from handlers.admin.utils import ensure_admin, parse_hybrid_id

# --- TENTA IMPORTAR A COLEÇÃO DE USERS PARA SINCRONIA ---
try:
    from modules.database import db
    users_col = db["users"]
except:
    users_col = None
# --------------------------------------------------------

logger = logging.getLogger(__name__)

# ---- States da conversa ----
(ASK_NAME,) = range(1)
ADMIN_ID = int(os.getenv("ADMIN_ID", "0")) 

# ==============================================================================
# FUNÇÃO AUXILIAR: SINCRONIA (Adicionada para corrigir o bug do site)
# ==============================================================================
def _sync_users_collection(user_id, tier: str, expires_at: Optional[str]):
    """Replica a alteração de Premium na coleção 'users'."""
    if users_col is None: return

    query = None
    if isinstance(user_id, int):
        query = {"telegram_id_owner": user_id}
    elif isinstance(user_id, ObjectId):
        query = {"_id": user_id}
    elif isinstance(user_id, str) and ObjectId.is_valid(user_id):
        query = {"_id": ObjectId(user_id)}
        
    if query:
        try:
            users_col.update_one(
                query, 
                {"$set": {"premium_tier": tier, "premium_expires_at": expires_at}}
            )
        except Exception as e:
            logger.error(f"Erro ao sincronizar premium com users: {e}")

# ---------------------------------------------------------
# Utilidades de Data
# ---------------------------------------------------------
def _fmt_date(iso: Optional[str]) -> str:
    if not iso: return "Nenhuma (Free)"
    
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        if dt < now:
            return "VENCIDO"
            
        remain = dt - now
        days = remain.days
        hours = remain.seconds // 3600
        return f"{dt.strftime('%d/%m/%Y')} ({days}d {hours}h)"
    except:
        return "Inválida"

# ---------------------------------------------------------
# Menu Principal do Painel
# ---------------------------------------------------------
async def _entry_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Acesso restrito.")
        return ConversationHandler.END

    await query.edit_message_text(
        "💎 **GERENCIAR PREMIUM**\n\n"
        "Digite o **ID Numérico**, **@Username** ou **Nome** do jogador:",
        parse_mode="Markdown"
    )
    return ASK_NAME

async def _receive_name_or_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    
    # Busca inteligente
    target_id = parse_hybrid_id(text)
    if not target_id:
        from modules.player.queries import find_player_by_name_norm
        found = await find_player_by_name_norm(text)
        if found:
            target_id = found[0]

    pdata = await player_manager.get_player_data(target_id)
    if not pdata:
        await update.message.reply_text("❌ Jogador não encontrado. Tente novamente ou /cancelar.")
        return ASK_NAME
    
    context.user_data["prem_target_id"] = target_id
    await _show_player_options(update, context, pdata)
    return ASK_NAME

async def _show_player_options(update: Update, context: ContextTypes.DEFAULT_TYPE, pdata: dict):
    target_id = context.user_data.get("prem_target_id")
    name = pdata.get("character_name", "Desconhecido")
    
    tier = pdata.get("premium_tier", "free")
    expires = pdata.get("premium_expires_at")
    
    txt = (
        f"👤 **Jogador:** {name}\n"
        f"🆔 **ID:** `{target_id}`\n"
        f"🌟 **Plano Atual:** {tier.upper()}\n"
        f"⏳ **Vencimento:** {_fmt_date(expires)}\n\n"
        "Selecione uma ação:"
    )
    
    kb = [
        [
            InlineKeyboardButton("🥇 PREMIUM", callback_data="prem_tier:gold"),
            InlineKeyboardButton("💎 VIP", callback_data="prem_tier:vip"),
            InlineKeyboardButton("🏆 LENDA", callback_data="prem_tier:lenda")
        ],
        [
            InlineKeyboardButton("+7 Dias", callback_data="prem_add:7"),
            InlineKeyboardButton("+15 Dias", callback_data="prem_add:15"),
            InlineKeyboardButton("+30 Dias", callback_data="prem_add:30")
        ],
         [
            InlineKeyboardButton("-1 Dia", callback_data="prem_add:-1"),
            InlineKeyboardButton("-7 Dias", callback_data="prem_add:-7"),
        ],
        [InlineKeyboardButton("❌ REMOVER VIP (Virar Free)", callback_data="prem_clear")],
        [InlineKeyboardButton("🔍 Outro Jogador", callback_data="prem_change_user")],
        [InlineKeyboardButton("🔙 Fechar", callback_data="prem_close")]
    ]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# ---------------------------------------------------------
# Ações (Agora com Sincronia de Users)
# ---------------------------------------------------------
async def _action_set_tier(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    target_id = context.user_data.get("prem_target_id")
    pdata = await player_manager.get_player_data(target_id)
    if not pdata:
        await query.edit_message_text("Erro: Jogador sumiu.")
        return ConversationHandler.END
        
    new_tier = query.data.split(":")[1]
    
    from modules.player.premium import PremiumManager
    pm = PremiumManager(pdata)
    
    # Se não tinha data, dá 30 dias ao definir tier
    if not pm.expiration_date:
        pm.add_days(30)
        
    pm.set_tier(new_tier)
    
    # 1. Salva no Jogo
    await player_manager.save_player_data(target_id, pdata)
    
    # 2. Sincroniza Login/Site
    _sync_users_collection(target_id, pdata.get("premium_tier"), pdata.get("premium_expires_at"))
    
    await _show_player_options(update, context, pdata)
    return ASK_NAME

async def _action_add_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    target_id = context.user_data.get("prem_target_id")
    pdata = await player_manager.get_player_data(target_id)
    days = int(query.data.split(":")[1])
    
    from modules.player.premium import PremiumManager
    pm = PremiumManager(pdata)
    
    # Se era free, vira Gold automaticamente
    if pm.tier == 'free' or not pm.tier:
        pm.set_tier('gold')
        
    pm.add_days(days)
    
    # 1. Salva no Jogo
    await player_manager.save_player_data(target_id, pdata)

    # 2. Sincroniza Login/Site
    _sync_users_collection(target_id, pdata.get("premium_tier"), pdata.get("premium_expires_at"))
    
    await _show_player_options(update, context, pdata)
    return ASK_NAME

async def _action_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("Vip removido!")
    
    target_id = context.user_data.get("prem_target_id")
    pdata = await player_manager.get_player_data(target_id)
    
    from modules.player.premium import PremiumManager
    pm = PremiumManager(pdata)
    pm.revoke() # Vira free
    
    # 1. Salva no Jogo
    await player_manager.save_player_data(target_id, pdata)

    # 2. Sincroniza Login/Site
    _sync_users_collection(target_id, "free", None)
    
    await _show_player_options(update, context, pdata)
    return ASK_NAME

async def _action_change_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Digite o **ID**, **@User** ou **Nome** do novo jogador:", parse_mode="Markdown")
    return ASK_NAME

async def _action_close(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    try: 
        await query.answer()
        await query.delete_message()
    except: pass
    context.user_data.clear()
    return ConversationHandler.END

async def _cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operação cancelada.")
    context.user_data.clear()
    return ConversationHandler.END

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
            CallbackQueryHandler(_action_set_tier, pattern=r"^prem_tier:"),
            CallbackQueryHandler(_action_add_days, pattern=r"^prem_add:"),
            CallbackQueryHandler(_action_clear, pattern=r"^prem_clear$"),
            CallbackQueryHandler(_action_change_user, pattern=r"^prem_change_user$"),
            CallbackQueryHandler(_action_close, pattern=r"^prem_close$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancelar", _cmd_cancel),
        CallbackQueryHandler(_action_close, pattern=r"^prem_close$"),
    ],
    per_chat=True
)