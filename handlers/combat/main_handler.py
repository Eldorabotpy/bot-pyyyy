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
from handlers.hunt_handler import start_hunt, _hunt_energy_cost

logger = logging.getLogger(__name__)

async def _safe_answer(query):
    try: await query.answer()
    except BadRequest: pass

async def _edit_caption_only(query, caption_text: str, reply_markup=None):
    try:
        await query.edit_message_caption(caption=caption_text, reply_markup=reply_markup, parse_mode='HTML')
    except (BadRequest, AttributeError):
        try:
            await query.edit_message_text(text=caption_text, reply_markup=reply_markup, parse_mode='HTML')
        except Exception: 
            pass 

async def _return_to_region_menu(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, msg: str | None = None):
    """Retorna ao menu principal da região, garantindo que o estado é 'idle'."""
    player = await player_manager.get_player_data(user_id) or {}
    player['player_state'] = {'action': 'idle'}
    await player_manager.save_player_data(user_id, player) 
    if msg:
        await context.bot.send_message(chat_id, msg)
    await send_region_menu(context=context, user_id=user_id, chat_id=chat_id)

#
# >>> INÍCIO DO CÓDIGO CORRIGIDO FINALÍSSIMO (combat_callback) <<<
# Substitua a função inteira no teu ficheiro handlers/combat/main_handler.py
#

