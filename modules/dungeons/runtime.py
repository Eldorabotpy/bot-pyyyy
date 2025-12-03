# modules/dungeons/runtime.py
from __future__ import annotations
import logging
import random # Importante para calcular drops aleatórios
from typing import List, Dict, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest

from modules import player_manager, game_data
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
# UI Functions
# ============================================================
def build_region_dungeon_button(region_key: str) -> InlineKeyboardButton:
    return InlineKeyboardButton("🏰 𝐂𝐚𝐥𝐚𝐛𝐨𝐮𝐜̧𝐨 🏰", callback_data=f"dungeon_open:{region_key}")

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
        except Exception:
            pass

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
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=chat_id, text=caption,
        parse_mode="HTML", reply_markup=reply_markup,
    )

# ============================================================
# Lógica do Menu
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
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Esta região ainda não tem um calabouço configurado.")
        return

    key_item = _key_item_for(dungeon)
    # Tenta pegar info bonita do item, ou usa o ID cru
    key_display = key_item.replace("_", " ").title()
    if game_data.ITEMS_DATA:
        k_data = game_data.ITEMS_DATA.get(key_item, {})
        if k_data:
            key_display = f"{k_data.get('emoji','🔹')} {k_data.get('display_name', key_display)}"

    pdata = await player_manager.get_player_data(update.effective_user.id) or {}
    have = int((_inv(pdata)).get(key_item, 0))

    caption = (
        f"<b>{dungeon.get('label','Calabouço')}</b>\n"
        f"Região: <code>{region_key}</code>\n\n"
        f"🗝️ Entrada: <b>{key_display}</b>\n"
        f"🎒 Você tem: <b>{have}</b>\n\n"
        f"Escolha a dificuldade:"
    )

    kb = []
    dungeon_progress = (pdata.get("dungeon_progress", {}) or {}).get(region_key, {})
    highest_completed = dungeon_progress.get("highest_completed")
    highest_completed_index = -1
    
    # Descobre o índice da maior dificuldade completada
    if highest_completed and highest_completed in DEFAULT_DIFFICULTY_ORDER:
        highest_completed_index = DEFAULT_DIFFICULTY_ORDER.index(highest_completed)
    
    for i, diff_key in enumerate(DEFAULT_DIFFICULTY_ORDER):
        meta = DIFFICULTIES.get(diff_key)
        if not meta: continue
        
        # Lógica de desbloqueio: Pode jogar se i <= (index completado + 1)
        # Ex: Se completou 0 (iniciante), pode jogar 1 (infernal).
        if i <= highest_completed_index + 1:
            button_text = f"{meta.emoji} {meta.label} ( -{meta.key_cost} chaves)"
            kb.append([InlineKeyboardButton(button_text, callback_data=f"dungeon_pick:{diff_key}:{region_key}")])
        else:
            kb.append([InlineKeyboardButton(f"🔒 {meta.label}", callback_data="dungeon_locked")])
            
    kb.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="continue_after_action")])
    
    reply_markup = InlineKeyboardMarkup(kb)
    menu_media_key = dungeon.get("menu_media_key") 
    await _send_battle_media(context, chat_id, caption, menu_media_key, reply_markup)

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
    
    return {
        "monster_name": f"{floor_mob.emoji} {floor_mob.display}",
        "id": floor_mob.key,
        "monster_hp": hp, "monster_max_hp": hp, 
        "monster_attack": int(round(base_stats.get("attack", 5) * stat_mult)),
        "monster_defense": int(round(base_stats.get("defense", 0) * stat_mult)), 
        "monster_initiative": int(round(base_stats.get("initiative", 5) * stat_mult)),
        "monster_luck": base_stats.get("luck", 5),
        
        "monster_xp_reward": int(round(base_stats.get("xp_reward", 20) * stat_mult)),
        "monster_gold_drop": int(round(base_stats.get("gold_drop", 10) * gold_mult)),
        
        # A lista de loot original (com chances) é passada para o combat hook
        # O runtime não processa o drop, quem processa é a victory logic ou combat engine.
        "loot_table": base_stats.get("loot_table", []),
        
        "file_id_name": floor_mob.media_key, 
        "is_boss": bool(base_stats.get("is_boss", False)),
        
        # Campos cruciais para o sistema saber onde estamos
        "region_key": region_key, 
        "difficulty": difficulty_cfg.key,
        
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
    
    try:
        dungeon = _load_region_dungeon(region_key)
    except Exception as e:
        await query.answer(f"Erro ao carregar calabouço: {e}", show_alert=True)
        return

    difficulty_cfg = DIFFICULTIES.get(difficulty_key)
    if not difficulty_cfg:
        await query.answer("Dificuldade inválida.", show_alert=True)
        return

    key_item = _key_item_for(dungeon)
    key_cost = _key_cost_for(difficulty_cfg)
    pdata = await player_manager.get_player_data(user_id) or {}
    
    if not _consume_keys(pdata, key_item, key_cost):
        try: await query.answer(f"Você precisa de {key_cost}x {key_item}.", show_alert=True)
        except: pass
        return

    floors: List[MobDef] = list(dungeon.get("floors") or [])
    if not floors:
        await context.bot.send_message(chat_id=chat_id, text="Erro: Este calabouço está vazio (sem monstros).")
        return

    # Inicia o estado
    state = _new_run_state(region_key, difficulty_key)
    # Pega o primeiro mob
    try:
        combat = _build_combat_details(floors[0], difficulty_cfg, region_key, 0)
    except Exception as e:
        logger.error(f"Erro ao buildar mob 0: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Erro interno ao criar monstro.")
        return

    state["action"] = "in_combat"
    state["details"] = combat
    pdata["player_state"] = state
    
    await player_manager.save_player_data(user_id, pdata)
    
    # Registra na API de runtime (memória)
    set_pending_battle(user_id, combat["dungeon_ctx"])

    caption = await format_combat_message(pdata)
    kb = [
        [InlineKeyboardButton("⚔️ 𝐀𝐭𝐚𝐜𝐚𝐫", callback_data="combat_attack"), InlineKeyboardButton("✨ Skills", callback_data="combat_skill_menu")],
        [InlineKeyboardButton("🧪 Poções", callback_data="combat_potion_menu"), InlineKeyboardButton("🏃 𝐅𝐮𝐠𝐢𝐫", callback_data="combat_flee")]
    ]
    
    await _send_battle_media(context, chat_id, caption, combat.get("file_id_name"), reply_markup=InlineKeyboardMarkup(kb)) 

# ============================================================
# Avanço Pós-Combate (AQUI ESTAVA O PROBLEMA)
# ============================================================
async def resume_dungeon_after_battle(context: ContextTypes.DEFAULT_TYPE, user_id: int, dungeon_ctx: dict | None, victory: bool):
    """
    Chamado quando o combate termina.
    """
    if not victory:
        await fail_dungeon_run(None, context, user_id, user_id, "Derrotado em combate")
        return

    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return

    run = pdata.get("player_state", {})
    details = run.get("details", {})
    
    # --- CURA DE ERRO CRÍTICO ---
    # Se dungeon_ctx for None (bot reiniciou e limpou RAM), tentamos recuperar do DB
    if not dungeon_ctx:
        logger.warning(f"Dungeon Context perdido na RAM para user {user_id}. Recuperando do DB...")
        dungeon_ctx = details.get("dungeon_ctx")
    
    # Se ainda assim não tiver contexto, não é uma run de dungeon
    if not dungeon_ctx:
        return

    # Validação de segurança básica
    if str(details.get("region_key")) != str(dungeon_ctx.get("region")):
        logger.warning(f"Desincronia detectada: {details.get('region_key')} != {dungeon_ctx.get('region')}")
        # Se houver desincronia, confiamos no DB (details)
        dungeon_ctx["region"] = details.get("region_key")

    # Calculamos os drops aqui (já que a engine de combate pode não ter passado)
    dropped_items = []
    loot_table = details.get("loot_table", [])
    if loot_table:
        for entry in loot_table:
            item_id = entry.get("item_id")
            chance = entry.get("drop_chance", 0)
            # Rola o dado (0-100)
            if random.uniform(0, 100) <= chance:
                dropped_items.append((item_id, 1, {}))

    rewards = {
        "xp": details.get("monster_xp_reward", 0),
        "gold": details.get("monster_gold_drop", 0),
        "items": dropped_items
    }

    await advance_after_victory(None, context, user_id, user_id, details, rewards)

async def fail_dungeon_run(update: Update | None, context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, reason: str):
    pdata = await player_manager.get_player_data(user_id)
    if pdata:
        # Reseta o player para Idle e recupera HP/MP
        total_stats = await player_manager.get_player_total_stats(pdata) 
        pdata['current_hp'] = total_stats.get('max_hp', 50)
        pdata['current_mp'] = total_stats.get('max_mana', 10)
        pdata["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(user_id, pdata)

    summary_text = f"💀 **Fim da Linha!**\n\nVocê caiu no calabouço.\nMotivo: {reason}."
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("⚰️ Retornar", callback_data="combat_return_to_map")]])
    await _send_battle_media(context, chat_id, summary_text, "media_dungeon_defeat", reply_markup)

