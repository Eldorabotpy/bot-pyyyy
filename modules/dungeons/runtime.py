# modules/dungeons/runtime.py
from __future__ import annotations
import logging
from typing import List, Dict, Any
from collections import Counter 
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest

from modules import player_manager, game_data
from modules.game_data.monsters import MONSTERS_DATA
from handlers.utils import format_combat_message
from .config import DIFFICULTIES, DEFAULT_DIFFICULTY_ORDER, Difficulty
from .regions import REGIONAL_DUNGEONS, MobDef
from modules.dungeons.runtime_api import set_pending_battle

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

# ============================================================
# Registry loader
# ============================================================
def _load_region_dungeon(region_key: str) -> dict:
    # Busca a configuração vinda de regions.py
    d = REGIONAL_DUNGEONS.get(region_key)
    if not d:
        logger.error(f"Calabouço não encontrado em regions.py para: {region_key}")
        raise RuntimeError("dungeon_not_found")
    return d

def _final_gold_for(dungeon_cfg: dict, difficulty_cfg: Difficulty) -> int:
    try:
        base_gold = int(dungeon_cfg.get("gold_base", 0)) 
        gold_mult = float(difficulty_cfg.gold_mult)
        return int(round(base_gold * gold_mult))
    except Exception as e:
        logger.warning(f"Falha ao calcular ouro final: {e}")
        return 0

def _find_monster_template(mob_id: str) -> dict | None:
    if not mob_id: return None
    for region_monsters in MONSTERS_DATA.values():
        if isinstance(region_monsters, list):
            for monster in region_monsters:
                if isinstance(monster, dict) and monster.get("id") == mob_id:
                    return monster.copy()
    
    if isinstance(MONSTERS_DATA, dict):
         monster = MONSTERS_DATA.get(mob_id)
         if isinstance(monster, dict):
             return monster.copy()
             
    logger.warning(f"Não foi possível encontrar o template do monstro: {mob_id}")
    return None

def _key_cost_for(difficulty_cfg: Difficulty) -> int:
    return difficulty_cfg.key_cost

def _key_item_for(dungeon_cfg: dict) -> str:
    return str(dungeon_cfg.get("key_item") or "cristal_de_abertura")

# ============================================================
# Botão para o menu da região (ESSENCIAL PARA O BOTÃO APARECER)
# ============================================================
def build_region_dungeon_button(region_key: str) -> InlineKeyboardButton:
    """Retorna o botão para entrar no calabouço da região."""
    return InlineKeyboardButton("🏰 𝐂𝐚𝐥𝐚𝐛𝐨𝐮𝐜̧𝐨 🏰", callback_data=f"dungeon_open:{region_key}")

# ============================================================
# Funções de Envio
# ============================================================
async def _send_battle_media(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    caption: str,
    file_id_name: str | None,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    fd = None
    if media_ids and hasattr(media_ids, "get_file_data") and file_id_name:
        try:
            fd = media_ids.get_file_data(file_id_name)
        except Exception as e:
            logger.debug("get_file_data(%s) falhou: %s", file_id_name, e)

    try:
        if fd and fd.get("id"):
            media_type = (fd.get("type") or "photo").lower()
            if media_type == "video":
                await context.bot.send_video( 
                    chat_id=chat_id, video=fd["id"], caption=caption,
                    parse_mode="HTML", reply_markup=reply_markup,
                )
            else:
                await context.bot.send_photo(
                    chat_id=chat_id, photo=fd["id"], caption=caption,
                    parse_mode="HTML", reply_markup=reply_markup,
                )
            return
    except Exception as e:
        logger.warning(f"Falha ao enviar mídia ({file_id_name}). Caindo para texto. {e}")

    await context.bot.send_message(
        chat_id=chat_id, text=caption,
        parse_mode="HTML", reply_markup=reply_markup,
    )

# ============================================================
# UI: abrir menu de dificuldade
# ============================================================
async def _open_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, region_key: str):
    q = update.callback_query
    if q:
        try: await q.answer()
        except BadRequest: pass
    
    chat_id = update.effective_chat.id
    try:
        dungeon = _load_region_dungeon(region_key) 
    except RuntimeError:
        # Se não houver calabouço configurado em regions.py, avisa o usuário
        await context.bot.send_message(chat_id=chat_id, text="Esta região ainda não tem um calabouço configurado.")
        return

    key_item = _key_item_for(dungeon)
    key_obj = (game_data.ITEMS_DATA or {}).get(key_item, {})
    key_name = f"{key_obj.get('emoji','🔹')} {key_obj.get('display_name', key_item)}"

    pdata = await player_manager.get_player_data(update.effective_user.id) or {}
    have = int((_inv(pdata)).get(key_item, 0))

    caption = (
        f"<b>{dungeon.get('label','Calabouço')}</b>\n"
        f"Região: <code>{region_key}</code>\n\n"
        f"🔹 Você tem: <b>{have} × {key_name}</b>\n\n"
        f"Escolha a dificuldade:"
    )

    kb = []
    dungeon_progress = (pdata.get("dungeon_progress", {}) or {}).get(region_key, {})
    highest_completed = dungeon_progress.get("highest_completed")
    highest_completed_index = -1
    if highest_completed:
        try:
            highest_completed_index = DEFAULT_DIFFICULTY_ORDER.index(highest_completed)
        except (ValueError, TypeError): pass 
    
    for i, diff_key in enumerate(DEFAULT_DIFFICULTY_ORDER):
        meta = DIFFICULTIES.get(diff_key)
        if not meta: continue
        key_cost = meta.key_cost
        
        if i <= highest_completed_index + 1:
            button_text = f"{meta.emoji} {meta.label} ( 🔹{key_cost})"
            kb.append([InlineKeyboardButton(button_text, callback_data=f"dungeon_pick:{diff_key}:{region_key}")])
        else:
            kb.append([InlineKeyboardButton(f"🔒 {meta.label}", callback_data="dungeon_locked")])
    kb.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="continue_after_action")])
    
    reply_markup = InlineKeyboardMarkup(kb)
    try:
        if q: await q.delete_message()
        menu_media_key = dungeon.get("menu_media_key") 
        await _send_battle_media(context, chat_id, caption, menu_media_key, reply_markup)
    except Exception as e:
        logger.error(f"Erro menu dungeon: {e}")
        try:
            await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")
        except: pass

