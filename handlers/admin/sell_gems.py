# handlers/admin/sell_gems.py

import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    CommandHandler,
)
from telegram.error import Forbidden

# --- Importações Modificadas para Busca Robusta ---
from modules import player_manager
from modules.player.core import players_collection  # Acesso direto ao DB
from modules.player.queries import _normalize_char_name
from handlers.admin.utils import ensure_admin

# --- Estados da Conversa ---
(ASK_TARGET_PLAYER, ASK_QUANTITY, CONFIRM_GRANT) = range(3)

# --- Funções Auxiliares Locais ---

async def robust_find_player(input_str: str):
    """
    Tenta encontrar um jogador de várias formas:
    1. Pelo ID numérico.
    2. Pelo nome exato normalizado.
    3. Pelo nome via Regex (case insensitive).
    """
    input_str = input_str.strip()

    # 1. Tenta por ID Numérico
    if input_str.isdigit():
        user_id = int(input_str)
        pdata = await player_manager.get_player_data(user_id)
        if pdata:
            return user_id, pdata

    # 2. Tenta por Nome Normalizado (Busca Padrão)
    normalized = _normalize_char_name(input_str)
    pdata_norm = players_collection.find_one({"character_name_normalized": normalized})
    if pdata_norm:
        return pdata_norm["_id"], pdata_norm

    # 3. Tenta por Regex (Case Insensitive) no nome real
    # Isso ajuda com caracteres especiais como 'ü' caso a normalização falhe
    try:
        regex_pattern = f"^{re.escape(input_str)}$"
        pdata_regex = players_collection.find_one({"character_name": {"$regex": regex_pattern, "$options": "i"}})
        if pdata_regex:
            return pdata_regex["_id"], pdata_regex
    except Exception as e:
        print(f"Erro na busca regex em sell_gems: {e}")

    return None

# --- Funções da Conversa ---

async def start_sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia a conversa para vender/entregar gemas."""
    if not await ensure_admin(update):
        return ConversationHandler.END
    
    query = update.callback_query
    await query.answer()
    
    text = (
        "💎 **Venda de Gemas**\n\n"
        "Por favor, envie o **User ID** ou o **nome exato do personagem** "
        "que vai receber as gemas\."
    )
    await query.edit_message_text(text, parse_mode="MarkdownV2")
    
    return ASK_TARGET_PLAYER

async def receive_target_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe o jogador e pede a quantidade de gemas."""
    target_input = update.message.text
    
    # Usa a nova função de busca robusta
    found_player = await robust_find_player(target_input)

    if not found_player:
        await update.message.reply_text(
            f"❌ Jogador '{target_input}' não encontrado.\n"
            "Tente verificar se há caracteres especiais ou use o **User ID** numérico.",
            parse_mode="Markdown"
        )
        return ASK_TARGET_PLAYER

    user_id, pdata = found_player
    
    context.user_data['gem_target_id'] = user_id
    context.user_data['gem_target_name'] = pdata.get('character_name', f"ID: {user_id}")
    
    char_name = context.user_data['gem_target_name']
    
    await update.message.reply_text(
        f"✅ Jogador selecionado: **{char_name}** (`{user_id}`).\n\n"
        "Agora, envie a **quantidade** de gemas que deseja entregar.",
        parse_mode="Markdown"
    )
    
    return ASK_QUANTITY

async def receive_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe a quantidade, mostra o resumo e pede confirmação."""
    try:
        quantity = int(update.message.text.strip())
        if quantity <= 0:
            raise ValueError("A quantidade deve ser positiva.")
    except ValueError:
        await update.message.reply_text("❌ Quantidade inválida. Por favor, envie um número inteiro e positivo.")
        return ASK_QUANTITY
        
    context.user_data['gem_quantity'] = quantity
    target_name = context.user_data['gem_target_name']
    user_id = context.user_data['gem_target_id']
    
    summary_text = (
        f"**Resumo da Entrega:**\n\n"
        f"🔹 **Item:** 💎 Gemas\n"
        f"🔹 **Quantidade:** {quantity}\n"
        f"🔹 **Para:** {target_name} (`{user_id}`)\n\n"
        f"Você confirma a entrega?"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Sim, entregar", callback_data="gem_confirm_yes"),
            InlineKeyboardButton("❌ Não, cancelar", callback_data="gem_confirm_no")
        ]
    ]
    
    await update.message.reply_text(summary_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    return CONFIRM_GRANT

async def dispatch_grant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Executa a entrega das gemas e notifica o jogador."""
    query = update.callback_query
    await query.answer()

    user_id = context.user_data['gem_target_id']
    quantity = context.user_data['gem_quantity']
    target_name = context.user_data['gem_target_name']
    
    # Carrega dados
    pdata = await player_manager.get_player_data(user_id)
    
    if not pdata:
        await query.edit_message_text(f"❌ Erro crítico! Não foi possível carregar os dados de {target_name} para a entrega.")
        context.user_data.clear()
        return ConversationHandler.END

    # Adiciona Gemas
    player_manager.add_gems(pdata, quantity)
    
    # Salva
    await player_manager.save_player_data(user_id, pdata)
    
    # Confirmação Admin
    await query.edit_message_text(f"✅ Sucesso! {quantity} 💎 Gemas foram entregues a {target_name}.")
    
    # Notificação ao Jogador
    try:
        notification_text = f"🎉 Boas notícias! Você acaba de adquirir **{quantity}** 💎 Gemas!"
        await context.bot.send_message(
            chat_id=user_id,
            text=notification_text,
            parse_mode="Markdown"
        )
    except Forbidden:
        print(f"AVISO: Não foi possível notificar o jogador {user_id} (Bloqueado).")
    except Exception as e:
        print(f"ERRO: Falha ao enviar notificação para o jogador {user_id}. Erro: {e}")

    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a conversa a qualquer momento."""
    message_text = "Operação cancelada."
    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(message_text)
        except:
            pass
    elif update.message:
        await update.message.reply_text(message_text)
        
    context.user_data.clear()
    return ConversationHandler.END

# --- O Handler da Conversa ---
sell_gems_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_sell, pattern=r"^admin_sell_gems$")],
    states={
        ASK_TARGET_PLAYER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_target_player)],
        ASK_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_quantity)],
        CONFIRM_GRANT: [
            CallbackQueryHandler(dispatch_grant, pattern=r"^gem_confirm_yes$"),
            CallbackQueryHandler(cancel, pattern=r"^gem_confirm_no$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancelar", cancel),
        CallbackQueryHandler(cancel, pattern=r"^grant_cancel$")
    ],
)