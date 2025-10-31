# modules/dungeons/runtime.py (Atualizado com Opção B + Edição de Mensagem)
from __future__ import annotations
import logging
from typing import List, Dict, Any
from collections import Counter 

# [MUDANÇA] Importa o tipo 'Message' para podermos retornar
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Message
from telegram.ext import CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest

from modules import player_manager, game_data, clan_manager
from handlers.utils import format_combat_message
from .config import DIFFICULTIES, DEFAULT_DIFFICULTY_ORDER, Difficulty
from .regions import REGIONAL_DUNGEONS, MobDef

# <<< CORREÇÃO DE SINTAXE APLICADA AQUI >>>
# Removidos os caracteres U+00A0
try:
    from modules import file_id_manager as media_ids
except Exception:
    media_ids = None

logger = logging.getLogger(__name__)


# ============================================================
# Helpers de inventário (Atualizados)
# ============================================================
def _inv(p: dict) -> dict:
    inv = p.get("inventory") or p.get("inventario") or {}
    return inv if isinstance(inv, dict) else {}

def _consume_keys(pdata: dict, key_item: str, key_cost: int) -> bool:
    # (Esta função já estava correta, verifica se tem chaves e consome)
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
# Registry loader (Lendo de regions.py e config.py)
# ============================================================
def _load_region_dungeon(region_key: str) -> dict:
    d = REGIONAL_DUNGEONS.get(region_key)
    if not d:
        logger.error(f"Tentativa de carregar calabouço não existente: {region_key}")
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

def _key_cost_for(difficulty_cfg: Difficulty) -> int:
    return difficulty_cfg.key_cost

def _key_item_for(dungeon_cfg: dict) -> str:
    return str(dungeon_cfg.get("key_item") or "cristal_de_abertura")

# ============================================================
# Botão para o menu da região (Sem alterações)
# ============================================================
def build_region_dungeon_button(region_key: str) -> InlineKeyboardButton:
    return InlineKeyboardButton("🏰 𝐂𝐚𝐥𝐚𝐛𝐨𝐮𝐜̧𝐨 🏰", callback_data=f"dungeon_open:{region_key}")

