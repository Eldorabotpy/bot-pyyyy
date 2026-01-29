# handlers/job_handler.py
# (VERSÃO BLINDADA: Garante o Destravamento com TRY/FINALLY)

import random
import logging
from typing import Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime, timezone
from modules.game_data import xp as xp_sys

# Módulos do Jogo
from modules import player_manager, game_data, file_ids

logger = logging.getLogger(__name__)

# ==========================================================
# 🎯 BALANCEAMENTO DE COLETA POR TIER DE FERRAMENTA
# ==========================================================
TIER_BALANCE = {
    1: {"qty": 0, "crit": 0.0, "rare": 0.000, "no_dura": 0.00},
    2: {"qty": 1, "crit": 1.0, "rare": 0.003, "no_dura": 0.10},
    3: {"qty": 2, "crit": 2.0, "rare": 0.007, "no_dura": 0.25},
    4: {"qty": 3, "crit": 3.5, "rare": 0.015, "no_dura": 0.45},
    5: {"qty": 4, "crit": 5.0, "rare": 0.030, "no_dura": 0.70},
}

# --- Helpers ---
def _int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return int(default)

def _get_item_info(base_id: str) -> dict:
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

def _dur_tuple(raw):
    cur, mx = 0, 0
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        try:
            cur = int(raw[0]); mx = int(raw[1])
        except Exception:
            cur, mx = 0, 0
    elif isinstance(raw, dict):
        try:
            cur = int(raw.get("current", 0)); mx = int(raw.get("max", 0))
        except Exception:
            cur, mx = 0, 0
    return max(0, min(cur, mx)), max(0, mx)

def _set_dur(item: dict, cur: int, mx: int) -> None:
    item["durability"] = [int(max(0, min(cur, mx))), int(max(0, mx))]

