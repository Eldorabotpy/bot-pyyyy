# handlers/admin/sell_gems.py
# (VERSÃO CORRIGIDA: Callback Sincronizado + Busca Estrita ObjectId)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, ConversationHandler, 
    MessageHandler, filters, CommandHandler
)
from bson import ObjectId

# Imports do Core
from modules.player.core import get_player_data, save_player_data
from modules.player.inventory import add_gems
from handlers.admin.utils import ensure_admin

logger = logging.getLogger(__name__)

# Estados da Conversation
(ASK_TARGET_PLAYER, ASK_QUANTITY, CONFIRM_ACTION) = range(3)

# ==============================================================================
# BUSCA RESTRITA (APENAS OBJECTID)
# ==============================================================================
async def smart_search_player_strict(term: str):
    """
    Busca ESTRITAMENTE por ObjectId (24 chars hex).
    Ignora nomes e IDs numéricos antigos.
    """
    term = str(term).strip()
    
    # Validação estrita: Se não for ObjectId válido, retorna None imediatamente.
    if not ObjectId.is_valid(term):
        return None

    # Busca direta no banco via Core
    # (ObjectId válido é convertido automaticamente dentro do get_player_data se necessário,
    # mas aqui já passamos o objeto limpo)
    try:
        oid = ObjectId(term)
        pdata = await get_player_data(oid)
        
        if pdata:
            return pdata.get("_id") # Retorna o ObjectId do documento
    except Exception:
        return None

    return None

# ==============================================================================
# ENTRY POINTS
# ==============================================================================

