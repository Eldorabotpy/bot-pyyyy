# handlers/combat/main_handler.py
# (VERSÃO FINAL COM 'BATTLE CACHE' E TROCA DE MÍDIA)

import logging
import random
import asyncio
import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaVideo, InputMediaPhoto, CallbackQuery
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

# Importações dos seus módulos
from modules import player_manager, game_data, class_evolution_service
from modules import clan_manager
from handlers.menu.region import send_region_menu

# --- Importa OS DOIS formatadores ---
from handlers.utils import format_combat_message_from_cache, format_combat_message

from modules.combat import durability, criticals, rewards
from modules.dungeons import runtime as dungeons_runtime
from handlers.class_evolution_handler import open_evolution
from handlers.hunt_handler import start_hunt # (Usado pelo fallback de auto-hunt)
from modules.game_data.skills import SKILL_DATA
from modules.player.actions import spend_mana
from handlers.profile_handler import _get_class_media
from modules.dungeons.runtime import _send_battle_media
from modules import file_ids as file_id_manager

logger = logging.getLogger(__name__)

async def _safe_answer(query):
    try: await query.answer()
    except BadRequest: pass

async def _edit_caption_only(query, caption_text: str, reply_markup=None):
    """ Tenta editar o caption, se falhar, tenta editar o texto. (Usado pelo Legacy)"""
    try:
        await query.edit_message_caption(caption=caption_text, reply_markup=reply_markup, parse_mode='HTML')
    except (BadRequest, AttributeError):
        try:
            await query.edit_message_text(text=caption_text, reply_markup=reply_markup, parse_mode='HTML')
        except Exception: 
            pass 

