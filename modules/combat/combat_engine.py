# modules/combat/combat_engine.py
# (VERSÃO CORRIGIDA: Importando durability da pasta correta 'modules.combat')

import random
import logging
from typing import Optional, Dict, Any

from modules.game_data.skills import SKILL_DATA
from modules.combat import criticals
from modules import player_manager

# --- CORREÇÃO AQUI ---
# Como o arquivo está em modules/combat/durability.py, importamos dele:
from modules.combat import durability 
# ---------------------

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
    attacker_pdata: dict, 
    attacker_stats: dict, 
    target_stats: dict, 
    skill_id: str | None,
    attacker_current_hp: int = 9999, 
) -> dict:
    """
    Este é o CÉREBRO UNIFICADO do combate.
    """
    
    # 1. Recupera dados da Skill (com raridade)
    if skill_id:
        skill_info = _get_player_skill_data_by_rarity(attacker_pdata, skill_id)
    else:
        skill_info = None

    skill_effects = skill_info.get("effects", {}) if skill_info else {}        
    attacker_stats_modified = attacker_stats.copy()
    target_stats_modified = target_stats.copy()
    
    log_messages = [] 

    # =========================================================================
    # 🛡️ 1. VERIFICAÇÃO DE ARMA QUEBRADA (Reduz Ataque)
    # =========================================================================
    is_weapon_broken, weapon_uid, (w_cur, w_max) = durability.is_weapon_broken(attacker_pdata)
    
    if is_weapon_broken:
        # PENALIDADE: Reduz o ataque em 90%
        original_atk = attacker_stats_modified.get('attack', 10)
        attacker_stats_modified['attack'] = max(1, int(original_atk * 0.1))
        
        log_messages.append(f"⚠️ <b>Sua arma está QUEBRADA ({w_cur}/{w_max})!</b>")
        log_messages.append("<i>Seu dano foi drasticamente reduzido.</i>")
    
    # =========================================================================
    # 🛡️ 2. VERIFICAÇÃO DE ARMADURA QUEBRADA (Reduz Defesa)
    # =========================================================================
    # Lista de slots de armadura para verificar
    armor_slots = ["elmo", "armadura", "calca", "luvas", "botas", "anel", "colar", "brinco"]
    broken_armor_count = 0
    
    equip = attacker_pdata.get("equipment", {})
    inv = attacker_pdata.get("inventory", {})
    
    for slot in armor_slots:
        uid = equip.get(slot)
        if uid and uid in inv:
            item = inv[uid]
            if durability.is_item_broken(item):
                broken_armor_count += 1
                
    if broken_armor_count > 0:
        # PENALIDADE: -10% de Defesa por peça quebrada
        penalty_percent = 0.10 * broken_armor_count
        # Limita a penalidade máxima a 80% (para não zerar a defesa totalmente)
        penalty_percent = min(0.80, penalty_percent)
        
        original_def = attacker_stats_modified.get('defense', 0)
        new_def = int(original_def * (1.0 - penalty_percent))
        attacker_stats_modified['defense'] = new_def
        
        log_messages.append(f"⚠️ <b>{broken_armor_count} equipamentos quebrados!</b>")
        log_messages.append(f"<i>Defesa reduzida em {int(penalty_percent*100)}%.</i>")

    # =========================================================================

    num_attacks = int(skill_effects.get("multi_hit", 0))
    defense_penetration = float(skill_effects.get("defense_penetration", 0.0))
    bonus_crit_chance = float(skill_effects.get("bonus_crit_chance", 0.0))

    if skill_id:
        num_attacks = int(skill_effects.get("multi_hit", 1))
    else:
        # Ataque Básico
        initiative = attacker_stats_modified.get('initiative', 0)
        double_attack_chance = (initiative * 0.25) / 100.0
        num_attacks = 2 if random.random() < min(double_attack_chance, 0.50) else 1
        
        if num_attacks == 2:
            log_messages.append("⚡ 𝐀𝐓𝐀Q𝐔𝐄 𝐃𝐔𝐏𝐋𝐎!")
    
    if defense_penetration > 0:
        target_stats_modified['defense'] = int(target_stats_modified['defense'] * (1.0 - defense_penetration))
        log_messages.append(f"💨 Você ignora {defense_penetration*100:.0f}% da defesa!")
    
    if bonus_crit_chance > 0:
        attacker_stats_modified['luck'] += int(bonus_crit_chance * 140) 
        log_messages.append(f"🎯 Mirando um ponto vital...")

    # Lógica para 'low_hp_dmg_boost'
    skill_effects_to_use = skill_effects.copy()
    if "low_hp_dmg_boost" in skill_effects:
        attacker_max_hp = attacker_stats.get('max_hp', 1) or 1
        player_hp_percent = attacker_current_hp / attacker_max_hp
        
        if player_hp_percent < 0.3: 
            current_mult = skill_effects_to_use.get("damage_multiplier", 1.0)
            boost = 1.0 + skill_effects.get("low_hp_dmg_boost", 0.0)
            skill_effects_to_use["damage_multiplier"] = current_mult * boost
            log_messages.append(f"🩸 Fúria Selvagem!")

    # --- Cálculo de Dano (Loop de Ataque) ---
    total_damage = 0
    
    for i in range(num_attacks):
        
        player_damage_raw, is_crit, is_mega = criticals.roll_damage(
            attacker_stats_modified, 
            target_stats_modified, 
            skill_effects_to_use 
        )
        
        player_damage = max(1, int(player_damage_raw))
        total_damage += player_damage
        
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
        "total_damage": total_damage,    
        "log_messages": log_messages,    
        "num_hits": num_attacks          
    }