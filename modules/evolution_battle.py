# modules/evolution_battle.py
from __future__ import annotations

import logging
from typing import Optional, Union

from bson import ObjectId
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from modules import player_manager
from modules.game_data.monsters import MONSTERS_DATA
from modules.game_data import class_evolution as evo_data
from modules import file_ids as file_id_manager
from handlers.utils import format_combat_message

# ID do jogador via sessão/login (async)
try:
    from modules.auth_utils import get_current_player_id_async
except Exception:  # pragma: no cover
    get_current_player_id_async = None  # type: ignore


logger = logging.getLogger(__name__)
PlayerId = Union[ObjectId, str]


def _normalize_objectid(pid: Union[ObjectId, str, None]) -> Optional[ObjectId]:
    if pid is None:
        return None
    if isinstance(pid, ObjectId):
        return pid
    if isinstance(pid, str) and ObjectId.is_valid(pid.strip()):
        return ObjectId(pid.strip())
    return None


async def _get_player_id_from_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[ObjectId]:
    """
    Padrão: pega o jogador autenticado (ObjectId) via sessão/login.
    Fallback: context.user_data['logged_player_id'] se existir.
    """
    pid = None
    if get_current_player_id_async:
        try:
            pid = await get_current_player_id_async(update, context)
        except Exception:
            pid = None

    if not pid:
        pid = context.user_data.get("logged_player_id")

    return _normalize_objectid(pid)


async def start_evolution_presentation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: PlayerId,
    target_class: str
):
    """
    FASE 1: Tela de Apresentação (VS).
    Recebe user_id como ObjectId ou string válida de ObjectId.
    """
    chat_id = update.effective_chat.id

    oid = _normalize_objectid(user_id)
    if not oid:
        await context.bot.send_message(chat_id, "⚠️ Erro: ID do jogador inválido (sessão).")
        return

    pdata = await player_manager.get_player_data(oid)
    if not pdata:
        await context.bot.send_message(chat_id, "⚠️ Erro: Jogador não encontrado no banco de dados novo.")
        return

    # 1. Busca Evolução e Monstro
    evo_opt = evo_data.find_evolution_by_target(target_class)
    if not evo_opt:
        await context.bot.send_message(chat_id, "⚠️ Erro: Evolução não encontrada.")
        return

    monster_id = evo_opt.get("trial_monster_id")
    monster_data = None

    # Procura na lista especial primeiro
    if "_evolution_trials" in MONSTERS_DATA:
        for m in MONSTERS_DATA["_evolution_trials"]:
            if m.get("id") == monster_id:
                monster_data = m
                break

    # Procura nas listas gerais
    if not monster_data:
        monster_data = MONSTERS_DATA.get(monster_id)

    if not monster_data:
        await context.bot.send_message(chat_id, f"⚠️ Erro: Guardião '{monster_id}' não configurado.")
        return

    # 2. Cura e Salva Estado
    await player_manager.full_restore(oid)

    pdata["player_state"] = {
        "action": "evolution_lobby",
        "details": {
            "target_class": target_class,
            "monster_id": monster_id,
            "monster_data_snapshot": monster_data
        }
    }
    await player_manager.save_player_data(oid, pdata)

    # 3. Monta Texto e Botão
    monster_name = monster_data.get("name", "Guardião")
    hp = monster_data.get("hp", 1000)
    atk = monster_data.get("attack", 100)

    caption = (
        f"⚡ <b>PROVAÇÃO DE {target_class.upper()}</b> ⚡\n\n"
        f"O <b>{monster_name}</b> bloqueia seu destino!\n"
        f"<i>\"Apenas os dignos herdam este poder. Prove seu valor!\"</i>\n\n"
        f"📊 <b>Atributos do Inimigo:</b>\n"
        f"❤️ HP: {hp} | ⚔️ ATK: {atk}\n\n"
        f"✨ <i>Você foi curado completamente para este duelo.</i>"
    )

    kb = [[InlineKeyboardButton("⚔️ COMEÇAR DUELO ⚔️", callback_data="start_evo_combat")]]
    reply_markup = InlineKeyboardMarkup(kb)

    # 4. Envia Mídia
    media_key = monster_data.get("media_key")
    file_info = file_id_manager.get_file_data(media_key)

    if update.callback_query:
        try:
            await update.callback_query.message.delete()
        except Exception:
            pass

    try:
        if file_info:
            if file_info.get("type") == "video":
                await context.bot.send_video(
                    chat_id,
                    video=file_info["id"],
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            else:
                await context.bot.send_photo(
                    chat_id,
                    photo=file_info["id"],
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
        else:
            await context.bot.send_message(chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Erro ao enviar VS screen: {e}")
        await context.bot.send_message(chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")


async def start_evo_combat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    FASE 2: Início do Combate (o botão foi clicado).
    """
    query = update.callback_query
    await query.answer("⚔️ A arena se fecha...")

    chat_id = query.message.chat_id

    player_id = await _get_player_id_from_session(update, context)
    if not player_id:
        await context.bot.send_message(chat_id, "⚠️ Erro crítico: Sessão de usuário não encontrada.")
        return

    pdata = await player_manager.get_player_data(player_id)
    if not pdata:
        await context.bot.send_message(chat_id, "⚠️ Erro crítico: Jogador não encontrado.")
        return

    state = pdata.get("player_state", {}) or {}
    if state.get("action") != "evolution_lobby":
        await context.bot.send_message(chat_id, "⚠️ Sessão expirada. Volte ao menu.")
        return

    details = state.get("details", {}) or {}
    monster_data = details.get("monster_data_snapshot", {}) or {}

    combat_details = {
        "monster_name": monster_data.get("name"),
        "monster_hp": int(monster_data.get("hp", 0)),
        "monster_max_hp": int(monster_data.get("hp", 0)),
        "monster_attack": int(monster_data.get("attack", 0)),
        "monster_defense": int(monster_data.get("defense", 0)),
        "monster_initiative": int(monster_data.get("initiative", 0)),
        "monster_luck": int(monster_data.get("luck", 0)),
        "monster_xp_reward": 0,
        "monster_gold_drop": 0,
        "loot_table": [],
        "id": monster_data.get("id"),
        "file_id_name": monster_data.get("media_key"),
        "is_evolution_trial": True,
        "target_class_reward": details.get("target_class"),
        "battle_log": [f"⚔️ O duelo contra {monster_data.get('name')} começou!"]
    }

    pdata["player_state"] = {
        "action": "evolution_combat",
        "details": combat_details
    }
    await player_manager.save_player_data(player_id, pdata)

    caption = await format_combat_message(pdata)

    kb = [
        [InlineKeyboardButton("⚔️ Atacar", callback_data="combat_attack"),
         InlineKeyboardButton("✨ Skills", callback_data="combat_skill_menu")],
        [InlineKeyboardButton("🧪 Poções", callback_data="combat_potion_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(kb)

    try:
        await query.message.delete()
    except Exception:
        pass

    media_key = combat_details.get("file_id_name")
    file_info = file_id_manager.get_file_data(media_key)

    try:
        if file_info:
            if file_info.get("type") == "video":
                await context.bot.send_video(
                    chat_id,
                    video=file_info["id"],
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            else:
                await context.bot.send_photo(
                    chat_id,
                    photo=file_info["id"],
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
        else:
            await context.bot.send_message(
                chat_id,
                text=f"👹 <b>{combat_details['monster_name']}</b>\n\n{caption}",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Erro crítico ao iniciar combat UI: {e}")
        await context.bot.send_message(chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")
