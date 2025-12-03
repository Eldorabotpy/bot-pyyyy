# modules/dungeons/runtime.py
# (VERSÃO BLINDADA: ATUALIZA O CACHE MESMO SE O ENVIO FALHAR)
from __future__ import annotations
import logging
import random
from typing import List, Dict, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest, Forbidden

from modules import player_manager, game_data
from handlers.utils import format_combat_message
from .config import DIFFICULTIES, DEFAULT_DIFFICULTY_ORDER, Difficulty
from .regions import REGIONAL_DUNGEONS, MobDef
from modules.dungeons.runtime_api import set_pending_battle
from handlers.profile_handler import _get_class_media 

try:
    from modules import file_id_manager as media_ids
except Exception:
    media_ids = None

logger = logging.getLogger(__name__)

# ============================================================
# Helpers
# ============================================================
def _inv(p: dict) -> dict:
    inv = p.get("inventory") or p.get("inventario") or {}
    return inv if isinstance(inv, dict) else {}

def _consume_keys(pdata: dict, key_item: str, key_cost: int) -> bool:
    inv = _inv(pdata)
    try:
        current_keys = int(inv.get(key_item, 0))
    except Exception:
        current_keys = 0
    if current_keys < key_cost:
        return False 
    inv[key_item] = current_keys - key_cost
    pdata["inventory"] = inv
    return True

def _load_region_dungeon(region_key: str) -> dict:
    d = REGIONAL_DUNGEONS.get(region_key)
    if not d:
        logger.error(f"Calabouço não encontrado em regions.py para: {region_key}")
        raise RuntimeError(f"Calabouço '{region_key}' não encontrado.")
    return d

def _final_gold_for(dungeon_cfg: dict, difficulty_cfg: Difficulty) -> int:
    try:
        base_gold = int(dungeon_cfg.get("gold_base", 0)) 
        gold_mult = float(difficulty_cfg.gold_mult)
        return int(round(base_gold * gold_mult))
    except Exception:
        return 0

def _key_cost_for(difficulty_cfg: Difficulty) -> int:
    return difficulty_cfg.key_cost

def _key_item_for(dungeon_cfg: dict) -> str:
    return str(dungeon_cfg.get("key_item") or "cristal_de_abertura")

# ============================================================
# 🛠️ CACHE BRIDGE
# ============================================================
async def _update_battle_cache(context: ContextTypes.DEFAULT_TYPE, user_id: int, pdata: dict, combat_details: dict, message_id: int = None, chat_id: int = None):
    """
    Força a criação do cache na memória RAM.
    """
    p_stats = await player_manager.get_player_total_stats(pdata)
    
    monster_stats = {
        'name': combat_details.get('monster_name', 'Inimigo'),
        'hp': combat_details.get('monster_hp', 100),
        'max_hp': combat_details.get('monster_max_hp', 100),
        'attack': combat_details.get('monster_attack', 10),
        'defense': combat_details.get('monster_defense', 0),
        'initiative': combat_details.get('monster_initiative', 0),
        'luck': combat_details.get('monster_luck', 0),
        'xp_reward': combat_details.get('monster_xp_reward', 0),
        'gold_drop': combat_details.get('monster_gold_drop', 0),
        'loot_table': combat_details.get('loot_table', []),
        'id': combat_details.get('id'),
        'flee_bias': combat_details.get('flee_bias', 0.0)
    }

    p_media = _get_class_media(pdata, purpose="combate")
    p_media_id = p_media.get("id") if p_media else None
    p_media_type = p_media.get("type", "photo") if p_media else "photo"

    cache = {
        'player_id': user_id,
        'chat_id': chat_id,
        'message_id': message_id, # Pode ser None se o envio falhar, mas o cache existe!
        'player_stats': p_stats,
        'monster_stats': monster_stats,
        'player_hp': pdata.get('current_hp'),
        'player_mp': pdata.get('current_mp'),
        'battle_log': combat_details.get('battle_log', []),
        'turn': 'player',
        'region_key': combat_details.get('region_key'),
        'player_media_id': p_media_id,
        'player_media_type': p_media_type,
        'monster_media_id': combat_details.get('file_id_name'),
        'monster_media_type': 'photo', 
        'dungeon_ctx': combat_details.get('dungeon_ctx') 
    }
    
    context.user_data['battle_cache'] = cache
    set_pending_battle(user_id, combat_details.get('dungeon_ctx'))

