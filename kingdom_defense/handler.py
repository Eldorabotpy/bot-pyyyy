# Arquivo: kingdom_defense/handler.py (versão final e completa)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes, CallbackQueryHandler
from .engine import event_manager
from modules import player_manager
import asyncio

logger = logging.getLogger(__name__)

ID_GRUPO_EVENTOS = -1002881364171  
ID_TOPICO_EVENTOS = 10340


def _get_battle_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("💥 ATACAR 💥", callback_data='kd_attack_wave')],
        [InlineKeyboardButton("📊 Status", callback_data='kd_show_status'),
         InlineKeyboardButton("🏆 Ranking", callback_data='kd_show_leaderboard')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_event_from_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Iniciando evento...")
    
    result = event_manager.start_event()

    if "message" in result and "já está ativo" in result["message"]:
        await query.answer(result["message"], show_alert=True)
        return

    message = None
    file_id, media_type = result.get("file_id"), result.get("media_type")
    caption, text = result.get("caption"), result.get("text")
    keyboard = _get_battle_keyboard()

    try:
        if file_id:
            send_func = context.bot.send_animation if media_type == 'animation' else context.bot.send_photo
            message = await send_func(
                chat_id=ID_GRUPO_EVENTOS,
                photo=file_id, animation=file_id, caption=caption,
                reply_markup=keyboard, parse_mode="HTML",
                message_thread_id=ID_TOPICO_EVENTOS
            )
    except Exception as e:
        logger.error(f"Falha ao enviar mídia no início do evento: {e}")
            
    if not message:
        message = await context.bot.send_message(
            chat_id=ID_GRUPO_EVENTOS,
            text=text or caption or "O evento começou!",
            reply_markup=keyboard, parse_mode="HTML",
            message_thread_id=ID_TOPICO_EVENTOS
        )
    
    if message:
        event_manager.set_battle_message_info(message.message_id, message.chat.id)
        logger.info(f"Evento iniciado. Msg ID: {message.message_id} no Chat ID: {message.chat.id}")
    
    await query.delete_message()

async def show_event_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    caption = "📢 **ALERTA DE INVASÃO!**\n\nHordas de monstros se aproximam do reino. Você irá atender ao chamado para defender Eldora?" if event_manager.is_active else "Não há nenhuma invasão acontecendo no momento."
    keyboard = [
        [InlineKeyboardButton("⚔️ PARTICIPAR DA DEFESA ⚔️", callback_data='kd_join_event')],
        [InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data='go_to_kingdom')]
    ] if event_manager.is_active else [[InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data='go_to_kingdom')]]
    
    await query.edit_message_text(text=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def join_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    player_data = player_manager.get_player_data(user_id)

    if not player_manager.has_item(player_data, 'ticket_defesa_reino'):
        await query.answer("Você precisa de um Ticket de Defesa do Reino para participar!", show_alert=True)
        return
    
    player_manager.remove_item_from_inventory(player_data, 'ticket_defesa_reino', 1)

    if event_manager.add_participant(user_id, player_data):
        player_manager.save_player_data(user_id, player_data)
        await query.answer("Você se juntou à defesa de Eldora! Boa sorte!", show_alert=True)
        await query.delete_message()

        msg_info = event_manager.get_battle_message_info()
        chat_id, msg_id = msg_info.get('chat_id'), msg_info.get('id')

        if not chat_id:
            logger.warning("Não foi possível encontrar o chat_id do evento para enviar a confirmação.")
            return

        chat_id_num = str(chat_id).replace("-100", "")
        msg_link = f"https://t.me/c/{chat_id_num}/{msg_id}"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Ir para a Batalha! 🚀", url=msg_link)]])
        
        player_name = player_data.get('character_name', 'Um herói')
        conf_text = f"⚔️ <b>{player_name}</b> atendeu ao chamado e se juntou à defesa de Eldora!"
        
        await context.bot.send_message(
            chat_id=ID_GRUPO_EVENTOS, text=conf_text, reply_markup=keyboard,
            parse_mode='HTML', message_thread_id=ID_TOPICO_EVENTOS
        )
    else:
        player_manager.add_item_to_inventory(player_data, 'ticket_defesa_reino', 1)
        await query.answer("Não foi possível entrar na defesa no momento. Tente novamente.", show_alert=True)

async def attack_wave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    player_data = player_manager.get_player_data(user_id)

    if not player_data:
        await query.answer("Erro ao encontrar seus dados!", show_alert=True)
        return
    
    result = event_manager.process_attack(user_id, player_data)
    
    if private_message := result.get("private_message"):
        await query.answer(private_message, show_alert=True)
        return
    
    if result.get("event_over"):
        await query.answer("A batalha terminou!")
        await _handle_event_end(update, context, result)
        return

    await query.answer("Ataque realizado!")

    msg_info = event_manager.get_battle_message_info()
    msg_id, chat_id = msg_info.get('id'), msg_info.get('chat_id')
    
    if not msg_id or not chat_id:
        logger.warning("Não foi encontrado um ID/CHAT_ID de mensagem de batalha para atualizar.")
        return

    try:
        if caption := result.get("caption"):
            await context.bot.edit_message_caption(
                chat_id=chat_id, message_id=msg_id, caption=caption, 
                parse_mode="HTML", reply_markup=_get_battle_keyboard()
            )
        elif text := result.get("text"):
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=msg_id, text=text, 
                parse_mode="HTML", reply_markup=_get_battle_keyboard()
            )
    except Exception as e:
        logger.error(f"Falha ao editar mensagem de batalha: {e}")

