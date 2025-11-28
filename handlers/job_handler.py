# handlers/job_handler.py
# (VERSÃO FINAL CORRIGIDA: COLETA ASSÍNCRONA + MISSÕES + RE)

import logging
import random
import math
import re
from datetime import datetime, timezone, timedelta
from typing import Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

from modules import player_manager, game_data, file_ids
from modules import mission_manager 
from handlers.utils_timed import schedule_or_replace_job
from modules.player.premium import PremiumManager

logger = logging.getLogger(__name__)

# --- CONSTANTES ---
DAILY_CRYSTAL_ITEM_ID = "cristal_de_abertura"
DAILY_CRYSTAL_BASE_QTY = 4
DAILY_NOTIFY_USERS = True
_non_premium_tick: dict[str, int] = {"count": 0}
ANNOUNCEMENT_CHAT_ID = -1002881364171 
ANNOUNCEMENT_THREAD_ID = 24 

def _humanize(seconds: int) -> str:
    """Converte segundos numa string legível."""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds} s"
    m = math.floor(seconds / 60)
    s = seconds % 60
    if s > 0:
        return f"{m} min {s} s"
    return f"{m} min"

async def _safe_answer(update: Update) -> None:
    q = update.callback_query
    if not q: return
    try: await q.answer()
    except BadRequest: pass
    except Exception: logger.debug("query.answer() ignorado", exc_info=True)

