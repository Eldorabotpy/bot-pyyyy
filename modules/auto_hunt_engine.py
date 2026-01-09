# modules/auto_hunt_engine.py
# (BACKEND: Lógica, Banco de Dados, Timer e Cálculo de XP Seguro)

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
from modules import mission_manager 
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
# ⚖️ BALANCEAMENTO DE MONSTROS (XP BAIXO E JUSTO)
# ==============================================================================
def _scale_monster_stats(mon: dict, player_level: int) -> dict:
    m = mon.copy()
    if "max_hp" not in m and "hp" in m: m["max_hp"] = m["hp"]
    elif "max_hp" not in m: m["max_hp"] = 10 

    min_lvl = m.get("min_level", 1)
    # Limita nível do monstro para não explodir stats
    target_lvl = max(min_lvl, min(player_level, min_lvl + 10)) 
    m["level"] = target_lvl

    raw_name = m.get("name", "Inimigo").replace("Lv.", "").strip()
    m["name"] = f"Lv.{target_lvl} {raw_name}"

    scaling_bonus = 1 + (target_lvl * 0.05) 
    m["max_hp"] = int(m.get("max_hp", 10) * scaling_bonus)
    m["hp"] = m["max_hp"]
    m["attack"] = int(m.get("attack", 2) * scaling_bonus)
    
    # --- TRAVA DE XP ---
    # Ignora valores absurdos do banco
    base_xp = int(m.get("xp_reward", 5))
    if base_xp > 50: base_xp = 15 # Força valor baixo se base estiver errada

    # Cálculo linear simples: Base + (Nível * 2)
    # Ex: Lobo (5) + (Lv 10 * 2) = 25 XP
    final_xp = base_xp + (target_lvl * 2)
    
    # Penalidade se o player for muito forte (Farm de low level)
    if player_level > min_lvl + 15:
        final_xp = max(1, int(final_xp * 0.2)) # Ganha só 20%

    m["xp_reward"] = final_xp
    m["gold_drop"] = int(m.get("gold_drop", 1) * scaling_bonus)
    
    return m

# ==============================================================================
# ⚔️ SIMULAÇÃO DE BATALHA
# ==============================================================================
async def _simulate_single_battle(player_data, player_stats, monster_data):
    if not monster_data: return {"result": "loss"}

    # Simulação simplificada para performance
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
        
    return {"result": "loss"} # Timeout

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
    """
    Inicia a lógica. NÃO envia mensagem visual (o handler já enviou).
    """
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
        
        # Salva Estado com o ID da mensagem para deletar depois
        player_data["player_state"] = {
            "action": "auto_hunting",
            "finish_time": finish_dt.isoformat(),
            "details": {
                "hunt_count": hunt_count, 
                "region_key": region_key, 
                "message_id": message_id_override # Salva o ID que veio do handler
            }
        }
        player_manager.set_last_chat_id(player_data, chat_id)
        await player_manager.save_player_data(db_user_id, player_data)

        # Agenda Job
        # Convertemos ID para string para passar no job queue sem erro de Pickle
        job_data = {
            "user_id": str(db_user_id), 
            "chat_id": chat_id, 
            "hunt_count": hunt_count, 
            "region_key": region_key, 
            "message_id": message_id_override
        }
        
        job_name = f"autohunt_{str(db_user_id)}"
        
        # Limpa jobs antigos
        for job in context.job_queue.get_jobs_by_name(job_name): 
            job.schedule_removal()

        context.job_queue.run_once(finish_auto_hunt_job, when=duration_seconds, data=job_data, name=job_name)
        
    except Exception as e:
        logger.error(f"Erro start engine: {e}")

# ==============================================================================
# 🏁 FINISH JOB (Executado pelo Timer)
# ==============================================================================
async def finish_auto_hunt_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        job_data = context.job.data
        uid_str = job_data.get("user_id")
        if not uid_str: return
        
        # 1. Tenta apagar a mensagem de "Viajando"
        if job_data.get("message_id"):
            try: await context.bot.delete_message(chat_id=job_data["chat_id"], message_id=job_data["message_id"])
            except: pass

        # 2. Executa conclusão
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
# 📊 COMPLETION & RELATÓRIO
# ==============================================================================
async def execute_hunt_completion(user_id, chat_id, hunt_count, region_key, context):
    db_id = ensure_object_id(user_id)
    player_data = await player_manager.get_player_data(db_id)
    if not player_data: return

    player_stats = await player_manager.get_player_total_stats(player_data)
    player_level = int(player_data.get("level", 1))

    # Busca monstros
    monster_list = game_data.MONSTERS_DATA.get(region_key) or [{"name": "Lobo", "xp_reward": 5, "gold_drop": 2, "id": "wolf"}]
    
    total_xp = 0
    total_gold = 0
    wins = 0
    losses = 0
    total_items = {}

    # Roda as lutas
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

    # --- SALVA RECOMPENSAS (BYPASS XP MODULE) ---
    player_manager.add_gold(player_data, total_gold)
    
    # Itens
    items_text = ""
    if total_items:
        items_text = "\n🎒 <b>Loot:</b>"
        for i_id, qty in total_items.items():
            player_manager.add_item_to_inventory(player_data, i_id, qty)
            items_text += f"\n• {i_id.replace('_', ' ').title()} x{qty}"

    # XP DIRETO (Sem multiplicador externo)
    player_data["exp"] = player_data.get("exp", 0) + total_xp
    
    # Check Level Up Simples
    next_xp = player_level * 100 # Exemplo simples
    lvl_msg = ""
    if player_data["exp"] >= next_xp:
        player_data["level"] = player_level + 1
        player_data["exp"] -= next_xp
        player_data["current_hp"] = player_data.get("max_hp", 100)
        lvl_msg = f"\n🎉 <b>LEVEL UP!</b> {player_level} ➔ {player_level + 1}"

    # Limpa estado
    player_data['player_state'] = {'action': 'idle'}
    await player_manager.save_player_data(db_id, player_data)

    # Relatório Final
    msg = (
        f"🏁 <b>Caçada Rápida Concluída!</b> 🏁\n"
        f"📊 Resultado: {wins} vitórias | {losses} derrotas\n"
        f"────────────────\n"
        f"💰 Ouro: +{total_gold} | ✨ XP: +{total_xp}"
        f"{items_text}"
        f"{lvl_msg}"
    )
    
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar", callback_data=f"open_region_{region_key}")]])
    await context.bot.send_message(chat_id, msg, parse_mode="HTML", reply_markup=kb)