# ============================================================
# [MUDANÇA] Funções de Envio e Edição de Mensagem
# ============================================================
async def _send_battle_media(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    caption: str,
    file_id_name: str | None,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> Message | None: # [MUDANÇA] Retorna a mensagem que foi enviada
    """
    Envia a mídia (primeira luta) e retorna o objeto Message.
    """
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
                # [MUDANÇA] Adiciona 'return'
                return await context.bot.send_video( 
                    chat_id=chat_id, video=fd["id"], caption=caption,
                    parse_mode="HTML", reply_markup=reply_markup,
                )
            else:
                # [MUDANÇA] Adiciona 'return'
                return await context.bot.send_photo(
                    chat_id=chat_id, photo=fd["id"], caption=caption,
                    parse_mode="HTML", reply_markup=reply_markup,
                )
    except Exception as e:
        logger.debug("Falha ao enviar mídia (%s). Caindo para texto. %s", file_id_name, e)

    # fallback: texto
    # [MUDANÇA] Adiciona 'return'
    return await context.bot.send_message(
        chat_id=chat_id, text=caption,
        parse_mode="HTML", reply_markup=reply_markup,
    )

# [MUDANÇA] Nova função para editar a mensagem de batalha
async def _edit_battle_message(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    message_id: int,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
):
    """
    Tenta editar o caption da mídia de batalha. 
    Se a mídia não tiver caption (ex: fallback de texto), edita o texto.
    """
    try:
        await context.bot.edit_message_caption(
            chat_id=chat_id,
            message_id=message_id,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        return # Sucesso
    except BadRequest as e:
        if "not modified" in str(e).lower():
            return # Ignora, usuário clicou rápido demais

        # Se falhou (ex: era uma mensagem de texto), tenta editar o texto
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=caption,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception as e_text:
            logger.warning(f"Falha ao editar msg {message_id} (caption e texto): {e} / {e_text}")
            # Se tudo falhar, apaga a msg antiga e envia uma nova
            try: await context.bot.delete_message(chat_id, message_id)
            except Exception: pass
            await context.bot.send_message(chat_id, caption, reply_markup=reply_markup, parse_mode="HTML")


# ============================================================
# UI: abrir menu de dificuldade (Já editava a msg, está correto)
# ============================================================
async def _open_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, region_key: str):
    q = update.callback_query
    if q:
        try: await q.answer()
        except BadRequest: pass

    chat_id = update.effective_chat.id
    if not chat_id: return

    try:
        dungeon = _load_region_dungeon(region_key) 
    except RuntimeError as e:
        msg = "Calabouço desta região não está configurado." if str(e) == "dungeon_not_found" else "Sistema de calabouços não instalado."
        await context.bot.send_message(chat_id=chat_id, text=msg)
        return

    key_item = _key_item_for(dungeon)
    key_obj = (game_data.ITEMS_DATA or {}).get(key_item, {})
    key_name = f"{key_obj.get('emoji','🔹')} {key_obj.get('display_name', key_item)}"

    pdata = await player_manager.get_player_data(update.effective_user.id) or {}
    have = int((_inv(pdata)).get(key_item, 0))

    caption = (
        f"<b>{dungeon.get('label','Calabouço')}</b>\n"
        f"Região: <code>{region_key}</code>\n\n"
        f"🔑 Você tem: <b>{have} × {key_name}</b>\n\n"
        f"Escolha a dificuldade:"
    )

    kb = []
    dungeon_progress = (pdata.get("dungeon_progress", {}) or {}).get(region_key, {})
    highest_completed = dungeon_progress.get("highest_completed")
    highest_completed_index = -1
    if highest_completed:
        try:
            highest_completed_index = DEFAULT_DIFFICULTY_ORDER.index(highest_completed)
        except (ValueError, TypeError):
            pass 
    
    for i, diff_key in enumerate(DEFAULT_DIFFICULTY_ORDER):
        meta = DIFFICULTIES.get(diff_key)
        if not meta: continue
        key_cost = meta.key_cost

        if i <= highest_completed_index + 1:
            button_text = f"{meta.emoji} {meta.label} (🔑 {key_cost})"
            kb.append([
                InlineKeyboardButton(
                    button_text, 
                    callback_data=f"dungeon_pick:{diff_key}:{region_key}"
                )
            ])
        else:
            kb.append([
                InlineKeyboardButton(
                    f"🔒 {meta.label}", 
                    callback_data="dungeon_locked"
                )
            ])

    kb.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="continue_after_action")])

    # [MUDANÇA] Tenta apagar a mensagem da query (que é a de batalha)
    # e envia o menu como uma nova mensagem.
    try:
        if q:
            # Apaga a msg de batalha anterior
            await q.delete_message()
        # Envia o menu como uma msg nova
        await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    except Exception:
        # Fallback se apagar falhar (ex: msg muito antiga)
        try:
            await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        except Exception as e:
            logger.error(f"Falha ao enviar menu da dungeon: {e}")


# ============================================================
# Lógica de Combate (Refatorada para Opção B + Edição)
# ============================================================
def _new_run_state(region_key: str, difficulty: str) -> dict:
    return {
        "action": "dungeon_run",
        "details": {
            "region_key": region_key,
            "difficulty": difficulty,
            "dungeon_stage": 0,
            # [MUDANÇA] Não precisamos mais acumular
            # "accumulated_rewards" foi removido
            # Vamos salvar o loot do boss aqui
            "last_fight_rewards": {}
        }
    }

