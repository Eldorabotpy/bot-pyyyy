# modules/auto_hunt_engine.py
# (VERSÃO FINAL VISUAL: Estilo Box Solicitado + Lógica Blindada)

import logging
import random
import asyncio
import html  # Importante para evitar erros de formatação
from datetime import datetime, timezone, timedelta

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

# Imports BSON
from bson import ObjectId

# Imports Core
from modules import player_manager, game_data
from modules import file_ids as file_id_manager
from modules.auth_utils import get_current_player_id

# Importa o módulo XP
from modules.game_data import xp as xp_module

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
# ⚖️ BALANCEAMENTO
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
    
    base_xp = int(m.get("xp_reward", 5))
    if base_xp > 50: base_xp = 15 

    final_xp = base_xp + (target_lvl * 2)
    
    if player_level > min_lvl + 15:
        final_xp = max(1, int(final_xp * 0.2)) 

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
        if player_hp <= 0: 
            return {"result": "loss"}
            
        turns += 1
        
    return {"result": "loss"} 

def _roll_loot(monster_data):
    drops = []
    for item in monster_data.get("loot_table", []):
        if random.uniform(0, 100) <= float(item.get("drop_chance", 0)):
            item_id = item.get("item_id") or item.get("base_id")
            qty = random.randint(item.get("min", 1), item.get("max", 1))
            drops.append((item_id, qty))
    return drops

# ==============================================================================
# ▶️ START (BACKEND)
# ==============================================================================
async def start_auto_hunt(update: Update, context: ContextTypes.DEFAULT_TYPE, hunt_count: int, region_key: str, message_id_override: int = None):
    logger.info(f"[AutoHunt] Iniciando request: {hunt_count}x em {region_key}")
    
    raw_uid = get_current_player_id(update, context)
    db_user_id = ensure_object_id(raw_uid)
    chat_id = update.effective_chat.id

    try:
        player_data = await player_manager.get_player_data(db_user_id)
        if not player_data: return

        # Débito de Energia
        total_cost = hunt_count 
        current_energy = int(player_data.get("energy", 0))
        
        if current_energy >= total_cost:
            player_data["energy"] = current_energy - total_cost
        else:
            logger.warning(f"[AutoHunt] Energia insuficiente no backend: {current_energy}/{total_cost}")
            return 
        
        # Timer
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

        # Configura Job
        job_data = {
            "user_id": str(db_user_id), 
            "chat_id": chat_id, 
            "hunt_count": hunt_count, 
            "region_key": region_key, 
            "message_id": message_id_override
        }
        
        job_name = f"autohunt_{str(db_user_id)}"
        
        # Limpa anteriores
        for job in context.job_queue.get_jobs_by_name(job_name): 
            job.schedule_removal()

        context.job_queue.run_once(finish_auto_hunt_job, when=duration_seconds, data=job_data, name=job_name)
        logger.info(f"[AutoHunt] Job agendado para {duration_seconds}s")
        
    except Exception as e:
        logger.error(f"[AutoHunt] Erro crítico no Start: {e}")

# ==============================================================================
# 🏁 FINISH JOB
# ==============================================================================
async def finish_auto_hunt_job(context: ContextTypes.DEFAULT_TYPE):
    logger.info("[AutoHunt] Job de finalização disparado.")
    try:
        job_data = context.job.data
        uid_str = job_data.get("user_id")
        if not uid_str: 
            logger.error("[AutoHunt] Job sem user_id!")
            return
        
        # Tenta apagar mensagem de loading
        if job_data.get("message_id"):
            try: 
                await context.bot.delete_message(chat_id=job_data["chat_id"], message_id=job_data["message_id"])
            except: pass

        await execute_hunt_completion(
            user_id=ensure_object_id(uid_str),
            chat_id=job_data["chat_id"],
            hunt_count=job_data["hunt_count"],
            region_key=job_data["region_key"],
            context=context
        )
    except Exception as e:
        logger.error(f"[AutoHunt] Erro fatal no Job Finish: {e}", exc_info=True)