async def start_add_gems(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo de ADICIONAR (VENDER) gemas."""
    if not await ensure_admin(update): return ConversationHandler.END
    await update.callback_query.answer()
    
    context.user_data.clear()
    context.user_data['gem_action'] = 'add'
    
    await update.callback_query.edit_message_text(
        "💎 <b>VENDER/ADICIONAR GEMAS</b>\n\n"
        "Envie o <b>ObjectId</b> do jogador (24 caracteres).\n"
        "<i>Ex: 675da...</i>\n\n"
        "⚠️ <b>Atenção:</b> Somente ID Hexadecimal é aceito.",
        parse_mode="HTML"
    )
    return ASK_TARGET_PLAYER

async def start_remove_gems(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo de REMOVER gemas."""
    if not await ensure_admin(update): return ConversationHandler.END
    await update.callback_query.answer()
    
    context.user_data.clear()
    context.user_data['gem_action'] = 'remove'
    
    await update.callback_query.edit_message_text(
        "🔥 <b>REMOVER GEMAS</b>\n\n"
        "Envie o <b>ObjectId</b> do jogador para debitar.\n"
        "⚠️ <b>Atenção:</b> Somente ID Hexadecimal é aceito.",
        parse_mode="HTML"
    )
    return ASK_TARGET_PLAYER

# ==============================================================================
# FLUXO DA CONVERSA
# ==============================================================================

async def receive_target_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        await update.message.reply_text("Envie apenas o ID (texto).")
        return ASK_TARGET_PLAYER

    txt = update.message.text.strip()
    
    # Verificação rápida visual antes de ir ao banco
    if not ObjectId.is_valid(txt):
        await update.message.reply_text("❌ <b>ID Inválido!</b>\nO ID deve ter 24 caracteres hexadecimais.\nTente novamente:", parse_mode="HTML")
        return ASK_TARGET_PLAYER

    status = await update.message.reply_text(f"🔍 Buscando ID: {txt}...")
    
    try:
        # Busca estrita
        uid = await smart_search_player_strict(txt)

        if not uid:
            await status.edit_text(f"❌ Jogador com ID <code>{txt}</code> não encontrado no banco.", parse_mode="HTML")
            return ASK_TARGET_PLAYER

        pdata = await get_player_data(uid)
        if not pdata:
            await status.edit_text("❌ Erro crítico ao carregar dados do jogador.")
            return ASK_TARGET_PLAYER

        # Salva dados no contexto
        context.user_data['gem_target_id'] = uid
        context.user_data['gem_target_name'] = pdata.get('character_name', 'Sem Nome')
        
        # Feedback visual
        action = context.user_data.get('gem_action', 'add')
        action_text = "ADICIONAR a" if action == 'add' else "REMOVER de"
        current_gems = pdata.get("gems", 0)
        
        await status.edit_text(
            f"✅ <b>ALVO CONFIRMADO</b>\n"
            f"👤 <b>Nome:</b> {context.user_data['gem_target_name']}\n"
            f"🆔 <b>ID:</b> <code>{str(uid)}</code>\n"
            f"💰 <b>Saldo Atual:</b> {current_gems} gemas\n\n"
            f"Digite a <b>QUANTIDADE</b> para {action_text} este jogador:",
            parse_mode="HTML"
        )
        return ASK_QUANTITY

    except Exception as e:
        logger.error("Erro em gem_manager", exc_info=True)
        await status.edit_text(f"ERRO INTERNO: {e}")
        return ConversationHandler.END

async def receive_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        qty = int(update.message.text.strip())
        if qty <= 0: raise ValueError
        
        context.user_data['gem_quantity'] = qty
        name = context.user_data['gem_target_name']
        action = context.user_data.get('gem_action', 'add')
        
        if action == 'add':
            msg = f"💎 <b>Confirmar VENDA?</b>\n\nEnviar <b>{qty}</b> gemas para <b>{name}</b>?"
            confirm_btn = InlineKeyboardButton("✅ CONFIRMAR ENVIO", callback_data="gem_confirm_yes")
        else:
            msg = f"🔥 <b>Confirmar REMOÇÃO?</b>\n\nRemover <b>{qty}</b> gemas de <b>{name}</b>?"
            confirm_btn = InlineKeyboardButton("🗑️ CONFIRMAR REMOÇÃO", callback_data="gem_confirm_yes")

        kb = InlineKeyboardMarkup([
            [confirm_btn],
            [InlineKeyboardButton("❌ CANCELAR", callback_data="gem_confirm_no")]
        ])
        
        await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")
        return CONFIRM_ACTION
        
    except:
        await update.message.reply_text("⚠️ Número inválido. Digite um valor maior que zero.")
        return ASK_QUANTITY

async def dispatch_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    if query.data == "gem_confirm_no":
        await query.edit_message_text("❌ Operação cancelada.")
        context.user_data.clear()
        return ConversationHandler.END

    uid = context.user_data['gem_target_id']
    qty = context.user_data['gem_quantity']
    action = context.user_data.get('gem_action', 'add')
    name = context.user_data['gem_target_name']
    
    pdata = await get_player_data(uid)
    if pdata:
        final_qty = qty
        if action == 'remove':
            final_qty = -qty 
        
        add_gems(pdata, final_qty)
        await save_player_data(uid, pdata)
        
        if action == 'add':
            await query.edit_message_text(f"✅ <b>SUCESSO!</b>\nForam adicionadas {qty} gemas para {name}.")
        else:
            await query.edit_message_text(f"🗑️ <b>REMOVIDO!</b>\nForam retiradas {qty} gemas de {name}.")

        await _notify_player(context, uid, pdata, action, qty)
    else:
        await query.edit_message_text("❌ Erro: Jogador não encontrado no momento da gravação.")
    
    context.user_data.clear()
    return ConversationHandler.END

async def _notify_player(context, uid, pdata, action, qty):
    try:
        target_chat_id = pdata.get("telegram_id_owner") or pdata.get("last_chat_id")
        if not target_chat_id: return

        if action == 'add':
            msg = (
                "💎 <b>ENTREGA DE GEMAS</b>\n"
                f"Você recebeu <b>{qty}</b> Gemas da administração!"
            )
        else:
            msg = (
                "⚖️ <b>AJUSTE DE CONTA</b>\n"
                f"Foram removidas <b>{qty}</b> Gemas da sua conta."
            )
            
        await context.bot.send_message(target_chat_id, msg, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"Falha ao notificar player {uid}: {e}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelado.")
    context.user_data.clear()
    return ConversationHandler.END

# ==============================================================================
# CONFIGURAÇÃO DO HANDLER
# ==============================================================================
sell_gems_conv_handler = ConversationHandler(
    entry_points=[
        # ✅ CORREÇÃO: "admin_sell_gems" para bater com o menu do admin_handler.py
        CallbackQueryHandler(start_add_gems, pattern=r"^admin_sell_gems$"),    
        CallbackQueryHandler(start_remove_gems, pattern=r"^admin_remove_gems$")
    ],
    states={
        ASK_TARGET_PLAYER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_target_player)],
        ASK_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_quantity)],
        CONFIRM_ACTION: [
            CallbackQueryHandler(dispatch_action, pattern=r"^gem_confirm_yes$"),
            CallbackQueryHandler(dispatch_action, pattern=r"^gem_confirm_no$"), 
        ],
    },
    fallbacks=[CommandHandler("cancelar", cancel)],
    per_message=False 
)