async def _edit_media_or_caption(context: ContextTypes.DEFAULT_TYPE, battle_cache: dict, new_caption: str, new_media_id: str, new_media_type: str, reply_markup=None):
    """
    Função 'inteligente' que troca a mídia E a legenda. (Usada pelo Cache)
    """
    try:
        # Fallback de mídia: Se a mídia desejada não existir, usa a do monstro
        if not new_media_id:
            new_media_id = battle_cache['monster_media_id']
            new_media_type = battle_cache['monster_media_type']
            # Se nem a do monstro existir, falha (vai para o 'except')
            if not new_media_id:
                 raise ValueError("Nenhuma mídia válida encontrada no cache (nem jogador, nem monstro)")

        InputMediaClass = InputMediaVideo if new_media_type == "video" else InputMediaPhoto
        
        await context.bot.edit_message_media(
            chat_id=battle_cache['chat_id'],
            message_id=battle_cache['message_id'],
            media=InputMediaClass(
                media=new_media_id,
                caption=new_caption,
                parse_mode="HTML"
            ),
            reply_markup=reply_markup
        )
    except Exception as e:
        if "Message is not modified" in str(e):
            pass 
        else:
            logger.warning(f"Falha ao trocar mídia (edit_message_media): {e}. Tentando editar só a legenda.")
            try:
                await context.bot.edit_message_caption(
                    chat_id=battle_cache['chat_id'],
                    message_id=battle_cache['message_id'],
                    caption=new_caption,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            except Exception as e_caption:
                logger.error(f"Falha CRÍTICA ao editar legenda no fallback: {e_caption}")


async def _return_to_region_menu(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, msg: str | None = None):
    """Retorna ao menu principal da região, garantindo que o estado é 'idle'."""
    player = await player_manager.get_player_data(user_id) or {}
    
    player['player_state'] = {'action': 'idle'}
    context.user_data.pop('battle_cache', None) 
    
    await player_manager.save_player_data(user_id, player) 
    if msg:
        await context.bot.send_message(chat_id, msg)
    await send_region_menu(context=context, user_id=user_id, chat_id=chat_id)


# Em: handlers/combat/main_handler.py
# (Função 'combat_callback' completa e corrigida)

async def combat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str = None) -> None:
    """
    Motor de Combate Principal (Usa o BATTLE CACHE).
    """
    query = update.callback_query
    
    if action is None and query:
        action = query.data
    elif action is None and not query:
        logger.error("combat_callback chamado sem query e sem action!")
        return

    user_id = query.from_user.id if query else update.effective_user.id
    chat_id = query.message.chat.id if query else update.effective_chat.id

    if action == 'combat_attack_menu':
        if not query: return
        await _safe_answer(query)
        kb = [
            [
                InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), 
                InlineKeyboardButton("✨ Skills", callback_data='combat_skill_menu')
            ],
            [
                InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu'),
                InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')
            ]
        ]
        try:
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            logger.debug(f"Falha ao editar markup para menu de ataque: {e}")
        return

    if query:
        await _safe_answer(query)
    
    # --- CARREGAR O CACHE DE BATALHA ---
    battle_cache = context.user_data.get('battle_cache')
    
    if not battle_cache or battle_cache.get('player_id') != user_id:
        # --- Fallback para Dungeons/PvP (que não usam cache) ---
        player_data_db = await player_manager.get_player_data(user_id)
        if not player_data_db or player_data_db.get('player_state', {}).get('action') != 'in_combat':
            idle_msg = "Você não está em combate."
            if query:
                try: await query.edit_message_caption(caption=idle_msg, reply_markup=None)
                except Exception:
                    try: await query.edit_message_text(text=idle_msg, reply_markup=None)
                    except Exception: pass
            return
        else:
            logger.debug(f"Ação de combate {action} recebida, mas SEM CACHE (é Dungeon/PvP?). Chamando _legacy_combat_callback...")
            await _legacy_combat_callback(update, context, action, player_data_db)
            return

    # --- Se chegamos aqui, temos um 'battle_cache' válido ---
    
    log = battle_cache.get('battle_log', [])
    player_stats = battle_cache.get('player_stats', {}) 
    monster_stats = battle_cache.get('monster_stats', {})
    is_auto_mode = battle_cache.get('is_auto_mode', False)

    kb_voltar = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ 𝕍𝕠𝕝𝕥𝕒𝕣", callback_data='continue_after_action')]])
    
    # --- LÓGICA DE FUGA (USA O CACHE) ---
    if action == 'combat_flee':
        if not query: return
        
        context.user_data.pop('battle_cache', None)
        player_data = await player_manager.get_player_data(user_id)
        player_data['player_state'] = {'action': 'idle'}
        
        total_stats = await player_manager.get_player_total_stats(player_data)
        player_data['current_hp'] = total_stats.get('max_hp', 50)
        player_data['current_mp'] = total_stats.get('max_mana', 10)
        await player_manager.save_player_data(user_id, player_data)
        
        try: await query.delete_message()
        except Exception: pass
        
        caption = "🏃 <b>FUGA!</b>\n\nVocê conseguiu fugir da batalha."
        await _send_battle_media(
            context, chat_id, caption, 
            "media_fuga_sucesso", 
            kb_voltar
        )
        return

    # --- LÓGICA DE ATAQUE (USA O CACHE) ---
    elif action == 'combat_attack':
        
        # --- TURNO DO JOGADOR ---
        battle_cache['turn'] = 'player'
        
        skill_id = battle_cache.pop('skill_to_use', None) 
        skill_info = SKILL_DATA.get(skill_id) if skill_id else None
        
        # Validação de Mana
        if skill_info:
            mana_cost = skill_info.get("mana_cost", 0)
            if mana_cost > 0: 
                player_data_db = await player_manager.get_player_data(user_id)
                if not spend_mana(player_data_db, mana_cost):
                    # Falhou
                    current_mp = player_data_db.get('current_mp', 0) # Pega o mana atual para o log
                    log.append(f"❗️ Você tentou usar <b>{skill_info['display_name']}</b>, mas falhou (Mana: {current_mp}/{mana_cost}).")
                    log.append("Seu personagem usa um ataque básico.")
                    skill_info = None 
                    skill_id = None
                else:
                    # Sucesso!
                    await player_manager.save_player_data(user_id, player_data_db) # Salva o pdata com o mana gasto
                    # Atualiza o cache da batalha
                    battle_cache['player_mp'] = player_data_db.get('current_mp', 0) 
                    log.append(f"✨ Você usa <b>{skill_info['display_name']}</b>! (-{mana_cost} MP)")
            else:
                log.append(f"✨ Você usa <b>{skill_info['display_name']}</b>!")
        
        # Pega os efeitos (seja da skill ou um dict vazio)
        skill_effects = skill_info.get("effects", {}) if skill_info else {}
        
        attacker_stats_modified = player_stats.copy() 
        target_stats_modified = monster_stats.copy()
        
        # (Nota: damage_mult é agora lido DENTRO do criticals.py)
        num_attacks = int(skill_effects.get("multi_hit", 0))
        defense_penetration = float(skill_effects.get("defense_penetration", 0.0))
        bonus_crit_chance = float(skill_effects.get("bonus_crit_chance", 0.0))

        if num_attacks == 0:
            initiative = attacker_stats_modified.get('initiative', 0)
            double_attack_chance = (initiative * 0.25) / 100.0
            num_attacks = 2 if random.random() < min(double_attack_chance, 0.50) else 1
            if num_attacks == 2 and not skill_id:
                log.append("⚡ 𝐀𝐓𝐀𝐐𝐔𝐄 𝐃𝐔𝐏𝐋𝐎!")

        if defense_penetration > 0:
            target_stats_modified['defense'] = int(target_stats_modified['defense'] * (1.0 - defense_penetration))
            log.append(f"💨 Você ignora {defense_penetration*100:.0f}% da defesa!")
        if bonus_crit_chance > 0:
            attacker_stats_modified['luck'] += int(bonus_crit_chance * 140) 
            log.append(f"🎯 Mirando um ponto vital...")
        if "low_hp_dmg_boost" in skill_effects:
            player_hp_percent = battle_cache.get('player_hp', 1) / attacker_stats_modified.get('max_hp', 1)
            if player_hp_percent < 0.3:
                # O 'criticals.py' não lê isto, então o damage_mult tem de ser
                # aplicado aqui... Oh, espera. 'criticals.py' NÃO lê low_hp_dmg_boost.
                # A tua lógica antiga estava a modificar 'damage_mult' aqui.
                
                # VAMOS REVER:
                # A tua lógica antiga era:
                # damage_mult = float(skill_effects.get("damage_multiplier", 1.0))
                # ...
                # if "low_hp_dmg_boost" in skill_effects:
                #     ...
                #     damage_mult *= (1.0 + skill_effects.get("low_hp_dmg_boost", 0.0))
                # ...
                # player_damage = max(1, int(player_damage_raw * damage_mult))
                
                # A lógica de 'criticals.py' SÓ lê 'damage_multiplier'.
                # Precisamos de *adicionar* o 'low_hp_dmg_boost' ao 'skill_effects'
                # antes de o passarmos para 'criticals.py'
                
                # Vamos criar uma cópia mutável dos efeitos
                skill_effects_modified = skill_effects.copy()
                
                if player_hp_percent < 0.3:
                    current_mult = skill_effects_modified.get("damage_multiplier", 1.0)
                    boost = 1.0 + skill_effects.get("low_hp_dmg_boost", 0.0)
                    skill_effects_modified["damage_multiplier"] = current_mult * boost
                    log.append(f"🩸 Fúria Selvagem!")
                
                # Passa os efeitos modificados para a fórmula de dano
                skill_effects_to_use = skill_effects_modified
            else:
                # Passa os efeitos originais
                skill_effects_to_use = skill_effects

        if "debuff_target" in skill_effects:
            debuff = skill_effects["debuff_target"]
            if debuff.get("stat") == "defense":
                reduction = abs(float(debuff.get("value", 0.0)))
                monster_stats['defense'] = int(monster_stats['defense'] * (1.0 - reduction))
                target_stats_modified['defense'] = monster_stats['defense']
                log.append(f"🛡️ A defesa do inimigo foi reduzida!")
        
        # (Se 'skill_effects_to_use' não foi definido no if do low_hp, define-o agora)
        if 'skill_effects_to_use' not in locals():
            skill_effects_to_use = skill_effects
            
        monster_defeated_in_turn = False
        
        # --- !!! ESTE É O BLOCO DE CÓDIGO CORRIGIDO !!! ---
        for i in range(num_attacks):
            
            # 1. Passa os 'skill_effects' (que contêm o damage_type E o multiplier)
            #    para a fórmula de dano. Usamos 'skill_effects_to_use'
            #    para incluir a lógica do 'low_hp_dmg_boost'.
            player_damage_raw, is_crit, is_mega = criticals.roll_damage(
                attacker_stats_modified, 
                target_stats_modified, 
                skill_effects_to_use # <--- CORREÇÃO AQUI
            )

            # 2. O dano 'raw' já vem com o multiplicador e o tipo (mágico) aplicado
            #    pelo 'criticals.py'. Não precisamos multiplicar de novo.
            player_damage = max(1, int(player_damage_raw))
            
            # --- !!! FIM DA CORREÇÃO !!! ---

            log.append(f"➡️ {battle_cache['player_name']} ataca e causa {player_damage} de dano.")
            if is_mega: log.append("💥💥 𝐌𝐄𝐆𝐀 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎!")
            elif is_crit: log.append("💥 𝐃𝐀𝐍𝐎 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎!")
            
            monster_stats['hp'] = int(monster_stats.get('hp', 0)) - player_damage
            
            if monster_stats['hp'] <= 0:
                monster_defeated_in_turn = True
                break
        # --- FIM DO BLOCO CORRIGIDO ---

        # 3. Atualizar Mídia (Turno do Jogador)
        battle_cache['battle_log'] = log
        caption_turno_jogador = await format_combat_message_from_cache(battle_cache)
        
        await _edit_media_or_caption(
            context, battle_cache, 
            caption_turno_jogador, 
            battle_cache['player_media_id'], 
            battle_cache['player_media_type'],
            reply_markup=None 
        )
        if not is_auto_mode:
            await asyncio.sleep(2) 

        # 4. Processar Resultado (Vitória ou Turno do Monstro)
        if monster_defeated_in_turn:
            # --- VITÓRIA ---
            log.append(f"🏆 <b>{monster_stats['name']} foi derrotado!</b>") # <-- USA O 'name' DO CACHE
            battle_cache['battle_log'] = log
            
            pdata = await player_manager.get_player_data(user_id)
            
            # --- CORREÇÃO: Usa a função de cache ---
            victory_summary = await rewards.apply_and_format_victory_from_cache(pdata, battle_cache)
            _, _, level_up_msg = player_manager.check_and_apply_level_up(pdata) 
            if level_up_msg:
                victory_summary += level_up_msg
            
            pdata['current_hp'] = player_stats.get('max_hp', 50)
            pdata['current_mp'] = player_stats.get('max_mana', 10)
            pdata['player_state'] = {'action': 'idle'}
            
            await player_manager.save_player_data(user_id, pdata)
            context.user_data.pop('battle_cache', None)
            
            await _edit_media_or_caption(
                context, battle_cache, 
                victory_summary,
                battle_cache['player_media_id'], 
                battle_cache['player_media_type'],
                reply_markup=kb_voltar
            )
            return 
            
        else:
            # --- TURNO DO MONSTRO ---
            battle_cache['turn'] = 'monster'
            
            active_cooldowns = battle_cache.setdefault("skill_cooldowns", {})
            skills_off_cooldown = []
            if active_cooldowns:
                for skill_id_cd, turns_left in list(active_cooldowns.items()):
                    active_cooldowns[skill_id_cd] = turns_left - 1
                    if active_cooldowns[skill_id_cd] <= 0:
                        skills_off_cooldown.append(skill_id_cd)
                
                for skill_id_cd in skills_off_cooldown:
                    del active_cooldowns[skill_id_cd]
                    skill_name = SKILL_DATA.get(skill_id_cd, {}).get('display_name', 'Habilidade')
                    log.append(f"🔔 <b>{skill_name}</b> está pronta!")
            
            initiative = player_stats.get('initiative', 0)
            dodge_chance = (initiative * 0.4) / 100.0
            dodge_chance = min(dodge_chance, 0.75)

            if random.random() < dodge_chance: 
                log.append("💨 Você se esquivou do ataque!")
            else:
                monster_damage, m_is_crit, m_is_mega = criticals.roll_damage(monster_stats, player_stats, {})
                log.append(f"⬅️ {monster_stats['name']} ataca e causa {monster_damage} de dano.")
                if m_is_mega: log.append("‼️ 𝕄𝔼𝔾𝔸 ℂℝ𝕀́𝕋𝕀ℂ𝕆 𝕚𝕟𝕚𝕞𝕚𝕘𝕠!")
                elif m_is_crit: log.append("❗️ 𝔻𝔸ℕ𝕆 ℂℝ𝕀́𝕋𝕀ℂ𝕆 𝕚𝕟𝕚𝕞𝕚𝕘𝕠!")
                
                battle_cache['player_hp'] = int(battle_cache.get('player_hp', 0)) - monster_damage
                
                if battle_cache['player_hp'] <= 0: # Derrota
                    log.append("☠️ <b>Você foi derrotado!</b>")
                    battle_cache['battle_log'] = log
                    
                    pdata = await player_manager.get_player_data(user_id)
                    # --- CORREÇÃO: Usa a função de cache ---
                    defeat_summary, _ = rewards.process_defeat_from_cache(pdata, battle_cache)
                    
                    pdata['current_hp'] = player_stats.get('max_hp', 50)
                    pdata['current_mp'] = player_stats.get('max_mana', 10)
                    pdata['player_state'] = {'action': 'idle'}
                    
                    await player_manager.save_player_data(user_id, pdata)
                    context.user_data.pop('battle_cache', None)
                    
                    await _edit_media_or_caption(
                        context, battle_cache, 
                        defeat_summary, 
                        (file_id_manager.get_file_data("media_derrota_cacada") or {}).get('id'), 
                        (file_id_manager.get_file_data("media_derrota_cacada") or {}).get('type', 'photo'),
                        reply_markup=kb_voltar
                    )
                    return # Fim da batalha

    # 5. Atualizar Mídia (Turno do Monstro)
    battle_cache['battle_log'] = log
    caption_turno_monstro = await format_combat_message_from_cache(battle_cache)
    
    kb_player_turn = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), 
            InlineKeyboardButton("✨ Skills", callback_data='combat_skill_menu')
        ],
        [
            InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu'),
            InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')
        ]
    ])
    
    # Volta para a Mídia do Monstro
    await _edit_media_or_caption(
        context, battle_cache, 
        caption_turno_monstro, 
        battle_cache['monster_media_id'], 
        battle_cache['monster_media_type'],
        reply_markup=kb_player_turn
    )
    
    if is_auto_mode:
        await asyncio.sleep(2) 
        fake_user = type("User", (), {"id": user_id})()
        fake_query = CallbackQuery(id=f"auto_{user_id}", from_user=fake_user, chat_instance="auto", data="combat_attack")
        fake_update = Update(update_id=0, callback_query=fake_query)
        await combat_callback(fake_update, context, action='combat_attack')
        return

