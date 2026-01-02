# handlers/admin/premium_panel.py
# (VERSÃO CORRIGIDA: Math de Datas Seguro + Proteção UTC)

from __future__ import annotations
import os
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

# Imports do Projeto
from modules import player_manager
from modules.game_data.premium import PREMIUM_TIERS
from handlers.admin.utils import ensure_admin, parse_hybrid_id

# Tenta importar conexão direta para atualizar a coleção 'users' (Auth)
try:
    from modules.player.core import players_collection
    db = players_collection.database
    users_col = db["users"]
except Exception:
    users_col = None

logger = logging.getLogger(__name__)

# ---- States da conversa ----
(ASK_NAME,) = range(1)

# ==============================================================================
# HELPER DE KEYBOARD
# ==============================================================================
def _get_premium_keyboard():
    return [
        [
            InlineKeyboardButton("👑 Setar: PREMIUM (30d)", callback_data="prem_tier:premium:30"),
            InlineKeyboardButton("🌟 Setar: VIP (30d)", callback_data="prem_tier:vip:30"),
            InlineKeyboardButton("🔱 Setar: LENDA (30d)", callback_data="prem_tier:lenda:30")
        ],
        [
            InlineKeyboardButton("📅 +1 Dia", callback_data="prem_add:1"),
            InlineKeyboardButton("📅 +7 Dias", callback_data="prem_add:7"),
            InlineKeyboardButton("📅 +15 Dias", callback_data="prem_add:15")
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
    if uid_candidate:
        pdata = await player_manager.get_player_data(uid_candidate)
        if pdata: return uid_candidate, pdata

    found = await player_manager.find_player_by_name(text)
    if found: return found[0], found[1]
    return None, None

def _format_date(iso_str: str) -> str:
    if not iso_str: return "Nunca"
    try:
        dt = datetime.fromisoformat(str(iso_str))
        # Ajusta para timezone local se possível, ou exibe UTC
        return dt.strftime("%d/%m/%Y %H:%M")
    except: return "Inválido"

def _get_user_info_text(pdata: dict, uid) -> str:
    raw_name = pdata.get("character_name", "Desconhecido")
    name = html.escape(str(raw_name))
    
    tier = pdata.get("premium_tier", "free")
    expires = pdata.get("premium_expires_at")
    
    # Verifica se já expirou visualmente
    status_extra = ""
    if expires:
        try:
            dt = datetime.fromisoformat(expires)
            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
            if dt < datetime.now(timezone.utc):
                status_extra = " (EXPIRADO)"
        except: pass

    tier_info = PREMIUM_TIERS.get(tier, {})
    tier_name = tier_info.get("display_name", tier.upper())
    
    txt = (
        f"👤 <b>Usuário:</b> {name}\n"
        f"🆔 <b>ID:</b> <code>{uid}</code>\n"
        f"------------------------------\n"
        f"💎 <b>Plano Atual:</b> {tier_name}{status_extra}\n"
        f"📅 <b>Expira em:</b> {_format_date(expires)}\n"
        f"------------------------------\n"
        f"Escolha uma ação:"
    )
    return txt

# ==============================================================================
# FUNÇÃO CRÍTICA DE SALVAMENTO (Sincronia Robusta)
# ==============================================================================
async def _save_premium_changes(uid, pdata, tier, expires_dt):
    """
    Salva no player_manager, limpa cache e sincroniza coleção 'users'.
    """
    # Garante UTC
    if expires_dt and expires_dt.tzinfo is None:
        expires_dt = expires_dt.replace(tzinfo=timezone.utc)

    expires_str = expires_dt.isoformat() if expires_dt else None
    
    # 1. Atualiza objeto principal e Salva
    pdata['premium_tier'] = tier
    pdata['premium_expires_at'] = expires_str
    
    await player_manager.save_player_data(uid, pdata)
    
    # 2. Limpa o Cache
    try:
        await player_manager.clear_player_cache(uid)
    except Exception as e:
        logger.error(f"Erro ao limpar cache premium: {e}")

    # 3. Sincroniza com Auth (users collection)
    if users_col is not None:
        try:
            query = None
            if isinstance(uid, str) and ObjectId.is_valid(uid):
                query = {"_id": ObjectId(uid)}
            elif isinstance(uid, ObjectId):
                query = {"_id": uid}
            elif isinstance(uid, int):
                query = {"telegram_id_owner": uid}
                
            if query:
                # Importante: Mongo prefere datetime objects, não strings ISO
                update_payload = {
                    "premium_tier": tier,
                    "premium_expires_at": expires_dt 
                }
                users_col.update_one(query, {"$set": update_payload})
                logger.info(f"Premium sincronizado (User DB) para: {uid}")
        except Exception as e:
            logger.error(f"Erro ao sincronizar premium no users para {uid}: {e}")

# ==============================================================================
# AÇÕES E CALLBACKS
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
    pdata = await player_manager.get_player_data(uid)
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
    pdata = await player_manager.get_player_data(uid)
    if not pdata: return ASK_NAME
    
    parts = query.data.split(":")
    new_tier = parts[1]
    days = int(parts[2])
    
    new_expire = datetime.now(timezone.utc) + timedelta(days=days)
    
    await _save_premium_changes(uid, pdata, new_tier, new_expire)
    await query.answer(f"✅ Definido {new_tier.upper()} por {days} dias!", show_alert=False)
    await _refresh_menu(update, context)
    return ASK_NAME

async def _action_add_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    uid = context.user_data.get('prem_target_id')
    pdata = await player_manager.get_player_data(uid)
    if not pdata: 
        await query.answer()
        return ASK_NAME
    
    try:
        days_to_add = int(query.data.split(":")[1])
    except: return ASK_NAME

    current_tier = pdata.get("premium_tier", "free")
    current_exp_str = pdata.get("premium_expires_at")
    
    if current_tier == "free" or not current_exp_str:
        await query.answer("⚠️ Usuário Free. Defina um plano primeiro!", show_alert=True)
        return ASK_NAME
        
    try:
        # 1. Parsing Seguro com UTC
        current_dt = datetime.fromisoformat(current_exp_str)
        if current_dt.tzinfo is None:
            current_dt = current_dt.replace(tzinfo=timezone.utc)
            
        now = datetime.now(timezone.utc)
        
        # 2. Lógica de Adição/Remoção
        # Se estiver adicionando dias e o plano já venceu, começa de AGORA.
        # Se estiver removendo ou o plano está ativo, usa a data atual do plano.
        if days_to_add > 0 and current_dt < now:
            base_date = now
        else:
            base_date = current_dt
            
        new_expire = base_date + timedelta(days=days_to_add)
        
        # 3. Proteção contra datas passadas (Remoção excessiva)
        # Se a nova data for no passado, o plano expira tecnicamente.
        # Não mudamos o Tier para "free" automaticamente aqui para permitir "reverter" se foi erro,
        # mas o jogo vai considerar expirado.
        
        await _save_premium_changes(uid, pdata, current_tier, new_expire)
        
        op = "+" if days_to_add > 0 else ""
        await query.answer(f"✅ Data atualizada: {op}{days_to_add} dias.")
        
    except Exception as e:
        logger.error(f"Erro math data premium: {e}")
        await query.answer("❌ Erro ao calcular data (formato inválido).")
        
    await _refresh_menu(update, context)
    return ASK_NAME

async def _action_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    uid = context.user_data.get('prem_target_id')
    pdata = await player_manager.get_player_data(uid)
    
    await _save_premium_changes(uid, pdata, "free", None)
    await query.answer("🗑️ Premium removido (Setado para Free).")
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
    
    # Tenta reabrir menu principal se possível
    from handlers.admin_handler import _send_admin_menu
    try: await _send_admin_menu(update.effective_chat.id, context)
    except: pass
    return ConversationHandler.END

async def _cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operação cancelada.")
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