# modules/combat/combat_engine.py
# (VERSÃO FINAL: Corrige logs invisíveis e falta de números)

import random
import logging
from typing import Optional, Dict, Any

from modules.game_data.skills import SKILL_DATA
from modules.combat import criticals
from modules.combat import durability 

logger = logging.getLogger(__name__)

def _get_player_skill_data_by_rarity(pdata: dict, skill_id: str) -> Optional[dict]:
    """Busca os dados base da skill e aplica os efeitos da raridade."""
    base_skill = SKILL_DATA.get(skill_id)
    if not base_skill: return None

    if "rarity_effects" not in base_skill:
        return base_skill.copy()

    player_skills = pdata.get("skills", {})
    rarity = "comum"
    if isinstance(player_skills, dict):
        skill_inst = player_skills.get(skill_id)
        if skill_inst: rarity = skill_inst.get("rarity", "comum")

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
    
    # --- 1. PREPARAÇÃO ---
    skill_info = None
    if skill_id:
        skill_info = _get_player_skill_data_by_rarity(attacker_pdata, skill_id)

    skill_effects = skill_info.get("effects", {}) if skill_info else {}        
    
    attacker_stats_modified = attacker_stats.copy()
    target_stats_modified = target_stats.copy()
    
    log_messages = [] 

    # --- 2. DURABILIDADE ---
    is_weapon_broken, _, (w_cur, w_max) = durability.is_weapon_broken(attacker_pdata)
    if is_weapon_broken:
        log_messages.append(f"⚠️ Sᴜᴀ ᴀʀᴍᴀ ᴇsᴛᴀ́ QUEBRADA!")
    
    # --- 3. MULTIPLICADORES ---
    # Força 1 hit se não definido
    raw_hits = skill_effects.get("multi_hit", 1)
    num_attacks = int(raw_hits)
    if num_attacks <= 0: num_attacks = 1 
    
    dmg_mult = float(skill_effects.get("damage_multiplier", skill_effects.get("damage_scale", 1.0)))
    defense_pen = float(skill_effects.get("defense_penetration", skill_effects.get("armor_penetration", 0.0)))
    magic_pen = float(skill_effects.get("magic_penetration", 0.0))
    
    # --- 4. ATAQUE BÁSICO / DUPLO ---
    if not skill_id:
        num_attacks = 1
        ini = attacker_stats_modified.get('initiative', 0)
        chance = (ini * 0.25) + attacker_stats_modified.get('double_attack_chance_flat', 0)
        
        if (random.random() * 100.0) < chance:
            num_attacks = 2
            log_messages.append("⚡ 𝐀𝐓𝐀𝐐𝐔𝐄 𝐃𝐔𝐏𝐋𝐎!")

    # --- 5. PENETRAÇÃO ---
    passive_pen = float(attacker_stats_modified.get("armor_penetration", 0.0))
    total_pen = min(1.0, defense_pen + passive_pen)
    
    if total_pen > 0:
        original_def = target_stats_modified.get('defense', 0)
        target_stats_modified['defense'] = int(original_def * (1.0 - total_pen))
        if total_pen >= 0.1:
            log_messages.append(f"💨 Iɢɴᴏʀᴏᴜ {int(total_pen*100)}% ᴅᴀ ᴅᴇғᴇsᴀ!")

    # --- 6. BERSERK / LIFE CHECK ---
    roll_opts = skill_effects.copy()
    roll_opts["damage_multiplier"] = dmg_mult
    
    if "low_hp_dmg_boost" in skill_effects:
        max_hp = attacker_stats.get('max_hp', 1)
        if (attacker_current_hp / max_hp) < 0.3:
            bonus = float(skill_effects["low_hp_dmg_boost"].get("bonus_mult", 0.0))
            roll_opts["damage_multiplier"] += bonus
            log_messages.append("🩸 𝙁𝙪́𝙧𝙞𝙖 𝘼𝙩𝙞𝙫𝙖𝙙𝙖!")

    # --- 7. LOOP DE DANO E LOGS ---
    total_damage = 0
    
    for i in range(num_attacks):
        dmg_raw, is_crit, is_mega = criticals.roll_damage(
            attacker_stats_modified, 
            target_stats_modified, 
            roll_opts 
        )
        
        final_hit = max(1, int(dmg_raw))
        total_damage += final_hit
        
        # --- CONSTROI A MENSAGEM DO GOLPE ---
        hit_msg = ""
        if is_mega:
            hit_msg = f"💥💥 𝑴𝑬𝑮𝑨 𝑪𝑹𝑰́𝑻𝑰𝑪𝑶: {final_hit}!"
        elif is_crit:
            hit_msg = f"💥 𝗖𝗥𝗜́𝗧𝗜𝗖𝗢: {final_hit}!"
        else:
            # Golpe normal agora tem texto
            hit_msg = f"⚔️ Dᴀɴᴏ: {final_hit}"

        # Adiciona ao log principal
        if num_attacks > 1:
            log_messages.append(f"➡️ Gᴏʟᴘᴇ {i+1}: {hit_msg}")
        else:
            # Se for 1 hit, joga direto
            log_messages.append(hit_msg)

    return {
        "total_damage": total_damage,    
        "log_messages": log_messages,    
        "num_hits": num_attacks          
    }