# handlers/job_handler.py
# (VERSÃO BLINDADA: Garante o Destravamento com TRY/FINALLY)

import random
import logging
import traceback
from typing import Any
from telegram.error import Forbidden
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Módulos do Jogo
from modules import player_manager, game_data, mission_manager, file_ids
from modules.player.premium import PremiumManager

logger = logging.getLogger(__name__)

# ==========================================================
# 🎯 BALANCEAMENTO DE COLETA POR TIER DE FERRAMENTA
# ==========================================================
# qty     → bônus fixo de quantidade
# crit    → bônus de chance crítica (%)
# rare    → bônus direto na chance de recurso raro
# no_dura → chance de NÃO consumir durabilidade (0.0 a 1.0)
# ==========================================================
TIER_BALANCE = {
    1: {  # Ferramentas básicas
        "qty": 0,
        "crit": 0.0,
        "rare": 0.000,
        "no_dura": 0.00,
    },
    2: {  # Ferro
        "qty": 1,
        "crit": 1.0,
        "rare": 0.003,
        "no_dura": 0.10,
    },
    3: {  # Aço
        "qty": 2,
        "crit": 2.0,
        "rare": 0.007,
        "no_dura": 0.25,
    },
    4: {  # Mithril / Obsidiana
        "qty": 3,
        "crit": 3.5,
        "rare": 0.015,
        "no_dura": 0.45,
    },
    5: {  # Adamantio / Lendárias
        "qty": 4,
        "crit": 5.0,
        "rare": 0.030,
        "no_dura": 0.70,
    },
}

# --- Helpers ---
def _int(v: Any, default: int = 0) -> int:
    try: return int(v)
    except Exception: return int(default)

def _clamp_float(v: Any, lo: float, hi: float, default: float) -> float:
    try: f = float(v)
    except Exception: f = default
    return max(lo, min(hi, f))

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

def _get_item_max_durability_from_info(info: dict, fallback_max: int) -> int:
    """
    Pega max dur do item base (ITEMS_DATA). Se não tiver, usa fallback.
    """
    dur = info.get("durability")
    if isinstance(dur, (list, tuple)) and len(dur) >= 2:
        try:
            return int(dur[1])
        except Exception:
            return int(fallback_max or 0)
    return int(fallback_max or 0)

