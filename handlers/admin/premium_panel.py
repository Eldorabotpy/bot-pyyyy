# handlers/admin/premium_panel.py
# (VERSÃO FINAL: COM BOTÕES DE REMOVER DIAS E FIX DE 'PERMANENTE')

from __future__ import annotations
import os
import logging
from datetime import datetime, timezone, timedelta 
from typing import Tuple, Optional

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

logger = logging.getLogger(__name__)

# ---- States da conversa ----
(ASK_NAME,) = range(1)
ADMIN_ID = int(os.getenv("ADMIN_ID", "0")) 

# ---------------------------------------------------------
# Utilidades
# ---------------------------------------------------------
def _fmt_date(iso: Optional[str]) -> str:
    # SE NÃO TIVER DATA, É FREE / SEM ASSINATURA (CORREÇÃO DE 'PERMANENTE')
    if not iso: return "Nenhuma (Free)"
    
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        
        # Verifica se já venceu
        now = datetime.now(timezone.utc)
        if dt < now:
            return "Expirado"
            
        return dt.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    except Exception: return "Data Inválida"

def _get_user_target(context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    return context.user_data.get("premium_target_uid")

def _set_user_target(context: ContextTypes.DEFAULT_TYPE, uid: int, name: str) -> None:
    context.user_data["premium_target_uid"] = int(uid)
    context.user_data["premium_target_name"] = name

def _panel_text(user_id: int, pdata: dict) -> str:
    name = pdata.get("character_name") or f"Jogador {user_id}"
    
    tier = pdata.get("premium_tier")
    exp_iso = pdata.get("premium_expires_at")
    
    # Se tier for None ou 'free', força exibição correta
    if not tier or tier == "free":
        tier_disp = "Aventureiro Comum (Free)"
        exp_disp = "-"
    else:
        tier_disp = game_data.PREMIUM_TIERS.get(tier, {}).get("display_name", tier.title())
        exp_disp = _fmt_date(exp_iso)

    return (
        "🔥 <b>PAINEL DE GESTÃO PREMIUM</b>\n\n"
        f"👤 <b>Usuário:</b> {name} <code>({user_id})</code>\n"
        f"👑 <b>Plano Atual:</b> {tier_disp}\n"
        f"📅 <b>Vencimento:</b> {exp_disp}\n\n"
        "👇 <b>Selecione uma ação:</b>"
    )

def _panel_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("🆓 Definir FREE", callback_data="prem_tier:free"),
            InlineKeyboardButton("⭐ Premium", callback_data="prem_tier:premium"),
        ],
        [
            InlineKeyboardButton("💎 VIP", callback_data="prem_tier:vip"),
            InlineKeyboardButton("👑 Lenda", callback_data="prem_tier:lenda"),
        ],
        [
            InlineKeyboardButton("📅 +1 Dia", callback_data="prem_add:1"),
            InlineKeyboardButton("📅 +7 Dias", callback_data="prem_add:7"),
            InlineKeyboardButton("📅 +30 Dias", callback_data="prem_add:30"),
        ],
        # --- NOVOS BOTÕES DE REMOVER DIAS ---
        [
            InlineKeyboardButton("🔻 -1 Dia", callback_data="prem_add:-1"),
            InlineKeyboardButton("🔻 -5 Dias", callback_data="prem_add:-5"),
        ],
        # ------------------------------------
        [
             InlineKeyboardButton("🗑️ LIMPAR TUDO (Reset)", callback_data="prem_clear"),
        ],
        [
            InlineKeyboardButton("🔎 Outro Usuário", callback_data="prem_change_user"),
            InlineKeyboardButton("❌ Sair", callback_data="prem_close"),
        ],
    ]
    return InlineKeyboardMarkup(rows)

# ---------------------------------------------------------
# Lógica
# ---------------------------------------------------------
async def _entry_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update): return ConversationHandler.END
    query = update.callback_query
    try: await query.answer()
    except: pass

    prompt = (
        "🔥 <b>GESTOR PREMIUM</b>\n\n"
        "Envie o <b>ID Numérico</b> ou <b>Nome do Personagem</b> para editar.\n"
        "<i>Use /cancelar para sair.</i>"
    )
    keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="prem_close")]]
    
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
            "❌ Jogador não encontrado. Tente novamente ou use /cancelar.", parse_mode="HTML"
        )
        return ASK_NAME

    player_name = pdata.get("character_name", f"ID: {user_id}")
    _set_user_target(context, user_id, player_name)

    text = _panel_text(user_id, pdata)
    await update.message.reply_text(text, reply_markup=_panel_keyboard(), parse_mode="HTML")

    return ASK_NAME

