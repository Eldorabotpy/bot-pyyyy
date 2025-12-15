# modules/combat/combat_engine.py
# (VERSÃO OTIMIZADA: Suporte a Passivas de Crítico e Ataque Duplo Corrigido)

import random
import logging
from typing import Optional, Dict, Any

from modules.game_data.skills import SKILL_DATA
from modules.combat import criticals
from modules.combat import durability 

logger = logging.getLogger(__name__)


def _get_player_skill_data_by_rarity(pdata: dict, skill_id: str) -> Optional[dict]:
    """
    Busca os dados base da skill e aplica os efeitos da raridade que o jogador possui.
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
    CÉREBRO UNIFICADO DO COMBATE
    Processa ataques, skills, durabilidade e buffs.
    """
    
    # 1. Recupera dados da Skill
    skill_info = None
    if skill_id:
        skill_info = _get_player_skill_data_by_rarity(attacker_pdata, skill_id)

    skill_effects = skill_info.get("effects", {}) if skill_info else {}        
    
    # Cria cópias dos status para não alterar o original permanentemente
    attacker_stats_modified = attacker_stats.copy()
    target_stats_modified = target_stats.copy()
    
    log_messages = [] 

    # =========================================================================
    # 🛡️ 1. VERIFICAÇÃO DE ARMA QUEBRADA
    # =========================================================================
    is_weapon_broken, weapon_uid, (w_cur, w_max) = durability.is_weapon_broken(attacker_pdata)
    
    if is_weapon_broken:
        log_messages.append(f"⚠️ <b>Sua arma está QUEBRADA ({w_cur}/{w_max})!</b>")
        # Sem penalidade de dano por enquanto, apenas aviso visual.
    
    # =========================================================================
    # 🛡️ 2. VERIFICAÇÃO DE ARMADURA QUEBRADA
    # =========================================================================
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
        # PENALIDADE: -10% de Defesa por peça quebrada (Max -80%)
        penalty_percent = min(0.80, 0.10 * broken_armor_count)
        
        original_def = attacker_stats_modified.get('defense', 0)
        new_def = int(original_def * (1.0 - penalty_percent))
        attacker_stats_modified['defense'] = new_def
        
        log_messages.append(f"⚠️ <b>{broken_armor_count} equipamentos quebrados!</b>")
        log_messages.append(f"<i>Defesa reduzida em {int(penalty_percent*100)}%.</i>")

    # =========================================================================
    # ⚔️ 3. CÁLCULOS DE SKILLS E PASSIVAS
    # =========================================================================

    num_attacks = int(skill_effects.get("multi_hit", 0))
    defense_penetration = float(skill_effects.get("defense_penetration", 0.0))
    
    # Bônus de Crítico ATIVO (Buffs temporários, valor 0.0 a 1.0)
    active_bonus_crit = float(skill_effects.get("bonus_crit_chance", 0.0))
    
    # Bônus de Crítico PASSIVO (Auras/Itens, valor 0 a 100)
    passive_crit_flat = float(attacker_stats_modified.get("crit_chance_flat", 0.0))

    # --- LÓGICA DE ATAQUE BÁSICO & ATAQUE DUPLO ---
    if not skill_id: # Apenas para ataques básicos
        num_attacks = 1
        
        # Fórmula: (Iniciativa * 0.25) + Bônus Fixo das Skills
        initiative = attacker_stats_modified.get('initiative', 0)
        base_chance = initiative * 0.25
        flat_bonus = attacker_stats_modified.get('double_attack_chance_flat', 0)
        
        total_double_chance = base_chance + flat_bonus
        
        # Rola o dado (0.0 a 100.0)
        if (random.random() * 100.0) < total_double_chance:
            num_attacks = 2
            log_messages.append("⚡ 𝐀𝐓𝐀Q𝐔𝐄 𝐃𝐔𝐏𝐋𝐎!")

    # --- PENETRAÇÃO DE DEFESA ---
    # Soma a penetração da skill com a penetração passiva dos status
    passive_pen = float(attacker_stats_modified.get("armor_penetration", 0.0))
    total_penetration = defense_penetration + passive_pen
    
    if total_penetration > 0:
        # Limita a 100%
        total_penetration = min(1.0, total_penetration)
        target_stats_modified['defense'] = int(target_stats_modified['defense'] * (1.0 - total_penetration))
        if total_penetration >= 0.1: # Só avisa se for relevante
            log_messages.append(f"💨 Você ignora {total_penetration*100:.0f}% da defesa!")
    
    # --- APLICAÇÃO DE BÔNUS DE CRÍTICO ---
    # Aqui convertemos as chances extras em SORTE para o criticals.py entender
    luck_bonus = 0
    
    # 1. Bônus Ativo (ex: 0.15 = 15%) -> Fator 140
    if active_bonus_crit > 0:
        luck_bonus += int(active_bonus_crit * 140)
        
    # 2. Bônus Passivo (ex: 10.0 = 10%) -> Fator 1.4 (para manter equivalência)
    if passive_crit_flat > 0:
        luck_bonus += int(passive_crit_flat * 1.4)
        
    if luck_bonus > 0:
        attacker_stats_modified['luck'] += luck_bonus
        log_messages.append(f"🎯 Foco Absoluto (+{luck_bonus} Sorte)")

    # --- BÔNUS DE DANO POR BAIXA VIDA (BERSERK) ---
    skill_effects_to_use = skill_effects.copy()
    if "low_hp_dmg_boost" in skill_effects:
        attacker_max_hp = attacker_stats.get('max_hp', 1) or 1
        player_hp_percent = attacker_current_hp / attacker_max_hp
        
        if player_hp_percent < 0.3: 
            current_mult = skill_effects_to_use.get("damage_multiplier", 1.0)
            boost = 1.0 + skill_effects.get("low_hp_dmg_boost", 0.0)
            skill_effects_to_use["damage_multiplier"] = current_mult * boost
            log_messages.append(f"🩸 Fúria Selvagem!")

    # =========================================================================
    # ⚔️ 4. LOOP DE DANO
    # =========================================================================
    total_damage = 0
    
    for i in range(num_attacks):
        
        player_damage_raw, is_crit, is_mega = criticals.roll_damage(
            attacker_stats_modified, 
            target_stats_modified, 
            skill_effects_to_use 
        )
        
        player_damage = max(1, int(player_damage_raw))
        total_damage += player_damage
        
        # Formatação do Log
        if num_attacks > 1:
            log_messages.append(f"➡️ Golpe {i+1}: {player_damage} dano.")
        else:
            log_messages.append(f"➡️ Você causa {player_damage} de dano.")

        if is_mega: 
            log_messages.append("💥💥 𝐌𝐄𝐆𝐀 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎!")
        elif is_crit: 
            log_messages.append("💥 𝐃𝐀𝐍𝐎 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎!")

    return {
        "total_damage": total_damage,    
        "log_messages": log_messages,    
        "num_hits": num_attacks          
    }