# ============================================================
# Lógica de Combate
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
    hp = int(round(base_stats.get("max_hp", 1) * stat_mult))
    
    return {
        
        "monster_name": f"{floor_mob.emoji} {floor_mob.display}".strip(),
        "id": floor_mob.key,
        "monster_hp": hp, "monster_max_hp": hp, 
        "monster_attack": int(round(base_stats.get("attack", 0) * stat_mult)),
        "monster_defense": int(round(base_stats.get("defense", 0) * stat_mult)), 
        "monster_initiative": int(round(base_stats.get("initiative", 0) * stat_mult)),
        "monster_luck": base_stats.get("luck", 5),
        "monster_xp_reward": int(round(base_stats.get("xp_reward", 10) * stat_mult)),
        "monster_gold_drop": int(round(base_stats.get("gold_drop", 5) * gold_mult)),
        "loot_table": base_stats.get("loot_table", []),
        "file_id_name": floor_mob.media_key, "is_boss": bool(base_stats.get("is_boss", False)),
        "region_key": region_key, "difficulty": difficulty_cfg.key,
        "dungeon_ctx": {
            "dungeon_id": region_key,
            "difficulty": difficulty_cfg.key,
            "floor_idx": stage,
            "region": region_key
        },
        "dungeon_stage": stage, 
        "battle_log": [f"Você avança no calabouço ({difficulty_cfg.label})."],
    }

async def _start_first_fight(update: Update, context: ContextTypes.DEFAULT_TYPE, region_key: str, difficulty_key: str):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    query = update.callback_query
    
    dungeon = _load_region_dungeon(region_key)
    difficulty_cfg = DIFFICULTIES.get(difficulty_key)
    
    if not difficulty_cfg:
        await query.answer("Dificuldade inválida.", show_alert=True)
        return

    key_item = _key_item_for(dungeon)
    key_cost = _key_cost_for(difficulty_cfg)
    pdata = await player_manager.get_player_data(user_id) or {}
    
    if not _consume_keys(pdata, key_item, key_cost):
        try: await query.answer(f"Faltam {key_cost}x {key_item}.", show_alert=True)
        except: await context.bot.send_message(chat_id=chat_id, text=f"Faltam {key_cost}x {key_item}.")
        return

    floors: List[MobDef] = list(dungeon.get("floors") or [])
    if not floors:
        await context.bot.send_message(chat_id=chat_id, text="Erro: Calabouço vazio.")
        return

    await player_manager.save_player_data(user_id, pdata) 

    state = _new_run_state(region_key, difficulty_key)
    combat = _build_combat_details(floors[0], difficulty_cfg, region_key, 0)
    state["action"] = "in_combat"
    state["details"] = combat
    pdata["player_state"] = state

    cache_ctx = combat["dungeon_ctx"]
    set_pending_battle(user_id, cache_ctx)

    await player_manager.save_player_data(user_id, pdata)

    caption = await format_combat_message(pdata)
    kb = [
        [InlineKeyboardButton("⚔️ 𝐀𝐭𝐚𝐜𝐚𝐫", callback_data="combat_attack"), InlineKeyboardButton("✨ Skills", callback_data="combat_skill_menu")],
        [InlineKeyboardButton("🧪 Poções", callback_data="combat_potion_menu"), InlineKeyboardButton("🏃 𝐅𝐮𝐠𝐢𝐫", callback_data="combat_flee")]
    ]
    
    await _send_battle_media(context, chat_id, caption, combat.get("file_id_name"), reply_markup=InlineKeyboardMarkup(kb)) 

