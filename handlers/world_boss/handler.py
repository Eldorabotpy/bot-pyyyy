# handlers/world_boss/handler.py (VERSÃO FINAL COM LOOT)

import logging
import time 
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

# <<< MUDANÇA: Importa a função de LOOT >>>
from .engine import world_boss_manager, BOSS_STATS, broadcast_boss_announcement, distribute_loot_and_announce

from modules import game_data
from modules import player_manager

logger = logging.getLogger(__name__)

ADMIN_IDS = [7262799478]

# --- COMANDO DE ADMIN ---
async def iniciar_worldboss_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Você não tem permissão para usar este comando.")
        return

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

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await query.answer("Não foi possível encontrar os teus dados de jogador.", show_alert=True)
        return

    result = await world_boss_manager.process_attack(user_id, player_data)

    if "error" in result:
        await query.answer(result["error"], show_alert=True)
        return

    await query.answer(result.get("log", "Você ataca!"), cache_time=1)

    # --- 👇 MUDANÇA PRINCIPAL (LÓGICA DE LOOT) 👇 ---
    if result.get("boss_defeated"):
        await query.edit_message_caption(
            caption="🎉 **O DEMÔNIO DIMENSIONAL FOI DERROTADO!** 🎉\n\nO reino agradece a vossa bravura! A processar recompensas...",
            reply_markup=None # Remove os botões
        )
        
        # Chama a função de loot do engine.py
        battle_results = result.get("battle_results", {})
        await distribute_loot_and_announce(context, battle_results)
        return
    # --- 👆 FIM DA MUDANÇA 👆 ---

    # Se a batalha continua, atualiza o menu
    new_caption = (
        f"‼️ **PERIGO IMINENTE** ‼️\n\n"
        f"O **Demônio Dimensional** está nesta região!\n\n"
        f"{world_boss_manager.get_status_text()}"
    )
    keyboard = [
        [InlineKeyboardButton("⚔️ ATACAR O DEMÔNIO ⚔️", callback_data='wb_attack')],
        [InlineKeyboardButton("👤 Personagem", callback_data='profile')],
        [InlineKeyboardButton("🗺️ Ver Mapa", callback_data='travel')]
    ]
    try:
        await query.edit_message_caption(caption=new_caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e).lower():
            logger.info(f"Não foi possível editar a mensagem do World Boss: {e}")

# --- REGISTO DOS HANDLERS ---
world_boss_admin_handler = CommandHandler("iniciar_worldboss", iniciar_worldboss_command)
world_boss_attack_handler = CallbackQueryHandler(world_boss_attack_callback, pattern=r'^wb_attack$')

all_world_boss_handlers = [world_boss_admin_handler, world_boss_attack_handler]