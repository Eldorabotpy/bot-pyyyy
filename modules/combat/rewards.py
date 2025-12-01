# modules/combat/rewards.py
# (VERSÃO CORRIGIDA: REMOVIDA CHAMADA DE CLÃ QUEBRADA + PREMIUM FIX)

import logging
import random
from collections import Counter
from modules import player_manager, game_data
from modules.player.premium import PremiumManager
# from modules import clan_manager # Removido temporariamente para evitar erro de import circular/sync

logger = logging.getLogger(__name__)

def calculate_victory_rewards(player_data: dict, combat_details: dict) -> tuple[int, int, list]:
    """
    Calcula XP, Ouro e Itens.
    NOTA: Esta função é SÍNCRONA. Não pode chamar funções async (DB) aqui dentro.
    """
    
    # 1. Base Values (Garante que sejam inteiros)
    try:
        base_xp = int(float(combat_details.get('monster_xp_reward', combat_details.get('xp_reward', 0))))
        base_gold = int(float(combat_details.get('monster_gold_drop', combat_details.get('gold_drop', 0))))
    except:
        base_xp = 0
        base_gold = 0

    # 2. Premium Multipliers
    # O PremiumManager lê do dict player_data, então é seguro e rápido
    premium = PremiumManager(player_data)
    xp_mult = float(premium.get_perk_value('xp_multiplier', 1.0))
    gold_mult = float(premium.get_perk_value('gold_multiplier', 1.0))

    # 3. Clan Buffs
    # [CORREÇÃO] Removemos a chamada direta ao clan_manager aqui porque
    # ele é assíncrono e causaria crash numa função síncrona.
    # Futuramente, passaremos os buffs dentro de 'player_data' antes de chamar esta função.
    # if clan_id: ... (Lógica removida para estabilidade)
        
    xp_reward = int(base_xp * xp_mult)
    gold_reward = int(base_gold * gold_mult)
    
    # 4. Loot System
    looted_items = []
    loot_table = combat_details.get('loot_table', [])
    
    if loot_table and isinstance(loot_table, list):
        for item in loot_table:
            if not isinstance(item, dict): continue
            
            chance = float(item.get('drop_chance', 0))
            # Bônus de sorte do jogador (exemplo simples)
            luck = int(player_data.get('total_stats', {}).get('luck', 0)) # Tenta pegar stats se existirem
            chance += (luck * 0.1) 
            
            if random.random() * 100 <= chance:
                item_id = item.get('item_id')
                if item_id:
                    looted_items.append(item_id)
    
    return xp_reward, gold_reward, looted_items

async def apply_and_format_victory(player_data: dict, monster_stats: dict, context=None) -> str:
    """
    Aplica recompensas ao player e retorna texto formatado.
    (Esta função é async, pode chamar coisas de DB se precisar)
    """
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
        for item_id in items:
            player_manager.add_item_to_inventory(player_data, item_id, 1)
            item_def = game_data.ITEMS_DATA.get(item_id, {})
            name = item_def.get('display_name', item_id)
            text += f"• 1x {name}\n"

    return text

def process_defeat(player_data: dict, combat_details: dict) -> tuple[str, bool]:
    """Processa derrota."""
    xp_lost = 0
    # Lógica simples de penalidade
    base_reward = int(combat_details.get('monster_xp_reward', 0))
    xp_lost = max(0, int(base_reward * 0.5))
    player_data['xp'] = max(0, int(player_data.get('xp', 0)) - xp_lost)
    
    monster_name = combat_details.get('name', 'Inimigo')
    summary = f"☠️ <b>Derrota!</b>\n\nVocê caiu para {monster_name}."
    if xp_lost > 0:
        summary += f"\n❌ Penalidade: -{xp_lost} XP"
    
    return summary, xp_lost > 0

# Compatibilidade para Cache (Auto Hunt)
def _calculate_rewards_from_cache(player_data: dict, battle_cache: dict) -> tuple[int, int, list]:
    monster_stats = battle_cache.get("monster_stats", {})
    # Garante chaves
    if 'monster_xp_reward' not in monster_stats:
        monster_stats['monster_xp_reward'] = monster_stats.get('xp_reward', 0)
    if 'monster_gold_drop' not in monster_stats:
        monster_stats['monster_gold_drop'] = monster_stats.get('gold_drop', 0)
        
    return calculate_victory_rewards(player_data, monster_stats)

def process_defeat_from_cache(player_data: dict, battle_cache: dict) -> tuple[str, bool]:
    return process_defeat(player_data, battle_cache.get("monster_stats", {}))