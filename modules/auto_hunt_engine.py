# modules/auto_hunt_engine.py
# (VERSÃO ROBUSTA: Preparada para Recovery System + Anti-Deadlock)

import random
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from telegram.ext import ContextTypes
from collections import Counter
from telegram.error import Forbidden

from telegram import (
    InlineKeyboardMarkup, InlineKeyboardButton, Update,
    InputMediaPhoto, InputMediaVideo
)

# Importa os módulos essenciais
from modules import player_manager, game_data, file_ids as file_id_manager
from modules import mission_manager 
from modules.combat import criticals, rewards 
from modules.player.premium import PremiumManager 

logger = logging.getLogger(__name__)

SECONDS_PER_HUNT = 30 

# ==========================================
# 1. SIMULADOR DE BATALHA (Core Lógico)
# ==========================================
async def _simulate_single_battle(
    player_data: dict, player_stats: dict, monster_data: dict
) -> dict:
    if not monster_data or not isinstance(monster_data, dict):
         return {"result": "loss", "reason": "Dados do monstro inválidos"}

    player_hp = player_stats.get('max_hp', 1)
    monster_hp = monster_data.get('hp', 1)
    
    # Prepara stats simulados
    monster_stats_sim = {
        'attack': monster_data.get('attack', 1),
        'defense': monster_data.get('defense', 0),
        'luck': monster_data.get('luck', 5),
        'monster_name': monster_data.get('name', 'Monstro')
    }

    # Loop de combate (limite 20 turnos)
    for _ in range(20):
        # 1. Player Ataca
        dmg_to_monster, _, _ = criticals.roll_damage(player_stats, monster_stats_sim, {})
        monster_hp -= max(1, dmg_to_monster)
        
        # 2. Verifica Vitória
        if monster_hp <= 0:
            combat_details_for_reward = monster_data.copy()
            combat_details_for_reward['monster_xp_reward'] = monster_data.get('xp_reward', 0)
            combat_details_for_reward['monster_gold_drop'] = monster_data.get('gold_drop', 0)
            
            xp, gold, item_ids_list = rewards.calculate_victory_rewards(player_data, combat_details_for_reward)
            items_rolled = list(Counter(item_ids_list).items())
            
            return {
                "result": "win", 
                "xp": xp, 
                "gold": gold, 
                "items": items_rolled,
                "monster_id": monster_data.get("id")
            }
            
        # 3. Monstro Ataca
        dmg_to_player, _, _ = criticals.roll_damage(monster_stats_sim, player_stats, {})
        player_hp -= max(1, dmg_to_player)
        
        # 4. Verifica Derrota
        if player_hp <= 0:
            return {"result": "loss", "reason": "HP do jogador chegou a 0"}

    return {"result": "loss", "reason": "Batalha demorou muito"}