# ============================================================
# UI Functions
# ============================================================
def build_region_dungeon_button(region_key: str) -> InlineKeyboardButton:
    return InlineKeyboardButton("🏰 𝐂𝐚𝐥𝐚𝐛𝐨𝐮𝐜̧𝐨 🏰", callback_data=f"dungeon_open:{region_key}")

async def _send_battle_media(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    caption: str,
    file_id_name: str | None,
    reply_markup: InlineKeyboardMarkup | None = None
) -> int | None:
    """Retorna o message_id se enviado com sucesso, ou None."""
    fd = None
    if media_ids and hasattr(media_ids, "get_file_data") and file_id_name:
        try: fd = media_ids.get_file_data(file_id_name)
        except Exception: pass

    sent_msg = None
    try:
        if fd and fd.get("id"):
            media_type = (fd.get("type") or "photo").lower()
            if media_type == "video":
                sent_msg = await context.bot.send_video(chat_id=chat_id, video=fd["id"], caption=caption, parse_mode="HTML", reply_markup=reply_markup)
            else:
                sent_msg = await context.bot.send_photo(chat_id=chat_id, photo=fd["id"], caption=caption, parse_mode="HTML", reply_markup=reply_markup)
        else:
            sent_msg = await context.bot.send_message(chat_id=chat_id, text=caption, parse_mode="HTML", reply_markup=reply_markup)
            
        return sent_msg.message_id if sent_msg else None

    except (BadRequest, Forbidden) as e:
        logger.error(f"Erro Telegram ao enviar dungeon: {e}")
        # Se o chat não existe, não há muito o que fazer, mas não travamos o código
        return None
    except Exception as e:
        logger.error(f"Erro genérico envio dungeon: {e}")
        try:
             sent_msg = await context.bot.send_message(chat_id=chat_id, text=caption, parse_mode="HTML", reply_markup=reply_markup)
             return sent_msg.message_id
        except: return None

# ============================================================
# Lógica do Menu
# ============================================================
async def _open_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, region_key: str):
    q = update.callback_query
    if q:
        try: await q.answer()
        except BadRequest: pass
    
    chat_id = update.effective_chat.id
    try: dungeon = _load_region_dungeon(region_key) 
    except RuntimeError:
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Esta região ainda não tem um calabouço configurado.")
        return

    key_item = _key_item_for(dungeon)
    key_display = key_item.replace("_", " ").title()
    if game_data.ITEMS_DATA:
        k_data = game_data.ITEMS_DATA.get(key_item, {})
        if k_data: key_display = f"{k_data.get('emoji','🔹')} {k_data.get('display_name', key_display)}"

    pdata = await player_manager.get_player_data(update.effective_user.id) or {}
    have = int((_inv(pdata)).get(key_item, 0))

    caption = (
        f"<b>{dungeon.get('label','Calabouço')}</b>\nRegião: <code>{region_key}</code>\n\n"
        f"🗝️ Entrada: <b>{key_display}</b>\n🎒 Você tem: <b>{have}</b>\n\nEscolha a dificuldade:"
    )

    kb = []
    dungeon_progress = (pdata.get("dungeon_progress", {}) or {}).get(region_key, {})
    highest_completed = dungeon_progress.get("highest_completed")
    highest_completed_index = -1
    
    if highest_completed and highest_completed in DEFAULT_DIFFICULTY_ORDER:
        highest_completed_index = DEFAULT_DIFFICULTY_ORDER.index(highest_completed)
    
    for i, diff_key in enumerate(DEFAULT_DIFFICULTY_ORDER):
        meta = DIFFICULTIES.get(diff_key)
        if not meta: continue
        if i <= highest_completed_index + 1:
            button_text = f"{meta.emoji} {meta.label} ( -{meta.key_cost} chaves)"
            kb.append([InlineKeyboardButton(button_text, callback_data=f"dungeon_pick:{diff_key}:{region_key}")])
        else:
            kb.append([InlineKeyboardButton(f"🔒 {meta.label}", callback_data="dungeon_locked")])
            
    kb.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="continue_after_action")])
    await _send_battle_media(context, chat_id, caption, dungeon.get("menu_media_key"), InlineKeyboardMarkup(kb))

# ============================================================
# Construção de Combate
# ============================================================
def _new_run_state(region_key: str, difficulty: str) -> dict:
    return {
        "action": "dungeon_run",
        "details": {
            "region_key": region_key, "difficulty": difficulty,
            "dungeon_stage": 0, "last_fight_rewards": {}
        }
    }

