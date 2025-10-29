# handlers/job_handler.py
import re
import random
import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest, Forbidden # Adiciona Forbidden

# Módulos do Jogo
from modules import player_manager, game_data, clan_manager, mission_manager, file_ids
# <<< CORREÇÃO: Importa PremiumManager >>>
from modules.player.premium import PremiumManager
# Importa funções específicas se necessário (ou use player_manager.func)
from modules.player_manager import (
    iter_players, add_energy, save_player_data, has_premium_plan,
    get_perk_value, get_player_max_energy, add_item_to_inventory,
    get_pvp_points, add_gems, get_player_data
)
# Importa config se necessário para EVENT_TIMES, JOB_TIMEZONE
from config import EVENT_TIMES, JOB_TIMEZONE
# Importa job finalizador de refino
from handlers.refining_handler import finish_dismantle_job
# Importa agendador pvp
from pvp.pvp_config import MONTHLY_RANKING_REWARDS # Importa recompensas
# Importa watchdog e parse_iso (verificar caminho)
from modules.player.actions import _parse_iso # Assume que está em actions.py
# Importa job finalizador
# from handlers.job_handler import finish_collection_job # Importação circular? Verificar.
# Importa job finalizador de menu/região
from handlers.menu.region import finish_travel_job
# Importa job finalizador de forge
from handlers.forge_handler import finish_craft_notification_job as finish_crafting_job
# Importa job finalizador de refino
from handlers.refining_handler import finish_refine_job as finish_refining_job
# Importa utilitário de agendamento
from handlers.utils_timed import schedule_or_replace_job
# Importa reset PvP
# from handlers.jobs import reset_pvp_season # Importação circular? Verificar.

logger = logging.getLogger(__name__)

# --- CONSTANTES --- (Mantidas do teu código anterior)
DAILY_CRYSTAL_ITEM_ID = "cristal_de_abertura"
DAILY_CRYSTAL_BASE_QTY = 4
DAILY_NOTIFY_USERS = True
_non_premium_tick: dict[str, int] = {"count": 0}
ANNOUNCEMENT_CHAT_ID = -1002881364171 # ID do Grupo/Canal
ANNOUNCEMENT_THREAD_ID = 24         # ID do Tópico

# -------------------------
# Helpers (Mantidos)
# -------------------------
def _humanize(seconds: int) -> str:
    """Converte segundos numa string legível (ex: '4 min', '45 s')."""
    seconds = int(seconds)
    
    # <<< CORREÇÃO: Mostra segundos se for menos de 1 minuto >>>
    if seconds < 60:
        return f"{seconds} s"
        
    # <<< CORREÇÃO: Usa math.floor (arredondar para baixo) para minutos >>>
    m = math.floor(seconds / 60)
    
    # Opcional: Mostrar segundos restantes
    s = seconds % 60
    if s > 0:
     return f"{m} min {s} s"
    
    return f"{m} min"
async def _safe_answer(update: Update) -> None:
    # ... (código existente) ...
    q = update.callback_query
    if not q: return
    try: await q.answer()
    except BadRequest: pass
    except Exception: logger.debug("query.answer() ignorado", exc_info=True)

