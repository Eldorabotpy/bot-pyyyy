# handlers/admin/premium_panel.py
# (VERSÃO FINAL: Integração com a busca corrigida)

from __future__ import annotations
import logging
import html
from datetime import datetime, timezone, timedelta 
from zoneinfo import ZoneInfo
from bson import ObjectId
from ui.ui_renderer import render_menu, render_scope_text

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

JOB_TIMEZONE = "America/Sao_Paulo"
logger = logging.getLogger(__name__)
(ASK_NAME,) = range(1)
PREM_SCOPE = "admin_premium"

def _parse_smart_date(value) -> datetime:
    if not value: return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except: return datetime.now(timezone.utc)

def _format_date_br(iso_str: str, tier: str) -> str:
    if tier == "free" or not iso_str: return "---"
    try:
        dt_utc = _parse_smart_date(iso_str)
        dt_br = dt_utc.astimezone(ZoneInfo(JOB_TIMEZONE))
        return dt_br.strftime("%d/%m/%Y %H:%M")
    except: return "Data Inválida"

async def _save_and_refresh(user_id, pdata):
    await save_player_data(user_id, pdata)
    # --- CORREÇÃO DO ERRO AQUI TAMBÉM ---
    if users_collection is not None:
        try:
            q = {"_id": ObjectId(user_id)} if ObjectId.is_valid(user_id) else None
            if q:
                users_collection.update_one(q, {"$set": {
                    "premium_tier": pdata.get("premium_tier"),
                    "premium_expires_at": pdata.get("premium_expires_at")
                }})
        except: pass
    await clear_player_cache(user_id)

# --- FLUXO DO PAINEL ---

async def _entry_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if context.user_data.get('prem_target_id'):
        target_id = context.user_data['prem_target_id']
        pdata = await get_player_data(target_id)
        if pdata:
            await _show_player_panel(update, context, pdata)
            return ASK_NAME
    
    await render_menu(
        update, context,
        "💎 <b>GERENCIADOR PREMIUM</b>\nEnvie o <b>Nome</b> ou <b>@Usuario</b>:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancelar", callback_data="prem_close")]]),
        scope=PREM_SCOPE,
        allow_edit=True,
        delete_previous_on_send=True,
    )
    return ASK_NAME

async def _receive_name_or_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    txt = update.message.text.strip()
    chat_id = update.effective_chat.id

    # Tenta editar o painel para "pesquisando..."
    await render_scope_text(
        context,
        chat_id,
        "🔍 <b>Buscando jogador...</b>",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancelar", callback_data="prem_close")]]),
        scope=PREM_SCOPE,
        parse_mode="HTML",
    )

    try:
        target_id = parse_hybrid_id(txt)
        pdata = None

        if target_id:
            pdata = await get_player_data(target_id)

        if not pdata:
            found = await find_player_by_name(txt)
            if found:
                target_id, pdata = found

        if not pdata:
            # Edita o mesmo painel com erro
            await render_scope_text(
                context,
                chat_id,
                f"❌ Não encontrado: <b>{html.escape(txt)}</b>\nVerifique se o nome/user está exato.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Voltar", callback_data="admin_premium")],
                    [InlineKeyboardButton("🔙 Cancelar", callback_data="prem_close")]
                ]),
                scope=PREM_SCOPE,
                parse_mode="HTML",
            )
            return ASK_NAME

        context.user_data['prem_target_id'] = target_id
        await _show_player_panel(update, context, pdata)

    except Exception as e:
        logger.error(f"Erro painel premium: {e}")
        await render_scope_text(
            context,
            chat_id,
            f"⚠️ Erro técnico: <code>{html.escape(str(e))}</code>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancelar", callback_data="prem_close")]]),
            scope=PREM_SCOPE,
            parse_mode="HTML",
        )

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

    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=markup, parse_mode="HTML")
    else:
        # EDITA o painel existente do scope
        chat_id = update.effective_chat.id
        ok = await render_scope_text(
            context,
            chat_id,
            msg,
            reply_markup=markup,
            scope=PREM_SCOPE,
            parse_mode="HTML",
        )
        if not ok:
            # fallback: se por algum motivo não existir painel, cria via render_menu
            await render_menu(update, context, msg, reply_markup=markup, scope=PREM_SCOPE, allow_edit=False)

# --- AÇÕES DO MENU ---
async def _action_set_tier(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    target_id = context.user_data.get('prem_target_id')
    new_tier = query.data.split(":")[1]
    
    pdata = await get_player_data(target_id)
    if pdata:
        pdata['premium_tier'] = new_tier
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
        if current_str:
            base_date = _parse_smart_date(current_str)
            if base_date < now_utc: base_date = now_utc
        else: base_date = now_utc

        new_date = base_date + timedelta(days=days_delta)
        pdata['premium_expires_at'] = new_date.isoformat()
        
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
        "💎 <b>GERENCIADOR PREMIUM</b>\nEnvie o novo <b>Nome</b> ou <b>@Usuario</b>:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancelar", callback_data="prem_close")]])
    )
    return ASK_NAME


async def _action_close(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from handlers.admin_handler import _admin_menu_kb
    await update.callback_query.answer()

    # limpa apenas dados do premium
    context.user_data.pop("prem_target_id", None)

    # volta para o menu admin PRINCIPAL (markup correto)
    await render_menu(
        update, context,
        "🎛️ <b>Painel do Admin</b>\nEscolha uma opção:",
        reply_markup=_admin_menu_kb(),   # <<<<<< AQUI está o ponto
        scope="admin",
        allow_edit=True,
        delete_previous_on_send=True
    )
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