async def advance_after_victory(update: Update | None, context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, combat_details: dict, rewards: dict):
    pdata = await player_manager.get_player_data(user_id) or {}
    run = pdata.get("player_state") or {}
    
    # Acumula recompensas da luta que acabou de vencer
    # (Poderíamos guardar em 'run' se quiséssemos entregar só no final, mas vamos entregar já)
    
    xp_gain = rewards.get("xp", 0)
    gold_gain = rewards.get("gold", 0)
    items_gain = rewards.get("items", [])

    # Entrega imediata de XP e Ouro do mob (opcional, pode ser só no final)
    pdata['xp'] = int(pdata.get('xp', 0)) + xp_gain
    if gold_gain > 0:
        player_manager.add_gold(pdata, gold_gain)
    
    # Entrega ITENS agora
    if items_gain:
        for i_id, i_qty, _ in items_gain:
            player_manager.add_item_to_inventory(pdata, i_id, i_qty)
            logger.info(f"Item Drop: {i_id} x{i_qty} para {user_id}")

    region_key = str(combat_details.get("region_key") or "")
    difficulty_key = str(combat_details.get("difficulty") or "iniciante")
    
    try:
        dungeon = _load_region_dungeon(region_key)
        difficulty_cfg = DIFFICULTIES.get(difficulty_key)
        if not difficulty_cfg: raise ValueError("Dificuldade perdida")
    except Exception as e:
        logger.error(f"Erro crítico no advance: {e}")
        await fail_dungeon_run(None, context, user_id, chat_id, "Erro nos dados do calabouço")
        return

    floors: List[MobDef] = list(dungeon.get("floors") or [])
    cur_stage = int(combat_details.get("dungeon_stage", 0))
    next_stage = cur_stage + 1
    
    # Atualiza o stage no run state (ainda não salvo)
    # run['details'] será sobrescrito se houver próximo mob
    
    # --- CHECK DE VITÓRIA FINAL ---
    if next_stage >= len(floors):
        # >> VITORIA DO CALABOUÇO <<
        
        # 1. Salva Progresso
        pdata.setdefault("dungeon_progress", {}).setdefault(region_key, {})
        current_highest = pdata["dungeon_progress"][region_key].get("highest_completed")
        
        # Verifica se essa diff é maior que a atual
        try:
            curr_idx = -1
            if current_highest in DEFAULT_DIFFICULTY_ORDER:
                curr_idx = DEFAULT_DIFFICULTY_ORDER.index(current_highest)
            new_idx = DEFAULT_DIFFICULTY_ORDER.index(difficulty_key)
            
            if new_idx > curr_idx:
                pdata["dungeon_progress"][region_key]["highest_completed"] = difficulty_key
            elif not current_highest:
                pdata["dungeon_progress"][region_key]["highest_completed"] = difficulty_key
        except Exception: 
            # Fallback
            pdata["dungeon_progress"][region_key]["highest_completed"] = difficulty_key

        # 2. Recompensa Final (Bônus por completar)
        final_gold_bonus = _final_gold_for(dungeon, difficulty_cfg)
        if final_gold_bonus > 0:
            player_manager.add_gold(pdata, final_gold_bonus)
        
        # 3. Restaura Player
        total_stats = await player_manager.get_player_total_stats(pdata)
        pdata['current_hp'] = total_stats.get('max_hp', 50)
        pdata['current_mp'] = total_stats.get('max_mana', 10)
        pdata["player_state"] = {"action": "idle"}
        
        await player_manager.save_player_data(user_id, pdata)
        
        # 4. Mensagem Final
        summary_text = (
            f"🏆 <b>CALABOUÇO CONCLUÍDO!</b> 🏆\n\n"
            f"Você dominou {dungeon.get('label')} na dificuldade {difficulty_cfg.label}!\n"
            f"💰 Bônus de Ouro: {final_gold_bonus}\n"
        )
        
        # Mostra o loot do último mob (BOSS) se houver
        if items_gain:
            summary_text += "\n<b>📦 Loot Obtido:</b>\n"
            for i_id, i_qty, _ in items_gain:
                d_name = i_id.replace("_", " ").title()
                summary_text += f"• {i_qty}x {d_name}\n"

        kb = [[InlineKeyboardButton("🎉 Continuar", callback_data="combat_return_to_map")]]
        await _send_battle_media(context, chat_id, summary_text, "media_dungeon_victory", InlineKeyboardMarkup(kb))
        return

    # --- PRÓXIMO MOB ---
    logger.info(f"Avançando dungeon {region_key} para andar {next_stage}")
    
    try:
        next_mob = floors[next_stage]
        combat = _build_combat_details(next_mob, difficulty_cfg, region_key, next_stage)
    except IndexError:
        # Isso não deve acontecer devido ao check de len(floors), mas por segurança
        await fail_dungeon_run(None, context, user_id, chat_id, "Erro interno (Andar inexistente)")
        return

    # Atualiza estado do jogador
    run["action"] = "in_combat"
    run["details"] = combat
    pdata["player_state"] = run
    await player_manager.save_player_data(user_id, pdata)

    # Atualiza API (Memória)
    set_pending_battle(user_id, combat["dungeon_ctx"])

    # Envia nova batalha
    caption = await format_combat_message(pdata)
    kb = [
        [InlineKeyboardButton("⚔️ 𝐀𝐭𝐚𝐜𝐚𝐫", callback_data="combat_attack"), InlineKeyboardButton("✨ Skills", callback_data="combat_skill_menu")],
        [InlineKeyboardButton("🧪 Poções", callback_data="combat_potion_menu"), InlineKeyboardButton("🏃 𝐅𝐮𝐠𝐢𝐫", callback_data="combat_flee")]
    ]
    
    await _send_battle_media(context, chat_id, caption, combat.get("file_id_name"), reply_markup=InlineKeyboardMarkup(kb))


