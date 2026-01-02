# handlers/guild/bank.py
# (VERSÃO ZERO LEGADO: BANCO DE CLÃ + AUTH SEGURA)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, ConversationHandler,
    MessageHandler, filters, CommandHandler
)
from modules import player_manager, clan_manager
from modules.auth_utils import get_current_player_id

ASKING_DEPOSIT_AMOUNT = 0
ASKING_WITHDRAW_AMOUNT = 1

# --- Helper de Limpeza ---
async def _clean_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove mensagens de interação do bot para manter o chat limpo."""
    try: await update.message.delete()
    except: pass
    last_id = context.user_data.get('last_bot_msg_id')
    if last_id:
        try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_id)
        except: pass
        context.user_data.pop('last_bot_msg_id', None)

async def show_clan_bank_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # 🔒 SEGURANÇA: Apenas sessão validada (String ID)
    user_id = get_current_player_id(update, context)
    if not user_id:
        await query.answer("❌ Sessão inválida. Use /start.", show_alert=True)
        return

    await query.answer()
    
    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        await query.edit_message_text("Perfil não encontrado.")
        return

    clan_id = pdata.get("clan_id")
    if not clan_id: 
        await query.edit_message_text("Você não possui um clã.")
        return

    clan = await clan_manager.get_clan(clan_id)
    if not clan:
        await query.edit_message_text("Clã não encontrado.")
        return

    saldo = clan.get("bank", 0)
    
    # Renderiza Log
    logs = clan.get("bank_log", [])[-5:]
    log_text = ""
    for l in reversed(logs):
        emoji = "📥" if l.get('action') == 'depositou' else "📤"
        p_name = l.get('player_name', 'Desconhecido')
        val = l.get('amount', 0)
        log_text += f"{emoji} {p_name}: {val:,} 🪙\n"

    text = (
        f"🏦 <b>COFRE DO CLÃ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 <b>Saldo Atual:</b> {saldo:,} Ouro\n\n"
        f"📜 <b>Últimas Movimentações:</b>\n{log_text if log_text else 'Vazio.'}"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📥 Depositar", callback_data="clan_deposit_start"),
            # InlineKeyboardButton("📤 Sacar (Líder)", callback_data="clan_withdraw_start") # Futuro
        ],
        [InlineKeyboardButton("🔙 Voltar ao Clã", callback_data="clan_menu")]
    ]
    
    try:
        await query.edit_message_caption(caption=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    except:
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# --- FLUXO DE DEPÓSITO ---

async def start_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # 🔒 SEGURANÇA PREVENTIVA
    if not get_current_player_id(update, context):
        await query.answer("Sessão expirada.")
        return ConversationHandler.END

    await query.answer()
    
    msg_text = "📥 <b>Depósito</b>\nDigite o valor que deseja doar:"
    try:
        msg = await query.edit_message_text(msg_text, parse_mode="HTML")
        context.user_data['last_bot_msg_id'] = msg.message_id
    except:
        await query.delete_message()
        msg = await context.bot.send_message(chat_id=query.message.chat.id, text=msg_text, parse_mode="HTML")
        context.user_data['last_bot_msg_id'] = msg.message_id
        
    return ASKING_DEPOSIT_AMOUNT

async def receive_deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 🔒 SEGURANÇA: Identificação via Auth Central
    user_id = get_current_player_id(update, context)
    if not user_id:
        return ConversationHandler.END

    text = update.message.text.strip()
    await _clean_chat(update, context) 

    if not text.isdigit():
        msg = await update.message.reply_text("❌ Digite apenas números inteiros.")
        context.user_data['last_bot_msg_id'] = msg.message_id
        return ASKING_DEPOSIT_AMOUNT
        
    amount = int(text)
    if amount <= 0: 
        return ConversationHandler.END
    
    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        return ConversationHandler.END

    # Verifica saldo e remove
    if not player_manager.spend_gold(pdata, amount):
        msg = await update.message.reply_text("❌ Ouro insuficiente no seu inventário.")
        context.user_data['last_bot_msg_id'] = msg.message_id
        return ConversationHandler.END
        
    # Efetua Depósito
    clan_id = pdata.get("clan_id")
    if clan_id:
        await clan_manager.bank_deposit(clan_id, user_id, amount)
    
    # Persiste alteração do jogador (ouro removido)
    await player_manager.save_player_data(user_id, pdata)
    
    # Feedback
    kb = [[InlineKeyboardButton("🔙 Voltar ao Banco", callback_data="clan_bank_menu")]]
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=f"✅ <b>Sucesso!</b> Você depositou {amount:,} Ouro no cofre do clã.", 
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

# --- REGISTRO DOS HANDLERS ---
clan_bank_menu_handler = CallbackQueryHandler(show_clan_bank_menu, pattern=r'^clan_bank_menu$')
clan_bank_log_handler = CallbackQueryHandler(lambda u,c: u.callback_query.answer("Use o menu acima."), pattern=r'^clan_bank_log$')

clan_deposit_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_deposit, pattern=r'^clan_deposit_start$')],
    states={ASKING_DEPOSIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_deposit_amount)]},
    fallbacks=[CommandHandler('cancelar', cancel_op)]
)

clan_withdraw_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(lambda u,c: u.callback_query.answer("Em breve!"), pattern=r'^clan_withdraw_start$')],
    states={}, fallbacks=[]
)