# modules/dungeons/runtime.py
# (VERSÃO FINAL: Conecta direto no Core/Users - Resolve o bug de 0 chaves)

from __future__ import annotations
import logging
import random
from typing import List, Dict, Any, Union, Optional

from bson import ObjectId
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest, Forbidden

# --- [CORREÇÃO] IMPORTS DIRETOS DO SISTEMA NOVO (Sem player_manager) ---
from modules.player.core import get_player_data, save_player_data
from modules.player.inventory import add_item_to_inventory, add_gold
from modules.player.stats import get_player_total_stats, check_and_apply_level_up
from modules.auth_utils import get_current_player_id
from modules import game_data
from modules.combat import durability

from handlers.utils import format_combat_message
from handlers.profile_handler import _get_class_media

from .config import DIFFICULTIES, DEFAULT_DIFFICULTY_ORDER, Difficulty
from .regions import REGIONAL_DUNGEONS, MobDef
from modules.dungeons.runtime_api import set_pending_battle

try:
    from modules import file_id_manager as media_ids
except Exception:
    media_ids = None

logger = logging.getLogger(__name__)
PlayerId = Union[ObjectId, str]


def _pid_to_str(pid: PlayerId) -> str:
    """
    Normaliza player_id para string canônica de ObjectId.
    Aceita ObjectId ou string válida de ObjectId.
    """
    if isinstance(pid, ObjectId):
        return str(pid)
    if isinstance(pid, str) and ObjectId.is_valid(pid.strip()):
        return str(ObjectId(pid.strip()))
    raise ValueError("player_id inválido (esperado ObjectId ou string de ObjectId).")


def _inv(p: dict) -> dict:
    inv = p.get("inventory") or p.get("inventario") or {}
    return inv if isinstance(inv, dict) else {}


# ============================================================
# 🛠️ HELPER: CONTAGEM INTELIGENTE DE CHAVES
# ============================================================
def _get_key_quantity(pdata: dict, key_item: str) -> int:
    """Retorna a quantidade de chaves, compatível com int e dict."""
    inv = _inv(pdata)
    item_data = inv.get(key_item)

    if not item_data:
        return 0

    # Se for Dicionário (Sistema Novo: {"quantity": 5, ...})
    if isinstance(item_data, dict):
        return int(item_data.get("quantity", 1))

    # Se for Inteiro (Sistema Antigo: 5)
    try:
        return int(item_data)
    except:
        return 0


def _consume_keys(pdata: dict, key_item: str, key_cost: int) -> bool:
    """Consome a chave do inventário."""
    inv = _inv(pdata)
    current_qty = _get_key_quantity(pdata, key_item)

    if current_qty < key_cost:
        return False

    # Realiza a subtração
    item_data = inv.get(key_item)

    if isinstance(item_data, dict):
        new_qty = current_qty - key_cost
        if new_qty <= 0:
            inv.pop(key_item, None)
        else:
            item_data["quantity"] = new_qty
            inv[key_item] = item_data
    else:
        # Lógica Int
        inv[key_item] = current_qty - key_cost
        if inv[key_item] <= 0:
            inv.pop(key_item, None)

    pdata["inventory"] = inv
    return True


def _load_region_dungeon(region_key: str) -> dict:
    d = REGIONAL_DUNGEONS.get(region_key)
    if not d:
        raise RuntimeError(f"Calabouço '{region_key}' não encontrado.")
    return d


def _final_gold_for(dungeon_cfg: dict, difficulty_cfg: Difficulty) -> int:
    try:
        base = int(dungeon_cfg.get("gold_base", 0))
        return int(round(base * float(difficulty_cfg.gold_mult)))
    except:
        return 0


def _key_cost_for(difficulty_cfg: Difficulty) -> int:
    return difficulty_cfg.key_cost


def _key_item_for(dungeon_cfg: dict) -> str:
    return str(dungeon_cfg.get("key_item") or "cristal_de_abertura")


