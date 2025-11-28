# modules/auto_hunt_engine.py
# (VERSÃO FINAL: Missões Integradas + Anti-Crash + Energia Correta)

import random
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from telegram.ext import ContextTypes
from collections import Counter

from telegram import (
    InlineKeyboardMarkup, InlineKeyboardButton, Update,
    InputMediaPhoto, InputMediaVideo
)

# Importa os módulos essenciais
from modules import player_manager, game_data, file_ids as file_id_manager
# Adicionado mission_manager para contar as missões
from modules import mission_manager 
from modules.combat import criticals, rewards 
from modules.player.premium import PremiumManager 

logger = logging.getLogger(__name__)

SECONDS_PER_HUNT = 30 

# ==========================================
# 1. SIMULADOR ROBUSTO (Com retorno de ID para missões)
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

    # Loop de combate (limite 20 turnos para evitar loops infinitos)
    for _ in range(20):
        # 1. Player Ataca
        dmg_to_monster, _, _ = criticals.roll_damage(player_stats, monster_stats_sim, {})
        monster_hp -= max(1, dmg_to_monster)
        
        # 2. Verifica Vitória
        if monster_hp <= 0:
            # Cria um contexto seguro para o cálculo de recompensas
            # Garante que 'xp_reward' e 'gold_drop' existam para não quebrar o rewards.py
            combat_details_for_reward = monster_data.copy()
            combat_details_for_reward['monster_xp_reward'] = monster_data.get('xp_reward', 0)
            combat_details_for_reward['monster_gold_drop'] = monster_data.get('gold_drop', 0)
            
            # Calcula o que ganhou (XP, Ouro, Itens)
            xp, gold, item_ids_list = rewards.calculate_victory_rewards(player_data, combat_details_for_reward)
            items_rolled = list(Counter(item_ids_list).items())
            
            return {
                "result": "win", 
                "xp": xp, 
                "gold": gold, 
                "items": items_rolled,
                "monster_id": monster_data.get("id") # Retorna o ID para a missão contar depois
            }
            
        # 3. Monstro Ataca
        dmg_to_player, _, _ = criticals.roll_damage(monster_stats_sim, player_stats, {})
        player_hp -= max(1, dmg_to_player)
        
        # 4. Verifica Derrota
        if player_hp <= 0:
            return {"result": "loss", "reason": "HP do jogador chegou a 0"}

    return {"result": "loss", "reason": "Batalha demorou muito (20 turnos)"}

