# handlers/combat/main_handler.py
# (VERSÃO ZERO-TOLERANCE: IDs STRINGS OBRIGATÓRIOS)

import logging
import random
import asyncio
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaVideo, InputMediaPhoto
from telegram.ext import ContextTypes, CallbackQueryHandler
# war
from telegram.error import BadRequest
from modules.guild_war.combat_integration import try_award_pve_kill_for_guild_war
from modules.game_data import regions as game_data_regions


# Importações dos módulos
from modules import player_manager, game_data, class_evolution_service, clan_manager
from modules import mission_manager 
from handlers.menu.region import send_region_menu
from handlers.utils import format_combat_message_from_cache, format_combat_message
from modules.combat import durability, criticals, rewards, combat_engine
from modules.cooldowns import verificar_cooldown, aplicar_cooldown, iniciar_turno

from modules.dungeons import runtime as dungeons_runtime
from handlers.class_evolution_handler import open_evolution_menu
from handlers.profile_handler import _get_class_media
from modules.dungeons.runtime import _send_battle_media
from modules import file_ids as file_id_manager

# Importação Centralizada de Skills
from modules.game_data.skills import SKILL_DATA, get_skill_data_with_rarity
from modules.skills.skill_effects_adapter import apply_skill_effects
from modules.skills.skill_effects_adapter import apply_on_hit_passives
from modules.game_data.skills import get_skill_data_with_rarity
from modules.game_data.monsters import MONSTER_SKILLS_DB
# Effect Engine (BUFF / DEBUFF)
from modules.effects.engine import (
    apply_effect,
    dispatch,
    tick_turn,
    can_act,
)
from modules.effects.models import (
    CombatContext,
    EVENT_ON_BEFORE_DAMAGE,
    EVENT_ON_HEAL,
)

logger = logging.getLogger(__name__)

# ================================================
# 1. HELPER DE SEGURANÇA (ID ESTRITO)
# ================================================
def _get_combat_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[str]:
    """
    Retorna o ID do jogador (ObjectId String) da sessão.
    NÃO faz fallback para ID do Telegram. Se não tiver sessão, retorna None.
    """
    logged_id = context.user_data.get("logged_player_id")
    if logged_id:
        return str(logged_id)
    return None

# ================================================
# 2. HELPERS VISUAIS
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
        # Fallback para reenvio se a edição falhar (ex: mídia expirada)
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


def _build_passive_overrides_for_player_attack(player_data: dict, battle_cache: dict) -> dict:
    """
    PASSIVA: evo_shadow_thief_ambush (Emboscada)
    Aplica bônus APENAS no primeiro ataque do combate (básico ou skill).
    Não altera player_data, só usa battle_cache.passive_state.
    """
    ps = battle_cache.setdefault("passive_state", {})
    if ps.get("first_hit_used", False):
        return {}

    ambush_id = "evo_shadow_thief_ambush"
    skills = (player_data.get("skills") or {})
    if ambush_id not in skills:
        return {}

    ambush_info = get_skill_data_with_rarity(player_data, ambush_id) or {}
    effects = (ambush_info.get("effects") or {})
    fh = (effects.get("first_hit_bonus") or {})
    if not fh:
        return {}

    ps["first_hit_used"] = True

    return {
        "damage_mult_add": float(fh.get("damage_mult", 0.0) or 0.0),
        "bonus_crit_chance_add": float(fh.get("crit_chance_flat", 0.0) or 0.0),
        "armor_pen_add": float(fh.get("armor_penetration", 0.0) or 0.0),
    }

# ================================================
# 3. MOTOR DE COMBATE
# ================================================