async def combat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str = None) -> None:
    query = update.callback_query
    
    if action is None and query:
        action = query.data
    elif action is None and not query:
        logger.error("combat_callback chamado sem query e sem action!")
        return

    user_id = query.from_user.id if query else update.effective_user.id
    chat_id = query.message.chat.id if query else update.effective_chat.id

    if action == 'combat_attack_menu':
        # ... (código do menu de ataque mantido igual) ...
        if not query: return
        await _safe_answer(query)
        kb = [
            [InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu')],
            [InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')]
        ]
        try:
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            logger.debug(f"Falha ao editar markup para menu de ataque: {e}")
        return

    if query:
        await _safe_answer(query)
    
    player_data = await player_manager.get_player_data(user_id) 
    if not player_data:
        # ... (tratamento de erro mantido igual) ...
        error_msg = "Não encontrei seus dados. Use /start."
        if query: await _edit_caption_only(query, error_msg)
        else: await context.bot.send_message(chat_id, error_msg)
        return

    state = player_data.get('player_state', {})
    if state.get('action') not in ['in_combat']:
         # ... (tratamento de erro mantido igual) ...
         idle_msg = "Você não está em combate."
         if not (action == 'combat_attack' and is_auto_mode): # is_auto_mode definido abaixo
             if query: await _edit_caption_only(query, idle_msg)
         return

    combat_details = dict(state.get('details', {}))
    if not combat_details:
        # ... (tratamento de erro mantido igual) ...
        error_msg = "Erro: Detalhes do combate não encontrados."
        if query: await _edit_caption_only(query, error_msg)
        else: await context.bot.send_message(chat_id, error_msg)
        player_data['player_state'] = {'action': 'idle'}
        await player_manager.save_player_data(user_id, player_data)
        return

    player_data["user_id"] = user_id
    is_auto_mode = combat_details.get('auto_mode', False) # Definido aqui
    log = list(combat_details.get('battle_log', []))
    player_total_stats = await player_manager.get_player_total_stats(player_data) 
    monster_stats = {
        'attack': combat_details.get('monster_attack', 1), 'defense': combat_details.get('monster_defense', 0),
        'luck': combat_details.get('monster_luck', 5), 'monster_name': combat_details.get('monster_name', 'Inimigo')
    }
    in_dungeon = "dungeon_ctx" in combat_details

    # --- LÓGICA DE FUGA (Mantida igual) ---
    if action == 'combat_flee':
        # ... (código da fuga mantido igual) ...
        if not query: return
        if random.random() <= 0.5: # Sucesso
            durability.apply_end_of_battle_wear(player_data, combat_details, log)
            await player_manager.save_player_data(user_id, player_data)
            try: await query.delete_message()
            except Exception: pass
            if in_dungeon:
                await dungeons_runtime.fail_dungeon_run(context, user_id, chat_id, "Você fugiu da batalha")
            else:
                await _return_to_region_menu(context, user_id, chat_id, "🏃 𝑽𝒐𝒄𝒆̂ 𝒄𝒐𝒏𝒔𝒆𝒈𝒖𝒊𝒖 𝒇𝒖𝒈𝒊𝒓 𝒅𝒂 𝒃𝒂𝒕𝒂𝒍𝒉𝒂.")
            return
        else: # Falha
            log.append("🏃 𝑺𝒖𝒂 𝒕𝒆𝒏𝒕𝒂𝒕𝒊𝒗𝒂 𝒅𝒆 𝒇𝒖𝒈𝒂 𝒇𝒂𝒍𝒉𝒐𝒖!")
            monster_damage, m_is_crit, m_is_mega = criticals.roll_damage(monster_stats, player_total_stats, {})
            log.append(f"⬅️ {monster_stats['monster_name']} ataca e causa {monster_damage} de dano.")
            if m_is_mega: log.append("‼️ <b>MEGA CRÍTICO inimigo!</b>")
            elif m_is_crit: log.append("❗️ <b>DANO CRÍTICO inimigo!</b>")
            player_data['current_hp'] = int(player_data.get('current_hp', 0)) - monster_damage
            combat_details["took_damage"] = True
            if player_data['current_hp'] <= 0: # Derrota
                durability.apply_end_of_battle_wear(player_data, combat_details, log)
                if in_dungeon:
                    await dungeons_runtime.fail_dungeon_run(context, user_id, chat_id, "Você foi derrotado")
                    return
                defeat_summary, _ = rewards.process_defeat(player_data, combat_details)
                player_data['current_hp'] = 1
                player_data['player_state'] = {'action': 'idle'}
                await player_manager.save_player_data(user_id, player_data) 
                try: await query.delete_message()
                except Exception: pass
                await context.bot.send_message(chat_id=chat_id, text=defeat_summary, parse_mode='HTML', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➡️ ℂ𝕠𝕟𝕥𝕚𝕟𝕦𝕒𝕣", callback_data='continue_after_action')]]))
                return

    # --- LÓGICA DE ATAQUE ---
    elif action == 'combat_attack':
        double_attack_chance = await player_manager.get_player_double_attack_chance(player_data)
        num_attacks = 2 if random.random() < double_attack_chance else 1
        if num_attacks == 2: log.append("⚡ 𝐀𝐓𝐀𝐐𝐔𝐄 𝐃𝐔𝐏𝐋𝐎!")
        
        monster_defeated_in_turn = False
        for i in range(num_attacks):
            player_damage, is_crit, is_mega = criticals.roll_damage(player_total_stats, monster_stats, {})
            log.append(f"➡️ {player_data.get('character_name','Você')} ataca e causa {player_damage} de dano.")
            if is_mega: log.append("💥💥 𝐌𝐄𝐆𝐀 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎!")
            elif is_crit: log.append("💥 𝐃𝐀𝐍𝐎 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎!")
            combat_details['monster_hp'] = int(combat_details.get('monster_hp', 0)) - player_damage
            combat_details["used_weapon"] = True
            if combat_details['monster_hp'] <= 0:
                monster_defeated_in_turn = True
                break

        # --- PROCESSAMENTO PÓS-ATAQUE DO JOGADOR ---
        if monster_defeated_in_turn: # Vitória
            durability.apply_end_of_battle_wear(player_data, combat_details, log)
            
            # ... (Lógica de evolução e dungeon mantida igual) ...
            if combat_details.get('evolution_trial'):
                target_class = combat_details.get('evolution_trial').get('target_class')
                success, message = await class_evolution_service.finalize_evolution(user_id, target_class)
                if query: await query.delete_message()
                await context.bot.send_message(chat_id=chat_id, text=f"🎉 {message} 🎉", parse_mode="HTML")
                await open_evolution(update, context) 
                return
            if in_dungeon:
                xp_reward, gold_reward, looted_items_list = rewards.calculate_victory_rewards(player_data, combat_details)
                rewards_package = {"xp": xp_reward, "gold": gold_reward, "items": looted_items_list}
                await player_manager.save_player_data(user_id, player_data)
                await dungeons_runtime.advance_after_victory(update, context, user_id, chat_id, combat_details, rewards_package)
                return

            # VITÓRIA NORMAL
            # ... (Lógica de missão de guilda mantida igual) ...
            clan_id = player_data.get("clan_id")
            monster_id = combat_details.get("id")
            if clan_id and monster_id:
                try:
                    await clan_manager.update_guild_mission_progress(
                        clan_id=clan_id, mission_type="MONSTER_HUNT",
                        details={"monster_id": monster_id, "count": 1}, context=context 
                    )
                except Exception as e:
                    logger.error(f"Falha ao atualizar progresso da missão de guilda para o clã {clan_id}: {e}")

            victory_summary = await rewards.apply_and_format_victory(player_data, combat_details, context)
            
            # <<< CORREÇÃO FINAL APLICADA AQUI: REMOVIDO 'await' >>>
            # check_and_apply_level_up é SÍNCRONO
            _, _, level_up_msg = player_manager.check_and_apply_level_up(player_data) 
            
            if level_up_msg:
                victory_summary += level_up_msg
            
            await player_manager.save_player_data(user_id, player_data) # Salva recompensas/level
            
            # ... (Lógica de Auto-Hunt após vitória mantida igual) ...
            if is_auto_mode:
                player_data = await player_manager.get_player_data(user_id)
                current_location = player_data.get("current_location")
                energy_cost_next = await _hunt_energy_cost(player_data, current_location)
                if player_data.get('energy', 0) >= energy_cost_next:
                    await context.bot.send_message(chat_id, victory_summary, parse_mode="HTML")
                    await context.bot.send_message(chat_id, "Buscando o próximo alvo em 3 segundos...")
                    await asyncio.sleep(3)
                    await start_hunt(user_id, chat_id, context, is_auto_mode=True, region_key=current_location, query=query)
                    return
                else: # Sem energia
                    player_data['player_state'] = {'action': 'idle'}
                    await player_manager.save_player_data(user_id, player_data) 
                    await context.bot.send_message(chat_id, victory_summary, parse_mode="HTML")
                    await context.bot.send_message(chat_id, "⚡️ Sua energia acabou! Caça automática finalizada.")
                    if query:
                         try: await query.delete_message()
                         except Exception: pass
                    return
            else: # Vitória Manual
                player_data['player_state'] = {'action': 'idle'}
                await player_manager.save_player_data(user_id, player_data)
                if query:
                     try: await query.delete_message()
                     except Exception: pass
                await context.bot.send_message(chat_id=chat_id, text=victory_summary, parse_mode='HTML', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ 𝕍𝕠𝕝𝕥𝕒𝕣", callback_data='continue_after_action')]]))
                return

        # --- TURNO DO MONSTRO (se sobreviveu) ---
        else: 
            # ... (Lógica do turno do monstro mantida igual, incluindo o await em get_player_dodge_chance) ...
            dodge_chance = await player_manager.get_player_dodge_chance(player_data)
            if random.random() < dodge_chance: 
                log.append("💨 Você se esquivou do ataque!")
            else:
                monster_damage, m_is_crit, m_is_mega = criticals.roll_damage(monster_stats, player_total_stats, {})
                log.append(f"⬅️ {monster_stats['monster_name']} ataca e causa {monster_damage} de dano.")
                if m_is_mega: log.append("‼️ 𝕄𝔼𝔾𝔸 ℂℝ𝕀́𝕋𝕀ℂ𝕆 𝕚𝕟𝕚𝕞𝕚𝕘𝕠!")
                elif m_is_crit: log.append("❗️ 𝔻𝔸ℕ𝕆 ℂℝ𝕀́𝕋𝕀ℂ𝕆 𝕚𝕟𝕚𝕞𝕚𝕘𝕠!")
                player_data['current_hp'] = int(player_data.get('current_hp', 0)) - monster_damage
                combat_details["took_damage"] = True
                if player_data['current_hp'] <= 0: # Derrota
                    durability.apply_end_of_battle_wear(player_data, combat_details, log)
                    if in_dungeon:
                        await dungeons_runtime.fail_dungeon_run(context, user_id, chat_id, "Você foi derrotado")
                        return
                    defeat_summary, _ = rewards.process_defeat(player_data, combat_details)
                    player_data['current_hp'] = 1
                    player_data['player_state'] = {'action': 'idle'}
                    await player_manager.save_player_data(user_id, player_data)
                    if query:
                         try: await query.delete_message()
                         except Exception: pass
                    await context.bot.send_message(chat_id=chat_id, text=defeat_summary, parse_mode='HTML', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➡️ ℂ𝕠𝕟𝕥𝕚𝕟𝕦𝕒𝕣", callback_data='continue_after_action')]]))
                    return

    # --- FIM DA LÓGICA DE AÇÃO ---

    # Atualiza o log e o estado
    combat_details['battle_log'] = log[-15:]
    player_data['player_state']['details'] = combat_details
    await player_manager.save_player_data(user_id, player_data) 

    # Formata a mensagem ATUALIZADA
    new_text = await format_combat_message(player_data, player_stats=player_total_stats) 
    
    # Define os botões
    if is_auto_mode:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🛑 PARAR AUTO-CAÇA", callback_data='autohunt_stop')]])
    else:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu')],
            [InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')]
        ])

    # Edita a mensagem (se houver query)
    if query:
        await _edit_caption_only(query, new_text, kb)

    # Continua auto-hunt se monstro estiver vivo
    if is_auto_mode and combat_details.get('monster_hp', 0) > 0:
        await asyncio.sleep(3)
        await combat_callback(update, context, action='combat_attack') 
        return

# Handler Registrado (mantido igual)
combat_handler = CallbackQueryHandler(combat_callback, pattern=r'^(combat_attack|combat_flee|combat_attack_menu)$')

#
# >>> FIM DO CÓDIGO CORRIGIDO FINALÍSSIMO (combat_callback) <<<
#