def _build_combat_details(floor_mob: MobDef, difficulty_cfg: Difficulty, region_key: str, stage: int) -> dict:
    base_stats = floor_mob.stats_base
    stat_mult = difficulty_cfg.stat_mult
    gold_mult = difficulty_cfg.gold_mult
    hp = int(round(base_stats.get("max_hp", 50) * stat_mult))
    
    dungeon_ctx = {
        "dungeon_id": region_key, "floor_idx":  stage,
        "difficulty": difficulty_cfg.key, "region":     region_key,
    }

    return {
        "monster_name":       f"{floor_mob.emoji} {floor_mob.display}",
        "monster_hp":         hp, "monster_max_hp":     hp, 
        "monster_attack":     int(round(base_stats.get("attack", 5) * stat_mult)),
        "monster_defense":    int(round(base_stats.get("defense", 0) * stat_mult)), 
        "monster_initiative": int(round(base_stats.get("initiative", 5) * stat_mult)),
        "monster_luck":       base_stats.get("luck", 5),
        "monster_xp_reward":  int(round(base_stats.get("xp_reward", 20) * stat_mult)),
        "monster_gold_drop":  int(round(base_stats.get("gold_drop", 10) * gold_mult)),
        "loot_table":         list(base_stats.get("loot_table", [])),
        "flee_bias":          float(base_stats.get("flee_bias", 0.0)),
        "dungeon_ctx":        dungeon_ctx,
        "battle_log":         [f"Você avança no calabouço ({difficulty_cfg.label}). Um {floor_mob.display} aparece!"],
        "id":            floor_mob.key,
        "file_id_name":  floor_mob.media_key, 
        "is_boss":       bool(base_stats.get("is_boss", False)),
        "region_key":    region_key, "difficulty":    difficulty_cfg.key, "dungeon_stage": stage, 
    }

async def _start_first_fight(update: Update, context: ContextTypes.DEFAULT_TYPE, region_key: str, difficulty_key: str):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    query = update.callback_query
    
    try: dungeon = _load_region_dungeon(region_key)
    except Exception as e:
        try: await query.answer(f"Erro: {e}", show_alert=True)
        except: pass
        return

    difficulty_cfg = DIFFICULTIES.get(difficulty_key)
    if not difficulty_cfg: return

    key_item = _key_item_for(dungeon)
    key_cost = _key_cost_for(difficulty_cfg)
    pdata = await player_manager.get_player_data(user_id) or {}
    
    if not _consume_keys(pdata, key_item, key_cost):
        try: await query.answer(f"Você precisa de {key_cost}x {key_item}.", show_alert=True)
        except: await context.bot.send_message(chat_id=chat_id, text=f"Faltam {key_cost}x {key_item}.")
        return

    floors: List[MobDef] = list(dungeon.get("floors") or [])
    if not floors: return

    state = _new_run_state(region_key, difficulty_key)
    try: combat = _build_combat_details(floors[0], difficulty_cfg, region_key, 0)
    except Exception as e:
        logger.error(f"Erro ao criar mob: {e}")
        return

    state["action"] = "in_combat"
    state["details"] = combat
    pdata["player_state"] = state
    await player_manager.save_player_data(user_id, pdata)
    
    caption = await format_combat_message(pdata)
    kb = [[InlineKeyboardButton("⚔️ 𝐀𝐭𝐚𝐜𝐚𝐫", callback_data="combat_attack"), InlineKeyboardButton("✨ Skills", callback_data="combat_skill_menu")],
          [InlineKeyboardButton("🧪 Poções", callback_data="combat_potion_menu"), InlineKeyboardButton("🏃 𝐅𝐮𝐠𝐢𝐫", callback_data="combat_flee")]]
    
    # 1. TENTA ENVIAR
    msg_id = await _send_battle_media(context, chat_id, caption, combat.get("file_id_name"), InlineKeyboardMarkup(kb))
    
    # 2. ATUALIZA CACHE INDEPENDENTE DO SUCESSO DO ENVIO
    # Se o envio falhou (msg_id=None), o cache é criado mesmo assim. 
    # O main_handler (versão suprema) vai conseguir ler e processar o clique.
    await _update_battle_cache(context, user_id, pdata, combat, message_id=msg_id, chat_id=chat_id)

