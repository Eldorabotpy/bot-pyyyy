# handlers/world_boss/handler.py

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

# --- IMPORTS ---
from .engine import world_boss_manager, distribute_loot_and_announce, broadcast_boss_announcement
from modules import player_manager
from modules import file_ids # <--- IMPORTAMOS SEU GERENCIADOR AQUI

logger = logging.getLogger(__name__)

# Chave da imagem no seu banco de dados (file_ids.json/mongo)
BOSS_IMAGE_KEY = "boss_raid" 

# --- COMANDO DE ADMIN PARA INICIAR ---
async def iniciar_worldboss_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Substitua pelo seu ID de Admin ou remova a verificação para testar
    ADMIN_IDS = [7262799478] 
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Apenas admins podem invocar o Demônio.")
        return

    result = world_boss_manager.start_event()
    if "error" in result:
        await update.message.reply_text(f"⚠️ {result['error']}")
    else:
        # Busca o ID da imagem usando seu módulo file_ids
        media_id = file_ids.get_file_id(BOSS_IMAGE_KEY)
        
        caption = (
            f"🚨 <b>RAID INICIADA!</b> 🚨\n\n"
            f"O Demônio Dimensional apareceu em: <b>{result['location']}</b>!\n"
            f"Use /worldboss ou vá até o local para lutar!"
        )
        
        # Anúncio Global (Envia imagem se tiver, senão texto)
        await broadcast_boss_announcement(context.application, result["location"])
        
        # Feedback para o admin
        if media_id:
            await update.message.reply_photo(photo=media_id, caption="✅ Evento iniciado com sucesso!")
        else:
            await update.message.reply_text("✅ Evento iniciado! (Sem imagem configurada na chave 'boss_raid')")


async def world_boss_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe o menu principal do Boss (HUD e Botões)."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    if not query:
        chat_id = update.effective_chat.id
    else:
        chat_id = query.message.chat_id
        await query.answer()
    
    # 1. Verifica estado
    if not world_boss_manager.state["is_active"]:
        msg = "O evento do World Boss terminou ou não está ativo no momento."
        if query: await query.edit_message_caption(msg)
        else: await context.bot.send_message(chat_id, msg)
        return

    # 2. HUD
    hud_text = await world_boss_manager.get_battle_hud()
    
    # 3. Botões
    ents = world_boss_manager.state["entities"]
    keyboard = []
    
    # Linha 1: Bruxas
    witches_row = []
    if ents["witch_heal"]["alive"]:
        witches_row.append(InlineKeyboardButton("🔮 Bruxa Cura", callback_data='wb_atk:witch_heal'))
    if ents["witch_buff"]["alive"]:
        witches_row.append(InlineKeyboardButton("🔥 Bruxa Buff", callback_data='wb_atk:witch_buff'))
    if witches_row: keyboard.append(witches_row)
    
    # Linha 2: Boss
    boss_text = "⚔️ ATACAR BOSS"
    if witches_row: boss_text = "🛡️ Boss (Escudo Ativo)"
    if ents["boss"]["alive"]:
        keyboard.append([InlineKeyboardButton(boss_text, callback_data='wb_atk:boss')])

    # Linha 3: Suporte
    pdata = await player_manager.get_player_data(user_id)
    p_class = (pdata.get("class") or "").lower()
    p_skills = pdata.get("skills", {})
    
    support_row = []
    if "bardo_melodia_restauradora" in p_skills:
        support_row.append(InlineKeyboardButton("🎵 Melodia (AoE)", callback_data='wb_skill:bardo_melodia_restauradora'))
    if any(c in p_class for c in ["curandeiro", "sacerdote", "druida"]):
        support_row.append(InlineKeyboardButton("💚 Curar Aliado", callback_data='wb_sup:heal_ally'))
    if any(c in p_class for c in ["guerreiro", "berserker", "paladino", "guardiao"]):
        support_row.append(InlineKeyboardButton("🛡️ Proteger Raid", callback_data='wb_sup:defend_ally'))
    if support_row: keyboard.append(support_row)
    
    keyboard.append([InlineKeyboardButton("🔄 Atualizar Status", callback_data='wb_menu')])
    
    final_caption = f"⚔️ **RAID EM PROGRESSO** ⚔️\n\n{hud_text}\nEscolha sua ação:"

    # Busca Imagem
    media_id = file_ids.get_file_id(BOSS_IMAGE_KEY)

    if query:
        try:
            # Se já tem imagem na mensagem, tenta editar só a legenda/media
            if query.message.photo:
                if media_id and media_id != query.message.photo[-1].file_id:
                     # Se a imagem mudou (raro aqui, mas possível), edita media
                     await query.edit_message_media(
                         media=InputMediaPhoto(media_id, caption=final_caption, parse_mode="HTML"),
                         reply_markup=InlineKeyboardMarkup(keyboard)
                     )
                else:
                    # Só edita texto
                    await query.edit_message_caption(
                        caption=final_caption, 
                        reply_markup=InlineKeyboardMarkup(keyboard), 
                        parse_mode="HTML"
                    )
            else:
                # Se era texto antes, apaga e manda foto
                await query.delete_message()
                if media_id:
                    await context.bot.send_photo(chat_id, media_id, caption=final_caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
                else:
                    await context.bot.send_message(chat_id, final_caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        except Exception:
            pass 
    else:
        # Comando /worldboss
        if media_id:
            await context.bot.send_photo(chat_id, media_id, caption=final_caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        else:
            await context.bot.send_message(chat_id, final_caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def world_boss_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa ações."""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data 
    
    if ":" in data: prefix, value = data.split(":", 1)
    else: prefix, value = data, None

    player_data = await player_manager.get_player_data(user_id)
    result = {}
    
    if prefix == "wb_atk":
        result = await world_boss_manager.perform_action(user_id, player_data, "attack", target_key=value)
    elif prefix == "wb_sup":
        result = await world_boss_manager.perform_action(user_id, player_data, value, target_key=None)
    elif prefix == "wb_skill":
        result = await world_boss_manager.perform_action(user_id, player_data, "heal_ally", skill_id=value)

    if "error" in result:
        await query.answer(f"⚠️ {result['error']}", show_alert=True)
        return

    if "log" in result:
        last_line = result["log"].strip().split("\n")[-1]
        await query.answer(last_line[:200], show_alert=False)

    if result.get("boss_defeated"):
        await query.edit_message_caption(
            caption="🎉 **VITÓRIA! O DEMÔNIO CAIU!** 🎉\n\nO mal foi banido de Eldora!\nCalculando recompensas...",
            reply_markup=None
        )
        await distribute_loot_and_announce(context, result["battle_results"])
    else:
        await world_boss_menu_callback(update, context)

# LISTA DE HANDLERS
wb_start_handler = CommandHandler("iniciar_worldboss", iniciar_worldboss_command)
wb_player_cmd_handler = CommandHandler("worldboss", world_boss_menu_callback)
wb_menu_handler = CallbackQueryHandler(world_boss_menu_callback, pattern="^wb_menu$")
wb_action_handler = CallbackQueryHandler(world_boss_action_callback, pattern="^wb_(atk|sup|skill):")

all_world_boss_handlers = [wb_start_handler, wb_player_cmd_handler, wb_menu_handler, wb_action_handler]