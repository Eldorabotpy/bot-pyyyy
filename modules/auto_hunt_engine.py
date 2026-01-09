# modules/auto_hunt_engine.py
# (VERSÃO CORRIGIDA: SELF-CONTAINED - Início e Fim no mesmo arquivo)

import random
import asyncio
import logging
import traceback 
from datetime import datetime, timezone, timedelta
from telegram.ext import ContextTypes
from collections import Counter
from telegram.error import BadRequest
from telegram import Update

# --- IMPORTS ESSENCIAIS ---
from modules import player_manager, game_data
from modules.player.premium import PremiumManager 
from modules.auth_utils import get_current_player_id
# Importamos o módulo de XP apenas na hora do uso para evitar ciclo, ou aqui se seguro
from modules.game_data import xp as xp_module 

logger = logging.getLogger(__name__)

# CONFIGURAÇÃO DE TEMPO
SECONDS_PER_HUNT = 30 

# ==============================================================================
# 1. SIMULAÇÃO DE COMBATE
# ==============================================================================
def _scale_monster_stats(mon: dict, player_level: int) -> dict:
    """Ajusta status do monstro (HP/Atk) baseado no nível do jogador."""
    m = mon.copy()
    if "max_hp" not in m and "hp" in m: m["max_hp"] = m["hp"]
    elif "max_hp" not in m: m["max_hp"] = 10 

    min_lvl = m.get("min_level", 1)
    max_lvl = m.get("max_level", player_level + 2)
    
    real_lvl = max(min_lvl, min(player_level + random.randint(-1, 1), max_lvl))
    if real_lvl < 1: real_lvl = 1
    m["level"] = real_lvl

    # Escala apenas status de batalha
    level_diff = max(0, real_lvl - min_lvl)
    multiplier = 1.0 + (level_diff * 0.05) 

    m["max_hp"] = int(m["max_hp"] * multiplier)
    m["current_hp"] = m["max_hp"]
    m["attack"] = int(m.get("attack", 5) * multiplier)
    m["defense"] = int(m.get("defense", 2) * multiplier)
    
    return m

def _simulate_single_fight(player_stats: dict, monster: dict) -> dict:
    """Simula uma única luta."""
    p_hp = player_stats.get("current_hp", 100)
    p_atk = player_stats.get("attack", 10)
    p_def = player_stats.get("defense", 5)
    
    m_hp = monster.get("max_hp", 50)
    m_atk = monster.get("attack", 8)
    m_def = monster.get("defense", 2)
    
    # XP Base Fixo
    base_xp = monster.get("xp", 10)
    xp_gain = int(base_xp) 

    dmg_taken_total = 0
    turns = 0
    max_turns = 20
    
    while p_hp > 0 and m_hp > 0 and turns < max_turns:
        turns += 1
        # Player bate
        dmg_p = max(1, p_atk - int(m_def * 0.5))
        if random.random() < 0.1: dmg_p = int(dmg_p * 1.5)
        m_hp -= dmg_p
        if m_hp <= 0: break
        
        # Monstro bate
        dmg_m = max(1, m_atk - int(p_def * 0.5))
        p_hp -= dmg_m
        dmg_taken_total += dmg_m

    win = (p_hp > 0)
    
    drops = []
    if win:
        for item in monster.get("loot_table", []):
            if random.random() < item.get("chance", 0.0):
                drops.append({
                    "base_id": item.get("base_id"),
                    "min": item.get("min", 1),
                    "max": item.get("max", 1)
                })
    else:
        xp_gain = 0
        
    return {
        "win": win,
        "xp": xp_gain,
        "drops": drops,
        "dmg_taken": dmg_taken_total
    }

