# handlers/combat/main_handler.py
# (VERSÃO CORRIGIDA: Restaura HP/MP em Vitória E Derrota)

import logging
import random
import asyncio
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaVideo, InputMediaPhoto
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

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
# HELPERS VISUAIS
# ================================================
async def _safe_answer(query):
    try: await query.answer()
    except BadRequest: pass

async def _edit_media_or_caption(context: ContextTypes.DEFAULT_TYPE, battle_cache: dict, new_caption: str, new_media_id: str, new_media_type: str, reply_markup=None):
    chat_id = battle_cache.get('chat_id')
    message_id = battle_cache.get('message_id')
    if not chat_id: return 

    try:
        if not new_media_id:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=new_caption, reply_markup=reply_markup, parse_mode="HTML")
            return

        InputMediaClass = InputMediaVideo if new_media_type == "video" else InputMediaPhoto
        await context.bot.edit_message_media(
            chat_id=chat_id, 
            message_id=message_id, 
            media=InputMediaClass(media=new_media_id, caption=new_caption, parse_mode="HTML"), 
            reply_markup=reply_markup
        )
    except Exception:
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
                
        except Exception:
            try:
                msg = await context.bot.send_message(chat_id=chat_id, text=new_caption, reply_markup=reply_markup, parse_mode="HTML")
                if msg: battle_cache['message_id'] = msg.message_id
            except: pass

def _get_player_skill_data_by_rarity(pdata: dict, skill_id: str) -> Optional[dict]:
    base_skill = SKILL_DATA.get(skill_id)
    if not base_skill: return None
    if "rarity_effects" not in base_skill: return base_skill
    player_skills = pdata.get("skills", {})
    if not isinstance(player_skills, dict): rarity = "comum"
    else:
        skill = player_skills.get(skill_id)
        rarity = skill.get("rarity", "comum") if skill else "comum"
    merged = base_skill.copy()
    merged.update(base_skill["rarity_effects"].get(rarity, {}))
    return merged

# ================================================
# MOTOR DE COMBATE
# ================================================