# ============================================================
# 🛠️ CACHE BRIDGE
# ============================================================
async def _update_battle_cache(
    context: ContextTypes.DEFAULT_TYPE,
    player_id: PlayerId,
    pdata: dict,
    combat_details: dict,
    message_id: int = None,
    chat_id: int = None
):
    # Normaliza para string canônica para cache/keys
    try:
        pid_str = _pid_to_str(player_id)
    except Exception:
        # Se falhar, guarda algo para diagnóstico, mas evita quebrar runtime
        pid_str = str(player_id)

    # Usa a função importada diretamente de stats.py
    p_stats = await get_player_total_stats(pdata)

    monster_stats = {
        "name": combat_details.get("monster_name", "Inimigo"),
        "hp": combat_details.get("monster_hp", 100),
        "max_hp": combat_details.get("monster_max_hp", 100),
        "attack": combat_details.get("monster_attack", 10),
        "defense": combat_details.get("monster_defense", 0),
        "initiative": combat_details.get("monster_initiative", 0),
        "luck": combat_details.get("monster_luck", 0),
        "xp_reward": combat_details.get("monster_xp_reward", 0),
        "gold_drop": combat_details.get("monster_gold_drop", 0),
        "loot_table": combat_details.get("loot_table", []),
        "id": combat_details.get("id"),
        "flee_bias": combat_details.get("flee_bias", 0.0),
    }

    p_media = _get_class_media(pdata, purpose="combate")
    player_name_fixed = pdata.get("character_name", "Herói")

    cache = {
        "player_id": pid_str,
        "chat_id": chat_id,
        "message_id": message_id,
        "player_name": player_name_fixed,
        "player_stats": p_stats,
        "monster_stats": monster_stats,
        "player_hp": pdata.get("current_hp"),
        "player_mp": pdata.get("current_mp"),
        "battle_log": combat_details.get("battle_log", []),
        "turn": "player",
        "region_key": combat_details.get("region_key"),
        "player_media_id": p_media.get("id") if p_media else None,
        "player_media_type": p_media.get("type", "photo") if p_media else "photo",
        "monster_media_id": combat_details.get("file_id_name"),
        "monster_media_type": "photo",
        "dungeon_ctx": combat_details.get("dungeon_ctx"),
        "skill_cooldowns": combat_details.get("skill_cooldowns", pdata.get("cooldowns", {})),
    }

    context.user_data["battle_cache"] = cache

    # runtime_api: mantenha chave estável (string ObjectId) quando possível
    try:
        set_pending_battle(pid_str, combat_details.get("dungeon_ctx"))
    except Exception:
        # não derruba o combate por falha de cache externo
        pass