# ============================================================
# Avanço Pós-Combate
# ============================================================
async def resume_dungeon_after_battle(context: ContextTypes.DEFAULT_TYPE, user_id: int, dungeon_ctx: dict | None, victory: bool):
    if not victory:
        await fail_dungeon_run(None, context, user_id, user_id, "Derrotado em combate")
        return

    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return
    run = pdata.get("player_state", {})
    details = run.get("details", {})
    
    if not dungeon_ctx: dungeon_ctx = details.get("dungeon_ctx")
    if not dungeon_ctx: return

    dropped_items = []
    loot_table = details.get("loot_table", [])
    if loot_table:
        for entry in loot_table:
            item_id = entry.get("item_id")
            chance = entry.get("drop_chance", 0)
            if random.uniform(0, 100) <= chance: dropped_items.append((item_id, 1, {}))

    rewards = {
        "xp": details.get("monster_xp_reward", 0),
        "gold": details.get("monster_gold_drop", 0),
        "items": dropped_items
    }
    await advance_after_victory(None, context, user_id, user_id, details, rewards)

async def fail_dungeon_run(update: Update | None, context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, reason: str):
    pdata = await player_manager.get_player_data(user_id)
    if pdata:
        total_stats = await player_manager.get_player_total_stats(pdata) 
        pdata['current_hp'] = total_stats.get('max_hp', 50)
        pdata['current_mp'] = total_stats.get('max_mana', 10)
        pdata["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(user_id, pdata)

    summary_text = f"💀 **Fim da Linha!**\n\nMotivo: {reason}."
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("⚰️ Retornar", callback_data="combat_return_to_map")]])
    await _send_battle_media(context, chat_id, summary_text, "media_dungeon_defeat", reply_markup)

async def advance_after_victory(update: Update | None, context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, combat_details: dict, rewards: dict):
    pdata = await player_manager.get_player_data(user_id) or {}
    run = pdata.get("player_state") or {}
    
    xp_gain = rewards.get("xp", 0)
    gold_gain = rewards.get("gold", 0)
    items_gain = rewards.get("items", [])
    pdata['xp'] = int(pdata.get('xp', 0)) + xp_gain
    if gold_gain > 0: player_manager.add_gold(pdata, gold_gain)
    for i_id, i_qty, _ in items_gain: player_manager.add_item_to_inventory(pdata, i_id, i_qty)

    region_key = str(combat_details.get("region_key") or "")
    difficulty_key = str(combat_details.get("difficulty") or "iniciante")
    
    try:
        dungeon = _load_region_dungeon(region_key)
        difficulty_cfg = DIFFICULTIES.get(difficulty_key)
        if not difficulty_cfg: raise ValueError("Diff error")
    except Exception:
        await fail_dungeon_run(None, context, user_id, chat_id, "Erro interno de dados")
        return

    floors: List[MobDef] = list(dungeon.get("floors") or [])
    cur_stage = int(combat_details.get("dungeon_stage", 0))
    next_stage = cur_stage + 1
    
    # --- VITÓRIA FINAL ---
    if next_stage >= len(floors):
        pdata.setdefault("dungeon_progress", {}).setdefault(region_key, {})
        pdata["dungeon_progress"][region_key]["highest_completed"] = difficulty_key
        final_gold_bonus = _final_gold_for(dungeon, difficulty_cfg)
        if final_gold_bonus > 0: player_manager.add_gold(pdata, final_gold_bonus)
        
        total_stats = await player_manager.get_player_total_stats(pdata)
        pdata['current_hp'] = total_stats.get('max_hp', 50)
        pdata['current_mp'] = total_stats.get('max_mana', 10)
        pdata["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(user_id, pdata)
        
        summary_text = f"🏆 <b>CALABOUÇO CONCLUÍDO!</b> 🏆\n\nDominou {dungeon.get('label')}!\n💰 Bônus: {final_gold_bonus} Ouro\n"
        if items_gain:
            summary_text += "\n<b>📦 Loot Final:</b>\n"
            for i_id, i_qty, _ in items_gain: summary_text += f"• {i_qty}x {i_id}\n"

        kb = [[InlineKeyboardButton("🎉 Continuar", callback_data="combat_return_to_map")]]
        await _send_battle_media(context, chat_id, summary_text, "media_dungeon_victory", InlineKeyboardMarkup(kb))
        return

    # --- PRÓXIMO MOB ---
    logger.info(f"Avançando dungeon {region_key} para andar {next_stage}")
    try: next_mob = floors[next_stage]
    except IndexError: return

    combat = _build_combat_details(next_mob, difficulty_cfg, region_key, next_stage)
    run["action"] = "in_combat"
    run["details"] = combat
    pdata["player_state"] = run
    await player_manager.save_player_data(user_id, pdata)

    caption = await format_combat_message(pdata)
    kb = [[InlineKeyboardButton("⚔️ 𝐀𝐭𝐚𝐜𝐚𝐫", callback_data="combat_attack"), InlineKeyboardButton("✨ Skills", callback_data="combat_skill_menu")],
          [InlineKeyboardButton("🧪 Poções", callback_data="combat_potion_menu"), InlineKeyboardButton("🏃 𝐅𝐮𝐠𝐢𝐫", callback_data="combat_flee")]]
    
    # ENVIAR E ATUALIZAR CACHE (MESMO SE FALHAR O ENVIO)
    msg_id = await _send_battle_media(context, chat_id, caption, combat.get("file_id_name"), InlineKeyboardMarkup(kb))
    await _update_battle_cache(context, user_id, pdata, combat, message_id=msg_id, chat_id=chat_id)

# ... (Handlers _open_menu_cb, etc permanecem iguais) ...
async def _open_menu_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    _, region_key = data.split(":", 1)
    await _open_menu(update, context, region_key)

async def _pick_diff_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    parts = data.split(":")
    if len(parts) != 3: return
    _, diff, region_key = parts
    if update.callback_query.message:
        try: await update.callback_query.message.delete()
        except Exception: pass
    await _start_first_fight(update, context, region_key, diff)

async def _dungeon_locked_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("🔒 Complete a dificuldade anterior!", show_alert=True)

# Callbacks de Combate
async def open_combat_skill_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except: pass
    user_id = update.effective_user.id
    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return
    learned_skills = pdata.get("skills") or pdata.get("learned_skills") or []
    kb = []
    row = []
    if not learned_skills:
        kb.append([InlineKeyboardButton("🚫 Sem skills", callback_data="ignore")])
    else:
        for skill_id in learned_skills:
            skill_name = str(skill_id).replace("_", " ").title()
            btn = InlineKeyboardButton(f"✨ {skill_name}", callback_data=f"combat_use_skill:{skill_id}")
            row.append(btn)
            if len(row) == 2: 
                kb.append(row)
                row = []
        if row: kb.append(row)
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="combat_menu_return")])
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))

