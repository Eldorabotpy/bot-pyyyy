# modules/combat/rewards.py
import logging
import random
from collections import Counter
from typing import Any, Dict, List, Tuple

from modules import player_manager, game_data, mission_manager, clan_manager, file_ids as file_id_manager
from modules.player.premium import PremiumManager
from modules.game_data import xp as xp_manager

logger = logging.getLogger(__name__)


def _to_float_safe(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _get_combat_value(details: Dict[str, Any], keys: List[str], default: float = 0.0) -> float:
    """
    Tenta várias chaves (ordem) e retorna um float seguro.
    Ex.: keys = ['monster_xp_reward', 'xp_reward']
    """
    for k in keys:
        if k in details:
            try:
                return float(details.get(k, default) or default)
            except Exception:
                continue
    return float(default)


def calculate_victory_rewards(player_data: dict, combat_details: dict) -> Tuple[int, int, List[str]]:
    """
    Calcula (sem aplicar) as recompensas de XP, ouro e itens para uma vitória.
    Retorna (xp_final:int, gold_final:int, looted_items:list[str]).
    """
    clan_id = player_data.get("clan_id")

    # Premium perks (defensivo)
    premium = PremiumManager(player_data)
    xp_mult = _to_float_safe(premium.get_perk_value('xp_multiplier', 1.0), 1.0)
    gold_mult = _to_float_safe(premium.get_perk_value('gold_multiplier', 1.0), 1.0)

    # Clan buffs (se existirem, podem ser síncronos)
    try:
        if clan_id:
            clan_buffs = clan_manager.get_clan_buffs(clan_id) or {}
            xp_mult += _to_float_safe(clan_buffs.get("xp_bonus_percent", 0.0)) / 100.0
            gold_mult += _to_float_safe(clan_buffs.get("gold_bonus_percent", 0.0)) / 100.0
    except Exception as e:
        logger.exception(f"Falha ao obter clan_buffs para clan {clan_id}: {e}")

    # Leitura defensiva de valores do combat_details (aceita variações de chave)
    xp_base = _get_combat_value(combat_details, ["monster_xp_reward", "xp_reward", "monster_xp", "xp"], 0.0)
    gold_base = _get_combat_value(combat_details, ["monster_gold_drop", "gold_drop", "gold"], 0.0)

    xp_reward = int(xp_base * xp_mult)
    gold_reward = int(gold_base * gold_mult)

    # Loot
    looted_items = []
    for item in (combat_details.get('loot_table') or []):
        try:
            drop_chance = float(item.get('drop_chance', 0) or 0)
            if random.random() * 100 <= drop_chance:
                item_id = item.get('item_id')
                if item_id:
                    looted_items.append(item_id)
        except Exception:
            logger.exception(f"Erro ao processar loot_table item: {item}")

    return xp_reward, gold_reward, looted_items


async def apply_and_format_victory(player_data: dict, combat_details: dict, context) -> str:
    """
    Aplica recompensas (XP, ouro, itens), atualiza missões e formata a mensagem de vitória.
    - Modifica player_data em memória; salva ao final.
    """
    user_id = player_data.get("user_id")
    if not user_id:
        logger.warning("apply_and_format_victory chamado sem user_id em player_data.")
        return "Erro ao aplicar recompensas: ID do jogador não encontrado."

    clan_id = player_data.get("clan_id")

    xp_reward, gold_reward, looted_items = calculate_victory_rewards(player_data, combat_details)

    # Aplica XP usando o xp_manager (garante level ups e retorno informativo)
    try:
        level_up_result = xp_manager.add_combat_xp_inplace(player_data, xp_reward)
    except Exception as e:
        logger.exception(f"Erro ao adicionar XP com xp_manager: {e}")
        # fallback defensivo: soma direta (não ideal)
        try:
            player_data['xp'] = int(player_data.get('xp', 0)) + int(xp_reward)
        except Exception:
            player_data['xp'] = player_data.get('xp', 0)
        level_up_result = {"levels_gained": 0, "points_awarded": 0, "new_level": player_data.get("level")}

    level_up_msg = ""
    if level_up_result and level_up_result.get("levels_gained", 0) > 0:
        levels_gained = level_up_result.get("levels_gained", 0)
        points_gained = level_up_result.get("points_awarded", 0)
        new_level = level_up_result.get("new_level", player_data.get("level", "?"))
        nivel_txt = "nível" if levels_gained == 1 else "níveis"
        ponto_txt = "ponto" if points_gained == 1 else "pontos"
        level_up_msg = (
            f"\n\n✨ <b>Parabéns!</b> Você subiu {levels_gained} {nivel_txt} "
            f"(agora Nv. {new_level}) e ganhou {points_gained} {ponto_txt} de atributo."
        )

    # Missões pessoais (síncrono)
    try:
        mission_manager.update_mission_progress(player_data, 'HUNT', details=combat_details)
        if combat_details.get('is_elite', False):
            mission_manager.update_mission_progress(player_data, 'HUNT_ELITE', details=combat_details)
    except Exception:
        logger.exception("Erro ao atualizar missões locais após vitória.")

    # Missão de clã (async)
    if clan_id:
        try:
            await clan_manager.update_guild_mission_progress(clan_id, 'HUNT', details=combat_details, context=context)
        except Exception:
            logger.exception(f"Erro ao atualizar missão de guilda HUNT para clã {clan_id}.")

    # Aplica ouro e itens (síncrono)
    try:
        player_manager.add_gold(player_data, gold_reward)
    except Exception:
        logger.exception("Erro ao adicionar ouro ao jogador.")

    for item_id in looted_items:
        try:
            player_manager.add_item_to_inventory(player_data, item_id, 1)
        except Exception:
            logger.exception(f"Erro ao adicionar item {item_id} ao inventário.")

    # Salva player_data após aplicar recompensas
    try:
        await player_manager.save_player_data(user_id, player_data)
    except Exception:
        logger.exception("Erro ao salvar player_data após aplicar recompensas.")

    # Monta a mensagem final
    monster_name = combat_details.get('monster_name', 'inimigo')
    summary = (f"✅ Você derrotou {monster_name}!\n"
               f"+{xp_reward} XP, +{gold_reward} ouro.")

    if looted_items:
        summary += "\n\n<b>Itens Adquiridos:</b>\n"
        item_names = [(game_data.ITEMS_DATA.get(item_id) or {}).get('display_name', item_id) for item_id in looted_items]
        for name, count in Counter(item_names).items():
            summary += f"- {count}x {name}\n"

    if level_up_msg:
        summary += level_up_msg

    return summary


def process_defeat(player_data: dict, combat_details: dict) -> Tuple[str, bool]:
    """
    Processa derrota, aplica penalidade de XP quando aplicável.
    Retorna (summary:str, punished:bool)
    """
    xp_lost = 0
    if combat_details.get("region_key") != "floresta_sombria":
        base_reward = int(combat_details.get('monster_xp_reward', 0) or 0)
        xp_lost = max(0, base_reward * 2)
        player_data['xp'] = max(0, int(player_data.get('xp', 0)) - xp_lost)

    monster_name = combat_details.get('monster_name', 'inimigo')
    summary = f"𝑽𝒐𝒄𝒆̂ 𝒇𝒐𝒊 𝒅𝒆𝒓𝒓𝒐𝒕𝒂𝒅𝒐 𝒑𝒆𝒍𝒐 {monster_name}!"
    if xp_lost > 0:
        summary += f"\n\n❌ 𝑷𝒆𝒏𝒂𝒍𝒊𝒅𝒂𝒅𝒆: Você perdeu {xp_lost} XP."

    return summary, xp_lost > 0


def _calculate_rewards_from_cache(player_data: dict, battle_cache: dict) -> Tuple[int, int, List[str]]:
    """
    Calcula recompensas lendo o battle_cache (utilizado no fluxo com battle_cache).
    """
    clan_id = player_data.get("clan_id")
    monster_stats = battle_cache.get("monster_stats", {}) or {}

    premium = PremiumManager(player_data)
    xp_mult = _to_float_safe(premium.get_perk_value('xp_multiplier', 1.0), 1.0)
    gold_mult = _to_float_safe(premium.get_perk_value('gold_multiplier', 1.0), 1.0)

    try:
        if clan_id:
            clan_buffs = clan_manager.get_clan_buffs(clan_id) or {}
            xp_mult += _to_float_safe(clan_buffs.get("xp_bonus_percent", 0.0)) / 100.0
            gold_mult += _to_float_safe(clan_buffs.get("gold_bonus_percent", 0.0)) / 100.0
    except Exception:
        logger.exception(f"Erro ao obter clan_buffs (cache) para clan {clan_id}")

    xp_base = _get_combat_value(monster_stats, ["xp_reward", "monster_xp_reward", "xp"], 0.0)
    gold_base = _get_combat_value(monster_stats, ["gold_drop", "monster_gold_drop", "gold"], 0.0)

    xp_reward = int(xp_base * xp_mult)
    gold_reward = int(gold_base * gold_mult)

    looted_items = []
    for item in (monster_stats.get('loot_table') or []):
        try:
            if random.random() * 100 <= float(item.get('drop_chance', 0) or 0):
                item_id = item.get('item_id')
                if item_id:
                    looted_items.append(item_id)
        except Exception:
            logger.exception(f"Erro ao processar loot_table (cache) item: {item}")

    return xp_reward, gold_reward, looted_items


async def apply_and_format_victory_from_cache(player_data: dict, battle_cache: dict) -> str:
    """
    Aplica recompensas lidas do battle_cache (não salva player_data).
    """
    user_id = player_data.get("user_id")
    clan_id = player_data.get("clan_id")
    monster_stats = battle_cache.get("monster_stats", {}) or {}

    xp_reward, gold_reward, looted_items = _calculate_rewards_from_cache(player_data, battle_cache)

    # Aplica XP via xp_manager (inplace)
    try:
        level_up_result = xp_manager.add_combat_xp_inplace(player_data, xp_reward)
    except Exception as e:
        logger.exception(f"Erro ao aplicar XP (cache): {e}")
        player_data['xp'] = player_data.get('xp', 0) + int(xp_reward)
        level_up_result = {"levels_gained": 0, "points_awarded": 0, "new_level": player_data.get("level")}

    # Aplica ouro e itens (no pdata)
    try:
        player_manager.add_gold(player_data, gold_reward)
    except Exception:
        logger.exception("Erro ao adicionar ouro (cache).")

    for item_id in looted_items:
        try:
            player_manager.add_item_to_inventory(player_data, item_id, 1)
        except Exception:
            logger.exception(f"Erro ao adicionar item {item_id} (cache).")

    # Missões
    try:
        mission_manager.update_mission_progress(player_data, 'HUNT', details=monster_stats)
        if monster_stats.get('is_elite', False):
            mission_manager.update_mission_progress(player_data, 'HUNT_ELITE', details=monster_stats)
    except Exception:
        logger.exception("Erro ao atualizar missões (cache).")

    # Clã: sem context aqui; caller deve atualizar se desejar (assíncrono)
    if clan_id and monster_stats.get("id"):
        # exemplo: asyncio.create_task(clan_manager.update_guild_mission_progress(...))
        pass

    # Salva player_data após aplicar recompensas
    try:
        if user_id:
            await player_manager.save_player_data(user_id, player_data)
    except Exception:
        logger.exception("Erro ao salvar player_data (cache).")

    # Formata mensagem
    monster_name = monster_stats.get('name', 'inimigo')
    summary = (f"✅ Você derrotou <b>{monster_name}</b>!\n"
               f"+{xp_reward} XP, +{gold_reward} Ouro.")

    if looted_items:
        summary += "\n\n<b>Itens Adquiridos:</b>\n"
        item_names = [(game_data.ITEMS_DATA.get(item_id) or {}).get('display_name', item_id) for item_id in looted_items]
        for name, count in Counter(item_names).items():
            summary += f"- {count}x {name}\n"

    if level_up_result and level_up_result.get("levels_gained", 0) > 0:
        levels_gained = level_up_result.get("levels_gained", 0)
        points_gained = level_up_result.get("points_awarded", 0)
        new_level = level_up_result.get("new_level", player_data.get("level", "?"))
        nivel_txt = "nível" if levels_gained == 1 else "níveis"
        ponto_txt = "ponto" if points_gained == 1 else "pontos"
        level_up_msg = (
            f"\n\n✨ <b>Parabéns!</b> Você subiu {levels_gained} {nivel_txt} "
            f"(agora Nv. {new_level}) e ganhou {points_gained} {ponto_txt} de atributo."
        )
        summary += level_up_msg

    return summary


def process_defeat_from_cache(player_data: dict, battle_cache: dict) -> Tuple[str, bool]:
    monster_stats = battle_cache.get("monster_stats", {}) or {}
    region_key = battle_cache.get("region_key")

    xp_lost = 0
    if region_key != "floresta_sombria":
        base_reward = int(monster_stats.get('xp_reward', 0) or 0)
        xp_lost = max(0, base_reward * 2)
        player_data['xp'] = max(0, int(player_data.get('xp', 0)) - xp_lost)

    monster_name = monster_stats.get('name', 'inimigo')
    summary = f"☠️ <b>Você foi derrotado por {monster_name}!</b>"
    if xp_lost > 0:
        summary += f"\n\n❌ <b>Penalidade:</b> Você perdeu {xp_lost} XP."

    return summary, xp_lost > 0
