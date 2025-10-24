# handlers/collection_handler.py

from __future__ import annotations

from typing import Any # Import Any
import logging
import random
import re
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

# Módulos do Jogo
from modules import player_manager, game_data, clan_manager, mission_manager
from modules import file_ids as file_id_manager
# <<< USA AS HELPERS CORRETAS DE actions.py >>>
from modules.player.actions import _collect_duration_seconds, _gather_cost, _gather_xp_mult
from modules.player.premium import PremiumManager
# util para (re)agendar jobs
from handlers.utils_timed import schedule_or_replace_job

logger = logging.getLogger(__name__)


# =============================================================================
# Helpers (Funções _humanize, _get_media_key_for_item, _int, _clamp_float mantidas)
# =============================================================================
def _humanize(seconds: int) -> str:
    seconds = int(seconds)
    if seconds >= 60:
        m = round(seconds / 60)
        return f"{m} min"
    return f"{seconds} s"

def _get_media_key_for_item(item_id: str) -> str:
    if not item_id: return ""
    items_data = getattr(game_data, "ITEMS_DATA", {}) or {}
    item_info = items_data.get(item_id)
    if item_info and (media_key := item_info.get("media_key")):
        return media_key
    return item_id

def _int(v: Any, default: int = 0) -> int:
    try: return int(v)
    except Exception: return int(default)

def _clamp_float(v: Any, lo: float, hi: float, default: float) -> float:
    try: f = float(v)
    except Exception: f = default
    return max(lo, min(hi, f))

