# handlers/autohunt_handler.py
# STATUS: ✅ SEGURO (ID Blindado + Restrição VIP)

import random
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional
from collections import Counter

from telegram import (
    InlineKeyboardMarkup, InlineKeyboardButton, Update,
    InputMediaPhoto, InputMediaVideo
)
from telegram.ext import ContextTypes
from telegram.error import Forbidden

# --- Imports do Core & Utils ---
from modules.auth_utils import get_current_player_id  # <--- ÚNICA FONTE DE VERDADE
from modules import player_manager, game_data, file_ids as file_id_manager
from modules import mission_manager 
from modules.combat import criticals, rewards 
from modules.player.premium import PremiumManager 

logger = logging.getLogger(__name__)

SECONDS_PER_HUNT = 30 

# ==============================================================================
# 🛠️ 1. FUNÇÕES AUXILIARES DE ESCALA (GAME DESIGN)
# ==============================================================================
def _scale_monster_stats(mon: dict, player_level: int) -> dict:
    """
    Escala os atributos do monstro dinamicamente baseada no nível do jogador.
    """
    m = mon.copy()

    # Normalização de HP
    if "max_hp" not in m and "hp" in m: m["max_hp"] = m["hp"]
    elif "max_hp" not in m: m["max_hp"] = 10 

    # Definição do Nível do Alvo
    min_lvl = m.get("min_level", 1)
    max_lvl = m.get("max_level", player_level + 2)
    target_lvl = max(min_lvl, min(player_level + random.randint(-1, 1), max_lvl))
    m["level"] = target_lvl

    # Formatação do Nome
    raw_name = m.get("name", "Inimigo").replace("Lv.", "").strip()
    raw_name = re.sub(r"^\d+\s+", "", raw_name) 
    m["name"] = f"Lv.{target_lvl} {raw_name}"

    if target_lvl <= 1:
        m["hp"] = m["max_hp"]
        return m

    # Coeficientes de Crescimento
    GROWTH_HP = 12       
    GROWTH_ATK = 2.0     
    GROWTH_DEF = 1.0     
    GROWTH_XP = 3
    GROWTH_GOLD = 1.5    
    
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
async def _simulate_single_battle(
    player_data: dict, player_stats: dict, monster_data: dict
) -> dict:
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

    # Limite de turnos para evitar loops infinitos
    for _ in range(20):
        # 1. Player Ataca
        dmg_to_monster, _, _ = criticals.roll_damage(player_stats, monster_stats_sim, {})
        monster_hp -= max(1, dmg_to_monster)
        
        if monster_hp <= 0:
            # Vitória
            combat_details = monster_data.copy()
            combat_details['monster_xp_reward'] = monster_data.get('xp_reward', 0)
            combat_details['monster_gold_drop'] = monster_data.get('gold_drop', 0)
            
            xp, gold, item_ids_list = rewards.calculate_victory_rewards(player_data, combat_details)
            items_rolled = list(Counter(item_ids_list).items())
            
            return {
                "result": "win", 
                "xp": xp, 
                "gold": gold, 
                "items": items_rolled,
                "monster_id": monster_data.get("id")
            }
            
        # 2. Monstro Ataca
        dmg_to_player, _, _ = criticals.roll_damage(monster_stats_sim, player_stats, {})
        player_hp -= max(1, dmg_to_player)
        
        if player_hp <= 0:
            return {"result": "loss", "reason": "HP do jogador esgotado"}

    return {"result": "loss", "reason": "Exaustão (Tempo Esgotado)"}

