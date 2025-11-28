from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, clan_manager
from modules.game_data.clans import CLAN_PRESTIGE_LEVELS
from ..utils import safe_edit_message, create_progress_bar, format_buffs_text # Importações combinadas

# --- Lógica de Aprimoramento do Clã ---

async def show_clan_upgrade_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o menu de aprimoramento, com custos e benefícios do próximo nível."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    # <<< CORREÇÃO 1: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")
    if not clan_id:
        await safe_edit_message(query, text="Você não está em um clã.")
        return
        
    # <<< CORREÇÃO 2: Adiciona await >>>
    clan_data = await clan_manager.get_clan(clan_id)
    
    # Apenas o líder pode ver este menu
    if clan_data.get("leader_id") != user_id:
        await context.bot.answer_callback_query(query.id, "Apenas o líder do clã pode aceder a este menu.", show_alert=True)
        return
        
    current_level = clan_data.get("prestige_level", 1)
    current_points = clan_data.get("prestige_points", 0)
    
    current_level_info = CLAN_PRESTIGE_LEVELS.get(current_level, {})
    next_level_info = CLAN_PRESTIGE_LEVELS.get(current_level + 1)

    caption = f"⚜️ <b>Aprimorar Clã: {clan_data.get('display_name')}</b> ⚜️\n\n"
    caption += f"<b>Nível de Prestígio Atual:</b> {current_level} ({current_level_info.get('title', '')})\n"
    
    caption += "<b>Buffs Ativos:</b>\n"
    caption += format_buffs_text(current_level_info.get("buffs", {}))
    
    keyboard = []
    
    if next_level_info:
        points_needed = current_level_info.get("points_to_next_level", 999999)
        progress_bar = create_progress_bar(current_points, points_needed)
        
        caption += f"\n<b>Progresso para o Nível {current_level + 1}:</b>\n"
        caption += f"Prestígio: {progress_bar} {current_points}/{points_needed}\n"
        
        caption += "\n<b>Benefícios do Próximo Nível:</b>\n"
        caption += f"   - Membros: {next_level_info.get('max_members', 0)}\n"
        caption += format_buffs_text(next_level_info.get("buffs", {}))

        upgrade_cost = next_level_info.get("upgrade_cost", {})
        cost_gold = upgrade_cost.get("gold", 0)
        cost_dimas = upgrade_cost.get("dimas", 0)
        
        caption += "\n<b>Custo do Aprimoramento:</b>\n"
        caption += f"   - 🪙 {cost_gold:,} Ouro\n"
        caption += f"   - 💎 {cost_dimas} Dimas\n"
        
        if current_points >= points_needed:
            caption += "\n<b>Você tem prestígio suficiente para aprimorar!</b>"
            keyboard.append([
                InlineKeyboardButton("🪙 Aprimorar com Ouro", callback_data='clan_upgrade_confirm:gold'),
                InlineKeyboardButton("💎 Aprimorar com Dimas", callback_data='clan_upgrade_confirm:dimas'),
            ])
    else: # Sem next_level_info, significa nível máximo
        caption += "\n<b>O seu clã já atingiu o nível máximo de prestígio!</b>"

    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data='clan_manage_menu')])
    
    await safe_edit_message(query, text=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def confirm_clan_upgrade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa o clique no botão para subir o nível do clã."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    # <<< CORREÇÃO 3: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")
    payment_method = query.data.split(':')[1]
    
    try:
        # <<< CORREÇÃO 4: Adiciona await >>>
        await clan_manager.level_up_clan(clan_id, user_id, payment_method)
        
        # <<< CORREÇÃO 5: Adiciona await >>>
        clan_data = await clan_manager.get_clan(clan_id)
        clan_name = clan_data.get("display_name")
        new_level = clan_data.get("prestige_level")

        await context.bot.answer_callback_query(
            query.id,
            f"Parabéns! O clã {clan_name} subiu para o nível {new_level}!",
            show_alert=True
        )
        
        for member_id in clan_data.get("members", []):
            if member_id != user_id:
                try:
                    await context.bot.send_message(
                        chat_id=member_id,
                        text=f"🎉 Boas notícias! O seu clã, {clan_name}, subiu para o nível de prestígio {new_level}!"
                    )
                except Exception:
                    pass

    except ValueError as e:
        await context.bot.answer_callback_query(query.id, str(e), show_alert=True)
        return

    from handlers.guild.dashboard import show_clan_dashboard
    # <<< CORREÇÃO 6: Adiciona await >>>
    await show_clan_dashboard(update, context)

# --- Definição dos Handlers ---
clan_upgrade_menu_handler = CallbackQueryHandler(show_clan_upgrade_menu, pattern=r'^clan_upgrade_menu$')
clan_upgrade_confirm_handler = CallbackQueryHandler(confirm_clan_upgrade_callback, pattern=r'^clan_upgrade_confirm:(gold|dimas)$')