# ==========================================
# 2. EXECUTOR DE CONCLUSÃO (Universal)
# ==========================================
async def execute_hunt_completion(
    user_id: int, 
    chat_id: int, 
    hunt_count: int, 
    region_key: str, 
    context: ContextTypes.DEFAULT_TYPE, 
    message_id: int = None
):
    """
    Executa a lógica final da caça: simulações, prêmios e mensagem.
    Pode ser chamado pelo Job (normal) ou pelo Recovery Manager (boot).
    """
    logger.info(f"[AutoHunt] Executando conclusão para User {user_id} | Count {hunt_count}")

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        return

    player_stats = await player_manager.get_player_total_stats(player_data)
    region_data = game_data.REGIONS_DATA.get(region_key, {})
    
    monster_list_data = game_data.MONSTERS_DATA.get(region_key)
    if not monster_list_data:
        monster_list_data = region_data.get('monsters', []) 

    if not monster_list_data:
        # Se não houver monstros, libera o jogador
        player_data['player_state'] = {'action': 'idle'}
        await player_manager.save_player_data(user_id, player_data)
        await context.bot.send_message(chat_id, f"⚠️ Erro: Região '{region_key}' sem monstros.")
        return

    # --- Simulação em Lote ---
    total_xp = 0
    total_gold = 0
    total_items = {}
    killed_monsters_ids = []
    wins = 0
    losses = 0

    try:
        for i in range(hunt_count):
            monster_template = random.choice(monster_list_data)
            
            if isinstance(monster_template, str):
                monster_id_str = monster_template
                monster_template = (getattr(game_data, "MONSTER_TEMPLATES", {}) or {}).get(monster_id_str)
                if not monster_template: continue 
            elif not isinstance(monster_template, dict):
                continue

            battle_result = await _simulate_single_battle(player_data, player_stats, monster_template)
            
            if battle_result["result"] == "win":
                wins += 1
                total_xp += int(battle_result["xp"])
                total_gold += int(battle_result["gold"])
                
                if battle_result.get("monster_id"):
                    killed_monsters_ids.append(battle_result.get("monster_id"))

                for item_id, qty in battle_result["items"]:
                    total_items[item_id] = total_items.get(item_id, 0) + qty
            else:
                losses += 1
                logger.info(f"[AutoHunt] {user_id} perdeu na batalha {i+1}. Parando.")
                break # Para na primeira derrota
                
    except Exception as e:
        logger.error(f"[AutoHunt] CRASH na simulação ({user_id}): {e}", exc_info=True)
        player_data['player_state'] = {'action': 'idle'}
        await player_manager.save_player_data(user_id, player_data)
        await context.bot.send_message(chat_id, "⚠️ Erro crítico na simulação.")
        return 

    # --- Aplica Recompensas ---
    player_manager.add_gold(player_data, total_gold)
    player_data['xp'] = player_data.get('xp', 0) + total_xp
    
    items_log_list = []
    items_source = getattr(game_data, "ITEMS_DATA", {}) or {}
    
    for item_id, qty in total_items.items():
        player_manager.add_item_to_inventory(player_data, item_id, qty)
        item_name = items_source.get(item_id, {}).get('display_name', item_id)
        items_log_list.append(f"• {item_name} x{qty}")

    # --- Atualiza Missões ---
    monsters_counter = Counter(killed_monsters_ids)
    try:
        for m_id, count in monsters_counter.items():
            await mission_manager.update_mission_progress(user_id, "hunt", m_id, count)
        for item_id, qty in total_items.items():
            await mission_manager.update_mission_progress(user_id, "collect", item_id, qty)
    except Exception as e:
        logger.error(f"[AutoHunt] Erro missões: {e}")

    # --- Finalização ---
    _, _, level_up_msg = player_manager.check_and_apply_level_up(player_data)
    
    player_data['player_state'] = {'action': 'idle'}
    await player_manager.save_player_data(user_id, player_data)

    # --- Mensagem Final ---
    reg_name = region_data.get('display_name', region_key.title())
    
    summary_msg = [
        "🏁 <b>𝐂𝐚𝐜̧𝐚𝐝𝐚 𝐑𝐚́𝐩𝐢𝐝𝐚 𝐂𝐨𝐧𝐜𝐥𝐮𝐢́𝐝𝐚!</b> 🏁",
        f"Região: {reg_name}",
        f"𝐑𝐞𝐬𝐮𝐥𝐭𝐚𝐝𝐨: <b>{wins} 𝐯𝐢𝐭𝐨́𝐫𝐢𝐚𝐬</b>, <b>{losses} 𝐝𝐞𝐫𝐫𝐨𝐭𝐚𝐬</b>",
        "---",
        f"💰 𝙊𝙪𝙧𝙤: {total_gold}",
        f"⏫🆙 𝙓𝙋: {total_xp}",
    ]
    
    if items_log_list:
        summary_msg.append("\n📦 𝑰𝒕𝒆𝒏𝒔:")
        summary_msg.extend(items_log_list)
    else:
        summary_msg.append("\n📦 𝑵𝒆𝒏𝒉𝒖𝒎 𝒊𝒕𝒆𝒎 𝒆𝒏𝒄𝒐𝒏𝒕𝒓𝒂𝒅𝒐.")
        
    if losses > 0:
        summary_msg.append(f"\n⚠️ <i>𝑷𝒂𝒓𝒐𝒖 𝒂𝒑𝒐́𝒔 𝒅𝒆𝒓𝒓𝒐𝒕𝒂.</i>")
    if level_up_msg:
        summary_msg.append(level_up_msg)
    
    final_caption = "\n".join(summary_msg)
    keyboard = [[InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫 𝐩𝐚𝐫𝐚 𝐚 𝐑𝐞𝐠𝐢𝐚̃𝐨", callback_data=f"open_region:{region_key}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        # Se não temos message_id (chamada via Recovery), mandamos nova mensagem
        if not message_id:
            await context.bot.send_message(chat_id, final_caption, parse_mode="HTML", reply_markup=reply_markup)
            return

        # Tenta editar a mensagem existente (chamada via Job)
        media_key = "autohunt_victory_media" if wins > 0 else "autohunt_defeat_media"
        file_data = file_id_manager.get_file_data(media_key)
        
        if file_data and file_data.get("id"):
            media_type = (file_data.get("type") or "photo").lower()
            InputMediaClass = InputMediaPhoto if media_type == "photo" else InputMediaVideo
            await context.bot.edit_message_media(
                chat_id=chat_id, message_id=message_id,
                media=InputMediaClass(media=file_data.get("id"), caption=final_caption, parse_mode="HTML"),
                reply_markup=reply_markup
            )
        else:
            await context.bot.edit_message_caption(
                chat_id=chat_id, message_id=message_id,
                caption=final_caption, parse_mode="HTML", reply_markup=reply_markup
            )

    except Forbidden:
        logger.warning(f"[AutoHunt] Usuário {user_id} bloqueou o bot. Recompensa entregue, mas notificação falhou.")
        # Não faz nada, pois o jogador já recebeu os itens/XP no banco de dados.
    except Exception as e:
        logger.error(f"[AutoHunt] Erro visual para {user_id}: {e}")
        # Fallback se edição falhar (ex: mensagem muito antiga)
        try:
            await context.bot.send_message(chat_id, final_caption, parse_mode="HTML", reply_markup=reply_markup)
        except Forbidden:
            pass # Ignora bloqueio no fallback também

# ==========================================
# 3. O JOB WRAPPER (Ponte para o Scheduler)
# ==========================================
async def finish_auto_hunt_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Função chamada pelo JobQueue. Apenas extrai dados e chama o executor.
    """
    job_data = context.job.data
    await execute_hunt_completion(
        user_id=job_data.get('user_id'),
        chat_id=job_data.get('chat_id'),
        hunt_count=job_data.get('hunt_count', 0),
        region_key=job_data.get('region_key'),
        context=context,
        message_id=job_data.get('message_id')
    )

# ==========================================
# 4. INICIADOR (Com Anti-Deadlock e Cálculo Local)
# ==========================================
async def start_auto_hunt(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE, 
    hunt_count: int, 
    region_key: str
) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    
    try:
        player_data = await player_manager.get_player_data(user_id)

        # 1. Checagem Premium
        if not PremiumManager(player_data).is_premium():
            await query.answer("⭐️ 𝗙𝘂𝗻𝗰𝗶𝗼𝗻𝗮𝗹𝗶𝗱𝗮𝗱𝗲 𝗲𝘅𝗰𝗹𝘂𝘀𝗶𝘃𝗮 𝗽𝗮𝗿𝗮 𝗣𝗿𝗲𝗺𝗶𝘂𝗺.", show_alert=True)
            return

        # 2. Anti-Deadlock (Cura Estado Travado)
        current_state = player_data.get('player_state', {}).get('action', 'idle')
        finish_time_str = player_data.get('player_state', {}).get('finish_time')
        
        is_stuck = False
        if current_state == 'auto_hunting' and finish_time_str:
            try:
                ft = datetime.fromisoformat(finish_time_str)
                # Se passou 1 min do tempo previsto e ainda tá 'auto_hunting', tá travado.
                if datetime.now(timezone.utc) > ft + timedelta(minutes=1):
                    is_stuck = True
            except:
                is_stuck = True # Data inválida = travado

        if current_state != 'idle' and not is_stuck:
            await query.answer(f"𝗩𝗼𝗰𝗲̂ 𝗲𝘀𝘁𝗮́ 𝗼𝗰𝘂𝗽𝗮𝗱𝗼: {current_state}", show_alert=True)
            return
        
        # 3. Cálculo de Energia (LOCAL - Sem Import Circular)
        base_cost = int(getattr(game_data, "HUNT_ENERGY_COST", 1))
        region_info = (getattr(game_data, "REGIONS_DATA", {}) or {}).get(region_key, {}) or {}
        base_cost = int(region_info.get("hunt_energy_cost", base_cost))
        
        premium = PremiumManager(player_data)
        perk_val = int(premium.get_perk_value("hunt_energy_cost", base_cost))
        cost_per_hunt = max(0, perk_val)
        total_cost = cost_per_hunt * hunt_count
        
        if player_data.get('energy', 0) < total_cost:
            await query.answer(f"𝗘𝗻𝗲𝗿𝗴𝗶𝗮 𝗶𝗻𝘀𝘂𝗳𝗶𝗰𝗶𝗲𝗻𝘁𝗲. 𝗣𝗿𝗲𝗰𝗶𝘀𝗮 𝗱𝗲 {total_cost}⚡.", show_alert=True)
            return

        # 4. Gasto e Setup
        success = player_manager.spend_energy(player_data, total_cost)
        if not success:
            await query.answer("𝗘𝗿𝗿𝗼 𝗮𝗼 𝗽𝗿𝗼𝗰𝗲𝘀𝘀𝗮𝗿 𝗲𝗻𝗲𝗿𝗴𝗶𝗮.", show_alert=True)
            return

        duration_seconds = SECONDS_PER_HUNT * hunt_count 
        
        player_data['player_state'] = {
            'action': 'auto_hunting',
            'finish_time': (datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)).isoformat(),
            'details': {
                'hunt_count': hunt_count, 
                'region_key': region_key
            }
        }
        # IMPORTANTE: Salvar o chat_id para o Recovery System usar depois
        player_manager.set_last_chat_id(player_data, chat_id)
        
        await player_manager.save_player_data(user_id, player_data)

        # 5. Feedback Visual
        region_name = region_info.get('display_name', region_key)
        duration_min = duration_seconds / 60
        
        msg = (
            f"⏱ <b>𝑪𝒂𝒄̧𝒂𝒅𝒂 𝑹𝒂́𝒑𝒊𝒅𝒂 𝑰𝒏𝒊𝒄𝒊𝒂𝒅𝒂!</b>\n"
            f"𝑺𝒊𝒎𝒖𝒍𝒂𝒏𝒅𝒐 {hunt_count} 𝒄𝒐𝒎𝒃𝒂𝒕𝒆𝒔 𝒆𝒎 <b>{region_name}</b>...\n\n"
            f"⚡ 𝑪𝒖𝒔𝒕𝒐: {total_cost} 𝒆𝒏𝒆𝒓𝒈𝒊𝒂\n"
            f"⏳ 𝑻𝒆𝒎𝒑𝒐: <b>{duration_min:.1f} 𝒎𝒊𝒏𝒖𝒕𝒐𝒔</b>.\n\n"
            f"𝑨𝒈𝒖𝒂𝒓𝒅𝒆 𝒐 𝒓𝒆𝒍𝒂𝒕𝒐́𝒓𝒊𝒐 𝒇𝒊𝒏𝒂𝒍."
        )
        
        sent_message = None
        try:
            sent_message = await query.edit_message_caption(caption=msg, parse_mode="HTML", reply_markup=None)
        except Exception:
            try:
                sent_message = await query.edit_message_text(text=msg, parse_mode="HTML", reply_markup=None)
            except:
                sent_message = await context.bot.send_message(chat_id, msg, parse_mode="HTML")

        # 6. Agenda Job
        job_data = {
            "user_id": user_id,
            "chat_id": chat_id,
            "message_id": sent_message.message_id if sent_message else None,
            "hunt_count": hunt_count,
            "region_key": region_key
        }
        context.job_queue.run_once(
            finish_auto_hunt_job, 
            when=duration_seconds, 
            data=job_data, 
            name=f"autohunt_{user_id}"
        )

    except Exception as e:
        logger.error(f"[AutoHunt] ERRO DE INICIALIZAÇÃO ({user_id}): {e}", exc_info=True)
        await query.answer("Erro ao iniciar. Admin notificado.", show_alert=True)