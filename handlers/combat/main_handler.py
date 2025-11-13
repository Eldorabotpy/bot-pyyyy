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
from handlers.class_evolution_handler import open_evolution_menu
from handlers.hunt_handler import start_hunt # (Usado pelo fallback de auto-hunt)
from modules.game_data.skills import SKILL_DATA
from modules.player.actions import spend_mana
from handlers.profile_handler import _get_class_media
from modules.dungeons.runtime import _send_battle_media
from modules import file_ids as file_id_manager
from modules.combat import combat_engine

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


async def combat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str = None) -> None:
    """
    Motor de Combate Principal (Usa o BATTLE CACHE).
    (VERSÃO REFATORADA - CHAMA O 'combat_engine')
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
        # (Esta parte permanece idêntica)
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
    
    # --- (A lógica de Fallback para o Legado permanece idêntica) ---
    if not battle_cache or battle_cache.get('player_id') != user_id:
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
            # Chama a versão LEGADA, que também será refatorada
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
        # (Esta parte permanece idêntica)
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
        await _send_battle_media(context, chat_id, caption, "media_fuga_sucesso", kb_voltar)
        return

    # --- LÓGICA DE ATAQUE (USA O CACHE) ---
    elif action == 'combat_attack':
        
        battle_cache['turn'] = 'player'
        
        skill_id = battle_cache.pop('skill_to_use', None) 
        # 🟢 NOVO: Extrai a action_type (deve ser definida no skill_handler)
        action_type = battle_cache.pop('action_type', 'attack') 
        
        skill_info = SKILL_DATA.get(skill_id) if skill_id else None
        
        # Variável para controlar se devemos pular o turno do monstro
        skip_monster_turn = False
        
        # --- LÓGICA DE SKILL/ATAQUE ---
        
        if skill_info:
            mana_cost = skill_info.get("mana_cost", 0)
            
            # ** Assumimos que a verificação de Mana e o gasto de Cooldown **
            # ** já foram aplicados no combat_use_skill_callback! **
            
            log.append(f"✨ Você usa <b>{skill_info['display_name']}</b>! (-{mana_cost} MP)")
            
            # 🟢 LÓGICA DE SKILL DE SUPORTE
            if action_type == 'support':
                # 1. Aplicar Efeitos de Suporte (Cura, Buffs, etc.)
                # O motor deve retornar os efeitos aplicados aqui (por exemplo, cura)
                
                # Exemplo: Se a skill curar 10 HP
                # battle_cache['player_hp'] = min(battle_cache.get('player_hp', 0) + 10, player_stats.get('max_hp'))
                
                log.append("➕ <i>Efeitos de suporte aplicados.</i>") 
                
                # 2. Marcar para Pular o Turno do Monstro
                skip_monster_turn = True
                
            # 🟢 LÓGICA DE SKILL DE ATAQUE (Dano)
            else: # action_type == 'attack' ou não definido
                # 2. CHAMAMOS O MOTOR UNIFICADO (Processa Dano)
                resultado_combate = await combat_engine.processar_acao_combate(
                    attacker_stats=player_stats,
                    target_stats=monster_stats,
                    skill_id=skill_id,
                    attacker_current_hp=battle_cache.get('player_hp', 9999)
                )

                # 3. Aplicamos os resultados
                player_damage = resultado_combate["total_damage"]
                log.extend(resultado_combate["log_messages"])
                
                if skill_info and "debuff_target" in skill_info.get("effects", {}):
                    # Lógica para aplicar debuffs ao monstro (seria implementada aqui)
                    pass 

                monster_stats['hp'] = int(monster_stats.get('hp', 0)) - player_damage
                monster_defeated_in_turn = monster_stats['hp'] <= 0
        
        else:
            # Caso use ataque básico (sem skill)
            log.append("⚔️ Você realiza um ataque básico.")
            resultado_combate = await combat_engine.processar_acao_combate(
                attacker_stats=player_stats, target_stats=monster_stats, skill_id=None,
                attacker_current_hp=battle_cache.get('player_hp', 9999)
            )
            player_damage = resultado_combate["total_damage"]
            log.extend(resultado_combate["log_messages"])
            monster_stats['hp'] = int(monster_stats.get('hp', 0)) - player_damage
            monster_defeated_in_turn = monster_stats['hp'] <= 0
            
        # 4. Atualizar Mídia (Pós-Ação do Jogador)
        battle_cache['battle_log'] = log
        caption_turno_jogador = await format_combat_message_from_cache(battle_cache)
        
        # 5. SAÍDA PARA SKILL DE SUPORTE
        if skip_monster_turn:
            battle_cache['turn'] = 'player' # Continua o turno do jogador
            
            # Recria o teclado principal para permitir outra ação
            kb_player_turn = InlineKeyboardMarkup([
                [InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), InlineKeyboardButton("✨ Skills", callback_data='combat_skill_menu')],
                [InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu'), InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')]
            ])
            
            # Edita a mensagem para mostrar os novos logs e a vida/mana atualizada
            await _edit_media_or_caption(
                context, battle_cache, 
                caption_turno_jogador, 
                battle_cache['player_media_id'], 
                battle_cache['player_media_type'],
                reply_markup=kb_player_turn 
            )
            return # ⬅️ FINALIZA A FUNÇÃO: o monstro não ataca.
        # 4. Processar Resultado (Vitória ou Turno do Monstro)
        if monster_defeated_in_turn:
            # (A lógica de VITÓRIA permanece idêntica)
            log.append(f"🏆 <b>{monster_stats['name']} foi derrotado!</b>")
            battle_cache['battle_log'] = log
            pdata = await player_manager.get_player_data(user_id)
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
            # (A lógica do TURNO DO MONSTRO permanece idêntica)
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
                    # (A lógica de DERROTA permanece idêntica)
                    log.append("☠️ <b>Você foi derrotado!</b>")
                    battle_cache['battle_log'] = log
                    pdata = await player_manager.get_player_data(user_id)
                    defeat_summary, _ = rewards.process_defeat_from_cache(pdata, battle_cache)
                    pdata['current_hp'] = 0 
                    pdata['current_mp'] = battle_cache.get('player_mp', player_stats.get('max_mana', 10))
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
    # (Esta parte permanece idêntica)
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
    
    await _edit_media_or_caption(
        context, battle_cache, 
        caption_turno_monstro, 
        battle_cache['monster_media_id'], 
        battle_cache['monster_media_type'],
        reply_markup=kb_player_turn
    )
    
    if is_auto_mode:
        # (Lógica de auto-hunt permanece idêntica)
        await asyncio.sleep(2) 
        fake_user = type("User", (), {"id": user_id})()
        fake_query = CallbackQuery(id=f"auto_{user_id}", from_user=fake_user, chat_instance="auto", data="combat_attack")
        fake_update = Update(update_id=0, callback_query=fake_query)
        await combat_callback(fake_update, context, action='combat_attack')
        return
    
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
        # 🟢 NOVO: Extrai a action_type (deve ser 'support' se for buff/cura)
        action_type = combat_details.pop('action_type', 'attack') 
        
        skill_info = SKILL_DATA.get(skill_id) if skill_id else None
        
        # Variável para controlar se devemos pular o turno do monstro
        skip_monster_turn = False
        
        # --- LÓGICA DE SKILL ---
        
        if skill_info:
            mana_cost = skill_info.get("mana_cost", 0)
            
            # Nota: O gasto de Mana já foi feito no combat_use_skill_callback,
            # mas o log é adicionado aqui.
            log.append(f"✨ Você usa <b>{skill_info['display_name']}</b>! (-{mana_cost} MP)")
            
            # 🟢 LÓGICA DE SKILL DE SUPORTE
            if action_type == 'support':
                # 1. Aplicar Efeitos de Suporte (Cura, Buffs, etc.)
                # *Neste ponto, você deve chamar a lógica real para aplicar buffs/curas ao player_data/combat_details*
                log.append("➕ <i>Efeitos de suporte aplicados.</i>") # Placeholder
                skip_monster_turn = True
                combat_details["turn"] = 'player' # Reinicia o turno para o jogador
                
            # 🟢 LÓGICA DE SKILL DE ATAQUE (Dano)
            else: # action_type == 'attack' ou não definido
                # 2. CHAMAMOS O MOTOR UNIFICADO (Processa Dano)
                resultado_combate = await combat_engine.processar_acao_combate(
                    attacker_stats=player_total_stats, # Stats totais do jogador
                    target_stats=monster_stats,
                    skill_id=skill_id,
                    attacker_current_hp=player_data.get('current_hp', 9999)
                )

                # 3. Aplicamos os resultados
                player_damage = resultado_combate["total_damage"]
                log.extend(resultado_combate["log_messages"])
                
                if skill_info and "debuff_target" in skill_info.get("effects", {}):
                     # Lógica para aplicar debuffs ao monstro
                     pass

                combat_details['monster_hp'] = int(combat_details.get('monster_hp', 0)) - player_damage
                combat_details["used_weapon"] = True
                monster_defeated_in_turn = combat_details['monster_hp'] <= 0

        else:
            # Caso use ataque básico (sem skill)
            log.append("⚔️ Você realiza um ataque básico.")
            resultado_combate = await combat_engine.processar_acao_combate(
                attacker_stats=player_total_stats, target_stats=monster_stats, skill_id=None,
                attacker_current_hp=player_data.get('current_hp', 9999)
            )
            player_damage = resultado_combate["total_damage"]
            log.extend(resultado_combate["log_messages"])
            combat_details['monster_hp'] = int(combat_details.get('monster_hp', 0)) - player_damage
            combat_details["used_weapon"] = True
            monster_defeated_in_turn = combat_details['monster_hp'] <= 0


        # --- 4. Resultado (Vitória, Suporte ou Turno do Monstro) ---
        if monster_defeated_in_turn: 
            # (Toda a lógica de Vitória permanece a mesma)
            durability.apply_end_of_battle_wear(player_data, combat_details, log)
            log.append(f"🏆 <b>{monster_stats['name']} foi derrotado!</b>")
            
            # Lógica de Evolução, Dungeon, Recompensas, etc. (Vitória)
            if combat_details.get('evolution_trial'):
                target_class = combat_details.get('evolution_trial').get('target_class')
                success, message = await class_evolution_service.finalize_evolution(user_id, target_class)
                if query: await query.delete_message()
                await context.bot.send_message(chat_id=chat_id, text=f"🎉 {message} 🎉", parse_mode="HTML")
                # NOME DA FUNÇÃO CORRIGIDO
                await open_evolution_menu(update, context) 
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

        elif skip_monster_turn:
            # ⬅️ SAÍDA PARA SKILL DE SUPORTE (Legado)
            
            # --- Atualização final do menu (Legado) ---
            combat_details['battle_log'] = log[-15:]
            player_data['player_state']['details'] = combat_details
            await player_manager.save_player_data(user_id, player_data) 
            
            new_text = await format_combat_message(player_data, player_stats=player_total_stats) 
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), InlineKeyboardButton("✨ Skills", callback_data='combat_skill_menu')],
                [InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu'), InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')]
            ])
            if query:
                await _edit_caption_only(query, new_text, kb)
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