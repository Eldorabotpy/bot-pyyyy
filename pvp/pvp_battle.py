import logging
import datetime
import random
import math
from modules import player_manager
from .pvp_config import ARENA_MODIFIERS
from . import pvp_config

logger = logging.getLogger(__name__)

# --- Ferramentas de Cáculo de Crítico e Dano ---

def _crit_params_for_player(stats: dict) -> dict:
    """
    # === [FUNÇÃO MODIFICADA] ===
    # Agora recebe o dicionário de 'stats' (que pode estar modificado)
    # em vez de 'p_data'.
    # Também dá prioridade ao stat 'crit_chance' se ele existir.
    """
    
    # Usa 'crit_chance' se existir (modificador), senão calcula com 'luck'
    if 'crit_chance' in stats:
        chance = float(stats.get('crit_chance', 5.0))
    else:
        # Fórmula original baseada na sorte
        luck = int(stats.get("luck", 5))
        chance = 100.0 * (1.0 - (0.99 ** max(0, luck)))
        chance = max(1.0, min(chance, 40.0))
    
    # Mega chance ainda pode ser baseada em sorte
    luck = int(stats.get("luck", 5)) # Pega a sorte de qualquer forma
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
            log.append("✨ 𝐀𝐂𝐄RT𝐎 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎! ✨")
    
    # =========================================================
    # 👇 [TESTE DE DIAGNÓSTICO TEMPORÁRIO] 👇
    # =========================================================
    
    # 1. Pega os stats de ataque e defesa
    #    Estamos a adicionar +50 a ambos para testar a fórmula.
    #    Se os teus stats forem 0, o 'ataque' será 50 e a 'defesa' será 50.
    
    attacker_atk = float(attacker_stats.get('ataque', 0)) + 50.0
    defender_def = float(defender_stats.get('defesa', 0)) + 50.0 
    
    # =========================================================
    
    # 2. Aplica o multiplicador de crítico ao ataque
    boosted_attack = math.ceil(attacker_atk * mult)
    
    # 3. Calcula a redução de dano (percentual)
    if defender_def < 0:
        defender_def = 0
    
    damage_reduction = 100.0 / (100.0 + defender_def)
    
    # 4. Calcula o dano final
    final_damage = boosted_attack * damage_reduction
    
    # 5. Garante um dano mínimo de 1
    damage = max(int(crit_params.get("min_damage", 1)), int(final_damage))
    
    # =========================================================
    # 👆 FIM DA SEÇÃO DE TESTE 👆
    # =========================================================
    
    return damage, log

