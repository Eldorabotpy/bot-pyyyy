# modules/dungeons/runtime.py
from __future__ import annotations
import logging
from typing import List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest
from modules import player_manager, game_data, clan_manager
from modules import player_manager, game_data
from handlers.utils import format_combat_message
from .config import DIFFICULTIES, DEFAULT_DIFFICULTY_ORDER

# 🔎 Mídias (batalha). Suporta tanto file_id_manager quanto file_ids.
try:
    from modules import file_id_manager as media_ids
except Exception:
    media_ids = None

logger = logging.getLogger(__name__)


# ============================================================
# Helpers de inventário
# ============================================================
def _inv(p: dict) -> dict:
    inv = p.get("inventory") or p.get("inventario") or {}
    return inv if isinstance(inv, dict) else {}

def _has_key(pdata: dict, key_item: str) -> bool:
    try:
        return int(_inv(pdata).get(key_item, 0)) > 0
    except Exception:
        return False

def _consume_key(pdata: dict, key_item: str) -> bool:
    inv = _inv(pdata)
    try:
        cur = int(inv.get(key_item, 0))
    except Exception:
        cur = 0
    if cur <= 0:
        return False
    inv[key_item] = cur - 1
    pdata["inventory"] = inv
    return True

# ============================================================
# Registry loader
# ============================================================
def _load_region_dungeon(region_key: str) -> dict:
    try:
        from modules.dungeons.registry import get_dungeon_for_region  # type: ignore
    except Exception as e:
        raise RuntimeError("registry_missing") from e

    d = get_dungeon_for_region(region_key)
    if not d:
        raise RuntimeError("dungeon_not_found")
    return d

def _scale_floor(stats: dict, scale: float) -> dict:
    def gi(k, default):
        try:
            return int(stats.get(k, default))
        except Exception:
            return default
    out = dict(stats)
    out["hp"]         = max(1, int(round(gi("hp", 10) * scale)))
    out["attack"]     = max(1, int(round(gi("attack", gi("atk", 5)) * scale)))
    out["defense"]    = max(0, int(round(gi("defense", gi("def", 2)) * scale)))
    out["initiative"] = max(1, int(round(gi("initiative", gi("ini", 5)) * scale)))
    out["luck"]       = gi("luck", 5)
    return out

def _difficulty_scale(dungeon_cfg: dict, diff: str) -> float:
    ds = (dungeon_cfg.get("difficulty_scale") or {})
    if diff in ds:
        try:
            return float(ds[diff])
        except Exception:
            pass
    return {"iniciante": 1.9, "infernal": 4.0, "pesadelo": 5.25}.get(diff, 1.0)

def _final_gold_for(dungeon_cfg: dict, diff: str) -> int:
    fg = (dungeon_cfg.get("final_gold") or {})
    if diff in fg:
        try:
            return int(fg[diff])
        except Exception:
            pass
    return {"facil": 400, "normal": 800, "infernal": 1800}.get(diff, 0)

def _key_item_for(dungeon_cfg: dict) -> str:
    return str(dungeon_cfg.get("key_item") or "cristal_de_abertura")

# ============================================================
# Botão para o menu da região
# ============================================================
def build_region_dungeon_button(region_key: str) -> InlineKeyboardButton:
    return InlineKeyboardButton("🏰 𝐂𝐚𝐥𝐚𝐛𝐨𝐮𝐜̧𝐨 🏰", callback_data=f"dungeon_open:{region_key}")