# ==============================================================================
# 📊 COMPLETION & RELATÓRIO
# ==============================================================================
async def execute_hunt_completion(user_id, chat_id, hunt_count, region_key, context, message_id=None):
    logger.info(f"[AutoHunt] Calculando resultados para {user_id}...")
    
    # Se recebeu message_id (pelo Recovery), tenta apagar caso ainda exista
    if message_id:
        try: await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except: pass

    db_id = ensure_object_id(user_id)
    player_data = await player_manager.get_player_data(db_id)
    if not player_data: return

    player_stats = await player_manager.get_player_total_stats(player_data)
    old_level = int(player_data.get("level", 1))

    monster_list = game_data.MONSTERS_DATA.get(region_key) or [{"name": "Lobo", "xp_reward": 5, "gold_drop": 2, "id": "wolf"}]
    
    total_xp = 0
    total_gold = 0
    wins = 0
    losses = 0
    total_items = {}

    # --- SIMULAÇÃO ---
    for _ in range(hunt_count):
        tpl = random.choice(monster_list)
        if isinstance(tpl, str): 
            tpl = game_data.MONSTERS_DATA.get(tpl, {"name": "Mob", "xp_reward": 5})
        
        monster = _scale_monster_stats(tpl, old_level)
        res = await _simulate_single_battle(player_data, player_stats, monster)
        
        if res["result"] == "win":
            wins += 1
            total_xp += res["xp"]
            total_gold += res["gold"]
            for i_id, qty in res.get("items", []):
                total_items[i_id] = total_items.get(i_id, 0) + qty
        else:
            losses += 1

    # --- RECOMPENSAS ---
    player_manager.add_gold(player_data, total_gold)
    
    items_text = ""
    if total_items:
        items_text = "\n├─➤🎒 Loot:"
        for i_id, qty in total_items.items():
            player_manager.add_item_to_inventory(player_data, i_id, qty)
            raw_name = (game_data.ITEMS_DATA or {}).get(i_id, {}).get("display_name", i_id.replace('_', ' ').title())
            clean_name = html.escape(str(raw_name))
            items_text += f"\n├─➤ • {clean_name} x{qty}"

    xp_result = await xp_module.add_combat_xp(db_id, total_xp)
    
    levels_gained = xp_result.get("levels_gained", 0)
    new_level = xp_result.get("new_level", old_level)
    points_awarded = xp_result.get("points_awarded", 0)
    
    lvl_msg = ""
    if levels_gained > 0:
        lvl_msg = (
            f"\n├────────────────────────────"
            f"\n├─➤ 🎉 <b>LEVEL UP!</b> {old_level} ➔ {new_level}"
            f"\n├─➤ ✨ Pontos de Atributo: +{points_awarded}"
        )

    try:
        await player_manager.users_collection.update_one(
            {"_id": db_id}, 
            {"$set": {"player_state": {"action": "idle"}}}
        )
    except Exception as e:
        logger.error(f"[AutoHunt] Erro ao limpar estado: {e}")

    # --- MENSAGEM ---
    msg = (
        f"╭────────────────────────────➤\n"
        f"├─➤🏁 <b>Caçada Rápida Concluída!</b> 🏁\n"
        f"├─➤📊 Resultado: {wins} vitórias | {losses} derrotas\n"
        f"├────────────────────────────\n"
        f"├─➤💰 Ouro: +{total_gold} | ✨ XP: +{total_xp}"
        f"{items_text}"
        f"{lvl_msg}"
        f"\n╰───────────────────────────➤"
    )
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Voltar para Região", callback_data=f"open_region:{region_key}")]
    ])
    
    media_sent = False
    media_key = "autohunt_victory_media" if wins > 0 else "autohunt_defeat_media"
    file_data = file_id_manager.get_file_data(media_key)

    if file_data and file_data.get("id"):
        try:
            m_id = file_data["id"]
            m_type = (file_data.get("type") or "photo").lower()
            
            if m_type in ["video", "animation"]:
                await context.bot.send_video(chat_id, video=m_id, caption=msg, parse_mode="HTML", reply_markup=kb)
            else:
                await context.bot.send_photo(chat_id, photo=m_id, caption=msg, parse_mode="HTML", reply_markup=kb)
            media_sent = True
        except Exception as e:
            logger.error(f"[AutoHunt] Falha mídia: {e}")
            media_sent = False

    if not media_sent:
        try:
            await context.bot.send_message(chat_id, msg, parse_mode="HTML", reply_markup=kb)
        except Exception:
            # Fallback final texto puro
            clean_msg = msg.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
            await context.bot.send_message(chat_id, clean_msg, reply_markup=kb)
            