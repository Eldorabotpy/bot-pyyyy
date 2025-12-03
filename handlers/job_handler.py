# handlers/job_handler.py
import re
import random
import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest, Forbidden

# Módulos do Jogo
from modules import player_manager, game_data, clan_manager, mission_manager, file_ids
from modules.player.premium import PremiumManager
# (Outros imports mantidos conforme sua necessidade)

logger = logging.getLogger(__name__)

# --- CONSTANTES ---
DAILY_CRYSTAL_ITEM_ID = "cristal_de_abertura"
DAILY_CRYSTAL_BASE_QTY = 4

# -------------------------
# Helpers
# -------------------------
def _humanize(seconds: int) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds} s"
    m = math.floor(seconds / 60)
    s = seconds % 60
    if s > 0:
        return f"{m} min {s} s"
    return f"{m} min"

def _int(v: Any, default: int = 0) -> int:
    try: return int(v)
    except Exception: return int(default)

def _clamp_float(v: Any, lo: float, hi: float, default: float) -> float:
    try: f = float(v)
    except Exception: f = default
    return max(lo, min(hi, f))

# -------------------------
# JOB DE FINALIZAÇÃO (Apenas Lógica, sem UI de início)
# -------------------------
async def finish_collection_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Finaliza a coleta, calcula recompensas e notifica.
    (VERSÃO SEGURA: Sem dependência de missões de Guilda)
    """
    job = context.job
    if not job: return

    user_id, chat_id = job.user_id, job.chat_id
    job_data = job.data or {}
    resource_id = job_data.get('resource_id')

    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return

    state = player_data.get('player_state') or {}
    details = state.get('details') or {}
    
    # Validações básicas
    item_info = game_data.ITEMS_DATA.get(resource_id, {}) or {}
    if not resource_id or not item_info:
        if state.get('action') == 'collecting':
            player_data['player_state'] = {'action': 'idle'}
            await player_manager.save_player_data(user_id, player_data)
        try: await context.bot.send_message(chat_id=chat_id, text="Erro: Recurso de coleta inválido.")
        except: pass
        return 

    # Limpa estado se ainda estiver coletando
    if state.get('action') == 'collecting':
        player_data['player_state'] = {'action': 'idle'}
    
    item_id_a_receber = job_data.get('item_id_yielded') or details.get('item_id_yielded', resource_id)

    # --- Cálculo de Recompensas ---
    XP_BASE_POR_ITEM = 3
    CHANCE_CRITICA_BASE = 3.0
    
    prof = player_data.get('profession', {}) or {}
    prof_level = _int(prof.get('level', 1), 1)
    
    total_stats = await player_manager.get_player_total_stats(player_data)
    luck_stat = _int(total_stats.get("luck", 5))

    quantidade_base = 1 + prof_level 
    quantidade_final = quantidade_base
    is_crit = False
    critical_message = ""

    # Crítico
    chance_critica = CHANCE_CRITICA_BASE + (prof_level * 0.1) + (luck_stat * 0.05) 
    if random.uniform(0, 100) < chance_critica:
        is_crit = True
        quantidade_final *= 2 # Dobra
        critical_message = "✨ <b>Sorte!</b> Você coletou o dobro!\n"

    # Entrega Item (Usa função segura do player_manager se disponível, ou inventory direto)
    player_manager.add_item_to_inventory(player_data, item_id_a_receber, quantidade_final)
    
    # Atualiza Missões Pessoais (Isso geralmente é seguro, mas se quiser remover também, apague a linha abaixo)
    try:
        mission_manager.update_mission_progress(player_data, 'GATHER', details={'item_id': item_id_a_receber, 'quantity': quantidade_final})
    except Exception: pass
    
    # --- BLOCO DE GUILDA REMOVIDO PARA EVITAR BUGS ---
    # (O código que chamava clan_manager foi apagado aqui)
    # --------------------------------------------------

    # --- XP de Profissão ---
    xp_ganho = 0
    level_up_text = ""
    required_profession = game_data.get_profession_for_resource(resource_id)
    
    if prof.get('type') == required_profession:
        xp_base = quantidade_base * XP_BASE_POR_ITEM
        premium = PremiumManager(player_data)
        xp_mult = _clamp_float(premium.get_perk_value('gather_xp_multiplier', 1.0), 1.0, 5.0, 1.0)
        
        xp_ganho = int(xp_base * xp_mult)
        if is_crit: xp_ganho *= 2
        
        prof['xp'] = _int(prof.get('xp', 0)) + xp_ganho
        
        # Level Up
        cur_level = prof_level
        while True:
            try: xp_need = int(game_data.get_xp_for_next_collection_level(cur_level))
            except: xp_need = 999999
            
            if xp_need <= 0 or prof['xp'] < xp_need: break
            prof['xp'] -= xp_need
            cur_level += 1
            prof['level'] = cur_level
            level_up_text += f"\n🆙 Profissão subiu para nível {cur_level}!"
            
        player_data['profession'] = prof

    # --- Item Raro (1% a 5%) ---
    rare_msg = ""
    current_location = player_data.get('current_location', 'reino_eldora')
    region_info = (game_data.REGIONS_DATA or {}).get(current_location, {})
    rare_cfg = region_info.get("rare_resource")
    
    if isinstance(rare_cfg, dict) and rare_cfg.get("key"):
        if random.random() < (0.01 + (luck_stat / 2000.0)):
            rare_key = rare_cfg["key"]
            rare_name = (game_data.ITEMS_DATA.get(rare_key, {})).get("display_name", rare_key)
            player_manager.add_item_to_inventory(player_data, rare_key, 1)
            rare_msg = f"💎 <b>Achado Raro!</b> +1 {rare_name}\n"

    # Salva tudo no final
    await player_manager.save_player_data(user_id, player_data)

    # --- Notificação ---
    item_recebido_name = (game_data.ITEMS_DATA.get(item_id_a_receber, {})).get("display_name", item_id_a_receber)
    xp_txt = f" (+{xp_ganho} XP)" if xp_ganho > 0 else ""
    
    msg = (
        f"{critical_message}{rare_msg}"
        f"✅ Coleta finalizada!\n"
        f"Recebeu: <b>{quantidade_final}x {item_recebido_name}</b>{xp_txt}"
        f"{level_up_text}"
    )
    
    # Mídia e Botão
    media_key = item_info.get("media_key", "coleta_sucesso")
    file_data = file_ids.get_file_data(media_key)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data=f"open_region:{current_location}")]])

    try:
        if file_data and file_data.get("id"):
            ftyp = file_data.get("type", "photo")
            if ftyp == "video":
                await context.bot.send_video(chat_id, file_data["id"], caption=msg, reply_markup=kb, parse_mode='HTML')
            else:
                await context.bot.send_photo(chat_id, file_data["id"], caption=msg, reply_markup=kb, parse_mode='HTML')
        else:
            await context.bot.send_message(chat_id, msg, reply_markup=kb, parse_mode='HTML')
    except Exception:
        pass