async def _send_battle_media(context, chat_id, caption, file_id_name, reply_markup=None) -> int | None:
    fd = None
    if media_ids and hasattr(media_ids, "get_file_data") and file_id_name:
        try:
            fd = media_ids.get_file_data(file_id_name)
        except:
            pass
    try:
        if fd and fd.get("id"):
            mtype = (fd.get("type") or "photo").lower()
            if mtype == "video":
                sent_msg = await context.bot.send_video(
                    chat_id=chat_id,
                    video=fd["id"],
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
            else:
                sent_msg = await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=fd["id"],
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
            return sent_msg.message_id
    except:
        pass
    try:
        sent_msg = await context.bot.send_message(
            chat_id=chat_id, text=caption, parse_mode="HTML", reply_markup=reply_markup
        )
        return sent_msg.message_id
    except:
        return None


# ============================================================
# 🖥️ MENU DO CALABOUÇO (AGORA LÊ AS CHAVES CORRETAMENTE)
# ============================================================
async def _open_menu(update, context, region_key):
    q = update.callback_query
    if q:
        try:
            await q.answer()
        except:
            pass

    try:
        dungeon = _load_region_dungeon(region_key)
    except:
        await context.bot.send_message(update.effective_chat.id, "Erro no calabouço.")
        return

    key_item = _key_item_for(dungeon)

    # 1. Pega ID da Sessão (Seguro)
    player_id = get_current_player_id(update, context)

    # 2. Busca dados direto do Core (Blindado contra sistema antigo)
    pdata = await get_player_data(player_id) or {}

    # 3. Usa o helper inteligente para ler a quantidade
    have = _get_key_quantity(pdata, key_item)

    caption = (
        f"<b>{dungeon.get('label','Calabouço')}</b>\n"
        f"Região: <code>{region_key}</code>\n\n"
        f"🎒 Chaves: <b>{have}</b>\n\n"
        f"Escolha:"
    )

    kb = []
    d_prog = (pdata.get("dungeon_progress", {}) or {}).get(region_key, {})
    high = d_prog.get("highest_completed")
    h_idx = -1

    if high in DEFAULT_DIFFICULTY_ORDER:
        h_idx = DEFAULT_DIFFICULTY_ORDER.index(high)

    for i, diff_key in enumerate(DEFAULT_DIFFICULTY_ORDER):
        meta = DIFFICULTIES.get(diff_key)
        if not meta:
            continue

        if i <= h_idx + 1:
            kb.append(
                [
                    InlineKeyboardButton(
                        f"{meta.emoji} {meta.label}",
                        callback_data=f"dungeon_pick:{diff_key}:{region_key}",
                    )
                ]
            )
        else:
            kb.append([InlineKeyboardButton(f"🔒 {meta.label}", callback_data="dungeon_locked")])

    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="combat_return_to_map")])

    await _send_battle_media(
        context,
        update.effective_chat.id,
        caption,
        dungeon.get("menu_media_key"),
        InlineKeyboardMarkup(kb),
    )


# ============================================================
# Construção de Combate
# ============================================================
def _new_run_state(region_key: str, difficulty: str) -> dict:
    return {
        "action": "dungeon_run",
        "details": {"region_key": region_key, "difficulty": difficulty, "dungeon_stage": 0, "last_fight_rewards": {}},
    }


def _build_combat_details(
    floor_mob: MobDef,
    difficulty_cfg: Difficulty,
    region_key: str,
    stage: int,
    active_cooldowns: dict = None,
) -> dict:
    base_stats = floor_mob.stats_base
    stat_mult = difficulty_cfg.stat_mult
    gold_mult = difficulty_cfg.gold_mult
    hp = int(round(base_stats.get("max_hp", 50) * stat_mult))

    mob_name = floor_mob.display
    if mob_name.lower().startswith(("o ", "a ", "os ", "as ")):
        intro_text = f"𝗩𝗼𝗰𝗲̂ 𝗮𝘃𝗮𝗻𝗰̧𝗮! {mob_name} 𝗯𝗹𝗼𝗾𝘂𝗲𝗶𝗮 𝘀𝗲𝘂 𝗰𝗮𝗺𝗶𝗻𝗵𝗼!"
    else:
        intro_text = f"𝗩𝗼𝗰𝗲̂ 𝗮𝘃𝗮𝗻𝗰̧𝗮! 𝗨𝗺 {mob_name} \n𝗮𝗽𝗮𝗿𝗲𝗰𝗲 𝗱𝗮𝘀 𝘀𝗼𝗺𝗯𝗿𝗮𝘀!"

    processed_cooldowns = {}
    if active_cooldowns:
        for skill_id, turns in active_cooldowns.items():
            if turns > 0:
                processed_cooldowns[skill_id] = turns

    return {
        "monster_name": f"{floor_mob.emoji} {floor_mob.display}",
        "monster_hp": hp,
        "monster_max_hp": hp,
        "monster_attack": int(round(base_stats.get("attack", 5) * stat_mult)),
        "monster_defense": int(round(base_stats.get("defense", 0) * stat_mult)),
        "monster_initiative": int(round(base_stats.get("initiative", 5) * stat_mult)),
        "monster_luck": base_stats.get("luck", 5),
        "monster_xp_reward": int(round(base_stats.get("xp_reward", 20) * stat_mult)),
        "monster_gold_drop": int(round(base_stats.get("gold_drop", 10) * gold_mult)),
        "loot_table": list(base_stats.get("loot_table", [])),
        "flee_bias": float(base_stats.get("flee_bias", 0.0)),
        "dungeon_ctx": {
            "dungeon_id": region_key,
            "floor_idx": stage,
            "difficulty": difficulty_cfg.key,
            "region": region_key,
        },
        "battle_log": [intro_text],
        "id": floor_mob.key,
        "file_id_name": floor_mob.media_key,
        "is_boss": bool(base_stats.get("is_boss", False)),
        "region_key": region_key,
        "difficulty": difficulty_cfg.key,
        "dungeon_stage": stage,
        "skill_cooldowns": processed_cooldowns,
    }