# ============================================================
# Lógica de Avanço e Ponte (Runtime API -> Runtime)
# ============================================================
async def resume_dungeon_after_battle(context: ContextTypes.DEFAULT_TYPE, user_id: int, dungeon_ctx: dict | None, victory: bool):
    if not victory:
        await fail_dungeon_run(None, context, user_id, user_id, "Derrota em combate")
        return

    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return

    run = pdata.get("player_state", {})
    details = run.get("details", {})
    
    # Validações de segurança
    if not dungeon_ctx or not details:
        return
    if str(details.get("region_key")) != str(dungeon_ctx.get("region")):
        logger.warning(f"Desincronia: {details.get('region_key')} != {dungeon_ctx.get('region')}")
        return

    rewards = {
        "xp": details.get("monster_xp_reward", 0),
        "gold": details.get("monster_gold_drop", 0),
        "items": [] 
    }

    await advance_after_victory(None, context, user_id, user_id, details, rewards)

async def fail_dungeon_run(update: Update | None, context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, reason: str):
    player_data = await player_manager.get_player_data(user_id)
    if player_data:
        total_stats = await player_manager.get_player_total_stats(player_data) 
        player_data['current_hp'] = total_stats.get('max_hp', 50)
        player_data['current_mp'] = total_stats.get('max_mana', 10)
        player_data["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(user_id, player_data)

    summary_text = f"❌ **Você falhou no calabouço!**\n\nMotivo: {reason}."
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("➡️ Continuar", callback_data="combat_return_to_map")]])

    if update and update.callback_query:
        try: await update.callback_query.delete_message()
        except Exception: pass
            
    await _send_battle_media(context, chat_id, summary_text, "media_dungeon_defeat", reply_markup)

