# handlers/combat_handler.py
import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest
from modules import player_manager, game_data
from handlers.menu.region import send_region_menu
from handlers.utils import format_combat_message


from modules.combat import durability, criticals, rewards
from modules.dungeons import runtime as dungeons_runtime

logger = logging.getLogger(__name__)

async def _safe_answer(query):
    try: await query.answer()
    except BadRequest: pass

async def _edit_caption_only(query, caption_text: str, reply_markup=None):
    try:
        await query.edit_message_caption(caption=caption_text, reply_markup=reply_markup, parse_mode='HTML')
    except (BadRequest, AttributeError):
        try:
            await query.message.reply_text(text=caption_text, reply_markup=reply_markup, parse_mode='HTML')
        except Exception: pass

async def _return_to_region_menu(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, msg: str | None = None):
    player = player_manager.get_player_data(user_id) or {}
    player['player_state'] = {'action': 'idle'}
    player_manager.save_player_data(user_id, player)
    if msg:
        await context.bot.send_message(chat_id, msg)
    await send_region_menu(context=context, user_id=user_id, chat_id=chat_id)


async def combat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await _safe_answer(query)

    user_id = query.from_user.id
    chat_id = query.message.chat.id
    player_data = player_manager.get_player_data(user_id)
    
    if not player_data:
        await _edit_caption_only(query, "Não encontrei seus dados. Use /start.")
        return

    state = player_data.get('player_state', {})
    if state.get('action') != 'in_combat':
        await _edit_caption_only(query, "Você não está em combate.")
        return

    player_data["user_id"] = user_id
    combat_details = dict(state.get('details', {}))
    log = list(combat_details.get('battle_log', []))
    action = query.data
    player_total_stats = player_manager.get_player_total_stats(player_data)
    monster_stats = {
        'attack': combat_details.get('monster_attack', 1),
        'defense': combat_details.get('monster_defense', 0),
        'luck': combat_details.get('monster_luck', 5),
        'monster_name': combat_details.get('monster_name', 'Inimigo')
    }
    in_dungeon = "dungeon_ctx" in combat_details

    if action == 'combat_flee':
        flee_chance = 0.5 
        
        if random.random() <= flee_chance:
            durability.apply_end_of_battle_wear(player_data, combat_details, log)
            try: await query.delete_message()
            except Exception: pass
            
            if in_dungeon:
                await dungeons_runtime.fail_dungeon_run(context, user_id, chat_id, "Você fugiu da batalha")
                return

            await _return_to_region_menu(context, user_id, chat_id, "🏃 𝑽𝒐𝒄𝒆̂ 𝒄𝒐𝒏𝒔𝒆𝒈𝒖𝒊𝒖 𝒇𝒖𝒈𝒊𝒓 𝒅𝒂 𝒃𝒂𝒕𝒂𝒍𝒉𝒂.")
            return
        else:
            log.append("🏃 𝑺𝒖𝒂 𝒕𝒆𝒏𝒕𝒂𝒕𝒊𝒗𝒂 𝒅𝒆 𝒇𝒖𝒈𝒂 𝒇𝒂𝒍𝒉𝒐𝒖!")
            
            monster_damage, m_is_crit, m_is_mega = criticals.roll_damage(monster_stats, player_total_stats, {})
            log.append(f"⬅️ {monster_stats['monster_name']} ataca\ne causa {monster_damage} de dano.")

            # --- NOVO: Mensagens de Crítico do Monstro ---
            if m_is_mega:
                log.append("‼️ <b>MEGA CRÍTICO inimigo!</b>")
            elif m_is_crit:
                log.append("❗️ <b>DANO CRÍTICO inimigo!</b>")

            player_data['current_hp'] = int(player_data.get('current_hp', 0)) - monster_damage
            combat_details["took_damage"] = True

            if player_data['current_hp'] <= 0:
                durability.apply_end_of_battle_wear(player_data, combat_details, log)
                if in_dungeon:
                    await dungeons_runtime.fail_dungeon_run(context, user_id, chat_id, "Você foi derrotado")
                    return
                defeat_summary, _ = rewards.process_defeat(player_data, combat_details)
                player_data['current_hp'] = int(player_total_stats.get('max_hp', 50))
                player_data['player_state'] = {'action': 'idle'}
                player_manager.save_player_data(user_id, player_data)
                try: await query.delete_message()
                except Exception: pass
                await context.bot.send_message(
                    chat_id=chat_id, text=defeat_summary, parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➡️ ℂ𝕠𝕟𝕥𝕚𝕟𝕦𝕒𝕣", callback_data='continue_after_action')]])
                )
                return

    # --- LÓGICA DE ATAQUE (ATUALIZADA) ---
    elif action == 'combat_attack':
        
        # --- NOVO: Lógica de Ataque Duplo ---
        num_attacks = 1
        double_attack_chance = player_manager.get_player_double_attack_chance(player_data)
        if random.random() < double_attack_chance:
            num_attacks = 2
            log.append("⚡ 𝐀𝐓𝐀𝐐𝐔𝐄 𝐃𝐔𝐏𝐋𝐎!")

        for i in range(num_attacks):
            player_damage, is_crit, is_mega = criticals.roll_damage(player_total_stats, monster_stats, {})
            log.append(f"➡️ {player_data.get('character_name','Você')} ataca \ne causa {player_damage} de dano.")
            
            # --- NOVO: Mensagens de Crítico ---
            if is_mega:
                log.append("💥💥 𝐌𝐄𝐆𝐀 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎!")
            elif is_crit:
                log.append("💥 𝐃𝐀𝐍𝐎 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎!")

            combat_details['monster_hp'] = int(combat_details.get('monster_hp', 0)) - player_damage
            combat_details["used_weapon"] = True
            
            if combat_details['monster_hp'] <= 0:
                break 
        
        if combat_details['monster_hp'] <= 0:
            durability.apply_end_of_battle_wear(player_data, combat_details, log)
            xp_reward, gold_reward, looted_items_list = rewards.calculate_victory_rewards(player_data, combat_details)
            if in_dungeon:
                rewards_package = {"xp": xp_reward, "gold": gold_reward, "items": looted_items_list}
                player_manager.save_player_data(user_id, player_data)
                await dungeons_runtime.advance_after_victory(update, context, user_id, chat_id, combat_details, rewards_package)
                return
            else:
                victory_summary = await rewards.apply_and_format_victory(player_data, combat_details, context)
                player_data['current_hp'] = int(player_total_stats.get('max_hp', 50))
                player_data['player_state'] = {'action': 'idle'}
                player_manager.save_player_data(user_id, player_data)
                try: await query.delete_message()
                except Exception: pass
                await context.bot.send_message(
                    chat_id=chat_id, text=victory_summary, parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ 𝕍𝕠𝕝𝕥𝕒𝕣", callback_data='continue_after_action')]])
                )
                return

        # --- NOVO: Lógica de Esquiva ---
        dodge_chance = player_manager.get_player_dodge_chance(player_data)
        if random.random() < dodge_chance:
            log.append("💨 Você se esquivou do ataque!")
        else:
            monster_damage, m_is_crit, m_is_mega = criticals.roll_damage(monster_stats, player_total_stats, {})
            log.append(f"⬅️ {monster_stats['monster_name']} ataca \ne causa {monster_damage} de dano.")

            # --- NOVO: Mensagens de Crítico do Monstro ---
            if m_is_mega:
                log.append("‼️ 𝕄𝔼𝔾𝔸 ℂℝ𝕀́𝕋𝕀ℂ𝕆 𝕚𝕟𝕚𝕞𝕚𝕘𝕠!")
            elif m_is_crit:
                log.append("❗️ 𝔻𝔸ℕ𝕆 ℂℝ𝕀́𝕋𝕀ℂ𝕆 𝕚𝕟𝕚𝕞𝕚𝕘𝕠!")
            
            player_data['current_hp'] = int(player_data.get('current_hp', 0)) - monster_damage
            combat_details["took_damage"] = True

            if player_data['current_hp'] <= 0:
                durability.apply_end_of_battle_wear(player_data, combat_details, log)
                if in_dungeon:
                    await dungeons_runtime.fail_dungeon_run(context, user_id, chat_id, "Você foi derrotado")
                    return
                defeat_summary, _ = rewards.process_defeat(player_data, combat_details)
                player_data['current_hp'] = int(player_total_stats.get('max_hp', 50))
                player_data['player_state'] = {'action': 'idle'}
                player_manager.save_player_data(user_id, player_data)
                try: await query.delete_message()
                except Exception: pass
                await context.bot.send_message(
                    chat_id=chat_id, text=defeat_summary, parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➡️ ℂ𝕠𝕟𝕥𝕚𝕟𝕦𝕒𝕣", callback_data='continue_after_action')]])
                )
                return
            
    combat_details['battle_log'] = log
    player_data['player_state']['details'] = combat_details
    player_manager.save_player_data(user_id, player_data)

    new_text = format_combat_message(player_data)
    kb = [[InlineKeyboardButton("⚔️ 𝔸𝕥𝕒𝕔𝕒𝕣", callback_data='combat_attack'), InlineKeyboardButton("🏃 𝔽𝕦𝕘𝕚𝕣", callback_data='combat_flee')]]
    await _edit_caption_only(query, new_text, InlineKeyboardMarkup(kb))

combat_handler = CallbackQueryHandler(combat_callback, pattern=r'^combat_(attack|flee)$')
