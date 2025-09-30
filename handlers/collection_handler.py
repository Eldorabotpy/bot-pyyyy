# handlers/collection_handler.py

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, game_data
# usa o gerenciador de mídias baseado no JSON
from modules import file_ids as file_id_manager

# util para (re)agendar jobs com nome fixo
from handlers.utils_timed import schedule_or_replace_job

logger = logging.getLogger(__name__)


# =============================================================================
# Helpers
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

def _collect_duration_seconds(player_data: dict) -> int:
    base_min = int(getattr(game_data, "COLLECTION_TIME_MINUTES", 10))
    base_sec = max(1, base_min * 60)
    try:
        mult = float(player_manager.get_player_perk_value(player_data, "gather_speed_multiplier", 1.0))
    except Exception:
        mult = 1.0
    mult = max(0.1, mult)
    return max(1, int(base_sec / mult))

def _gather_cost(player_data: dict) -> int:
    try:
        return int(player_manager.get_player_perk_value(player_data, "gather_energy_cost", 1))
    except Exception:
        return 1

def _gather_xp_mult(player_data: dict) -> float:
    try:
        return float(player_manager.get_player_perk_value(player_data, "gather_xp_multiplier", 1.0))
    except Exception:
        return 1.0


# =============================================================================
# JOB: finalizar a coleta
# =============================================================================
async def finish_collection_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Finaliza a coleta, calcula recompensas com base no nível e mostra a imagem do item.
    """
    try:
        job = context.job
        user_id = job.user_id
        chat_id = job.chat_id
        region_key = (job.data or {}).get("region_key")

        player_data = player_manager.get_player_data(user_id)
        if not player_data or (player_data.get("player_state") or {}).get("action") != "collecting":
            return

        region_info = (game_data.REGIONS_DATA or {}).get(region_key) or {}
        resource_key = region_info.get("resource")
        if not region_info or not resource_key:
            player_data["player_state"] = {"action": "idle"}
            player_manager.save_player_data(user_id, player_data)
            await context.bot.send_message(chat_id=chat_id, text="Coleta finalizada (região ou recurso indisponível).")
            return

        # =========================
        # Recompensas (LÓGICA ATUALIZADA)
        # =========================
        profession_data = player_data.get("profession", {}) or {}
        profession_lvl = int(profession_data.get("level", 1))
        total_stats = player_manager.get_player_total_stats(player_data)
        luck_stat = int(total_stats.get("luck", 5))
        
        # Pega as informações do recurso dos dados de itens
        resource_info = (game_data.ITEMS_DATA or {}).get(resource_key, {})

        # (1) MODIFICADO: Nova lógica de quantidade com base nos dados do item
        base_qty = resource_info.get("base_quantity", 1)
        bonus_per_lvl_req = resource_info.get("quantity_bonus_per_level", 9999) # 9999 para evitar bônus se não definido
        quantity_bonus = profession_lvl // bonus_per_lvl_req
        amount_collected = base_qty + quantity_bonus

        # (2) MODIFICADO: Nova lógica de XP com base nos dados do item
        base_xp = resource_info.get("base_xp", 5)
        # Exemplo: +0.5 XP para cada nível de profissão (exceto o primeiro)
        xp_level_bonus = (profession_lvl - 1) * 0.5
        xp_gain = int(round((base_xp + xp_level_bonus) * _gather_xp_mult(player_data)))

        # (3) Coleta crítica
        critical_chance = 0.05 + (luck_stat / 200.0)
        is_critical = random.random() < critical_chance
        critical_message = ""
        if is_critical:
            amount_collected *= 2
            xp_gain = int(xp_gain * 1.5) # Bônus de XP para crítico
            critical_message = "✨ <b>𝑪𝒐𝒍𝒆𝒕𝒂 𝑪𝒓𝒊́𝒕𝒊𝒄𝒂!</b> 𝑽𝒐𝒄𝒆̂ 𝒆𝒏𝒄𝒐𝒏𝒕𝒓𝒐𝒖 𝒖𝒎𝒂 𝒗𝒆𝒊𝒂 𝒓𝒊𝒄𝒂 𝒆 𝒅𝒐𝒃𝒓𝒐𝒖 𝒔𝒆𝒖𝒔 𝒈𝒂𝒏𝒉𝒐𝒔!\n"

        # (4) Recurso principal
        player_manager.add_item_to_inventory(player_data, resource_key, amount_collected)

        # (5) Recurso raro
        rare_find_message = ""
        rare_cfg = region_info.get("rare_resource")
        if isinstance(rare_cfg, dict) and rare_cfg.get("key"):
            rare_chance = 0.10 + (luck_stat / 150.0)
            if random.random() < rare_chance:
                rare_key = rare_cfg["key"]
                rare_name = rare_cfg.get("name", rare_key)
                player_manager.add_item_to_inventory(player_data, rare_key, 1)
                rare_find_message = f"💎 𝑽𝒐𝒄𝒆̂ 𝒅𝒆𝒖 𝒔𝒐𝒓𝒕𝒆 𝒆 𝒆𝒏𝒄𝒐𝒏𝒕𝒓𝒐𝒖 1𝒙 {rare_name}!\n"

        # (6) XP da PROFISSÃO e Level Up
        profession_data["xp"] = int(profession_data.get("xp", 0)) + xp_gain
        level_up_message = ""
        try:
            xp_needed = int(game_data.get_xp_for_next_collection_level(int(profession_data.get("level", 1))))
        except Exception:
            xp_needed = 999999

        while profession_data["xp"] >= xp_needed:
            profession_data["level"] = int(profession_data.get("level", 1)) + 1
            profession_data["xp"] -= xp_needed
            prof_type = profession_data.get("type", "")
            prof_name = (game_data.PROFESSIONS_DATA or {}).get(prof_type, {}).get("display_name", "Profissão")
            level_up_message += f"\n🎉 𝑺𝒖𝒂 𝒑𝒓𝒐𝒇𝒊𝒔𝒔𝒂̃𝒐 𝒅𝒆 {prof_name} 𝒔𝒖𝒃𝒊𝒖 𝒑𝒂𝒓𝒂 𝒐 𝒏𝒊́𝒗𝒆𝒍 {profession_data['level']}!"
            try:
                xp_needed = int(game_data.get_xp_for_next_collection_level(int(profession_data.get("level", 1))))
            except Exception:
                break

        # Persistência
        player_data["profession"] = profession_data
        player_data["player_state"] = {"action": "idle"}
        player_manager.save_player_data(user_id, player_data)

        # Mensagem final
        res_name = resource_info.get("display_name", resource_key)
        caption = (
            f"{critical_message}{rare_find_message}"
            f"✅ <b>𝑪𝒐𝒍𝒆𝒕𝒂 𝒇𝒊𝒏𝒂𝒍𝒊𝒛𝒂𝒅𝒂!</b>\n"
            f"Você obteve <b>{amount_collected}x {res_name}</b> 𝒆 𝒈𝒂𝒏𝒉𝒐𝒖 <b>{xp_gain}</b> 𝒅𝒆 𝑿𝑷 𝒅𝒆 𝒄𝒐𝒍𝒆𝒕𝒂!"
            f"{level_up_message}\n\n"
            f"𝑽𝒐𝒄𝒆̂ 𝒂𝒊𝒏𝒅𝒂 𝒆𝒔𝒕𝒂́ 𝒆𝒎 <b>{region_info.get('display_name', 'Região')}</b>."
        )

        keyboard = [
            [InlineKeyboardButton("🖐️ 𝐂𝐨𝐥𝐞𝐭𝐚𝐫 𝐧𝐨𝐯𝐚𝐦𝐞𝐧𝐭𝐞 🖐️", callback_data=f"collect_{region_key}")],
            [InlineKeyboardButton("🗺️ 𝐕𝐨𝐥𝐭𝐚𝐫 𝐚𝐨 𝐌𝐚𝐩𝐚 🗺️", callback_data="travel")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # MODIFICADO: A imagem final agora é a do item coletado, não da região.
        image_key = _get_media_key_for_item(resource_key)
        file_data = file_id_manager.get_file_data(image_key)

        if file_data and file_data.get("id"):
            fid = file_data["id"]
            ftyp = (file_data.get("type") or "photo").lower()
            try:
                if ftyp == "video":
                    await context.bot.send_video(chat_id=chat_id, video=fid, caption=caption, reply_markup=reply_markup, parse_mode="HTML")
                else:
                    await context.bot.send_photo(chat_id=chat_id, photo=fid, caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            except Exception as e:
                logger.warning("Falha ao enviar mídia de coleta finalizada: %s", e)
                await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")
        else:
            await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")

    except Exception:
        logger.exception("Erro ao finalizar coleta")
        
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

    user_id = query.from_user.id
    chat_id = query.message.chat_id
    player_data = player_manager.get_player_data(user_id)
    if not player_data:
        await context.bot.send_message(chat_id, "Use /start para criar seu personagem.")
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
        await query.answer("Esta região não possui recurso coletável.", show_alert=True)
        return

    # Profissão exigida para o recurso
    req_prof = game_data.get_profession_for_resource(resource_key)
    cur_prof = (player_data.get("profession") or {}).get("type")
    if req_prof and cur_prof != req_prof:
        req_name = (game_data.PROFESSIONS_DATA or {}).get(req_prof, {}).get("display_name", "Profissão")
        await query.answer(f"Você precisa ser {req_name} para coletar aqui.", show_alert=True)
        return

    # Ocupado?
    st = player_data.get("player_state") or {"action": "idle"}
    if st.get("action") not in (None, "idle"):
        await query.answer(f"Você está ocupado com '{st.get('action')}'. Aguarde terminar.", show_alert=True)
        return

    # Energia (respeita perk do plano)
    cost = _gather_cost(player_data)
    if cost > 0:
        ok = player_manager.spend_energy(player_data, cost)
        if not ok:
            await query.answer("Energia insuficiente para coletar.", show_alert=True)
            return

    # Duração respeitando o plano
    secs = _collect_duration_seconds(player_data)

    # Estado cronometrado padronizado (com started_at/finish_time + last_chat_id)
    player_manager.ensure_timed_state(
        pdata=player_data,
        action="collecting",
        seconds=secs,
        details={"region_key": region_key, "resource_id": resource_key},
        chat_id=chat_id,
    )
    player_manager.save_player_data(user_id, player_data)

    # Agenda o término com nome estável
    schedule_or_replace_job(
        context=context,
        job_id=f"collect:{user_id}",
        when=secs,  # aceita segundos (int) também
        callback=finish_collection_job,
        data={"region_key": region_key},
        chat_id=chat_id,
        user_id=user_id,
    )

    # Mensagem "coletando..."
    human = _humanize(secs)
    cost_txt = "grátis" if cost == 0 else f"-{cost} ⚡️"
    caption = f"⛏️ 𝑪𝒐𝒍𝒆𝒕𝒂𝒏𝒅𝒐… (~{human}, {cost_txt})\n𝑽𝒐𝒄𝒆̂ 𝒏𝒂̃𝒐 𝒑𝒐𝒅𝒆𝒓𝒂́ 𝒓𝒆𝒂𝒍𝒊𝒛𝒂𝒓 𝒐𝒖𝒕𝒓𝒂𝒔 𝒂𝒄̧𝒐̃𝒆𝒔 𝒅𝒖𝒓𝒂𝒏𝒕𝒆 𝒆𝒔𝒔𝒆 𝒑𝒆𝒓𝒊́𝒐𝒅𝒐."

    # mídia de "coleta_<região>" se existir
    collect_key = f"coleta_{region_key}"
    file_data = file_id_manager.get_file_data(collect_key)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ 𝐂𝐚𝐜̧𝐚𝐫 𝐌𝐨𝐧𝐬𝐭𝐫𝐨𝐬 ⚔️", callback_data=f"hunt_{region_key}")],
        [InlineKeyboardButton("👤 𝐏𝐞𝐫𝐬𝐨𝐧𝐚𝐠𝐞𝐦 👤", callback_data="profile")],
        [InlineKeyboardButton("🖐️ 𝐂𝐨𝐥𝐞𝐭𝐚𝐫 𝐧𝐨𝐯𝐚𝐦𝐞𝐧𝐭𝐞 🖐️", callback_data=f"collect_{region_key}")],
        [InlineKeyboardButton("🗺️ 𝐕𝐞𝐫 𝐌𝐚𝐩𝐚 🗺️", callback_data="travel")],
    ])

    try:
        await query.delete_message()
    except Exception:
        pass

    if file_data and file_data.get("id"):
        fid = file_data["id"]
        ftyp = (file_data.get("type") or "photo").lower()
        if ftyp == "video":
            await context.bot.send_video(chat_id=chat_id, video=fid, caption=caption, reply_markup=kb, parse_mode="HTML")
        else:
            await context.bot.send_photo(chat_id=chat_id, photo=fid, caption=caption, reply_markup=kb, parse_mode="HTML")
    else:
        await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=kb, parse_mode="HTML")


# =============================================================================
# Exports
# =============================================================================
collection_handler = CallbackQueryHandler(collection_callback, pattern=r"^collect_[A-Za-z0-9_]+$")
