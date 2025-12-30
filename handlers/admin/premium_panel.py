# handlers/admin/premium_panel.py
# (VERSÃO BLINDADA: Corrige busca de ID Numérico vs Texto)

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
from handlers.admin.utils import ensure_admin 
# Removemos parse_hybrid_id externo para usar o local mais seguro

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
# FUNÇÃO LOCAL: PARSER INTELIGENTE DE ID
# ==============================================================================
async def _smart_identify_target(text: str) -> Optional[int | str]:
    """
    Identifica se o input é ID Numérico (Old), ObjectId (New), 
    Username ou Nome, e retorna o ID correto pronto para uso.
    """
    text = text.strip()
    
    # 1. É um ID Numérico? (Conta Antiga)
    if text.isdigit():
        return int(text)  # <--- CRUCIAL: Retorna como INT
        
    # 2. É um ObjectId? (Conta Nova)
    if ObjectId.is_valid(text):
        return str(text)  # Retorna como STRING
        
    # 3. É um Username (@Usuario)?
    if text.startswith("@"):
        from modules.player.queries import find_by_username
        pdata = await find_by_username(text)
        if pdata:
            return pdata.get("user_id") or pdata.get("_id")
            
    # 4. Busca por Nome do Personagem (Tenta os dois bancos)
    from modules.player.queries import find_player_by_name_norm
    found = await find_player_by_name_norm(text)
    if found:
        return found[0] # Retorna o ID encontrado (int ou str)
        
    return None

# ==============================================================================
# FUNÇÃO AUXILIAR: SINCRONIA
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
    
    if not await ensure_admin(update):
        return ConversationHandler.END

    await query.edit_message_text(
        "💎 **GERENCIAR PREMIUM**\n\n"
        "Digite o **ID Numérico**, **@Username** ou **Nome** do jogador:",
        parse_mode="Markdown"
    )
    return ASK_NAME

async def _receive_name_or_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    
    # --- USA O NOVO PARSER BLINDADO ---
    target_id = await _smart_identify_target(text)
    # ----------------------------------

    if not target_id:
        await update.message.reply_text(f"❌ Jogador '{text}' não encontrado em nenhum banco de dados.")
        return ASK_NAME
    
    pdata = await player_manager.get_player_data(target_id)
    if not pdata:
        # Tenta forçar int se for string numérica (última tentativa)
        if isinstance(target_id, str) and target_id.isdigit():
             pdata = await player_manager.get_player_data(int(target_id))
             if pdata: target_id = int(target_id)

    if not pdata:
        await update.message.reply_text(f"❌ ID identificado ({target_id}), mas os dados estão corrompidos ou vazios.")
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
            InlineKeyboardButton("🥇 GOLD", callback_data="prem_tier:gold"),
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
# Ações
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
    
    # Se não tiver data de expiração, adiciona 30 dias por padrão
    if not pm.expiration_date:
        pm.grant_days(new_tier, 30, force=True)
    else:
        # Apenas muda o tier mantendo a data
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
    
    # Determina qual tier usar para a renovação
    current_tier = pm.tier
    if not current_tier or current_tier == 'free':
        current_tier = 'gold' # Default se for free e tentar adicionar dias
        
    # CORREÇÃO: Usa grant_days em vez de add_days
    pm.grant_days(current_tier, days)
    
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