async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer(text=event_manager.get_battle_status_text(), show_alert=True)

async def _handle_event_end(update: Update, context: ContextTypes.DEFAULT_TYPE, result: dict):
    msg_info = event_manager.get_battle_message_info()
    msg_id, chat_id = msg_info.get('id'), msg_info.get('chat_id')
    
    final_caption = result.get("final_caption", "A batalha chegou ao fim.")
    final_file_id = result.get("final_file_id")

    rewards_log = []
    if rewards := result.get("rewards"):
        for uid_str, u_rewards in rewards.items():
            uid_int = int(uid_str)
            p_data = player_manager.get_player_data(uid_int)
            p_name = p_data.get('character_name', f"Jogador {uid_int}")
            
            r_texts = [f"{q}x {i}" for i, q in u_rewards.items()]
            for item, quantity in u_rewards.items():
                player_manager.add_item_to_inventory(p_data, item, quantity)
            
            player_manager.save_player_data(uid_int, p_data)
            rewards_log.append(f"🎖️ {p_name} recebeu: {', '.join(r_texts)}")

    if rewards_log: final_caption += "\n\n<b>Recompensas:</b>\n" + "\n".join(rewards_log)

    try:
        if final_file_id and msg_id:
             media = InputMediaPhoto(media=final_file_id, caption=final_caption, parse_mode="HTML")
             await context.bot.edit_message_media(chat_id=chat_id, message_id=msg_id, media=media)
        elif msg_id:
             await context.bot.edit_message_caption(chat_id=chat_id, message_id=msg_id, caption=final_caption, parse_mode="HTML", reply_markup=None)
        elif chat_id: await context.bot.send_message(chat_id=chat_id, text=final_caption, parse_mode="HTML", message_thread_id=ID_TOPICO_EVENTOS)
    except Exception as e:
        logger.error(f"Falha ao editar mensagem de final de evento: {e}")
        if chat_id: await context.bot.send_message(chat_id=chat_id, text=final_caption, parse_mode="HTML", message_thread_id=ID_TOPICO_EVENTOS)

    event_manager.end_event()

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer(text=event_manager.get_leaderboard_text(), show_alert=True)

async def delete_message_after(message, seconds):
    """Espera um tempo e depois apaga uma mensagem."""
    await asyncio.sleep(seconds)
    try:
        await message.delete()
    except Exception as e:
        logger.info(f"Não foi possível apagar a mensagem temporária: {e}")

# --- REGISTRO DOS HANDLERS ---

def register_handlers(application):
    patterns = {
        'show_events_menu': show_event_menu,
        'kd_join_event': join_event,
        'kd_attack_wave': attack_wave,
        'kd_show_status': show_status,
        'kd_show_leaderboard': show_leaderboard
    }
    for pattern, handler in patterns.items():
        application.add_handler(CallbackQueryHandler(handler, pattern=f'^{pattern}$'))