# =============================================================================
# JOB: finalizar a coleta
# =============================================================================
async def finish_collection_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Finaliza a coleta, calcula recompensas com base no nível e mostra a imagem do item.
    """
    try:
        job = context.job
        if not job: return
        user_id = job.user_id
        chat_id = job.chat_id
        # job_data = job.data or {} # region_key não é mais necessário aqui

        player_data = player_manager.get_player_data(user_id)
        if not player_data: return

        state = player_data.get("player_state") or {}
        if state.get("action") != "collecting":
            logger.info(f"Job coleta {user_id}: Ação '{state.get('action')}'. Ignorando.")
            return

        details = state.get("details", {})
        resource_key = details.get("resource_id")
        resource_info = (game_data.ITEMS_DATA or {}).get(resource_key, {})
        if not resource_key or not resource_info:
            logger.warning(f"Coleta {user_id}: resource_key '{resource_key}' inválido.")
            player_data["player_state"] = {"action": "idle"}
            player_manager.save_player_data(user_id, player_data)
            await context.bot.send_message(chat_id=chat_id, text="Coleta finalizada (recurso inválido).")
            return

        # ========================= Recompensas =========================
        profession_data = player_data.get("profession", {}) or {}
        profession_lvl = _int(profession_data.get("level", 1))
        total_stats = player_manager.get_player_total_stats(player_data)
        luck_stat = _int(total_stats.get("luck", 5))

        # Quantidade
        base_qty = _int(resource_info.get("base_quantity", 1))
        bonus_per_lvl_req = _int(resource_info.get("quantity_bonus_per_level", 9999))
        quantity_bonus = profession_lvl // bonus_per_lvl_req if bonus_per_lvl_req > 0 else 0
        amount_collected = base_qty + quantity_bonus

        # XP
        base_xp = _int(resource_info.get("base_xp", 5))
        xp_level_bonus = (profession_lvl - 1) * 0.5
        # <<< CORREÇÃO APLICADA: Usa a helper importada >>>
        xp_mult_perks = _gather_xp_mult(player_data)
        xp_gain = int(round((base_xp + xp_level_bonus) * xp_mult_perks))

        # Crítico
        critical_chance = 0.05 + (luck_stat / 200.0)
        is_critical = random.random() < critical_chance
        critical_message = ""
        if is_critical:
            amount_collected *= 2
            xp_gain = int(xp_gain * 1.5)
            critical_message = "✨ <b>𝑪𝒐𝒍𝒆𝒕𝒂 𝑪𝒓𝒊́𝒕𝒊𝒄𝒂!</b> Dobrou os ganhos!\n"

        # Add Item + Missões
        player_manager.add_item_to_inventory(player_data, resource_key, amount_collected)
        mission_manager.update_mission_progress(player_data, 'GATHER', details={'item_id': resource_key, 'quantity': amount_collected})
        clan_id = player_data.get("clan_id")
        if clan_id:
            try:
                 await clan_manager.update_guild_mission_progress(clan_id=clan_id, mission_type='GATHER', details={'item_id': resource_key, 'count': amount_collected}, context=context)
            except TypeError:
                try: clan_manager.update_guild_mission_progress(clan_id=clan_id, mission_type='GATHER', details={'item_id': resource_key, 'count': amount_collected})
                except Exception as e_clan: logger.error(f"Erro missão guilda (coleta) clan {clan_id}: {e_clan}")

        # Recurso Raro
        rare_find_message = ""
        region_info = (game_data.REGIONS_DATA or {}).get(player_data.get('current_location', ''), {})
        rare_cfg = region_info.get("rare_resource")
        if isinstance(rare_cfg, dict) and rare_cfg.get("key"):
            rare_chance = 0.10 + (luck_stat / 150.0)
            if random.random() < rare_chance:
                rare_key = rare_cfg["key"]
                rare_item_info = game_data.ITEMS_DATA.get(rare_key, {})
                rare_name = rare_item_info.get("display_name", rare_key)
                player_manager.add_item_to_inventory(player_data, rare_key, 1)
                rare_find_message = f"💎 Sorte! Encontrou 1x {rare_name}!\n"

        # XP Profissão + Level Up
        profession_data["xp"] = _int(profession_data.get("xp", 0)) + xp_gain
        level_up_message = ""
        try:
            current_prof_level = _int(profession_data.get("level", 1))
            xp_needed = _int(game_data.get_xp_for_next_collection_level(current_prof_level))
            while xp_needed > 0 and profession_data["xp"] >= xp_needed:
                current_prof_level += 1
                profession_data["level"] = current_prof_level
                profession_data["xp"] -= xp_needed
                prof_type = profession_data.get("type", "")
                prof_name = (game_data.PROFESSIONS_DATA or {}).get(prof_type, {}).get("display_name", "Profissão")
                level_up_message += f"\n🎉 Sua profissão de {prof_name} subiu para o nível {current_prof_level}!"
                xp_needed = _int(game_data.get_xp_for_next_collection_level(current_prof_level))
        except Exception as e_lvl:
             logger.error(f"Erro level up profissão {user_id}: {e_lvl}")

        # Persistência
        player_data["profession"] = profession_data
        player_data["player_state"] = {"action": "idle"}
        player_manager.save_player_data(user_id, player_data)

        # Mensagem final
        res_name = resource_info.get("display_name", resource_key)
        region_display_name = region_info.get('display_name', player_data.get('current_location', 'Região Desconhecida'))
        caption = (
            f"{critical_message}{rare_find_message}"
            f"✅ <b>Coleta finalizada!</b>\n"
            f"Obteve <b>{amount_collected}x {res_name}</b> (+<b>{xp_gain}</b> XP)"
            f"{level_up_message}\n\n"
            f"Você ainda está em <b>{region_display_name}</b>."
        )

        keyboard = [
            [InlineKeyboardButton("🖐️ Coletar novamente", callback_data=f"collect_{player_data.get('current_location', '')}")],
            [InlineKeyboardButton("🗺️ Voltar ao Mapa", callback_data="travel")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Envio de Mídia
        image_key = _get_media_key_for_item(resource_key)
        file_data = file_id_manager.get_file_data(image_key)

        try:
            if file_data and file_data.get("id"):
                fid = file_data["id"]
                ftyp = (file_data.get("type") or "photo").lower()
                if ftyp == "video":
                    await context.bot.send_video(chat_id=chat_id, video=fid, caption=caption, reply_markup=reply_markup, parse_mode="HTML")
                else:
                    await context.bot.send_photo(chat_id=chat_id, photo=fid, caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            else:
                await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")
        except Exception as e_send:
            logger.warning(f"Falha envio msg/mídia coleta finalizada {chat_id}: {e_send}")
            try: await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")
            except Exception as e_final_fallback: logger.error(f"Falha CRÍTICA envio msg final coleta {chat_id}: {e_final_fallback}")

    except Exception as e_job:
        logger.exception(f"Erro GERAL job finish_collection_job user {context.job.user_id if context.job else '??'}: {e_job}")
        try: # Tenta notificar o usuário sobre a falha
            user_id_err = context.job.user_id
            chat_id_err = context.job.chat_id
            pdata_err = player_manager.get_player_data(user_id_err)
            if pdata_err:
                 pdata_err['player_state'] = {'action': 'idle'}
                 player_manager.save_player_data(user_id_err, pdata_err)
            await context.bot.send_message(chat_id=chat_id_err, text="⚠️ Erro ao finalizar coleta. Estado resetado.")
        except Exception: pass

# =============================================================================
# CALLBACK: iniciar coleta
# =============================================================================
async def collection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Inicia a coleta na região escolhida, desconta energia (respeitando o plano),
    grava estado cronometrado padronizado e agenda a finalização.
    """
    query = update.callback_query
    await query.answer()
    if not query or not query.message: return

    user_id = query.from_user.id
    chat_id = query.message.chat_id
    player_data = player_manager.get_player_data(user_id)
    if not player_data:
        try: await query.edit_message_text("Use /start para criar seu personagem.")
        except Exception: await context.bot.send_message(chat_id, "Use /start.")
        return

    data = (query.data or "")
    if not data.startswith("collect_"):
        await query.answer("Ação inválida.", show_alert=True)
        return
    region_key = data.replace("collect_", "", 1)

    region_info = (game_data.REGIONS_DATA or {}).get(region_key)
    if not region_info:
        await query.answer("Região não encontrada!", show_alert=True)
        return
    resource_key = region_info.get("resource")
    if not resource_key:
        await query.answer("Sem recurso coletável aqui.", show_alert=True)
        return

    req_prof = game_data.get_profession_for_resource(resource_key)
    cur_prof = (player_data.get("profession") or {}).get("type")
    if req_prof and cur_prof != req_prof:
        req_name = (game_data.PROFESSIONS_DATA or {}).get(req_prof, {}).get("display_name", "???")
        await query.answer(f"Precisa ser {req_name}.", show_alert=True)
        return

    state = player_data.get("player_state") or {"action": "idle"}
    if state.get("action") not in (None, "idle"):
        await query.answer(f"Ocupado com '{state.get('action')}'.", show_alert=True)
        return

    # --- Aplica Perks Premium usando as helpers importadas ---
    cost = _gather_cost(player_data)
    duration_seconds = _collect_duration_seconds(player_data)
    try:
        premium_temp = PremiumManager(player_data)
        speed_mult = float(premium_temp.get_perk_value("gather_speed_multiplier", 1.0))
    except Exception: speed_mult = 1.0
    # --- FIM APLICAÇÃO ---

    # Valida energia
    if cost > 0:
        current_energy = _int(player_data.get('energy', 0))
        if current_energy < cost:
            await query.answer("Energia insuficiente!", show_alert=True)
            return
        player_data['energy'] = current_energy - cost # Gasta energia

    # Define o estado e salva
    finish_time_dt = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
    player_manager.ensure_timed_state(
        pdata=player_data, action="collecting", seconds=duration_seconds,
        details={"region_key": region_key, "resource_id": resource_key, "energy_cost": cost, "speed_mult": speed_mult },
        chat_id=chat_id,
    )
    player_manager.save_player_data(user_id, player_data)

    # Agenda o término
    try:
        job_data_for_finish = {"region_key": region_key}
        schedule_or_replace_job(
            context=context, job_id=f"collect:{user_id}", when=duration_seconds,
            callback=finish_collection_job, data=job_data_for_finish,
            chat_id=chat_id, user_id=user_id,
        )
    except Exception as e_schedule:
        logger.exception(f"Falha agendar coleta {user_id}: {e_schedule}")
        await query.answer("Erro ao iniciar coleta.", show_alert=True)
        player_data['player_state'] = {'action': 'idle'}
        if cost > 0: player_manager.add_energy(player_data, cost) # Devolve energia
        player_manager.save_player_data(user_id, player_data)
        return

    # Mensagem "coletando..."
    human = _humanize(duration_seconds)
    cost_txt = "grátis" if cost == 0 else f"-{cost} ⚡️"
    caption = f"⛏️ Coletando... (~{human}, {cost_txt})\nVocê não poderá realizar outras ações."

    collect_key = f"coleta_{region_key}"
    file_data = file_id_manager.get_file_data(collect_key)

    kb_list = [
        [InlineKeyboardButton("⚔️ Caçar", callback_data=f"hunt_{region_key}")],
        [InlineKeyboardButton("👤 Personagem", callback_data="profile")],
        [InlineKeyboardButton("🗺️ Mapa", callback_data="travel")],
    ]
    kb = InlineKeyboardMarkup(kb_list)

    try: await query.delete_message()
    except Exception: pass
    try:
        if file_data and file_data.get("id"):
            fid = file_data["id"]
            ftyp = (file_data.get("type") or "photo").lower()
            if ftyp == "video":
                await context.bot.send_video(chat_id=chat_id, video=fid, caption=caption, reply_markup=kb, parse_mode="HTML")
            else:
                await context.bot.send_photo(chat_id=chat_id, photo=fid, caption=caption, reply_markup=kb, parse_mode="HTML")
        else:
            await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=kb, parse_mode="HTML")
    except Exception as e_send_start:
         logger.error(f"Falha ao enviar msg 'Coletando...' {chat_id}: {e_send_start}")
         await query.answer("Erro interface coleta.", show_alert=True)

# =============================================================================
# Exports
# =============================================================================
collection_handler = CallbackQueryHandler(collection_callback, pattern=r"^collect_[A-Za-z0-9_]+$")