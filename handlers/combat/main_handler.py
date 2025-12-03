# handlers/combat/main_handler.py
# (VERSÃO BLINDADA: ANTI-TRAVAMENTO PARA CONTAS ANTIGAS)

import logging
import random
import asyncio
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaVideo, InputMediaPhoto, CallbackQuery
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest
from datetime import datetime, timedelta, timezone
# Importações dos módulos
from modules import player_manager, game_data, class_evolution_service, clan_manager
from modules import mission_manager 
from handlers.menu.region import send_region_menu
from handlers.utils import format_combat_message_from_cache, format_combat_message
from modules.combat import durability, criticals, rewards, combat_engine
from modules.dungeons import runtime as dungeons_runtime
from handlers.class_evolution_handler import open_evolution_menu
from handlers.profile_handler import _get_class_media
from modules.dungeons.runtime import _send_battle_media
from modules import file_ids as file_id_manager
from modules.game_data.skills import SKILL_DATA

logger = logging.getLogger(__name__)

# ================================================
# HELPERS VISUAIS ROBUSTOS
# ================================================
async def _safe_answer(query):
    try: await query.answer()
    except BadRequest: pass

async def _edit_caption_only(query, caption_text: str, reply_markup=None):
    """Tenta editar a legenda. Se falhar, envia nova mensagem."""
    try: 
        await query.edit_message_caption(caption=caption_text, reply_markup=reply_markup, parse_mode='HTML')
    except BadRequest as e:
        if "Message is not modified" in str(e): return
        # Se falhar, tenta mandar nova
        try: await query.message.reply_text(text=caption_text, reply_markup=reply_markup, parse_mode='HTML')
        except: pass
    except Exception:
        pass

async def _edit_media_or_caption(context: ContextTypes.DEFAULT_TYPE, battle_cache: dict, new_caption: str, new_media_id: str, new_media_type: str, reply_markup=None):
    """
    Tenta editar a mídia. Se der erro, apaga e manda nova.
    Se der erro crítico, manda texto puro para não travar.
    """
    chat_id = battle_cache.get('chat_id')
    message_id = battle_cache.get('message_id')
    
    if not chat_id: return # Cache corrompido

    try:
        # Se não tiver mídia nova, tenta editar só o texto
        if not new_media_id:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=new_caption, reply_markup=reply_markup, parse_mode="HTML")
            return

        # Tenta editar a mídia
        InputMediaClass = InputMediaVideo if new_media_type == "video" else InputMediaPhoto
        await context.bot.edit_message_media(
            chat_id=chat_id, 
            message_id=message_id, 
            media=InputMediaClass(media=new_media_id, caption=new_caption, parse_mode="HTML"), 
            reply_markup=reply_markup
        )
    except Exception as e:
        if "Message is not modified" in str(e): return

        # Se falhar a edição, tenta recriar a mensagem
        try:
            try: await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            except: pass

            sent_message = None
            if new_media_type == "video":
                sent_message = await context.bot.send_video(chat_id=chat_id, video=new_media_id, caption=new_caption, reply_markup=reply_markup, parse_mode="HTML")
            else:
                sent_message = await context.bot.send_photo(chat_id=chat_id, photo=new_media_id, caption=new_caption, reply_markup=reply_markup, parse_mode="HTML")
            
            if sent_message:
                battle_cache['message_id'] = sent_message.message_id
                
        except Exception as e2:
            logger.error(f"[COMBAT] Falha crítica visual: {e2}. Tentando fallback texto.")
            try:
                msg = await context.bot.send_message(chat_id=chat_id, text=new_caption, reply_markup=reply_markup, parse_mode="HTML")
                if msg: battle_cache['message_id'] = msg.message_id
            except: pass

# ================================================
# FUNÇÃO AUXILIAR DE SKILL
# ================================================
def _get_player_skill_data_by_rarity(pdata: dict, skill_id: str) -> Optional[dict]:
    base_skill = SKILL_DATA.get(skill_id)
    if not base_skill: return None
    if "rarity_effects" not in base_skill: return base_skill

    player_skills = pdata.get("skills", {})
    if not isinstance(player_skills, dict): rarity = "comum"
    else:
        player_skill_instance = player_skills.get(skill_id)
        rarity = player_skill_instance.get("rarity", "comum") if player_skill_instance else "comum"

    merged_data = base_skill.copy()
    rarity_data = base_skill["rarity_effects"].get(rarity, base_skill["rarity_effects"].get("comum", {}))
    merged_data.update(rarity_data)
    return merged_data

