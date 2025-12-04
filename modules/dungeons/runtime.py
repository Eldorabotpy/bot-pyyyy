# modules/dungeons/runtime.py
# (VERSÃO CORRIGIDA: AGORA OS COOLDOWNS DIMINUEM CORRETAMENTE)
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


def _inv(p: dict) -> dict:
    inv = p.get("inventory") or p.get("inventario") or {}
    return inv if isinstance(inv, dict) else {}

def _consume_keys(pdata: dict, key_item: str, key_cost: int) -> bool:
    inv = _inv(pdata)
    try: current_keys = int(inv.get(key_item, 0))
    except: current_keys = 0
    if current_keys < key_cost: return False 
    inv[key_item] = current_keys - key_cost
    pdata["inventory"] = inv
    return True

def _load_region_dungeon(region_key: str) -> dict:
    d = REGIONAL_DUNGEONS.get(region_key)
    if not d: raise RuntimeError(f"Calabouço '{region_key}' não encontrado.")
    return d

def _final_gold_for(dungeon_cfg: dict, difficulty_cfg: Difficulty) -> int:
    try:
        base = int(dungeon_cfg.get("gold_base", 0)) 
        return int(round(base * float(difficulty_cfg.gold_mult)))
    except: return 0

def _key_cost_for(difficulty_cfg: Difficulty) -> int: return difficulty_cfg.key_cost
def _key_item_for(dungeon_cfg: dict) -> str: return str(dungeon_cfg.get("key_item") or "cristal_de_abertura")

# ============================================================
# 🛠️ CACHE BRIDGE
# ============================================================
async def _update_battle_cache(context: ContextTypes.DEFAULT_TYPE, user_id: int, pdata: dict, combat_details: dict, message_id: int = None, chat_id: int = None):
    """
    Atualiza o cache de batalha com TODOS os dados necessários, incluindo o NOME.
    """
    p_stats = await player_manager.get_player_total_stats(pdata)
    
    # 1. Prepara Stats do Monstro
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
    
    player_name_fixed = pdata.get("character_name", "Herói")

    # 3. Cria o Cache
    cache = {
        'player_id': user_id, 
        'chat_id': chat_id, 
        'message_id': message_id, 
        'player_name': player_name_fixed, 
        'player_stats': p_stats, 
        'monster_stats': monster_stats,
        'player_hp': pdata.get('current_hp'), 
        'player_mp': pdata.get('current_mp'),
        'battle_log': combat_details.get('battle_log', []), 
        'turn': 'player',
        'region_key': combat_details.get('region_key'),
        'player_media_id': p_media.get("id") if p_media else None,
        'player_media_type': p_media.get("type", "photo") if p_media else "photo",
        'monster_media_id': combat_details.get('file_id_name'), 
        'monster_media_type': 'photo', 
        'dungeon_ctx': combat_details.get('dungeon_ctx'),
        'skill_cooldowns': combat_details.get('skill_cooldowns', {}) 
    }
    
    context.user_data['battle_cache'] = cache
    set_pending_battle(user_id, combat_details.get('dungeon_ctx'))

def build_region_dungeon_button(region_key: str) -> InlineKeyboardButton:
    return InlineKeyboardButton("🏰 𝐂𝐚𝐥𝐚𝐛𝐨𝐮𝐜̧𝐨 🏰", callback_data=f"dungeon_open:{region_key}")

async def _send_battle_media(context, chat_id, caption, file_id_name, reply_markup=None) -> int | None:
    fd = None
    if media_ids and hasattr(media_ids, "get_file_data") and file_id_name:
        try: fd = media_ids.get_file_data(file_id_name)
        except: pass
    sent_msg = None
    try:
        if fd and fd.get("id"):
            mtype = (fd.get("type") or "photo").lower()
            if mtype == "video": sent_msg = await context.bot.send_video(chat_id=chat_id, video=fd["id"], caption=caption, parse_mode="HTML", reply_markup=reply_markup)
            else: sent_msg = await context.bot.send_photo(chat_id=chat_id, photo=fd["id"], caption=caption, parse_mode="HTML", reply_markup=reply_markup)
            return sent_msg.message_id
    except: pass
    try:
        sent_msg = await context.bot.send_message(chat_id=chat_id, text=caption, parse_mode="HTML", reply_markup=reply_markup)
        return sent_msg.message_id
    except: return None