# "Fábrica" de Monstros (Sem alterações, já estava correta)
def _build_combat_details(
    floor_mob: MobDef, difficulty_cfg: Difficulty, region_key: str, stage: int
) -> dict:
    base_stats = floor_mob.stats_base
    stat_mult = difficulty_cfg.stat_mult
    hp = int(round(base_stats.get("max_hp", 1) * stat_mult))
    attack = int(round(base_stats.get("attack", 0) * stat_mult))
    defense = int(round(base_stats.get("defense", 0) * stat_mult))
    initiative = int(round(base_stats.get("initiative", 0) * stat_mult))
    is_boss = bool(base_stats.get("is_boss", False))
    return {
        "monster_name": f"{floor_mob.emoji} {floor_mob.display}".strip(),
        "monster_hp": hp, "monster_max_hp": hp, "monster_attack": attack,
        "monster_defense": defense, "monster_initiative": initiative,
        "monster_luck": base_stats.get("luck", 5),
        "monster_xp_reward": base_stats.get("xp_reward", 10),
        "monster_gold_drop": base_stats.get("gold_drop", 5),
        "loot_table": base_stats.get("loot_table", []),
        "file_id_name": floor_mob.media_key, "is_boss": is_boss,
        "region_key": region_key, "difficulty": difficulty_cfg.key, 
        "dungeon_ctx": True, "dungeon_stage": stage, 
        "battle_log": [f"Você avança no calabouço ({difficulty_cfg.label})."],
    }


async def _start_first_fight(update: Update, context: ContextTypes.DEFAULT_TYPE, region_key: str, difficulty_key: str):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    query = update.callback_query

    dungeon = _load_region_dungeon(region_key)
    difficulty_cfg = DIFFICULTIES.get(difficulty_key)
    if not difficulty_cfg:
        await query.answer("Dificuldade não encontrada.", show_alert=True)
        return

    key_item = _key_item_for(dungeon)
    key_cost = _key_cost_for(difficulty_cfg)
    pdata = await player_manager.get_player_data(user_id) or {}

    if not _consume_keys(pdata, key_item, key_cost):
        try:
            await query.answer(f"Você precisa de {key_cost}× {key_item} para entrar.", show_alert=True)
        except Exception:
            await context.bot.send_message(chat_id=chat_id, text=f"Você precisa de {key_cost}× {key_item} para entrar.")
        return

    floors: List[MobDef] = list(dungeon.get("floors") or [])
    if not floors:
        await context.bot.send_message(chat_id=chat_id, text="Este calabouço não tem andares configurados.")
        return

    # Salva o consumo da chave
    await player_manager.save_player_data(user_id, pdata)

    state = _new_run_state(region_key, difficulty_key)
    combat = _build_combat_details(
        floor_mob=floors[0], difficulty_cfg=difficulty_cfg,
        region_key=region_key, stage=0
    )

    state["action"] = "in_combat"
    state["details"] = combat
    pdata["player_state"] = state
    caption = await format_combat_message(pdata)
    kb = [
        [
            InlineKeyboardButton("⚔️ 𝐀𝐭𝐚𝐜𝐚𝐫", callback_data="combat_attack"),
            InlineKeyboardButton("✨ Skills", callback_data="combat_skill_menu")
        ],
        [
            InlineKeyboardButton("🧪 Poções", callback_data="combat_potion_menu"), 
            InlineKeyboardButton("🏃 𝐅𝐮𝐠𝐢𝐫", callback_data="combat_flee")
        ]
    ]

    # [MUDANÇA] Envia a msg de batalha e guarda o ID dela
    sent_message = await _send_battle_media(
        context, chat_id, caption, 
        combat.get("file_id_name"), 
        reply_markup=InlineKeyboardMarkup(kb)
    )

    if sent_message:
        pdata["player_state"]["details"]["battle_message_id"] = sent_message.message_id

    await player_manager.save_player_data(user_id, pdata) # Salva estado de combate + message_id


