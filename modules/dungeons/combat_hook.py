# modules/dungeons/combat_hook.py
from __future__ import annotations
from typing import Dict, Any
from modules import player_manager
from modules.dungeons.runtime_api import set_pending_battle
from handlers.utils import format_combat_message
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ContextTypes # Importa Update e ContextTypes
from modules.auth_utils import get_current_player_id

# (Certifica-te de que 'logging' está importado no topo do ficheiro, se ainda não estiver)
import logging
logger = logging.getLogger(__name__)


async def start_pve_battle(update: Update, context: ContextTypes.DEFAULT_TYPE, mob_state: Dict[str, Any]) -> None:
    """
    Dispara o combate interativo usando o seu combat_handler.
    (Versão corrigida com async/await E botão de Skills)
    """
    user_id = get_current_player_id(update, context)
    chat_id = update.effective_chat.id

    # --- Bloco síncrono (Correto) ---
    combat_details = {
        "monster_name":       mob_state.get("name", "Inimigo"),
        "monster_hp":         int(mob_state.get("hp", 0)),
        "monster_max_hp":     int(mob_state.get("hp", 0)),
        "monster_attack":     int(mob_state.get("attack", 0)),
        "monster_defense":    int(mob_state.get("defense", 0)),
        "monster_initiative": int(mob_state.get("initiative", 0)),
        "monster_luck":       int(mob_state.get("luck", 0)),
        "monster_xp_reward":  int(mob_state.get("xp_reward", 10)),
        "monster_gold_drop":  int(mob_state.get("gold_drop", 10)),
        "loot_table":         list(mob_state.get("loot_table", [])),
        "flee_bias":          float(mob_state.get("flee_bias", 0.0)),
        "dungeon_ctx": {
            "dungeon_id": mob_state.get("dungeon_id"),
            "floor_idx":  mob_state.get("floor_idx"),
            "difficulty": mob_state.get("difficulty"),
            "region":     mob_state.get("region"),
        },
        # Adiciona um log de batalha inicial
        "battle_log": [f"Um {mob_state.get('name', 'Inimigo')} selvagem aparece!"]
    }
    # --- Fim do Bloco ---

    # <<< CORREÇÃO 1: Adiciona await >>>
    pdata = await player_manager.get_player_data(user_id) or {}
    
    pdata["player_state"] = {"action": "in_combat", "details": combat_details} # Síncrono

    # <<< CORREÇÃO 2: Adiciona await >>>
    await player_manager.save_player_data(user_id, pdata)

    # <<< CORREÇÃO 3: Adiciona await (Assumindo que set_pending_battle é async) >>>
    # Se esta função for síncrona, remove o await.
    set_pending_battle(user_id, combat_details["dungeon_ctx"])

    caption = format_combat_message(pdata) # Síncrono

    # =====================================================
    # --- TECLADO ATUALIZADO ---
    # =====================================================
    kb = [
        [
            InlineKeyboardButton("⚔️ Atacar", callback_data="combat_attack"), 
            # 👇 BOTÃO ADICIONADO 👇
            InlineKeyboardButton("✨ Skills", callback_data="combat_skill_menu") 
        ],
        [
            InlineKeyboardButton("🧪 Poções", callback_data="combat_potion_menu"), 
            InlineKeyboardButton("🏃 Fugir", callback_data="combat_flee")
        ]
    ]
    # =====================================================

    # Await já estava correto aqui
    await context.bot.send_message(
        chat_id=chat_id, 
        text=caption, 
        reply_markup=InlineKeyboardMarkup(kb), 
        parse_mode="HTML"
    )