async def open_combat_potion_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except: pass
    user_id = update.effective_user.id
    pdata = await player_manager.get_player_data(user_id)
    inv = _inv(pdata)
    kb = []
    potion_ids = ["hp_potion", "mp_potion", "pocao_vida", "pocao_mana", "elixir"]
    found_any = False
    for item_id, qtd in inv.items():
        if int(qtd) > 0 and any(pid in item_id for pid in potion_ids):
            found_any = True
            name = item_id.replace("_", " ").title()
            kb.append([InlineKeyboardButton(f"🧪 {name} (x{qtd})", callback_data=f"combat_use_item:{item_id}")])
    if not found_any:
        kb.append([InlineKeyboardButton("🚫 Mochila vazia", callback_data="ignore")])
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="combat_menu_return")])
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))

async def return_to_main_combat_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except: pass
    kb = [[InlineKeyboardButton("⚔️ Atacar", callback_data="combat_attack"), InlineKeyboardButton("✨ Skills", callback_data="combat_skill_menu")],
          [InlineKeyboardButton("🧪 Poções", callback_data="combat_potion_menu"), InlineKeyboardButton("🏃 Fugir", callback_data="combat_flee")]]
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))

dungeon_open_handler = CallbackQueryHandler(_open_menu_cb, pattern=r"^dungeon_open:[A-Za-z0-9_]+$")
dungeon_pick_handler = CallbackQueryHandler(_pick_diff_cb, pattern=r"^dungeon_pick:[A-Za-z0-9_]+:[A-Za-z0-9_]+$")
dungeon_locked_handler = CallbackQueryHandler(_dungeon_locked_cb, pattern=r'^dungeon_locked$')
combat_skill_handler = CallbackQueryHandler(open_combat_skill_menu, pattern="^combat_skill_menu$")
combat_potion_handler = CallbackQueryHandler(open_combat_potion_menu, pattern="^combat_potion_menu$")
combat_return_handler = CallbackQueryHandler(return_to_main_combat_menu, pattern="^combat_menu_return$")