async def _open_menu(update, context, region_key):
    q = update.callback_query
    if q: 
        try: await q.answer()
        except: pass
    try: dungeon = _load_region_dungeon(region_key)
    except: 
        await context.bot.send_message(update.effective_chat.id, "Erro no calabouço.")
        return
    key_item = _key_item_for(dungeon)
    pdata = await player_manager.get_player_data(update.effective_user.id) or {}
    have = int((_inv(pdata)).get(key_item, 0))
    caption = f"<b>{dungeon.get('label','Calabouço')}</b>\nRegião: <code>{region_key}</code>\n\n🎒 Chaves: <b>{have}</b>\n\nEscolha:"
    kb = []
    d_prog = (pdata.get("dungeon_progress", {}) or {}).get(region_key, {})
    high = d_prog.get("highest_completed")
    h_idx = -1
    if high in DEFAULT_DIFFICULTY_ORDER: h_idx = DEFAULT_DIFFICULTY_ORDER.index(high)
    for i, diff_key in enumerate(DEFAULT_DIFFICULTY_ORDER):
        meta = DIFFICULTIES.get(diff_key)
        if not meta: continue
        if i <= h_idx + 1: kb.append([InlineKeyboardButton(f"{meta.emoji} {meta.label}", callback_data=f"dungeon_pick:{diff_key}:{region_key}")])
        else: kb.append([InlineKeyboardButton(f"🔒 {meta.label}", callback_data="dungeon_locked")])
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="combat_return_to_map")])
    await _send_battle_media(context, update.effective_chat.id, caption, dungeon.get("menu_media_key"), InlineKeyboardMarkup(kb))

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

# 🔥 CORREÇÃO AQUI: REDUÇÃO DE COOLDOWNS AO AVANÇAR MOB 🔥
def _build_combat_details(floor_mob: MobDef, difficulty_cfg: Difficulty, region_key: str, stage: int, active_cooldowns: dict = None) -> dict:
    base_stats = floor_mob.stats_base
    stat_mult = difficulty_cfg.stat_mult
    gold_mult = difficulty_cfg.gold_mult
    hp = int(round(base_stats.get("max_hp", 50) * stat_mult))
    
    mob_name = floor_mob.display
    if mob_name.lower().startswith(("o ", "a ", "os ", "as ")):
        intro_text = f"Você avança! <b>{mob_name}</b> bloqueia seu caminho!"
    else:
        intro_text = f"Você avança! Um <b>{mob_name}</b> aparece das sombras!"

    # 🔥 CORREÇÃO: Reduz 1 turno de todos os cooldowns ativos 🔥
    processed_cooldowns = {}
    if active_cooldowns:
        for skill_id, turns in active_cooldowns.items():
            new_turns = turns - 1
            if new_turns > 0:
                processed_cooldowns[skill_id] = new_turns

    return {
        "monster_name":       f"{floor_mob.emoji} {floor_mob.display}",
        "monster_hp":         hp, "monster_max_hp": hp, 
        "monster_attack":     int(round(base_stats.get("attack", 5) * stat_mult)),
        "monster_defense":    int(round(base_stats.get("defense", 0) * stat_mult)), 
        "monster_initiative": int(round(base_stats.get("initiative", 5) * stat_mult)),
        "monster_luck":       base_stats.get("luck", 5),
        "monster_xp_reward":  int(round(base_stats.get("xp_reward", 20) * stat_mult)),
        "monster_gold_drop":  int(round(base_stats.get("gold_drop", 10) * gold_mult)),
        "loot_table":         list(base_stats.get("loot_table", [])),
        "flee_bias":          float(base_stats.get("flee_bias", 0.0)),
        "dungeon_ctx":        {"dungeon_id": region_key, "floor_idx": stage, "difficulty": difficulty_cfg.key, "region": region_key},
        "battle_log":         [intro_text],
        "id":            floor_mob.key,
        "file_id_name":  floor_mob.media_key, 
        "is_boss":       bool(base_stats.get("is_boss", False)),
        "region_key":    region_key, "difficulty": difficulty_cfg.key, "dungeon_stage": stage,
        
        # Passa os cooldowns reduzidos para a próxima luta
        "skill_cooldowns": processed_cooldowns
    }

