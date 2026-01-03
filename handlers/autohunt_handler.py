# handlers/autohunt_handler.py
# (VERSÃO CORRIGIDA: Libera Plano Lenda/Admin Manualmente)

import random
import logging
import re
from datetime import datetime, timezone, timedelta
from collections import Counter

from telegram import (
    InlineKeyboardMarkup, InlineKeyboardButton, Update,
    InputMediaPhoto, InputMediaVideo
)
from telegram.ext import ContextTypes, CallbackQueryHandler

# --- Imports do Core & Utils ---
from modules.auth_utils import get_current_player_id
from modules import player_manager, game_data, file_ids as file_id_manager
from modules import mission_manager 
from modules.combat import criticals, rewards 
from modules.player.premium import PremiumManager 

logger = logging.getLogger(__name__)

SECONDS_PER_HUNT = 30 

# ==============================================================================
# 🛠️ 1. FUNÇÕES AUXILIARES DE ESCALA
# ==============================================================================
def _scale_monster_stats(mon: dict, player_level: int) -> dict:
    m = mon.copy()
    if "max_hp" not in m and "hp" in m: m["max_hp"] = m["hp"]
    elif "max_hp" not in m: m["max_hp"] = 10 

    min_lvl = m.get("min_level", 1)
    max_lvl = m.get("max_level", player_level + 2)
    target_lvl = max(min_lvl, min(player_level + random.randint(-1, 1), max_lvl))
    m["level"] = target_lvl

    raw_name = m.get("name", "Inimigo").replace("Lv.", "").strip()
    raw_name = re.sub(r"^\d+\s+", "", raw_name) 
    m["name"] = f"Lv.{target_lvl} {raw_name}"

    if target_lvl <= 1:
        m["hp"] = m["max_hp"]
        return m

    # Coeficientes
    GROWTH_HP, GROWTH_ATK, GROWTH_DEF = 12, 2.0, 1.0
    GROWTH_XP, GROWTH_GOLD = 3, 1.5    
    scaling_bonus = 1 + (target_lvl * 0.02) 

    base_hp = int(m.get("max_hp", 10))
    base_atk = int(m.get("attack", 2))
    base_def = int(m.get("defense", 0))
    base_xp = int(m.get("xp_reward", 5))
    base_gold = int(m.get("gold_drop", 1))

    m["max_hp"] = int((base_hp * scaling_bonus) + (target_lvl * GROWTH_HP))
    m["hp"] = m["max_hp"]
    m["attack"] = int((base_atk * scaling_bonus) + (target_lvl * GROWTH_ATK))
    m["defense"] = int((base_def * scaling_bonus) + (target_lvl * GROWTH_DEF))
    m["xp_reward"] = int((base_xp * scaling_bonus) + (target_lvl * GROWTH_XP))
    m["gold_drop"] = int((base_gold * scaling_bonus) + (target_lvl * GROWTH_GOLD))
    
    return m

# ==============================================================================
# ⚔️ 2. MOTOR DE SIMULAÇÃO DE BATALHA
# ==============================================================================
async def _simulate_single_battle(player_data: dict, player_stats: dict, monster_data: dict) -> dict:
    if not monster_data or not isinstance(monster_data, dict):
         return {"result": "loss", "reason": "Dados do monstro inválidos"}

    player_hp = player_stats.get('max_hp', 1)
    monster_hp = monster_data.get('hp', 1)
    
    monster_stats_sim = {
        'attack': monster_data.get('attack', 1),
        'defense': monster_data.get('defense', 0),
        'luck': monster_data.get('luck', 5),
        'monster_name': monster_data.get('name', 'Monstro')
    }

    for _ in range(20):
        # 1. Player Ataca
        dmg_to_monster, _, _ = criticals.roll_damage(player_stats, monster_stats_sim, {})
        monster_hp -= max(1, dmg_to_monster)
        
        if monster_hp <= 0:
            combat_details = monster_data.copy()
            combat_details['monster_xp_reward'] = monster_data.get('xp_reward', 0)
            combat_details['monster_gold_drop'] = monster_data.get('gold_drop', 0)
            
            xp, gold, item_ids_list = rewards.calculate_victory_rewards(player_data, combat_details)
            items_rolled = list(Counter(item_ids_list).items())
            
            return {
                "result": "win", "xp": xp, "gold": gold, "items": items_rolled,
                "monster_id": monster_data.get("id")
            }
            
        # 2. Monstro Ataca
        dmg_to_player, _, _ = criticals.roll_damage(monster_stats_sim, player_stats, {})
        player_hp -= max(1, dmg_to_player)
        if player_hp <= 0: return {"result": "loss", "reason": "HP do jogador esgotado"}

    return {"result": "loss", "reason": "Exaustão (Tempo Esgotado)"}

