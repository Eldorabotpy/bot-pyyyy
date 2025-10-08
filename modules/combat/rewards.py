# Em modules/combat/rewards.py
import logging
import random
from collections import Counter
from modules import player_manager, game_data, mission_manager, clan_manager
from modules.player.premium import PremiumManager

def calculate_victory_rewards(player_data: dict, combat_details: dict) -> tuple[int, int, list]:
    """
    Apenas CALCULA o XP, ouro e itens de uma vitória, mas não os aplica ao jogador.
    Retorna uma tupla com: (xp_final, gold_final, lista_de_ids_de_itens).
    """
    clan_id = player_data.get("clan_id")

    # =================================================================
    # --- INÍCIO DA CORREÇÃO ---
    # 1. Instanciamos o PremiumManager com os dados do jogador
    premium = PremiumManager(player_data)

    # 2. Buscamos os perks de multiplicador usando o método correto
    xp_mult = float(premium.get_perk_value('xp_multiplier', 1.0))
    gold_mult = float(premium.get_perk_value('gold_multiplier', 1.0))
    # =================================================================
    # --- FIM DA CORREÇÃO ---

    # A sua lógica de buffs de clã continua aqui, intacta e funcional!
    if clan_id:
        clan_buffs = clan_manager.get_clan_buffs(clan_id)
        xp_mult += clan_buffs.get("xp_bonus_percent", 0) / 100.0
        gold_mult += clan_buffs.get("gold_bonus_percent", 0) / 100.0
        
    xp_reward = int(float(combat_details.get('monster_xp_reward', 0)) * xp_mult)
    gold_reward = int(float(combat_details.get('monster_gold_drop', 0)) * gold_mult)
    
    # Loot (sua lógica original, sem alterações)
    looted_items = []
    for item in combat_details.get('loot_table', []):
        if random.random() * 100 <= float(item.get('drop_chance', 0)):
            if item_id := item.get('item_id'):
                looted_items.append(item_id)
    
    return xp_reward, gold_reward, looted_items

async def apply_and_format_victory(player_data: dict, combat_details: dict, context) -> str:
    """
    Aplica as recompensas de uma caça NORMAL, atualiza missões, verifica level up
    e formata a mensagem final de vitória.
    """
    user_id = player_data["user_id"]
    clan_id = player_data.get("clan_id")

    xp_reward, gold_reward, looted_items = calculate_victory_rewards(player_data, combat_details)


    mission_manager.update_mission_progress(player_data, 'HUNT', details=combat_details)
    if combat_details.get('is_elite', False):
        mission_manager.update_mission_progress(player_data, 'HUNT_ELITE', details=combat_details)
    if clan_id:
        await clan_manager.update_guild_mission_progress(clan_id, 'HUNT', details=combat_details, context=context)

  
    player_data['xp'] += xp_reward
    player_manager.add_gold(player_data, gold_reward)
    for item_id in looted_items:
        player_manager.add_item_to_inventory(player_data, item_id)
    
    levels_gained, points_gained, level_up_msg = player_manager.check_and_apply_level_up(player_data)

  
    monster_name = combat_details.get('monster_name', 'inimigo')
    summary = (f"✅ Você derrotou {monster_name}!\n"
               f"+{xp_reward} XP, +{gold_reward} ouro.")
    
    if looted_items:
        summary += "\n\n<b>𝑰𝒕𝒆𝒏𝒔 𝑨𝒅𝒒𝒖𝒊𝒓𝒊𝒅𝒐𝒔:</b>\n"
        item_names = [(game_data.ITEMS_DATA.get(item_id) or {}).get('display_name', item_id) for item_id in looted_items]
        for name, count in Counter(item_names).items():
            summary += f"- {count}x {name}\n"
            
    if level_up_msg:
        summary += level_up_msg
        
    return summary

def process_defeat(player_data: dict, combat_details: dict) -> tuple[str, bool]:
    """
    Processa uma derrota, aplicando a penalidade de XP e formatando a mensagem.
    """
    xp_lost = 0
    if combat_details.get("region_key") != "floresta_sombria":
        base_reward = int(combat_details.get('monster_xp_reward', 0))
        xp_lost = max(0, base_reward * 2)
        player_data['xp'] = max(0, int(player_data.get('xp', 0)) - xp_lost)
    
    monster_name = combat_details.get('monster_name', 'inimigo')
    summary = f"𝑽𝒐𝒄𝒆̂ 𝒇𝒐𝒊 𝒅𝒆𝒓𝒓𝒐𝒕𝒂𝒅𝒐 𝒑𝒆𝒍𝒐 {monster_name}!"
    if xp_lost > 0:
        summary += f"\n\n❌ 𝑷𝒆𝒏𝒂𝒍𝒊𝒅𝒂𝒅𝒆: Você perdeu {xp_lost} XP."
    
    return summary, xp_lost > 0