async def _start_first_fight(update, context, region_key, difficulty_key):
    player_id = get_current_player_id(update, context)
    chat_id = update.effective_chat.id

    try:
        dungeon = _load_region_dungeon(region_key)
    except:
        return

    diff_cfg = DIFFICULTIES.get(difficulty_key)
    key_item = _key_item_for(dungeon)
    key_cost = _key_cost_for(diff_cfg)

    # Busca Direta
    pdata = await get_player_data(player_id) or {}

    # Verifica Chave
    if not _consume_keys(pdata, key_item, key_cost):
        await context.bot.send_message(
            chat_id,
            f"🔒 <b>Acesso Negado</b>\nVocê precisa de {key_cost}x <b>{key_item.replace('_', ' ').title()}</b>.",
            parse_mode="HTML",
        )
        return

    floors = list(dungeon.get("floors") or [])
    if not floors:
        return

    state = _new_run_state(region_key, difficulty_key)
    current_cooldowns = pdata.get("cooldowns", {})
    combat = _build_combat_details(floors[0], diff_cfg, region_key, 0, active_cooldowns=current_cooldowns)

    state["action"] = "in_combat"
    state["details"] = combat
    pdata["player_state"] = state

    # Salva Direto
    await save_player_data(player_id, pdata)

    caption = await format_combat_message(pdata)
    kb = [
        [
            InlineKeyboardButton("⚔️ 𝐀𝐭𝐚𝐜𝐚𝐫", callback_data="combat_attack"),
            InlineKeyboardButton("✨ 𝙎𝙠𝙞𝙡𝙡𝙨", callback_data="combat_skill_menu"),
        ],
        [
            InlineKeyboardButton("🧪 𝙋𝙤𝙘̧𝗼̃𝗲𝘀", callback_data="combat_potion_menu"),
            InlineKeyboardButton("🏃 𝐅𝐮𝐠𝐢𝙧", callback_data="combat_flee"),
        ],
    ]
    msg_id = await _send_battle_media(context, chat_id, caption, combat.get("file_id_name"), InlineKeyboardMarkup(kb))
    await _update_battle_cache(context, player_id, pdata, combat, message_id=msg_id, chat_id=chat_id)


# ============================================================
# Avanço Pós-Combate
# ============================================================
async def resume_dungeon_after_battle(context, player_id, dungeon_ctx, victory):
    cache = context.user_data.get("battle_cache") or {}
    final_hp = cache.get("player_hp")
    final_mp = cache.get("player_mp")

    await advance_after_victory(
        None,
        context,
        player_id,
        player_id,
        dungeon_ctx,
        {},
        current_hp=final_hp,
        current_mp=final_mp,
        current_cds=None,
    )


