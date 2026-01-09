# modules/auto_hunt_engine.py
# (CORREÇÃO FINAL: Visual Restaurado + Botão Voltar Menu + XP Seguro)

import logging
import random
import asyncio
from datetime import datetime, timezone, timedelta
from collections import Counter

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

# Imports BSON
from bson import ObjectId

# Imports Core
from modules import player_manager, game_data
from modules import file_ids as file_id_manager # Necessário para o vídeo final
from modules.auth_utils import get_current_player_id

logger = logging.getLogger(__name__)

SECONDS_PER_HUNT = 30 

# ==============================================================================
# 🛠️ HELPER
# ==============================================================================
def ensure_object_id(uid):
    if isinstance(uid, ObjectId): return uid
    if isinstance(uid, str) and ObjectId.is_valid(uid): return ObjectId(uid)
    return uid

# ==============================================================================
# ⚖️ BALANCEAMENTO (XP)
# ==============================================================================
def _scale_monster_stats(mon: dict, player_level: int) -> dict:
    m = mon.copy()
    if "max_hp" not in m and "hp" in m: m["max_hp"] = m["hp"]
    elif "max_hp" not in m: m["max_hp"] = 10 

    min_lvl = m.get("min_level", 1)
    target_lvl = max(min_lvl, min(player_level, min_lvl + 10)) 
    m["level"] = target_lvl

    raw_name = m.get("name", "Inimigo").replace("Lv.", "").strip()
    m["name"] = f"Lv.{target_lvl} {raw_name}"

    scaling_bonus = 1 + (target_lvl * 0.05) 
    m["max_hp"] = int(m.get("max_hp", 10) * scaling_bonus)
    m["hp"] = m["max_hp"]
    m["attack"] = int(m.get("attack", 2) * scaling_bonus)
    
    # --- XP Fixo e Baixo ---
    base_xp = int(m.get("xp_reward", 5))
    if base_xp > 50: base_xp = 15 # Trava de segurança

    final_xp = base_xp + (target_lvl * 2)
    
    if player_level > min_lvl + 15:
        final_xp = max(1, int(final_xp * 0.2)) # Penalidade de nível alto

    m["xp_reward"] = final_xp
    m["gold_drop"] = int(m.get("gold_drop", 1) * scaling_bonus)
    
    return m

# ==============================================================================
# ⚔️ SIMULAÇÃO
# ==============================================================================
async def _simulate_single_battle(player_data, player_stats, monster_data):
    if not monster_data: return {"result": "loss"}

    player_hp = player_stats.get('max_hp', 100)
    monster_hp = monster_data.get('max_hp', 10)
    player_atk = player_stats.get('attack', 10)
    monster_atk = monster_data.get('attack', 2)

    turns = 0
    while turns < 20:
        monster_hp -= player_atk
        if monster_hp <= 0:
            return {
                "result": "win", 
                "xp": monster_data.get("xp_reward", 5), 
                "gold": monster_data.get("gold_drop", 1), 
                "items": _roll_loot(monster_data),
                "monster_id": monster_data.get("id")
            }
        player_hp -= monster_atk
        if player_hp <= 0: return {"result": "loss"}
        turns += 1
        
    return {"result": "loss"} 

def _roll_loot(monster_data):
    drops = []
    for item in monster_data.get("loot_table", []):
        if random.uniform(0, 100) <= float(item.get("drop_chance", 0)):
            drops.append((item.get("item_id") or item.get("base_id"), random.randint(item.get("min", 1), item.get("max", 1))))
    return drops

# ==============================================================================
# ▶️ START (Lógica Backend)
# ==============================================================================
async def start_auto_hunt(update: Update, context: ContextTypes.DEFAULT_TYPE, hunt_count: int, region_key: str, message_id_override: int = None):
    raw_uid = get_current_player_id(update, context)
    db_user_id = ensure_object_id(raw_uid)
    chat_id = update.effective_chat.id

    try:
        player_data = await player_manager.get_player_data(db_user_id)
        if not player_data: return

        # Consome Energia
        total_cost = hunt_count 
        if player_data.get("energy", 0) >= total_cost:
            player_data["energy"] -= total_cost
        
        # Configura Timer
        duration_seconds = hunt_count * SECONDS_PER_HUNT
        finish_dt = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
        
        # Salva Estado
        player_data["player_state"] = {
            "action": "auto_hunting",
            "finish_time": finish_dt.isoformat(),
            "details": {
                "hunt_count": hunt_count, 
                "region_key": region_key, 
                "message_id": message_id_override 
            }
        }
        player_manager.set_last_chat_id(player_data, chat_id)
        await player_manager.save_player_data(db_user_id, player_data)

        # Agenda Job
        job_data = {
            "user_id": str(db_user_id), 
            "chat_id": chat_id, 
            "hunt_count": hunt_count, 
            "region_key": region_key, 
            "message_id": message_id_override
        }
        
        job_name = f"autohunt_{str(db_user_id)}"
        
        for job in context.job_queue.get_jobs_by_name(job_name): 
            job.schedule_removal()

        context.job_queue.run_once(finish_auto_hunt_job, when=duration_seconds, data=job_data, name=job_name)
        
    except Exception as e:
        logger.error(f"Erro start engine: {e}")

