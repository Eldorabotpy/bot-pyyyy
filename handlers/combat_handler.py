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
    
    # --- DADOS PRINCIPAIS PARA O COMBATE ---
    player_total_stats = player_manager.get_player_total_stats(player_data)
    # Criamos um dicionário de stats para o monstro para padronizar
    monster_stats = {
        'attack': combat_details.get('monster_attack', 1),
        'defense': combat_details.get('monster_defense', 0),
        'luck': combat_details.get('monster_luck', 5),
        'monster_name': combat_details.get('monster_name', 'Inimigo') # Identificador
    }
    in_dungeon = "dungeon_ctx" in combat_details

    if action == 'combat_flee':
        flee_chance = 0.5
        
        if random.random() <= flee_chance:
            # (Lógica de fuga bem-sucedida - sem alterações)
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
            
            # --- CORREÇÃO 1: Ataque do monstro após fuga falhada ---
            # Passamos os dicionários completos para a função roll_damage
            monster_damage, _, _ = criticals.roll_damage(monster_stats, player_total_stats, {})
            
            player_data['current_hp'] = int(player_data.get('current_hp', 0)) - monster_damage
            combat_details["took_damage"] = True
            log.append(f"🩸 𝑽𝒐𝒄𝒆̂ 𝒓𝒆𝒄𝒆𝒃𝒆 {monster_damage} 𝒅𝒆 𝒅𝒂𝒏𝒐.")

            if player_data['current_hp'] <= 0:
                # (Lógica de derrota - sem alterações)
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
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➡️ Continuar", callback_data='continue_after_action')]])
                )
                return


    elif action == 'combat_attack':
        
        # --- CORREÇÃO 2: Ataque do jogador ---
        # Passamos os dicionários completos para a função roll_damage
        player_damage, is_crit, is_mega = criticals.roll_damage(player_total_stats, monster_stats, {})
        
        log.append(f"➡️ {player_data.get('character_name','Você')} ataca e causa {player_damage} de dano.")
        combat_details['monster_hp'] = int(combat_details.get('monster_hp', 0)) - player_damage
        combat_details["used_weapon"] = True

        if combat_details['monster_hp'] <= 0:
            # (Lógica de vitória - sem alterações)
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
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data='continue_after_action')]])
                )
                return

        # --- CORREÇÃO 3: Contra-ataque do monstro ---
        # Passamos os dicionários completos para a função roll_damage
        monster_damage, _, _ = criticals.roll_damage(monster_stats, player_total_stats, {})

        log.append(f"⬅️ {combat_details.get('monster_name','Inimigo')} contra-ataca e causa {monster_damage} de dano.")
        player_data['current_hp'] = int(player_data.get('current_hp', 0)) - monster_damage
        combat_details["took_damage"] = True

        if player_data['current_hp'] <= 0:
            # (Lógica de derrota - sem alterações)
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
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➡️ Continuar", callback_data='continue_after_action')]])
            )
            return
            
    # (Final da função - sem alterações)
    combat_details['battle_log'] = log
    player_data['player_state']['details'] = combat_details
    player_manager.save_player_data(user_id, player_data)

    new_text = format_combat_message(player_data)
    kb = [[InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')]]
    await _edit_caption_only(query, new_text, InlineKeyboardMarkup(kb))