async def combat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str = None) -> None:
    query = update.callback_query
    if action is None and query: action = query.data
    elif action is None and not query: return

    # --- SEGURANÇA DE SESSÃO ---
    user_id = _get_combat_user_id(update, context)
    chat_id = query.message.chat_id if query else update.effective_chat.id
    
    if not user_id:
        if query:
            try: await query.answer("⚠️ Sessão expirada. Use /start para logar.", show_alert=True)
            except: pass
        return
    # ---------------------------

    # 1. Retornar ao Mapa
    if action == 'combat_return_to_map':
        if query: await _safe_answer(query)
        context.user_data.pop('battle_cache', None)
        player_data = await player_manager.get_player_data(user_id)
        if player_data:
            if "cooldowns" in player_data:
                player_data.pop("cooldowns", None)
            
            player_data['player_state'] = {'action': 'idle'}
            await player_manager.save_player_data(user_id, player_data)
            await send_region_menu(context, user_id, chat_id)
            try: await query.delete_message()
            except: pass
        return

    # 2. Menu de Ataque
    if action == 'combat_attack_menu':
        if not query: return
        await _safe_answer(query)
        kb = [[InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), InlineKeyboardButton("✨ Skills", callback_data='combat_skill_menu')],
              [InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu'), InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')]]
        try: await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
        except: pass
        return

    if query: await _safe_answer(query)
    
    # 3. Recuperação/Criação do Cache de Batalha
    battle_cache = context.user_data.get('battle_cache')
    cache_uid = str(battle_cache.get('player_id')) if battle_cache else None
    current_uid = str(user_id)

    # Verifica se o cache existe e pertence ao usuário LOGADO atual
    if not battle_cache or cache_uid != current_uid:
        player_data = await player_manager.get_player_data(user_id)
        if not player_data: return

        state_action = player_data.get('player_state', {}).get('action')
            
        if state_action in ['in_combat', 'evolution_combat']:
            details = player_data['player_state'].get('details', {})
            
            # Recuperação de Dungeon
            if "dungeon_ctx" in details:
                from modules.dungeons import runtime as d_rt
                msg_id = query.message.message_id if query and query.message else None
                await d_rt._update_battle_cache(context, user_id, player_data, details, message_id=msg_id, chat_id=chat_id)
                return await combat_callback(update, context, action)
            
            # Recuperação de Caçada Normal
            else:
                p_stats = await player_manager.get_player_total_stats(player_data)
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
                # ==================================================
                # NORMALIZAÇÃO DE STATS DO MONSTRO (IGUAL AO PLAYER)
                # ==================================================
                monster_stats.setdefault("accuracy", 0.0)
                monster_stats.setdefault("dodge_chance_flat", 0.0)
                monster_stats.setdefault("crit_chance_flat", 0.0)
                monster_stats.setdefault("crit_damage_mult", 0.0)
                monster_stats.setdefault("armor_penetration", 0.0)
                monster_stats.setdefault("cannot_be_dodged", False)

                # Garantia de hp_max para efeitos e engine
                monster_stats["hp_max"] = monster_stats.get("max_hp", monster_stats.get("hp", 1))

                p_media = _get_class_media(player_data, purpose="combate")
                new_cache = {
                    'player_id': user_id, # String ID
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
                    'dungeon_ctx': None,
                    'region_key': details.get('region_key'),
                    'passive_state': {
                        'first_hit_used': False,
                    },
                }
                context.user_data['battle_cache'] = new_cache
                return await combat_callback(update, context, action)
        else:
            if query:
                try: await query.edit_message_caption(caption="⚠️ Sessão de batalha expirada. Retornando...", reply_markup=None)
                except: pass
                await asyncio.sleep(1)
                await send_region_menu(context, user_id, chat_id)
            return

    # --- VARIÁVEIS DE BATALHA ---
    log = list(battle_cache.get('battle_log', []))
    player_stats = battle_cache.get('player_stats', {}) 
    monster_stats = battle_cache.get('monster_stats', {})
    dungeon_ctx = battle_cache.get('dungeon_ctx')
    in_dungeon = bool(dungeon_ctx)

    kb_voltar = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar para o Mapa", callback_data='combat_return_to_map')]])
    
    # ============================================
    # AÇÃO: FUGA
    # ============================================
    if action == 'combat_flee':
        hp_atual_batalha = battle_cache.get('player_hp')
        context.user_data.pop('battle_cache', None)
        player_data = await player_manager.get_player_data(user_id)
        
        if hp_atual_batalha is not None:
            player_data['current_hp'] = int(hp_atual_batalha)
            
        player_data['player_state'] = {'action': 'idle'}
        if "cooldowns" in player_data: player_data.pop("cooldowns", None)

        await player_manager.save_player_data(user_id, player_data)
        try: await query.delete_message()
        except: pass
        
        if in_dungeon:
             await dungeons_runtime.fail_dungeon_run(update, context, user_id, chat_id, "Você fugiu")
             return

        media_fuga = (file_id_manager.get_file_data("media_fuga_sucesso") or {}).get("id")
        await _send_battle_media(context, chat_id, "🏃 <b>FUGA!</b>\n\nEscapou com segurança.", media_fuga, kb_voltar)
        return

    # ============================================
    # AÇÃO: ATAQUE / SKILL
    # ============================================
    elif action == 'combat_attack':
        player_data = await player_manager.get_player_data(user_id)
        if not player_data: return
                # ============================
        # EFFECTS: início do turno do jogador (DOT/HOT + expiração)
        # ============================

        # Garantir hp_max para o engine limitar cura corretamente
        # (o engine usa hp_max ou max_hp)
        battle_cache["hp_max"] = int(player_stats.get("max_hp", 100))

        effect_msgs = tick_turn(
            battle_cache,      # entidade do jogador (usando battle_cache)
            battle_cache,      # battle (contexto)
            apply_to_hp_key="player_hp"
        )
        if effect_msgs:
            log.extend(effect_msgs)

        # ============================
        # EFFECTS: controle (stun/cannot_act)
        # ============================
        if not can_act(battle_cache):
            log.append("💫 Você está impedido de agir!")
            # Se estiver stunado, o jogador perde a ação, mas o monstro ainda joga.
            # Forçamos: não usar skill/ataque, e segue para TURNO DO MONSTRO.
            skip_monster_turn = False
            player_damage = 0

            # NÃO retorne aqui — deixe o fluxo seguir para o TURNO DO MONSTRO
            # Abaixo, vamos pular o processamento do ataque do jogador.
    
        battle_cache['turn'] = 'player'
        skill_id = battle_cache.pop('skill_to_use', None) 
        action_type = battle_cache.pop('action_type', 'attack')
        
        if skill_id:
            pode_usar, msg_cd = verificar_cooldown(player_data, skill_id)
            if not pode_usar:
                if query: await query.answer(msg_cd, show_alert=True)
                return 

        skill_info = get_skill_data_with_rarity(player_data, skill_id) if skill_id else None
        skip_monster_turn = False
        player_damage = 0 
        
        if not can_act(battle_cache):
            skill_info = None
            action_type = "attack"

        # --- TURNO DO JOGADOR ---
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
                    
                    cur = int(battle_cache.get('player_hp', 0))
                    mx = int(player_stats.get('max_hp', 100))

                    # ============================
                    # EFFECTS: heal pipeline (anti-heal, buffs de cura, etc.)
                    # ============================
                    battle_cache["hp_max"] = mx  # garante limite para o engine

                    ctx = CombatContext(
                        event=EVENT_ON_HEAL,
                        source=battle_cache,
                        target=battle_cache,
                        battle=battle_cache,
                        heal=int(base_heal),
                    )
                    dispatch(EVENT_ON_HEAL, ctx)
                    final_heal = int(ctx.heal)

                    new_h = min(mx, cur + final_heal)
                    if new_h > cur:
                        battle_cache['player_hp'] = new_h
                        log.append(f"❤️ Cura: +{new_h - cur} HP")

                skip_monster_turn = True 
            else:
                passive_overrides = _build_passive_overrides_for_player_attack(player_data, battle_cache)

                res = await combat_engine.processar_acao_combate(
                    player_data,
                    player_stats,
                    monster_stats,
                    skill_id,
                    battle_cache.get('player_hp'),
                    passive_overrides=passive_overrides,
                )
                player_damage = res["total_damage"]
                log.extend(res["log_messages"])

                # ============================
                # EFFECTS: aplicar efeitos da skill
                # ============================
                apply_skill_effects(
                    skill_id=skill_id,
                    skill_info=skill_info,
                    player_id=user_id,
                    player_stats=player_stats,
                    battle_cache=battle_cache,
                    monster_stats=monster_stats,
                    log=log,
                    combat_result=res,
                )



            
            raridade = "comum"
            if player_data.get("skills") and skill_id in player_data["skills"]:
                raridade = player_data["skills"][skill_id].get("rarity", "comum")
            player_data = aplicar_cooldown(player_data, skill_id, raridade)

        else:
            # ATAQUE BÁSICO
            # Regra de design:
            # - NÃO aplica DOT ATIVO (bleed)
            # - PASSIVAS on-hit (ex.: veneno) podem proc-ar aqui
            log.append("⚔️ Ataque básico.")

            passive_overrides = _build_passive_overrides_for_player_attack(player_data, battle_cache)

            res = await combat_engine.processar_acao_combate(
                player_data,
                player_stats,
                monster_stats,
                None,
                battle_cache.get('player_hp'),
                passive_overrides=passive_overrides,
            )

            player_damage = res["total_damage"]
            log.extend(res["log_messages"])

            # ============================
            # PASSIVAS ON-HIT (VENENO ETC)
            # ============================
            apply_on_hit_passives(
                player_data=player_data,
                player_id=user_id,
                player_stats=player_stats,
                battle_cache=battle_cache,
                monster_stats=monster_stats,
                log=log,
                combat_result=res,
            )


            player_damage = res["total_damage"]
            log.extend(res["log_messages"])


        if not skip_monster_turn:
            if 'hp' not in monster_stats:
                monster_stats['hp'] = monster_stats.get('max_hp', 100)

            # ============================
            # EFFECTS: before damage (jogador -> monstro)
            # ============================
            # Garantir hp_max no monstro para o engine (cura/limites futuros)
            if "hp_max" not in monster_stats:
                monster_stats["hp_max"] = int(monster_stats.get("max_hp", monster_stats.get("hp", 1)))

            ctx = CombatContext(
                event=EVENT_ON_BEFORE_DAMAGE,
                source=battle_cache,      # jogador (entidade)
                target=monster_stats,     # monstro
                battle=battle_cache,      # contexto do combate
                damage=int(player_damage),
                damage_type="physical",
            )
            dispatch(EVENT_ON_BEFORE_DAMAGE, ctx)

            final_damage = int(ctx.damage)
            monster_stats['hp'] = int(monster_stats['hp']) - final_damage

            
        monster_defeated = monster_stats.get('hp', 0) <= 0
        battle_cache['battle_log'] = log[-12:]
        
        caption_p = await format_combat_message_from_cache(battle_cache)
        
        if skip_monster_turn:
            
            player_data, msgs_cd = iniciar_turno(player_data)
            if msgs_cd:
                for msg in msgs_cd: log.append(msg)
            await player_manager.save_player_data(user_id, player_data)
            
            kb = [[InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), InlineKeyboardButton("✨ Skills", callback_data='combat_skill_menu')],
                  [InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu'), InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')]]
            await _edit_media_or_caption(context, battle_cache, caption_p, battle_cache['player_media_id'], battle_cache['player_media_type'], InlineKeyboardMarkup(kb))
            return 
            
        # ============================================
        # VITÓRIA
        # ============================================
        if monster_defeated:
            # limpa cooldowns e salva
            if "cooldowns" in player_data:
                player_data.pop("cooldowns", None)

            await player_manager.save_player_data(user_id, player_data)

            try:
                log.append(f"🏆 <b>{monster_stats.get('name')} derrotado!</b>")

                state_action = player_data.get("player_state", {}).get("action")

                # =========================
                # EVOLUTION COMBAT
                # =========================
                if state_action == "evolution_combat":
                    context.user_data.pop("battle_cache", None)

                    if "cooldowns" in player_data:
                        player_data.pop("cooldowns", None)

                    details = player_data.get("player_state", {}).get("details", {})
                    target_class = details.get("target_class_reward")

                    success, msg_evo = await class_evolution_service.finalize_evolution(user_id, target_class)
                    player_data = await player_manager.get_player_data(user_id)

                    player_data["player_state"] = {"action": "idle"}
                    await player_manager.save_player_data(user_id, player_data)

                    media_sucesso = (file_id_manager.get_file_data("media_evolution_success") or {}).get("id")
                    final_text = (
                        f"🏆 <b>VITÓRIA LENDÁRIA!</b>\n\n{msg_evo}\n\n"
                        f"<i>Seus atributos aumentaram e novas habilidades foram desbloqueadas.</i>"
                    )
                    kb_fim = [[InlineKeyboardButton("📜 Ver Perfil", callback_data="profile")]]

                    await _edit_media_or_caption(
                        context,
                        battle_cache,
                        final_text,
                        media_sucesso,
                        "photo",
                        InlineKeyboardMarkup(kb_fim),
                    )
                    return

                # =========================
                # CASO 1: DUNGEON (NÃO CONTA PARA GUERRA)
                # =========================
                if in_dungeon:
                    combat_details_recon = {
                        "region_key": battle_cache.get("region_key"),
                        "difficulty": dungeon_ctx.get("difficulty"),
                        "dungeon_stage": dungeon_ctx.get("floor_idx", 0),
                        "dungeon_ctx": dungeon_ctx,
                        "loot_table": monster_stats.get("loot_table", []),
                        "file_id_name": battle_cache.get("monster_media_id"),
                    }

                    r_ctx = battle_cache.copy()
                    r_ctx.update(monster_stats)

                    xp, gold, items = rewards.calculate_victory_rewards(player_data, r_ctx)

                    fmt_items = []
                    for i in items:
                        if isinstance(i, str):
                            fmt_items.append((i, 1, {}))
                        elif isinstance(i, (list, tuple)):
                            fmt_items.append((i[0], i[1], {}))

                    pkg = {"xp": xp, "gold": gold, "items": fmt_items}
                    await dungeons_runtime.advance_after_victory(update, context, user_id, chat_id, combat_details_recon, pkg)
                    return

                # =========================
                # CASO 2: COMBATE NORMAL
                # =========================
                durability.apply_end_of_battle_wear(player_data, battle_cache, log)
                await player_manager.save_player_data(user_id, player_data)

                r_ctx = battle_cache.copy()
                r_ctx.update(monster_stats)

                xp, gold, items = rewards.calculate_victory_rewards(player_data, r_ctx)

                player_data["xp"] = player_data.get("xp", 0) + xp
                player_data["gold"] = player_data.get("gold", 0) + gold

                processed_loot = []
                for i in items:
                    if isinstance(i, str):
                        processed_loot.append((i, 1))
                    elif isinstance(i, (list, tuple)):
                        processed_loot.append((i[0], i[1]))

                for i_id, qty in processed_loot:
                    player_manager.add_item_to_inventory(player_data, i_id, qty)

                summary = (
                    f"🏆 <b>VITÓRIA!</b>\n\n"
                    f"Derrotou {monster_stats.get('name')}!\n"
                    f"✨ XP: +{xp}\n"
                    f"💰 Ouro: +{gold}\n"
                )
                # =========================
                # LOG FINAL (últimos eventos)
                # =========================
                final_log_lines = log[-10:]  # ajuste 8-12 como preferir
                if final_log_lines:
                    summary += "\n\n📜 <b>Últimos eventos:</b>\n"
                    for line in final_log_lines:
                        summary += f"• {line}\n"

                if processed_loot:
                    summary += "\n📦 <b>Loot Encontrado:</b>\n"
                    for i_id, qty in processed_loot:
                        item_info = game_data.ITEMS_DATA.get(i_id, {})
                        i_name = item_info.get("display_name") or i_id.replace("_", " ").title()
                        i_emoji = item_info.get("emoji", "🎲")
                        summary += f"• {qty}x {i_emoji} {i_name}\n"

                try:
                    before_lvl = player_data.get("level")
                    before_xp = player_data.get("xp")

                    _, _, lvl_msg = player_manager.check_and_apply_level_up(player_data)

                    after_lvl = player_data.get("level")
                    after_xp = player_data.get("xp")

                    logger.warning(
                        f"[LEVELUP] before: lvl={before_lvl} xp={before_xp} | "
                        f"after: lvl={after_lvl} xp={after_xp} | msg={lvl_msg}"
                    )

                    if lvl_msg:
                        summary += lvl_msg

                    mid = monster_stats.get("id")
                    if mid:
                        await mission_manager.update_mission_progress(user_id, "hunt", mid, 1)

                except Exception as e:
                    logger.exception(f"[LEVELUP] erro em check_and_apply_level_up: {e}")


                stats = await player_manager.get_player_total_stats(player_data)
                player_data["current_hp"] = stats.get("max_hp", 100)
                player_data["current_mp"] = stats.get("max_mana", 50)
                player_data["player_state"] = {"action": "idle"}

                # =========================
                # GUERRA DE CLÃ (PVE KILL) - SOMENTE COMBATE NORMAL
                # =========================
                try:
                    await try_award_pve_kill_for_guild_war(
                        player_id=user_id,
                        player_data=player_data,
                        region_key=battle_cache.get("region_key"),
                        game_data_regions_module=game_data_regions,
                        base_points=3,
                    )
                except Exception:
                    pass

                await player_manager.save_player_data(user_id, player_data)
                context.user_data.pop("battle_cache", None)

                await _edit_media_or_caption(
                    context,
                    battle_cache,
                    summary,
                    battle_cache["player_media_id"],
                    battle_cache["player_media_type"],
                    kb_voltar,
                )
                return

            except Exception as e:
                logger.error(f"Erro vitória: {e}")
                player_data["player_state"] = {"action": "idle"}
                await player_manager.save_player_data(user_id, player_data)
                context.user_data.pop("battle_cache", None)
                await context.bot.send_message(chat_id, "⚠️ Erro na vitória.", reply_markup=kb_voltar)
                return

    # ============================================
    # TURNO DO MONSTRO
    # ============================================
        battle_cache['turn'] = 'monster'
        
        # ============================
        # EFFECTS: início do turno do monstro (DOT/HOT + expiração)
        # ============================
        if "hp_max" not in monster_stats:
            monster_stats["hp_max"] = int(monster_stats.get("max_hp", monster_stats.get("hp", 1)))

        effect_msgs = tick_turn(
            monster_stats,
            battle_cache,
            apply_to_hp_key="hp"
        )
        if effect_msgs:
            log.extend(effect_msgs)

        # Se o monstro morreu por DOT (bleed/poison), não executa o ataque do monstro
        if monster_stats.get("hp", 0) <= 0:
            log.append(f"🏆 <b>{monster_stats.get('name')} derrotado!</b>")
            battle_cache['battle_log'] = log[-12:]
            caption_m = await format_combat_message_from_cache(battle_cache)
            kb = [[InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'),
                   InlineKeyboardButton("✨ Skills", callback_data='combat_skill_menu')],
                  [InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu'),
                   InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')]]
            await _edit_media_or_caption(
                context,
                battle_cache,
                caption_m,
                battle_cache['monster_media_id'],
                battle_cache['monster_media_type'],
                InlineKeyboardMarkup(kb)
            )
            return

        dodge_chance = min((player_stats.get('initiative', 0) * 0.4)/100, 0.75)
        dodge_chance += player_stats.get('dodge_chance_flat', 0)
        cannot_miss = monster_stats.get("cannot_be_dodged", False)


        if not cannot_miss and random.random() < dodge_chance:
            log.append(f"💨 Você esquivou do ataque de {monster_stats['name']}!")
            player_data, msgs_cd = iniciar_turno(player_data)
            if msgs_cd: log.extend(msgs_cd)
            await player_manager.save_player_data(user_id, player_data)
        
        else:
            skill_used = None
            damage_dealt = 0
            mob_skills = monster_stats.get("skills", [])
            
            if mob_skills:
                chosen_id = random.choice(mob_skills)
                s_data = MONSTER_SKILLS_DB.get(chosen_id)
                if s_data and random.random() < s_data.get("chance", 0.2):
                    skill_used = s_data

            if skill_used:
                action_msg = skill_used.get("log", "{mob} ataca violentamente!").format(mob=monster_stats['name'])
                log.append(f"⚠️ {action_msg}")
                
                if "heal_pct" in skill_used:
                    heal_val = int(monster_stats['max_hp'] * skill_used['heal_pct'])
                    monster_stats['hp'] = min(monster_stats['max_hp'], monster_stats['hp'] + heal_val)
                    log.append(f"💚 {monster_stats['name']} recuperou {heal_val} HP!")
                    damage_dealt = 0
                else:
                    mult = skill_used.get("damage_mult", 1.0)
                    is_magic = skill_used.get("magic", False)

                    raw_dmg = int(monster_stats['attack'] * mult)
                    def_val = (
                        player_stats.get('magic_resistance', 0)
                        if is_magic
                        else player_stats.get('defense', 0)
                    )
                    base_dmg = max(1, raw_dmg - int(def_val * 0.5))

                    # ============================
                    # EFFECTS: before damage (monstro -> jogador)
                    # ============================
                    ctx = CombatContext(
                        event=EVENT_ON_BEFORE_DAMAGE,
                        source=monster_stats,
                        target=battle_cache,
                        battle=battle_cache,
                        damage=int(base_dmg),
                        damage_type="magic" if is_magic else "physical",
                    )
                    dispatch(EVENT_ON_BEFORE_DAMAGE, ctx)

                    final_taken = int(ctx.damage)
                    battle_cache['player_hp'] = int(battle_cache.get('player_hp', 0)) - final_taken

                    log.append(f"💥 Recebeu {final_taken} dano! ({skill_used['name']})")


            else:
                dmg, is_crit, _ = criticals.roll_damage(monster_stats, player_stats, {})
                crit_txt = " (CRÍTICO!)" if is_crit else ""

                # ============================
                # EFFECTS: before damage (monstro -> jogador)
                # ============================
                ctx = CombatContext(
                    event=EVENT_ON_BEFORE_DAMAGE,
                    source=monster_stats,
                    target=battle_cache,
                    battle=battle_cache,
                    damage=int(dmg),
                    damage_type="physical",
                )
                ctx.flags.is_crit = bool(is_crit)

                dispatch(EVENT_ON_BEFORE_DAMAGE, ctx)

                final_taken = int(ctx.damage)
                battle_cache['player_hp'] = int(battle_cache.get('player_hp', 0)) - final_taken

                log.append(f"⬅️ Recebeu {final_taken}{crit_txt} dano.")



            if battle_cache['player_hp'] <= 0:
                log.append("☠️ <b>Derrota!</b>")
                if "cooldowns" in player_data: player_data.pop("cooldowns", None)

                if in_dungeon:
                    await dungeons_runtime.fail_dungeon_run(update, context, user_id, chat_id, "Derrota")
                    return
                
                xp_loss = int(monster_stats.get('xp_reward', 0) * 0.5)
                player_data['xp'] = max(0, player_data.get('xp', 0) - xp_loss)
                
                stats_rec = await player_manager.get_player_total_stats(player_data)
                player_data['current_hp'] = stats_rec.get('max_hp', 100)
                player_data['current_mp'] = stats_rec.get('max_mana', 50)
                player_data['player_state'] = {'action': 'idle'}
                
                await player_manager.save_player_data(user_id, player_data)
                context.user_data.pop('battle_cache', None)
                media_derrota = (file_id_manager.get_file_data("media_derrota_cacada") or {}).get('id')
                defeat_text = f"☠️ <b>Derrota!</b>\n-{xp_loss} XP\n"

                final_log_lines = log[-10:]
                if final_log_lines:
                    defeat_text += "\n📜 <b>Últimos eventos:</b>\n"
                    for line in final_log_lines:
                        defeat_text += f"• {line}\n"

                await _edit_media_or_caption(context, battle_cache, defeat_text, media_derrota, "photo", kb_voltar)

                return

            player_data, msgs_cd = iniciar_turno(player_data)
            if msgs_cd:
                for msg in msgs_cd: log.append(msg)
            await player_manager.save_player_data(user_id, player_data)

    # Atualização Visual
    battle_cache['battle_log'] = log[-12:]
    caption_m = await format_combat_message_from_cache(battle_cache)
    kb = [[InlineKeyboardButton("⚔️ Atacar", callback_data='combat_attack'), InlineKeyboardButton("✨ Skills", callback_data='combat_skill_menu')],
          [InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu'), InlineKeyboardButton("🏃 Fugir", callback_data='combat_flee')]]
    
    await _edit_media_or_caption(context, battle_cache, caption_m, battle_cache['monster_media_id'], battle_cache['monster_media_type'], InlineKeyboardMarkup(kb))

combat_handler = CallbackQueryHandler(combat_callback, pattern=r'^(combat_attack|combat_flee|combat_attack_menu|combat_return_to_map)$')