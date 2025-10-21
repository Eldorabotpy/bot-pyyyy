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

    player_data = player_manager.get_player_data(user_id)
    npc_info = NPC_TRADES.get(npc_id, {})
    npc_trades = npc_info.get('trades', {})

    if not npc_trades:
        await context.bot.send_message(chat_id=chat_id, text="Este NPC não tem nada para trocar no momento.")
        return

    intro_message = npc_info.get('intro_message', "'Vê os meus produtos.'")
    
    # --- LÓGICA DE MONTAGEM DA MENSAGEM CORRIGIDA ---
    caption_parts = [
        f"📜 <b>{npc_info.get('display_name', 'Mercador')}</b>",
        f"\n{intro_message}\n"
    ]
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
        
        # Adiciona cada ingrediente numa nova linha
        for item_id_input, qty in ingredients.items():
            input_info = game_data.ITEMS_DATA.get(item_id_input, {})
            input_name = input_info.get('display_name', item_id_input)
            has_item = player_manager.has_item(player_data, item_id_input, qty)
            emoji = "✅" if has_item else "❌"
            caption_parts.append(f"{emoji} {qty}x {input_name}")
        
        # Adiciona o custo em ouro numa nova linha
        if gold_cost > 0:
            has_gold = player_manager.get_gold(player_data) >= gold_cost
            gold_emoji = "✅" if has_gold else "❌"
            caption_parts.append(f"{gold_emoji} {gold_cost} Ouro")
        
        caption_parts.append("") # Adiciona uma linha em branco para espaçamento
        
        keyboard.append([InlineKeyboardButton(f"Trocar por {output_name}", callback_data=f"npc_confirm:{npc_id}:{item_id_output}")])

    caption = "\n".join(caption_parts)
    # --- FIM DA LÓGICA ---

    keyboard.append([InlineKeyboardButton("⬅️ Voltar à Região", callback_data=f"open_region:{player_data.get('current_location')}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    media_key = "npc_alquimista_tenda_media"
    file_data = file_id_manager.get_file_data(media_key)
    
    try:
        await query.delete_message()
    except Exception as e:
        logger.info(f"Não foi possível apagar mensagem anterior no menu NPC: {e}")

    if file_data and file_data.get("id"):
        media_id = file_data["id"]
        media_type = (file_data.get("type") or "photo").lower()
        try:
            if media_type in ("video", "animation"):
                await context.bot.send_animation(chat_id=chat_id, animation=media_id, caption=caption, reply_markup=reply_markup, parse_mode='HTML')
            else:
                await context.bot.send_photo(chat_id=chat_id, photo=media_id, caption=caption, reply_markup=reply_markup, parse_mode='HTML')
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
    player_data = player_manager.get_player_data(user_id)
    
    trade_info = NPC_TRADES.get(npc_id, {}).get('trades', {}).get(item_id_output)
    if not trade_info:
        await query.answer("Esta troca já não está disponível.", show_alert=True)
        return
    
    ingredients = trade_info.get('items', {})
    gold_cost = trade_info.get('gold', 0)
        
    for item_id, qty in ingredients.items():
        if not player_manager.has_item(player_data, item_id, qty):
            await query.answer("Materiais insuficientes!", show_alert=True)
            return
            
    if player_manager.get_gold(player_data) < gold_cost:
        await query.answer("Ouro insuficiente!", show_alert=True)
        return

    for item_id, qty in ingredients.items():
        player_manager.remove_item_from_inventory(player_data, item_id, qty)
    player_manager.spend_gold(player_data, gold_cost)
    
    player_manager.add_item_to_inventory(player_data, item_id_output, 1)
    player_manager.save_player_data(user_id, player_data)
    
    output_name = game_data.ITEMS_DATA.get(item_id_output, {}).get('display_name', item_id_output)
    await query.answer(f"✅ Troca bem-sucedida! Você obteve 1x {output_name}.", show_alert=True)
    await npc_trade_callback(update, context)


# --- REGISTO DOS HANDLERS ---
npc_trade_handler = CallbackQueryHandler(npc_trade_callback, pattern=r"^npc_trade:.*$")
npc_trade_confirm_handler = CallbackQueryHandler(npc_trade_confirm_callback, pattern=r"^npc_confirm:.*$")
all_npc_handlers = [npc_trade_handler, npc_trade_confirm_handler]