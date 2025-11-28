# Em modules/combat/rewards.py
import logging
import random
from collections import Counter
from modules import player_manager, game_data, mission_manager, clan_manager
from modules.player.premium import PremiumManager
from modules.game_data import xp as xp_manager
from modules.player.inventory import add_item_to_inventory

logger = logging.getLogger(__name__)

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

async def apply_and_format_victory(player_data: dict, monster_stats: dict, context=None) -> str:
    """Aplica recompensas ao player e retorna texto formatado."""
    xp, gold, items = calculate_victory_rewards(player_data, monster_stats)
    
    # Aplica
    player_data['xp'] = player_data.get('xp', 0) + xp
    player_manager.add_gold(player_data, gold)
    
    # Formata
    monster_name = monster_stats.get('name') or monster_stats.get('monster_name', 'Inimigo')
    text = f"🏆 <b>VITÓRIA!</b>\n\nVocê derrotou {monster_name}!\n"
    text += f"✨ XP: +{xp}\n💰 Ouro: +{gold}\n"
    
    if items:
        text += "\n<b>📦 Itens Encontrados:</b>\n"
        for item_id, qty in items:
            add_item_to_inventory(player_data, item_id, qty)
            item_def = game_data.ITEMS_DATA.get(item_id, {})
            name = item_def.get('display_name', item_id)
            text += f"• {qty}x {name}\n"

    # --- CORREÇÃO: INTEGRAÇÃO COM MISSÕES ---
    monster_id = monster_stats.get('id')
    user_id = player_data.get("user_id")
    
    if user_id and monster_id:
        try:
            # Atualiza missão de CAÇA
            logs = await mission_manager.update_mission_progress(
                user_id=user_id, 
                mission_type="hunt", 
                target_id=monster_id, 
                amount=1
            )
            if logs: text += "\n" + "\n".join(logs)
            
            # Atualiza missão de COLETA (para cada item dropado)
            for item_id, qty in items:
                c_logs = await mission_manager.update_mission_progress(
                    user_id=user_id,
                    mission_type="collect",
                    target_id=item_id,
                    amount=qty
                )
                if c_logs: text += "\n" + "\n".join(c_logs)
                
        except Exception as e:
            print(f"[Rewards] Erro ao atualizar missão: {e}")

    return text

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

def _calculate_rewards_from_cache(player_data: dict, battle_cache: dict) -> tuple[int, int, list]:
    """
    CALCULA recompensas lendo do 'battle_cache'.
    Retorna (xp_final, gold_final, lista_de_ids_de_itens).
    """
    clan_id = player_data.get("clan_id")
    monster_stats = battle_cache.get("monster_stats", {})

    premium = PremiumManager(player_data)
    xp_mult = float(premium.get_perk_value('xp_multiplier', 1.0))
    gold_mult = float(premium.get_perk_value('gold_multiplier', 1.0))

    if clan_id:
        clan_buffs = clan_manager.get_clan_buffs(clan_id) 
        xp_mult += clan_buffs.get("xp_bonus_percent", 0) / 100.0
        gold_mult += clan_buffs.get("gold_bonus_percent", 0) / 100.0
        
    xp_reward = int(float(monster_stats.get('xp_reward', 0)) * xp_mult)
    gold_reward = int(float(monster_stats.get('gold_drop', 0)) * gold_mult)
    
    looted_items = []
    for item in monster_stats.get('loot_table', []):
        if random.random() * 100 <= float(item.get('drop_chance', 0)):
            if item_id := item.get('item_id'):
                looted_items.append(item_id)
    
    return xp_reward, gold_reward, looted_items

async def apply_and_format_victory_from_cache(player_data: dict, battle_cache: dict) -> str:
    """
    APLICA e FORMATA recompensas de caça (lendo do 'battle_cache').
    Modifica 'player_data' (XP, Ouro, Itens) mas NÃO o salva.
    """
    user_id = player_data.get("user_id")
    clan_id = player_data.get("clan_id")
    monster_stats = battle_cache.get("monster_stats", {})

    # 1. Calcula Recompensas (lendo do cache)
    xp_reward, gold_reward, looted_items = _calculate_rewards_from_cache(player_data, battle_cache)

    # 2. Aplica XP e Ouro (no pdata)
    player_manager.add_gold(player_data, gold_reward)
    player_data['xp'] = player_data.get('xp', 0) + xp_reward 

    # 3. Adiciona Itens (no pdata)
    for item_id in looted_items:
        player_manager.add_item_to_inventory(player_data, item_id, 1)
    
    # 4. Atualiza Missões (no pdata)
    mission_manager.update_mission_progress(player_data, 'HUNT', details=monster_stats)
    if monster_stats.get('is_elite', False):
        mission_manager.update_mission_progress(player_data, 'HUNT_ELITE', details=monster_stats)

    # 5. Missão de Clã (Async)
    if clan_id and monster_stats.get("id"):
        try:
            # (Não temos 'context' aqui, a missão de clã de caça não pode ser atualizada)
            pass 
        except Exception as e_clan_hunt:
            logger.error(f"Erro ao atualizar missão de guilda HUNT (cache) para clã {clan_id}: {e_clan_hunt}")

    # 6. Formata a Mensagem
    monster_name = monster_stats.get('name', 'inimigo')
    summary = (f"✅ Você derrotou <b>{monster_name}</b>!\n"
               f"+{xp_reward} XP, +{gold_reward} Ouro.")
    
    if looted_items:
        summary += "\n\n<b>Itens Adquiridos:</b>\n"
        item_names = [(game_data.ITEMS_DATA.get(item_id) or {}).get('display_name', item_id) for item_id in looted_items]
        for name, count in Counter(item_names).items():
            summary += f"- {count}x {name}\n"
            
    return summary

def process_defeat_from_cache(player_data: dict, battle_cache: dict) -> tuple[str, bool]:
    """
    Processa uma derrota (lendo do 'battle_cache'), aplicando penalidade de XP.
    """
    monster_stats = battle_cache.get("monster_stats", {})
    region_key = battle_cache.get("region_key")
    
    xp_lost = 0
    if region_key != "floresta_sombria": 
        base_reward = int(monster_stats.get('xp_reward', 0))
        xp_lost = max(0, base_reward * 2)
        player_data['xp'] = max(0, int(player_data.get('xp', 0)) - xp_lost)
    
    monster_name = monster_stats.get('name', 'inimigo')
    summary = f"☠️ <b>Você foi derrotado por {monster_name}!</b>"
    if xp_lost > 0:
        summary += f"\n\n❌ <b>Penalidade:</b> Você perdeu {xp_lost} XP."
    
    return summary, xp_lost > 0