# ================================================
# MOTOR DE COMBATE PRINCIPAL
# ================================================

async def combat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str = None) -> None:
    query = update.callback_query
    if action is None and query: action = query.data
    elif action is None and not query: return

    user_id = query.from_user.id if query else update.effective_user.id
    chat_id = query.message.chat_id if query else update.effective_chat.id

    # --- AÇÃO: VOLTAR PARA O MAPA ---
    if action == 'combat_return_to_map':
        if query: await _safe_answer(query)
        context.user_data.pop('battle_cache', None)
        
        # Destrava o jogador forçadamente
        player_data = await player_manager.get_player_data(user_id)
        if player_data:
            player_data['player_state'] = {'action': 'idle'}
            await player_manager.save_player_data(user_id, player_data)
            await send_region_menu(context, user_id, chat_id)
            try: await query.delete_message()
            except: pass
        return

    # --- MENUS SECUNDÁRIOS ---
    if action == 'combat_attack_menu':
        if not query: return
        await _safe_answer(query)
        kb = [
            [InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), InlineKeyboardButton("✨ Skills", callback_data='combat_skill_menu')],
            [InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu'), InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')]
        ]
        try: await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
        except: pass
        return

    if query: await _safe_answer(query)
    
    # --- CARREGA CACHE ---
    battle_cache = context.user_data.get('battle_cache')
    
    # Se não tiver cache ou for inválido, tenta limpar o estado e voltar
    if not battle_cache or battle_cache.get('player_id') != user_id:
        player_data = await player_manager.get_player_data(user_id)
        if player_data:
            # Se a conta estiver presa em combate mas sem cache, libera
            if player_data.get('player_state', {}).get('action') == 'in_combat':
                player_data['player_state'] = {'action': 'idle'}
                await player_manager.save_player_data(user_id, player_data)
                
        if query:
            try: await query.edit_message_caption(caption="⚠️ Sessão expirada ou dados antigos. Retornando...", reply_markup=None)
            except: pass
            await asyncio.sleep(1)
            await send_region_menu(context, user_id, chat_id)
        return

    # Dados da batalha
    log = battle_cache.get('battle_log', [])
    player_stats = battle_cache.get('player_stats', {}) 
    monster_stats = battle_cache.get('monster_stats', {})
    is_auto_mode = battle_cache.get('is_auto_mode', False)
    
    kb_voltar = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar para o Mapa", callback_data='combat_return_to_map')]])
    
    # --- FUGIR ---
    if action == 'combat_flee':
        context.user_data.pop('battle_cache', None)
        player_data = await player_manager.get_player_data(user_id)
        player_data['player_state'] = {'action': 'idle'}
        # Penalidade leve ao fugir
        max_hp = player_stats.get('max_hp', 100)
        player_data['current_hp'] = max(1, int(max_hp * 0.1))
        await player_manager.save_player_data(user_id, player_data)
        
        try: await query.delete_message()
        except: pass
        
        media_fuga = (file_id_manager.get_file_data("media_fuga_sucesso") or {}).get("id")
        await _send_battle_media(context, chat_id, "🏃 <b>FUGA!</b>\n\nVocê escapou com vida, mas exausto.", media_fuga, kb_voltar)
        return

    # --- ATACAR ---
    elif action == 'combat_attack':
        player_data = await player_manager.get_player_data(user_id)
        if not player_data: return
            
        battle_cache['turn'] = 'player'
        skill_id = battle_cache.pop('skill_to_use', None) 
        action_type = battle_cache.pop('action_type', 'attack') 
        skill_info = _get_player_skill_data_by_rarity(player_data, skill_id) if skill_id else None
        skip_monster_turn = False
        
        # Variável para armazenar o dano calculado neste turno
        player_damage = 0 

        # PROCESSA AÇÃO DO JOGADOR
        if skill_info:
            mana_cost = skill_info.get("mana_cost", 0)
            log.append(f"✨ Você usa {skill_info['display_name']}! (-{mana_cost} 💧MP)")
            
            if action_type == 'support':
                # ... (Lógica de suporte/cura permanece igual) ...
                skill_effects = skill_info.get("effects", {})
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
                skip_monster_turn = True
            else: 
                # Ataque com Skill
                resultado = await combat_engine.processar_acao_combate(
                    attacker_pdata=player_data, attacker_stats=player_stats,
                    target_stats=monster_stats, skill_id=skill_id,
                    attacker_current_hp=battle_cache.get('player_hp', 9999)
                )
                player_damage = resultado["total_damage"]
                log.extend(resultado["log_messages"])
                
        else:
            # Ataque Básico
            log.append("⚔️ Ataque básico.")
            resultado = await combat_engine.processar_acao_combate(
                attacker_pdata=player_data, attacker_stats=player_stats, 
                target_stats=monster_stats, skill_id=None,
                attacker_current_hp=battle_cache.get('player_hp', 9999)
            )
            player_damage = resultado["total_damage"]
            log.extend(resultado["log_messages"])

        # === CORREÇÃO DO BUG: INICIALIZAÇÃO DE HP DO MONSTRO ===
        # Só aplica o dano se não for turno de suporte (skip_monster_turn)
        if not skip_monster_turn:
            # Se não tiver 'hp' atual, inicializa com o 'max_hp'
            if 'hp' not in monster_stats:
                monster_stats['hp'] = monster_stats.get('max_hp', 100) # Fallback 100 se não tiver max_hp
            
            # Aplica o dano
            monster_stats['hp'] = int(monster_stats['hp']) - player_damage
            
        monster_defeated_in_turn = monster_stats.get('hp', 0) <= 0
        battle_cache['battle_log'] = log[-12:] # Mantém log curto
        
        caption_turno_jogador = await format_combat_message_from_cache(battle_cache)
        
        # SE FOR SKILL DE SUPORTE (Pula turno monstro)
        if skip_monster_turn:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), InlineKeyboardButton("✨ Skills", callback_data='combat_skill_menu')],
                [InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu'), InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')]
            ])
            await _edit_media_or_caption(context, battle_cache, caption_turno_jogador, battle_cache['player_media_id'], battle_cache['player_media_type'], reply_markup=kb)
            return 
            
        # ==========================================================
        # 🏆 VITÓRIA (COM PROTEÇÃO ANTI-CRASH)
        # ==========================================================
        if monster_defeated_in_turn:
            try:
                log.append(f"🏆 <b>{monster_stats.get('name', 'Inimigo')} derrotado!</b>")
                
                # Prepara contexto para rewards (Garante que existam chaves críticas)
                reward_context = battle_cache.copy()
                reward_context.update(monster_stats)
                if 'monster_xp_reward' not in reward_context:
                    reward_context['monster_xp_reward'] = monster_stats.get('xp_reward', 0)
                if 'monster_gold_drop' not in reward_context:
                    reward_context['monster_gold_drop'] = monster_stats.get('gold_drop', 0)
                
                # 1. Calcula Recompensas
                xp, gold, looted_items_raw = rewards.calculate_victory_rewards(player_data, reward_context)
                
                # 2. Processa Loot (Seguro)
                processed_loot = []
                if looted_items_raw:
                    for drop in looted_items_raw:
                        if isinstance(drop, str): processed_loot.append((drop, 1, None))
                        elif isinstance(drop, (list, tuple)):
                            processed_loot.append((drop[0], drop[1] if len(drop)>1 else 1, None))
                
                # 3. Aplica no Player
                player_data["xp"] = player_data.get("xp", 0) + xp
                player_data["gold"] = player_data.get("gold", 0) + gold
                
                for item_id, qty, _ in processed_loot:
                    player_manager.add_item_to_inventory(player_data, item_id, qty)

                # 4. Formata Texto
                summary = f"🏆 <b>VITÓRIA!</b>\n\nVocê derrotou {monster_stats.get('name', 'Inimigo')}!\n"
                summary += f"✨ XP: +{xp}\n💰 Ouro: +{gold}\n"
                
                if processed_loot:
                    summary += "\n<b>📦 Loot:</b>\n"
                    for item_id, qty, _ in processed_loot:
                        item_def = game_data.ITEMS_DATA.get(item_id, {})
                        iname = item_def.get("display_name", item_id)
                        summary += f"• {qty}x {iname}\n"

                # 5. Atualiza Missões (BLINDADO)
                try:
                    mission_logs = []
                    monster_id = monster_stats.get("id")
                    if monster_id:
                        h_logs = await mission_manager.update_mission_progress(user_id, "hunt", monster_id, 1)
                        if h_logs: mission_logs.extend(h_logs)
                    
                    for item_id, qty, _ in processed_loot:
                        c_logs = await mission_manager.update_mission_progress(user_id, "collect", item_id, qty)
                        if c_logs: mission_logs.extend(c_logs)
                        
                    if mission_logs: summary += "\n" + "\n".join(mission_logs)
                except Exception as e_miss:
                    logger.error(f"[COMBAT] Erro ao atualizar missões (ignorado): {e_miss}")

                # 6. Level Up
                try:
                    _, _, lvl_msg = player_manager.check_and_apply_level_up(player_data)
                    if lvl_msg: summary += lvl_msg
                except: pass
                
                # 7. Restaura HP/MP e Salva (CRUCIAL: DESTRAVAR JOGADOR)
                total_stats = await player_manager.get_player_total_stats(player_data)
                player_data['current_hp'] = total_stats.get('max_hp', 100)
                player_data['current_mp'] = total_stats.get('max_mana', 50)
                player_data['player_state'] = {'action': 'idle'} # <--- LIBERA AQUI
                
                await player_manager.save_player_data(user_id, player_data)
                context.user_data.pop('battle_cache', None)
                
                # 8. Tenta enviar a mensagem final
                await _edit_media_or_caption(
                    context, battle_cache, summary, 
                    battle_cache['player_media_id'], battle_cache['player_media_type'], 
                    reply_markup=kb_voltar
                )
                return 

            except Exception as e_crit:
                # SAFETY NET FINAL: Se tudo der errado, libera o jogador
                logger.error(f"[COMBAT] ERRO CRÍTICO NA VITÓRIA: {e_crit}", exc_info=True)
                
                player_data['player_state'] = {'action': 'idle'}
                await player_manager.save_player_data(user_id, player_data)
                context.user_data.pop('battle_cache', None)
                
                await context.bot.send_message(chat_id, "⚠️ <b>Erro ao processar vitória.</b>\nSeus dados foram salvos e você foi liberado do combate.", parse_mode="HTML", reply_markup=kb_voltar)
                return

        # ==========================================================
        # TURNO DO MONSTRO
        # ==========================================================
        else:
            battle_cache['turn'] = 'monster'
            # Gerencia cooldowns
            active_cooldowns = battle_cache.setdefault("skill_cooldowns", {})
            for sid, t in list(active_cooldowns.items()):
                if t - 1 <= 0: del active_cooldowns[sid]
                else: active_cooldowns[sid] = t - 1
            
            # Esquiva
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
                
                # --- DERROTA ---
                if battle_cache['player_hp'] <= 0:
                    log.append("☠️ <b>Derrota!</b>")
                    battle_cache['battle_log'] = log
                    
                    # Processa Derrota
                    player_data['current_hp'] = player_stats.get('max_hp', 50)
                    player_data['current_mp'] = battle_cache.get('player_mp', 10)
                    
                    # Penalidade XP (simples)
                    xp_loss = int(monster_stats.get('xp_reward', 0) * 0.5)
                    player_data['xp'] = max(0, player_data.get('xp', 0) - xp_loss)
                    
                    player_data['player_state'] = {'action': 'idle'}
                    await player_manager.save_player_data(user_id, player_data)
                    context.user_data.pop('battle_cache', None)
                    
                    summ_loss = f"☠️ <b>Você foi derrotado!</b>\n\n{monster_stats.get('name')} foi mais forte.\n❌ Penalidade: -{xp_loss} XP"
                    
                    media_derrota = (file_id_manager.get_file_data("media_derrota_cacada") or {}).get('id')
                    await _edit_media_or_caption(context, battle_cache, summ_loss, media_derrota, "photo", reply_markup=kb_voltar)
                    return 

    # --- ATUALIZA TELA (TURNO SEGUINTE) ---
    battle_cache['battle_log'] = log[-12:]
    caption_turno_monstro = await format_combat_message_from_cache(battle_cache)
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), InlineKeyboardButton("✨ Skills", callback_data='combat_skill_menu')],
        [InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu'), InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')]
    ])
    
    await _edit_media_or_caption(context, battle_cache, caption_turno_monstro, battle_cache['monster_media_id'], battle_cache['monster_media_type'], reply_markup=kb)
    
    # Auto-Battle Loop
    if is_auto_mode:
        await asyncio.sleep(2) 
        fake_user = type("User", (), {"id": user_id})()
        fake_query = CallbackQuery(id=f"auto_{user_id}", from_user=fake_user, chat_instance="auto", data="combat_attack")
        fake_update = Update(update_id=0, callback_query=fake_query)
        # Chama recursivamente (sem bloquear muito a stack)
        asyncio.create_task(combat_callback(fake_update, context, action='combat_attack'))