# ============================================================
# Handlers
# ============================================================
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
    await update.callback_query.answer("🔒 Complete a dificuldade anterior para desbloquear esta!", show_alert=True)

# Callbacks de Combate (Auxiliares)
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
    # IDs comuns de poções
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
    kb = [
        [InlineKeyboardButton("⚔️ Atacar", callback_data="combat_attack"), InlineKeyboardButton("✨ Skills", callback_data="combat_skill_menu")],
        [InlineKeyboardButton("🧪 Poções", callback_data="combat_potion_menu"), InlineKeyboardButton("🏃 Fugir", callback_data="combat_flee")]
    ]
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))

# Registro
dungeon_open_handler = CallbackQueryHandler(_open_menu_cb, pattern=r"^dungeon_open:[A-Za-z0-9_]+$")
dungeon_pick_handler = CallbackQueryHandler(_pick_diff_cb, pattern=r"^dungeon_pick:[A-Za-z0-9_]+:[A-Za-z0-9_]+$")
dungeon_locked_handler = CallbackQueryHandler(_dungeon_locked_cb, pattern=r'^dungeon_locked$')
combat_skill_handler = CallbackQueryHandler(open_combat_skill_menu, pattern="^combat_skill_menu$")
combat_potion_handler = CallbackQueryHandler(open_combat_potion_menu, pattern="^combat_potion_menu$")
combat_return_handler = CallbackQueryHandler(return_to_main_combat_menu, pattern="^combat_menu_return$")