# ==============================================================================
# 🏁 3. EXECUTOR DE CONCLUSÃO (JOB)
# ==============================================================================
async def execute_hunt_completion(user_id: str, chat_id: int, hunt_count: int, region_key: str, context: ContextTypes.DEFAULT_TYPE, message_id: int = None):
    """Finaliza a simulação, limpa a mídia de início e envia o resultado."""
    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return

    player_stats = await player_manager.get_player_total_stats(player_data)
    player_level = int(player_data.get("level", 1))

    region_data = game_data.REGIONS_DATA.get(region_key, {})
    monster_list_data = game_data.MONSTERS_DATA.get(region_key) or region_data.get('monsters', []) 

    if not monster_list_data:
        player_data['player_state'] = {'action': 'idle'}
        await player_manager.save_player_data(user_id, player_data)
        return

    # --- Loop de Simulação ---
    total_xp, total_gold, wins, losses = 0, 0, 0, 0
    total_items = {}
    killed_monsters_ids = []

    try:
        for _ in range(hunt_count):
            monster_template = random.choice(monster_list_data)
            if isinstance(monster_template, str):
                monster_template = (getattr(game_data, "MONSTER_TEMPLATES", {}) or {}).get(monster_template)
            
            if not monster_template: continue
            
            monster_scaled = _scale_monster_stats(monster_template, player_level)
            battle_result = await _simulate_single_battle(player_data, player_stats, monster_scaled)
            
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
                break 
                
    except Exception as e:
        logger.error(f"[AutoHunt] Erro na simulação: {e}")
        player_data['player_state'] = {'action': 'idle'}
        await player_manager.save_player_data(user_id, player_data)
        return 

    # --- Recompensas ---
    player_manager.add_gold(player_data, total_gold)
    player_data['xp'] = player_data.get('xp', 0) + total_xp
    
    items_log_list = []
    items_source = getattr(game_data, "ITEMS_DATA", {}) or {}
    for item_id, qty in total_items.items():
        player_manager.add_item_to_inventory(player_data, item_id, qty)
        name = items_source.get(item_id, {}).get('display_name', item_id)
        items_log_list.append(f"• {name} x{qty}")

    try:
        mission_uid = str(user_id)
        for m_id, count in Counter(killed_monsters_ids).items():
            await mission_manager.update_mission_progress(mission_uid, "hunt", m_id, count)
        for item_id, qty in total_items.items():
            await mission_manager.update_mission_progress(mission_uid, "collect", item_id, qty)
    except: pass

    _, _, level_up_msg = player_manager.check_and_apply_level_up(player_data)
    
    player_data['player_state'] = {'action': 'idle'}
    await player_manager.save_player_data(user_id, player_data)

    # --- Relatório ---
    summary_msg = [
        "🏁 <b>𝐂𝐚𝐜̧𝐚𝐝𝐚 𝐑𝐚́𝐩𝐢𝐝𝐚 𝐂𝐨𝐧𝐜𝐥𝐮𝐢́𝐝𝐚!</b> 🏁",
        f"📊 Resultado: <b>{wins} vitórias</b> | <b>{losses} derrotas</b>",
        "────────────────",
        f"💰 Ouro: +{total_gold} | ✨ XP: +{total_xp}",
    ]
    if items_log_list:
        summary_msg.append("\n🎒 <b>𝐋𝐨𝐨𝐭:</b>")
        summary_msg.extend(items_log_list)
    if level_up_msg: summary_msg.append(f"\n{level_up_msg}")
    
    final_caption = "\n".join(summary_msg)
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar", callback_data=f"open_region:{region_key}")]])

    # Limpeza e Mídia
    if message_id:
        try: await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception: pass 

    media_key = "autohunt_victory_media" if wins > 0 else "autohunt_defeat_media"
    file_data = file_id_manager.get_file_data(media_key)
    
    try:
        if file_data and file_data.get("id"):
            m_id = file_data["id"]
            m_type = (file_data.get("type") or "photo").lower()
            if m_type == "video":
                await context.bot.send_video(chat_id, video=m_id, caption=final_caption, parse_mode="HTML", reply_markup=reply_markup)
            else:
                await context.bot.send_photo(chat_id, photo=m_id, caption=final_caption, parse_mode="HTML", reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id, final_caption, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"[AutoHunt] Erro no envio final: {e}")
        await context.bot.send_message(chat_id, final_caption, parse_mode="HTML", reply_markup=reply_markup)

