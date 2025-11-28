# handlers/combat/main_handler.py
# (VERSÃO FINAL CORRIGIDA - HP na Morte, Custo de Mana e Lógica de Cura de Suporte)

import logging
import random
import asyncio
import math
from typing import Optional, Dict, Any 
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaVideo, InputMediaPhoto, CallbackQuery
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

# Importações dos seus módulos
from modules import player_manager, game_data, class_evolution_service, clan_manager
# IMPORTANTE: Adicionado mission_manager
from modules import mission_manager 
from handlers.menu.region import send_region_menu

# --- Importa OS DOIS formatadores ---
from handlers.utils import format_combat_message_from_cache, format_combat_message

from modules.combat import durability, criticals, rewards
from modules.dungeons import runtime as dungeons_runtime
from handlers.class_evolution_handler import open_evolution_menu
from handlers.hunt_handler import start_hunt 
from modules.game_data.skills import SKILL_DATA
from modules.player.actions import spend_mana
from handlers.profile_handler import _get_class_media
from modules.dungeons.runtime import _send_battle_media
from modules import file_ids as file_id_manager
from modules.combat import combat_engine

logger = logging.getLogger(__name__)

# ================================================
# INÍCIO: FUNÇÃO AUXILIAR DE SKILL
# ================================================
def _get_player_skill_data_by_rarity(pdata: dict, skill_id: str) -> Optional[dict]:
    """
    Helper para buscar os dados de uma skill (SKILL_DATA) e mesclá-los
    com os dados da raridade que o jogador possui.
    """
    base_skill = SKILL_DATA.get(skill_id)
    if not base_skill: 
        return None # Skill não existe

    if "rarity_effects" not in base_skill:
        return base_skill

    player_skills = pdata.get("skills", {})
    if not isinstance(player_skills, dict):
        rarity = "comum"
    else:
        player_skill_instance = player_skills.get(skill_id)
        if not player_skill_instance:
            rarity = "comum"
        else:
            rarity = player_skill_instance.get("rarity", "comum")

    merged_data = base_skill.copy()
    rarity_data = base_skill["rarity_effects"].get(rarity, base_skill["rarity_effects"].get("comum", {}))
    merged_data.update(rarity_data)
    
    return merged_data
