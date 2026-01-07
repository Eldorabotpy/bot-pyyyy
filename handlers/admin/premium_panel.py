# handlers/admin/premium_panel.py
# (VERSÃO CORRIGIDA: Tratamento de erro na busca de jogador e logs)

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

from modules.player.core import get_player_data, save_player_data, clear_player_cache, users_collection
from modules.player.queries import find_player_by_name
from modules.game_data.premium import PREMIUM_TIERS
from handlers.admin.utils import ensure_admin, parse_hybrid_id

# Configuração fixa de Timezone
JOB_TIMEZONE = "America/Sao_Paulo"

logger = logging.getLogger(__name__)
(ASK_NAME,) = range(1)

# ==============================================================================
# HELPER DE DATA (UTC -> BRT)
# ==============================================================================
def _parse_smart_date(value) -> datetime:
    """Lê do banco e garante UTC."""
    if not value: return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except: return datetime.now(timezone.utc)

def _format_date_br(iso_str: str, tier: str) -> str:
    """Mostra a data no horário BRT (São Paulo)."""
    if tier == "free" or not iso_str:
        return "---"
    try:
        dt_utc = _parse_smart_date(iso_str)
        # Converte UTC -> America/Sao_Paulo
        dt_br = dt_utc.astimezone(ZoneInfo(JOB_TIMEZONE))
        return dt_br.strftime("%d/%m/%Y %H:%M")
    except: return "Data Inválida"

# ==============================================================================
# SYNC BANCO
# ==============================================================================
async def _save_and_refresh(user_id, pdata):
    # Salva no sistema novo (users) se possível
    await save_player_data(user_id, pdata)
    
    # Update forçado direto no Mongo para garantir sincronia imediata
    if users_collection is not None:
        try:
            q = None
            if isinstance(user_id, ObjectId): q = {"_id": user_id}
            elif isinstance(user_id, str) and ObjectId.is_valid(user_id): q = {"_id": ObjectId(user_id)}
            # Fallback legado
            elif isinstance(user_id, int): q = {"telegram_id_owner": user_id}
            
            if q:
                users_collection.update_one(q, {"$set": {
                    "premium_tier": pdata.get("premium_tier"),
                    "premium_expires_at": pdata.get("premium_expires_at")
                }})
        except: pass
    await clear_player_cache(user_id)

# ==============================================================================
# PAINEL
# ==============================================================================
async def _entry_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    # Se já tem um alvo selecionado na memória, abre direto
    if context.user_data.get('prem_target_id'):
        target_id = context.user_data['prem_target_id']
        pdata = await get_player_data(target_id)
        if pdata:
            await _show_player_panel(update, context, pdata)
            return ASK_NAME
            
    await query.edit_message_text(
        "💎 <b>GERENCIADOR PREMIUM</b>\nEnvie o <b>Nome</b> ou <b>ID</b>:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancelar", callback_data="prem_close")]])
    )
    return ASK_NAME

async def _receive_name_or_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    txt = update.message.text.strip()
    
    # Feedback visual (opcional, ajuda a saber que o bot leu)
    status_msg = await update.message.reply_text("🔍 Procurando...", quote=True)
    
    try:
        target_id = parse_hybrid_id(txt)
        pdata = None
        
        # 1. Tenta buscar por ID direto
        if target_id: 
            pdata = await get_player_data(target_id)
        
        # 2. Se não achou ou não é ID, busca por nome
        if not pdata:
            # Proteção contra erros no find_player_by_name
            try:
                found = await find_player_by_name(txt)
                if found:
                    # Garante que o retorno é desempacotável
                    if isinstance(found, (list, tuple)) and len(found) >= 2:
                        target_id, pdata = found[0], found[1]
            except Exception as e_query:
                logger.error(f"Erro ao buscar jogador por nome '{txt}': {e_query}")
        
        # 3. Resultado
        if not pdata:
            await status_msg.edit_text("❌ Jogador não encontrado.\nTente novamente ou envie o ID.")
            return ASK_NAME
            
        context.user_data['prem_target_id'] = target_id
        
        # Apaga a mensagem de "Procurando..." e mostra o painel
        await status_msg.delete()
        await _show_player_panel(update, context, pdata)
        
    except Exception as e:
        logger.exception("Erro fatal no gerenciador premium:")
        await status_msg.edit_text(f"❌ Erro interno ao processar: {e}")
        
    return ASK_NAME