async def fail_dungeon_run(update, context, player_id, chat_id, reason):
    await _delete_previous_battle_msg(context, player_id)
    # Busca Direta
    pdata = await get_player_data(player_id)
    if pdata:
        stats = await get_player_total_stats(pdata)
        pdata["current_hp"] = stats.get("max_hp", 50)
        pdata["current_mp"] = stats.get("max_mana", 10)
        pdata["player_state"] = {"action": "idle"}

        cache = context.user_data.get("battle_cache") or {}
        if cache.get("region_key"):
            pdata["location"] = cache.get("region_key")

        await save_player_data(player_id, pdata)

    await _send_battle_media(
        context,
        chat_id,
        f"💀 𝗙𝗶𝗺 𝗱𝗮 𝗟𝗶𝗻𝗵𝗮\n{reason}.",
        "media_dungeon_defeat",
        InlineKeyboardMarkup([[InlineKeyboardButton("⚰️ 𝙎𝙖𝙞𝙧", callback_data="combat_return_to_map")]]),
    )


async def advance_after_victory(update, context, player_id, chat_id, combat_details, rewards, current_hp=None, current_mp=None, current_cds=None):
    if context and context.user_data.get("battle_cache"):
        cache = context.user_data["battle_cache"]
        if current_hp is None:
            current_hp = cache.get("player_hp")
        if current_mp is None:
            current_mp = cache.get("player_mp")

    # Busca Direta
    pdata = await get_player_data(player_id) or {}
    run = pdata.get("player_state") or {}

    if current_hp is not None:
        pdata["current_hp"] = int(current_hp)
    if current_mp is not None:
        pdata["current_mp"] = int(current_mp)

    xp, gold, items = rewards.get("xp", 0), rewards.get("gold", 0), rewards.get("items", [])
    pdata["xp"] = int(pdata.get("xp", 0)) + xp

    levelup_text = ""
    try:
        # Usa função importada de stats.py
        lvls, pts, msg = check_and_apply_level_up(pdata)
        if lvls > 0:
            stats = await get_player_total_stats(pdata)
            pdata["current_hp"] = stats.get("max_hp", 100)
            pdata["current_mp"] = stats.get("max_mana", 50)
            levelup_text = f"\n\n🆙 <b>LEVEL UP!</b>\n{msg}"
    except Exception as e:
        print(f"Erro no level up: {e}")

    if gold > 0:
        add_gold(pdata, gold)
    for i, q, _ in items:
        add_item_to_inventory(pdata, i, q)

    reg_key = str(combat_details.get("region_key"))
    diff_key = str(combat_details.get("difficulty"))
    try:
        dungeon = _load_region_dungeon(reg_key)
        diff_cfg = DIFFICULTIES.get(diff_key)
    except:
        return

    floors = list(dungeon.get("floors") or [])
    cur_stg = int(combat_details.get("dungeon_stage", 0))
    next_stg = cur_stg + 1

    dummy_log = []
    active_cds = pdata.get("cooldowns", {})

    # --- VITÓRIA FINAL ---
    if next_stg >= len(floors):
        await _delete_previous_battle_msg(context, player_id)
        pdata.setdefault("dungeon_progress", {}).setdefault(reg_key, {})
        pdata["dungeon_progress"][reg_key]["highest_completed"] = diff_key
        bonus = _final_gold_for(dungeon, diff_cfg)
        if bonus > 0:
            add_gold(pdata, bonus)

        durability.apply_end_of_battle_wear(pdata, {}, dummy_log)

        stats = await get_player_total_stats(pdata)
        pdata["current_hp"] = stats.get("max_hp", 50)
        pdata["current_mp"] = stats.get("max_mana", 10)
        pdata["player_state"] = {"action": "idle"}
        pdata["location"] = reg_key

        if "cooldowns" in pdata:
            pdata.pop("cooldowns", None)

        await save_player_data(player_id, pdata)

        summ = f"🏆 <b>CALABOUÇO CONCLUÍDO!</b>\n\n✨ <b>XP Ganho:</b> {xp}\n💰 <b>Bônus Ouro:</b> {bonus}"
        summ += levelup_text

        if items:
            loot_lines = []
            for i, q, _ in items:
                info = (game_data.ITEMS_DATA or {}).get(i, {})
                name = info.get("display_name") or i.replace("_", " ").title()
                emoji = info.get("emoji", "")
                loot_lines.append(f"• {q}x {emoji} {name}")
            summ += "\n\n🎒 <b>Loot Final:</b>\n" + "\n".join(loot_lines)

        await _send_battle_media(
            context,
            chat_id,
            summ,
            "media_dungeon_victory",
            InlineKeyboardMarkup([[InlineKeyboardButton("🎉 Continuar", callback_data="combat_return_to_map")]]),
        )
        return

    try:
        next_mob = floors[next_stg]
    except:
        return

    durability.apply_end_of_battle_wear(pdata, {}, dummy_log)

    combat = _build_combat_details(next_mob, diff_cfg, reg_key, next_stg, active_cooldowns=active_cds)

    run["action"] = "in_combat"
    run["details"] = combat
    pdata["player_state"] = run

    await save_player_data(player_id, pdata)

    caption = await format_combat_message(pdata)
    kb = [
        [
            InlineKeyboardButton("⚔️ 𝐀𝐭𝐚𝐜𝐚𝐫", callback_data="combat_attack"),
            InlineKeyboardButton("✨ 𝙎𝙠𝙞𝙡𝙡𝙨", callback_data="combat_skill_menu"),
        ],
        [
            InlineKeyboardButton("🧪 𝙋𝙤𝙘̧𝗼̃𝗲𝘀", callback_data="combat_potion_menu"),
            InlineKeyboardButton("🏃 𝐅𝐮𝐠𝐢𝙧", callback_data="combat_flee"),
        ],
    ]

    await _delete_previous_battle_msg(context, player_id)
    if levelup_text:
        await context.bot.send_message(
            chat_id,
            "🆙 𝙑𝙤𝙘𝙚̂ 𝙨𝙪𝙗𝙞𝙪 𝙙𝙚 𝙣𝙞́𝙫𝙚𝙡 𝙙𝙪𝙧𝙖𝙣𝙩𝙚 𝙖 𝙢𝙖𝙨𝙢𝙤𝙧𝙧𝙖!\n𝙎𝙪𝙖𝙨 𝙚𝙣𝙚𝙧𝙜𝙞𝙖𝙨 𝙛𝙤𝙧𝙖𝙢 𝙧𝙚𝙨𝙩𝙖𝙪𝙧𝙖𝙙𝙖𝙨!",
            parse_mode="HTML",
        )

    msg_id = await _send_battle_media(context, chat_id, caption, combat.get("file_id_name"), InlineKeyboardMarkup(kb))
    await _update_battle_cache(context, player_id, pdata, combat, message_id=msg_id, chat_id=chat_id)