async def fail_dungeon_run(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, reason: str):
    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return

    # [MUDANÇA] Pega o ID da mensagem de batalha
    run = player_data.get("player_state") or {}
    det = (run.get("details") or {})
    battle_message_id = det.get("battle_message_id")

    total_stats = player_manager.get_player_total_stats(player_data)
    player_data['current_hp'] = total_stats.get('max_hp', 50)
    player_data['player_state'] = {'action': 'idle'}
    await player_manager.save_player_data(user_id, player_data)

    summary_text = f"❌ **Você falhou no calabouço!**\n\nMotivo: {reason}."
    keyboard = [[InlineKeyboardButton("➡️ Continuar", callback_data="continue_after_action")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # [MUDANÇA] Edita a mensagem de batalha com o sumário de falha
    if battle_message_id:
        await _edit_battle_message(
            context, chat_id, battle_message_id, 
            summary_text, reply_markup
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id, text=summary_text,
            parse_mode="HTML", reply_markup=reply_markup
        )

async def advance_after_victory(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, combat_details: dict, rewards_to_accumulate: dict):
    pdata = await player_manager.get_player_data(user_id) or {}
    clan_id = pdata.get("clan_id")

    if clan_id and combat_details.get("is_boss"):
        await clan_manager.update_guild_mission_progress(
            clan_id=clan_id, mission_type='DUNGEON_BOSS_KILL',
            details={'count': 1}, context=context
        )

    run = pdata.get("player_state") or {}
    det = (run.get("details") or {})
    
    # [MUDANÇA] Pega o ID da mensagem de batalha
    battle_message_id = det.get("battle_message_id")

    # [MUDANÇA - OPÇÃO B] 
    # Não acumulamos mais o loot. 
    # Apenas guardamos o loot da luta ATUAL, para o caso de ser o boss.
    det["last_fight_rewards"] = rewards_to_accumulate

    region_key = str(det.get("region_key") or "")
    difficulty_key = str(det.get("difficulty") or "normal")
    try:
        dungeon = _load_region_dungeon(region_key)
        difficulty_cfg = DIFFICULTIES.get(difficulty_key)
    except Exception:
        pdata["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(user_id, pdata)
        await context.bot.send_message(chat_id=chat_id, text="Calabouço foi encerrado (erro ao carregar).")
        return

    floors: List[MobDef] = list(dungeon.get("floors") or [])
    if not floors:
        pdata["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(user_id, pdata)
        await context.bot.send_message(chat_id=chat_id, text="Calabouço sem andares. Encerrado.")
        return

    cur_stage = int(det.get("dungeon_stage", 0))
    next_stage = cur_stage + 1
    det["dungeon_stage"] = next_stage

    # Verificação de Vitória Final
    if next_stage >= len(floors):
        if clan_id:
            await clan_manager.update_guild_mission_progress(
                clan_id=clan_id, mission_type='DUNGEON_COMPLETE',
                details={'dungeon_id': region_key, 'difficulty': difficulty_key, 'count': 1},
                context=context
            )

        # ... (Lógica de salvar progresso, sem alterações) ...
        completed_diff_key = difficulty_key
        pdata.setdefault("dungeon_progress", {}).setdefault(region_key, {})
        current_highest_key = pdata["dungeon_progress"][region_key].get("highest_completed")
        try:
            completed_index = DEFAULT_DIFFICULTY_ORDER.index(completed_diff_key)
            current_highest_index = -1
            if current_highest_key: current_highest_index = DEFAULT_DIFFICULTY_ORDER.index(current_highest_key)
            if completed_index > current_highest_index:
                pdata["dungeon_progress"][region_key]["highest_completed"] = completed_diff_key
                logger.info(f"PROGRESSO ATUALIZADO user {user_id} em '{region_key}': {completed_diff_key}")
        except (ValueError, TypeError):
            logger.warning(f"Chave de dificuldade inválida: '{current_highest_key}', '{completed_diff_key}'")

        # [MUDANÇA - OPÇÃO B] Aplicação de recompensas
        # Pega o loot do boss (da última luta)
        boss_rewards = det.get("last_fight_rewards", {})
        final_xp = boss_rewards.get("xp", 0)
        final_gold = boss_rewards.get("gold", 0)
        final_items = boss_rewards.get("items", [])
        
        # Adiciona o bônus de ouro do calabouço
        final_gold += _final_gold_for(dungeon, difficulty_cfg)

        pdata['xp'] = int(pdata.get('xp', 0)) + final_xp
        if final_gold > 0: player_manager.add_gold(pdata, final_gold)

        looted_items_text = ""
        if final_items:
            for item_id in final_items: player_manager.add_item_to_inventory(pdata, item_id, 1)
            item_names = [(game_data.ITEMS_DATA.get(item_id, {}) or {}).get('display_name', item_id) for item_id in final_items]
            looted_items_text = "\n\n<b>Tesouros Adquiridos:</b>\n"
            for name, count in Counter(item_names).items(): looted_items_text += f"- {count}x {name}\n"

        pdata["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(user_id, pdata) # Salva tudo

        summary_text = (
            f"🏆 <b>Calabouço Concluído!</b> 🏆\n\n"
            f"Você superou todos os desafios e reclamou suas recompensas:\n"
            f"+{final_xp:,} XP\n"
            f"+{final_gold:,} Ouro"
            f"{looted_items_text}"
        )
        keyboard = [[InlineKeyboardButton("➡️ 𝐂𝐨𝐧𝐭𝐢𝐧𝐮𝐚𝐫", callback_data="continue_after_action")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # [MUDANÇA] Edita a mensagem de batalha com o sumário de vitória
        if battle_message_id:
            await _edit_battle_message(
                context, chat_id, battle_message_id, 
                summary_text, reply_markup
            )
        else:
            await context.bot.send_message(chat_id=chat_id, text=summary_text, parse_mode="HTML", reply_markup=reply_markup)
        return

    # Próximo combate (NÃO é o final)
    combat = _build_combat_details(
        floor_mob=floors[next_stage],
        difficulty_cfg=difficulty_cfg,
        region_key=region_key, 
        stage=next_stage
    )
    run["action"] = "in_combat"
    run["details"] = combat
    pdata["player_state"] = run
    
    # [MUDANÇA] Atualiza o ID da msg de batalha no estado
    if battle_message_id:
        pdata["player_state"]["details"]["battle_message_id"] = battle_message_id

    await player_manager.save_player_data(user_id, pdata) # Salva o estado

    caption = await format_combat_message(pdata)
    kb = [
        [
            InlineKeyboardButton("⚔️ 𝐀𝐭𝐚𝐜𝐚𝐫", callback_data="combat_attack"),
            InlineKeyboardButton("✨ Skills", callback_data="combat_skill_menu")
        ],
        [
            InlineKeyboardButton("🧪 Poções", callback_data="combat_potion_menu"), 
            InlineKeyboardButton("🏃 𝐅𝐮𝐠𝐢𝐫", callback_data="combat_flee")
        ]
    ]
    
    # [MUDANÇA] Edita a mensagem de batalha com o próximo combate
    if battle_message_id:
        await _edit_battle_message(
            context, chat_id, battle_message_id, 
            caption, InlineKeyboardMarkup(kb)
        )
    else:
        # Fallback caso o ID tenha se perdido
        await _send_battle_media(context, chat_id, caption, combat.get("file_id_name"), reply_markup=InlineKeyboardMarkup(kb))


# ============================================================
# Handlers (Sem alterações, já estavam corretos)
# ============================================================
async def _open_menu_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    _, region_key = data.split(":", 1)
    await _open_menu(update, context, region_key)

async def _pick_diff_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    parts = data.split(":")
    if len(parts) != 3:
        await update.callback_query.answer("Escolha inválida.", show_alert=True)
        return
    _, diff, region_key = parts
    if diff not in DIFFICULTIES:
        await update.callback_query.answer("Dificuldade inválida.", show_alert=True)
        return
    
    # [MUDANÇA] Apaga a mensagem do menu antes de começar a luta
    try:
        if update.callback_query:
            await update.callback_query.delete_message()
    except Exception:
        pass # Ignora se falhar

    await _start_first_fight(update, context, region_key, diff)

async def _dungeon_locked_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Você precisa de completar a dificuldade anterior para desbloquear esta!", show_alert=True)

dungeon_open_handler = CallbackQueryHandler(_open_menu_cb, pattern=r"^dungeon_open:[A-Za-z0-9_]+$")
dungeon_pick_handler = CallbackQueryHandler(_pick_diff_cb, pattern=r"^dungeon_pick:(iniciante|infernal|pesadelo):[A-Za-z0-9_]+$")
dungeon_locked_handler = CallbackQueryHandler(_dungeon_locked_cb, pattern=r'^dungeon_locked$')