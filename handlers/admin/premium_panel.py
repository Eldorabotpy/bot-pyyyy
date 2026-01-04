# handlers/admin/premium_panel.py
# (VERSÃO FINAL: Importações Corrigidas para Core/Queries)

from __future__ import annotations
import logging
import html
from datetime import datetime, timezone, timedelta 
from typing import Optional, Union
from bson import ObjectId

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)
from telegram.error import BadRequest

# --- IMPORTS CORRIGIDOS (Aponta para o sistema novo) ---
from modules.player.core import get_player_data, save_player_data, clear_player_cache
from modules.player.queries import find_player_by_name
from modules.game_data.premium import PREMIUM_TIERS
from handlers.admin.utils import ensure_admin, parse_hybrid_id

# Tenta importar conexão direta para atualizar a coleção 'users' (Auth)
try:
    from modules.player.core import users_collection
except Exception:
    users_collection = None

logger = logging.getLogger(__name__)

# ---- States da conversa ----
(ASK_NAME,) = range(1)

# ==============================================================================
# HELPER DE DATA
# ==============================================================================
def _parse_smart_date(value) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    
    dt = None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try: dt = datetime.fromisoformat(value)
        except: return datetime.now(timezone.utc)
    
    if dt and dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
        
    return dt

# ==============================================================================
# KEYBOARD
# ==============================================================================
def _get_premium_keyboard():
    return [
        [
            InlineKeyboardButton("👑 Setar: PREMIUM", callback_data="prem_tier:premium:0"),
            InlineKeyboardButton("🌟 Setar: VIP", callback_data="prem_tier:vip:0"),
            InlineKeyboardButton("🔱 Setar: LENDA", callback_data="prem_tier:lenda:0")
        ],
        [
            InlineKeyboardButton("📅 +1 Dia", callback_data="prem_add:1"),
            InlineKeyboardButton("📅 +7 Dias", callback_data="prem_add:7"),
            InlineKeyboardButton("📅 +15 Dias", callback_data="prem_add:15"),
            InlineKeyboardButton("📅 +30 Dias", callback_data="prem_add:30")
        ],
        [
            InlineKeyboardButton("📅 -1 Dia", callback_data="prem_add:-1"),
            InlineKeyboardButton("📅 -7 Dias", callback_data="prem_add:-7")
        ],
        [
            InlineKeyboardButton("🗑️ Remover VIP (Free)", callback_data="prem_clear"),
            InlineKeyboardButton("🔍 Trocar Usuário", callback_data="prem_change_user")
        ],
        [InlineKeyboardButton("❌ Fechar", callback_data="prem_close")]
    ]

# ==============================================================================
# HELPERS LOCAIS
# ==============================================================================

async def _smart_find_player(text: str) -> tuple[Optional[Union[int, str, ObjectId]], Optional[dict]]:
    text = text.strip()
    uid_candidate = parse_hybrid_id(text)
    
    # 1. Tenta por ID
    if uid_candidate:
        pdata = await get_player_data(uid_candidate)
        if pdata: return uid_candidate, pdata

    # 2. Tenta por Nome (Usando QUERIES novo)
    found = await find_player_by_name(text)
    if found: return found[0], found[1]
    
    return None, None

def _format_date(val) -> str:
    if not val: return "Nunca"
    dt = _parse_smart_date(val)
    return dt.strftime("%d/%m/%Y %H:%M")

def _get_user_info_text(pdata: dict, uid) -> str:
    raw_name = pdata.get("character_name", "Desconhecido")
    name = html.escape(str(raw_name))
    
    tier = pdata.get("premium_tier", "free")
    expires_val = pdata.get("premium_expires_at")
    
    status_extra = ""
    is_expired = False
    
    if expires_val:
        dt = _parse_smart_date(expires_val)
        if dt < datetime.now(timezone.utc):
            status_extra = " (EXPIRADO / 0 DIAS)"
            is_expired = True
    elif tier != "free":
        status_extra = " (Permanente?)"

    tier_info = PREMIUM_TIERS.get(tier, {})
    tier_name = tier_info.get("display_name", tier.upper())
    
    instruction = "✅ Adicione dias abaixo para ativar." if (is_expired or tier != "free") else "Escolha uma ação:"

    txt = (
        f"👤 <b>Usuário:</b> {name}\n"
        f"🆔 <b>ID:</b> <code>{uid}</code>\n"
        f"------------------------------\n"
        f"💎 <b>Plano Definido:</b> {tier_name}{status_extra}\n"
        f"📅 <b>Vencimento:</b> {_format_date(expires_val)}\n"
        f"------------------------------\n"
        f"👇 <b>{instruction}</b>"
    )
    return txt