# ==============================================================================
# 🏁 3. EXECUTOR DE CONCLUSÃO (JOB - DATA DRIVEN)
# ==============================================================================
async def execute_hunt_completion(
    user_id: str,  # ID do Banco (ObjectId String)
    chat_id: int, 
    hunt_count: int, 
    region_key: str, 
    context: ContextTypes.DEFAULT_TYPE, 
    message_id: int = None
):
    logger.info(f"[AutoHunt] Processando conclusão para ID Interno: {user_id}")

    # Recuperação via ID Interno (Blindado)
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        logger.error(f"[AutoHunt] CRÍTICO: Jogador {user_id} não encontrado no banco durante execução do job.")
        return

    player_stats = await player_manager.get_player_total_stats(player_data)
    player_level = int(player_data.get("level", 1))

    # Dados da Região
    region_data = game_data.REGIONS_DATA.get(region_key, {})
    monster_list_data = game_data.MONSTERS_DATA.get(region_key) or region_data.get('monsters', []) 

    if not monster_list_data:
        player_data['player_state'] = {'action': 'idle'}
        await player_manager.save_player_data(user_id, player_data)
        try:
            await context.bot.send_message(chat_id, f"⚠️ Erro de Dados: Região '{region_key}' sem monstros definidos.")
        except: pass
        return

    # --- Loop de Simulação ---
    total_xp = 0
    total_gold = 0
    total_items = {}
    killed_monsters_ids = []
    wins = 0
    losses = 0

    try:
        for i in range(hunt_count):
            monster_template = random.choice(monster_list_data)
            
            # Resolve referência de string para objeto se necessário
            if isinstance(monster_template, str):
                monster_id_str = monster_template
                monster_template = (getattr(game_data, "MONSTER_TEMPLATES", {}) or {}).get(monster_id_str)
                if not monster_template: continue 
            elif not isinstance(monster_template, dict):
                continue
            
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
                # AutoHunt para na primeira derrota para segurança
                break 
                
    except Exception as e:
        logger.error(f"[AutoHunt] Exception na simulação ({user_id}): {e}", exc_info=True)
        player_data['player_state'] = {'action': 'idle'}
        await player_manager.save_player_data(user_id, player_data)
        return 

    # --- Aplicação de Recompensas ---
    player_manager.add_gold(player_data, total_gold)
    player_data['xp'] = player_data.get('xp', 0) + total_xp
    
    items_log_list = []
    items_source = getattr(game_data, "ITEMS_DATA", {}) or {}
    
    for item_id, qty in total_items.items():
        player_manager.add_item_to_inventory(player_data, item_id, qty)
        item_name = items_source.get(item_id, {}).get('display_name', item_id)
        items_log_list.append(f"• {item_name} x{qty}")

    # --- Atualização de Missões ---
    monsters_counter = Counter(killed_monsters_ids)
    try:
        # mission_manager espera string do ID
        mission_uid = str(user_id)
        for m_id, count in monsters_counter.items():
            await mission_manager.update_mission_progress(mission_uid, "hunt", m_id, count)
        for item_id, qty in total_items.items():
            await mission_manager.update_mission_progress(mission_uid, "collect", item_id, qty)
    except Exception as e:
        logger.error(f"[AutoHunt] Erro ao atualizar missões: {e}")

    # --- Finalização e Persistência ---
    _, _, level_up_msg = player_manager.check_and_apply_level_up(player_data)
    player_data['player_state'] = {'action': 'idle'}
    await player_manager.save_player_data(user_id, player_data)

    # --- Geração do Relatório (UI) ---
    reg_name = region_data.get('display_name', region_key.title())
    summary_msg = [
        "🏁 <b>𝐂𝐚𝐜̧𝐚𝐝𝐚 𝐑𝐚́𝐩𝐢𝐝𝐚 𝐂𝐨𝐧𝐜𝐥𝐮𝐢́𝐝𝐚!</b> 🏁",
        f"📍 Região: {reg_name}",
        f"📊 𝐑𝐞𝐬𝐮𝐥𝐭𝐚𝐝𝐨: <b>{wins} 𝐯𝐢𝐭𝐨́𝐫𝐢𝐚𝐬</b> | <b>{losses} 𝐝𝐞𝐫𝐫𝐨𝐭𝐚𝐬</b>",
        "────────────────",
        f"💰 𝙊𝙪𝙧𝙤: +{total_gold}",
        f"✨ 𝙓𝙋: +{total_xp}",
    ]
    
    if items_log_list:
        summary_msg.append("\n🎒 <b>𝐋𝐨𝐨𝐭 𝐂𝐨𝐥𝐞𝐭𝐚𝐝𝐨:</b>")
        summary_msg.extend(items_log_list)
    else:
        summary_msg.append("\n🍃 <i>Nenhum item encontrado desta vez.</i>")
        
    if losses > 0:
        summary_msg.append(f"\n⚠️ <i>A caçada parou antecipadamente devido a uma derrota.</i>")
        
    if level_up_msg:
        summary_msg.append(level_up_msg)
    
    final_caption = "\n".join(summary_msg)
    keyboard = [[InlineKeyboardButton("🔙 𝐕𝐨𝐥𝐭𝐚𝐫 𝐩𝐚𝐫𝐚 𝐚 𝐑𝐞𝐠𝐢𝐚̃𝐨", callback_data=f"open_region:{region_key}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Envio Inteligente (Edição ou Nova Mensagem)
    try:
        if not message_id:
            await context.bot.send_message(chat_id, final_caption, parse_mode="HTML", reply_markup=reply_markup)
            return

        # Tenta pegar mídia dinâmica de vitória/derrota
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
        logger.warning(f"[AutoHunt] Bot bloqueado pelo user {user_id}")
    except Exception:
        # Fallback se edição falhar (ex: mensagem muito antiga)
        try:
            await context.bot.send_message(chat_id, final_caption, parse_mode="HTML", reply_markup=reply_markup)
        except: pass 

# ==============================================================================
# 🧩 4. JOB WRAPPER (CALLBACK)
# ==============================================================================
async def finish_auto_hunt_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Wrapper chamado pelo JobQueue. Desempacota os dados e chama o executor.
    """
    job_data = context.job.data
    # Garante que o ID venha como string do job
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
# 🚀 5. INICIADOR (SISTEMA DE LOGIN OBRIGATÓRIO + PREMIUM)
# ==============================================================================
async def start_auto_hunt(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE, 
    hunt_count: int, 
    region_key: str
) -> None:
    query = update.callback_query
    
    # ---------------------------------------------------------
    # 🔒 SEGURANÇA NIVEL 1: RECUPERAÇÃO DE SESSÃO
    # ---------------------------------------------------------
    # Obtém o ID interno (ObjectId) armazenado na sessão do bot após Login
    raw_uid = get_current_player_id(update, context)
    
    if not raw_uid:
        # Se falhar, o usuário não está logado via senha
        await query.answer("❌ Sessão expirada ou inválida. Faça login novamente (/start).", show_alert=True)
        return

    # Garante tipagem String (compatível com users_collection / ObjectId)
    user_id = str(raw_uid)
    chat_id = query.message.chat.id
    
    try:
        player_data = await player_manager.get_player_data(user_id)
        if not player_data:
            await query.answer("❌ Perfil não encontrado no banco de dados.", show_alert=True)
            return

        # ---------------------------------------------------------
        # 🔒 SEGURANÇA NIVEL 2: VERIFICAÇÃO DE PLANO PAGO
        # ---------------------------------------------------------
        # Apenas usuários com plano Aventureiro (Premium) podem usar essa feature
        if not PremiumManager(player_data).is_premium():
            await query.answer("⭐️ Recurso exclusivo para Aventureiros Premium!", show_alert=True)
            return

        # 2. Anti-Deadlock (Verifica se já não está fazendo algo)
        current_state = player_data.get('player_state', {}).get('action', 'idle')
        if current_state != 'idle':
            finish_str = player_data.get('player_state', {}).get('finish_time')
            is_stuck = False
            if finish_str:
                try:
                    # Se passou mais de 1 minuto do prazo, considera travado
                    if datetime.now(timezone.utc) > datetime.fromisoformat(finish_str) + timedelta(minutes=1):
                        is_stuck = True
                except: is_stuck = True
            
            if not is_stuck:
                await query.answer(f"⚠️ Você já está ocupado com: {current_state}", show_alert=True)
                return
        
        # 3. Cálculo de Custo de Energia
        base_cost_per_hunt = int(getattr(game_data, "HUNT_ENERGY_COST", 1))
        region_info = (getattr(game_data, "REGIONS_DATA", {}) or {}).get(region_key, {}) or {}
        # Regiões podem ter custo específico
        cost_per_hunt = int(region_info.get("hunt_energy_cost", base_cost_per_hunt))
        
        # Aplica Perk de redução de custo
        premium = PremiumManager(player_data)
        final_cost_per_hunt = int(premium.get_perk_value("hunt_energy_cost", cost_per_hunt))
        total_cost = max(0, final_cost_per_hunt) * hunt_count
        
        if player_data.get('energy', 0) < total_cost:
            await query.answer(f"⚡ Energia insuficiente. Necessário: {total_cost}.", show_alert=True)
            return

        # 4. Consumo
        if not player_manager.spend_energy(player_data, total_cost):
            await query.answer("❌ Erro ao processar consumo de energia.", show_alert=True)
            return

        # 5. Definição de Tempo e Estado
        duration_seconds = SECONDS_PER_HUNT * hunt_count 
        
        player_data['player_state'] = {
            'action': 'auto_hunting',
            'finish_time': (datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)).isoformat(),
            'details': {
                'hunt_count': hunt_count, 
                'region_key': region_key
            }
        }
        player_manager.set_last_chat_id(player_data, chat_id)
        await player_manager.save_player_data(user_id, player_data)

        # 6. Feedback Visual
        region_name = region_info.get('display_name', region_key)
        duration_min = duration_seconds / 60.0
        
        msg = (
            f"⏱ <b>𝐂𝐚𝐜̧𝐚𝐝𝐚 𝐑𝐚́𝐩𝐢𝐝𝐚 𝐈𝐧𝐢𝐜𝐢𝐚𝐝𝐚!</b>\n"
            f"⚔️ Simulando <b>{hunt_count} combates</b> em <b>{region_name}</b>...\n\n"
            f"⚡ Custo: {total_cost} energia\n"
            f"⏳ Tempo Estimado: <b>{duration_min:.1f} minutos</b>.\n\n"
            f"<i>Você pode fechar o menu. O relatório chegará automaticamente.</i>"
        )
        
        sent_message = None
        try:
            sent_message = await query.edit_message_caption(caption=msg, parse_mode="HTML", reply_markup=None)
        except:
            sent_message = await context.bot.send_message(chat_id, msg, parse_mode="HTML")

        # 7. Agendamento do Job (ID BLINDADO)
        job_data = {
            "user_id": user_id, # String ID para persistência no Job
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
        logger.error(f"[AutoHunt] Erro crítico ao iniciar ({user_id}): {e}", exc_info=True)
        await query.answer("❌ Ocorreu um erro ao iniciar a caçada.", show_alert=True)