async def _start_first_fight(update, context, region_key, difficulty_key):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try: dungeon = _load_region_dungeon(region_key)
    except: return
    diff_cfg = DIFFICULTIES.get(difficulty_key)
    key_item = _key_item_for(dungeon)
    key_cost = _key_cost_for(diff_cfg)
    pdata = await player_manager.get_player_data(user_id) or {}
    if not _consume_keys(pdata, key_item, key_cost):
        await context.bot.send_message(chat_id, f"Falta {key_cost}x {key_item}.")
        return
    floors = list(dungeon.get("floors") or [])
    if not floors: return

    state = _new_run_state(region_key, difficulty_key)
    combat = _build_combat_details(floors[0], diff_cfg, region_key, 0)
    
    state["action"] = "in_combat"
    state["details"] = combat
    pdata["player_state"] = state
    await player_manager.save_player_data(user_id, pdata)
    
    caption = await format_combat_message(pdata)
    kb = [[InlineKeyboardButton("⚔️ 𝐀𝐭𝐚𝐜𝐚𝐫", callback_data="combat_attack"), InlineKeyboardButton("✨ Skills", callback_data="combat_skill_menu")],
          [InlineKeyboardButton("🧪 Poções", callback_data="combat_potion_menu"), InlineKeyboardButton("🏃 𝐅𝐮𝐠𝐢𝐫", callback_data="combat_flee")]]
    msg_id = await _send_battle_media(context, chat_id, caption, combat.get("file_id_name"), InlineKeyboardMarkup(kb))
    await _update_battle_cache(context, user_id, pdata, combat, message_id=msg_id, chat_id=chat_id)

# ============================================================
# Avanço Pós-Combate
# ============================================================
async def resume_dungeon_after_battle(context, user_id, dungeon_ctx, victory):
    if not victory:
        await fail_dungeon_run(None, context, user_id, user_id, "Derrotado")
        return
    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return
    run = pdata.get("player_state", {})
    details = run.get("details", {})
    
    if not dungeon_ctx: dungeon_ctx = details.get("dungeon_ctx")
    if not dungeon_ctx: return

    items = []
    loot = details.get("loot_table", [])
    if loot:
        for e in loot:
            if random.uniform(0, 100) <= e.get("drop_chance", 0): items.append((e.get("item_id"), 1, {}))
            
    rewards = {
        "xp": details.get("monster_xp_reward", 0), "gold": details.get("monster_gold_drop", 0),
        "items": items
    }
    await advance_after_victory(None, context, user_id, user_id, details, rewards)

