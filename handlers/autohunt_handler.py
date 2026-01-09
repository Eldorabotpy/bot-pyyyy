# handlers/autohunt_handler.py
# (FRONTEND: Visual, Mídia e Botões)

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler

# Imports do Sistema
from modules import auto_hunt_engine
from modules import file_ids as file_id_manager
from modules import player_manager
from modules.auth_utils import get_current_player_id
from modules.player.premium import PremiumManager 

logger = logging.getLogger(__name__)

async def _autohunt_button_parser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # 1. Recupera ID e valida sessão
    user_id = get_current_player_id(update, context)
    if not user_id:
        await query.answer("⚠️ Sessão expirada.", show_alert=True)
        return

    # 2. Parse dos dados (Ex: autohunt_start_10_floresta)
    try:
        data = query.data.replace("autohunt_start_", "")
        parts = data.split("_", 1)
        if len(parts) < 2: raise ValueError("Dados incompletos")
        
        hunt_count = int(parts[0])
        region_key = parts[1]
    except ValueError:
        await query.answer("❌ Erro nos dados do botão.", show_alert=True)
        return

    # 3. Validações Prévias (Energia/VIP) antes de apagar o menu
    # Isso evita apagar o menu se o cara não puder caçar
    player_data = await player_manager.get_player_data(user_id)
    if not PremiumManager(player_data).is_premium():
        await query.answer("🔒 Exclusivo para Premium/VIP.", show_alert=True)
        return

    # 4. LIMPEZA E VISUAL (Aqui garantimos o visual correto)
    try:
        await query.message.delete() # Apaga o menu antigo
    except Exception:
        pass 

    # Prepara a mensagem de "Viajando..."
    region_name = region_key.replace('_', ' ').title()
    cost = hunt_count # Assumindo custo base 1
    duration = hunt_count * 0.5 # 30s por mob = 0.5 min

    caption_text = (
        f"⏱ <b>Caçada Rápida Iniciada!</b>\n"
        f"⚔️ Simulando <b>{hunt_count} combates</b> em <b>{region_name}</b>...\n\n"
        f"⚡ Custo: {cost} energia\n"
        f"⏳ Tempo: {duration:.1f} minutos.\n\n"
        f"<i>O relatório chegará automaticamente.</i>"
    )

    sent_msg = None
    try:
        # Busca Mídia (Prioridade: Região -> Padrão)
        media_key = f"hunt_{region_key}"
        file_data = file_id_manager.get_file_data(media_key)
        
        if not file_data:
            file_data = file_id_manager.get_file_data("autohunt_start_media")

        chat_id = query.message.chat_id

        # Envia VIDEO ou FOTO
        if file_data and file_data.get('id'):
            media_id = file_data['id']
            media_type = file_data.get('type', 'photo')

            if media_type in ['video', 'animation']:
                sent_msg = await context.bot.send_video(
                    chat_id=chat_id, video=media_id, caption=caption_text, parse_mode="HTML"
                )
            else:
                sent_msg = await context.bot.send_photo(
                    chat_id=chat_id, photo=media_id, caption=caption_text, parse_mode="HTML"
                )
        else:
            # Fallback texto
            sent_msg = await context.bot.send_message(
                chat_id=chat_id, text=caption_text, parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Erro visual autohunt: {e}")
        # Se der erro na mídia, manda texto simples para não travar
        try:
            sent_msg = await context.bot.send_message(query.message.chat_id, f"🌲 Iniciando caçada em {region_name}...")
        except: pass

    # 5. PASSA PARA A ENGINE (Com o ID da mensagem para deletar depois)
    msg_id = sent_msg.message_id if sent_msg else None
    
    # Chama a função Start da Engine (Backend)
    # Note que passamos message_id_override=msg_id
    await auto_hunt_engine.start_auto_hunt(
        update, 
        context, 
        hunt_count, 
        region_key, 
        message_id_override=msg_id 
    )

autohunt_start_handler = CallbackQueryHandler(_autohunt_button_parser, pattern=r'^autohunt_start_')