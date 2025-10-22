# handlers/guild/missions.py
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, clan_manager, mission_manager
from modules.game_data.missions import MISSION_CATALOG
from modules.game_data.guild_missions import GUILD_MISSIONS_CATALOG
from modules.game_data.clans import CLAN_CONFIG

# Importa a função auxiliar de barra de progresso do dashboard
from handlers.utils import create_progress_bar

# --- Lógica de Missões Diárias do Jogador ---

async def _safe_edit_message(query, text, reply_markup=None, parse_mode='HTML'):
    """Tenta editar a legenda de uma mensagem, se falhar, edita o texto."""
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        try:
            await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e:
            print(f"Erro ao editar a mensagem: {e}")


async def show_missions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o menu de missões diárias do jogador."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    missions_data = mission_manager.get_player_missions(user_id)
    active_missions = missions_data.get("active_missions", [])
    rerolls_left = missions_data.get("daily_rerolls_left", 0)
    
    caption = f"📜 <b>Missões Diárias</b>\n"
    caption += f"🔄 Você pode atualizar {rerolls_left} missões hoje.\n\n"
    
    keyboard = []
    
    if not active_missions:
        caption += "Um novo dia, novas missões! Boa sorte."
    
    for i, mission_state in enumerate(active_missions):
        template = next((m for m in MISSION_CATALOG if m["id"] == mission_state["mission_id"]), None)
        if not template: continue

        progress = mission_state.get("progress", 0)
        target = template.get("target_count", 1)
        
        status_icon = "⏳"
        progress_text = f"({progress}/{target})"
        buttons = []

        if mission_state.get("is_claimed"):
            status_icon = "🏅"
            progress_text = "(Reclamada)"
        elif mission_state.get("is_complete"):
            status_icon = "✅"
            progress_text = "<b>(Completa!)</b>"
            buttons.append(InlineKeyboardButton("🏆 Reclamar", callback_data=f"mission_claim:{i}"))
        elif rerolls_left > 0:
            buttons.append(InlineKeyboardButton("🔄 Atualizar", callback_data=f"mission_reroll:{i}"))
        
        caption += f"<b>{status_icon} {template['title']}</b>: {template['description']} {progress_text}\n"
        
        if buttons:
            keyboard.append(buttons)

    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data='guild_menu')])
    await _safe_edit_message(query, text=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def claim_reward_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa a recompensa de uma missão diária."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    mission_index = int(query.data.split(':')[1])
    
    player_data = player_manager.get_player_data(user_id)
    rewards = mission_manager.claim_reward(player_data, mission_index)
    
    if rewards:
        player_manager.save_player_data(user_id, player_data)
        
        rewards_text = "<b>Recompensas Recebidas:</b>\n"
        if "xp" in rewards: rewards_text += f"- {rewards['xp']} XP ✨\n"
        if "gold" in rewards: rewards_text += f"- {rewards['gold']} Ouro 🪙\n"
        
        try:
            await query.delete_message()
        except Exception:
            pass
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ <b>Missão Concluída!</b>\n\n{rewards_text}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📜 Ver Novas Missões", callback_data="guild_missions")]]),
            parse_mode='HTML'
        )
    else:
        await context.bot.answer_callback_query(query.id, "Recompensa já reclamada ou missão incompleta.", show_alert=True)
        await show_missions_menu(update, context)
        
async def claim_reward_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa a recompensa de uma missão diária."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    mission_index = int(query.data.split(':')[1])
    
    player_data = player_manager.get_player_data(user_id)
    rewards = mission_manager.claim_reward(player_data, mission_index)
    
    if rewards:
        player_manager.save_player_data(user_id, player_data)
        
        rewards_text = "<b>Recompensas Recebidas:</b>\n"
        if "xp" in rewards: rewards_text += f"- {rewards['xp']} XP ✨\n"
        if "gold" in rewards: rewards_text += f"- {rewards['gold']} Ouro 🪙\n"
        
        try:
            await query.delete_message()
        except Exception:
            pass
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ <b>Missão Concluída!</b>\n\n{rewards_text}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📜 Ver Novas Missões", callback_data="guild_missions")]]),
            parse_mode='HTML'
        )
    else:
        await context.bot.answer_callback_query(query.id, "Recompensa já reclamada ou missão incompleta.", show_alert=True)
        await show_missions_menu(update, context)