async def _safe_edit(update: Update, text: str, reply_markup=None, parse_mode='HTML') -> None: # Adiciona reply_markup e parse_mode
    """ Tenta editar caption ou texto, com fallback para send_message. """
    q = update.callback_query
    if not q or not q.message:
         # Se não houver query ou mensagem original, tenta enviar uma nova
         if update.effective_chat:
              try: await update.effective_chat.send_message(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
              except Exception as e_send: logger.error(f"Falha ao enviar msg (safe_edit fallback): {e_send}")
         return

    try: # Tenta editar caption primeiro
        await q.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except BadRequest as e:
        if "message is not modified" in str(e).lower(): return # Ignora se a msg é a mesma
        # Se o erro NÃO for 'not modified', tenta editar texto
    except Exception: # Outros erros ao editar caption, tenta texto
        pass

    try: # Tenta editar texto
        await q.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except BadRequest as e:
         if "message is not modified" in str(e).lower(): return # Ignora
         logger.warning(f"Falha ao editar texto (safe_edit): {e}")
    except Exception as e:
        logger.warning(f"Falha ao editar texto (safe_edit geral): {e}")
        # Sem pânico: a msg pode ter sido apagada/alterada

def _clamp_float(v: Any, lo: float, hi: float, default: float) -> float:

    try: f = float(v)
    except Exception: f = default
    return max(lo, min(hi, f))

def _int(v: Any, default: int = 0) -> int:

    try: return int(v)
    except Exception: return int(default)

async def finish_collection_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Finaliza a coleta, calcula recompensas com base no nível, aplica perks e notifica.
    (Versão robusta e ASSÍNCRONA que lê os dados do job)
    """
    job = context.job
    if not job:
        logger.error("finish_collection_job executed without job context!")
        return

    user_id, chat_id = job.user_id, job.chat_id

    job_data = job.data or {}
    resource_id = job_data.get('resource_id')

    # <<< CORREÇÃO 1: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        logger.warning(f"finish_collection_job: Player data not found for user {user_id}")
        return

    # ... (Validação e estado mantidos) ...
    state = player_data.get('player_state') or {}
    details = state.get('details') or {}
    
    item_info = game_data.ITEMS_DATA.get(resource_id, {}) or {}
    if not resource_id or not item_info:
        logger.warning(f"Collection end {user_id}: Invalid resource_key '{resource_id}' in job.data.")

        if (player_data.get('player_state') or {}).get('action') == 'collecting':
            player_data['player_state'] = {'action': 'idle'}
            # <<< CORREÇÃO 2: Adiciona await >>>
            await player_manager.save_player_data(user_id, player_data)

        try: 
            await context.bot.send_message(chat_id=chat_id, text="Sua ação de coleta foi finalizada (recurso inválido).")
        except Exception as e_notify_err:
            logger.error(f"Failed to notify invalid resource error {chat_id}: {e_notify_err}")
        return 

    # Pega o estado atual para ver se limpamos e para pegar detalhes
    current_state_action = state.get('action')
    current_state_resource = details.get('resource_id')

    if current_state_action == 'collecting' and current_state_resource == resource_id:
        player_data['player_state'] = {'action': 'idle'}
    elif current_state_action == 'collecting':
        logger.warning(f"finish_collection_job {user_id}: Job (res: {resource_id}) ran, but state is collecting OTHER resource (res: {current_state_resource}).")
    
    item_id_a_receber = job_data.get('item_id_yielded') or details.get('item_id_yielded', resource_id)

    # --- Rewards Calculation ---
    XP_BASE_POR_ITEM = 3
    CHANCE_CRITICA_BASE = 3.0
    MULTIPLICADOR_CRITICO_ITENS = 3
    MULTIPLICADOR_CRITICO_XP = 2

    # Usa o item_info do resource_id (o nó de coleta)
    item_name_node = item_info.get('display_name', resource_id)
    prof = player_data.get('profession', {}) or {}
    prof_level = _int(prof.get('level', 1), 1)
    level_up_text = ""
    xp_ganho = 0
    is_crit = False
    total_stats = player_manager.get_player_total_stats(player_data)
    luck_stat = _int(total_stats.get("luck", 5))

    quantidade_base = 1 + prof_level 
    quantidade_final = quantidade_base

    chance_critica_final = CHANCE_CRITICA_BASE + (prof_level * 0.1) + (luck_stat * 0.05) 
    if random.uniform(0, 100) < chance_critica_final:
        is_crit = True
        quantidade_final = quantidade_base * MULTIPLICADOR_CRITICO_ITENS
        critical_message = "✨ <b>𝑪𝒐𝒍𝒆𝒕𝒂 𝑪𝒓𝒊́𝒕𝒊𝒄𝒂!</b> Dobrou os ganhos!\n"
    else:
        critical_message = ""

    # --- Grant item and update missions ---
    player_manager.add_item_to_inventory(player_data, item_id_a_receber, quantidade_final)
    # mission_manager.update_mission_progress é síncrono
    mission_manager.update_mission_progress(player_data, 'GATHER', details={'item_id': item_id_a_receber, 'quantity': quantidade_final})
    clan_id = player_data.get("clan_id")
    if clan_id:
        try: 
            # <<< CORREÇÃO 3: clan_manager.update_guild_mission_progress deve ser async >>>
            await clan_manager.update_guild_mission_progress(clan_id=clan_id, mission_type='GATHER', details={'item_id': item_id_a_receber, 'count': quantidade_final}, context=context)
        except TypeError: 
            # Se a versão síncrona ainda for usada, ela é chamada aqui (sem await)
            try: clan_manager.update_guild_mission_progress(clan_id=clan_id, mission_type='GATHER', details={'item_id': item_id_a_receber, 'count': quantidade_final})
            except Exception as e_clan: logger.error(f"Error guild mission (gather) clan {clan_id}: {e_clan}")

    # --- Calculate XP & Level Up ---
    required_profession = game_data.get_profession_for_resource(resource_id)
    if prof.get('type') and required_profession and prof['type'] == required_profession:
        xp_base = quantidade_base * XP_BASE_POR_ITEM

        try:
            premium = PremiumManager(player_data)
            xp_mult_perks = _clamp_float(premium.get_perk_value('gather_xp_multiplier', 1.0), 0.0, 100.0, 1.0)
        except Exception as e_xp_mult:
            logger.warning(f"Error getting gather_xp_multiplier for {user_id}: {e_xp_mult}")
            xp_mult_perks = 1.0

        xp_ganho = int(round(xp_base * xp_mult_perks))
        if is_crit: xp_ganho = xp_ganho * MULTIPLICADOR_CRITICO_XP
        prof['xp'] = _int(prof.get('xp', 0)) + xp_ganho

        cur_level = prof_level
        try:
            xp_needed = _int(game_data.get_xp_for_next_collection_level(cur_level), 0)
            while xp_needed > 0 and prof['xp'] >= xp_needed:
                prof['xp'] -= xp_needed
                cur_level += 1
                prof['level'] = cur_level
                prof_name = (game_data.PROFESSIONS_DATA or {}).get(prof['type'], {}).get("display_name", "Profissão")
                level_up_text += f"\n✨ Sua profissão ({prof_name}) subiu para o nível {cur_level}!"
                xp_needed = _int(game_data.get_xp_for_next_collection_level(cur_level), 0) 
        except Exception as e_lvl:
            logger.error(f"Error in profession level up for {user_id}: {e_lvl}")
        player_data['profession'] = prof
    
    # --- Rare Resource (optional) ---
    rare_find_message = ""
    current_location = player_data.get('current_location', '')
    region_info_final = (game_data.REGIONS_DATA or {}).get(current_location, {})
    rare_cfg = region_info_final.get("rare_resource")
    if isinstance(rare_cfg, dict) and rare_cfg.get("key"):
        rare_chance = 0.10 + (luck_stat / 150.0) 
        if random.random() < rare_chance:
            rare_key = rare_cfg["key"]
            rare_item_info = game_data.ITEMS_DATA.get(rare_key, {})
            rare_name = rare_item_info.get("display_name", rare_key)
            player_manager.add_item_to_inventory(player_data, rare_key, 1)
            rare_find_message = f"💎 Sorte! Encontrou 1x {rare_name}!\n"

    # Save player data
    try:
        # <<< CORREÇÃO 4: Adiciona await >>>
        await player_manager.save_player_data(user_id, player_data)
    except Exception as e_save:
        logger.error(f"Error saving data in finish_collection_job for {user_id}: {e_save}", exc_info=True)
        try: await context.bot.send_message(chat_id=chat_id, text="⚠️ Erro ao salvar o resultado da coleta.")
        except Exception: pass
        return

    # --- Prepare Completion Message ---
    # O nome do item que o jogador recebeu
    item_recebido_info = game_data.ITEMS_DATA.get(item_id_a_receber, {}) or {}
    res_name = item_recebido_info.get("display_name", item_id_a_receber)
    
    xp_info = f" (+{xp_ganho} XP)" if xp_ganho > 0 else ""
    region_name_final = region_info_final.get('display_name', current_location) 

    completion_text = (
        f"{critical_message}{rare_find_message}"
        f"✅ Coleta finalizada! Obteve {quantidade_final}x {res_name}{xp_info}."
        f"{level_up_text}\n\n"
        f"Você ainda está em {region_name_final}."
    )

    # --- Send Notification ---
    media_key_to_use = item_info.get("media_key", "coleta_sucesso_generica")
    media_data = file_ids.get_file_data(media_key_to_use)
    keyboard = [[InlineKeyboardButton("➡️ Continuar", callback_data=f"open_region:{current_location}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if media_data and media_data.get("id"):
            fid = media_data["id"]
            ftyp = (media_data.get("type") or "photo").lower()
            if ftyp == "video":
                await context.bot.send_video(chat_id=chat_id, video=fid, caption=completion_text, reply_markup=reply_markup, parse_mode='HTML')
            else:
                await context.bot.send_photo(chat_id=chat_id, photo=fid, caption=completion_text, reply_markup=reply_markup, parse_mode='HTML')
        else:
             await context.bot.send_message(chat_id=chat_id, text=completion_text, reply_markup=reply_markup, parse_mode='HTML')
    except Forbidden:
        logger.warning(f"Failed to send collection completion to {chat_id} (user {user_id}): BOT BLOCKED")
    except Exception as e_send_final:
        logger.warning(f"Failed sending collection result msg/media {chat_id}: {e_send_final}", exc_info=True)
        try: await context.bot.send_message(chat_id=chat_id, text=completion_text, reply_markup=reply_markup, parse_mode='HTML')
        except Exception as e_final_fb: logger.error(f"CRITICAL failure sending final collection msg {chat_id}: {e_final_fb}", exc_info=True)

# Callback de início da coleta
# -------------------------
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
    resource_id = m.group(1) # Pega resource_id do botão

    item_info = game_data.ITEMS_DATA.get(resource_id)
    if not item_info or item_info.get("type") != "resource":
         await query.answer("Recurso inválido!", show_alert=True) # Simplificado
         return

    required_profession = game_data.get_profession_for_resource(resource_id)
    prof = player_data.get('profession', {}) or {}
    if not (required_profession and prof.get('type') == required_profession):
        prof_name = (game_data.PROFESSIONS_DATA.get(required_profession, {}) or {}).get("display_name", "???")
        await query.answer(f"Precisa ser {prof_name}.", show_alert=True)
        return

    # --- Aplica Perks Premium ---
    # <<< CORREÇÃO: Usa PremiumManager >>>
    try:
        premium = PremiumManager(player_data)
        speed_mult_raw = premium.get_perk_value('gather_speed_multiplier', 1.0)
        speed_mult = _clamp_float(speed_mult_raw, lo=0.25, hi=4.0, default=1.0)
        
        energy_cost_raw = premium.get_perk_value('gather_energy_cost', 1)
        energy_cost = max(0, _int(energy_cost_raw, 1))
    except Exception as e_perks:
        logger.warning(f"Erro obter perks coleta {user_id}: {e_perks}")
        speed_mult = 1.0
        energy_cost = 1
    # <<< FIM CORREÇÃO >>>
    
    # Calcula duração com speed_mult
    base_secs = int(getattr(game_data, "COLLECTION_TIME_MINUTES", 10) * 60) # Usa constante
    duration_seconds = max(1, int(base_secs / max(speed_mult, 1e-9))) 

    # Valida e gasta energia
    current_energy = _int(player_data.get('energy', 0))
    if current_energy < energy_cost:
        await query.answer("Energia insuficiente.", show_alert=True)
        return
    if energy_cost > 0:
        player_data['energy'] = current_energy - energy_cost

    # Define o estado e salva
    finish_time_dt = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
    # Usa ensure_timed_state importado (assumindo que esta função foi refeita para ser async ou síncrona/não-bloqueante)
    # Se player_manager.ensure_timed_state for assíncrona, adicione await
    # Assumindo que o player_manager.ensure_timed_state apenas manipula o dicionário, é síncrono.
    player_manager.ensure_timed_state(
        pdata=player_data, action="collecting", seconds=duration_seconds,
        details={'resource_id': resource_id, 'energy_cost': energy_cost, 'speed_mult': speed_mult },
        chat_id=chat_id,
    )
    # <<< CORREÇÃO 6: Adiciona await >>>
    await player_manager.save_player_data(user_id, player_data)

    # Agenda o término
    try:
        job_data_for_finish = {"resource_id": resource_id} # Passa resource_id
        schedule_or_replace_job(
            context=context, job_id=f"collect:{user_id}", when=duration_seconds,
            callback=finish_collection_job, data=job_data_for_finish,
            chat_id=chat_id, user_id=user_id,
        )
    except Exception as e_schedule:
        logger.exception(f"Falha agendar coleta {user_id}: {e_schedule}")
        await query.answer("Erro ao iniciar coleta.", show_alert=True)
        player_data['player_state'] = {'action': 'idle'}
        # <<< CORREÇÃO 7: Adiciona await >>>
        if energy_cost > 0: player_manager.add_energy(player_data, energy_cost) # Devolve
        await player_manager.save_player_data(user_id, player_data) # Salva o estado 'idle' e devolve a energia
        return

    # Mensagem "coletando..."
    item_name_start = item_info.get('display_name', resource_id)
    human = _humanize(duration_seconds)
    cost_txt = "grátis" if energy_cost == 0 else f"-{energy_cost} ⚡️"
    status_text = f"⛏️ Coletando {item_name_start}... (~{human}, {cost_txt})"

    # Mídia (mantido)
    collect_media_key = item_info.get("collection_media_key", "coleta_generica_media")
    file_data = file_ids.get_file_data(collect_media_key)

    # Teclado (mantido)
    current_location = player_data.get('current_location', 'reino_eldora') # Pega localização atual
    kb_list = [
        [InlineKeyboardButton("⚔️ Caçar", callback_data=f"hunt_{current_location}")],
        [InlineKeyboardButton("👤 Personagem", callback_data="profile")],
        [InlineKeyboardButton("🗺️ Mapa", callback_data="travel")],
    ]
    kb = InlineKeyboardMarkup(kb_list)

    # Envio da mensagem (mantido)
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
         await query.answer("Erro interface coleta.", show_alert=True)

# =============================================================================
# Exports
# =============================================================================
collection_handler = CallbackQueryHandler(start_collection_callback, pattern=r'^collect_([A-Za-z0-9_]+)$')

# <<< Verifica se finish_dismantle_job e outras funções de job estão definidas neste ficheiro ou precisam ser importadas >>>
# Exemplo: Se regenerate_energy_job está aqui:
# async def regenerate_energy_job(context: ContextTypes.DEFAULT_TYPE) -> None: ...
# Se daily_crystal_grant_job está aqui:
# async def daily_crystal_grant_job(context: ContextTypes.DEFAULT_TYPE) -> int: ...
# ... e assim por diante para todas as funções de job.