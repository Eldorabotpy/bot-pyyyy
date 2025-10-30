# handlers/world_boss/handler.py (VERSÃO FINAL E COMPLETA)

import logging
import time 
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from .engine import world_boss_manager, BOSS_STATS, broadcast_boss_announcement
from modules import game_data
# Importa o nosso "motor" do evento e as stats do boss
from .engine import world_boss_manager, BOSS_STATS

# Importa o player_manager para obter os dados do jogador
from modules import player_manager

logger = logging.getLogger(__name__)

# --- CONFIGURAÇÃO DE ADMIN ---
ADMIN_IDS = [7262799478] # Coloca aqui os teus IDs de admin

# --- COMANDO DE ADMIN (já existe) ---
async def iniciar_worldboss_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Você não tem permissão para usar este comando.")
        return

    # start_event é síncrono (altera o estado do manager)
    result = world_boss_manager.start_event()
    if "error" in result:
        await update.message.reply_text(f"⚠️ Erro: {result['error']}")
    else:
        location_name = (game_data.REGIONS_DATA.get(result['location']) or {}).get("display_name", result['location'])
        await update.message.reply_text(
            f"✅ Evento do Demônio Dimensional iniciado com sucesso!\n"
            f"O boss apareceu em: <b>{location_name}</b>.\n\n"
            f"A enviar anúncio global...",
            parse_mode='HTML'
        )

        # <<< CORREÇÃO 1: Adiciona await >>>
        # broadcast_boss_announcement é async pois envia mensagens
        await broadcast_boss_announcement(context.application, result["location"])

async def world_boss_attack_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Função chamada quando o jogador clica no botão 'ATACAR O DEMÔNIO'.
    """
    query = update.callback_query
    user_id = query.from_user.id

    # --- Trava de ataque (cooldown) ---
    now = time.time()
    last_attack = context.user_data.get('wb_last_attack_time', 0)
    if now - last_attack < 3.0: # 3 segundos de cooldown
        await query.answer("Você está a atacar muito rápido! Aguarde um momento.", cache_time=1)
        return
    context.user_data['wb_last_attack_time'] = now

    # <<< CORREÇÃO 2: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await query.answer("Não foi possível encontrar os teus dados de jogador.", show_alert=True)
        return

    # Processa o ataque usando o nosso engine (process_attack é síncrono)
    result = world_boss_manager.process_attack(user_id, player_data)

    # Dá feedback ao jogador sobre o resultado do ataque
    if "error" in result:
        await query.answer(result["error"], show_alert=True)
        return

    # Mostra o log de dano
    await query.answer(result.get("log", "Você ataca!"), cache_time=1)

    # Se o boss foi derrotado com este ataque
    if result.get("boss_defeated"):
        await query.edit_message_caption(
            caption="🎉 **O DEMÔNIO DIMENSIONAL FOI DERROTADO!** 🎉\n\nO reino agradece a vossa bravura! As recompensas serão distribuídas em breve.",
            reply_markup=None # Remove os botões
        )
        # TODO: Enviar anúncio global de vitória e distribuir recompensas
        return

    # Se a batalha continua, atualiza o menu com o novo HP do boss
    new_caption = (
        f"‼️ **PERIGO IMINENTE** ‼️\n\n"
        f"O **Demônio Dimensional** está nesta região!\n\n"
        f"{world_boss_manager.get_status_text()}" # Pega o status atualizado (síncrono)
    )
    keyboard = [
        [InlineKeyboardButton("⚔️ ATACAR O DEMÔNIO ⚔️", callback_data='wb_attack')],
        [InlineKeyboardButton("👤 Personagem", callback_data='profile')],
        [InlineKeyboardButton("🗺️ Ver Mapa", callback_data='travel')]
    ]
    try:
        await query.edit_message_caption(caption=new_caption, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.info(f"Não foi possível editar a mensagem do World Boss: {e}")

# --- REGISTO DOS HANDLERS (ATUALIZADO) ---
# Exportamos uma lista com todos os handlers deste módulo para facilitar o registo
world_boss_admin_handler = CommandHandler("iniciar_worldboss", iniciar_worldboss_command)
world_boss_attack_handler = CallbackQueryHandler(world_boss_attack_callback, pattern=r'^wb_attack$')

all_world_boss_handlers = [world_boss_admin_handler, world_boss_attack_handler]