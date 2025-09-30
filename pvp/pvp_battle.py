# Em pvp/pvp_battle.py (VERSÃO SIMULADOR)

import logging
import datetime
import random
import math
from modules import player_manager
from .pvp_config import ARENA_MODIFIERS

logger = logging.getLogger(__name__)

# --- Ferramentas de Cáculo de Crítico e Dano ---
def _crit_params_for_player(p_data: dict) -> dict:
    stats = player_manager.get_player_total_stats(p_data)
    luck = int(stats.get("luck", 5))
    chance = 100.0 * (1.0 - (0.99 ** max(0, luck)))
    chance = max(1.0, min(chance, 40.0))
    mega_chance = min(25.0, luck / 2.0)
    return {"chance": chance, "mega_chance": mega_chance, "mult": 1.6, "mega_mult": 2.0, "min_damage": 1}

def _roll_damage(attacker_stats: dict, defender_stats: dict, crit_params: dict) -> tuple[int, list[str]]:
    log = []
    r = random.random() * 100.0
    is_crit = (r <= float(crit_params.get("chance", 0.0)))
    mult, mega = 1.0, False
    if is_crit:
        if random.random() * 100.0 <= float(crit_params.get("mega_chance", 0.0)):
            mult, mega = float(crit_params.get("mega_mult", 2.0)), True
            log.append("💥 𝐌𝐄𝐆𝐀 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎! 💥")
        else:
            mult = float(crit_params.get("mult", 1.6))
            log.append("✨ 𝐀𝐂𝐄𝐑𝐓𝐎 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎! ✨")
    
    boosted_attack = math.ceil(float(attacker_stats['attack']) * mult)
    damage = max(int(crit_params.get("min_damage", 1)), boosted_attack - int(defender_stats['defense']))
    return damage, log

# --- A FUNÇÃO PRINCIPAL DO SIMULADOR ---
def simular_batalha_completa(p1_id: int, p2_id: int) -> tuple[int, list[str]]:
    """
    Simula uma batalha PvP completa do início ao fim.
    Retorna o ID do vencedor e o log completo da batalha.
    """
    p1_data = player_manager.get_player_data(p1_id)
    p2_data = player_manager.get_player_data(p2_id)

    # Prepara os stats dos jogadores
    p1_stats = player_manager.get_player_total_stats(p1_data)
    p2_stats = player_manager.get_player_total_stats(p2_data)
    p1_hp = p1_stats['max_hp']
    p2_hp = p2_stats['max_hp']
    p1_name = p1_data.get("character_name", "Jogador 1")
    p2_name = p2_data.get("character_name", "Jogador 2")
    
    # Aplica modificadores diários (se houver)
    # ... (podemos adicionar a lógica dos modificadores aqui depois) ...

    battle_log = [f"<b>{p1_name}</b> VS <b>{p2_name}</b>\n"]
    
    # Decide quem ataca primeiro
    atacante_stats, defensor_stats = (p1_stats, p2_stats)
    atacante_hp, defensor_hp = (p1_hp, p2_hp)
    atacante_name, defensor_name = (p1_name, p2_name)
    atacante_data, defensor_data = (p1_data, p2_data)

    if p2_stats.get('initiative', 0) > p1_stats.get('initiative', 0):
        atacante_stats, defensor_stats = (p2_stats, p1_stats)
        atacante_hp, defensor_hp = (p2_hp, p1_hp)
        atacante_name, defensor_name = (p2_name, p1_name)
        atacante_data, defensor_data = (p2_data, p1_data)

    # Loop da batalha (máximo de 20 rodadas para evitar loops infinitos)
    for round_num in range(1, 21):
        battle_log.append(f"\n--- <b>Turno {round_num}</b> ---")
        
        # 1. Primeiro jogador ataca
        crit_params = _crit_params_for_player(atacante_data)
        dano, crit_log = _roll_damage(atacante_stats, defensor_stats, crit_params)
        defensor_hp -= dano
        battle_log.append(f"➡️ {atacante_name} ataca!")
        battle_log.extend(crit_log)
        battle_log.append(f"💥 {defensor_name} recebe {dano} de dano. (HP restante: {defensor_hp})")

        if defensor_hp <= 0:
            battle_log.append(f"\n🎉 {atacante_name} venceu a batalha!")
            return atacante_stats.get('user_id', 0), battle_log # Retorna o ID do vencedor

        # 2. Segundo jogador ataca (se sobreviveu)
        crit_params = _crit_params_for_player(defensor_data)
        dano, crit_log = _roll_damage(defensor_stats, atacante_stats, crit_params)
        atacante_hp -= dano
        battle_log.append(f"⬅️ {defensor_name} ataca!")
        battle_log.extend(crit_log)
        battle_log.append(f"💥 {atacante_name} recebe {dano} de dano. (HP restante: {atacante_hp})")

        if atacante_hp <= 0:
            battle_log.append(f"\n🎉 {defensor_name} venceu a batalha!")
            return defensor_stats.get('user_id', 0), battle_log # Retorna o ID do vencedor

    # Se a batalha durar 20 turnos, declara empate
    battle_log.append("\n⚖️ A batalha foi longa e terminou em empate!")
    return 0, battle_log # 0 significa empate