# ============================================================
# Envio da mídia de batalha (vídeo/foto) com caption + botões
# ============================================================
async def _send_battle_media(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    caption: str,
    file_id_name: str | None,
    reply_markup: InlineKeyboardMarkup | None = None,
):
    """
    Tenta enviar vídeo/foto com base em file_id_name.
    Se não achar mídia, envia texto — SEMPRE com reply_markup quando fornecido.
    """
    fd = None
    if media_ids and hasattr(media_ids, "get_file_data") and file_id_name:
        try:
            fd = media_ids.get_file_data(file_id_name)
        except Exception as e:
            logger.debug("get_file_data(%s) falhou: %s", file_id_name, e)

    if fd and fd.get("id"):
        try:
            media_type = (fd.get("type") or "photo").lower()
            if media_type == "video":
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=fd["id"],
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
            else:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=fd["id"],
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
            return
        except Exception as e:
            logger.debug("Falha ao enviar mídia de batalha (%s - %s). Caindo para texto.", file_id_name, e)

    # fallback: texto
    await context.bot.send_message(
        chat_id=chat_id,
        text=caption,
        parse_mode="HTML",
        reply_markup=reply_markup,
    )

# ============================================================
# UI: abrir menu de dificuldade
# ============================================================
async def _open_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, region_key: str):
    q = update.callback_query
    if q:
        try:
            await q.answer()
        except BadRequest:
            pass

    chat_id = update.effective_chat.id

    try:
        dungeon = _load_region_dungeon(region_key)
    except RuntimeError as e:
        msg = "Calabouço desta região não está configurado." if str(e) == "dungeon_not_found" else "Sistema de calabouços não instalado (registry)."
        await context.bot.send_message(chat_id=chat_id, text=msg)
        return

    key_item = _key_item_for(dungeon)
    key_obj = (game_data.ITEMS_DATA or {}).get(key_item, {})
    key_name = f"{key_obj.get('emoji','🔹')} {key_obj.get('display_name', key_item)}"

    pdata = player_manager.get_player_data(update.effective_user.id) or {}
    have = int((_inv(pdata)).get(key_item, 0))

    caption = (
        f"<b>{dungeon.get('display_name','Calabouço')}</b>\n"
        f"Região: <code>{region_key}</code>\n\n"
        f"🔑 Chave necessária: <b>1× {key_name}</b> — Você tem: <b>{have}</b>\n\n"
        f"Escolha a dificuldade:"
    )

    # --- Lógica de Desbloqueio de Dificuldade ---
    kb = []
    dungeon_progress = (pdata.get("dungeon_progress", {}) or {}).get(region_key, {})
    highest_completed = dungeon_progress.get("highest_completed")
    highest_completed_index = -1
    
    if highest_completed:
        try:
            # Encontra o índice da dificuldade mais alta que o jogador já completou
            # Ex: 'iniciante' é 0, 'veterano' é 1, etc.
            highest_completed_index = DEFAULT_DIFFICULTY_ORDER.index(highest_completed)
        except (ValueError, TypeError):
            pass # Se o valor guardado for inválido, ignora

    # Percorre as dificuldades na ordem correta (iniciante -> veterano -> etc.)
    for i, diff_key in enumerate(DEFAULT_DIFFICULTY_ORDER):
        # Pega nos metadados da dificuldade do seu config.py
        meta = DIFFICULTIES.get(diff_key)
        if not meta: continue

        # A dificuldade está desbloqueada se o seu índice for menor ou igual
        # ao da última completada + 1. A primeira (índice 0) está sempre desbloqueada.
        if i <= highest_completed_index + 1:
            # Botão para dificuldade desbloqueada
            kb.append([
                InlineKeyboardButton(
                    f"{meta.emoji} {meta.label}", 
                    callback_data=f"dungeon_pick:{diff_key}:{region_key}"
                )
            ])
        else:
            # Botão para dificuldade bloqueada
            kb.append([
                InlineKeyboardButton(
                    f"🔒 {meta.label}", 
                    callback_data="dungeon_locked"
                )
            ])

    kb.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="continue_after_action")])

    try:
        # Tenta editar a mensagem existente
        await q.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    except Exception:
        # Se falhar (ex: a mensagem foi apagada), envia uma nova
        await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

  