# ================================================
# FIM: FUNÇÃO AUXILIAR DE SKILL
# ================================================

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
        if not new_media_id:
            new_media_id = battle_cache['monster_media_id']
            new_media_type = battle_cache['monster_media_type']
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
    """Motor de Combate Principal (Usa o BATTLE CACHE)."""
    query = update.callback_query
    
    if action is None and query: action = query.data
    elif action is None and not query: return

    user_id = query.from_user.id if query else update.effective_user.id
    chat_id = query.message.chat.id if query else update.effective_chat.id

    if action == 'combat_attack_menu':
        if not query: return
        await _safe_answer(query)
        kb = [
            [InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), InlineKeyboardButton("✨ Skills", callback_data='combat_skill_menu')],
            [InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu'), InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')]
        ]
        try: await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
        except Exception: pass
        return

    if query: await _safe_answer(query)
    
    battle_cache = context.user_data.get('battle_cache')
    
    # Fallback para legado
    if not battle_cache or battle_cache.get('player_id') != user_id:
        player_data_db = await player_manager.get_player_data(user_id)
        if not player_data_db or player_data_db.get('player_state', {}).get('action') != 'in_combat':
            if query:
                try: await query.edit_message_caption(caption="Você não está em combate.", reply_markup=None)
                except: pass
            return
        else:
            await _legacy_combat_callback(update, context, action, player_data_db)
            return

    log = battle_cache.get('battle_log', [])
    player_stats = battle_cache.get('player_stats', {}) 
    monster_stats = battle_cache.get('monster_stats', {})
    is_auto_mode = battle_cache.get('is_auto_mode', False)
    kb_voltar = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ 𝕍𝕠𝕝𝕥𝕒𝕣", callback_data='continue_after_action')]])
    
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
        await _send_battle_media(context, chat_id, "🏃 <b>FUGA!</b>\n\nVocê fugiu.", "media_fuga_sucesso", kb_voltar)
        return

    elif action == 'combat_attack':
        player_data = await player_manager.get_player_data(user_id)
        if not player_data: return
            
        battle_cache['turn'] = 'player'
        skill_id = battle_cache.pop('skill_to_use', None) 
        action_type = battle_cache.pop('action_type', 'attack') 
        skill_info = _get_player_skill_data_by_rarity(player_data, skill_id) if skill_id else None
        skip_monster_turn = False
        
        if skill_info:
            mana_cost = skill_info.get("mana_cost", 0)
            log.append(f"✨ Você usa <b>{skill_info['display_name']}</b>! (-{mana_cost} MP)")
            
            if action_type == 'support':
                skill_effects = skill_info.get("effects", {})
                heal_applied = False
                if "party_heal" in skill_effects:
                    heal_def = skill_effects["party_heal"]
                    heal_amount = 0
                    if "amount_percent_max_hp" in heal_def:
                        heal_amount = int(player_stats.get('max_hp', 1) * heal_def["amount_percent_max_hp"])
                    elif heal_def.get("heal_type") == "magic_attack":
                        m_atk = player_stats.get('magic_attack', player_stats.get('attack', 0))
                        heal_amount = int(m_atk * heal_def.get("heal_scale", 1.0))
                    
                    if heal_amount > 0:
                        current_hp = battle_cache.get('player_hp', 0)
                        max_hp = player_stats.get('max_hp', 1)
                        new_hp = min(max_hp, current_hp + heal_amount)
                        healed_for = new_hp - current_hp
                        if healed_for > 0:
                            battle_cache['player_hp'] = new_hp
                            log.append(f"❤️ Cura: +{healed_for} HP!")
                            heal_applied = True
                
                if not heal_applied: log.append("➕ <i>Buffs aplicados.</i>")
                skip_monster_turn = True
            else: 
                resultado = await combat_engine.processar_acao_combate(
                    attacker_pdata=player_data, attacker_stats=player_stats,
                    target_stats=monster_stats, skill_id=skill_id,
                    attacker_current_hp=battle_cache.get('player_hp', 9999)
                )
                player_damage = resultado["total_damage"]
                log.extend(resultado["log_messages"])
                monster_stats['hp'] = int(monster_stats.get('hp', 0)) - player_damage
                monster_defeated_in_turn = monster_stats['hp'] <= 0
        else:
            log.append("⚔️ Ataque básico.")
            resultado = await combat_engine.processar_acao_combate(
                attacker_pdata=player_data, attacker_stats=player_stats, 
                target_stats=monster_stats, skill_id=None,
                attacker_current_hp=battle_cache.get('player_hp', 9999)
            )
            player_damage = resultado["total_damage"]
            log.extend(resultado["log_messages"])
            monster_stats['hp'] = int(monster_stats.get('hp', 0)) - player_damage
            monster_defeated_in_turn = monster_stats['hp'] <= 0
            
        battle_cache['battle_log'] = log
        caption_turno_jogador = await format_combat_message_from_cache(battle_cache)
        
        if skip_monster_turn:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), InlineKeyboardButton("✨ Skills", callback_data='combat_skill_menu')],
                [InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu'), InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')]
            ])
            await _edit_media_or_caption(context, battle_cache, caption_turno_jogador, battle_cache['player_media_id'], battle_cache['player_media_type'], reply_markup=kb)
            return 
            
        if monster_defeated_in_turn:
            log.append(f"🏆 <b>{monster_stats['name']} foi derrotado!</b>")
            
            # A. Calcula Recompensas e DROPS
            xp, gold, looted_items = rewards.calculate_victory_rewards(player_data, battle_cache)
            
            # B. Atualiza Player (XP/Ouro)
            player_data["xp"] = player_data.get("xp", 0) + xp
            player_data["gold"] = player_data.get("gold", 0) + gold
            
            # C. Atualiza Inventário (Drops)
            for item_id, qty in looted_items:
                player_manager.add_item_to_inventory(player_data, item_id, qty)

            # D. Formata Texto Base
            summary = f"🏆 <b>VITÓRIA!</b>\n\nVocê derrotou {monster_stats['name']}!\n"
            summary += f"✨ XP: +{xp}\n💰 Ouro: +{gold}\n"
            if looted_items:
                summary += "\n<b>📦 Itens Encontrados:</b>\n"
                for item_id, qty in looted_items:
                    iname = game_data.ITEMS_DATA.get(item_id, {}).get("display_name", item_id)
                    summary += f"• {qty}x {iname}\n"

            # --- E. INTEGRAÇÃO DE MISSÕES (O PULO DO GATO) ---
            mission_logs = []
            
            # 1. Conta a CAÇA (Matar o monstro)
            monster_id = monster_stats.get("id")
            if monster_id:
                try:
                    hunt_logs = await mission_manager.update_mission_progress(user_id, "hunt", monster_id, 1)
                    mission_logs.extend(hunt_logs)
                except Exception: pass

            # 2. Conta a COLETA (Pelos itens dropados)
            # Isso permite que o Ferreiro complete missões de coleta lutando!
            for item_id, qty in looted_items:
                try:
                    # "collect" é o tipo da missão de coleta
                    collect_logs = await mission_manager.update_mission_progress(user_id, "collect", item_id, qty)
                    mission_logs.extend(collect_logs)
                except Exception: pass
            
            if mission_logs:
                summary += "\n" + "\n".join(mission_logs)
            # -------------------------------------------------------

            # F. Check Level Up e Restaura Status
            _, _, lvl_msg = player_manager.check_and_apply_level_up(player_data)
            if lvl_msg: summary += lvl_msg
            
            total_stats = await player_manager.get_player_total_stats(player_data)
            player_data['current_hp'] = total_stats.get('max_hp', 100)
            player_data['current_mp'] = total_stats.get('max_mana', 50)
            player_data['player_state'] = {'action': 'idle'}
            
            await player_manager.save_player_data(user_id, player_data)
            context.user_data.pop('battle_cache', None)
            
            # G. Envia Tela Final
            await _edit_media_or_caption(
                context, battle_cache, summary, 
                battle_cache['player_media_id'], battle_cache['player_media_type'], 
                reply_markup=kb_voltar
            )
            return 
            
        else:
            battle_cache['turn'] = 'monster'
            active_cooldowns = battle_cache.setdefault("skill_cooldowns", {})
            skills_off = [sid for sid, t in active_cooldowns.items() if t - 1 <= 0]
            for sid in skills_off: del active_cooldowns[sid]
            for sid, t in active_cooldowns.items(): active_cooldowns[sid] = t - 1
            
            initiative = player_stats.get('initiative', 0)
            dodge_chance = min((initiative * 0.4) / 100.0, 0.75)

            if random.random() < dodge_chance: 
                log.append("💨 Você esquivou!")
            else:
                dmg, crit, mega = criticals.roll_damage(monster_stats, player_stats, {})
                log.append(f"⬅️ Inimigo causa {dmg} de dano.")
                if mega: log.append("‼️ MEGA CRÍTICO!")
                elif crit: log.append("❗️ CRÍTICO!")
                
                battle_cache['player_hp'] = int(battle_cache.get('player_hp', 0)) - dmg
                if battle_cache['player_hp'] <= 0:
                    log.append("☠️ <b>Derrota!</b>")
                    battle_cache['battle_log'] = log
                    player_data = await player_manager.get_player_data(user_id)
                    defeat_summary, _ = rewards.process_defeat_from_cache(player_data, battle_cache)
                    player_data['current_hp'] = player_stats.get('max_hp', 50)
                    player_data['current_mp'] = battle_cache.get('player_mp', 10)
                    player_data['player_state'] = {'action': 'idle'}
                    await player_manager.save_player_data(user_id, player_data)
                    context.user_data.pop('battle_cache', None)
                    
                    await _edit_media_or_caption(context, battle_cache, defeat_summary, 
                        (file_id_manager.get_file_data("media_derrota_cacada") or {}).get('id'), 
                        "photo", reply_markup=kb_voltar)
                    return 

    battle_cache['battle_log'] = log
    caption_turno_monstro = await format_combat_message_from_cache(battle_cache)
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), InlineKeyboardButton("✨ Skills", callback_data='combat_skill_menu')],
        [InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu'), InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')]
    ])
    
    await _edit_media_or_caption(context, battle_cache, caption_turno_monstro, battle_cache['monster_media_id'], battle_cache['monster_media_type'], reply_markup=kb)
    
    if is_auto_mode:
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
                # (HP na derrota do modo legado JÁ ESTAVA CORRETO)
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
        action_type = combat_details.pop('action_type', 'attack') 
        
        # --- CORREÇÃO 4: Lê a skill (com raridade) usando a função auxiliar ---
        skill_info = _get_player_skill_data_by_rarity(player_data, skill_id) if skill_id else None
        
        skip_monster_turn = False
        
        # --- LÓGICA DE SKILL ---
        
        if skill_info:
            # (O custo de mana agora é lido corretamente da raridade)
            mana_cost = skill_info.get("mana_cost", 0)
            
            log.append(f"✨ Você usa <b>{skill_info['display_name']}</b>! (-{mana_cost} MP)")
            
            # --- CORREÇÃO 5: Lógica de Suporte (Cura) ---
            if action_type == 'support':
                skill_effects = skill_info.get("effects", {})
                heal_applied = False
                
                if "party_heal" in skill_effects:
                    heal_def = skill_effects["party_heal"]
                    heal_amount = 0
                    
                    if "amount_percent_max_hp" in heal_def: 
                        heal_amount = int(player_total_stats.get('max_hp', 1) * heal_def["amount_percent_max_hp"])
                    elif heal_def.get("heal_type") == "magic_attack":
                        m_atk = player_total_stats.get('magic_attack', player_total_stats.get('attack', 0))
                        heal_amount = int(m_atk * heal_def.get("heal_scale", 1.0))
                    
                    if heal_amount > 0:
                        current_hp = player_data.get('current_hp', 0)
                        max_hp = player_total_stats.get('max_hp', 1)
                        new_hp = min(max_hp, current_hp + heal_amount)
                        healed_for = new_hp - current_hp
                        
                        if healed_for > 0:
                            player_data['current_hp'] = new_hp
                            log.append(f"❤️ Você e seus aliados são curados em {healed_for} HP!")
                            heal_applied = True
                
                if not heal_applied:
                    log.append("➕ <i>Efeitos de suporte (Buffs) aplicados.</i>")
                
                skip_monster_turn = True
                combat_details["turn"] = 'player'
                
            # LÓGICA DE SKILL DE ATAQUE (Dano)
            else: 
                resultado_combate = await combat_engine.processar_acao_combate(
                    attacker_pdata=player_data, 
                    attacker_stats=player_total_stats, 
                    target_stats=monster_stats,
                    skill_id=skill_id,
                    attacker_current_hp=player_data.get('current_hp', 9999)
                )

                player_damage = resultado_combate["total_damage"]
                log.extend(resultado_combate["log_messages"])
                
                combat_details['monster_hp'] = int(combat_details.get('monster_hp', 0)) - player_damage
                combat_details["used_weapon"] = True
                monster_defeated_in_turn = combat_details['monster_hp'] <= 0

        else:
            # Caso use ataque básico (sem skill)
            log.append("⚔️ Você realiza um ataque básico.")
            
            resultado_combate = await combat_engine.processar_acao_combate(
                attacker_pdata=player_data,
                attacker_stats=player_total_stats, 
                target_stats=monster_stats, 
                skill_id=None,
                attacker_current_hp=player_data.get('current_hp', 9999)
            )
            
            player_damage = resultado_combate["total_damage"]
            log.extend(resultado_combate["log_messages"])
            combat_details['monster_hp'] = int(combat_details.get('monster_hp', 0)) - player_damage
            combat_details["used_weapon"] = True
            monster_defeated_in_turn = combat_details['monster_hp'] <= 0


        # --- 4. Resultado (Vitória, Suporte ou Turno do Monstro) ---
        if monster_defeated_in_turn: 
            durability.apply_end_of_battle_wear(player_data, combat_details, log)
            log.append(f"🏆 <b>{monster_stats['name']} foi derrotado!</b>")
            
            if combat_details.get('evolution_trial'):
                target_class = combat_details.get('evolution_trial').get('target_class')
                success, message = await class_evolution_service.finalize_evolution(user_id, target_class)
                if query: await query.delete_message()
                await context.bot.send_message(chat_id=chat_id, text=f"🎉 {message} 🎉", parse_mode="HTML")
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
            # (Saída para Skill de Suporte - Legado)
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
                    # (HP na derrota do modo legado JÁ ESTAVA CORRETO)
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