# ==============================================================================
# SALVAMENTO
# ==============================================================================
async def _save_premium_changes(uid, pdata, tier, expires_dt):
    if expires_dt and expires_dt.tzinfo is None:
        expires_dt = expires_dt.replace(tzinfo=timezone.utc)

    # JSON String para cache/banco
    expires_str = expires_dt.isoformat() if expires_dt else None
    
    pdata['premium_tier'] = tier
    pdata['premium_expires_at'] = expires_str
    
    # Salva usando CORE (híbrido)
    await save_player_data(uid, pdata)
    
    try: await clear_player_cache(uid)
    except: pass

    # Sincroniza com Auth (Mongo Users) diretamente
    if users_collection is not None:
        try:
            query = None
            if isinstance(uid, str) and ObjectId.is_valid(uid):
                query = {"_id": ObjectId(uid)}
            elif isinstance(uid, ObjectId):
                query = {"_id": uid}
            elif isinstance(uid, int):
                query = {"telegram_id_owner": uid}
                
            if query:
                await asyncio_wrap(users_collection.update_one, query, {"$set": {
                    "premium_tier": tier,
                    "premium_expires_at": expires_dt 
                }})
        except Exception as e:
            logger.error(f"Erro sync premium: {e}")

import asyncio
async def asyncio_wrap(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)

# ==============================================================================
# AÇÕES DO MENU
# ==============================================================================

async def _entry_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.pop('prem_target_id', None)
    await query.edit_message_text(
        "💎 <b>Painel Premium/VIP</b>\n\nEnvie o <b>ID</b> ou <b>Nome do Personagem</b>:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancelar", callback_data="prem_close")]])
    )
    return ASK_NAME

async def _receive_name_or_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    uid, pdata = await _smart_find_player(text)
    
    if not pdata:
        await update.message.reply_text("❌ Jogador não encontrado.")
        return ASK_NAME
    
    context.user_data['prem_target_id'] = uid
    await update.message.reply_text(
        _get_user_info_text(pdata, uid),
        reply_markup=InlineKeyboardMarkup(_get_premium_keyboard()),
        parse_mode="HTML"
    )
    return ASK_NAME

async def _refresh_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = context.user_data.get('prem_target_id')
    if not uid: return
    pdata = await get_player_data(uid)
    try:
        await update.callback_query.edit_message_text(
            _get_user_info_text(pdata, uid),
            reply_markup=InlineKeyboardMarkup(_get_premium_keyboard()),
            parse_mode="HTML"
        )
    except BadRequest: pass

async def _action_set_tier(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    uid = context.user_data.get('prem_target_id')
    pdata = await get_player_data(uid)
    if not pdata: return ASK_NAME
    
    parts = query.data.split(":")
    new_tier = parts[1]
    new_expire = datetime.now(timezone.utc)
    
    await _save_premium_changes(uid, pdata, new_tier, new_expire)
    await query.answer(f"✅ Tier {new_tier.upper()} definido! Adicione dias.", show_alert=True)
    await _refresh_menu(update, context)
    return ASK_NAME

async def _action_add_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    uid = context.user_data.get('prem_target_id')
    pdata = await get_player_data(uid)
    if not pdata: 
        await query.answer()
        return ASK_NAME
    
    try:
        days_to_add = int(query.data.split(":")[1])
    except: return ASK_NAME

    current_tier = pdata.get("premium_tier", "free")
    expires_val = pdata.get("premium_expires_at")
    
    if current_tier == "free":
        await query.answer("⚠️ Defina um plano antes de adicionar dias!", show_alert=True)
        return ASK_NAME
        
    try:
        current_dt = _parse_smart_date(expires_val)
        now = datetime.now(timezone.utc)
        
        if days_to_add > 0:
            base_date = now if current_dt < now else current_dt
        else:
            base_date = current_dt
            
        new_expire = base_date + timedelta(days=days_to_add)
        await _save_premium_changes(uid, pdata, current_tier, new_expire)
        
        op = "+" if days_to_add > 0 else ""
        await query.answer(f"✅ Atualizado: {op}{days_to_add} dias.")
    except Exception as e:
        logger.error(f"Erro math premium: {e}")
        await query.answer("❌ Erro de data.", show_alert=True)
        
    await _refresh_menu(update, context)
    return ASK_NAME

async def _action_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    uid = context.user_data.get('prem_target_id')
    pdata = await get_player_data(uid)
    
    await _save_premium_changes(uid, pdata, "free", None)
    await query.answer("🗑️ Removido.", show_alert=True)
    await _refresh_menu(update, context)
    return ASK_NAME

async def _action_change_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.pop('prem_target_id', None)
    await query.edit_message_text(
        "🔎 <b>Trocar Usuário</b>\n\nEnvie o novo ID ou Nome:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancelar", callback_data="prem_close")]])
    )
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
    await update.message.reply_text("Cancelado.")
    context.user_data.clear()
    return ConversationHandler.END

premium_panel_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(_entry_from_callback, pattern=r'^admin_premium$')],
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
        CommandHandler('cancel', _cmd_cancel),
        CallbackQueryHandler(_action_close, pattern=r"^prem_close$")
    ],
    per_message=False
)