async def _safe_edit(query, text, keyboard):
    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
    except BadRequest: pass 
    except Exception as e: logger.error(f"Erro edit: {e}")

async def _action_set_tier(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update): return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    target_uid = _get_user_target(context)
    if not target_uid:
        await query.answer("Sessão expirada.", show_alert=True)
        return ASK_NAME

    new_tier = (query.data or "prem_tier:free").split(":", 1)[1]

    try:
        pdata = await player_manager.get_player_data(target_uid)
        
        pdata["premium_tier"] = new_tier
        
        if new_tier == "free":
            pdata["premium_expires_at"] = None 
        else:
            if not pdata.get("premium_expires_at"):
                now = datetime.now(timezone.utc)
                pdata["premium_expires_at"] = (now + timedelta(days=30)).isoformat()
        
        await player_manager.save_player_data(target_uid, pdata)

        text = _panel_text(target_uid, pdata)
        await _safe_edit(query, text, _panel_keyboard())

    except Exception as e:
        await query.answer(f"Erro: {e}", show_alert=True)

    return ASK_NAME

async def _action_add_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update): return ConversationHandler.END
    query = update.callback_query
    target_uid = _get_user_target(context)
    if not target_uid: return ASK_NAME

    try:
        days = int(query.data.split(":")[1])
    except: return ASK_NAME

    # Feedback visual (Adicionando ou Removendo)
    action_text = f"Adicionando {days}" if days > 0 else f"Removendo {abs(days)}"
    await query.answer(f"{action_text} dias...")

    try:
        pdata = await player_manager.get_player_data(target_uid)
        
        # Limpa lixo legado
        for k in ["is_permanent", "infinite_premium", "lifetime"]:
            if k in pdata: del pdata[k]

        now = datetime.now(timezone.utc)
        current_exp_iso = pdata.get("premium_expires_at") 
        new_date = None

        if not current_exp_iso:
            # Se não tem data, começa de agora (só funciona bem se days > 0)
            new_date = now + timedelta(days=days)
        else:
            try:
                curr = datetime.fromisoformat(current_exp_iso)
                if curr.tzinfo is None: curr = curr.replace(tzinfo=timezone.utc)
                
                if curr > now:
                    # Se ainda é válido, soma (ou subtrai) da data final
                    new_date = curr + timedelta(days=days)
                else:
                    # Se já venceu, começa de agora
                    new_date = now + timedelta(days=days)
            except:
                new_date = now + timedelta(days=days)

        # Se a subtração resultar numa data passada, ainda salvamos (vai aparecer como Expirado)
        pdata["premium_expires_at"] = new_date.isoformat()
        
        if not pdata.get("premium_tier") or pdata.get("premium_tier") == "free":
             pdata["premium_tier"] = "premium"

        await player_manager.save_player_data(target_uid, pdata)

        text = _panel_text(target_uid, pdata)
        await _safe_edit(query, text, _panel_keyboard())

    except Exception as e:
        logger.error(f"Erro add days: {e}")

    return ASK_NAME

async def _action_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update): return ConversationHandler.END
    query = update.callback_query
    target_uid = _get_user_target(context)
    
    await query.answer("Limpando dados premium...")

    try:
        pdata = await player_manager.get_player_data(target_uid)
        
        pdata["premium_tier"] = "free"
        pdata["premium_expires_at"] = None
        
        for k in ["premium_expiration", "is_permanent", "infinite_premium", "lifetime", "vip_data"]:
            if k in pdata: del pdata[k]
        
        await player_manager.save_player_data(target_uid, pdata)

        text = _panel_text(target_uid, pdata)
        await _safe_edit(query, text, _panel_keyboard())

    except Exception as e:
        logger.error(f"Erro clear: {e}")

    return ASK_NAME

async def _action_change_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _entry_from_callback(update, context)

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
    name="premium_panel_conv",
    persistent=False,
)