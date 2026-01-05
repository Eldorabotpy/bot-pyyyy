# handlers/admin/premium_panel.py
# (VERSÃO FINAL: Sem Permanente + Layout Estrito + Sync Users)

from __future__ import annotations
import logging
import html
from datetime import datetime, timezone, timedelta 
from zoneinfo import ZoneInfo
from typing import Optional
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

# --- IMPORTS DO CORE ---
from modules.player.core import get_player_data, save_player_data, clear_player_cache, users_collection
from modules.player.queries import find_player_by_name
from modules.game_data.premium import PREMIUM_TIERS
from handlers.admin.utils import ensure_admin, parse_hybrid_id

# Usa a config ou fallback para SP
try:
    from config import JOB_TIMEZONE
except ImportError:
    JOB_TIMEZONE = "America/Sao_Paulo"

logger = logging.getLogger(__name__)

(ASK_NAME,) = range(1)

# ==============================================================================
# HELPER DE DATA
# ==============================================================================
def _parse_smart_date(value) -> datetime:
    """Converte string do banco para objeto datetime UTC."""
    if not value:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except:
        return datetime.now(timezone.utc)

def _format_date_br(iso_str: str, tier: str) -> str:
    """Mostra a data no horário BRT."""
    if tier == "free" or not iso_str:
        return "---"
        
    try:
        dt_utc = _parse_smart_date(iso_str)
        dt_br = dt_utc.astimezone(ZoneInfo(JOB_TIMEZONE))
        return dt_br.strftime("%d/%m/%Y %H:%M")
    except:
        return "Inválida"

# ==============================================================================
# SYNC BANCO (FORÇA ATUALIZAÇÃO DO PERFIL)
# ==============================================================================
async def _save_and_refresh(user_id, pdata):
    # 1. Salva no banco de jogo
    await save_player_data(user_id, pdata)
    
    # 2. Força update no banco de login (Users)
    if users_collection is not None:
        try:
            q = None
            if isinstance(user_id, ObjectId): q = {"_id": user_id}
            elif isinstance(user_id, int): q = {"$or": [{"_id": user_id}, {"telegram_id_owner": user_id}]}
            elif isinstance(user_id, str):
                if ObjectId.is_valid(user_id): q = {"_id": ObjectId(user_id)}
                elif user_id.isdigit(): q = {"telegram_id_owner": int(user_id)}
            
            if q:
                users_collection.update_one(q, {"$set": {
                    "premium_tier": pdata.get("premium_tier"),
                    "premium_expires_at": pdata.get("premium_expires_at")
                }})
        except Exception as e:
            logger.error(f"Erro sync users: {e}")

    # 3. Limpa Cache
    await clear_player_cache(user_id)

# ==============================================================================
# FLUXO DE PAINEL
# ==============================================================================

async def _entry_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    if context.user_data.get('prem_target_id'):
        target_id = context.user_data['prem_target_id']
        pdata = await get_player_data(target_id)
        if pdata:
            await _show_player_panel(update, context, pdata)
            return ASK_NAME

    await query.edit_message_text(
        "💎 <b>GERENCIADOR PREMIUM</b>\n\nEnvie o <b>Nome</b> ou <b>ID</b>:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancelar", callback_data="prem_close")]])
    )
    return ASK_NAME

async def _receive_name_or_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    txt = update.message.text.strip()
    target_id = parse_hybrid_id(txt)
    pdata = None
    
    if target_id:
        pdata = await get_player_data(target_id)
    if not pdata:
        found = await find_player_by_name(txt)
        if found:
            target_id, pdata = found

    if not pdata:
        await update.message.reply_text("❌ Jogador não encontrado.")
        return ASK_NAME

    context.user_data['prem_target_id'] = target_id
    await _show_player_panel(update, context, pdata)
    return ASK_NAME

