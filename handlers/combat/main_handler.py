# handlers/combat/main_handler.py (VERSÃO FINAL DEFINITIVA)

import logging
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

# Importações dos seus módulos
from modules import player_manager, game_data, class_evolution_service
from modules import clan_manager
from handlers.menu.region import send_region_menu
from handlers.utils import format_combat_message
from modules.combat import durability, criticals, rewards
from modules.dungeons import runtime as dungeons_runtime
from handlers.class_evolution_handler import open_evolution

# Importa as funções necessárias do hunt_handler
from handlers.hunt_handler import start_hunt, _hunt_energy_cost

logger = logging.getLogger(__name__)

# Suas funções auxiliares
async def _safe_answer(query):
    try: await query.answer()
    except BadRequest: pass

async def _edit_caption_only(query, caption_text: str, reply_markup=None):
    try:
        await query.edit_message_caption(caption=caption_text, reply_markup=reply_markup, parse_mode='HTML')
    except (BadRequest, AttributeError):
        try:
            # Se a mensagem original não tinha mídia, a edição da legenda falha.
            # Tentamos então editar como uma mensagem de texto normal.
            await query.edit_message_text(text=caption_text, reply_markup=reply_markup, parse_mode='HTML')
        except Exception: 
            pass # Se tudo falhar, não faz nada para evitar spam

async def _return_to_region_menu(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, msg: str | None = None):
    player = player_manager.get_player_data(user_id) or {}
    player['player_state'] = {'action': 'idle'}
    player_manager.save_player_data(user_id, player)
    if msg:
        await context.bot.send_message(chat_id, msg)
    await send_region_menu(context=context, user_id=user_id, chat_id=chat_id)

