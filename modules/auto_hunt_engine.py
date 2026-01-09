# modules/auto_hunt_engine.py
# (VERSÃO CORRIGIDA: XP BASE FIXO - Ignora Scaling de Nível)

import random
import asyncio
import logging
import re
import traceback 
from datetime import datetime, timezone, timedelta
from telegram.ext import ContextTypes
from collections import Counter
from telegram.error import Forbidden, BadRequest

from telegram import (
    InlineKeyboardMarkup, InlineKeyboardButton, Update,
    InputMediaPhoto, InputMediaVideo
)

# --- IMPORTS ESSENCIAIS ---
from modules import player_manager, game_data, file_ids as file_id_manager
from modules import mission_manager 
from modules.combat import criticals, rewards 
from modules.player.premium import PremiumManager 
from modules.auth_utils import get_current_player_id

logger = logging.getLogger(__name__)

SECONDS_PER_HUNT = 30 

# ==============================================================================
# 🛠️ FUNÇÕES AUXILIARES E SIMULAÇÃO
# ==============================================================================
def _scale_monster_stats(mon: dict, player_level: int) -> dict:
    """
    Ajusta os atributos de combate do monstro baseando-se no nível do jogador.
    (O XP NÃO é alterado aqui, apenas HP/Atk/Def para o combate ser justo).
    """
    m = mon.copy()
    if "max_hp" not in m and "hp" in m: m["max_hp"] = m["hp"]
    elif "max_hp" not in m: m["max_hp"] = 10 

    min_lvl = m.get("min_level", 1)
    max_lvl = m.get("max_level", player_level + 2)
    
    # Define o nível do monstro para o combate
    real_lvl = max(min_lvl, min(player_level + random.randint(-1, 1), max_lvl))
    if real_lvl < 1: real_lvl = 1
    m["level"] = real_lvl

    # Escala apenas status de batalha (HP, ATK, DEF)
    # Fórmula simples: +5% status por nível acima do base
    level_diff = max(0, real_lvl - min_lvl)
    multiplier = 1.0 + (level_diff * 0.05) 

    m["max_hp"] = int(m["max_hp"] * multiplier)
    m["current_hp"] = m["max_hp"]
    m["attack"] = int(m.get("attack", 5) * multiplier)
    m["defense"] = int(m.get("defense", 2) * multiplier)
    
    return m

def _simulate_single_fight(player_stats: dict, monster: dict) -> dict:
    """
    Simula uma luta turno a turno (rápida).
    Retorna: {'win': bool, 'xp': int, 'drops': list, 'log': str, 'dmg_taken': int}
    """
    p_hp = player_stats.get("current_hp", 100)
    p_atk = player_stats.get("attack", 10)
    p_def = player_stats.get("defense", 5)
    
    m_hp = monster.get("max_hp", 50)
    m_atk = monster.get("attack", 8)
    m_def = monster.get("defense", 2)
    
    # ✅ CORREÇÃO AQUI: XP FIXO BASE
    # Pega o XP definido no monstro. Se não tiver, usa 10.
    # Não aplica multiplicador de nível.
    base_xp = monster.get("xp", 10)
    xp_gain = int(base_xp) 

    # Variação mínima de RNG (opcional, mantive +- 5% para não ficar robótico demais)
    # Se quiser estritamente fixo, remova a linha abaixo.
    xp_gain = int(xp_gain * random.uniform(0.95, 1.05))

    dmg_taken_total = 0
    turns = 0
    max_turns = 20
    
    # Loop de Combate Simplificado
    while p_hp > 0 and m_hp > 0 and turns < max_turns:
        turns += 1
        
        # Player Ataca
        dmg_p = max(1, p_atk - int(m_def * 0.5))
        # Crítico simples (10% chance)
        if random.random() < 0.1: dmg_p = int(dmg_p * 1.5)
        m_hp -= dmg_p
        
        if m_hp <= 0: break
        
        # Monstro Ataca
        dmg_m = max(1, m_atk - int(p_def * 0.5))
        p_hp -= dmg_m
        dmg_taken_total += dmg_m

    win = (p_hp > 0)
    
    drops = []
    if win:
        # Processa Loot (Drop Chance)
        loot_table = monster.get("loot_table", [])
        for item in loot_table:
            chance = item.get("chance", 0.0) # 0.0 a 1.0
            if random.random() < chance:
                # Dropou!
                drops.append({
                    "base_id": item.get("base_id"),
                    "min": item.get("min", 1),
                    "max": item.get("max", 1)
                })
    else:
        xp_gain = 0 # Perdeu = 0 XP
        
    return {
        "win": win,
        "xp": xp_gain,
        "drops": drops,
        "dmg_taken": dmg_taken_total
    }