async def combat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str = None) -> None:
    query = update.callback_query
    if action is None and query: action = query.data
    elif action is None and not query: return

    user_id = query.from_user.id if query else update.effective_user.id
    chat_id = query.message.chat_id if query else update.effective_chat.id

    # --- Retorno ao Mapa ---
    if action == 'combat_return_to_map':
        if query: await _safe_answer(query)
        context.user_data.pop('battle_cache', None)
        player_data = await player_manager.get_player_data(user_id)
        if player_data:
            # Garante que o estado está limpo
            player_data['player_state'] = {'action': 'idle'}
            await player_manager.save_player_data(user_id, player_data)
            await send_region_menu(context, user_id, chat_id)
            try: await query.delete_message()
            except: pass
        return

    # --- Menu de Ataque ---
    if action == 'combat_attack_menu':
        if not query: return
        await _safe_answer(query)
        kb = [[InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), InlineKeyboardButton("✨ Skills", callback_data='combat_skill_menu')],
              [InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu'), InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')]]
        try: await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
        except: pass
        return

    if query: await _safe_answer(query)
    
    battle_cache = context.user_data.get('battle_cache')
    
    # =========================================================================
    # 🚑 AUTO-RECUPERAÇÃO (CORRIGIDA PARA CAÇADAS NORMAIS)
    # =========================================================================
    if not battle_cache or battle_cache.get('player_id') != user_id:
        player_data = await player_manager.get_player_data(user_id)
        
        # Se o jogador estiver em combate no DB, vamos restaurar a sessão!
        if player_data and player_data.get('player_state', {}).get('action') == 'in_combat':
            details = player_data['player_state'].get('details', {})
            
            # --- RECUPERAÇÃO DE DUNGEON ---
            if "dungeon_ctx" in details:
                from modules.dungeons import runtime as d_rt
                msg_id = query.message.message_id if query and query.message else None
                await d_rt._update_battle_cache(
                    context, user_id, player_data, details, 
                    message_id=msg_id, chat_id=chat_id
                )
                return await combat_callback(update, context, action)
            
            # --- RECUPERAÇÃO DE CAÇADA NORMAL ---
            else:
                # Reconstrói o cache manualmente para caçadas normais
                p_stats = await player_manager.get_player_total_stats(player_data)
                
                # Mapeia os dados do DB para o formato do cache
                monster_stats = {
                    'name': details.get('monster_name', details.get('name', 'Inimigo')),
                    'hp': details.get('monster_hp', 1),
                    'max_hp': details.get('monster_max_hp', 1),
                    'attack': details.get('monster_attack', 1),
                    'defense': details.get('monster_defense', 0),
                    'initiative': details.get('monster_initiative', 0),
                    'luck': details.get('monster_luck', 0),
                    'xp_reward': details.get('monster_xp_reward', 0),
                    'gold_drop': details.get('monster_gold_drop', 0),
                    'id': details.get('id'),
                    'loot_table': details.get('loot_table', [])
                }
                
                p_media = _get_class_media(player_data, purpose="combate")
                
                new_cache = {
                    'player_id': user_id,
                    'chat_id': chat_id,
                    'message_id': query.message.message_id if query and query.message else None,
                    'player_stats': p_stats,
                    'monster_stats': monster_stats,
                    'player_hp': player_data.get('current_hp'),
                    'player_mp': player_data.get('current_mp'),
                    'battle_log': details.get('battle_log', []),
                    'turn': 'player',
                    'player_media_id': p_media.get("id") if p_media else None,
                    'player_media_type': p_media.get("type", "photo") if p_media else "photo",
                    'monster_media_id': details.get('file_id_name') or details.get('image'),
                    'monster_media_type': 'photo',
                    'dungeon_ctx': None, # Garante que sabe que NÃO é dungeon
                    'region_key': details.get('region_key')
                }
                
                context.user_data['battle_cache'] = new_cache
                # Reinicia a função com o cache restaurado
                return await combat_callback(update, context, action)
        
        else:
            # Se não estiver em combate no DB, aí sim expira
            if query:
                try: await query.edit_message_caption(caption="⚠️ Sessão expirada. Retornando...", reply_markup=None)
                except: pass
                await asyncio.sleep(1)
                await send_region_menu(context, user_id, chat_id)
            return

    # =========================================================================
    
    log = battle_cache.get('battle_log', [])
    player_stats = battle_cache.get('player_stats', {}) 
    monster_stats = battle_cache.get('monster_stats', {})
    is_auto_mode = battle_cache.get('is_auto_mode', False)
    dungeon_ctx = battle_cache.get('dungeon_ctx')
    in_dungeon = bool(dungeon_ctx)

    kb_voltar = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar para o Mapa", callback_data='combat_return_to_map')]])
    
    # --- FUGIR ---
    if action == 'combat_flee':
        context.user_data.pop('battle_cache', None)
        player_data = await player_manager.get_player_data(user_id)
        player_data['player_state'] = {'action': 'idle'}
        
        # Fuga = 10% de HP restante (penalidade)
        player_data['current_hp'] = max(1, int(player_stats.get('max_hp', 100) * 0.1))
        
        await player_manager.save_player_data(user_id, player_data)
        try: await query.delete_message()
        except: pass
        
        if in_dungeon:
             await dungeons_runtime.fail_dungeon_run(update, context, user_id, chat_id, "Você fugiu")
             return

        media_fuga = (file_id_manager.get_file_data("media_fuga_sucesso") or {}).get("id")
        await _send_battle_media(context, chat_id, "🏃 <b>FUGA!</b>\n\nEscapou por pouco.", media_fuga, kb_voltar)
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
        player_damage = 0 

        if skill_info:
            mana_cost = skill_info.get("mana_cost", 0)
            log.append(f"✨ {skill_info['display_name']}! (-{mana_cost} MP)")
            
            if action_type == 'support':
                effects = skill_info.get("effects", {})
                if "party_heal" in effects:
                    heal_def = effects["party_heal"]
                    base_heal = 0
                    if "amount_percent_max_hp" in heal_def:
                        base_heal = int(player_stats.get('max_hp', 100) * heal_def["amount_percent_max_hp"])
                    elif heal_def.get("heal_type") == "magic_attack":
                         base_heal = int(player_stats.get('magic_attack', 10) * heal_def.get("heal_scale", 1.0))
                    
                    cur = battle_cache.get('player_hp', 0)
                    mx = player_stats.get('max_hp', 100)
                    new_h = min(mx, cur + base_heal)
                    if new_h > cur:
                        battle_cache['player_hp'] = new_h
                        log.append(f"❤️ Cura: +{new_h - cur} HP")
                skip_monster_turn = True
            else:
                res = await combat_engine.processar_acao_combate(player_data, player_stats, monster_stats, skill_id, battle_cache.get('player_hp'))
                player_damage = res["total_damage"]
                log.extend(res["log_messages"])
        else:
            log.append("⚔️ Ataque básico.")
            res = await combat_engine.processar_acao_combate(player_data, player_stats, monster_stats, None, battle_cache.get('player_hp'))
            player_damage = res["total_damage"]
            log.extend(res["log_messages"])

        if not skip_monster_turn:
            if 'hp' not in monster_stats: monster_stats['hp'] = monster_stats.get('max_hp', 100)
            monster_stats['hp'] = int(monster_stats['hp']) - player_damage
            
        monster_defeated = monster_stats.get('hp', 0) <= 0
        battle_cache['battle_log'] = log[-12:]
        
        caption_p = await format_combat_message_from_cache(battle_cache)
        
        if skip_monster_turn:
            kb = [[InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), InlineKeyboardButton("✨ Skills", callback_data='combat_skill_menu')],
                  [InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu'), InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')]]
            await _edit_media_or_caption(context, battle_cache, caption_p, battle_cache['player_media_id'], battle_cache['player_media_type'], InlineKeyboardMarkup(kb))
            return 
            
        if monster_defeated:
            try:
                log.append(f"🏆 <b>{monster_stats.get('name')} derrotado!</b>")
                
                # --- LÓGICA DE DUNGEON (Não altera HP) ---
                if in_dungeon:
                    combat_details_recon = {
                         "region_key": battle_cache.get("region_key"),
                         "difficulty": dungeon_ctx.get("difficulty"),
                         "dungeon_stage": dungeon_ctx.get("floor_idx", 0),
                         "dungeon_ctx": dungeon_ctx,
                         "loot_table": monster_stats.get("loot_table", []),
                         "file_id_name": battle_cache.get("monster_media_id") 
                    }
                    
                    r_ctx = battle_cache.copy()
                    r_ctx.update(monster_stats)
                    xp, gold, items = rewards.calculate_victory_rewards(player_data, r_ctx)
                    
                    fmt_items = []
                    for i in items:
                        if isinstance(i, str): fmt_items.append((i, 1, {}))
                        elif isinstance(i, (list, tuple)): fmt_items.append((i[0], i[1], {}))

                    pkg = {"xp": xp, "gold": gold, "items": fmt_items}
                    await player_manager.save_player_data(user_id, player_data)
                    await dungeons_runtime.advance_after_victory(update, context, user_id, chat_id, combat_details_recon, pkg)
                    return

                # --- LÓGICA CAÇADA NORMAL ---
                r_ctx = battle_cache.copy()
                r_ctx.update(monster_stats)
                xp, gold, items = rewards.calculate_victory_rewards(player_data, r_ctx)
                
                player_data["xp"] = player_data.get("xp", 0) + xp
                player_data["gold"] = player_data.get("gold", 0) + gold
                
                processed_loot = []
                for i in items:
                     if isinstance(i, str): processed_loot.append((i, 1))
                     elif isinstance(i, (list, tuple)): processed_loot.append((i[0], i[1]))
                
                for i_id, qty in processed_loot:
                    player_manager.add_item_to_inventory(player_data, i_id, qty)

                summary = f"🏆 <b>VITÓRIA!</b>\n\nDerrotou {monster_stats.get('name')}!\n✨ XP: +{xp}\n💰 Ouro: +{gold}\n"
                if processed_loot:
                    summary += "\n📦 Loot:\n" + "\n".join([f"• {q}x {id}" for id, q in processed_loot])

                # Level Up & Missões
                try:
                    _, _, lvl_msg = player_manager.check_and_apply_level_up(player_data)
                    if lvl_msg: summary += lvl_msg
                    
                    mid = monster_stats.get("id")
                    if mid: await mission_manager.update_mission_progress(user_id, "hunt", mid, 1)
                except: pass
                
                # --- [CORREÇÃO] RESTAURAÇÃO COMPLETA PÓS-VITÓRIA ---
                # Recalcula stats (pois o nível pode ter subido) e força HP/MP Max
                stats = await player_manager.get_player_total_stats(player_data)
                player_data['current_hp'] = stats.get('max_hp', 100)
                player_data['current_mp'] = stats.get('max_mana', 50)
                
                player_data['player_state'] = {'action': 'idle'}
                await player_manager.save_player_data(user_id, player_data)
                
                context.user_data.pop('battle_cache', None)
                
                await _edit_media_or_caption(context, battle_cache, summary, battle_cache['player_media_id'], battle_cache['player_media_type'], kb_voltar)
                return 

            except Exception as e:
                logger.error(f"Erro vitória: {e}")
                # Fallback de segurança: salva como idle
                player_data['player_state'] = {'action': 'idle'}
                await player_manager.save_player_data(user_id, player_data)
                context.user_data.pop('battle_cache', None)
                await context.bot.send_message(chat_id, "⚠️ Erro na vitória.", reply_markup=kb_voltar)
                return

        # TURNO DO MONSTRO
        battle_cache['turn'] = 'monster'
        
        dodge = min((player_stats.get('initiative', 0) * 0.4)/100, 0.75)
        if random.random() < dodge:
            log.append("💨 Esquivou!")
        else:
            dmg, _, _ = criticals.roll_damage(monster_stats, player_stats, {})
            log.append(f"⬅️ Recebeu {dmg} dano.")
            battle_cache['player_hp'] = int(battle_cache.get('player_hp', 0)) - dmg
            
            if battle_cache['player_hp'] <= 0:
                log.append("☠️ <b>Derrota!</b>")
                if in_dungeon:
                    await dungeons_runtime.fail_dungeon_run(update, context, user_id, chat_id, "Derrota")
                    return
                
                # --- [CORREÇÃO] Derrota Normal ---
                xp_loss = int(monster_stats.get('xp_reward', 0) * 0.5)
                player_data['xp'] = max(0, player_data.get('xp', 0) - xp_loss)
                
                # <<< RESTAURAÇÃO ADICIONADA AQUI >>>
                # Mesmo na derrota, o jogador volta à vida "na cidade"
                stats_rec = await player_manager.get_player_total_stats(player_data)
                player_data['current_hp'] = stats_rec.get('max_hp', 100)
                player_data['current_mp'] = stats_rec.get('max_mana', 50)
                
                player_data['player_state'] = {'action': 'idle'}
                await player_manager.save_player_data(user_id, player_data)
                
                context.user_data.pop('battle_cache', None)
                media_derrota = (file_id_manager.get_file_data("media_derrota_cacada") or {}).get('id')
                await _edit_media_or_caption(context, battle_cache, f"☠️ <b>Derrota!</b> -{xp_loss} XP", media_derrota, "photo", kb_voltar)
                return

    battle_cache['battle_log'] = log[-12:]
    caption_m = await format_combat_message_from_cache(battle_cache)
    kb = [[InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), InlineKeyboardButton("✨ Skills", callback_data='combat_skill_menu')],
          [InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu'), InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')]]
    
    await _edit_media_or_caption(context, battle_cache, caption_m, battle_cache['monster_media_id'], battle_cache['monster_media_type'], InlineKeyboardMarkup(kb))

combat_handler = CallbackQueryHandler(combat_callback, pattern=r'^(combat_attack|combat_flee|combat_attack_menu|combat_return_to_map)$')