# A função de combate completa e corrigida
async def combat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str = None) -> None:
    query = update.callback_query
    
    if action is None:
        action = query.data

    user_id = query.from_user.id
    chat_id = query.message.chat.id

    if action == 'combat_attack_menu':
        await _safe_answer(query)
        kb = [
            [InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu')],
            [InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')]
        ]
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
        return

    await _safe_answer(query)
    player_data = player_manager.get_player_data(user_id)

    if not player_data:
        await _edit_caption_only(query, "Não encontrei seus dados. Use /start.")
        return

    state = player_data.get('player_state', {})
    if state.get('action') not in ['in_combat', 'auto_hunting']:
        await _edit_caption_only(query, "Você não está em combate.")
        return

    player_data["user_id"] = user_id
    combat_details = dict(state.get('details', {}))
    is_auto_mode = combat_details.get('auto_mode', False)
    log = list(combat_details.get('battle_log', []))
    player_total_stats = player_manager.get_player_total_stats(player_data)
    monster_stats = {
        'attack': combat_details.get('monster_attack', 1), 'defense': combat_details.get('monster_defense', 0),
        'luck': combat_details.get('monster_luck', 5), 'monster_name': combat_details.get('monster_name', 'Inimigo')
    }
    in_dungeon = "dungeon_ctx" in combat_details

    if action == 'combat_flee':
        if random.random() <= 0.5:
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
            log.append(f"⬅️ {monster_stats['monster_name']} ataca e causa {monster_damage} de dano.")
            if m_is_mega: log.append("‼️ <b>MEGA CRÍTICO inimigo!</b>")
            elif m_is_crit: log.append("❗️ <b>DANO CRÍTICO inimigo!</b>")
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
                await context.bot.send_message(chat_id=chat_id, text=defeat_summary, parse_mode='HTML', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➡️ ℂ𝕠𝕟𝕥𝕚𝕟𝕦𝕒𝕣", callback_data='continue_after_action')]]))
                return
    
    elif action == 'combat_attack':
        num_attacks = 2 if random.random() < player_manager.get_player_double_attack_chance(player_data) else 1
        if num_attacks == 2: log.append("⚡ 𝐀𝐓𝐀𝐐𝐔𝐄 𝐃𝐔𝐏𝐋𝐎!")
        for i in range(num_attacks):
            player_damage, is_crit, is_mega = criticals.roll_damage(player_total_stats, monster_stats, {})
            log.append(f"➡️ {player_data.get('character_name','Você')} ataca e causa {player_damage} de dano.")
            if is_mega: log.append("💥💥 𝐌𝐄𝐆𝐀 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎!")
            elif is_crit: log.append("💥 𝐃𝐀𝐍𝐎 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎!")
            combat_details['monster_hp'] = int(combat_details.get('monster_hp', 0)) - player_damage
            combat_details["used_weapon"] = True
            if combat_details['monster_hp'] <= 0:
                break 
        
        if combat_details['monster_hp'] <= 0: # Vitória
            durability.apply_end_of_battle_wear(player_data, combat_details, log)
            
            if combat_details.get('evolution_trial'):
                target_class = combat_details.get('evolution_trial').get('target_class')
                success, message = class_evolution_service.finalize_evolution(user_id, target_class)
                await query.delete_message()
                await context.bot.send_message(chat_id=chat_id, text=f"🎉 {message} 🎉", parse_mode="HTML")
                await open_evolution(update, context)
                return
            if in_dungeon:
                xp_reward, gold_reward, looted_items_list = rewards.calculate_victory_rewards(player_data, combat_details)
                rewards_package = {"xp": xp_reward, "gold": gold_reward, "items": looted_items_list}
                player_manager.save_player_data(user_id, player_data)
                await dungeons_runtime.advance_after_victory(update, context, user_id, chat_id, combat_details, rewards_package)
                return

            # VITÓRIA NORMAL
            print(f"[DEBUG MISSÃO DE GUILDA] Detalhes do combate: {combat_details}")
            clan_id = player_data.get("clan_id")
            monster_id = combat_details.get("id") # Pega o ID do monstro derrotado
            
            print(f"[DEBUG MISSÃO DE GUILDA] Clan ID: {clan_id}, Monster ID: {monster_id}")

            # Se o jogador tem um clã E o monstro tem um ID
            if clan_id and monster_id:
                try:
                    # Avisa o clan_manager para registar a morte
                    await clan_manager.update_guild_mission_progress(
                        clan_id=clan_id,
                        mission_type="HUNT", # Tipo da nossa missão
                        details={"monster_id": monster_id, "count": 1}, # Detalhes
                        context=context # Passa o 'context' para enviar notificações
                    )
                except Exception as e:
                    # Loga o erro, mas não quebra o combate
                    logger.error(f"Falha ao atualizar progresso da missão de guilda para o clã {clan_id}: {e}")

            victory_summary = await rewards.apply_and_format_victory(player_data, combat_details, context)
            _, _, level_up_msg = player_manager.check_and_apply_level_up(player_data)
            if level_up_msg:
                victory_summary += level_up_msg
            
            player_manager.save_player_data(user_id, player_data)
            
            if is_auto_mode:
                player_data = player_manager.get_player_data(user_id)
                current_location = player_data.get("current_location")
                if player_data.get('energy', 0) > _hunt_energy_cost(player_data, current_location):
                    await context.bot.send_message(chat_id, victory_summary, parse_mode="HTML")
                    await context.bot.send_message(chat_id, "Buscando o próximo alvo em 3 segundos...")
                    await asyncio.sleep(3)
                    await start_hunt(user_id, chat_id, context, is_auto_mode=True, region_key=current_location, query=query)
                else:
                    player_data['player_state'] = {'action': 'idle'}
                    player_manager.save_player_data(user_id, player_data)
                    await context.bot.send_message(chat_id, victory_summary, parse_mode="HTML")
                    await context.bot.send_message(chat_id, "⚡️ Sua energia acabou! Caça automática finalizada.")
                
                try: await query.delete_message()
                except Exception: pass
                return
            else: # Vitória Manual
                player_data['current_hp'] = int(player_total_stats.get('max_hp', 50))
                player_data['player_state'] = {'action': 'idle'}
                player_manager.save_player_data(user_id, player_data)
                try: await query.delete_message()
                except Exception: pass
                await context.bot.send_message(chat_id=chat_id, text=victory_summary, parse_mode='HTML', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ 𝕍𝕠𝕝𝕥𝕒𝕣", callback_data='continue_after_action')]]))
                return

        # TURNO DO MONSTRO (se ele sobreviveu)
        if random.random() < player_manager.get_player_dodge_chance(player_data):
            log.append("💨 Você se esquivou do ataque!")
        else:
            monster_damage, m_is_crit, m_is_mega = criticals.roll_damage(monster_stats, player_total_stats, {})
            log.append(f"⬅️ {monster_stats['monster_name']} ataca e causa {monster_damage} de dano.")
            if m_is_mega: log.append("‼️ 𝕄𝔼𝔾𝔸 ℂℝ𝕀́𝕋𝕀ℂ𝕆 𝕚𝕟𝕚𝕞𝕚𝕘𝕠!")
            elif m_is_crit: log.append("❗️ 𝔻𝔸ℕ𝕆 ℂℝ𝕀́𝕋𝕀ℂ𝕆 𝕚𝕟𝕚𝕞𝕚𝕘𝕠!")
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
                await context.bot.send_message(chat_id=chat_id, text=defeat_summary, parse_mode='HTML', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➡️ ℂ𝕠𝕟𝕥𝕚𝕟𝕦𝕒𝕣", callback_data='continue_after_action')]]))
                return

    combat_details['battle_log'] = log
    player_data['player_state']['details'] = combat_details
    player_manager.save_player_data(user_id, player_data)

    new_text = format_combat_message(player_data)
    
    if is_auto_mode:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🛑 PARAR AUTO-CAÇA", callback_data='autohunt_stop')]])
    else:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu')],
            [InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')]
        ])

    if is_auto_mode and combat_details.get('monster_hp', 0) > 0:
        await _edit_caption_only(query, new_text, kb)
        await asyncio.sleep(3)
        await combat_callback(update, context, action='combat_attack')
        return

    await _edit_caption_only(query, new_text, kb)

combat_handler = CallbackQueryHandler(combat_callback, pattern=r'^(combat_attack|combat_flee|combat_attack_menu)$')