async def _open_menu_cb(update, context):
    await _open_menu(update, context, update.callback_query.data.split(":")[1])


async def _pick_diff_cb(update, context):
    d = update.callback_query.data.split(":")
    try:
        await update.callback_query.message.delete()
    except:
        pass
    await _start_first_fight(update, context, d[2], d[1])


async def _dungeon_locked_cb(update, context):
    await update.callback_query.answer("Trancado!", show_alert=True)


async def _delete_previous_battle_msg(context: ContextTypes.DEFAULT_TYPE, player_id: PlayerId):
    cache = context.user_data.get("battle_cache")
    if not cache:
        return

    try:
        pid_str = _pid_to_str(player_id)
    except Exception:
        pid_str = str(player_id)

    if cache.get("player_id") == pid_str:
        chat_id = cache.get("chat_id")
        msg_id = cache.get("message_id")
        if chat_id and msg_id:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except Exception:
                pass


dungeon_open_handler = CallbackQueryHandler(_open_menu_cb, pattern=r"^dungeon_open:[A-Za-z0-9_]+$")
dungeon_pick_handler = CallbackQueryHandler(_pick_diff_cb, pattern=r"^dungeon_pick:[A-Za-z0-9_]+:[A-Za-z0-9_]+$")
dungeon_locked_handler = CallbackQueryHandler(_dungeon_locked_cb, pattern=r"^dungeon_locked$")