async def execute_hunt_completion(
    user_id: str, 
    chat_id: int, 
    hunt_count: int, 
    region_key: str, 
    context: ContextTypes.DEFAULT_TYPE, 
    message_id: int = None
):
    """
    Roda a simulação completa, calcula drops totais e salva.
    """
    try:
        player_data = await player_manager.get_player_data(user_id)
        if not player_data: return

        # Recupera Stats Totais
        from modules.player.stats import get_player_total_stats
        total_stats = await get_player_total_stats(player_data)
        
        # Garante HP atual sincronizado
        current_hp = player_data.get("current_hp", total_stats["max_hp"])
        total_stats["current_hp"] = current_hp

        # Carrega Monstros da Região
        region_monsters = game_data.get_monsters_for_region(region_key)
        if not region_monsters:
            await context.bot.send_message(chat_id, "❌ Nenhum monstro encontrado nesta região.")
            return

        results = []
        player_level = player_data.get("level", 1)
        
        # --- LOOP DE BATALHAS ---
        for _ in range(hunt_count):
            # Se morreu, para
            if total_stats["current_hp"] <= 0:
                break
                
            # Escolhe monstro e escala
            base_mon = random.choice(region_monsters)
            scaled_mon = _scale_monster_stats(base_mon, player_level)
            
            # Luta
            res = _simulate_single_fight(total_stats, scaled_mon)
            
            # Atualiza HP do player para a próxima luta
            total_stats["current_hp"] -= res["dmg_taken"]
            results.append(res)

        # --- PROCESSA RESULTADOS FINAIS ---
        wins = sum(1 for r in results if r["win"])
        losses = sum(1 for r in results if not r["win"])
        total_xp = sum(r["xp"] for r in results)
        
        # Agrega Drops
        loot_summary = Counter()
        for r in results:
            for d in r["drops"]:
                qty = random.randint(d["min"], d["max"])
                loot_summary[d["base_id"]] += qty

        # Salva no Player
        # 1. XP (O módulo xp.py aplica bônus Premium)
        from modules.game_data import xp as xp_module
        xp_res = await xp_module.add_combat_xp(user_id, total_xp)
        
        # 2. Loot
        for bid, qty in loot_summary.items():
            player_manager.add_item_to_inventory(player_data, bid, qty)
            
        # 3. HP Final
        final_hp = max(0, total_stats["current_hp"])
        player_data["current_hp"] = final_hp
        
        # 4. Limpa Estado (Watchdog Libera)
        player_data["player_state"] = {"action": "idle"}
        
        await player_manager.save_player_data(user_id, player_data)

        # --- RELATÓRIO ---
        msg_lines = [
            f"🏹 <b>Relatório de Caça:</b> {game_data.REGIONS_DATA.get(region_key, {}).get('display_name', region_key)}",
            f"⚔️ <b>Combates:</b> {len(results)}/{hunt_count}",
            f"✅ <b>Vitórias:</b> {wins} | ❌ <b>Derrotas:</b> {losses}",
            f"✨ <b>XP Total:</b> {total_xp} (Base)",
            "",
            "🎒 <b>Saque (Loot):</b>"
        ]
        
        if not loot_summary:
            msg_lines.append("Nothing... (Nada encontrado)")
        else:
            for bid, qty in loot_summary.items():
                iname = game_data.item_display_name(bid)
                msg_lines.append(f"▫️ {iname} x{qty}")

        if xp_res["levels_gained"] > 0:
            msg_lines.append(f"\n🎉 <b>LEVEL UP!</b> {xp_res['old_level']} ➔ {xp_res['new_level']}")

        # Envia relatório e deleta msg de "iniciando" se possível
        if message_id:
            try: await context.bot.delete_message(chat_id, message_id)
            except: pass
            
        await context.bot.send_message(chat_id, "\n".join(msg_lines), parse_mode="HTML")

    except Exception as e:
        logger.error(f"Erro critical no AutoHunt execution: {e}")
        traceback.print_exc()
        # Fallback de segurança para não travar conta
        try:
            pdata = await player_manager.get_player_data(user_id)
            if pdata:
                pdata["player_state"] = {"action": "idle"}
                await player_manager.save_player_data(user_id, pdata)
        except: pass