# ==============================================================================
# 1. A LÓGICA PURA (BLINDADA COM TRY/FINALLY)
# ==============================================================================
async def execute_collection_logic(
    user_id: str,
    chat_id: int,
    resource_id: str,
    item_id_yielded: str,
    quantity_base: int,
    context: ContextTypes.DEFAULT_TYPE,
    message_id_to_delete: int = None
):
    # --- AUTO-CORREÇÃO DE IDs (Compatibilidade Legado) ---
    FIX_IDS = {
        "minerio_ferro": "minerio_de_ferro",
        "iron_ore": "minerio_de_ferro",
        "pedra_ferro": "minerio_de_ferro",
        "minerio_estanho": "minerio_de_estanho",
        "tin_ore": "minerio_de_estanho",
        "madeira_rara_bruta": "madeira_rara"
    }

    if resource_id in FIX_IDS:
        resource_id = FIX_IDS[resource_id]
    if item_id_yielded in FIX_IDS:
        item_id_yielded = FIX_IDS[item_id_yielded]

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        return

    # 1) Limpa mensagem "Coletando..." (cosmético)
    if message_id_to_delete:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
        except Exception:
            pass

    # resource_id pode ser None em regiões especiais
    if resource_id is None:
        pass
    elif not resource_id:
        player_data["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(user_id, player_data)
        return

    sucesso_operacao = False

    try:
        # 🔓 Estado
        player_data["player_state"] = {"action": "idle"}
        current_loc = player_data.get("current_location", "reino_eldora")

        # 🔧 Normaliza estrutura legado (garante slot tool existir)
        equip = player_data.setdefault("equipment", {})
        equip.setdefault("tool", None)
        inv = player_data.setdefault("inventory", {})

        # ================================
        # 🛑 TRAVA DE PROFISSÃO
        # ================================
        prof = player_data.get("profession", {}) or {}
        user_prof_key = (prof.get("key") or prof.get("type") or "").strip().lower()

        required_profession = None
        if resource_id is not None:
            required_profession = game_data.get_profession_for_resource(resource_id)

        if required_profession and user_prof_key != required_profession:
            prof_info = game_data.PROFESSIONS_DATA.get(required_profession, {})
            prof_name = prof_info.get("display_name", required_profession.capitalize())

            await context.bot.send_message(
                chat_id,
                f"❌ <b>Falha na Coleta!</b>\n\n"
                f"⚠️ Requisito: <b>{prof_name}</b>.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⬅️ Voltar", callback_data=f"open_region:{current_loc}")]]
                ),
                parse_mode="HTML"
            )
            return

        # ================================
        # 🛠️ TRAVA DE FERRAMENTA
        # ================================
        tool_uid = equip.get("tool")

        if not tool_uid or tool_uid not in inv or not isinstance(inv.get(tool_uid), dict):
            await context.bot.send_message(
                chat_id,
                "❌ <b>Falha na Coleta!</b>\n\n"
                "Você precisa equipar uma <b>ferramenta</b>.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⬅️ Voltar", callback_data=f"open_region:{current_loc}")]]
                ),
                parse_mode="HTML"
            )
            return

        tool_inst = inv[tool_uid]
        tool_base_id = tool_inst.get("base_id")
        if not tool_base_id:
            await context.bot.send_message(
                chat_id,
                "❌ <b>Falha na Coleta!</b>\n\n"
                "Sua ferramenta equipada está inválida (sem base_id).",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⬅️ Voltar", callback_data=f"open_region:{current_loc}")]]
                ),
                parse_mode="HTML"
            )
            return

        tool_info = _get_item_info(tool_base_id)
        if not tool_info or tool_info.get("type") != "tool":
            await context.bot.send_message(
                chat_id,
                "❌ <b>Falha na Coleta!</b>\n\n"
                "O item equipado não é uma ferramenta válida.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⬅️ Voltar", callback_data=f"open_region:{current_loc}")]]
                ),
                parse_mode="HTML"
            )
            return

        tool_type = (tool_info.get("tool_type") or "").strip().lower()
        if required_profession and tool_type != required_profession:
            prof_info = game_data.PROFESSIONS_DATA.get(required_profession, {})
            prof_name = prof_info.get("display_name", required_profession.capitalize())

            await context.bot.send_message(
                chat_id,
                "❌ <b>Falha na Coleta!</b>\n\n"
                "Sua ferramenta não é compatível com este recurso.\n"
                f"⚠️ Requer: <b>{prof_name}</b>.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⬅️ Voltar", callback_data=f"open_region:{current_loc}")]]
                ),
                parse_mode="HTML"
            )
            return

        # ================================
        # 🧱 DURABILIDADE
        # ================================
        cur_d, mx_d = _dur_tuple(tool_inst.get("durability"))
        if cur_d <= 0:
            await context.bot.send_message(
                chat_id,
                "❌ <b>Falha na Coleta!</b>\n\n"
                "Sua ferramenta está <b>quebrada</b>.\n"
                "➡️ Use um pergaminho de reparo ou equipe outra ferramenta.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⬅️ Voltar", callback_data=f"open_region:{current_loc}")]]
                ),
                parse_mode="HTML"
            )
            return

        # ================================
        # ⚙️ TIER BALANCE
        # ================================
        tier_balance = globals().get("TIER_BALANCE") or {
            1: {"qty": 0, "crit": 0.0, "rare": 0.0, "no_dura": 0.0}
        }
        tool_tier = _int(tool_info.get("tier", 1), 1)
        tier_cfg = tier_balance.get(tool_tier, tier_balance[1])

        # ================================
        # 🧮 CÁLCULOS
        # ================================
        prof_level = _int(prof.get("level", 1), 1)
        stats = await player_manager.get_player_total_stats(player_data)
        luck = _int(stats.get("luck", 5))

        quantidade = quantity_base + prof_level + _int(tier_cfg.get("qty", 0), 0)
        crit_chance = (
            3.0
            + (prof_level * 0.1)
            + (luck * 0.05)
            + float(tier_cfg.get("crit", 0.0) or 0.0)
        )

        is_crit = random.uniform(0, 100) < crit_chance
        if is_crit:
            quantidade *= 2

        # ================================
        # 🎲 GATHER TABLE
        # ================================
        # fallback seguro: se resource_id for None e item_id_yielded também, evita inserir None no inventário
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

        player_manager.add_item_to_inventory(player_data, final_item_id, quantidade)

        logger.info(
            f"[GATHER] user={user_id} item={final_item_id} "
            f"qty={quantidade} region={current_loc} "
            f"prof={user_prof_key} lvl={prof_level}"
        )

        # ================================
        # 🔧 DURABILIDADE (chance não consumir)
        # ================================
        no_dura = float(tier_cfg.get("no_dura", 0.0) or 0.0)
        if no_dura <= 0.0 or random.random() >= no_dura:
            cur_d = max(0, cur_d - 1)
        _set_dur(tool_inst, cur_d, mx_d)

        sucesso_operacao = True

    except Exception as e:
        logger.error(f"[Collection] ERRO CRÍTICO {user_id}: {e}", exc_info=True)

    finally:
        try:
            await player_manager.save_player_data(user_id, player_data)
        except Exception as e:
            logger.critical(f"[Collection] FALHA AO SALVAR {user_id}: {e}")

# ==============================================================================
# 2. O WRAPPER DO TELEGRAM (MANTIDO E PROTEGIDO)
# ==============================================================================
async def finish_collection_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Job chamado pelo scheduler.
    """
    job = context.job
    if not job: return

    job_data = job.data or {}
    
    # --- RECUPERAÇÃO SEGURA DO ID ---
    raw_uid = job_data.get('user_id') or job.user_id
    user_id = str(raw_uid) # Garante String para Auth
    
    chat_id = job_data.get('chat_id') or job.chat_id
    
    # Injeção de Sessão
    if context.user_data is not None:
        context.user_data['logged_player_id'] = user_id
    
    msg_id = job_data.get('message_id')
    if not msg_id:
        try:
            pdata = await player_manager.get_player_data(user_id)
            if pdata:
                msg_id = pdata.get('player_state', {}).get('details', {}).get('collect_message_id')
        except: pass

    await execute_collection_logic(
        user_id=user_id,
        chat_id=chat_id,
        resource_id=job_data.get('resource_id'),
        item_id_yielded=job_data.get('item_id_yielded'),
        quantity_base=job_data.get('quantity', 1),
        context=context,
        message_id_to_delete=msg_id
    )