async def fail_dungeon_run(update, context, user_id, chat_id, reason):
    # 👇 1. APAGA A MENSAGEM ANTERIOR AQUI
    await _delete_previous_battle_msg(context, user_id)

    pdata = await player_manager.get_player_data(user_id)
    if pdata:
        stats = await player_manager.get_player_total_stats(pdata) 
        pdata['current_hp'] = stats.get('max_hp', 50)
        pdata['current_mp'] = stats.get('max_mana', 10)
        pdata["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(user_id, pdata)
    
    # Envia a nova mensagem de derrota
    await _send_battle_media(context, chat_id, f"💀 **Fim da Linha!**\n{reason}.", "media_dungeon_defeat", 
                             InlineKeyboardMarkup([[InlineKeyboardButton("⚰️ Sair", callback_data="combat_return_to_map")]]))
    
async def advance_after_victory(update, context, user_id, chat_id, combat_details, rewards):
    pdata = await player_manager.get_player_data(user_id) or {}
    run = pdata.get("player_state") or {}
    
    xp, gold, items = rewards.get("xp",0), rewards.get("gold",0), rewards.get("items",[])
    pdata['xp'] = int(pdata.get('xp', 0)) + xp
    if gold > 0: player_manager.add_gold(pdata, gold)
    for i, q, _ in items: player_manager.add_item_to_inventory(pdata, i, q)

    reg_key = str(combat_details.get("region_key"))
    diff_key = str(combat_details.get("difficulty"))
    try:
        dungeon = _load_region_dungeon(reg_key)
        diff_cfg = DIFFICULTIES.get(diff_key)
    except: return

    floors = list(dungeon.get("floors") or [])
    cur_stg = int(combat_details.get("dungeon_stage", 0))
    next_stg = cur_stg + 1
    
    active_cds = combat_details.get("skill_cooldowns", {})

    # --- CASO 1: VITÓRIA TOTAL (Fim do Calabouço) ---
    if next_stg >= len(floors):
        # 👇 APAGA A MENSAGEM DO ÚLTIMO BOSS AQUI
        await _delete_previous_battle_msg(context, user_id)

        pdata.setdefault("dungeon_progress", {}).setdefault(reg_key, {})
        pdata["dungeon_progress"][reg_key]["highest_completed"] = diff_key
        bonus = _final_gold_for(dungeon, diff_cfg)
        if bonus > 0: player_manager.add_gold(pdata, bonus)
        
        stats = await player_manager.get_player_total_stats(pdata)
        pdata['current_hp'] = stats.get('max_hp', 50)
        pdata['current_mp'] = stats.get('max_mana', 10)
        pdata["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(user_id, pdata)
        
        summ = f"🏆 <b>CALABOUÇO CONCLUÍDO!</b>\nBônus: {bonus} Ouro"
        if items: summ += "\n\nLoot Final:\n" + "\n".join([f"• {q}x {i}" for i,q,_ in items])
        
        # Envia a mensagem de Vitória
        await _send_battle_media(context, chat_id, summ, "media_dungeon_victory", 
                                 InlineKeyboardMarkup([[InlineKeyboardButton("🎉 Continuar", callback_data="combat_return_to_map")]]))
        return

    # --- CASO 2: PRÓXIMO MONSTRO ---
    try: next_mob = floors[next_stg]
    except: return

    combat = _build_combat_details(next_mob, diff_cfg, reg_key, next_stg, active_cooldowns=active_cds)
    
    run["action"] = "in_combat"
    run["details"] = combat
    pdata["player_state"] = run
    await player_manager.save_player_data(user_id, pdata)

    caption = await format_combat_message(pdata)
    kb = [[InlineKeyboardButton("⚔️ 𝐀𝐭𝐚𝐜𝐚𝐫", callback_data="combat_attack"), InlineKeyboardButton("✨ Skills", callback_data="combat_skill_menu")],
          [InlineKeyboardButton("🧪 Poções", callback_data="combat_potion_menu"), InlineKeyboardButton("🏃 𝐅𝐮𝐠𝐢𝐫", callback_data="combat_flee")]]
    
    # 👇 APAGA A MENSAGEM DO MONSTRO ANTERIOR AQUI
    await _delete_previous_battle_msg(context, user_id)

    # Envia o próximo monstro
    msg_id = await _send_battle_media(context, chat_id, caption, combat.get("file_id_name"), InlineKeyboardMarkup(kb))
    await _update_battle_cache(context, user_id, pdata, combat, message_id=msg_id, chat_id=chat_id)

async def _open_menu_cb(update, context): await _open_menu(update, context, update.callback_query.data.split(":")[1])
async def _pick_diff_cb(update, context): 
    d = update.callback_query.data.split(":")
    try: await update.callback_query.message.delete()
    except: pass
    await _start_first_fight(update, context, d[2], d[1])
async def _dungeon_locked_cb(update, context): await update.callback_query.answer("Trancado!", show_alert=True)

async def open_combat_skill_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except: pass
    user_id = update.effective_user.id
    
    # Carrega dados
    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return
    learned_skills = pdata.get("skills") or pdata.get("learned_skills") or []
    
    # 🔥 Pega os cooldowns da memória 🔥
    battle_cache = context.user_data.get('battle_cache', {})
    active_cds = battle_cache.get('skill_cooldowns', {})

    kb = []
    row = []
    if not learned_skills:
        kb.append([InlineKeyboardButton("🚫 Sem skills", callback_data="ignore")])
    else:
        for skill_id in learned_skills:
            skill_name = str(skill_id).replace("_", " ").title()
            
            # Verifica se tem tempo restante
            turns_left = active_cds.get(skill_id, 0)
            
            if turns_left > 0:
                # Mostra ampulheta e tempo
                btn_text = f"⏳ {skill_name} ({turns_left}t)"
                cb_data = "ignore"
            else:
                # Libera o uso
                btn_text = f"✨ {skill_name}"
                cb_data = f"combat_use_skill:{skill_id}"
                
            row.append(InlineKeyboardButton(btn_text, callback_data=cb_data))
            if len(row) == 2: 
                kb.append(row)
                row = []
        if row: kb.append(row)
        
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="combat_menu_return")])
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))

