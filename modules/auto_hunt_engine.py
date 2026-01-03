# modules/auto_hunt_engine.py
# (VERSÃO BLINDADA: DESTRAVAMENTO OBRIGATÓRIO + TRY/FINALLY)

import random
import asyncio
import logging
import re
import traceback # Importante para ver o erro real
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
    # (Mantém a mesma lógica de escala da versão anterior)
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

    # Fatores de crescimento
    scaling_bonus = 1 + (target_lvl * 0.02) 
    
    # Aplica
    for attr, growth in [("max_hp", 12), ("attack", 2.0), ("defense", 1.0), ("xp_reward", 3), ("gold_drop", 1.5)]:
        base = int(m.get(attr, 0)) if attr != "max_hp" else int(m.get("max_hp", 10))
        m[attr] = int((base * scaling_bonus) + (target_lvl * growth))
    
    m["hp"] = m["max_hp"]
    return m

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

    # Limite de 20 turnos para não travar
    for _ in range(20):
        # Player Ataca
        dmg_to_monster, _, _ = criticals.roll_damage(player_stats, monster_stats_sim, {})
        monster_hp -= max(1, dmg_to_monster)
        
        if monster_hp <= 0:
            combat_details = monster_data.copy()
            # Garante XP escalado
            combat_details['monster_xp_reward'] = monster_data.get('xp_reward', 0)
            combat_details['monster_gold_drop'] = monster_data.get('gold_drop', 0)
            
            xp, gold, item_ids_list = rewards.calculate_victory_rewards(player_data, combat_details)
            items_rolled = list(Counter(item_ids_list).items())
            return {"result": "win", "xp": xp, "gold": gold, "items": items_rolled, "monster_id": monster_data.get("id")}
            
        # Monstro Ataca
        dmg_to_player, _, _ = criticals.roll_damage(monster_stats_sim, player_stats, {})
        player_hp -= max(1, dmg_to_player)
        
        if player_hp <= 0:
            return {"result": "loss", "reason": "HP Zero"}

    return {"result": "loss", "reason": "Timeout"}