async def _show_player_panel(update: Update, context: ContextTypes.DEFAULT_TYPE, pdata: dict):
    name = pdata.get("character_name", "Sem Nome")
    uid = pdata.get("user_id") or pdata.get("_id")
    tier = pdata.get("premium_tier", "free")
    expires = pdata.get("premium_expires_at")
    
    tier_name = PREMIUM_TIERS.get(tier, {}).get("display_name", tier.capitalize())
    
    msg = (
        f"👤 <b>GERENCIAR PREMIUM</b>\n"
        f"jog: <b>{html.escape(name)}</b>\n"
        f"🆔 <code>{uid}</code>\n"
        "──────────────────\n"
        f"🎖️ <b>Plano:</b> {tier_name}\n"
        f"⏳ <b>Vence (BRT):</b> {_format_date_br(expires, tier)}\n"
        "──────────────────"
    )
    
    kb = [
        [
            InlineKeyboardButton("💎 Premium", callback_data="prem_tier:premium"),
            InlineKeyboardButton("🌟 VIP", callback_data="prem_tier:vip"),
            InlineKeyboardButton("👑 Lenda", callback_data="prem_tier:lenda"),
        ],
        [
            InlineKeyboardButton("📅 +1 Dia", callback_data="prem_mod:1"),
            InlineKeyboardButton("📅 +7 Dias", callback_data="prem_mod:7"),
            InlineKeyboardButton("📅 +30 Dias", callback_data="prem_mod:30"),
        ],
        [
            InlineKeyboardButton("📆 -1 Dia", callback_data="prem_mod:-1"),
            InlineKeyboardButton("📆 -7 Dias", callback_data="prem_mod:-7"),
        ],
        [
            InlineKeyboardButton("🗑️ Remover Plano", callback_data="prem_clear"),
            InlineKeyboardButton("🎯 Outro User", callback_data="prem_change_user"),
        ],
        [InlineKeyboardButton("🔙 Sair", callback_data="prem_close")]
    ]
    
    markup = InlineKeyboardMarkup(kb)
    
    # Se foi chamado via callback (botão) edita, se foi via texto (input nome) envia nova
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=markup, parse_mode="HTML")
    else:
        await update.message.reply_text(msg, reply_markup=markup, parse_mode="HTML")

# ==============================================================================
# AÇÕES
# ==============================================================================
async def _action_set_tier(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    target_id = context.user_data.get('prem_target_id')
    new_tier = query.data.split(":")[1]
    
    pdata = await get_player_data(target_id)
    if pdata:
        pdata['premium_tier'] = new_tier
        # Se não tem data, define +30 dias a partir de AGORA (UTC)
        if not pdata.get("premium_expires_at"):
            now = datetime.now(timezone.utc)
            pdata['premium_expires_at'] = (now + timedelta(days=30)).isoformat()
        
        await _save_and_refresh(target_id, pdata)
        await _show_player_panel(update, context, pdata)
    return ASK_NAME

async def _action_mod_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    target_id = context.user_data.get('prem_target_id')
    try: days_delta = int(query.data.split(":")[1])
    except: days_delta = 0
    
    pdata = await get_player_data(target_id)
    if pdata:
        current_str = pdata.get("premium_expires_at")
        now_utc = datetime.now(timezone.utc)
        
        # Se já tem data, usa ela. Se não, usa Agora.
        if current_str:
            base_date = _parse_smart_date(current_str)
            # Se a data antiga já passou (estava vencido), reinicia do Agora
            if base_date < now_utc:
                base_date = now_utc
        else:
            base_date = now_utc

        new_date = base_date + timedelta(days=days_delta)
        pdata['premium_expires_at'] = new_date.isoformat()
        
        # Se adicionou dias em conta Free, vira Premium básico
        if pdata.get("premium_tier", "free") == "free" and days_delta > 0:
             pdata['premium_tier'] = "premium"
             
        await _save_and_refresh(target_id, pdata)
        await query.answer(f"Tempo ajustado ({days_delta}d).")
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
        "💎 <b>GERENCIADOR PREMIUM</b>\nEnvie o novo <b>Nome</b> ou <b>ID</b>:",
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
