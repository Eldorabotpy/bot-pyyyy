# handlers/admin/sell_gems.py
# (VERSÃO FINAL: FILTRO UNIVERSAL E LOGS)

import re
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, ConversationHandler, 
    MessageHandler, filters, CommandHandler
)
from bson import ObjectId
from modules.player.core import players_collection, get_player_data, save_player_data
from modules.player.inventory import add_gems
from handlers.admin.utils import ensure_admin

logger = logging.getLogger(__name__)

(ASK_TARGET_PLAYER, ASK_QUANTITY, CONFIRM_GRANT) = range(3)

def _blocking_search(term: str):
    if players_collection is None: return None
    try:
        term = str(term).strip()
        
        # 1. ID Numérico (Legado)
        if term.isdigit():
            doc = players_collection.find_one({"_id": int(term)})
            if doc: return doc["_id"]

        # 2. ID ObjectId (Novo) - ADICIONAR ISSO
        if ObjectId.is_valid(term):
            doc = players_collection.find_one({"_id": ObjectId(term)})
            if doc: return doc["_id"]

        # 3. Regex (Haküro)
        safe = re.escape(term)
        doc = players_collection.find_one({"character_name": {"$regex": f"^{safe}$", "$options": "i"}})
        if doc: return doc["_id"]
        
        # 4. Normalizado
        from modules.player.queries import _normalize_char_name
        norm = _normalize_char_name(term)
        doc = players_collection.find_one({"character_name_normalized": norm})
        if doc: return doc["_id"]
    except Exception as e:
        logger.error(f"Erro DB: {e}")
    return None

async def start_sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update): return ConversationHandler.END
    await update.callback_query.answer()
    
    # Limpa dados anteriores
    context.user_data.clear()
    
    await update.callback_query.edit_message_text(
        "DIAGNOSTICO DE GEMAS V2:\n\n"
        "Mande o NOME ou ID.\n"
        "Estou ouvindo tudo (Filtro Universal)."
    )
    return ASK_TARGET_PLAYER

async def receive_target_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Captura qualquer coisa que o usuário mandou
    if update.message and update.message.text:
        txt = update.message.text
    else:
        await update.message.reply_text("Por favor, envie apenas texto.")
        return ASK_TARGET_PLAYER

    status = await update.message.reply_text(f"🔍 Buscando: {txt}...")
    
    try:
        uid = await asyncio.to_thread(_blocking_search, txt)

        if not uid:
            await status.edit_text(f"❌ '{txt}' não encontrado no DB.")
            return ASK_TARGET_PLAYER

        pdata = await get_player_data(uid)
        if not pdata:
            await status.edit_text("❌ Erro ao carregar dados do jogador.")
            return ASK_TARGET_PLAYER

        context.user_data['gem_target_id'] = uid
        context.user_data['gem_target_name'] = pdata.get('character_name', str(uid))

        await status.edit_text(
            f"✅ ALVO: {context.user_data['gem_target_name']}\n"
            f"🆔 ID: {uid}\n\n"
            "Digite a QUANTIDADE:"
        )
        return ASK_QUANTITY

    except Exception as e:
        logger.error("Erro critico", exc_info=True)
        await status.edit_text(f"ERRO: {e}")
        return ConversationHandler.END

async def receive_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        qty = int(update.message.text.strip())
        if qty <= 0: raise ValueError
        context.user_data['gem_quantity'] = qty
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ ENVIAR", callback_data="gem_confirm_yes")],
            [InlineKeyboardButton("❌ CANCELAR", callback_data="gem_confirm_no")]
        ])
        await update.message.reply_text(
            f"Confirma {qty} gemas para {context.user_data['gem_target_name']}?",
            reply_markup=kb
        )
        return CONFIRM_GRANT
    except:
        await update.message.reply_text("Número inválido.")
        return ASK_QUANTITY

async def dispatch_grant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    uid = context.user_data['gem_target_id']
    qty = context.user_data['gem_quantity']
    name = context.user_data['gem_target_name']
    
    pdata = await get_player_data(uid)
    if pdata:
        add_gems(pdata, qty)
        await save_player_data(uid, pdata)
        
        # Feedback para o Admin
        await update.callback_query.edit_message_text(f"✅ <b>SUCESSO!</b>\n{qty} gemas foram enviadas para {name}.", parse_mode="HTML")
        
        # --- NOTIFICAÇÃO RPG PARA O JOGADOR ---
        try:
            msg_rpg = (
                "👑 ⚜️ <b>𝐃𝐄𝐂𝐑𝐄𝐓𝐎 𝐃𝐄 𝐄𝐋𝐃𝐎𝐑𝐀</b> ⚜️ 👑\n"
                "═════════════════════════\n"
                "<i>Por ordem superior, recursos especiais\n"
                "foram alocados para sua jornada.</i>\n\n"
                f"💎 <b>𝐐𝐮𝐚𝐧𝐭𝐢𝐝𝐚𝐝𝐞:</b> <code>{qty}</code> Gemas\n"
                "📦 <b>𝐒𝐭𝐚𝐭𝐮𝐬:</b> Entregue com Sucesso\n\n"
                "<i>Faça bom uso destas riquezas.</i>\n"
                "═════════════════════════"
            )
            
            await context.bot.send_message(uid, msg_rpg, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Não foi possível notificar o jogador {uid}: {e}")
        # --------------------------------------
        
    else:
        await update.callback_query.edit_message_text("❌ Erro ao salvar dados no banco.")
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelado.")
    context.user_data.clear()
    return ConversationHandler.END

sell_gems_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_sell, pattern=r"^admin_sell_gems$")],
    states={
        # USANDO FILTERS.ALL para garantir que pegue TUDO
        ASK_TARGET_PLAYER: [MessageHandler(filters.ALL & ~filters.COMMAND, receive_target_player)],
        ASK_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_quantity)],
        CONFIRM_GRANT: [
            CallbackQueryHandler(dispatch_grant, pattern=r"^gem_confirm_yes$"),
            CallbackQueryHandler(dispatch_grant, pattern=r"^gem_confirm_no$"), 
        ],
    },
    fallbacks=[CommandHandler("cancelar", cancel)],
    per_message=False # Garante persistência por usuário
)