# ==============================================================================
# ▶️ INICIADOR (Chamado pelo Handler ou Watchdog)
# ==============================================================================
async def start_auto_hunt(update: Update, context: ContextTypes.DEFAULT_TYPE, hunt_count: int, region_key: str) -> None:
    """
    Inicia o processo. Verifica requisitos e salva estado no banco.
    """
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    chat_id = query.message.chat.id
    
    try:
        player_data = await player_manager.get_player_data(user_id)

        # 1. Verifica VIP/Lenda (Como já corrigimos no handler, aqui é dupla checagem de segurança)
        tier = str(player_data.get("premium_tier", "free")).lower()
        is_vip = any(x in tier for x in ["premium", "vip", "lenda", "admin"])
        if not is_vip:
            try: 
                if PremiumManager(player_data).is_premium(): is_vip = True
            except: pass

        if not is_vip:
            await query.answer("⭐️ Recurso Premium.", show_alert=True)
            return

        # 2. Verifica Energia
        # Lenda/Admin = Custo 0
        cost_per_hunt = 1
        if "lenda" in tier or "admin" in tier:
            cost_per_hunt = 0
        
        total_cost = hunt_count * cost_per_hunt
        current_energy = player_data.get("energy", 0)

        if current_energy < total_cost:
            await query.answer(f"⚡ Energia insuficiente ({current_energy}/{total_cost})", show_alert=True)
            return

        # Consome Energia
        if total_cost > 0:
            player_data["energy"] = current_energy - total_cost

        # 3. Salva Estado no Banco (Para o Watchdog pegar se reiniciar)
        duration_seconds = hunt_count * 1.5 # 1.5s por luta simulada (exemplo)
        # O job real vai rodar nesse tempo
        finish_dt = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
        
        player_data["player_state"] = {
            "action": "auto_hunting",
            "finish_time": finish_dt.isoformat(),
            "details": {
                "hunt_count": hunt_count, 
                "region_key": region_key,
                # Salva ID da mensagem se quiser deletar depois
                "message_id": query.message.message_id 
            }
        }
        player_manager.set_last_chat_id(player_data, chat_id)
        await player_manager.save_player_data(user_id, player_data)

        # 4. Mensagem Inicial
        reg_name = game_data.REGIONS_DATA.get(region_key, {}).get("display_name", region_key)
        duration_min = duration_seconds / 60.0
        
        msg = (
            f"⏱ <b>𝐂𝐚𝐜̧𝐚𝐝𝐚 𝐑𝐚́𝐩𝐢𝐝𝐚 𝐈𝐧𝐢𝐜𝐢𝐚𝐝𝐚!</b>\n"
            f"Simulando {hunt_count} combates em <b>{reg_name}</b>...\n\n"
            f"⚡ 𝑪𝒖𝒔𝒕𝒐: {total_cost} energia\n"
            f"⏳ 𝑻𝒆𝒎𝒑𝒐: <b>{duration_min:.1f} minutos</b>.\n\n"
            f"𝑨𝒈𝒖𝒂𝒓𝒅𝒆 𝒐 𝒓𝒆𝒍𝒂𝒕𝒐́𝒓𝒊𝒐 𝒇𝒊𝒏𝒂𝒍."
        )
        
        sent_msg = await context.bot.send_message(chat_id, msg, parse_mode="HTML")
        
        # Atualiza ID da mensagem no estado (opcional, para delete preciso)
        player_data["player_state"]["details"]["message_id"] = sent_msg.message_id
        await player_manager.save_player_data(user_id, player_data)

        # 5. Agenda o Job
        job_data = {
            "user_id": user_id,
            "chat_id": chat_id,
            "hunt_count": hunt_count,
            "region_key": region_key,
            "message_id": sent_msg.message_id
        }
        
        # Importa job localmente para evitar ciclo se necessário
        from handlers.autohunt_handler import finish_auto_hunt_job as handler_finish
        # OU usa um wrapper local
        
        # Agenda
        context.job_queue.run_once(
            finish_auto_hunt_job, 
            when=duration_seconds, 
            data=job_data, 
            name=f"autohunt_{user_id}"
        )

    except Exception as e:
        logger.error(f"Erro start_auto_hunt: {e}")
        await query.answer("❌ Erro ao iniciar.", show_alert=True)

# Wrapper para o JobQueue
def finish_auto_hunt_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        job_data = context.job.data
        if not job_data: return
        
        user_id = job_data.get("user_id")
        if not user_id: return

        # Transforma em tarefa async
        asyncio.create_task(execute_hunt_completion(
            user_id=user_id,
            chat_id=job_data.get("chat_id"),
            hunt_count=job_data.get("hunt_count"),
            region_key=job_data.get("region_key"),
            context=context,
            message_id=job_data.get("message_id")
        ))
    except Exception as e:
        logger.error(f"Job finish error: {e}")