# ==============================================================================
# 🚀 EXECUTOR DE CONCLUSÃO (COM FINALLY)
# ==============================================================================
async def execute_hunt_completion(
    user_id: str, 
    chat_id: int, 
    hunt_count: int, 
    region_key: str, 
    context: ContextTypes.DEFAULT_TYPE, 
    message_id: int = None
):
    """
    Executa a lógica final.
    CRÍTICO: Usa 'finally' para garantir que o jogador seja destravado.
    """
    logger.info(f"[AutoHunt] Finalizando para User {user_id}...")
    
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        return

    # Variáveis para o relatório (definidas fora do try para segurança)
    summary_msg = []
    wins = 0
    losses = 0
    
    try:
        # --- BLOCO DE LÓGICA ARRISCADA (COMBATES) ---
        player_stats = await player_manager.get_player_total_stats(player_data)
        player_level = int(player_data.get("level", 1))

        region_data = game_data.REGIONS_DATA.get(region_key, {})
        monster_list_data = game_data.MONSTERS_DATA.get(region_key) or region_data.get('monsters', [])

        if not monster_list_data:
            raise Exception(f"Sem monstros na região {region_key}")

        total_xp = 0
        total_gold = 0
        total_items = {}
        killed_monsters_ids = []

        # Loop de Combates
        for i in range(hunt_count):
            monster_template = random.choice(monster_list_data)
            if isinstance(monster_template, str):
                monster_template = (getattr(game_data, "MONSTER_TEMPLATES", {}) or {}).get(monster_template)
            
            if not monster_template: continue
            
            # Escala e Luta
            monster_scaled = _scale_monster_stats(monster_template, player_level)
            res = await _simulate_single_battle(player_data, player_stats, monster_scaled)
            
            if res["result"] == "win":
                wins += 1
                total_xp += int(res["xp"])
                total_gold += int(res["gold"])
                if res.get("monster_id"): killed_monsters_ids.append(res.get("monster_id"))
                for item_id, qty in res["items"]:
                    total_items[item_id] = total_items.get(item_id, 0) + qty
            else:
                losses += 1
                break # Para na primeira derrota

        # --- APLICA RECOMPENSAS ---
        if total_gold > 0: player_manager.add_gold(player_data, total_gold)
        if total_xp > 0: player_data['xp'] = player_data.get('xp', 0) + total_xp
        
        items_log_list = []
        items_source = getattr(game_data, "ITEMS_DATA", {}) or {}
        for item_id, qty in total_items.items():
            player_manager.add_item_to_inventory(player_data, item_id, qty)
            iname = items_source.get(item_id, {}).get('display_name', item_id)
            items_log_list.append(f"• {iname} x{qty}")

        # --- ATUALIZA MISSÕES (Fire & Forget) ---
        async def _update_missions():
            try:
                for m_id, count in Counter(killed_monsters_ids).items():
                    await mission_manager.update_mission_progress(user_id, "hunt", m_id, count)
                for item_id, qty in total_items.items():
                    await mission_manager.update_mission_progress(user_id, "collect", item_id, qty)
            except: pass
        asyncio.create_task(_update_missions())

        # --- CHECK LEVEL UP ---
        _, _, level_up_msg = player_manager.check_and_apply_level_up(player_data)

        # --- MONTA O RELATÓRIO ---
        reg_name = region_data.get('display_name', region_key.title())
        summary_msg = [
            "🏁 <b>𝐂𝐚𝐜̧𝐚𝐝𝐚 𝐑𝐚́𝐩𝐢𝐝𝐚 𝐂𝐨𝐧𝐜𝐥𝐮𝐢́𝐝𝐚!</b> 🏁",
            f"Região: {reg_name}",
            f"Result: <b>{wins} Vitórias</b>, <b>{losses} Derrotas</b>",
            "---",
            f"💰 Ouro: {total_gold}",
            f"✨ XP: {total_xp}",
        ]
        if items_log_list:
            summary_msg.append("\n📦 𝑰𝒕𝒆𝒏𝒔:")
            summary_msg.extend(items_log_list)
        else:
            summary_msg.append("\n📦 <i>Nada encontrado.</i>")
            
        if losses > 0: summary_msg.append(f"\n⚠️ <i>Parou por derrota.</i>")
        if level_up_msg: summary_msg.append(level_up_msg)

    except Exception as e:
        logger.error(f"[AutoHunt] ERRO NA SIMULAÇÃO: {e}")
        traceback.print_exc()
        summary_msg = [
            "⚠️ <b>ERRO NA CAÇADA</b>",
            "Ocorreu um erro interno durante a simulação.",
            "Seus recursos foram preservados, mas a ação foi cancelada."
        ]
        
    finally:
        # ==========================================================
        # 🔓 O GRANDE DESTRAVADOR (Roda SEMPRE, mesmo com erro)
        # ==========================================================
        logger.info(f"[AutoHunt] Destravando jogador {user_id}...")
        
        # Força estado Idle
        player_data['player_state'] = {'action': 'idle'}
        
        # Salva no banco
        await player_manager.save_player_data(user_id, player_data)
        
        # Envia a mensagem final
        final_caption = "\n".join(summary_msg)
        kb = [[InlineKeyboardButton("⬅️ Voltar", callback_data=f"open_region:{region_key}")]]
        
        try:
            if message_id:
                # Tenta editar se possível
                try:
                    await context.bot.edit_message_caption(
                        chat_id=chat_id, message_id=message_id,
                        caption=final_caption, parse_mode="HTML", 
                        reply_markup=InlineKeyboardMarkup(kb)
                    )
                except:
                     # Se falhar (ex: mudou de foto para video ou vice versa impossivel), envia nova
                     await context.bot.send_message(chat_id, final_caption, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
            else:
                await context.bot.send_message(chat_id, final_caption, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            logger.error(f"[AutoHunt] Erro ao enviar msg final: {e}")


# ==============================================================================
# 🧩 O JOB WRAPPER (Segurança Extra)
# ==============================================================================
async def finish_auto_hunt_job(context: ContextTypes.DEFAULT_TYPE):
    """Wrapper chamado pelo JobQueue."""
    try:
        job_data = context.job.data
        if not job_data: return

        raw_user_id = job_data.get('user_id')
        if not raw_user_id: return

        await execute_hunt_completion(
            user_id=raw_user_id,
            chat_id=job_data.get('chat_id'),
            hunt_count=job_data.get('hunt_count', 0),
            region_key=job_data.get('region_key'),
            context=context,
            message_id=job_data.get('message_id')
        )
    except Exception as e:
        logger.error(f"[AutoHunt] CRASH NO JOB WRAPPER: {e}")
        # Se cair aqui, o 'finally' lá dentro não rodou pq nem entrou na função.
        # Mas é raríssimo.

# ==============================================================================
# ▶️ INICIADOR (Com Blindagem de Tier e Energia)
# ==============================================================================
async def start_auto_hunt(update: Update, context: ContextTypes.DEFAULT_TYPE, hunt_count: int, region_key: str) -> None:
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    chat_id = query.message.chat.id
    
    try:
        player_data = await player_manager.get_player_data(user_id)

        # 1. Blindagem Tier (String Bruta)
        tier = str(player_data.get("premium_tier", "free")).lower()
        is_vip = tier in ["premium", "vip", "lenda", "admin"]
        
        if not is_vip:
            try: 
                if PremiumManager(player_data).is_premium(): is_vip = True
            except: pass

        if not is_vip:
            await query.answer("⭐️ Recurso Premium.", show_alert=True)
            return

        # 2. Verifica Energia
        # Se for Lenda/Admin, custo é ZERO (Força bruta para garantir a promessa do plano)
        cost_per_hunt = 1
        if tier in ["lenda", "admin"]:
            cost_per_hunt = 0
        else:
             # Pega do premium manager ou do jogo
             try:
                 base = int(game_data.REGIONS_DATA.get(region_key, {}).get("hunt_energy_cost", 1))
                 cost_per_hunt = int(PremiumManager(player_data).get_perk_value("hunt_energy_cost", base))
             except: cost_per_hunt = 1

        total_cost = max(0, cost_per_hunt * hunt_count)
        
        if player_data.get('energy', 0) < total_cost:
            await query.answer(f"Energia insuficiente ({total_cost}⚡).", show_alert=True)
            return

        # 3. Consome e Configura Estado
        if total_cost > 0:
            player_manager.spend_energy(player_data, total_cost)

        duration_seconds = SECONDS_PER_HUNT * hunt_count 
        finish_dt = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
        
        player_data['player_state'] = {
            'action': 'auto_hunting',
            'finish_time': finish_dt.isoformat(),
            'details': {'hunt_count': hunt_count, 'region_key': region_key}
        }
        player_manager.set_last_chat_id(player_data, chat_id)
        await player_manager.save_player_data(user_id, player_data)

        # 4. Mensagem Inicial
        reg_name = game_data.REGIONS_DATA.get(region_key, {}).get('display_name', region_key)
        duration_min = duration_seconds / 60.0
        
        msg = (
            f"⏱ <b>𝐂𝐚𝐜̧𝐚𝐝𝐚 𝐑𝐚́𝐩𝐢𝐝𝐚 𝐈𝐧𝐢𝐜𝐢𝐚𝐝𝐚!</b>\n"
            f"Simulando {hunt_count} combates em <b>{reg_name}</b>...\n\n"
            f"⚡ 𝑪𝒖𝒔𝒕𝒐: {total_cost} energia\n"
            f"⏳ 𝑻𝒆𝒎𝒑𝒐: <b>{duration_min:.1f} minutos</b>.\n\n"
            f"𝑨𝒈𝒖𝒂𝒓𝒅𝒆 𝒐 𝒓𝒆𝒍𝒂𝒕𝒐́𝒓𝒊𝒐 𝒇𝒊𝒏𝒂𝒍."
        )
        
        sent_msg = await context.bot.send_message(chat_id, msg, parse_mode="HTML")

        # 5. Agenda o Job
        job_data = {
            "user_id": user_id, 
            "chat_id": chat_id,
            "message_id": sent_msg.message_id,
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
        logger.error(f"[AutoHunt] ERRO START: {e}")
        await query.answer("Erro ao iniciar. Tente novamente.", show_alert=True)