async def finish_auto_hunt_job(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    raw_uid = job_data.get('user_id')
    user_id = str(raw_uid) if raw_uid else None
    
    if user_id:
        await execute_hunt_completion(
            user_id=user_id,
            chat_id=job_data.get('chat_id'),
            hunt_count=job_data.get('hunt_count', 0),
            region_key=job_data.get('region_key'),
            context=context,
            message_id=job_data.get('message_id')
        )

# ==============================================================================
# 🚀 5. INICIADOR (START) - CORRIGIDO PARA ACEITAR LENDA/VIP
# ==============================================================================
async def start_auto_hunt(update: Update, context: ContextTypes.DEFAULT_TYPE, hunt_count: int, region_key: str) -> None:
    query = update.callback_query
    
    user_id = get_current_player_id(update, context)
    if not user_id:
        await query.answer("❌ Sessão expirada.", show_alert=True)
        return

    chat_id = query.message.chat.id
    player_data = await player_manager.get_player_data(user_id)
    
    # --- VALIDAÇÃO VIP CORRIGIDA ---
    # Verifica tanto o sistema Premium quanto o nome bruto do plano (Lenda/Admin/VIP)
    is_vip = False
    
    # 1. Tentativa Padrão
    try:
        if PremiumManager(player_data).is_premium():
            is_vip = True
    except: pass
    
    # 2. Tentativa Manual (String Bruta) - Garante que Lenda/Admin passe
    tier_name = str(player_data.get("premium_tier", "")).lower()
    if any(x in tier_name for x in ["lenda", "vip", "premium", "admin"]):
        is_vip = True

    if not is_vip:
        await query.answer("⭐️ Recurso exclusivo Premium!", show_alert=True)
        return
    # ---------------------------------

    total_cost = hunt_count
    if player_data.get('energy', 0) < total_cost:
        await query.answer(f"⚡ Energia insuficiente. Precisa de {total_cost}.", show_alert=True)
        return

    if not player_manager.spend_energy(player_data, total_cost):
        await query.answer("❌ Erro ao processar energia.", show_alert=True)
        return

    # Visual: Apagar menu anterior
    try: await query.message.delete()
    except Exception as e: logger.warning(f"[AutoHunt] Não foi possível apagar o menu: {e}")

    duration_seconds = SECONDS_PER_HUNT * hunt_count 
    finish_dt = (datetime.now(timezone.utc) + timedelta(seconds=duration_seconds))
    
    player_data['player_state'] = {
        'action': 'auto_hunting',
        'finish_time': finish_dt.isoformat(),
        'details': {'hunt_count': hunt_count, 'region_key': region_key}
    }
    await player_manager.save_player_data(user_id, player_data)

    region_info = game_data.REGIONS_DATA.get(region_key, {})
    region_name = region_info.get('display_name', region_key)
    duration_min = duration_seconds / 60.0
    
    msg = (
        f"⏱ <b>𝐂𝐚𝐜̧𝐚𝐝𝐚 𝐑𝐚́𝐩𝐢𝐝𝐚 𝐈𝐧𝐢𝐜𝐢𝐚𝐝𝐚!</b>\n"
        f"⚔️ Simulando <b>{hunt_count} combates</b> em <b>{region_name}</b>...\n\n"
        f"⚡ Custo: <b>{total_cost} energia</b>\n"
        f"⏳ Tempo: <b>{duration_min:.1f} minutos</b>.\n\n"
        f"<i>O relatório chegará automaticamente.</i>"
    )

    media_key = "autohunt_start_media"
    media_data = file_id_manager.get_file_data(media_key)
    sent_message = None

    try:
        if media_data and media_data.get("id"):
            file_id = media_data["id"]
            file_type = (media_data.get("type") or "photo").lower()
            if file_type == "video":
                sent_message = await context.bot.send_video(chat_id=chat_id, video=file_id, caption=msg, parse_mode="HTML")
            else:
                sent_message = await context.bot.send_photo(chat_id=chat_id, photo=file_id, caption=msg, parse_mode="HTML")
        else:
            sent_message = await context.bot.send_message(chat_id, msg, parse_mode="HTML")
    except Exception as e:
        logger.error(f"[AutoHunt] Erro ao enviar mídia: {e}")
        sent_message = await context.bot.send_message(chat_id, msg, parse_mode="HTML")

    job_data = {
        "user_id": user_id, "chat_id": chat_id,
        "message_id": sent_message.message_id if sent_message else None,
        "hunt_count": hunt_count, "region_key": region_key
    }
    
    context.job_queue.run_once(finish_auto_hunt_job, when=duration_seconds, data=job_data, name=f"autohunt_{user_id}")

# ==============================================================================
# 🧩 6. HANDLER DE BOTÃO (PARSER INTELIGENTE)
# ==============================================================================
async def _autohunt_button_parser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lê botões no formato: autohunt_start_10_floresta_sombria"""
    query = update.callback_query
    data = query.data
    
    try:
        content = data.replace("autohunt_start_", "")
        parts = content.split("_", 1)
        
        if len(parts) < 2:
            await query.answer("❌ Erro nos dados do botão.", show_alert=True)
            return

        hunt_count = int(parts[0])
        region_key = parts[1]
        await start_auto_hunt(update, context, hunt_count, region_key)
        
    except ValueError:
        await query.answer("❌ Erro de formato (número inválido).", show_alert=True)
    except Exception as e:
        logger.error(f"Erro no parser do autohunt: {e}")
        await query.answer("❌ Erro interno.", show_alert=True)

autohunt_start_handler = CallbackQueryHandler(_autohunt_button_parser, pattern=r"^autohunt_start_")