async def advance_after_victory(update: Update | None, context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, combat_details: dict, rewards_to_accumulate: dict):
    pdata = await player_manager.get_player_data(user_id) or {}
    run = pdata.get("player_state") or {}
    det = (run.get("details") or {})
    det["last_fight_rewards"] = rewards_to_accumulate

    region_key = str(det.get("region_key") or "")
    difficulty_key = str(det.get("difficulty") or "iniciante")
    
    try:
        dungeon = _load_region_dungeon(region_key)
        difficulty_cfg = DIFFICULTIES.get(difficulty_key)
        if not difficulty_cfg: raise ValueError("Diff not found")
    except Exception:
        pdata["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(user_id, pdata)
        await context.bot.send_message(chat_id=chat_id, text="Erro ao carregar dados do calabouço.")
        return

    # =========================================================================
    # 👇 CORREÇÃO 1: ENTREGAR OS ITENS (BOSS E MOBS) 👇
    # =========================================================================
    # O main_handler passou os itens, mas eles estavam sendo ignorados.
    items_dropped = rewards_to_accumulate.get("items", [])
    if items_dropped:
        for item_id, qty, _ in items_dropped:
            # Entrega o item ao inventário do jogador
            player_manager.add_item_to_inventory(pdata, item_id, qty)
            logger.info(f"Dungeon Drop: {qty}x {item_id} para user {user_id}")
    # =========================================================================

    floors: List[MobDef] = list(dungeon.get("floors") or [])
    cur_stage = int(det.get("dungeon_stage", 0))
    next_stage = cur_stage + 1
    det["dungeon_stage"] = next_stage

    # --- VITÓRIA FINAL (BOSS) ---
    if next_stage >= len(floors):
        pdata.setdefault("dungeon_progress", {}).setdefault(region_key, {})
        current_highest = pdata["dungeon_progress"][region_key].get("highest_completed")
        try:
            if current_highest:
                if DEFAULT_DIFFICULTY_ORDER.index(difficulty_key) > DEFAULT_DIFFICULTY_ORDER.index(current_highest):
                    pdata["dungeon_progress"][region_key]["highest_completed"] = difficulty_key
            else:
                pdata["dungeon_progress"][region_key]["highest_completed"] = difficulty_key
        except Exception: pass

        final_gold = _final_gold_for(dungeon, difficulty_cfg) + rewards_to_accumulate.get("gold", 0)
        final_xp = rewards_to_accumulate.get("xp", 0)
        
        pdata['xp'] = int(pdata.get('xp', 0)) + final_xp
        if final_gold > 0: player_manager.add_gold(pdata, final_gold)
        
        # Recupera vida ao sair
        total_stats = await player_manager.get_player_total_stats(pdata)
        pdata['current_hp'] = total_stats.get('max_hp', 50)
        pdata['current_mp'] = total_stats.get('max_mana', 10)
        
        pdata["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(user_id, pdata)
        
        # =========================================================================
        # 👇 CORREÇÃO 2: MOSTRAR OS ITENS NO TEXTO DA VITÓRIA 👇
        # =========================================================================
        summary_text = (
            f"🏆 <b>Calabouço Concluído!</b> 🏆\n\n"
            f"Você venceu o desafio {difficulty_cfg.label}!\n"
            f"+{final_xp} XP\n+{final_gold} Ouro"
        )
        
        if items_dropped:
            summary_text += "\n\n<b>📦 Loot do Boss:</b>\n"
            for item_id, qty, _ in items_dropped:
                # Tenta buscar nome bonito se existir game_data disponível
                try:
                    item_def = game_data.ITEMS_DATA.get(item_id, {})
                    i_name = item_def.get("display_name", item_id)
                except:
                    i_name = item_id
                summary_text += f"• {qty}x {i_name}\n"
        # =========================================================================

        kb = [[InlineKeyboardButton("➡️ 𝐂𝐨𝐧𝐭𝐢𝐧𝐮𝐚𝐫", callback_data="combat_return_to_map")]]
        if update and update.callback_query:
            try: await update.callback_query.delete_message()
            except Exception: pass
            
        await _send_battle_media(context, chat_id, summary_text, "media_dungeon_victory", InlineKeyboardMarkup(kb))
        return

    # --- PRÓXIMO MOB ---
    logger.info(f"Avançando dungeon para estágio {next_stage}")
    combat = _build_combat_details(floors[next_stage], difficulty_cfg, region_key, next_stage)
    run["action"] = "in_combat"
    run["details"] = combat
    pdata["player_state"] = run
    await player_manager.save_player_data(user_id, pdata)

    cache_ctx = combat["dungeon_ctx"]
    set_pending_battle(user_id, cache_ctx)

    caption = await format_combat_message(pdata)
    kb = [
        [InlineKeyboardButton("⚔️ 𝐀𝐭𝐚𝐜𝐚𝐫", callback_data="combat_attack"), InlineKeyboardButton("✨ Skills", callback_data="combat_skill_menu")],
        [InlineKeyboardButton("🧪 Poções", callback_data="combat_potion_menu"), InlineKeyboardButton("🏃 𝐅𝐮𝐠𝐢𝐫", callback_data="combat_flee")]
    ]
    if update and update.callback_query:
        try: await update.callback_query.delete_message()
        except Exception: pass
            
    await _send_battle_media(context, chat_id, caption, combat.get("file_id_name"), reply_markup=InlineKeyboardMarkup(kb))

# ============================================================
# Handlers de Menu e Navegação
# ============================================================
async def _open_menu_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback para o botão 'dungeon_open:REGION'."""
    data = update.callback_query.data
    _, region_key = data.split(":", 1)
    await _open_menu(update, context, region_key)

async def _pick_diff_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback para a escolha da dificuldade."""
    data = update.callback_query.data
    parts = data.split(":")
    if len(parts) != 3: return
    _, diff, region_key = parts
    
    if update.callback_query.message:
        try: await update.callback_query.message.delete()
        except Exception: pass

    await _start_first_fight(update, context, region_key, diff)

async def _dungeon_locked_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("🔒 Complete a dificuldade anterior para desbloquear!", show_alert=True)

# ============================================================
# Handlers de Combate (Skills, Potions)
# ============================================================
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
    potion_ids = ["hp_potion_small", "hp_potion_medium", "mp_potion_small", "pocao_vida", "pocao_mana"]
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
    kb = [
        [InlineKeyboardButton("⚔️ Atacar", callback_data="combat_attack"), InlineKeyboardButton("✨ Skills", callback_data="combat_skill_menu")],
        [InlineKeyboardButton("🧪 Poções", callback_data="combat_potion_menu"), InlineKeyboardButton("🏃 Fugir", callback_data="combat_flee")]
    ]
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))

# Registro dos Handlers
dungeon_open_handler = CallbackQueryHandler(_open_menu_cb, pattern=r"^dungeon_open:[A-Za-z0-9_]+$")
dungeon_pick_handler = CallbackQueryHandler(_pick_diff_cb, pattern=r"^dungeon_pick:(iniciante|infernal|pesadelo):[A-Za-z0-9_]+$")
dungeon_locked_handler = CallbackQueryHandler(_dungeon_locked_cb, pattern=r'^dungeon_locked$')
combat_skill_handler = CallbackQueryHandler(open_combat_skill_menu, pattern="^combat_skill_menu$")
combat_potion_handler = CallbackQueryHandler(open_combat_potion_menu, pattern="^combat_potion_menu$")
combat_return_handler = CallbackQueryHandler(return_to_main_combat_menu, pattern="^combat_menu_return$")