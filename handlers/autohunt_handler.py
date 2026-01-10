# handlers/autohunt_handler.py
# (VERSÃO CORRIGIDA: Validação de Tier + Popup de Energia)

import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

# Imports do Sistema
from modules import auto_hunt_engine
from modules import file_ids as file_id_manager
from modules import player_manager
from modules.auth_utils import get_current_player_id

# Tenta importar PremiumManager com segurança
try:
    from modules.player.premium import PremiumManager 
except ImportError:
    PremiumManager = None

logger = logging.getLogger(__name__)

# --- CONFIGURAÇÃO DE LIMITES POR TIER ---
TIER_LIMITS = {
    "free": 0,       # Free não caça automático
    "premium": 10,   # 10x
    "vip": 25,       # 25x
    "lenda": 35,     # 35x
    "admin": 100     # Admin (opcional)
}

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
        
        requested_count = int(parts[0])
        region_key = parts[1]
    except ValueError:
        await query.answer("❌ Erro nos dados do botão.", show_alert=True)
        return

    # 3. Carrega Jogador
    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return

    # --- VALIDAÇÃO DE TIER E LIMITES ---
    user_tier = str(player_data.get("premium_tier", "free")).lower()
    
    # Se tiver PremiumManager, confirma se não expirou
    if PremiumManager:
        pm = PremiumManager(player_data)
        if not pm.is_premium() and user_tier != "admin":
            user_tier = "free"

    allowed_count = TIER_LIMITS.get(user_tier, 0)

    # 1. Verifica se pode caçar
    if allowed_count <= 0:
        await query.answer("🔒 Recurso exclusivo para Premium, VIP ou Lenda.", show_alert=True)
        return

    # 2. Verifica se está tentando fazer mais do que o plano permite
    if requested_count > allowed_count and user_tier != "admin":
        msg_erro = (
            f"🚫 Seu plano ({user_tier.capitalize()}) permite máximo de {allowed_count}x.\n\n"
            "Faça um upgrade para aumentar o limite!"
        )
        await query.answer(msg_erro, show_alert=True)
        return

    # --- VALIDAÇÃO DE ENERGIA (POPUP) ---
    # Custo: 1 energia por caçada
    total_cost = requested_count
    current_energy = int(player_data.get("energy", 0))

    if current_energy < total_cost:
        # ✅ AQUI ESTÁ O POPUP COM O BOTÃO OK
        await query.answer(
            f"🚫 Você não tem energia suficiente!\n\n"
            f"Necessário: {total_cost} ⚡\n"
            f"Atual: {current_energy} ⚡",
            show_alert=True
        )
        return

    # 4. LIMPEZA E VISUAL
    try:
        await query.message.delete() # Apaga o menu antigo
    except Exception:
        pass 

    # Prepara a mensagem de "Viajando..."
    region_name = region_key.replace('_', ' ').title()
    duration_min = (requested_count * 30) / 60 # 30s por mob

    caption_text = (
        f"⏱ <b>Caçada Rápida Iniciada!</b>\n"
        f"⚔️ Simulando <b>{requested_count} combates</b> em <b>{region_name}</b>...\n\n"
        f"⚡ Custo: {total_cost} energia\n"
        f"⏳ Tempo: {duration_min:.1f} minutos.\n\n"
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
            sent_msg = await context.bot.send_message(
                chat_id=chat_id, text=caption_text, parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Erro visual autohunt: {e}")
        try:
            sent_msg = await context.bot.send_message(query.message.chat_id, f"🌲 Iniciando caçada em {region_name}...")
        except: pass

    # 5. PASSA PARA A ENGINE
    msg_id = sent_msg.message_id if sent_msg else None
    
    # Chama a função Start da Engine (Backend)
    await auto_hunt_engine.start_auto_hunt(
        update, 
        context, 
        requested_count, 
        region_key, 
        message_id_override=msg_id 
    )

autohunt_start_handler = CallbackQueryHandler(_autohunt_button_parser, pattern=r'^autohunt_start_')