# ==============================================================================
# 🏁 FINISH JOB
# ==============================================================================
async def finish_auto_hunt_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        job_data = context.job.data
        uid_str = job_data.get("user_id")
        if not uid_str: return
        
        # Apaga msg de "Viajando"
        if job_data.get("message_id"):
            try: await context.bot.delete_message(chat_id=job_data["chat_id"], message_id=job_data["message_id"])
            except: pass

        await execute_hunt_completion(
            user_id=ensure_object_id(uid_str),
            chat_id=job_data["chat_id"],
            hunt_count=job_data["hunt_count"],
            region_key=job_data["region_key"],
            context=context
        )
    except Exception as e:
        logger.error(f"Erro job finish: {e}")

# ==============================================================================
# 📊 COMPLETION
# ==============================================================================
async def execute_hunt_completion(user_id, chat_id, hunt_count, region_key, context):
    db_id = ensure_object_id(user_id)
    player_data = await player_manager.get_player_data(db_id)
    if not player_data: return

    player_stats = await player_manager.get_player_total_stats(player_data)
    player_level = int(player_data.get("level", 1))

    monster_list = game_data.MONSTERS_DATA.get(region_key) or [{"name": "Lobo", "xp_reward": 5, "gold_drop": 2, "id": "wolf"}]
    
    total_xp = 0
    total_gold = 0
    wins = 0
    losses = 0
    total_items = {}

    for _ in range(hunt_count):
        tpl = random.choice(monster_list)
        if isinstance(tpl, str): tpl = game_data.MONSTERS_DATA.get(tpl, {"name": "Mob", "xp_reward": 5})
        
        monster = _scale_monster_stats(tpl, player_level)
        res = await _simulate_single_battle(player_data, player_stats, monster)
        
        if res["result"] == "win":
            wins += 1
            total_xp += res["xp"]
            total_gold += res["gold"]
            for i_id, qty in res.get("items", []):
                total_items[i_id] = total_items.get(i_id, 0) + qty
        else:
            losses += 1

    # Salva
    player_manager.add_gold(player_data, total_gold)
    
    items_text = ""
    if total_items:
        items_text = "\n🎒 <b>Loot:</b>"
        for i_id, qty in total_items.items():
            player_manager.add_item_to_inventory(player_data, i_id, qty)
            items_text += f"\n• {i_id.replace('_', ' ').title()} x{qty}"

    # XP
    player_data["exp"] = player_data.get("exp", 0) + total_xp
    
    next_xp = player_level * 100 
    lvl_msg = ""
    if player_data["exp"] >= next_xp:
        player_data["level"] = player_level + 1
        player_data["exp"] -= next_xp
        player_data["current_hp"] = player_data.get("max_hp", 100)
        lvl_msg = f"\n🎉 <b>LEVEL UP!</b> {player_level} ➔ {player_level + 1}"

    player_data['player_state'] = {'action': 'idle'}
    await player_manager.save_player_data(db_id, player_data)

    # Relatório Texto
    msg = (
        f"🏁 <b>Caçada Rápida Concluída!</b> 🏁\n"
        f"📊 Resultado: {wins} vitórias | {losses} derrotas\n"
        f"────────────────\n"
        f"💰 Ouro: +{total_gold} | ✨ XP: +{total_xp}"
        f"{items_text}"
        f"{lvl_msg}"
    )
    
    # --- CORREÇÃO DO BOTÃO E MÍDIA ---
    
    # 1. Botão: Usa open_region_ para abrir o menu, não hunt_ que abre luta
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar", callback_data=f"open_region_{region_key}")]])
    
    # 2. Mídia: Restaura o envio de Video/Foto
    media_key = "autohunt_victory_media" if wins > 0 else "autohunt_defeat_media"
    file_data = file_id_manager.get_file_data(media_key)
    
    try:
        if file_data and file_data.get("id"):
            m_id = file_data["id"]
            m_type = (file_data.get("type") or "photo").lower()
            
            if m_type in ["video", "animation"]:
                await context.bot.send_video(chat_id, video=m_id, caption=msg, parse_mode="HTML", reply_markup=kb)
            else:
                await context.bot.send_photo(chat_id, photo=m_id, caption=msg, parse_mode="HTML", reply_markup=kb)
        else:
            # Fallback se não tiver mídia
            await context.bot.send_message(chat_id, msg, parse_mode="HTML", reply_markup=kb)
            
    except Exception as e:
        logger.error(f"Erro visual final: {e}")
        # Garante que envie ao menos o texto se a mídia falhar
        await context.bot.send_message(chat_id, msg, parse_mode="HTML", reply_markup=kb)