# Em: handlers/combat/main_handler.py

async def _legacy_combat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, player_data: dict):
    """
    (VERSÃO CORRIGIDA)
    Função 'combat_callback' antiga, usada como fallback
    para sistemas (Dungeon/PvP) que AINDA usam player_state.
    """
    logger.debug("[LEGACY COMBAT] Executando fallback de combate (sem cache)")
    query = update.callback_query
    user_id = player_data["user_id"]
    chat_id = update.effective_chat.id

    state = player_data.get('player_state', {})
    combat_details = dict(state.get('details', {}))
    is_auto_mode = combat_details.get('auto_mode', False)
    log = list(combat_details.get('battle_log', []))
    player_total_stats = await player_manager.get_player_total_stats(player_data) 
    
    monster_stats = {
        'name': combat_details.get('monster_name', 'Inimigo'),
        'hp': combat_details.get('monster_hp', 1),
        'max_hp': combat_details.get('monster_max_hp', 1),
        'attack': combat_details.get('monster_attack', 1), 
        'defense': combat_details.get('monster_defense', 0),
        'luck': combat_details.get('monster_luck', 5), 
        'initiative': combat_details.get('monster_initiative', 0),
        'gold_drop': combat_details.get('monster_gold_drop', 0),
        'xp_reward': combat_details.get('monster_xp_reward', 0),
        'loot_table': combat_details.get('loot_table', []),
        'id': combat_details.get('id'),
        'is_elite': combat_details.get('is_elite', False),
    }
    
    in_dungeon = "dungeon_ctx" in combat_details

    # --- LÓGICA DE FUGA (Legada) ---
    if action == 'combat_flee':
        if not query: return
        
        # (Lógica de fuga permanece a mesma)
        if random.random() <= 0.5: # Sucesso
            durability.apply_end_of_battle_wear(player_data, combat_details, log)
            
            player_data['current_hp'] = player_total_stats.get('max_hp', 50)
            player_data['current_mp'] = player_total_stats.get('max_mana', 10)
            await player_manager.save_player_data(user_id, player_data) 
            
            try: await query.delete_message()
            except Exception: pass
            
            if in_dungeon:
                await dungeons_runtime.fail_dungeon_run(update, context, user_id, chat_id, "Você fugiu da batalha")
                return
            else:
                caption = "🏃 <b>FUGA!</b>\n\nVocê conseguiu fugir da batalha."
                keyboard = [[InlineKeyboardButton("➡️ Continuar", callback_data='continue_after_action')]]
                await _send_battle_media(
                    context, chat_id, caption, 
                    "media_fuga_sucesso", 
                    InlineKeyboardMarkup(keyboard)
                )
                return
        else: # Falha na Fuga
            log.append("🏃 𝑺𝒖𝒂 𝒕𝒆𝒏𝒕𝒂𝒕𝒊𝒗𝒂 𝒅𝒆 𝒇𝒖𝒈𝒂 𝒇𝒂𝒍𝒉𝒐𝒖!")
            
            dodge_chance = await player_manager.get_player_dodge_chance(player_total_stats)
            if random.random() < dodge_chance: 
                log.append("💨 Você se esquivou do ataque!")
            else:
                monster_damage, m_is_crit, m_is_mega = criticals.roll_damage(monster_stats, player_total_stats, {})
                log.append(f"⬅️ {monster_stats['name']} ataca e causa {monster_damage} de dano.")
                if m_is_mega: log.append("‼️ <b>MEGA CRÍTICO inimigo!</b>")
                elif m_is_crit: log.append("❗️ <b>DANO CRÍTICO inimigo!</b>")
                player_data['current_hp'] = int(player_data.get('current_hp', 0)) - monster_damage
                combat_details["took_damage"] = True
            
            if player_data['current_hp'] <= 0: # Derrota
                durability.apply_end_of_battle_wear(player_data, combat_details, log)
                if in_dungeon:
                    await dungeons_runtime.fail_dungeon_run(update, context, user_id, chat_id, "Você foi derrotado")
                    return
                
                defeat_summary, _ = rewards.process_defeat(player_data, combat_details)
                player_data['current_hp'] = int(player_total_stats.get('max_hp', 50))
                player_data['current_mp'] = int(player_total_stats.get('max_mana', 10))
                player_data['player_state'] = {'action': 'idle'}
                await player_manager.save_player_data(user_id, player_data) 
                
                try: await query.delete_message()
                except Exception: pass
                
                keyboard = [[InlineKeyboardButton("➡️ ℂ𝕠𝕟𝕥𝕚𝕟𝕦𝕒𝕣", callback_data='continue_after_action')]]
                await _send_battle_media(
                    context, chat_id, defeat_summary, 
                    "media_derrota_cacada", 
                    InlineKeyboardMarkup(keyboard)
                )
                return

    # ======================================================
    # --- (INÍCIO) LÓGICA DE ATAQUE (Legada - CORRIGIDA) ---
    # ======================================================
    elif action == 'combat_attack':
        
        skill_id = combat_details.pop('skill_to_use', None) 
        skill_info = SKILL_DATA.get(skill_id) if skill_id else None
        
        attacker_stats_modified = player_total_stats.copy()
        target_stats_modified = monster_stats.copy()
        skill_effects = {}
        
        # --- 1. Validação de Skill e Mana ---
        if skill_info:
            mana_cost = skill_info.get("mana_cost", 0)
            if mana_cost > 0:
                max_mp = player_total_stats.get('max_mana', 10)
                current_mp = player_data.get('current_mp', max_mp)
                
                if current_mp < mana_cost:
                    log.append(f"❗️ Você tentou usar <b>{skill_info['display_name']}</b>, mas não tem Mana suficiente (Custo: {mana_cost} MP).")
                    log.append("Seu personagem usa um ataque básico.")
                    skill_info = None 
                    skill_id = None
                else:
                    # (SUCESSO) Gasta o Mana
                    spend_mana(player_data, mana_cost) 
                    log.append(f"✨ Você usa <b>{skill_info['display_name']}</b>! (-{mana_cost} MP)")
            else:
                log.append(f"✨ Você usa <b>{skill_info['display_name']}</b>!")
        
        # --- 2. Aplicação de Efeitos (Se a skill foi usada) ---
        if skill_info:
            skill_effects = skill_info.get("effects", {})
            
            defense_penetration = float(skill_effects.get("defense_penetration", 0.0))
            bonus_crit_chance = float(skill_effects.get("bonus_crit_chance", 0.0))

            if defense_penetration > 0:
                target_stats_modified['defense'] = int(target_stats_modified['defense'] * (1.0 - defense_penetration))
                log.append(f"💨 Você ignora {defense_penetration*100:.0f}% da defesa!")
            if bonus_crit_chance > 0:
                # (Aumenta a sorte temporariamente para o cálculo do crítico)
                attacker_stats_modified['luck'] += int(bonus_crit_chance * 140) 
                log.append(f"🎯 Mirando um ponto vital...")
            if "low_hp_dmg_boost" in skill_effects:
                player_hp_percent = player_data.get('current_hp', 1) / attacker_stats_modified.get('max_hp', 1)
                if player_hp_percent < 0.3:
                    # (Aumenta o multiplicador de dano)
                    skill_effects["damage_multiplier"] = float(skill_effects.get("damage_multiplier", 1.0)) * (1.0 + skill_effects.get("low_hp_dmg_boost", 0.0))
                    log.append(f"🩸 Fúria Selvagem!")
            if "debuff_target" in skill_effects:
                debuff = skill_effects["debuff_target"]
                if debuff.get("stat") == "defense":
                    reduction = abs(float(debuff.get("value", 0.0)))
                    combat_details['monster_defense'] = int(combat_details['monster_defense'] * (1.0 - reduction))
                    target_stats_modified['defense'] = combat_details['monster_defense']
                    log.append(f"🛡️ A defesa do inimigo foi reduzida!")
        
        # --- 3. Cálculo de Dano e Multi-Hit ---
        
        # Define o número de ataques (baseado na skill ou chance de ataque duplo)
        num_attacks = int(skill_effects.get("multi_hit", 0))
        if num_attacks == 0: # Se não for multi-hit, verifica ataque duplo
            initiative = attacker_stats_modified.get('initiative', 0)
            double_attack_chance = (initiative * 0.25) / 100.0
            num_attacks = 2 if random.random() < min(double_attack_chance, 0.50) else 1
            if num_attacks == 2 and not skill_id:
                log.append("⚡ 𝐀𝐓𝐀𝐐𝐔𝐄 𝐃𝐔𝐏𝐋𝐎!")

        monster_defeated_in_turn = False
        
        for i in range(num_attacks):
            # Passa os 'skill_effects' para o 'roll_damage'
            player_damage_raw, is_crit, is_mega = criticals.roll_damage(
                attacker_stats_modified, 
                target_stats_modified, 
                skill_effects # <--- CORREÇÃO AQUI
            )
            
            # (O damage_multiplier já deve ser aplicado dentro do roll_damage)
            # (Vamos assumir que roll_damage lida com damage_multiplier)
            player_damage = max(1, int(player_damage_raw)) 
            
            log.append(f"➡️ {player_data.get('character_name','Você')} ataca e causa {player_damage} de dano.")
            if is_mega: log.append("💥💥 𝐌𝐄𝐆𝐀 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎!")
            elif is_crit: log.append("💥 𝐃𝐀𝐍𝐎 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎!")
            
            combat_details['monster_hp'] = int(combat_details.get('monster_hp', 0)) - player_damage
            combat_details["used_weapon"] = True
            if combat_details['monster_hp'] <= 0:
                monster_defeated_in_turn = True
                break

        # --- 4. Resultado (Vitória ou Turno do Monstro) ---
        if monster_defeated_in_turn: 
            # (Toda a lógica de Vitória permanece a mesma)
            durability.apply_end_of_battle_wear(player_data, combat_details, log)
            log.append(f"🏆 <b>{monster_stats['name']} foi derrotado!</b>")
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
            _, _, level_up_msg = player_manager.check_and_apply_level_up(player_data) 
            if level_up_msg:
                victory_summary += level_up_msg
            player_data['current_hp'] = player_total_stats.get('max_hp', 50)
            player_data['current_mp'] = player_total_stats.get('max_mana', 10)
            player_data['player_state'] = {'action': 'idle'}
            await player_manager.save_player_data(user_id, player_data)
            if query:
                try: await query.delete_message()
                except Exception: pass
            player_media = _get_class_media(player_data, purpose="vitoria")
            media_key = None
            if player_media and player_media.get("id"):
                media_key = player_media.get("id") 
            keyboard = [[InlineKeyboardButton("⬅️ 𝕍𝕠𝕝𝕥𝕒𝕣", callback_data='continue_after_action')]]
            await _send_battle_media(
                context, chat_id, victory_summary, 
                media_key, 
                InlineKeyboardMarkup(keyboard)
            )
            return

        else: 
            # --- TURNO DO MONSTRO (Legado - Sem alterações) ---
            active_cooldowns = combat_details.setdefault("skill_cooldowns", {})
            skills_off_cooldown = []
            if active_cooldowns:
                for skill_id_cd, turns_left in list(active_cooldowns.items()):
                    active_cooldowns[skill_id_cd] = turns_left - 1
                    if active_cooldowns[skill_id_cd] <= 0:
                        skills_off_cooldown.append(skill_id_cd)
                for skill_id_cd in skills_off_cooldown:
                    del active_cooldowns[skill_id_cd]
                    skill_name = SKILL_DATA.get(skill_id_cd, {}).get('display_name', 'Habilidade')
                    log.append(f"🔔 <b>{skill_name}</b> está pronta para ser usada!")
            
            dodge_chance = await player_manager.get_player_dodge_chance(player_total_stats)
            if random.random() < dodge_chance: 
                log.append("💨 Você se esquivou do ataque!")
            else:
                monster_damage, m_is_crit, m_is_mega = criticals.roll_damage(monster_stats, player_total_stats, {})
                log.append(f"⬅️ {monster_stats['name']} ataca e causa {monster_damage} de dano.")
                if m_is_mega: log.append("‼️ 𝕄𝔼𝔾𝔸 ℂℝ𝕀́𝕋𝕀ℂ𝕆 𝕚𝕟𝕚𝕞𝕚𝕘𝕠!")
                elif m_is_crit: log.append("❗️ 𝔻𝔸ℕ𝕆 ℂℝ𝕀́𝕋𝕀ℂ𝕆 𝕚𝕟𝕚𝕞𝕚𝕘𝕠!")
                player_data['current_hp'] = int(player_data.get('current_hp', 0)) - monster_damage
                combat_details["took_damage"] = True
                
                if player_data['current_hp'] <= 0: # Derrota
                    durability.apply_end_of_battle_wear(player_data, combat_details, log)
                    if in_dungeon:
                        await dungeons_runtime.fail_dungeon_run(update, context, user_id, chat_id, "Você foi derrotado")
                        return
                    
                    defeat_summary, _ = rewards.process_defeat(player_data, combat_details)
                    player_data['current_hp'] = int(player_total_stats.get('max_hp', 50))
                    player_data['current_mp'] = int(player_total_stats.get('max_mana', 10))
                    player_data['player_state'] = {'action': 'idle'}
                    await player_manager.save_player_data(user_id, player_data)
                    
                    try: await query.delete_message()
                    except Exception: pass
                    keyboard = [[InlineKeyboardButton("➡️ ℂ𝕠𝕟𝕥𝕚𝕟𝕦𝕒𝕣", callback_data='continue_after_action')]]
                    await _send_battle_media(
                        context, chat_id, defeat_summary, 
                        "media_derrota_cacada", 
                        InlineKeyboardMarkup(keyboard)
                    )
                    return

    # --- (FIM) LÓGICA DE ATAQUE (Legada - CORRIGIDA) ---
    
    # --- Atualização final do menu (Legado) ---
    combat_details['battle_log'] = log[-15:]
    player_data['player_state']['details'] = combat_details
    await player_manager.save_player_data(user_id, player_data) 

    new_text = await format_combat_message(player_data, player_stats=player_total_stats) 
    
    if is_auto_mode:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🛑 PARAR AUTO-CAÇA", callback_data='autohunt_stop')]])
    else:
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), 
                InlineKeyboardButton("✨ Skills", callback_data='combat_skill_menu')
            ],
            [
                InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu'),
                InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')
            ]
        ])

    if query:
        await _edit_caption_only(query, new_text, kb)

    if is_auto_mode and combat_details.get('monster_hp', 0) > 0:
        await asyncio.sleep(3)
        pass

# Handler Registrado
combat_handler = CallbackQueryHandler(combat_callback, pattern=r'^(combat_attack|combat_flee|combat_attack_menu)$')