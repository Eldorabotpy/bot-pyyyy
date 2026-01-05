# handlers/admin/sell_gems.py
# (VERSÃO FINAL: Add/Remove Gemas + Busca Estrita ObjectId)

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
from modules.player.queries import find_player_by_name
from handlers.admin.utils import ensure_admin

logger = logging.getLogger(__name__)

# Estados da Conversation
(ASK_TARGET_PLAYER, ASK_QUANTITY, CONFIRM_ACTION) = range(3)

# ==============================================================================
# BUSCA RESTRITA (APENAS OBJECTID OU NOME)
# ==============================================================================
async def smart_search_player_strict(term: str):
    """
    Busca apenas por ObjectId válido ou Nome do Personagem.
    Ignora IDs numéricos (int) legados para evitar erros de tipagem.
    """
    term = str(term).strip()
    
    # 1. Validação estrita de ObjectId (24 chars hex)
    if ObjectId.is_valid(term):
        # Busca direta no banco novo
        pdata = await get_player_data(ObjectId(term))
        if pdata:
            # Retorna o ObjectId puro do documento
            return pdata.get("_id")

    # 2. Busca por Nome (Retorna tupla (uid, pdata))
    # A query interna do find_player_by_name já varre as duas coleções
    found = await find_player_by_name(term)
    if found:
        # Retorna o UID encontrado (pode ser str ou ObjectId, dependendo da origem)
        return found[0]

    return None

# ==============================================================================
# ENTRY POINTS (ADICIONAR vs REMOVER)
# ==============================================================================

async def start_add_gems(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo de ADICIONAR gemas."""
    if not await ensure_admin(update): return ConversationHandler.END
    await update.callback_query.answer()
    
    context.user_data.clear()
    context.user_data['gem_action'] = 'add' # Define o modo
    
    await update.callback_query.edit_message_text(
        "💎 <b>ADICIONAR GEMAS</b>\n\n"
        "Envie o <b>NOME</b> ou <b>ObjectId</b> do jogador.\n"
        "<i>(Sistema Novo - IDs numéricos ignorados)</i>",
        parse_mode="HTML"
    )
    return ASK_TARGET_PLAYER

async def start_remove_gems(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo de REMOVER gemas."""
    if not await ensure_admin(update): return ConversationHandler.END
    await update.callback_query.answer()
    
    context.user_data.clear()
    context.user_data['gem_action'] = 'remove' # Define o modo
    
    await update.callback_query.edit_message_text(
        "🔥 <b>REMOVER GEMAS (Sanção/Correção)</b>\n\n"
        "Envie o <b>NOME</b> ou <b>ObjectId</b> do jogador para debitar.",
        parse_mode="HTML"
    )
    return ASK_TARGET_PLAYER

# ==============================================================================
# FLUXO DA CONVERSA
# ==============================================================================

async def receive_target_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        await update.message.reply_text("Envie apenas texto.")
        return ASK_TARGET_PLAYER

    txt = update.message.text.strip()
    status = await update.message.reply_text(f"🔍 Buscando: {txt}...")
    
    try:
        # Usa a busca estrita
        uid = await smart_search_player_strict(txt)

        if not uid:
            await status.edit_text(f"❌ Jogador '{txt}' não encontrado.")
            return ASK_TARGET_PLAYER

        pdata = await get_player_data(uid)
        if not pdata:
            await status.edit_text("❌ Erro ao carregar dados.")
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
        
        # Monta mensagem de confirmação baseada na ação
        if action == 'add':
            msg = f"💎 <b>Confirmar DOAÇÃO?</b>\n\nEnviar <b>{qty}</b> gemas para <b>{name}</b>?"
            confirm_btn = InlineKeyboardButton("✅ ENVIAR", callback_data="gem_confirm_yes")
        else:
            msg = f"🔥 <b>Confirmar REMOÇÃO?</b>\n\nRemover <b>{qty}</b> gemas de <b>{name}</b>?"
            confirm_btn = InlineKeyboardButton("🗑️ REMOVER", callback_data="gem_confirm_yes")

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
        await query.edit_message_text("❌ Cancelado.")
        context.user_data.clear()
        return ConversationHandler.END

    # Recupera dados
    uid = context.user_data['gem_target_id']
    qty = context.user_data['gem_quantity']
    action = context.user_data.get('gem_action', 'add')
    name = context.user_data['gem_target_name']
    
    pdata = await get_player_data(uid)
    if pdata:
        # --- LÓGICA DE AÇÃO ---
        final_qty = qty
        if action == 'remove':
            final_qty = -qty # Inverte para negativo
            
            # O add_gems no inventory.py usa set_gems(max(0, ...))
            # então ele já protege contra saldo negativo automaticamente.
        
        # Aplica a mudança
        add_gems(pdata, final_qty)
        await save_player_data(uid, pdata)
        
        # --- FEEDBACK ADMIN ---
        if action == 'add':
            await query.edit_message_text(f"✅ <b>SUCESSO!</b>\nForam adicionadas {qty} gemas para {name}.")
        else:
            await query.edit_message_text(f"🗑️ <b>REMOVIDO!</b>\nForam retiradas {qty} gemas de {name}.")

        # --- NOTIFICAÇÃO AO JOGADOR ---
        await _notify_player(context, uid, pdata, action, qty)
        
    else:
        await query.edit_message_text("❌ Erro: Jogador não encontrado no momento da gravação.")
    
    context.user_data.clear()
    return ConversationHandler.END

async def _notify_player(context, uid, pdata, action, qty):
    """Envia a mensagem imersiva correta."""
    try:
        # Tenta achar o chat_id mais recente
        target_chat_id = pdata.get("telegram_id_owner") or pdata.get("last_chat_id")
        
        # Se for ID legado (int), ele pode ser o chat_id
        if not target_chat_id and isinstance(uid, int):
            target_chat_id = uid
            
        if not target_chat_id: return

        if action == 'add':
            msg = (
                "👑 ⚜️ <b>𝐃𝐄𝐂𝐑𝐄𝐓𝐎 𝐃𝐄 𝐄𝐋𝐃𝐎𝐑𝐀</b> ⚜️ 👑\n"
                "═════════════════════════\n"
                "<i>Recursos especiais foram alocados.</i>\n\n"
                f"💎 <b>Recebido:</b> <code>{qty}</code> Gemas\n"
                "═════════════════════════"
            )
        else:
            msg = (
                "⚖️ 📜 <b>𝐒𝐀𝐍ÇÃ𝐎 𝐑𝐄𝐀𝐋</b> 📜 ⚖️\n"
                "═════════════════════════\n"
                "<i>Um ajuste administrativo foi realizado.</i>\n\n"
                f"🔥 <b>Removido:</b> <code>{qty}</code> Gemas\n"
                "═════════════════════════"
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
        CallbackQueryHandler(start_add_gems, pattern=r"^admin_add_gems$"),    # Botão de Adicionar
        CallbackQueryHandler(start_remove_gems, pattern=r"^admin_remove_gems$") # Botão de Remover
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