async def _safe_edit(update: Update, text: str, reply_markup=None, parse_mode='HTML') -> None:
    q = update.callback_query
    if not q or not q.message:
        if update.effective_chat:
            try: await update.effective_chat.send_message(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
            except Exception as e: logger.error(f"Falha ao enviar msg (safe_edit fallback): {e}")
        return

    try: 
        await q.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except BadRequest as e:
        if "message is not modified" in str(e).lower(): return 
    except Exception: pass

    try:
        await q.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except BadRequest as e:
        if "message is not modified" in str(e).lower(): return 
    except Exception: pass

def _clamp_float(v: Any, lo: float, hi: float, default: float) -> float:
    try: f = float(v)
    except Exception: f = default
    return max(lo, min(hi, f))

def _int(v: Any, default: int = 0) -> int:
    try: return int(v)
    except Exception: return int(default)


async def finish_collection_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Chamado pelo JobQueue quando o tempo de coleta termina.
    """
    job = context.job
    if not job:
        logger.error("finish_collection_job executed without job context!")
        return

    user_id = job.user_id
    chat_id = job.chat_id
    data = job.data or {}
    
    resource_id = data.get("resource_id")
    item_id_yielded = data.get("item_id_yielded")
    energy_cost = data.get("energy_cost", 0)
    speed_mult = data.get("speed_mult", 1.0)
    
    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return

    # Verifica estado
    state = player_data.get("player_state", {})
    if state.get("action") != "collecting":
        return 

    # Calcula quantidade
    base_qty = random.randint(2, 5)
    
    total_stats = await player_manager.get_player_total_stats(player_data)
    luck = total_stats.get("luck", 1)
    
    bonus_luck = 1 if random.random() < (luck * 0.01) else 0
    final_qty = int(base_qty * speed_mult) + bonus_luck
    if final_qty < 1: final_qty = 1

    # Adiciona ao inventário
    player_manager.add_item_to_inventory(player_data, item_id_yielded, final_qty)
    
    # Ganha XP de Profissão
    profession_type = (player_data.get("profession") or {}).get("type")
    xp_gain = 10 * final_qty
    
    if profession_type:
        current_prof_xp = player_data["profession"].get("xp", 0)
        player_data["profession"]["xp"] = current_prof_xp + xp_gain

    # Reseta estado
    player_data["player_state"] = {"action": "idle"}
    
    # --- ATUALIZAÇÃO DE MISSÕES (CORRIGIDO COM AWAIT) ---
    mission_text = ""
    try:
        # IMPORTANTE: await adicionado aqui
        reports = await mission_manager.update_mission_progress(user_id, "collect", resource_id, final_qty)
        if reports:
            mission_text = "\n\n" + "\n".join(reports)
    except Exception as e:
        logger.error(f"Erro ao atualizar missão de coleta: {e}")
    # ----------------------------------------------------

    await player_manager.save_player_data(user_id, player_data)
    
    # Mensagem Final
    item_info = (game_data.ITEMS_DATA or {}).get(item_id_yielded, {})
    item_name = item_info.get("display_name", item_id_yielded)
    emoji = item_info.get("emoji", "📦")
    
    text = (
        f"✅ <b>Coleta Finalizada!</b>\n\n"
        f"Você obteve: <b>{final_qty}x {emoji} {item_name}</b>\n"
        f"Gastou: {energy_cost} Energia\n"
        f"XP Profissão: +{xp_gain}"
        f"{mission_text}"
    )
    
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")

# --- Callback para INICIAR coleta ---
async def start_collection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await _safe_answer(update)
    if not query or not query.message: return

    user_id = query.from_user.id
    chat_id = query.message.chat_id

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await _safe_edit(update, "Use /start para começar.")
        return

    state = (player_data.get('player_state') or {})
    if state.get('action') not in (None, 'idle'):
        await query.answer("Você já está ocupado!", show_alert=True)
        return

    m = re.match(r'^collect_([A-Za-z0-9_]+)$', (query.data or ""))
    if not m: return
    resource_id = m.group(1) 

    item_info = game_data.ITEMS_DATA.get(resource_id)
    if not item_info: 
         await query.answer("Recurso inválido!", show_alert=True) 
         return
    
    required_profession = game_data.get_profession_for_resource(resource_id)
    prof = player_data.get('profession', {}) or {}
    
    is_specialist = False
    if required_profession and prof.get('type') == required_profession:
        is_specialist = True
    
    item_rarity = item_info.get("rarity", "comum")
    if item_rarity in ("lendario", "mistico") and not is_specialist:
         await query.answer(f"Apenas um mestre {required_profession} pode extrair este recurso raro!", show_alert=True)
         return

    try:
        premium = PremiumManager(player_data)
        speed_mult_raw = premium.get_perk_value('gather_speed_multiplier', 1.0)
        
        if is_specialist:
            speed_mult_raw += 0.5 
            
        speed_mult = _clamp_float(speed_mult_raw, lo=0.25, hi=4.0, default=1.0)
        
        energy_cost_raw = premium.get_perk_value('gather_energy_cost', 1)
        energy_cost = max(0, _int(energy_cost_raw, 1))
    except Exception as e_perks:
        logger.warning(f"Erro obter perks coleta {user_id}: {e_perks}")
        speed_mult = 1.0
        energy_cost = 1
    
    base_secs = int(getattr(game_data, "COLLECTION_TIME_MINUTES", 1) * 60)
    duration_seconds = max(1, int(base_secs / max(speed_mult, 1e-9))) 
    current_energy = _int(player_data.get('energy', 0))
    
    if current_energy < energy_cost:
        await query.answer("Energia insuficiente.", show_alert=True)
        return
        
    if energy_cost > 0:
        player_data['energy'] = current_energy - energy_cost

    profession_resources = (game_data.PROFESSIONS_DATA.get(required_profession, {}) or {}).get('resources', {})
    item_id_yielded = profession_resources.get(resource_id, resource_id)

    finish_time_dt = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
    
    player_data["player_state"] = {
        "action": "collecting",
        "finish_time": finish_time_dt.isoformat(),
        "details": {
            "resource_id": resource_id,
            "item_id_yielded": item_id_yielded,
            "energy_cost": energy_cost,
            "speed_mult": speed_mult,
        }
    }
    player_data["last_chat_id"] = chat_id
    await player_manager.save_player_data(user_id, player_data)

    try:
        job_data_for_finish = {
            "resource_id": resource_id, 
            "item_id_yielded": item_id_yielded,
            "energy_cost": energy_cost,
            "speed_mult": speed_mult
        }
        schedule_or_replace_job(
            context=context, job_id=f"collect:{user_id}", when=duration_seconds,
            callback=finish_collection_job, data=job_data_for_finish,
            chat_id=chat_id, user_id=user_id,
        )
    except Exception as e_schedule:
        logger.exception(f"Falha agendar coleta {user_id}: {e_schedule}")
        await query.answer("Erro ao iniciar coleta.", show_alert=True)
        return

    item_name_start = item_info.get('display_name', resource_id)
    human = _humanize(duration_seconds)
    cost_txt = "grátis" if energy_cost == 0 else f"-{energy_cost} ⚡️"
    status_text = f"⛏️ Coletando {item_name_start}... (~{human}, {cost_txt})"
    
    collect_media_key = item_info.get("collection_media_key", "coleta_generica_media")
    file_data = file_ids.get_file_data(collect_media_key)

    current_location = player_data.get('current_location', 'reino_eldora') 
    kb_list = [
        [InlineKeyboardButton("⚔️ Caçar", callback_data=f"hunt_{current_location}")],
        [InlineKeyboardButton("👤 Personagem", callback_data="profile")],
        [InlineKeyboardButton("🗺️ Mapa", callback_data="travel")],
    ]
    kb = InlineKeyboardMarkup(kb_list)

    try: await query.delete_message()
    except Exception: pass
    
    try:
        if file_data and file_data.get("id"):
            fid = file_data["id"] ; ftyp = (file_data.get("type") or "photo").lower()
            if ftyp == "video": await context.bot.send_video(chat_id=chat_id, video=fid, caption=status_text, reply_markup=kb, parse_mode="HTML")
            else: await context.bot.send_photo(chat_id=chat_id, photo=fid, caption=status_text, reply_markup=kb, parse_mode="HTML")
        else: await context.bot.send_message(chat_id=chat_id, text=status_text, reply_markup=kb, parse_mode="HTML")
    except Exception as e_send_start:
         logger.error(f"Falha envio msg 'Coletando...' {chat_id}: {e_send_start}")
         await query.answer("Coleta iniciada (erro visual).", show_alert=True)


# =============================================================================
# Exports
# =============================================================================
finish_collection_job_handler = None
collection_handler = CallbackQueryHandler(start_collection_callback, pattern=r'^collect_([A-Za-z0-9_]+)$')