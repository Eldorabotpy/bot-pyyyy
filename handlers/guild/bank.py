import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    CommandHandler,
)
from modules import player_manager, clan_manager
from ..guild_handler import ASKING_DEPOSIT_AMOUNT, ASKING_WITHDRAW_AMOUNT
from ..utils import safe_edit_message

logger = logging.getLogger(__name__)

# --- Menu Principal do Banco ---

async def show_clan_bank_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o menu do banco do clã."""
    query = update.callback_query
    user_id = update.effective_user.id
    player_data = await player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")
    
    if not clan_id:
        await query.answer("Erro: Não foi possível encontrar seu clã.", show_alert=True)
        return

    clan_data = await clan_manager.get_clan(clan_id)

    if not clan_data:
        await query.answer("Você não está em um clã.", show_alert=True)
        return

    bank_gold = clan_data.get("bank", {}).get("gold", 0)
    bank_dimas = clan_data.get("bank", {}).get("dimas", 0)
    
    caption = (
        "🏦 <b>Banco do Clã</b> 🏦\n\n"
        "Aqui você e seus companheiros podem depositar e retirar recursos "
        "para ajudar no crescimento e fortalecimento do clã.\n\n"
        "<b>Recursos Atuais no Banco:</b>\n"
        f"- 🪙 Ouro: {bank_gold:,}\n"
        f"- 💎 Diamantes: {bank_dimas:,}"
    )

    keyboard = [
        [
            InlineKeyboardButton("💰 Depositar Ouro", callback_data="clan_deposit_start"),
            InlineKeyboardButton("💸 Retirar Ouro", callback_data="clan_withdraw_start"),
        ],
        [InlineKeyboardButton("📖 Ver Histórico", callback_data="clan_bank_log")],
        [InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="clan_menu")],
    ]
    
    await safe_edit_message(
        query,
        text=caption,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# --- Lógica de Depósito e Retirada ---
async def show_bank_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o histórico de transações do banco."""
    print(">>> DEBUG: Função show_bank_log FOI CHAMADA!")
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    # <<< CORREÇÃO 3: Adiciona await e separa a lógica >>>
    player_data = await player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")
    
    # <<< CORREÇÃO 4: Adiciona await >>>
    clan_data = await clan_manager.get_clan(clan_id)
    
    bank_log = clan_data.get("bank_log", [])
    
    caption = "📖 <b>Histórico do Banco</b> 📖\n\n"
    
    if not bank_log:
        caption += "Nenhuma transação registrada ainda."
    else:
        # Mostra as últimas 10 transações
        for entry in bank_log[:10]:
            action_emoji = "💰" if entry['action'] == 'depositou' else "💸"
            caption += (
                f"<code>[{entry['timestamp']}]</code>\n"
                f"{action_emoji} {entry['player_name']} {entry['action']} "
                f"<b>{entry['amount']:,}</b> 🪙\n\n"
            )
            
    keyboard = [[InlineKeyboardButton("⬅️ Voltar ao Banco", callback_data="clan_bank_menu")]]
    
    await safe_edit_message(
        query,
        text=caption,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def start_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia a conversa para depositar ouro."""
    query = update.callback_query
    await query.answer()
    await safe_edit_message(query, text="Quanto ouro você gostaria de depositar?\nEnvie um número ou use /cancelar.")
    return ASKING_DEPOSIT_AMOUNT

async def receive_deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa a quantia de ouro a ser depositada."""
    user_id = update.effective_user.id
    
    # <<< CORREÇÃO 5: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")

    try:
        amount = int(update.message.text)
        if amount <= 0:
            await update.message.reply_text("Por favor, envie um número positivo.")
            return ASKING_DEPOSIT_AMOUNT
    except ValueError:
        await update.message.reply_text("Entrada inválida. Por favor, envie apenas números.")
        return ASKING_DEPOSIT_AMOUNT

    print(f"[DEBUG BANCO] Tentando depositar: {amount}. Ouro do jogador (lido pelo bank.py): {player_data.get('gold', 0)}")
    
    # <<< CORREÇÃO 6: Adiciona await >>>
    # (deposit_gold precisa ser async pois lê/escreve no player E no clã)
    success, message = await clan_manager.deposit_gold(clan_id, user_id, amount)

    keyboard = [[InlineKeyboardButton("⬅️ Voltar ao Banco", callback_data="clan_bank_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if success:
        await update.message.reply_text(
            f"✅ {message}", 
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            f"❌ Erro: {message}",
            reply_markup=reply_markup
        )
        
    return ConversationHandler.END

async def start_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia a conversa para retirar ouro."""
    query = update.callback_query
    await query.answer()
    await safe_edit_message(query, text="Quanto ouro você gostaria de retirar?\nEnvie um número ou use /cancelar.")
    return ASKING_WITHDRAW_AMOUNT

async def receive_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa a quantia de ouro a ser retirada."""
    user_id = update.effective_user.id
    
    # <<< CORREÇÃO 7: Adiciona await e separa a lógica >>>
    player_data = await player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")

    try:
        amount = int(update.message.text)
        if amount <= 0:
            await update.message.reply_text("Por favor, envie um número positivo.")
            return ASKING_WITHDRAW_AMOUNT
    except ValueError:
        await update.message.reply_text("Entrada inválida. Por favor, envie apenas números.")
        return ASKING_WITHDRAW_AMOUNT

    # <<< CORREÇÃO 8: Adiciona await >>>
    # (withdraw_gold precisa ser async)
    success, message = await clan_manager.withdraw_gold(clan_id, user_id, amount)

    keyboard = [[InlineKeyboardButton("⬅️ Voltar ao Banco", callback_data="clan_bank_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if success:
        await update.message.reply_text(
            f"✅ Você retirou {amount:,} 🪙 de ouro do banco do clã com sucesso!",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            f"❌ Erro: {message}",
            reply_markup=reply_markup
        )

    return ConversationHandler.END

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a operação atual (depósito/retirada)."""
    # ✅ MESMA LÓGICA APLICADA AO CANCELAMENTO
    keyboard = [[InlineKeyboardButton("⬅️ Voltar ao Banco", callback_data="clan_bank_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Operação cancelada.",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

# --- Definição dos Handlers ---

clan_bank_menu_handler = CallbackQueryHandler(show_clan_bank_menu, pattern=r'^clan_bank_menu$')
clan_bank_log_handler = CallbackQueryHandler(show_bank_log, pattern=r'^clan_bank_log$')
clan_deposit_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_deposit, pattern=r'^clan_deposit_start$')],
    states={
        ASKING_DEPOSIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_deposit_amount)],
    },
    fallbacks=[CommandHandler('cancelar', cancel_conversation)],
)

clan_withdraw_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_withdraw, pattern=r'^clan_withdraw_start$')],
    states={
        ASKING_WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_withdraw_amount)],
    },
    fallbacks=[CommandHandler('cancelar', cancel_conversation)],
)