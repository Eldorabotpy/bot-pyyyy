# handlers/npc_handler.py (VERSÃO FINAL E COMPLETA)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, game_data
from modules import file_ids as file_id_manager
# Importa a variável das receitas de troca
from modules.game_data.npc_trades import NPC_TRADES

logger = logging.getLogger(__name__)

async def npc_trade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Mostra o menu de trocas para um NPC específico, com o layout corrigido.
    """
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    try:
        npc_id = query.data.split(':')[1]
    except IndexError:
        await context.bot.send_message(chat_id=chat_id, text="Erro: NPC não encontrado.")
        return

    # <<< CORREÇÃO 1: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)
    # Verifica se player_data foi carregado
    if not player_data:
         logger.warning(f"npc_trade_callback: Player data not found for user {user_id}")
         await context.bot.send_message(chat_id=chat_id, text="Erro ao carregar seus dados. Use /start.")
         return

    # Lógica síncrona para obter dados do NPC e construir mensagem/teclado
    npc_info = NPC_TRADES.get(npc_id, {})
    npc_trades = npc_info.get('trades', {})

    if not npc_trades:
        await context.bot.send_message(chat_id=chat_id, text="Este NPC não tem nada para trocar no momento.")
        # Adiciona botão de voltar mesmo se não houver trocas
        keyboard_empty = [[InlineKeyboardButton("⬅️ Voltar à Região", callback_data=f"open_region:{player_data.get('current_location')}")]]
        # Tenta editar a mensagem anterior se possível
        try:
             await query.edit_message_text("Este NPC não tem nada para trocar no momento.", reply_markup=InlineKeyboardMarkup(keyboard_empty))
        except Exception:
             await context.bot.send_message(chat_id=chat_id, text="Este NPC não tem nada para trocar no momento.", reply_markup=InlineKeyboardMarkup(keyboard_empty))
        return

    intro_message = npc_info.get('intro_message', "'Vê os meus produtos.'")
    caption_parts = [ f"📜 <b>{npc_info.get('display_name', 'Mercador')}</b>", f"\n{intro_message}\n" ]
    keyboard = []

    for item_id_output, costs in npc_trades.items():
        caption_parts.append("──────────")
        output_info = game_data.ITEMS_DATA.get(item_id_output, {})
        output_name = output_info.get('display_name', item_id_output)
        output_emoji = output_info.get('emoji', '✨')
        caption_parts.append(f"<b>Troca por:</b> {output_emoji} {output_name}\n")
        caption_parts.append(f"<b>Custo:</b>")
        ingredients = costs.get('items', {})
        gold_cost = costs.get('gold', 0)
        for item_id_input, qty in ingredients.items():
            input_info = game_data.ITEMS_DATA.get(item_id_input, {})
            input_name = input_info.get('display_name', item_id_input)
            has_item = player_manager.has_item(player_data, item_id_input, qty) # Síncrono
            emoji = "✅" if has_item else "❌"
            caption_parts.append(f"{emoji} {qty}x {input_name}")
        if gold_cost > 0:
            has_gold = player_manager.get_gold(player_data) >= gold_cost # Síncrono
            gold_emoji = "✅" if has_gold else "❌"
            caption_parts.append(f"{gold_emoji} {gold_cost:,} Ouro") # Adiciona formatação de milhar
        caption_parts.append("")
        keyboard.append([InlineKeyboardButton(f"Trocar por {output_name}", callback_data=f"npc_confirm:{npc_id}:{item_id_output}")])

    caption = "\n".join(caption_parts)
    keyboard.append([InlineKeyboardButton("⬅️ Voltar à Região", callback_data=f"open_region:{player_data.get('current_location')}")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Lógica de envio de mídia (síncrono + async)
    media_key = npc_info.get("media_key", f"npc_{npc_id}_media") # Usa media_key do NPC_TRADES se existir
    file_data = file_id_manager.get_file_data(media_key)

    try: await query.delete_message()
    except Exception as e: logger.info(f"Não foi possível apagar mensagem anterior no menu NPC: {e}")

    # As chamadas send_* já usam await
    if file_data and file_data.get("id"):
        media_id = file_data["id"]
        media_type = (file_data.get("type") or "photo").lower()
        try:
            if media_type in ("video", "animation"): await context.bot.send_animation(chat_id=chat_id, animation=media_id, caption=caption, reply_markup=reply_markup, parse_mode='HTML')
            else: await context.bot.send_photo(chat_id=chat_id, photo=media_id, caption=caption, reply_markup=reply_markup, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Falha ao enviar mídia do NPC '{media_key}': {e}. Usando fallback.")
            await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode='HTML')

async def npc_trade_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Executa a troca de itens com o NPC."""
    query = update.callback_query

    try:
        _, npc_id, item_id_output = query.data.split(':')
    except ValueError:
        await query.answer("Erro no callback da troca.", show_alert=True)
        return

    user_id = query.from_user.id
    # <<< CORREÇÃO 2: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)
    # Verifica se player_data foi carregado
    if not player_data:
         logger.warning(f"npc_trade_confirm_callback: Player data not found for user {user_id}")
         await query.answer("Erro ao carregar seus dados. Use /start.", show_alert=True)
         return

    # Lógica síncrona
    trade_info = NPC_TRADES.get(npc_id, {}).get('trades', {}).get(item_id_output)
    if not trade_info:
        await query.answer("Esta troca já não está disponível.", show_alert=True)
        return

    ingredients = trade_info.get('items', {})
    gold_cost = trade_info.get('gold', 0)

    # Verificações síncronas
    for item_id, qty in ingredients.items():
        if not player_manager.has_item(player_data, item_id, qty):
            await query.answer("Materiais insuficientes!", show_alert=True)
            return
    if player_manager.get_gold(player_data) < gold_cost:
        await query.answer("Ouro insuficiente!", show_alert=True)
        return

    # Modificações síncronas locais
    for item_id, qty in ingredients.items():
        player_manager.remove_item_from_inventory(player_data, item_id, qty)
    player_manager.spend_gold(player_data, gold_cost)
    player_manager.add_item_to_inventory(player_data, item_id_output, 1)

    # <<< CORREÇÃO 3: Adiciona await >>>
    await player_manager.save_player_data(user_id, player_data)

    output_name = game_data.ITEMS_DATA.get(item_id_output, {}).get('display_name', item_id_output)
    await query.answer(f"✅ Troca bem-sucedida! Você obteve 1x {output_name}.", show_alert=True)

    # <<< CORREÇÃO 4: Adiciona await >>>
    await npc_trade_callback(update, context) # Chama a função async que redesenha o menu

# --- REGISTO DOS HANDLERS ---
npc_trade_handler = CallbackQueryHandler(npc_trade_callback, pattern=r"^npc_trade:.*$")
npc_trade_confirm_handler = CallbackQueryHandler(npc_trade_confirm_callback, pattern=r"^npc_confirm:.*$")
all_npc_handlers = [npc_trade_handler, npc_trade_confirm_handler]