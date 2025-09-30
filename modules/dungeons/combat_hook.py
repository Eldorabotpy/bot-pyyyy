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
    NÃO retorna vitória/derrota aqui. O resultado será reportado depois
    pelo próprio combat_handler via runtime_api.resume_after_battle(...).
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # 1) monta o "combat_details" do formato que seu combat_handler espera
    stats = mob_state.get("stats", {}) or {}
    combat_details = {
        "monster_name":  mob_state.get("display", "Inimigo"),
        "monster_hp":    int(stats.get("max_hp", 40)),
        "attack":        int(stats.get("attack", 8)),       # seu handler aceita 'attack' ou 'monster_attack'
        "defense":       int(stats.get("defense", 4)),
        "initiative":    int(stats.get("initiative", 4)),
        "luck":          int(stats.get("luck", 0)),
        "monster_xp_reward": int(mob_state.get("xp", 10)),
        "monster_gold_drop": int(mob_state.get("gold", 10)),
        "loot_table":    list(mob_state.get("loot", [])),
        "flee_bias":     float(mob_state.get("flee_bias", 0.0)),

        # 🔗 sinaliza para o combat_handler que isso veio da dungeon
        "dungeon_ctx": {
            "dungeon_id": mob_state.get("dungeon_id"),
            "floor_idx":  mob_state.get("floor_idx"),   # 0..N-1
            "difficulty": mob_state.get("difficulty"),
            "region":     mob_state.get("region"),
        },
    }

    # 2) coloca o jogador no estado de combate
    pdata = player_manager.get_player_data(user_id) or {}
    pdata["player_state"] = {"action": "in_combat", "details": combat_details}
    player_manager.save_player_data(user_id, pdata)

    # 3) marca a dungeon como “pendente de combate”
    set_pending_battle(user_id, combat_details["dungeon_ctx"])

    # 4) envia a mensagem inicial de combate (mesma UI do seu handler)
    caption = format_combat_message(pdata)
    kb = [[
        InlineKeyboardButton("⚔️ 𝐀𝐭𝐚𝐜𝐚𝐫", callback_data="combat_attack"),
        InlineKeyboardButton("🏃 𝐅𝐮𝐠𝐢𝐫",   callback_data="combat_flee"),
    ]]
    await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

    # ❗️Sem retorno de True/False aqui – o motor deve tratar como “adiado”.
