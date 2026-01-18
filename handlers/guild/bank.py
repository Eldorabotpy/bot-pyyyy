# handlers/guild/bank.py
# (VERSÃO CORRIGIDA: UI RENDERER + VISUAL DE COFRE + PROTEÇÃO DE SESSÃO)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, ConversationHandler,
    MessageHandler, filters, CommandHandler
)
from modules import player_manager, clan_manager, file_ids
from modules.auth_utils import get_current_player_id
from ui.ui_renderer import render_photo_or_text

# Estados do ConversationHandler
ASKING_DEPOSIT_AMOUNT = 0
ASKING_WITHDRAW_AMOUNT = 1

# ==============================================================================
# HELPERS VISUAIS
# ==============================================================================

def _pick_bank_media(clan_data):
    """
    Tenta selecionar uma imagem de 'Cofre/Tesouro'.
    Se não tiver, usa o Logo do Clã.
    """
    # 1. Tenta imagem de Banco
    try:
        fid = file_ids.get_file_id("img_clan_bank")
        if fid: return fid
    except: pass

    # 2. Logo do Clã
    if clan_data and clan_data.get("logo_media_key"):
        return clan_data.get("logo_media_key")
    
    # 3. Fallback
    try:
        return file_ids.get_file_id("img_clan_default")
    except:
        return None

async def _render_bank_screen(update, context, clan_data, text, keyboard):
    """Renderiza a tela usando o sistema unificado UI Renderer."""
    media_id = _pick_bank_media(clan_data)
    
    await render_photo_or_text(
        update,
        context,
        text=text,
        photo_file_id=media_id,
        reply_markup=InlineKeyboardMarkup(keyboard),
        scope="clan_bank_screen", 
        parse_mode="HTML",
        allow_edit=True
    )

async def _clean_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Limpa mensagens de interação do bot para manter o chat organizado."""
    try: await update.message.delete()
    except: pass
    last_id = context.user_data.get('last_bot_msg_id')
    if last_id:
        try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_id)
        except: pass
        context.user_data.pop('last_bot_msg_id', None)

# ==============================================================================
# MENU DO BANCO
# ==============================================================================
async def show_clan_bank_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    # 🔒 SEGURANÇA
    user_id = get_current_player_id(update, context)
    if not user_id: return

    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return

    clan_id = pdata.get("clan_id")
    if not clan_id: 
        await render_photo_or_text(update, context, "Você não possui um clã.", None)
        return

    clan = await clan_manager.get_clan(clan_id)
    if not clan: return

    saldo = clan.get("bank", 0)
    
    # Renderiza Log de Transações
    logs = clan.get("bank_log", [])[-5:] # Pega os últimos 5
    log_text = ""
    if logs:
        for l in reversed(logs):
            emoji = "📥" if l.get('action') == 'depositou' else "📤"
            p_name = l.get('player_name', 'Membro')
            val = l.get('amount', 0)
            log_text += f"{emoji} <b>{p_name}</b>: {val:,} 🪙\n"
    else:
        log_text = "<i>O cofre ainda não foi utilizado.</i>"

    text = (
        f"🏦 <b>COFRE DO CLÃ</b>\n"
        f"Clã: {clan.get('display_name')}\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 <b>Saldo Atual:</b> <code>{saldo:,}</code> Ouro\n\n"
        f"📜 <b>Últimas Movimentações:</b>\n{log_text}"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📥 Depositar Ouro", callback_data="clan_deposit_start"),
            # InlineKeyboardButton("📤 Sacar (Em breve)", callback_data="clan_withdraw_start") 
        ],
        [InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="clan_menu")]
    ]
    
    await _render_bank_screen(update, context, clan, text, keyboard)


# ==============================================================================
# FLUXO DE DEPÓSITO
# ==============================================================================

async def start_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not get_current_player_id(update, context):
        return ConversationHandler.END

    # Limpa a mensagem anterior (opcional, ou manda nova abaixo)
    # Aqui optamos por mandar uma nova mensagem de input para ser limpa depois
    try: await query.delete_message()
    except: pass
    
    msg_text = "📥 <b>DEPÓSITO</b>\n\nDigite a quantia de <b>OURO</b> que deseja doar para o clã:"
    msg = await context.bot.send_message(chat_id=query.message.chat.id, text=msg_text, parse_mode="HTML")
    context.user_data['last_bot_msg_id'] = msg.message_id
        
    return ASKING_DEPOSIT_AMOUNT

async def receive_deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_current_player_id(update, context)
    if not user_id: return ConversationHandler.END

    text = update.message.text.strip()
    await _clean_chat(update, context) 

    if not text.isdigit():
        msg = await update.message.reply_text("❌ Digite apenas números inteiros.")
        context.user_data['last_bot_msg_id'] = msg.message_id
        return ASKING_DEPOSIT_AMOUNT
        
    amount = int(text)
    if amount <= 0: 
        msg = await update.message.reply_text("❌ O valor deve ser maior que zero.")
        context.user_data['last_bot_msg_id'] = msg.message_id
        return ASKING_DEPOSIT_AMOUNT
    
    pdata = await player_manager.get_player_data(user_id)
    
    # Verifica saldo
    if not player_manager.spend_gold(pdata, amount):
        msg = await update.message.reply_text(f"❌ Você não tem {amount:,} de ouro.")
        context.user_data['last_bot_msg_id'] = msg.message_id
        return ConversationHandler.END
        
    # Efetua Depósito
    clan_id = pdata.get("clan_id")
    if clan_id:
        await clan_manager.bank_deposit(clan_id, user_id, amount)
    
    # Salva o jogador (ouro foi gasto)
    await player_manager.save_player_data(user_id, pdata)
    
    # Feedback Final
    kb = [[InlineKeyboardButton("🔙 Voltar ao Cofre", callback_data="clan_bank_menu")]]
    
    # Usa send_message normal pois o fluxo de conversa limpou a tela
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=f"✅ <b>Doação Recebida!</b>\nVocê depositou <b>{amount:,} Ouro</b> no cofre do clã.\nObrigado pela contribuição!", 
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="HTML"
    )
    return ConversationHandler.END

async def cancel_op(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _clean_chat(update, context)
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="❌ Operação cancelada.", 
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar", callback_data="clan_bank_menu")]])
    )
    return ConversationHandler.END

# ==============================================================================
# REGISTRO DOS HANDLERS
# ==============================================================================
clan_bank_menu_handler = CallbackQueryHandler(show_clan_bank_menu, pattern=r'^clan_bank_menu$')
clan_bank_log_handler = CallbackQueryHandler(lambda u,c: u.callback_query.answer("Use o menu acima."), pattern=r'^clan_bank_log$')

clan_deposit_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_deposit, pattern=r'^clan_deposit_start$')],
    states={ASKING_DEPOSIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_deposit_amount)]},
    fallbacks=[CommandHandler('cancelar', cancel_op)],
    
)

clan_withdraw_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(lambda u,c: u.callback_query.answer("Em breve!"), pattern=r'^clan_withdraw_start$')],
    states={}, 
    fallbacks=[],
    
)