# ============================================================
# Fluxo de run
# ============================================================
def _new_run_state(region_key: str, difficulty: str) -> dict:
    return {
        "action": "dungeon_run",
        "details": {
            "region_key": region_key,
            "difficulty": difficulty,
            "dungeon_stage": 0,
            # O nosso "saco de loot temporário" começa vazio
            "accumulated_rewards": {
                "xp": 0,
                "gold": 0,
                "items": []
            }
        }
    }
def _build_combat_details(floor: dict, region_key: str, difficulty: str, stage: int) -> dict:
    name  = floor.get("name") or floor.get("display") or str(floor.get("id") or "Inimigo")
    emoji = floor.get("emoji", "")
    return {
        "monster_name": f"{emoji} {name}".strip(),
        "monster_hp": int(floor.get("hp", 0)),
        "monster_max_hp": int(floor.get("hp", 0)),
        "monster_attack": int(floor.get("attack", 0)),
        "monster_defense": int(floor.get("defense", 0)),
        "monster_initiative": int(floor.get("initiative", 0)),
        "monster_luck": int(floor.get("luck", 0)),
        "monster_xp_reward": int(floor.get("xp_reward", 10)),
        "monster_gold_drop": int(floor.get("gold_drop", 5)),
        "loot_table": list(floor.get("loot_table") or []),
        "battle_log": [f"Você avança no calabouço ({difficulty})."],
        "region_key": region_key, "difficulty": difficulty, "dungeon_ctx": True,
        "dungeon_stage": stage, "file_id_name": floor.get("file_id_name"),
        "is_boss": bool(floor.get("is_boss")),
    }

async def _start_first_fight(update: Update, context: ContextTypes.DEFAULT_TYPE, region_key: str, difficulty: str):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    dungeon = _load_region_dungeon(region_key)
    key_item = _key_item_for(dungeon)

    pdata = player_manager.get_player_data(user_id) or {}

    # chave
    if not _has_key(pdata, key_item) or not _consume_key(pdata, key_item):
        try:
            await context.bot.answer_callback_query(update.callback_query.id, text="Você precisa de 1× chave para entrar.", show_alert=True)
        except Exception:
            await context.bot.send_message(chat_id=chat_id, text="Você precisa de 1× chave para entrar.")
        return

    floors: List[dict] = list(dungeon.get("floors") or [])
    if not floors:
        await context.bot.send_message(chat_id=chat_id, text="Este calabouço não tem andares configurados.")
        return

    scale = _difficulty_scale(dungeon, difficulty)
    lineup = [_scale_floor(f, scale) for f in floors]

    # salvar consumo da chave
    player_manager.save_player_data(user_id, pdata)

    # estado inicial + primeiro combate
    state = _new_run_state(region_key, difficulty)
    combat = _build_combat_details(lineup[0], region_key, difficulty, 0)
    state["action"] = "in_combat"
    state["details"] = combat
    pdata["player_state"] = state
    player_manager.save_player_data(user_id, pdata)

    caption = format_combat_message(pdata)
    kb = [[InlineKeyboardButton("⚔️ 𝐀𝐭𝐚𝐜𝐚𝐫", callback_data="combat_attack"),
           InlineKeyboardButton("🏃 𝐅𝐮𝐠𝐢𝐫",   callback_data="combat_flee")]]
    await _send_battle_media(context, chat_id, caption, combat.get("file_id_name"), reply_markup=InlineKeyboardMarkup(kb))