async def reroll_mission_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa a troca de uma missão diária."""
    query = update.callback_query
    mission_index = int(query.data.split(':')[1])
    success = mission_manager.reroll_mission(update.effective_user.id, mission_index)
    
    if success:
        await context.bot.answer_callback_query(query.id, "Missão atualizada!")
    else:
        await context.bot.answer_callback_query(query.id, "Não foi possível atualizar a missão.", show_alert=True)

    await show_missions_menu(update, context)

# --- Lógica de Missões de Guilda (Clã) ---

async def handle_clan_mission_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Roteador: Verifica se o clã pode pegar missões ou se precisa comprar o quadro primeiro."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    clan_id = player_manager.get_player_data(user_id).get("clan_id")
    clan_data = clan_manager.get_clan(clan_id)

    if clan_data.get("has_mission_board"):
        await show_mission_selection_menu(update, context)
    else:
        await show_purchase_board_menu(update, context)

async def show_purchase_board_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o menu para o líder comprar o quadro de missões."""
    query = update.callback_query
    cost = CLAN_CONFIG.get("mission_board_cost", {}).get("gold", 0)
    
    caption = (
        "<b>Quadro de Missões da Guilda</b>\n\n"
        "Para que o seu clã possa realizar missões, o líder precisa de adquirir um Quadro de Missões.\n\n"
        "Esta é uma compra única e permitirá o acesso permanente às missões de guilda.\n\n"
        f"<b>Custo:</b> {cost:,} 🪙 Ouro (será debitado do Banco do Clã)"
    )
    
    keyboard = [
        [InlineKeyboardButton("🪙 Comprar Quadro", callback_data="clan_board_purchase")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="clan_manage_menu")]
    ]
    
    await _safe_edit_message(query, text=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def handle_board_purchase_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa a compra do quadro de missões."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    clan_id = player_manager.get_player_data(user_id).get("clan_id")

    try:
        clan_manager.purchase_mission_board(clan_id, user_id)
        await context.bot.answer_callback_query(query.id, "Quadro de Missões comprado com sucesso!", show_alert=True)
        await show_mission_selection_menu(update, context)
    except ValueError as e:
        await context.bot.answer_callback_query(query.id, str(e), show_alert=True)

async def show_mission_selection_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra 3 missões aleatórias para o líder escolher."""
    query = update.callback_query
    user_id = update.effective_user.id
    clan_id = player_manager.get_player_data(user_id).get("clan_id")
    clan_data = clan_manager.get_clan(clan_id)

    if "active_mission" in clan_data and clan_data.get("active_mission"):
        await context.bot.answer_callback_query(query.id, "O seu clã já tem uma missão ativa.", show_alert=True)
        return

    mission_ids = list(GUILD_MISSIONS_CATALOG.keys())
    sample_size = min(3, len(mission_ids))
    random_mission_ids = random.sample(mission_ids, sample_size)
    
    caption = "🎯 <b>Escolha a Próxima Missão</b>\n\nSelecione uma das missões abaixo para ver os detalhes:"
    keyboard = []
    for mission_id in random_mission_ids:
        mission = GUILD_MISSIONS_CATALOG[mission_id]
        # ATUALIZADO: Chama a tela de preview (confirmação) em vez de aceitar direto
        keyboard.append([InlineKeyboardButton(f"📜 {mission['title']}", callback_data=f"clan_mission_preview:{mission_id}")])

    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data='clan_manage_menu')])
    await _safe_edit_message(query, text=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def accept_mission_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirma e inicia a missão de guilda escolhida pelo líder."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    clan_id = player_manager.get_player_data(user_id).get("clan_id")
    mission_id = query.data.split(':')[1] # Agora ouve 'clan_mission_accept'

    try:
        clan_manager.assign_mission_to_clan(clan_id, mission_id, user_id)
        mission_title = GUILD_MISSIONS_CATALOG[mission_id]['title']
        await context.bot.answer_callback_query(query.id, f"Missão '{mission_title}' iniciada!", show_alert=True)
    except ValueError as e:
        await context.bot.answer_callback_query(query.id, str(e), show_alert=True)
    
    from handlers.guild.dashboard import show_clan_dashboard
    await show_clan_dashboard(update, context)

async def show_guild_mission_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra os detalhes da missão de guilda ativa, agora com história."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    clan_id = player_manager.get_player_data(user_id).get("clan_id")
    active_mission = clan_manager.get_active_guild_mission(clan_id)
    
    if not active_mission:
        await _safe_edit_message(
            query,
            text="O seu clã não tem uma missão ativa.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="clan_menu")]])
        )
        return

    progress = active_mission.get("current_progress", 0)
    target = active_mission.get("target_count", 1)
    
    # --- Lógica de História Adicionada ---
    title = active_mission.get("title", "Missão Misteriosa")
    story = active_mission.get("story", "Uma tarefa aguarda...")
    objective = active_mission.get("objective", "Complete a tarefa.")

    caption = f"📜 <b>{title}</b> 📜\n\n"
    caption += f"<i>{story}</i>\n\n"
    caption += f"🎯 <b>Objetivo:</b> {objective}\n\n"
    caption += f"<b>Progresso:</b> {create_progress_bar(progress, target)} {progress}/{target}\n"
    # --- Fim da Lógica de História ---
    
    rewards = active_mission.get("rewards", {})
    if rewards:
        caption += "\n<b>Recompensas pela Conclusão:</b>\n"
        if "guild_xp" in rewards: caption += f"- Prestígio para o Clã: {rewards['guild_xp']} ✨\n"
        if "gold_per_member" in rewards: caption += f"- Ouro p/ membro: {rewards['gold_per_member']} 🪙\n"

    keyboard = [[InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="clan_menu")]]
    await _safe_edit_message(query, text=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def show_mission_confirmation_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o preview da missão (com história) antes do líder aceitar."""
    query = update.callback_query
    await query.answer()
    mission_id = query.data.split(':')[1]
    
    mission = GUILD_MISSIONS_CATALOG.get(mission_id)
    if not mission:
        await context.bot.answer_callback_query(query.id, "Essa missão não foi encontrada.", show_alert=True)
        return

    # Pega os dados da história
    title = mission.get("title", "Missão Misteriosa")
    story = mission.get("story", "Uma tarefa aguarda...")
    objective = mission.get("objective", "Complete a tarefa.") # Note que 'description' não existe mais

    caption = f"📜 <b>{title}</b> 📜\n\n"
    caption += f"<i>{story}</i>\n\n"
    caption += f"🎯 <b>Objetivo:</b> {objective}\n"
    
    rewards = mission.get("rewards", {})
    if rewards:
        caption += "\n<b>Recompensas pela Conclusão:</b>\n"
        if "guild_xp" in rewards: caption += f"- Prestígio para o Clã: {rewards['guild_xp']} ✨\n"
        if "gold_per_member" in rewards: caption += f"- Ouro p/ membro: {rewards['gold_per_member']} 🪙\n"

    caption += "\n<b>Deseja aceitar esta missão para a guilda?</b>"

    keyboard = [
        [InlineKeyboardButton("✅ Aceitar Missão", callback_data=f"clan_mission_accept:{mission_id}")],
        [InlineKeyboardButton("⬅️ Voltar (Escolher Outra)", callback_data="clan_mission_start")]
    ]
    await _safe_edit_message(query, text=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')


# --- Definição dos Handlers ---
missions_menu_handler = CallbackQueryHandler(show_missions_menu, pattern=r'^guild_missions$')
mission_claim_handler = CallbackQueryHandler(claim_reward_callback, pattern=r'^mission_claim:\d+$')
mission_reroll_handler = CallbackQueryHandler(reroll_mission_callback, pattern=r'^mission_reroll:\d+$')

clan_mission_start_handler = CallbackQueryHandler(handle_clan_mission_button, pattern=r'^clan_mission_start$')
clan_board_purchase_handler = CallbackQueryHandler(handle_board_purchase_callback, pattern=r'^clan_board_purchase$')
clan_guild_mission_details_handler = CallbackQueryHandler(show_guild_mission_details, pattern=r'^clan_guild_mission_details$')
clan_mission_details_handler = CallbackQueryHandler(show_guild_mission_details, pattern=r'^clan_mission_details$')

# --- NOVOS HANDLERS ---
clan_mission_preview_handler = CallbackQueryHandler(show_mission_confirmation_screen, pattern=r'^clan_mission_preview:[a-zA-Z0-9_]+$')
clan_mission_accept_handler = CallbackQueryHandler(accept_mission_callback, pattern=r'^clan_mission_accept:[a-zA-Z0-9_]+$')