async def _show_player_panel(update: Update, context: ContextTypes.DEFAULT_TYPE, pdata: dict):
    name = pdata.get("character_name", "Sem Nome")
    uid = pdata.get("user_id") or pdata.get("_id")
    
    tier = pdata.get("premium_tier", "free")
    expires = pdata.get("premium_expires_at")
    
    tier_display = PREMIUM_TIERS.get(tier, {}).get("display_name", tier.capitalize())
    if tier == "free": tier_display = "Comum (Free)"
    
    msg = (
        f"👤 <b>GERENCIAR PREMIUM</b>\n"
        f"jog: <b>{html.escape(name)}</b>\n"
        f"🆔 <code>{uid}</code>\n"
        "──────────────────\n"
        f"🎖️ <b>Plano:</b> {tier_display}\n"
        f"⏳ <b>Vence:</b> {_format_date_br(expires, tier)}\n"
        "──────────────────"
    )
    
    # --- SEU LAYOUT (SEM PERMANENTE) ---
    kb = [
        # Linha 1: Planos
        [
            InlineKeyboardButton("💎 Premium", callback_data="prem_tier:premium"),
            InlineKeyboardButton("🌟 VIP", callback_data="prem_tier:vip"),
            InlineKeyboardButton("👑 Lenda", callback_data="prem_tier:lenda"),
        ],
        # Linha 2: Adicionar Dias
        [
            InlineKeyboardButton("📅 +1 Dia", callback_data="prem_mod:1"),
            InlineKeyboardButton("📅 +7 Dias", callback_data="prem_mod:7"),
            InlineKeyboardButton("📅 +30 Dias", callback_data="prem_mod:30"),
        ],
        # Linha 3: Remover Dias
        [
            InlineKeyboardButton("📆 -1 Dia", callback_data="prem_mod:-1"),
            InlineKeyboardButton("📆 -7 Dias", callback_data="prem_mod:-7"),
        ],
        # Linha 4: Ações Finais
        [
            InlineKeyboardButton("🗑️ Remover Plano", callback_data="prem_clear"),
            InlineKeyboardButton("🎯 Trocar Alvo", callback_data="prem_change_user"),
        ],
        # Linha 5: Sair
        [InlineKeyboardButton("🔙 Sair", callback_data="prem_close")]
    ]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    else:
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

# ==============================================================================
# AÇÕES
# ==============================================================================

async def _action_set_tier(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Define APENAS o Tier. Se não tiver data, define 30 dias."""
    query = update.callback_query
    await query.answer()
    
    target_id = context.user_data.get('prem_target_id')
    new_tier = query.data.split(":")[1]
    
    pdata = await get_player_data(target_id)
    if pdata:
        pdata['premium_tier'] = new_tier
        
        # Se estava free ou sem data, obriga ter uma data (30 dias base)
        if not pdata.get("premium_expires_at"):
            now = datetime.now(timezone.utc)
            pdata['premium_expires_at'] = (now + timedelta(days=30)).isoformat()
        
        await _save_and_refresh(target_id, pdata)
        await _show_player_panel(update, context, pdata)
        
    return ASK_NAME

async def _action_mod_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Adiciona ou Remove dias da data atual."""
    query = update.callback_query
    
    target_id = context.user_data.get('prem_target_id')
    try:
        days_delta = int(query.data.split(":")[1])
    except:
        days_delta = 0
    
    pdata = await get_player_data(target_id)
    if pdata:
        current_str = pdata.get("premium_expires_at")
        
        # Se não tem data (None/Free), base é AGORA (UTC).
        if not current_str:
            base_date = datetime.now(timezone.utc)
        else:
            base_date = _parse_smart_date(current_str)
            
        # Calcula nova data
        new_date = base_date + timedelta(days=days_delta)
        
        # Salva em formato ISO UTC
        pdata['premium_expires_at'] = new_date.isoformat()
        
        # Se for free e adicionou dias, vira Premium automaticamente
        if pdata.get("premium_tier", "free") == "free" and days_delta > 0:
             pdata['premium_tier'] = "premium"

        await _save_and_refresh(target_id, pdata)
        
        action_txt = "adicionado(s)" if days_delta > 0 else "removido(s)"
        await query.answer(f"{abs(days_delta)} dia(s) {action_txt}.")
        await _show_player_panel(update, context, pdata)

    return ASK_NAME

async def _action_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    target_id = context.user_data.get('prem_target_id')
    pdata = await get_player_data(target_id)
    
    if pdata:
        pdata['premium_tier'] = "free"
        pdata['premium_expires_at'] = None
        
        await _save_and_refresh(target_id, pdata)
        await query.answer("Plano removido!")
        await _show_player_panel(update, context, pdata)
        
    return ASK_NAME

async def _action_change_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.pop('prem_target_id', None)
    
    await query.edit_message_text(
        "💎 <b>GERENCIADOR PREMIUM</b>\n\nEnvie o novo <b>Nome</b> ou <b>ID</b>:",
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
            CallbackQueryHandler(_action_mod_days, pattern=r"^prem_mod:"),
            CallbackQueryHandler(_action_clear, pattern=r"^prem_clear$"),
            CallbackQueryHandler(_action_change_user, pattern=r"^prem_change_user$"),
            CallbackQueryHandler(_action_close, pattern=r"^prem_close$"),
        ]
    },
    fallbacks=[CommandHandler('cancel', _cmd_cancel)],
    per_chat=True
)