async def fail_dungeon_run(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, reason: str):
    """
    Função chamada quando o jogador falha um calabouço (derrotado ou foge).
    """
    from handlers.menu.region import send_region_menu

    player_data = player_manager.get_player_data(user_id)
    if not player_data: return

    # Restaura a vida do jogador para o máximo
    total_stats = player_manager.get_player_total_stats(player_data)
    player_data['current_hp'] = total_stats.get('max_hp', 50)
    
    # Limpa o estado do jogador para "idle"
    player_data['player_state'] = {'action': 'idle'}
    player_manager.save_player_data(user_id, player_data)
    
    # Envia a mensagem de falha e o botão para continuar
    summary_text = f"❌ **Você falhou no calabouço!**\n\nMotivo: {reason}."
    keyboard = [[InlineKeyboardButton("➡️ Continuar", callback_data="continue_after_action")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=chat_id, text=summary_text,
        parse_mode="HTML", reply_markup=reply_markup
    )

async def advance_after_victory(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, combat_details: dict, rewards_to_accumulate: dict):
    pdata = player_manager.get_player_data(user_id) or {}
    clan_id = pdata.get("clan_id")

    # =========================================================
    # INTEGRAÇÃO 1: MISSÃO DE MATAR CHEFE
    # =========================================================
    if clan_id and combat_details.get("is_boss"):
        await clan_manager.update_guild_mission_progress(
            clan_id=clan_id,
            mission_type='DUNGEON_BOSS_KILL',
            details={'count': 1},
            context=context
        )
        
    # =========================================================

    run = pdata.get("player_state") or {}
    det = (run.get("details") or {})

    # Acumula as recompensas da batalha que acabámos de vencer
    current_rewards = det.get("accumulated_rewards", {"xp": 0, "gold": 0, "items": []})
    current_rewards["xp"] += rewards_to_accumulate.get("xp", 0)
    current_rewards["gold"] += rewards_to_accumulate.get("gold", 0)
    current_rewards["items"].extend(rewards_to_accumulate.get("items", []))
    det["accumulated_rewards"] = current_rewards

    region_key = str(det.get("region_key") or combat_details.get("region_key") or "")
    difficulty = str(det.get("difficulty") or combat_details.get("difficulty") or "normal")

    try:
        dungeon = _load_region_dungeon(region_key)
    except Exception:
        pdata["player_state"] = {"action": "idle"}
        player_manager.save_player_data(user_id, pdata)
        await context.bot.send_message(chat_id=chat_id, text="Calabouço foi encerrado.")
        return

    floors: List[dict] = list(dungeon.get("floors") or [])
    if not floors:
        pdata["player_state"] = {"action": "idle"}
        player_manager.save_player_data(user_id, pdata)
        await context.bot.send_message(chat_id=chat_id, text="Calabouço sem andares. Encerrado.")
        return

    scale = _difficulty_scale(dungeon, difficulty)
    lineup = [_scale_floor(f, scale) for f in floors]
    cur_stage = int(det.get("dungeon_stage", 0))
    next_stage = cur_stage + 1
    det["dungeon_stage"] = next_stage # Atualiza o piso atual

    # Verificação de Vitória Final
    if next_stage >= len(lineup):
        # =========================================================
        # INTEGRAÇÃO 2: MISSÃO DE COMPLETAR CALABOUÇO
        # =========================================================
        if clan_id:
            await clan_manager.update_guild_mission_progress(
                clan_id=clan_id,
                mission_type='DUNGEON_COMPLETE',
                details={
                    'dungeon_id': region_key,
                    'difficulty': difficulty,
                    'count': 1
                },
                context=context
            )
        # =========================================================

        # ATUALIZAÇÃO DO PROGRESSO DE DIFICULDADE DO JOGADOR
        completed_diff_key = difficulty
        pdata.setdefault("dungeon_progress", {}).setdefault(region_key, {})
        
        current_highest_key = pdata["dungeon_progress"][region_key].get("highest_completed")

        try:
            completed_index = DEFAULT_DIFFICULTY_ORDER.index(completed_diff_key)
            current_highest_index = -1
            if current_highest_key:
                current_highest_index = DEFAULT_DIFFICULTY_ORDER.index(current_highest_key)

            if completed_index > current_highest_index:
                pdata["dungeon_progress"][region_key]["highest_completed"] = completed_diff_key
                logger.info(f"PROGRESSO DO CALABOUÇO ATUALIZADO para user {user_id} em '{region_key}': {completed_diff_key}")

        except (ValueError, TypeError):
            logger.warning(f"Chave de dificuldade inválida durante a atualização de progresso: atual='{current_highest_key}', completada='{completed_diff_key}'")

        # O jogador venceu o último piso! Entregamos tudo do "saco de loot".
        final_rewards = det.get("accumulated_rewards", {})
        final_xp = final_rewards.get("xp", 0)
        final_gold = final_rewards.get("gold", 0) + _final_gold_for(dungeon, difficulty)
        final_items = final_rewards.get("items", [])

        pdata['xp'] = int(pdata.get('xp', 0)) + final_xp
        if final_gold > 0:
            player_manager.add_gold(pdata, final_gold)

        looted_items_text = ""
        if final_items:
            for item_id in final_items:
                player_manager.add_item_to_inventory(pdata, item_id, 1)

            from collections import Counter
            item_names = [(game_data.ITEMS_DATA.get(item_id, {}) or {}).get('display_name', item_id) for item_id in final_items]
            looted_items_text = "\n\n<b>Tesouros Adquiridos:</b>\n"
            for name, count in Counter(item_names).items():
                looted_items_text += f"- {count}x {name}\n"

        pdata["player_state"] = {"action": "idle"}
        player_manager.save_player_data(user_id, pdata)

        summary_text = (
            f"🏆 <b>Calabouço Concluído!</b> 🏆\n\n"
            f"Você superou todos os desafios e reclamou suas recompensas:\n"
            f"+{final_xp:,} XP\n"
            f"+{final_gold:,} Ouro"
            f"{looted_items_text}"
        )
        
        keyboard = [[
            InlineKeyboardButton("➡️ 𝐂𝐨𝐧𝐭𝐢𝐧𝐮𝐚𝐫", callback_data="continue_after_action")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=chat_id,
            text=summary_text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        return

    # Se não for o último piso, continua para o próximo combate
    combat = _build_combat_details(lineup[next_stage], region_key, difficulty, next_stage)
    run["action"] = "in_combat"
    run["details"] = combat
    pdata["player_state"] = run
    player_manager.save_player_data(user_id, pdata)

    caption = format_combat_message(pdata)
    kb = [[InlineKeyboardButton("⚔️ 𝐀𝐭𝐚𝐜𝐚𝐫", callback_data="combat_attack"),
           InlineKeyboardButton("🏃 𝐅𝐮𝐠𝐢𝐫",   callback_data="combat_flee")]]
    await _send_battle_media(context, chat_id, caption, combat.get("file_id_name"), reply_markup=InlineKeyboardMarkup(kb))

# ============================================================
async def _open_menu_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    _, region_key = data.split(":", 1)
    await _open_menu(update, context, region_key)

async def _pick_diff_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # pattern: dungeon_pick:<diff>:<region_key>
    data = update.callback_query.data
    parts = data.split(":")
    if len(parts) != 3:
        await update.callback_query.answer("Escolha inválida.", show_alert=True)
        return
    _, diff, region_key = parts
    if diff not in DIFFICULTIES:
        await update.callback_query.answer("Dificuldade inválida.", show_alert=True)
        return
    await _start_first_fight(update, context, region_key, diff)

async def _dungeon_locked_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback para quando o jogador clica numa dificuldade bloqueada."""
    query = update.callback_query
    await query.answer("Você precisa de completar a dificuldade anterior para desbloquear esta!", show_alert=True)

dungeon_open_handler = CallbackQueryHandler(_open_menu_cb, pattern=r"^dungeon_open:[A-Za-z0-9_]+$")
dungeon_pick_handler = CallbackQueryHandler(_pick_diff_cb, pattern=r"^dungeon_pick:(iniciante|infernal|pesadelo):[A-Za-z0-9_]+$")
dungeon_locked_handler = CallbackQueryHandler(_dungeon_locked_cb, pattern=r'^dungeon_locked$')