# modules/dungeons/combat_hook.py
from __future__ import annotations
from typing import Dict, Any
from modules import player_manager
from modules.dungeons.runtime_api import set_pending_battle  # novo
from handlers.utils import format_combat_message
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def start_pve_battle(update, context, mob_state: Dict[str, Any]) -> None:
    """
    Dispara o combate interativo usando o seu combat_handler.
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # --- CORREÇÃO: Lemos os atributos diretamente do mob_state ---
    # Removemos a linha `stats = mob_state.get("stats", {})`
    combat_details = {
        "monster_name":       mob_state.get("name", "Inimigo"),
        "monster_hp":         int(mob_state.get("hp", 0)),
        "monster_max_hp":     int(mob_state.get("hp", 0)),
        "monster_attack":     int(mob_state.get("attack", 0)),
        "monster_defense":    int(mob_state.get("defense", 0)),
        "monster_initiative": int(mob_state.get("initiative", 0)),
        "monster_luck":       int(mob_state.get("luck", 0)),
        "monster_xp_reward":  int(mob_state.get("xp_reward", 10)), # Usando o nome correto
        "monster_gold_drop":  int(mob_state.get("gold_drop", 10)), # Usando o nome correto
        "loot_table":         list(mob_state.get("loot_table", [])),
        "flee_bias":          float(mob_state.get("flee_bias", 0.0)),

        "dungeon_ctx": {
            "dungeon_id": mob_state.get("dungeon_id"),
            "floor_idx":  mob_state.get("floor_idx"),
            "difficulty": mob_state.get("difficulty"),
            "region":     mob_state.get("region"),
        },
    }
    # --- FIM DA CORREÇÃO ---

    pdata = player_manager.get_player_data(user_id) or {}
    pdata["player_state"] = {"action": "in_combat", "details": combat_details}
    player_manager.save_player_data(user_id, pdata)

    set_pending_battle(user_id, combat_details["dungeon_ctx"])

    caption = format_combat_message(pdata)
    kb = [
        [InlineKeyboardButton("⚔️ Atacar", callback_data="combat_attack"), InlineKeyboardButton("🧪 Poções", callback_data="combat_potion_menu")],
        [InlineKeyboardButton("🏃 Fugir", callback_data="combat_flee")]
    ]
    await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