def _parse_iso(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(str(dt_str).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None

def _resolve_bot(context) -> Any:
    """
    Aceita ContextTypes.DEFAULT_TYPE ou Application.
    Retorna um objeto bot com .send_message/.send_photo/.delete_message.
    """
    bot = getattr(context, "bot", None)
    if bot is not None:
        return bot
    app = getattr(context, "application", None)
    if app is not None and getattr(app, "bot", None) is not None:
        return app.bot
    # fallback final: context pode ser Application direto
    if getattr(context, "bot", None) is not None:
        return context.bot
    return None

# ==============================================================================
# COLETA (LÓGICA FINAL)
# ==============================================================================
async def execute_collection_logic(
    user_id: str,
    chat_id: int | None,
    resource_id: str,
    item_id_yielded: str,
    quantity_base: int,
    context,
    message_id_to_delete: int = None
):
    """
    Finaliza a coleta (IDEMPOTENTE) e notifica com mídia.
    Compatível com context=CallbackContext OU context=Application.
    """

    FIX_IDS = {
        "minerio_ferro": "minerio_de_ferro",
        "iron_ore": "minerio_de_ferro",
        "pedra_ferro": "minerio_de_ferro",
        "minerio_estanho": "minerio_de_estanho",
        "tin_ore": "minerio_de_estanho",
        "madeira_rara_bruta": "madeira_rara",
    }

    if resource_id in FIX_IDS:
        resource_id = FIX_IDS[resource_id]
    if item_id_yielded in FIX_IDS:
        item_id_yielded = FIX_IDS[item_id_yielded]

    bot = _resolve_bot(context)
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        return

    current_loc = player_data.get("current_location", "reino_eldora")

    state = player_data.get("player_state") or {}
    if state.get("action") != "collecting":
        return

    details = state.get("details") or {}

    # ==========================================================
    # ✅ Resolve chat_id (pós-restart)
    # ==========================================================
    if not chat_id:
        try:
            chat_id = int(details.get("collect_chat_id") or 0) or None
        except Exception:
            chat_id = None

    if not chat_id:
        try:
            chat_id = int(player_data.get("last_chat_id") or 0) or None
        except Exception:
            chat_id = None

    # ==========================================================
    # ✅ Guard anti-job duplicado (idempotência)
    # ==========================================================
    state_res = details.get("resource_id")
    if state_res and resource_id and str(state_res) != str(resource_id):
        return

    finish_iso = state.get("finish_time")
    finish_dt = _parse_iso(finish_iso) if finish_iso else None
    if finish_dt:
        if datetime.now(timezone.utc) < finish_dt:
            return

    # ✅ Se o job não passou message_id, tenta pegar do estado salvo
    if not message_id_to_delete:
        try:
            message_id_to_delete = int(details.get("collect_message_id") or 0) or None
        except Exception:
            message_id_to_delete = None

    # tenta apagar a msg "Coletando..." (somente se tiver chat_id/bot)
    if bot and chat_id and message_id_to_delete:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
        except Exception:
            pass

    # resource_id pode ser None em regiões especiais
    if resource_id is None:
        pass
    elif not resource_id:
        try:
            player_data["player_state"] = {"action": "idle"}
            await player_manager.save_player_data(user_id, player_data)
        except Exception:
            pass
        return

    sucesso_operacao = False
    is_crit = False
    quantidade = int(quantity_base or 1)
    final_item_id = item_id_yielded or resource_id or "madeira"
    tool_name = "Ferramenta"
    dur_txt = ""
    xp_result = {}
    user_prof_key = ""

    async def _notify_text(text: str, back_region: str | None = None):
        if not bot or not chat_id:
            return
        back_region = back_region or current_loc
        try:
            await bot.send_message(
                chat_id,
                text,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⬅️ Voltar", callback_data=f"open_region:{back_region}")]]
                ),
                parse_mode="HTML",
            )
        except Exception:
            return

    # 🔒 guard: nível anterior para fallback do UI (mesmo se xp_result vier vazio/ignored)
    prof_level_before_xp = 1

    try:
        equip = player_data.setdefault("equipment", {}) or {}
        equip.setdefault("tool", None)
        inv = player_data.setdefault("inventory", {}) or {}

        # 🛑 profissão
        prof = player_data.get("profession", {}) or {}
        user_prof_key = (prof.get("type") or prof.get("key") or "").strip().lower()
        if user_prof_key and not prof.get("type"):
            prof["type"] = user_prof_key
            player_data["profession"] = prof

        required_profession = None
        if resource_id is not None:
            required_profession = game_data.get_profession_for_resource(resource_id)

        if required_profession and user_prof_key != required_profession:
            prof_info = game_data.PROFESSIONS_DATA.get(required_profession, {}) or {}
            prof_name = prof_info.get("display_name", required_profession.capitalize())
            await _notify_text(f"❌ <b>Falha na Coleta!</b>\n\n⚠️ Requisito: <b>{prof_name}</b>.")
            return

        # 🛠️ ferramenta
        tool_uid = equip.get("tool")
        if not tool_uid or tool_uid not in inv or not isinstance(inv.get(tool_uid), dict):
            await _notify_text("❌ <b>Falha na Coleta!</b>\n\nVocê precisa equipar uma <b>ferramenta</b>.")
            return

        tool_inst = inv[tool_uid]
        tool_base_id = tool_inst.get("base_id")
        if not tool_base_id:
            await _notify_text("❌ <b>Falha na Coleta!</b>\n\nSua ferramenta equipada está inválida (sem base_id).")
            return

        tool_info = _get_item_info(tool_base_id) or {}
        if tool_info.get("type") != "tool":
            await _notify_text("❌ <b>Falha na Coleta!</b>\n\nO item equipado não é uma ferramenta válida.")
            return

        tool_name = tool_info.get("display_name", tool_base_id.replace("_", " ").title())

        tool_type = (tool_info.get("tool_type") or "").strip().lower()
        if required_profession and tool_type != required_profession:
            prof_info = game_data.PROFESSIONS_DATA.get(required_profession, {}) or {}
            prof_name = prof_info.get("display_name", required_profession.capitalize())
            await _notify_text(
                "❌ <b>Falha na Coleta!</b>\n\n"
                "Sua ferramenta não é compatível com este recurso.\n"
                f"⚠️ Requer: <b>{prof_name}</b>."
            )
            return

        # 🧱 durabilidade
        cur_d, mx_d = _dur_tuple(tool_inst.get("durability"))
        if cur_d <= 0:
            await _notify_text(
                "❌ <b>Falha na Coleta!</b>\n\n"
                "Sua ferramenta está <b>quebrada</b>.\n"
                "➡️ Use um pergaminho de reparo ou equipe outra ferramenta."
            )
            return

        # ⚙️ tier
        tool_tier = _int(tool_info.get("tier", 1), 1)
        tier_cfg = TIER_BALANCE.get(tool_tier, TIER_BALANCE[1])

        # 🧮 cálculos
        prof_level = _int(prof.get("level", 1), 1)
        prof_level_before_xp = prof_level  # fallback UI
        stats = await player_manager.get_player_total_stats(player_data)
        luck = _int(stats.get("luck", 5))

        quantidade = int(quantity_base or 1) + prof_level + _int(tier_cfg.get("qty", 0), 0)
        quantidade = max(1, quantidade)

        crit_chance = (
            3.0
            + (prof_level * 0.1)
            + (luck * 0.05)
            + float(tier_cfg.get("crit", 0.0) or 0.0)
        )

        is_crit = (random.uniform(0, 100) < crit_chance)
        if is_crit:
            quantidade *= 2

        # 🎲 gather table
        final_item_id = item_id_yielded or resource_id or "madeira"

        region_info = (game_data.REGIONS_DATA or {}).get(current_loc, {}) or {}
        gather_table = region_info.get("gather_table", {}) or {}
        options = gather_table.get(user_prof_key, []) or []

        eligible = []
        for opt in options:
            if not isinstance(opt, dict):
                continue
            min_lvl = _int(opt.get("min_level", 1), 1)
            if prof_level < min_lvl:
                continue
            item_key = opt.get("item")
            w = _int(opt.get("weight", 0), 0)
            if item_key and w > 0:
                eligible.append((item_key, w))

        if eligible:
            total = sum(w for _, w in eligible)
            roll = random.randint(1, total)
            acc = 0
            for item, w in eligible:
                acc += w
                if roll <= acc:
                    final_item_id = item
                    break

        if not final_item_id:
            final_item_id = "madeira"

        player_manager.add_item_to_inventory(player_data, final_item_id, quantidade)

        # ⭐ XP profissão
        xp_gain = 6 + prof_level
        if is_crit:
            xp_gain = int(xp_gain * 1.5)

        xp_result = xp_sys.add_profession_xp_inplace(
            player_data,
            xp_gain,
            expected_type=user_prof_key
        )

        # 🔧 durabilidade (-1)
        no_dura = float(tier_cfg.get("no_dura", 0.0) or 0.0)
        if no_dura <= 0.0 or random.random() >= no_dura:
            cur_d = max(0, cur_d - 1)

        _set_dur(tool_inst, cur_d, mx_d)
        dur_txt = f"{cur_d}/{mx_d}"

        sucesso_operacao = True

    except Exception as e:
        logger.error(f"[Collection] ERRO CRÍTICO {user_id}: {e}", exc_info=True)

    finally:
        # garante idle + salva sempre
        try:
            player_data["player_state"] = {"action": "idle"}
        except Exception:
            pass

        try:
            await player_manager.save_player_data(user_id, player_data)
        except Exception as e:
            logger.critical(f"[Collection] FALHA AO SALVAR {user_id}: {e}")

        if not sucesso_operacao:
            return

        # ✅ texto final
        item_info = _get_item_info(final_item_id) or {}
        item_name = item_info.get("display_name", final_item_id.replace("_", " ").title())
        emoji = item_info.get("emoji", "📦")
        crit_tag = " ✨<b>CRÍTICO!</b>" if is_crit else ""

        xp_added = int((xp_result or {}).get("xp_added", 0) or 0)

        # ✅ usa old/new do xp_result; fallback para o nível real anterior
        old_lvl = int((xp_result or {}).get("old_level", prof_level_before_xp) or prof_level_before_xp)
        new_lvl = int((xp_result or {}).get("new_level", old_lvl) or old_lvl)

        # ✅ preferir levels_gained do xp_result quando vier
        levels_gained = (xp_result or {}).get("levels_gained", None)
        if levels_gained is None:
            levels_gained = max(0, new_lvl - old_lvl)
        else:
            try:
                levels_gained = max(0, int(levels_gained))
            except Exception:
                levels_gained = max(0, new_lvl - old_lvl)

        # ✅ nome bonito da profissão (se existir)
        prof_display = None
        try:
            prof_info = (game_data.PROFESSIONS_DATA or {}).get(user_prof_key, {}) or {}
            prof_display = prof_info.get("display_name")
        except Exception:
            prof_display = None
        prof_name_ui = (prof_display or user_prof_key or "profissão").title()

        lines = []
        lines.append(f"╭┈┈┈┈┈➤➤✅ ℂ𝕠𝕝𝕖𝕥𝕒 𝔽𝕚𝕟𝕒𝕝𝕚𝕫𝕒𝕕𝕒!┈┈┈➤➤{crit_tag}")
        lines.append("│")
        lines.append(f"├┈➤{emoji} <b>{item_name}</b> x<b>{quantidade}</b>")

        if xp_added:
            lines.append(f"├┈➤⭐ <b>XP da Profissão:</b> +<b>{xp_added}</b>")

        if levels_gained > 0:
            lines.append(
                f"├┈➤⬆️ <b>{prof_name_ui} subiu {levels_gained} nível(is)!</b> "
                f"(Lv. <b>{old_lvl}</b> → <b>{new_lvl}</b>)"
            )

        if dur_txt:
            lines.append(f"├┈➤🛠️ <b>{tool_name}</b> (Durab.: <b>{dur_txt}</b>)")

        lines.append("╰┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤")
        final_text = "\n".join(lines)

        # botão voltar
        back_region = current_loc
        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Voltar", callback_data=f"open_region:{back_region}")]]
        )

        # mídia final
        done_key = f"collect_done_{user_prof_key}"
        done_media = file_ids.get_file_data(done_key) or file_ids.get_file_data("collect_done_generic") or {}
        done_id = done_media.get("id")
        done_type = (done_media.get("type") or "photo").strip().lower()

        if not bot or not chat_id:
            return

        try:
            if done_id and done_type == "video":
                await bot.send_video(chat_id, done_id, caption=final_text, parse_mode="HTML", reply_markup=reply_markup)
            elif done_id:
                await bot.send_photo(chat_id, done_id, caption=final_text, parse_mode="HTML", reply_markup=reply_markup)
            else:
                await bot.send_message(chat_id, final_text, parse_mode="HTML", reply_markup=reply_markup)
        except Exception:
            try:
                await bot.send_message(chat_id, final_text, parse_mode="HTML", reply_markup=reply_markup)
            except Exception:
                pass

# ==============================================================================
# JOB WRAPPER
# ==============================================================================
async def finish_collection_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    if not job:
        return

    job_data = job.data or {}

    raw_uid = job_data.get("user_id") or getattr(job, "user_id", None)
    user_id = str(raw_uid)

    chat_id = job_data.get("chat_id") or getattr(job, "chat_id", None)

    # compat: injeta sessão se existir
    if context.user_data is not None:
        context.user_data["logged_player_id"] = user_id

    msg_id = job_data.get("message_id")
    if not msg_id:
        try:
            pdata = await player_manager.get_player_data(user_id)
            if pdata:
                msg_id = (pdata.get("player_state", {}) or {}).get("details", {}).get("collect_message_id")
        except Exception:
            pass

    await execute_collection_logic(
        user_id=user_id,
        chat_id=chat_id,
        resource_id=job_data.get("resource_id"),
        item_id_yielded=job_data.get("item_id_yielded"),
        quantity_base=job_data.get("quantity", 1),
        context=context,
        message_id_to_delete=msg_id,
    )
