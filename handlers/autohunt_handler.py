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
# 🏁 3. EXECUTOR DE CONCLUSÃO (JOB - ATUALIZADO E IMERSIVO)
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
    Finaliza a simulação de caçada, entrega as recompensas e limpa a interface.
    Garante o envio de mídias dinâmicas de acordo com o resultado.
    """
    logger.info(f"[AutoHunt] Finalizando caçada para ID: {user_id}")

    # 1. Recuperação de Dados do Jogador
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        return

    # Obtém status totais (Base + Itens) para a simulação
    player_stats = await player_manager.get_player_total_stats(player_data)
    player_level = int(player_data.get("level", 1))

    # 2. Configuração da Região e Lista de Monstros
    region_data = game_data.REGIONS_DATA.get(region_key, {})
    monster_list_data = game_data.MONSTERS_DATA.get(region_key) or region_data.get('monsters', []) 

    if not monster_list_data:
        player_data['player_state'] = {'action': 'idle'}
        await player_manager.save_player_data(user_id, player_data)
        return

    # 3. Ciclo de Simulação de Combates
    total_xp, total_gold, wins, losses = 0, 0, 0, 0
    total_items = {}
    killed_monsters_ids = []

    try:
        for _ in range(hunt_count):
            monster_template = random.choice(monster_list_data)
            if isinstance(monster_template, str):
                monster_template = (getattr(game_data, "MONSTER_TEMPLATES", {}) or {}).get(monster_template)
            
            if not monster_template: continue
            
            # Escala o monstro e executa a batalha simulada
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
                break # A caçada para na primeira derrota para realismo
                
    except Exception as e:
        logger.error(f"[AutoHunt] Erro na simulação: {e}")
        player_data['player_state'] = {'action': 'idle'}
        await player_manager.save_player_data(user_id, player_data)
        return 

    # 4. Entrega de Recompensas e Atualização de Inventário
    player_manager.add_gold(player_data, total_gold)
    player_data['xp'] = player_data.get('xp', 0) + total_xp
    
    items_log_list = []
    items_source = getattr(game_data, "ITEMS_DATA", {}) or {}
    for item_id, qty in total_items.items():
        player_manager.add_item_to_inventory(player_data, item_id, qty)
        name = items_source.get(item_id, {}).get('display_name', item_id)
        items_log_list.append(f"• {name} x{qty}")

    # 5. Atualização de Progresso de Missões
    try:
        mission_uid = str(user_id)
        for m_id, count in Counter(killed_monsters_ids).items():
            await mission_manager.update_mission_progress(mission_uid, "hunt", m_id, count)
        for item_id, qty in total_items.items():
            await mission_manager.update_mission_progress(mission_uid, "collect", item_id, qty)
    except Exception as e:
        logger.warning(f"Erro ao atualizar missões: {e}")

    # 6. Destravamento do Jogador e Checagem de Level Up
    _, _, level_up_msg = player_manager.check_and_apply_level_up(player_data)
    player_data['player_state'] = {'action': 'idle'} # Permite que o jogador inicie novas ações
    await player_manager.save_player_data(user_id, player_data)

    # 7. Limpeza da Interface (Apaga Cronômetro)
    if message_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            pass

    # 8. Geração e Envio do Relatório Imersivo
    summary_msg = [
        "🏁 <b>𝐂𝐚𝐜̧𝐚𝐝𝐚 𝐑𝐚́𝐩𝐢𝐝𝐚 𝐂𝐨𝐧𝐜𝐥𝐮𝐢́𝐝𝐚!</b> 🏁",
        f"📊 Resultado: <b>{wins} vitórias</b> | <b>{losses} derrotas</b>",
        "────────────────",
        f"💰 Ouro: +{total_gold} | ✨ XP: +{total_xp}",
    ]
    if items_log_list:
        summary_msg.append("\n🎒 <b>𝐋𝐨𝐨𝐭:</b>")
        summary_msg.extend(items_log_list)
    if level_up_msg: 
        summary_msg.append(f"\n{level_up_msg}")
    
    final_caption = "\n".join(summary_msg)
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar", callback_data=f"open_region:{region_key}")]])

    # Busca a mídia correta baseada no sucesso da caçada
    media_key = "autohunt_victory_media" if wins > 0 else "autohunt_defeat_media"
    file_data = file_id_manager.get_file_data(media_key)
    
    try:
        if file_data and file_data.get("id"):
            m_id = file_data["id"]
            m_type = (file_data.get("type") or "photo").lower()
            
            # Envia o relatório final com Foto ou Vídeo
            if m_type == "video":
                await context.bot.send_video(chat_id, video=m_id, caption=final_caption, parse_mode="HTML", reply_markup=reply_markup)
            else:
                await context.bot.send_photo(chat_id, photo=m_id, caption=final_caption, parse_mode="HTML", reply_markup=reply_markup)
        else:
            # Fallback para mensagem de texto simples
            await context.bot.send_message(chat_id, final_caption, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"[AutoHunt] Erro no envio do relatório final: {e}")

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
    """
    Inicia o motor de caçada automática.
    Limpa o menu anterior, cobra energia 1:1 e envia mídia de feedback.
    """
    query = update.callback_query
    
    # 1. Recuperação Segura da Sessão (Auth Híbrida)
    # Utiliza get_current_player_id conforme módulos/auth_utils.py
    raw_uid = get_current_player_id(update, context)
    if not raw_uid:
        await query.answer("❌ Sessão expirada. Faça login novamente (/start).", show_alert=True)
        return

    user_id = str(raw_uid)
    chat_id = query.message.chat.id
    
    try:
        # Recupera dados do jogador garantindo o formato do ID via player_manager
        player_data = await player_manager.get_player_data(user_id)
        if not player_data:
            await query.answer("❌ Perfil não encontrado.", show_alert=True)
            return

        # 2. Verificação de Plano Premium
        if not PremiumManager(player_data).is_premium():
            await query.answer("⭐️ Recurso exclusivo para Aventureiros Premium!", show_alert=True)
            return

        # Anti-Deadlock: Impede múltiplas ações simultâneas
        current_state = player_data.get('player_state', {}).get('action', 'idle')
        if current_state != 'idle':
            await query.answer(f"⚠️ Você já está ocupado com: {current_state}", show_alert=True)
            return
        
        # 3. Cálculo de Custo de Energia (Regra Absoluta: 1 por 1)
        # O custo é linear: 10 caçadas = 10 energias, sem descontos VIP
        total_cost = hunt_count 
        
        if player_data.get('energy', 0) < total_cost:
            await query.answer(f"⚡ Energia insuficiente. Necessário: {total_cost}.", show_alert=True)
            return

        # 4. Consumo Real e Persistência de Estado via player_manager
        if not player_manager.spend_energy(player_data, total_cost):
            await query.answer("❌ Erro ao consumir energia.", show_alert=True)
            return

        # Calcula tempo de conclusão baseado na constante SECONDS_PER_HUNT
        duration_seconds = SECONDS_PER_HUNT * hunt_count 
        finish_dt = (datetime.now(timezone.utc) + timedelta(seconds=duration_seconds))
        
        # Define o estado do jogador como ocupado (auto_hunting)
        player_data['player_state'] = {
            'action': 'auto_hunting',
            'finish_time': finish_dt.isoformat(),
            'details': {'hunt_count': hunt_count, 'region_key': region_key}
        }
        await player_manager.save_player_data(user_id, player_data)

        # 5. Limpeza Imersiva: Apaga o menu de seleção anterior para não empilhar
        menu_message_id = query.message.message_id
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=menu_message_id)
        except Exception as e:
            logger.warning(f"[AutoHunt] Falha ao apagar menu: {e}")

        # 6. Feedback Visual: Nova Mensagem com Mídia Dinâmica
        region_info = game_data.REGIONS_DATA.get(region_key, {})
        region_name = region_info.get('display_name', region_key)
        duration_min = duration_seconds / 60.0
        
        msg = (
            f"⏱ <b>𝐂𝐚𝐜̧𝐚𝐝𝐚 𝐑𝐚́𝐩𝐢𝐝𝐚 𝐈𝐧𝐢𝐜𝐢𝐚𝐝𝐚!</b>\n"
            f"⚔️ Simulando <b>{hunt_count} combates</b> em <b>{region_name}</b>...\n\n"
            f"⚡ Custo: <b>{total_cost} energia</b>\n"
            f"⏳ Tempo Estimado: <b>{duration_min:.1f} minutos</b>.\n\n"
            f"<i>O relatório final será enviado automaticamente.</i>"
        )

        # Busca mídia de início ("autohunt_start_media") via file_id_manager
        media_data = file_id_manager.get_file_data("autohunt_start_media")
        sent_message = None

        try:
            if media_data and media_data.get("id"):
                m_id = media_data["id"]
                m_type = (media_data.get("type") or "photo").lower()
                
                # Envia nova mídia: Suporta nativamente Vídeo ou Foto
                if m_type == "video":
                    sent_message = await context.bot.send_video(chat_id, video=m_id, caption=msg, parse_mode="HTML")
                else:
                    sent_message = await context.bot.send_photo(chat_id, photo=m_id, caption=msg, parse_mode="HTML")
            else:
                sent_message = await context.bot.send_message(chat_id, msg, parse_mode="HTML")
        except Exception as e:
            logger.error(f"[AutoHunt] Erro ao enviar mídia: {e}")
            sent_message = await context.bot.send_message(chat_id, msg, parse_mode="HTML")

        # 7. Agendamento do Job de Finalização (JobQueue)
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
        logger.error(f"[AutoHunt] Erro crítico ao iniciar: {e}", exc_info=True)
        # Em caso de erro catastrófico, tenta avisar o usuário
        try:
            await context.bot.send_message(chat_id, "❌ Erro ao iniciar a caçada automática.")
        except:
            pass