async def _legacy_combat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, player_data: dict):
    """
    (VERSÃO CORRIGIDA COM SUPORTE A DADOS IMPERFEITOS)
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
    
    # --- CORREÇÃO DE DADOS DE MONSTRO (BUSCA ROBUSTA) ---
    m_name = combat_details.get('monster_name', combat_details.get('name', 'Inimigo'))
    m_xp = combat_details.get('monster_xp_reward', combat_details.get('xp_reward', combat_details.get('xp', 0)))
    m_gold = combat_details.get('monster_gold_drop', combat_details.get('gold_drop', combat_details.get('gold', 0)))
    
    monster_stats = {
        'name': m_name,
        'hp': combat_details.get('monster_hp', 1),
        'max_hp': combat_details.get('monster_max_hp', 1),
        'attack': combat_details.get('monster_attack', 1), 
        'defense': combat_details.get('monster_defense', 0),
        'luck': combat_details.get('monster_luck', 5), 
        'initiative': combat_details.get('monster_initiative', 0),
        'gold_drop': m_gold,
        'xp_reward': m_xp,
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
        else: 
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
    # --- (INÍCIO) LÓGICA DE ATAQUE (Legada) ---
    # ======================================================
    elif action == 'combat_attack':
        
        skill_id = combat_details.pop('skill_to_use', None) 
        action_type = combat_details.pop('action_type', 'attack') 
        
        skill_info = _get_player_skill_data_by_rarity(player_data, skill_id) if skill_id else None
        
        skip_monster_turn = False
        
        # --- LÓGICA DE SKILL ---
        if skill_info:
            mana_cost = skill_info.get("mana_cost", 0)
            log.append(f"✨ Você usa <b>{skill_info['display_name']}</b>! (-{mana_cost} MP)")
            
            # --- Lógica de Suporte (Cura) ---
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
                reward_context = combat_details.copy()
                reward_context.update(monster_stats) 
                xp_reward, gold_reward, looted_items_list = rewards.calculate_victory_rewards(player_data, reward_context)
                
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
            
            # --- CORREÇÃO FINAL DE RECOMPENSAS NO LEGACY ---
            combat_details.update(monster_stats)
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
            keyboard = [[InlineKeyboardButton("⬅️ 𝕍𝕠𝕝𝕥𝕒𝕣", callback_data='combat_return_to_map')]]
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
            # --- TURNO DO MONSTRO (Legado) ---
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

    # --- (FIM) LÓGICA DE ATAQUE (Legada) ---
    
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
combat_handler = CallbackQueryHandler(combat_callback, pattern=r'^(combat_attack|combat_flee|combat_attack_menu|combat_return_to_map)$')# handlers/guild_menu_handler.py
# (VERSÃO FINAL E ROBUSTA: CORREÇÃO DO ERRO DE LEGENDA)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules import player_manager, guild_system, clan_manager, file_ids

def _bar(current, total, blocks=8):
    if total <= 0: return "🟩" * blocks
    ratio = min(1.0, max(0.0, current / total))
    filled = int(ratio * blocks)
    return "🟩" * filled + "⬜" * (blocks - filled)

# Helper para editar mensagens de forma segura (Texto ou Legenda)
async def _safe_edit(query, text, markup):
    try:
        # Tenta editar legenda (se for foto/video)
        await query.edit_message_caption(caption=text, reply_markup=markup, parse_mode="HTML")
    except Exception:
        try:
            # Se falhar, tenta editar o texto (se for mensagem de texto puro)
            await query.edit_message_text(text=text, reply_markup=markup, parse_mode="HTML")
        except Exception:
            # Se tudo falhar (ex: mensagem antiga demais), manda nova
            await query.message.reply_text(text, reply_markup=markup, parse_mode="HTML")

async def adventurer_guild_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return

    gdata = pdata.get("adventurer_guild", {})
    missions = guild_system.generate_daily_missions(pdata)
    await player_manager.save_player_data(user_id, pdata)

    rank_letra = gdata.get("rank", "F")
    points = gdata.get("points", 0)
    rank_info = guild_system.get_rank_info(rank_letra)
    next_pts = rank_info.get("req_points", 9999)
    prog_bar = _bar(points, next_pts) if next_pts > 0 else "🌟🌟🌟🌟🌟🌟🌟🌟"
    prog_text = f"{points}/{next_pts}" if next_pts > 0 else "MÁXIMO"

    text = (
        f"🏰 <b>GUILDA DE AVENTUREIROS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎫 <b>CARTEIRA DE MEMBRO</b>\n"
        f"👤 <b>Nome:</b> {pdata.get('character_name')}\n"
        f"🎖️ <b>Rank:</b> {rank_info.get('emoji', '🔰')} <b>{rank_letra}</b> - {rank_info.get('title', 'Aventureiro')}\n"
        f"💠 <b>Prestígio:</b> <code>[{prog_bar}]</code> ({prog_text})\n\n"
        f"📋 <b>QUADRO DE AVISOS DIÁRIO:</b>\n"
    )

    keyboard = []
    
    for idx, m in enumerate(missions):
        status_icon = "✅" if m.get('status') in ['completed', 'claimed'] else "⬜"
        if m.get('status') == 'completed': status_icon = "🎁"
        
        name = m.get('title') or m.get('name') or "Missão"
        rewards = m.get('rewards', {})
        pts = rewards.get('prestige_points', m.get('reward_points', 0))
        prog = m.get('progress', 0)
        target = m.get('target_count', m.get('qty', 1))
        
        btn_txt = f"{status_icon} {name} ({prog}/{target}) [+ {pts} pts]"
        keyboard.append([InlineKeyboardButton(btn_txt, callback_data=f"gld_mission_view_{idx}")])

    if pdata.get("clan_id"):
        keyboard.append([InlineKeyboardButton("🛡️ Acessar Meu Clã", callback_data="clan_menu")])
    else:
        keyboard.append([InlineKeyboardButton("🛡️ Criar ou Buscar Clã", callback_data="guild_menu")])

    keyboard.append([InlineKeyboardButton("🔙 Voltar", callback_data="profile")])

    # Envio Inteligente (Mídia ou Texto)
    media_id = None
    try: media_id = file_ids.get_file_id("img_guild_npc")
    except: pass

    try:
        if media_id and query.message.photo:
             await query.edit_message_media(
                media=InputMediaPhoto(media_id, caption=text, parse_mode="HTML"),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        elif media_id:
            await query.delete_message()
            await context.bot.send_photo(
                chat_id=query.message.chat.id, photo=media_id, caption=text, 
                reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML"
            )
        else:
            # Fallback para texto puro (isso evita o erro futuro de caption)
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    except:
        # Se falhar edição (ex: mudou de foto pra texto), manda nova
        try: 
            await query.delete_message()
            await context.bot.send_message(chat_id=query.message.chat.id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        except: pass

async def view_mission_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe os detalhes de uma missão pessoal."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    try: idx = int(query.data.split("_")[-1])
    except: return

    pdata = await player_manager.get_player_data(user_id)
    missions = pdata.get("adventurer_guild", {}).get("active_missions", [])
    if idx >= len(missions): return
        
    m = missions[idx]
    title = m.get('title') or m.get('name') or "Missão"
    desc = m.get('description') or m.get('desc') or "Sem descrição."
    status = m.get('status', 'active')
    
    rewards = m.get('rewards', {})
    xp = rewards.get('xp', m.get('xp', 0))
    gold = rewards.get('gold', m.get('reward_gold', 0))
    pts = rewards.get('prestige_points', m.get('reward_points', 0))
    
    prog = m.get('progress', 0)
    target = m.get('target_count', m.get('qty', 1))
    
    text = (
        f"📜 <b>{title}</b>\n"
        f"<i>{desc}</i>\n\n"
        f"📊 <b>Progresso:</b> {prog}/{target}\n"
        f"💰 <b>Recompensas:</b> {gold} Ouro, {xp} XP, {pts} Prestígio\n\n"
    )
    
    kb = []
    if status == 'completed':
        text += "✅ <b>Concluída!</b> Resgate sua recompensa."
        kb.append([InlineKeyboardButton("🎁 RESGATAR", callback_data=f"gld_mission_claim_{idx}")])
    elif status == 'claimed':
        text += "📦 <b>Recompensa já coletada.</b>"
    
    kb.append([InlineKeyboardButton("🔙 Voltar", callback_data="adventurer_guild_main")])
    
    # [CORREÇÃO] Usa o helper seguro para editar
    await _safe_edit(query, text, InlineKeyboardMarkup(kb))

async def claim_mission_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    try: idx = int(query.data.split("_")[-1])
    except: return

    from modules import mission_manager
    result = await mission_manager.claim_personal_reward(user_id, idx)
    
    if not result:
        await query.answer("Erro ao resgatar.", show_alert=True)
        return
        
    await query.answer(f"Recebido: {result['gold']} Ouro, {result['xp']} XP!", show_alert=True)
    if result.get("rank_up"):
        await context.bot.send_message(chat_id=query.message.chat.id, text=f"🎉 <b>PARABÉNS!</b>\nSubiu para Rank {result['rank_up']['title']}!", parse_mode="HTML")
    await adventurer_guild_menu(update, context)

async def clan_mission_board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    pdata = await player_manager.get_player_data(user_id)
    
    if not pdata.get("clan_id"):
        await query.answer("Você precisa estar em um Clã!", show_alert=True)
        return

    try: clan_data = await clan_manager.get_clan(pdata["clan_id"])
    except: clan_data = {}

    if not clan_data:
        await query.answer("Clã não encontrado.", show_alert=True)
        return

    clan_lvl = clan_data.get('level', 1)
    clan_name = clan_data.get('name', 'Seu Clã')
    leader_id = int(clan_data.get('leader_id', 0))
    is_leader = (user_id == leader_id)
    active_m = clan_data.get('active_mission')
    
    text = (
        f"🛡️ <b>MISSÕES DE EXPANSÃO DO CLÃ</b>\n"
        f"Clã: <b>{clan_name}</b> | Nível: {clan_lvl}\n\n"
    )
    
    keyboard = []

    if active_m:
        title = active_m.get('title', 'Missão')
        prog = active_m.get('current_progress', 0)
        targ = active_m.get('target_count', 1)
        desc = active_m.get('description', '')
        
        # Formatação do nome do alvo
        target_raw = active_m.get('target_monster_id') or active_m.get('target_item_id') or "Alvo"
        target_pretty = str(target_raw).replace("_", " ").title()
        m_type = active_m.get('type', 'HUNT')
        action = "Derrotar" if m_type == "HUNT" else "Coletar"
        percent = (prog / targ) * 100 if targ > 0 else 0

        text += (
            f"⚔️ <b>MISSÃO ATIVA:</b>\n"
            f"📜 <b>{title}</b>\n"
            f"<i>\"{desc}\"</i>\n\n"
            f"🎯 <b>Objetivo:</b> {action} {targ}x <b>{target_pretty}</b>\n"
            f"📊 <b>Progresso:</b> {prog}/{targ} ({percent:.1f}%)\n"
            f"<code>[{_bar(prog, targ, 10)}]</code>\n"
        )
        if prog >= targ:
            text += "\n✅ <b>CONCLUÍDA! O líder deve finalizar.</b>"
    else:
        text += "💤 <i>Nenhuma missão ativa no momento.</i>\n\n"
        if is_leader:
            text += "👑 <b>Você é o Líder!</b> Inicie uma missão para seu clã."
            keyboard.append([InlineKeyboardButton("📜 Iniciar Nova Missão", callback_data="gld_mission_select_menu")])
        else:
            text += "<i>Peça ao seu Líder para iniciar uma missão.</i>"
    
    keyboard.append([InlineKeyboardButton("🔙 Voltar à Guilda", callback_data="adventurer_guild_main")])
    
    # [CORREÇÃO] Usa o helper seguro
    await _safe_edit(query, text, InlineKeyboardMarkup(keyboard))

# Exports
adventurer_guild_handler = CallbackQueryHandler(adventurer_guild_menu, pattern=r'^adventurer_guild_main$')
clan_board_handler = CallbackQueryHandler(clan_mission_board, pattern=r'^gld_clan_board$')
mission_view_handler = CallbackQueryHandler(view_mission_details, pattern=r'^gld_mission_view_')
mission_claim_handler = CallbackQueryHandler(claim_mission_reward, pattern=r'^gld_mission_claim_')