async def _delete_previous_battle_msg(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Tenta apagar a mensagem de batalha anterior salva no cache."""
    cache = context.user_data.get('battle_cache')
    # Verifica se o cache pertence ao usuário atual
    if cache and cache.get('player_id') == user_id:
        chat_id = cache.get('chat_id')
        msg_id = cache.get('message_id')
        if chat_id and msg_id:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except Exception as e:
                # Ignora erros se a mensagem já foi apagada ou é muito antiga
                pass

async def open_combat_potion_menu(update, context):
    q = update.callback_query
    try: await q.answer()
    except: pass
    uid = q.from_user.id
    pd = await player_manager.get_player_data(uid)
    inv = _inv(pd)
    kb = []
    pids = ["hp_potion", "mp_potion", "pocao_vida", "pocao_mana"]
    f = False
    for i, q in inv.items():
        if int(q)>0 and any(x in i for x in pids):
            f=True
            n = i.replace("_", " ").title()
            kb.append([InlineKeyboardButton(f"🧪 {n} (x{q})", callback_data=f"combat_use_item:{i}")])
    if not f: kb.append([InlineKeyboardButton("🚫 Vazio", callback_data="ignore")])
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="combat_menu_return")])
    await q.edit_message_reply_markup(InlineKeyboardMarkup(kb))

async def return_to_main_combat_menu(update, context):
    q = update.callback_query
    try: await q.answer()
    except: pass
    kb = [[InlineKeyboardButton("⚔️ Atacar", callback_data="combat_attack"), InlineKeyboardButton("✨ Skills", callback_data="combat_skill_menu")],
          [InlineKeyboardButton("🧪 Poções", callback_data="combat_potion_menu"), InlineKeyboardButton("🏃 Fugir", callback_data="combat_flee")]]
    await q.edit_message_reply_markup(InlineKeyboardMarkup(kb))

dungeon_open_handler = CallbackQueryHandler(_open_menu_cb, pattern=r"^dungeon_open:[A-Za-z0-9_]+$")
dungeon_pick_handler = CallbackQueryHandler(_pick_diff_cb, pattern=r"^dungeon_pick:[A-Za-z0-9_]+:[A-Za-z0-9_]+$")
dungeon_locked_handler = CallbackQueryHandler(_dungeon_locked_cb, pattern=r'^dungeon_locked$')
combat_skill_handler = CallbackQueryHandler(open_combat_skill_menu, pattern="^combat_skill_menu$")
combat_potion_handler = CallbackQueryHandler(open_combat_potion_menu, pattern="^combat_potion_menu$")
combat_return_handler = CallbackQueryHandler(return_to_main_combat_menu, pattern="^combat_menu_return$")