# ==============================================================================
# 2. EXECUÇÃO DA FINALIZAÇÃO (Lógica Pesada)
# ==============================================================================
async def execute_hunt_completion(
    user_id: str, 
    chat_id: int, 
    hunt_count: int, 
    region_key: str, 
    context: ContextTypes.DEFAULT_TYPE, 
    message_id: int = None
):
    try:
        player_data = await player_manager.get_player_data(user_id)
        if not player_data: return

        # Recupera Stats e Sincroniza HP
        from modules.player.stats import get_player_total_stats
        total_stats = await get_player_total_stats(player_data)
        current_hp = player_data.get("current_hp", total_stats["max_hp"])
        total_stats["current_hp"] = current_hp

        # Monstros
        region_monsters = game_data.get_monsters_for_region(region_key)
        if not region_monsters:
            await context.bot.send_message(chat_id, "❌ Erro: Região sem monstros.")
            player_data["player_state"] = {"action": "idle"}
            await player_manager.save_player_data(user_id, player_data)
            return

        results = []
        player_level = player_data.get("level", 1)
        
        # Batalhas
        for _ in range(hunt_count):
            if total_stats["current_hp"] <= 0: break
            base_mon = random.choice(region_monsters)
            scaled_mon = _scale_monster_stats(base_mon, player_level)
            res = _simulate_single_fight(total_stats, scaled_mon)
            total_stats["current_hp"] -= res["dmg_taken"]
            results.append(res)

        # Consolidar Resultados
        wins = sum(1 for r in results if r["win"])
        losses = sum(1 for r in results if not r["win"])
        total_xp = sum(r["xp"] for r in results)
        
        loot_summary = Counter()
        for r in results:
            for d in r["drops"]:
                qty = random.randint(d["min"], d["max"])
                loot_summary[d["base_id"]] += qty

        # Salvar Recompensas
        xp_res = await xp_module.add_combat_xp(user_id, total_xp)
        
        for bid, qty in loot_summary.items():
            player_manager.add_item_to_inventory(player_data, bid, qty)
            
        final_hp = max(0, total_stats["current_hp"])
        player_data["current_hp"] = final_hp
        
        # ✅ LIBERA O JOGADOR (CRUCIAL)
        player_data["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(user_id, player_data)

        # Relatório
        reg_name = game_data.REGIONS_DATA.get(region_key, {}).get("display_name", region_key)
        msg_lines = [
            f"🏹 <b>Relatório:</b> {reg_name}",
            f"⚔️ {len(results)}/{hunt_count} Lutas | ✅ {wins} | ❌ {losses}",
            f"✨ <b>XP Total:</b> {total_xp}",
            "",
            "🎒 <b>Loot:</b>"
        ]
        
        if not loot_summary:
            msg_lines.append("Nada encontrado.")
        else:
            for bid, qty in loot_summary.items():
                iname = game_data.item_display_name(bid)
                msg_lines.append(f"▫️ {iname} x{qty}")

        if xp_res["levels_gained"] > 0:
            msg_lines.append(f"\n🎉 <b>LEVEL UP!</b> {xp_res['old_level']} ➔ {xp_res['new_level']}")

        # Limpa mensagem de "Iniciando..."
        if message_id:
            try: await context.bot.delete_message(chat_id, message_id)
            except: pass
            
        await context.bot.send_message(chat_id, "\n".join(msg_lines), parse_mode="HTML")

    except Exception as e:
        logger.error(f"Erro execute_hunt_completion: {e}")
        traceback.print_exc()
        # Fallback de emergência
        try:
            pdata = await player_manager.get_player_data(user_id)
            if pdata:
                pdata["player_state"] = {"action": "idle"}
                await player_manager.save_player_data(user_id, pdata)
        except: pass

# ==============================================================================
# 3. JOB WRAPPER (CORRIGIDO PARA ASYNC)
# ==============================================================================
async def finish_auto_hunt_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Função chamada pelo JobQueue quando o tempo acaba.
    Agora é ASYNC para garantir execução correta.
    """
    try:
        job_data = context.job.data
        if not job_data: return
        
        user_id = job_data.get("user_id")
        if not user_id: return

        # Chama a lógica e ESPERA terminar
        await execute_hunt_completion(
            user_id=user_id,
            chat_id=job_data.get("chat_id"),
            hunt_count=job_data.get("hunt_count"),
            region_key=job_data.get("region_key"),
            context=context,
            message_id=job_data.get("message_id")
        )
    except Exception as e:
        logger.error(f"Job finish error: {e}")

# ==============================================================================
# 4. INICIADOR (Start)
# ==============================================================================
async def start_auto_hunt(update: Update, context: ContextTypes.DEFAULT_TYPE, hunt_count: int, region_key: str) -> None:
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    chat_id = query.message.chat.id
    
    try:
        player_data = await player_manager.get_player_data(user_id)

        # 1. Verifica Premium
        pm = PremiumManager(player_data)
        if not pm.is_premium():
             await query.answer("⭐️ Recurso exclusivo Premium/VIP.", show_alert=True)
             return

        # 2. Verifica Energia (Custo 1)
        total_cost = hunt_count * 1
        current_energy = player_data.get("energy", 0)

        if current_energy < total_cost:
            await query.answer(f"⚡ Energia insuficiente ({current_energy}/{total_cost})", show_alert=True)
            return

        # Consome Energia
        player_data["energy"] = current_energy - total_cost

        # 3. Tempo Real (30s)
        duration_seconds = hunt_count * SECONDS_PER_HUNT
        finish_dt = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
        
        # 4. Salva Estado
        player_data["player_state"] = {
            "action": "auto_hunting",
            "finish_time": finish_dt.isoformat(),
            "details": {
                "hunt_count": hunt_count, 
                "region_key": region_key,
                "message_id": query.message.message_id 
            }
        }
        player_manager.set_last_chat_id(player_data, chat_id)
        await player_manager.save_player_data(user_id, player_data)

        # 5. Mensagem
        reg_name = game_data.REGIONS_DATA.get(region_key, {}).get("display_name", region_key)
        duration_min = duration_seconds / 60.0
        
        msg = (
            f"⏱ <b>𝐂𝐚𝐜̧𝐚𝐝𝐚 𝐈𝐧𝐢𝐜𝐢𝐚𝐝𝐚!</b>\n"
            f"Alvo: {hunt_count} monstros em <b>{reg_name}</b>\n"
            f"⚡ Custo: {total_cost} Energia\n"
            f"⏳ Retorno em: <b>{duration_min:.1f} minutos</b>"
        )
        sent_msg = await context.bot.send_message(chat_id, msg, parse_mode="HTML")
        
        # Atualiza Msg ID
        player_data["player_state"]["details"]["message_id"] = sent_msg.message_id
        await player_manager.save_player_data(user_id, player_data)

        # 6. Agenda o Job (USANDO A FUNÇÃO LOCAL)
        job_data = {
            "user_id": user_id,
            "chat_id": chat_id,
            "hunt_count": hunt_count,
            "region_key": region_key,
            "message_id": sent_msg.message_id
        }
        
        # ✅ CORREÇÃO: Usa finish_auto_hunt_job definida acima, sem import externo
        context.job_queue.run_once(
            finish_auto_hunt_job, 
            when=duration_seconds, 
            data=job_data, 
            name=f"autohunt_{user_id}"
        )

    except Exception as e:
        logger.error(f"Erro start_auto_hunt: {e}")
        await query.answer("❌ Erro ao iniciar.", show_alert=True)