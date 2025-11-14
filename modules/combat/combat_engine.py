# modules/combat/combat_engine.py
import random
import logging
from modules.game_data.skills import SKILL_DATA
from modules.combat import criticals
from typing import Optional, Dict, Any
from modules import player_manager

logger = logging.getLogger(__name__)


def _get_player_skill_data_by_rarity(pdata: dict, skill_id: str) -> Optional[dict]:
    """
    Helper para buscar os dados de uma skill (SKILL_DATA) e mesclá-los
    com os dados da raridade que o jogador possui.
    """
    base_skill = SKILL_DATA.get(skill_id)
    if not base_skill: 
        return None

    if "rarity_effects" not in base_skill:
        return base_skill

    player_skills = pdata.get("skills", {})
    if not isinstance(player_skills, dict):
        rarity = "comum"
    else:
        player_skill_instance = player_skills.get(skill_id)
        if not player_skill_instance:
            rarity = "comum"
        else:
            rarity = player_skill_instance.get("rarity", "comum")

    merged_data = base_skill.copy()
    rarity_data = base_skill["rarity_effects"].get(rarity, base_skill["rarity_effects"].get("comum", {}))
    merged_data.update(rarity_data)
    
    return merged_data

async def processar_acao_combate(
    attacker_pdata: dict, # MODIFICADO: Recebe o pdata completo
    attacker_stats: dict, 
    target_stats: dict, 
    skill_id: str | None,
    attacker_current_hp: int = 9999, # HP atual para skills (como low_hp_dmg_boost)
) -> dict:
    """
    Este é o CÉREBRO UNIFICADO do combate.
    Ele recebe os stats e a skill, e retorna o resultado (dano, logs, etc.).
    """
    
    # MODIFICADO: Usa a nova função auxiliar para ler a raridade
    if skill_id:
        skill_info = _get_player_skill_data_by_rarity(attacker_pdata, skill_id)
    else:
        skill_info = None

    # Lê os efeitos de dentro da skill_info (que já tem os dados da raridade)
    skill_effects = skill_info.get("effects", {}) if skill_info else {}        
    attacker_stats_modified = attacker_stats.copy()
    target_stats_modified = target_stats.copy()
    
    log_messages = [] 

    num_attacks = int(skill_effects.get("multi_hit", 0))
    defense_penetration = float(skill_effects.get("defense_penetration", 0.0))
    bonus_crit_chance = float(skill_effects.get("bonus_crit_chance", 0.0))

    if skill_id:
        
        num_attacks = int(skill_effects.get("multi_hit", 1))
    else:
        
        initiative = attacker_stats_modified.get('initiative', 0)
        double_attack_chance = (initiative * 0.25) / 100.0
        num_attacks = 2 if random.random() < min(double_attack_chance, 0.50) else 1
        
        if num_attacks == 2:
            log_messages.append("⚡ 𝐀𝐓𝐀Q𝐔𝐄 𝐃𝐔𝐏𝐋𝐎!")
    
    if defense_penetration > 0:
        target_stats_modified['defense'] = int(target_stats_modified['defense'] * (1.0 - defense_penetration))
        log_messages.append(f"💨 Você ignora {defense_penetration*100:.0f}% da defesa!")
    
    if bonus_crit_chance > 0:
        # Aumenta a sorte temporariamente para o cálculo do crítico
        attacker_stats_modified['luck'] += int(bonus_crit_chance * 140) 
        log_messages.append(f"🎯 Mirando um ponto vital...")

    # Lógica para 'low_hp_dmg_boost' (Ex: Fúria)
    skill_effects_to_use = skill_effects.copy()
    if "low_hp_dmg_boost" in skill_effects:
        attacker_max_hp = attacker_stats.get('max_hp', 1)
        if attacker_max_hp == 0: attacker_max_hp = 1 # Evitar divisão por zero
        
        player_hp_percent = attacker_current_hp / attacker_max_hp
        
        if player_hp_percent < 0.3: # (Ex: menos de 30% HP)
            current_mult = skill_effects_to_use.get("damage_multiplier", 1.0)
            boost = 1.0 + skill_effects.get("low_hp_dmg_boost", 0.0)
            skill_effects_to_use["damage_multiplier"] = current_mult * boost
            log_messages.append(f"🩸 Fúria Selvagem!")

    # --- Fim da Lógica de Efeitos ---

    # --- Cálculo de Dano (Loop de Ataque) ---
    total_damage = 0
    
    for i in range(num_attacks):
        
        # O módulo criticals faz o cálculo principal
        player_damage_raw, is_crit, is_mega = criticals.roll_damage(
            attacker_stats_modified, 
            target_stats_modified, 
            skill_effects_to_use # Passa os efeitos modificados (ex: com Fúria)
        )
        
        player_damage = max(1, int(player_damage_raw))
        total_damage += player_damage
        
        # (Logs mais descritivos)
        if num_attacks > 1:
            log_messages.append(f"➡️ Golpe {i+1} causa {player_damage} de dano.")
        else:
            log_messages.append(f"➡️ Você causa {player_damage} de dano.")

        if is_mega: 
            log_messages.append("💥💥 𝐌𝐄𝐆𝐀 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎!")
        elif is_crit: 
            log_messages.append("💥 𝐃𝐀𝐍𝐎 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎!")

    # 3. Retornar o Resultado Padronizado
    return {
        "total_damage": total_damage,    # Dano total a ser aplicado
        "log_messages": log_messages,    # Lista de logs
        "num_hits": num_attacks          # Quantos ataques foram dados
    }