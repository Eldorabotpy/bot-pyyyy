# handlers/job_handler.py
import re
import random
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

# Módulos do Jogo
from modules import player_manager, game_data, clan_manager, mission_manager, file_ids

logger = logging.getLogger(__name__)

# -------------------------
# Helpers
# -------------------------
async def _safe_answer(update: Update) -> None:
    q = update.callback_query
    if not q:
        return
    try:
        await q.answer()
    except BadRequest:
        pass
    except Exception:
        logger.debug("query.answer() ignorado", exc_info=True)

async def _safe_edit(update: Update, text: str) -> None:
    """
    Tenta editar caption primeiro (mensagens com mídia), se falhar, edita texto.
    """
    q = update.callback_query
    if not q or not q.message:
        return
    try:
        await q.edit_message_caption(caption=text)
        return
    except Exception:
        pass
    try:
        await q.edit_message_text(text=text)
    except Exception:
        # sem pânico: a msg pode ter sido apagada/alterada
        logger.debug("Falha ao editar mensagem de status de coleta", exc_info=True)

def _clamp_float(v: Any, lo: float, hi: float, default: float) -> float:
    try:
        f = float(v)
    except Exception:
        f = default
    return max(lo, min(hi, f))


def _int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default

# -------------------------
# Job de término da coleta
# -------------------------
async def finish_collection_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    if not job:
        return

    user_id, chat_id = job.user_id, job.chat_id
    job_data = job.data or {}
    resource_id = job_data.get('resource_id')

    player_data = player_manager.get_player_data(user_id)
    if not player_data:
        return

    # Lógica de compatibilidade para coletas antigas
    item_id_a_receber = job_data.get('item_id_yielded')
    if not item_id_a_receber and resource_id:
        player_profession = (player_data.get('profession', {}) or {}).get('type')
        if player_profession:
            profession_resources = (game_data.PROFESSIONS_DATA.get(player_profession, {}) or {}).get('resources', {})
            item_id_a_receber = profession_resources.get(resource_id, resource_id)
    if not item_id_a_receber:
        item_id_a_receber = resource_id

    # Verificações de segurança
    state = (player_data.get('player_state') or {}) if isinstance(player_data.get('player_state'), dict) else {}
    if state.get('action') != 'collecting':
        return
    details = (state.get('details') or {}) if isinstance(state.get('details'), dict) else {}
    if details.get('resource_id') and details.get('resource_id') != resource_id:
        return

    # Limpa o estado do jogador
    player_data['player_state'] = {'action': 'idle'}

    if not item_id_a_receber:
        player_manager.save_player_data(user_id, player_data)
        await context.bot.send_message(chat_id=chat_id, text="Sua ação anterior foi finalizada e você está livre para continuar.")
        return

    # ############################################################### #
    # ## INÍCIO DO NOVO SISTEMA DE COLETA DINÂMICA ## #
    # ############################################################### #

    # --- 1. Parâmetros de Balanceamento (Ajuste aqui para mudar o jogo) ---
    XP_BASE_POR_ITEM = 3      # XP ganho por cada item base coletado
    #LVL_PARA_ITEM_EXTRA = 10  # A cada X níveis de profissão, ganha +1 item base
    CHANCE_CRITICA_BASE = 3.0 # Chance base de acerto crítico em % (ex: 5.0 para 5%)
    MULTIPLICADOR_CRITICO_ITENS = 3  # Quantas vezes os itens são multiplicados num crítico
    MULTIPLICADOR_CRITICO_XP = 2     # Quantas vezes o XP é multiplicado num crítico

    # --- 2. Preparação dos dados ---
    item_info = game_data.ITEMS_DATA.get(item_id_a_receber, {}) or {}
    item_name = item_info.get('display_name', item_id_a_receber)
    prof = player_data.get('profession', {}) or {}
    prof_level = _int(prof.get('level', 1), 1)
    level_up_text = ""
    xp_ganho = 0
    is_crit = False

    # --- 3. Cálculo da quantidade de itens ---
    # O jogador ganha +1 item base a cada LVL_PARA_ITEM_EXTRA níveis.
    quantidade_base = 1 + prof_level
    quantidade_final = quantidade_base

    # Chance de Coleta Crítica (aumenta 0.1% por nível de profissão)
    chance_critica_final = CHANCE_CRITICA_BASE + (prof_level * 0.1)
    if random.uniform(0, 100) < chance_critica_final:
        is_crit = True
        quantidade_final = quantidade_base * MULTIPLICADOR_CRITICO_ITENS

    # --- 4. Entrega dos itens e atualização de missões ---
    player_manager.add_item_to_inventory(player_data, item_id_a_receber, quantidade_final)
    mission_manager.update_mission_progress(player_data, 'GATHER', details={'item_id': item_id_a_receber, 'quantity': quantidade_final})
    clan_id = player_data.get("clan_id")
    if clan_id:
        clan_manager.update_guild_mission_progress(clan_id=clan_id, mission_type='GATHER', details={'item_id': item_id_a_receber, 'count': quantidade_final})

    # --- 5. Cálculo de XP e Level Up ---
    required_profession = game_data.get_profession_for_resource(resource_id) if resource_id else None
    if prof.get('type') and required_profession and prof['type'] == required_profession:
        # XP base é calculado sobre a quantidade de itens coletados
        xp_base = quantidade_base * XP_BASE_POR_ITEM
        xp_mult_perks = _clamp_float(player_manager.get_player_perk_value(player_data, 'gather_xp_multiplier', 1.0), 0.0, 100.0, 1.0)
        
        xp_ganho = int(round(xp_base * xp_mult_perks))
        
        if is_crit:
            xp_ganho = xp_ganho * MULTIPLICADOR_CRITICO_XP

        prof['xp'] = _int(prof.get('xp', 0)) + xp_ganho

        # Lógica de Level Up
        cur_level = prof_level
        for _ in range(100):
            xp_needed = _int(game_data.get_xp_for_next_collection_level(cur_level), 0)
            if xp_needed <= 0 or prof['xp'] < xp_needed:
                break
            prof['xp'] -= xp_needed
            cur_level += 1
            prof['level'] = cur_level
            level_up_text = f"\n✨ Sua profissão subiu para o nível {cur_level}!"
        player_data['profession'] = prof
    
    # ############################################################### #
    # ## FIM DO NOVO SISTEMA DE COLETA DINÂMICA ## #
    # ############################################################### #

    # Salva os dados do jogador com o item e o progresso da missão
    player_manager.save_player_data(user_id, player_data)

    # --- Preparação da Mensagem de Conclusão ---
    xp_info = f" (+{xp_ganho} XP)" if xp_ganho > 0 else ""
    crit_info = "✨ 𝐂𝐎𝐋𝐄𝐓𝐀 𝐂𝐑𝐈́𝐓𝐈𝐂𝐀! ✨\n\n" if is_crit else ""

    completion_text = (
        f"{crit_info}✅ Coleta finalizada! Você obteve {quantidade_final}x {item_name}{xp_info}."
        f"{level_up_text}"
    )
    
    # --- LÓGICA DE ENVIO DE MÍDIA PARA A COLETA ---
    media_key_to_use = item_info.get("media_key")
    if not media_key_to_use:
        media_key_to_use = "coleta_sucesso_generica"

    media_data = file_ids.get_file_data(media_key_to_use)
    
    # Adicionamos um botão "Continuar" para voltar ao menu da região
    keyboard = [[InlineKeyboardButton("➡️ 𝑪𝒐𝒏𝒕𝒊𝒏𝒖𝒂𝒓", callback_data=f"open_region:{player_data.get('current_location', 'reino_eldora')}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if media_data and media_data.get("id"):
            await context.bot.send_photo(chat_id=chat_id, photo=media_data["id"], caption=completion_text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            await context.bot.send_message(chat_id=chat_id, text=completion_text, reply_markup=reply_markup, parse_mode='HTML')
    except Exception:
        # Fallback se tudo o resto falhar
        await context.bot.send_message(chat_id=chat_id, text=completion_text, reply_markup=reply_markup, parse_mode='HTML')

# -------------------------
# Callback de início da coleta
# -------------------------
async def start_collection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await _safe_answer(update)
    if not query or not query.message:
        return

    user_id = query.from_user.id
    chat_id = query.message.chat.id

    player_data = player_manager.get_player_data(user_id)
    if not player_data:
        await _safe_edit(update, "Não encontrei seus dados. Use /start para começar.")
        return

    state = (player_data.get('player_state') or {}) if isinstance(player_data.get('player_state'), dict) else {}
    if state.get('action') not in (None, 'idle'):
        await query.answer("Você já está ocupado com outra ação!", show_alert=True)
        return

    m = re.match(r'^collect_([A-Za-z0-9_]+)$', (query.data or ""))
    if not m:
        return
    resource_id = m.group(1)

    required_profession = game_data.get_profession_for_resource(resource_id)
    prof = player_data.get('profession', {}) or {}
    if not (required_profession and prof.get('type') == required_profession):
        await query.answer("Você não possui a profissão necessária para coletar isso.", show_alert=True)
        return

    profession_resources = (game_data.PROFESSIONS_DATA.get(required_profession, {}) or {}).get('resources', {})
    item_id_yielded = profession_resources.get(resource_id, resource_id)

    base_secs = int(getattr(game_data, "COLLECTION_TIME_MINUTES", 1) * 60)
    speed_mult = _clamp_float(player_manager.get_player_perk_value(player_data, 'gather_speed_multiplier', 1.0), lo=0.25, hi=4.0, default=1.0)
    duration_seconds = max(1, int(base_secs / max(speed_mult, 1e-9)))
    energy_cost = max(0, _int(player_manager.get_player_perk_value(player_data, 'gather_energy_cost', 1), 1))

    current_energy = _int(player_data.get('energy', 0))
    if current_energy < energy_cost:
        await query.answer("Você está sem energia para coletar. Descanse um pouco.", show_alert=True)
        return

    player_data['energy'] = current_energy - energy_cost
    finish_time_dt = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)

    player_data['player_state'] = {
        'action': 'collecting',
        'finish_time': finish_time_dt.isoformat(),
        'details': {
            'resource_id': resource_id,
            'item_id_yielded': item_id_yielded,
            'energy_cost': energy_cost,
            'speed_mult': speed_mult
        }
    }
    player_manager.save_player_data(user_id, player_data)

    try:
        context.job_queue.run_once(
            finish_collection_job,
            when=duration_seconds,
            user_id=user_id,
            chat_id=chat_id,
            data={
                'resource_id': resource_id,
                'item_id_yielded': item_id_yielded,
                'energy_cost': energy_cost,
                'charged': True,
                'speed_mult': speed_mult
            }
        )
    except Exception:
        logger.exception("Falha ao agendar job de coleta")

    item_info = game_data.ITEMS_DATA.get(item_id_yielded, {}) or {}
    item_name = item_info.get('display_name', item_id_yielded)
    minutes = duration_seconds / 60
    human = f"{minutes:.0f} minutos" if minutes >= 1 else f"{duration_seconds} segundos"
    cost_txt = "grátis" if energy_cost == 0 else f"-{energy_cost} ⚡️"
    status_text = f"⛏️ Você começou a coletar {item_name}. A tarefa levará ~{human} ({cost_txt})."
    await _safe_edit(update, status_text)

# Handler principal
job_handler = CallbackQueryHandler(start_collection_callback, pattern=r'^collect_[A-Za-z0-9_]+$')