def simular_batalha_completa(player1_id, player2_id, modifier_effect=None):

    """
    Simula uma batalha PvP completa do início ao fim.
    Retorna o ID do vencedor e o log completo da batalha.
    """
    p1_data = player_manager.get_player_data(player1_id)
    p2_data = player_manager.get_player_data(player2_id)

    # Prepara os stats dos jogadores
    p1_stats = player_manager.get_player_total_stats(p1_data).copy()
    p2_stats = player_manager.get_player_total_stats(p2_data).copy()
    
    p1_stats['user_id'] = player1_id
    p2_stats['user_id'] = player2_id

    p1_hp = p1_stats.get('max_hp', 1) 
    p2_hp = p2_stats.get('max_hp', 1)
    p1_name = p1_data.get("character_name", "Jogador 1")
    p2_name = p2_data.get("character_name", "Jogador 2")
    
    battle_log = [f"<b>{p1_name}</b> VS <b>{p2_name}</b>\n"]

    # =========================================================
    # 👇 Lógica dos Modificadores de Arena 👇
    # =========================================================
    if modifier_effect:
        try:
            today_weekday = datetime.datetime.now().weekday()
            mod_data = pvp_config.ARENA_MODIFIERS.get(today_weekday)
            if mod_data and mod_data.get("effect") == modifier_effect:
                 battle_log.append(f"🔥 <b>Modificador: {mod_data['name']}</b>")
                 battle_log.append(f"<i>{mod_data['description']}</i>\n")
        except Exception as e:
            logger.warning(f"Erro ao carregar descrição do modificador: {e}") 

        # Função interna para aplicar modificadores aos stats
        def apply_mods_to_stats(stats_dict, effect):
            
            if effect == "fury_day":
                stats_dict['ataque'] = stats_dict.get('ataque', 0) * 1.20
                stats_dict['defesa'] = stats_dict.get('defesa', 0) * 0.90
            
            elif effect == "agility_day":
                # (Nota: Isto ainda não faz nada no loop de batalha)
                stats_dict['dodge_chance'] = stats_dict.get('dodge_chance', 0) + 15
                stats_dict['double_attack_chance'] = stats_dict.get('double_attack_chance', 0) + 15

            # [LÓGICA DE BALANCEAMENTO - MANTIDA]
            elif effect == "wall_day":
                # Defesa +50%
                stats_dict['defesa'] = stats_dict.get('defesa', 0) * 1.5
                # Ataque -20%
                stats_dict['ataque'] = stats_dict.get('ataque', 0) * 0.8
            
            elif effect == "critical_day":
                # (Isto agora funciona)
                stats_dict['crit_chance'] = stats_dict.get('crit_chance', 20) + 20

            elif effect == "glass_cannon_day":
                stats_dict['ataque'] = stats_dict.get('ataque', 0) * 2.0
                stats_dict['defesa'] = 0

        # Aplica os modificadores para ambos os jogadores
        apply_mods_to_stats(p1_stats, modifier_effect)
        apply_mods_to_stats(p2_stats, modifier_effect)
    # =========================================================
    # 👆 Fim da Lógica dos Modificadores 👆
    # =========================================================

    
    # Decide quem ataca primeiro
    atacante_stats, defensor_stats = (p1_stats, p2_stats)
    atacante_hp, defensor_hp = (p1_hp, p2_hp)
    atacante_name, defensor_name = (p1_name, p2_name)

    if p2_stats.get('initiative', 0) > p1_stats.get('initiative', 0):
        atacante_stats, defensor_stats = (p2_stats, p1_stats)
        atacante_hp, defensor_hp = (p2_hp, p1_hp)
        atacante_name, defensor_name = (p2_name, p1_name)

    # Loop da batalha (máximo de 20 rodadas para evitar loops infinitos)
    for round_num in range(1, 21):
        battle_log.append(f"\n--- <b>Turno {round_num}</b> ---")
        
        # 1. Primeiro jogador ataca
        # [CORREÇÃO mantida] Passando os stats MODIFICADOS para o crítico
        crit_params = _crit_params_for_player(atacante_stats)
        dano, crit_log = _roll_damage(atacante_stats, defensor_stats, crit_params)
        defensor_hp -= dano
        battle_log.append(f"➡️ {atacante_name} ataca!")
        battle_log.extend(crit_log)
        battle_log.append(f"💥 {defensor_name} recebe {dano} de dano. (HP restante: {max(0, int(defensor_hp))})") 

        if defensor_hp <= 0:
            battle_log.append(f"\n🎉 {atacante_name} venceu a batalha!")
            return atacante_stats.get('user_id', 0), battle_log 

        # 2. Segundo jogador ataca (se sobreviveu)
        # [CORREÇÃO mantida] Passando os stats MODIFICADOS para o crítico
        crit_params = _crit_params_for_player(defensor_stats)
        dano, crit_log = _roll_damage(defensor_stats, atacante_stats, crit_params)
        atacante_hp -= dano
        battle_log.append(f"⬅️ {defensor_name} ataca!")
        battle_log.extend(crit_log)
        battle_log.append(f"💥 {atacante_name} recebe {dano} de dano. (HP restante: {max(0, int(atacante_hp))})") 

        if atacante_hp <= 0:
            battle_log.append(f"\n🎉 {defensor_name} venceu a batalha!")
            return defensor_stats.get('user_id', 0), battle_log 

    # Se a batalha durar 20 turnos, declara empate
    battle_log.append("\n⚖️ A batalha foi longa e terminou em empate!")
    return 0, battle_log