# ==========================================
# 2. O JOB (Processa tudo e salva missões em lote)
# ==========================================
async def finish_auto_hunt_job(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    user_id = job_data.get('user_id')
    chat_id = job_data.get('chat_id')
    hunt_count = job_data.get('hunt_count', 0)
    region_key = job_data.get('region_key')
    
    # Lê o message_id para editar
    message_id_to_edit = job_data.get('message_id')

    logger.info(f"[AutoHunt] Finalizando job para {user_id}. Editando msg {message_id_to_edit}.")

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        logger.warning(f"[AutoHunt] Jogador {user_id} não encontrado.")
        return

    player_stats = await player_manager.get_player_total_stats(player_data)
    region_data = game_data.REGIONS_DATA.get(region_key, {})
    
    monster_list_data = game_data.MONSTERS_DATA.get(region_key)
    if not monster_list_data:
        monster_list_data = region_data.get('monsters', []) 

    if not monster_list_data:
        player_data['player_state'] = {'action': 'idle'}
        await player_manager.save_player_data(user_id, player_data)
        await context.bot.send_message(chat_id, f"⚠️ Erro: Região '{region_data.get('display_name', region_key)}' sem monstros.")
        return

    # --- A Simulação ---
    total_xp = 0
    total_gold = 0
    total_items = {}
    killed_monsters_ids = [] # Lista para acumular IDs dos monstros mortos
    wins = 0
    losses = 0

    try:
        for i in range(hunt_count):
            monster_template = random.choice(monster_list_data)
            
            # Resolve se for ID (str) ou Dicionário direto
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
                
                # Guarda o ID para missão
                if battle_result.get("monster_id"):
                    killed_monsters_ids.append(battle_result.get("monster_id"))

                for item_id, qty in battle_result["items"]:
                    total_items[item_id] = total_items.get(item_id, 0) + qty
            else:
                losses += 1
                logger.info(f"[AutoHunt] {user_id} perdeu na simulação {i+1}. Parando.")
                break
    except Exception as e:
        logger.error(f"[AutoHunt] CRASH no loop de simulação para {user_id}: {e}", exc_info=True)
        await context.bot.send_message(chat_id, f"⚠️ Erro crítico na simulação. Admin notificado.")
        player_data['player_state'] = {'action': 'idle'}
        await player_manager.save_player_data(user_id, player_data)
        return 
    
    # --- Aplica Recompensas Físicas ---
    player_manager.add_gold(player_data, total_gold)
    player_data['xp'] = player_data.get('xp', 0) + total_xp
    
    items_log_list = []
    items_data_source = getattr(game_data, "ITEMS_DATA", {}) or {}
    
    for item_id, qty in total_items.items():
        player_manager.add_item_to_inventory(player_data, item_id, qty)
        item_name = items_data_source.get(item_id, {}).get('display_name', item_id)
        items_log_list.append(f"• {item_name} x{qty}")

    # --- ATUALIZA MISSÕES (LOTE) ---
    # Conta quantos de cada monstro foram mortos (Ex: {'goblin': 5, 'orc': 3})
    monsters_counter = Counter(killed_monsters_ids)
    
    try:
        # Atualiza Missão de Caça (HUNT)
        for m_id, count in monsters_counter.items():
            await mission_manager.update_mission_progress(user_id, "hunt", m_id, count)
        
        # Atualiza Missão de Coleta (COLLECT)
        for item_id, qty in total_items.items():
            await mission_manager.update_mission_progress(user_id, "collect", item_id, qty)
            
    except Exception as e:
        logger.error(f"[AutoHunt] Erro ao atualizar missões em lote: {e}")

    # --- Finalização (Level Up e Save) ---
    _, _, level_up_msg = player_manager.check_and_apply_level_up(player_data)
    
    player_data['player_state'] = {'action': 'idle'}
    await player_manager.save_player_data(user_id, player_data)

    # --- Relatório Final ---
    summary_msg = [
        "🏁 <b>Caçada Rápida Concluída!</b> 🏁",
        f"Região: {region_data.get('display_name', region_key.title())}",
        f"Resultado: <b>{wins} vitórias</b>, <b>{losses} derrotas</b>",
        "---",
        f"💰 Ouro obtido: {total_gold}",
        f"✨ XP ganho: {total_xp}",
    ]
    
    if items_log_list:
        summary_msg.append("\n📦 Itens encontrados:")
        summary_msg.extend(items_log_list)
    else:
        summary_msg.append("\n📦 Nenhum item encontrado.")
        
    if losses > 0:
        summary_msg.append(f"\n⚠️ <i>A caçada parou após uma derrota.</i>")
        
    if level_up_msg:
        summary_msg.append(level_up_msg)
    
    final_caption = "\n".join(summary_msg)
    keyboard = [[InlineKeyboardButton("⬅️ Voltar para a Região", callback_data=f"open_region:{region_key}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
        
    # --- Visual (Mídia e Edição) ---
    if wins > 0:
        media_key = "autohunt_victory_media" 
    else:
        media_key = "autohunt_defeat_media" 

    file_data = file_id_manager.get_file_data(media_key)
    
    # Se não tiver msg para editar, envia nova
    if not message_id_to_edit:
        await context.bot.send_message(chat_id, final_caption, parse_mode="HTML", reply_markup=reply_markup)
        return

    try:
        if file_data and file_data.get("id"):
            # Edita Mídia + Texto
            media_type = (file_data.get("type") or "photo").lower()
            InputMediaClass = InputMediaPhoto if media_type == "photo" else InputMediaVideo
            
            await context.bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id_to_edit,
                media=InputMediaClass(media=file_data.get("id"), caption=final_caption, parse_mode="HTML"),
                reply_markup=reply_markup
            )
        else:
            # Edita só Texto
            await context.bot.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id_to_edit,
                caption=final_caption,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"AutoHunt: Falha ao editar msg final: {e}")
        # Fallback: envia nova
        await context.bot.send_message(chat_id, final_caption, parse_mode="HTML", reply_markup=reply_markup)

# ==========================================
# 3. O INICIADOR (Verifica energia e agenda)
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
    
    player_data = await player_manager.get_player_data(user_id)

    # Verifica Premium
    if not PremiumManager(player_data).is_premium():
        await query.answer("⭐️ Funcionalidade exclusiva para Premium.", show_alert=True)
        return

    # Verifica estado
    if player_data.get('player_state', {}).get('action', 'idle') != 'idle':
        await query.answer("Você já está ocupado.", show_alert=True)
        return
    
    # --- CÁLCULO DE ENERGIA ---
    from handlers.hunt_handler import _hunt_energy_cost 

    # Custo unitário x Quantidade (Ex: 1 x 35 = 35)
    cost_per_hunt = await _hunt_energy_cost(player_data, region_key)
    total_cost = cost_per_hunt * hunt_count
     
    if player_data.get('energy', 0) < total_cost:
        await query.answer(f"Energia insuficiente. Precisa de {total_cost}⚡.", show_alert=True)
        return

    # Gasta a energia
    player_manager.spend_energy(player_data, total_cost)
    
    duration_seconds = SECONDS_PER_HUNT * hunt_count # Ex: 30s * 10 = 5 min (ajuste SECONDS_PER_HUNT se quiser mais rápido)
    duration_minutes = duration_seconds / 60

    # Define estado
    player_data['player_state'] = {
        'action': 'auto_hunting',
        'finish_time': (datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)).isoformat(),
        'details': {
            'hunt_count': hunt_count, 
            'region_key': region_key
        }
    }

    await player_manager.save_player_data(user_id, player_data)

    region_name = game_data.REGIONS_DATA.get(region_key, {}).get('display_name', region_key)
    msg = (
        f"⏱ <b>Caçada Rápida Iniciada!</b>\n"
        f"Simulando {hunt_count} combates em <b>{region_name}</b>...\n\n"
        f"⚡ Custo: {total_cost} energia\n"
        f"⏳ Tempo estimado: <b>{duration_minutes:.1f} minutos</b>.\n\n"
        f"Você receberá o relatório aqui quando terminar."
    )
    
    sent_message = None
    try:
        sent_message = await query.edit_message_caption(caption=msg, parse_mode="HTML", reply_markup=None)
    except Exception:
        try:
            sent_message = await query.edit_message_text(text=msg, parse_mode="HTML", reply_markup=None)
        except Exception:
            pass

    # Agenda o Job
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