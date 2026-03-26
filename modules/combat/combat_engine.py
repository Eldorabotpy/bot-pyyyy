# modules/combat/combat_engine.py
# (VERSÃO FINAL: Corrige logs invisíveis e falta de números)

import random
import logging
from typing import Optional, Dict, Any
from modules.skills.skill_canonical_adapter import adapt_skill_to_canon
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
    attacker_current_mp: int = 9999,
    passive_overrides: dict | None = None,
) -> dict:
    # --- 1. PREPARAÇÃO (CANÔNICO) ---
    canon = None
    canon_effects: dict = {}
    attacker_mp_left = attacker_current_mp

    if skill_id:
        rarity = (
            attacker_pdata
            .get("skills", {})
            .get(skill_id, {})
            .get("rarity", "comum")
        )

        canon = adapt_skill_to_canon(
            skills_db=SKILL_DATA,
            skill_id=skill_id,
            rarity=rarity,
        )
        canon_effects = (canon or {}).get("effects", {}) or {}
        
        # ======= LÓGICA DE CONSUMO DE MANA =======
        base_skill = SKILL_DATA.get(skill_id, {})
        mana_cost = int(base_skill.get("mana_cost", base_skill.get("mp_cost", 0)))
        
        if attacker_mp_left < mana_cost:
            # Caso não tenha mana suficiente, o feitiço falha
            return {
                "total_damage": 0,
                "log_messages": ["⚠️ 𝗠𝗮𝗻𝗮 𝗶𝗻𝘀𝘂𝗳𝗶𝗰𝗶𝗲𝗻𝘁𝗲! O feitiço falhou e você perdeu o turno."],
                "num_hits": 0,
                "attacker_mp_left": attacker_mp_left
            }
        
        # Desconta a mana usada
        attacker_mp_left -= mana_cost
        # =========================================
        
    attacker_stats_modified = attacker_stats.copy()
    target_stats_modified = target_stats.copy()
    log_messages: list[str] = []

    # --- 2. DURABILIDADE ---
    is_weapon_broken, _, (w_cur, w_max) = durability.is_weapon_broken(attacker_pdata)
    if is_weapon_broken:
        log_messages.append("⚠️ Sᴜᴀ ᴀʀᴍᴀ ᴇsᴛᴀ́ QUEBRADA!")

    # --- 3. MULTI-HIT / MULTIPLICADORES / PENETRAÇÃO (CANÔNICO -> BRIDGE) ---
    damage_def = (canon_effects.get("damage") or {}) if canon_effects else {}
    multi_def = (canon_effects.get("multi_hit") or {}) if canon_effects else {}
    exec_def = (canon_effects.get("execute") or {}) if canon_effects else {}

    # Hits da skill (se for multi-hit canônico)
    num_attacks = 1
    if multi_def:
        mh_min = int(multi_def.get("min", 1) or 1)
        mh_max = int(multi_def.get("max", mh_min) or mh_min)
        if mh_min > mh_max:
            mh_min, mh_max = mh_max, mh_min
        num_attacks = random.randint(max(1, mh_min), max(1, mh_max))

    # Multiplicador de dano
    # - multi_hit: per_hit_mult
    # - dano simples: damage.mult
    if multi_def:
        dmg_mult = float(multi_def.get("per_hit_mult", 1.0) or 1.0)
    elif damage_def:
        dmg_mult = float(damage_def.get("mult", 1.0) or 1.0)
    else:
        dmg_mult = 1.0

    # Penetração (armadura/defesa física)
    defense_pen = 0.0
    if damage_def:
        defense_pen = float(damage_def.get("armor_pen", 0.0) or 0.0)

    # Se você tiver magia depois, deixe aqui (por ora, mantemos compatível)
    magic_pen = 0.0

    # Bônus de crítico “neste golpe” (Golpe Sombrio épico/lendário etc.)
    bonus_crit = 0.0
    if damage_def:
        bonus_crit = float(damage_def.get("bonus_crit", 0.0) or 0.0)

    # --- 4. ATAQUE BÁSICO / DUPLO ---
    # Só aplica ataque duplo quando NÃO há skill ativa
    if not skill_id:
        num_attacks = 1
        ini = attacker_stats_modified.get("initiative", 0)
        chance = (ini * 0.25) + attacker_stats_modified.get("double_attack_chance_flat", 0)

        if (random.random() * 100.0) < chance:
            num_attacks = 2
            log_messages.append("⚡ 𝐀𝐓𝐀𝐐𝐔𝐄 𝐃𝐔𝐏𝐋𝐎!")

    # --- 5. PENETRAÇÃO TOTAL ---
    passive_pen = float(attacker_stats_modified.get("armor_penetration", 0.0) or 0.0)
    pen_add = float((passive_overrides or {}).get("armor_pen_add", 0.0) or 0.0)
    total_pen = min(1.0, max(0.0, defense_pen + passive_pen + pen_add))

    if total_pen > 0:
        original_def = target_stats_modified.get("defense", 0) or 0
        target_stats_modified["defense"] = int(original_def * (1.0 - total_pen))
        if total_pen >= 0.1:
            log_messages.append(f"💨 Iɢɴᴏʀᴏᴜ {int(total_pen * 100)}% ᴅᴀ ᴅᴇғᴇsᴀ!")

    # --- 6. OPÇÕES DE ROLL (bridge para criticals.roll_damage) ---
    roll_opts = {}
    roll_opts["damage_multiplier"] = float(dmg_mult)
    # --- 6.1 OVERRIDES DE PASSIVAS (handler -> engine) ---
    po = passive_overrides or {}

    # dano: +X% (aditivo) aplicado como multiplicativo
    d_add = float(po.get("damage_mult_add", 0.0) or 0.0)
    if d_add:
        roll_opts["damage_multiplier"] = float(roll_opts.get("damage_multiplier", 1.0)) * (1.0 + d_add)

    # crit chance flat
    c_add = float(po.get("bonus_crit_chance_add", 0.0) or 0.0)
    if c_add:
        roll_opts["bonus_crit_chance"] = float(roll_opts.get("bonus_crit_chance", 0.0)) + c_add

    # cannot be dodged
    if bool(po.get("cannot_be_dodged", False)):
        roll_opts["cannot_be_dodged"] = True

    if bonus_crit > 0:
        roll_opts["bonus_crit_chance"] = float(bonus_crit)
    
    # Acerto garantido (não pode ser esquivado) - canônico
    cannot_dodge = bool(damage_def.get("cannot_dodge", False)) if damage_def else False
    if cannot_dodge:
        roll_opts["cannot_be_dodged"] = True

    # (opcional para o futuro) tipo de dano
    if damage_def and damage_def.get("type") == "magic":
        roll_opts["is_magic"] = True

    # Berserk / low hp do atacante
    if "low_hp_dmg_boost" in canon_effects:
        max_hp = attacker_stats.get("max_hp", 1) or 1
        if (attacker_current_hp / max_hp) < 0.3:
            bonus = float((canon_effects["low_hp_dmg_boost"] or {}).get("bonus_mult", 0.0) or 0.0)
            roll_opts["damage_multiplier"] += bonus
            log_messages.append("🩸 𝙁𝙪́𝙧𝙞𝙖 𝘼𝙩𝙞𝙫𝙖𝙙𝙖!")

    # Execução (bônus por alvo com HP baixo)
    if exec_def:
        try:
            t_hp = float(target_stats_modified.get("hp", 0) or 0)
            t_mx = float(target_stats_modified.get("max_hp", 0) or 0)
            if t_mx > 0:
                pct = t_hp / t_mx
                hp_lt = float(exec_def.get("hp_lt", 0.0) or 0.0)
                bonus_mult = float(exec_def.get("bonus_mult", 0.0) or 0.0)
                if pct <= hp_lt and bonus_mult > 0:
                    roll_opts["damage_multiplier"] += bonus_mult
                    log_messages.append("🗡️ 𝐄𝐗𝐄𝐂𝐔𝐂̧𝐀̃𝐎!")
        except Exception:
            pass

    # --- 7. LOOP DE DANO E LOGS ---
    total_damage = 0

    for i in range(int(num_attacks)):
        dmg_raw, is_crit, is_mega = criticals.roll_damage(
            attacker_stats_modified,
            target_stats_modified,
            roll_opts
        )

        final_hit = max(0, int(dmg_raw))
        total_damage += final_hit

        # --- CONSTROI A MENSAGEM DO GOLPE ---
        if final_hit == 0:
            hit_msg = "💨 O alvo esquivou!"
        elif is_mega:
            hit_msg = f"💥💥 𝑴𝑬𝑮𝑨 𝑪𝑹𝑰́𝑻𝑰𝑪𝑶: {final_hit}!"
        elif is_crit:
            hit_msg = f"💥 𝗖𝗥𝗜́𝗧𝗜𝗖𝗢: {final_hit}!"
        else:
            hit_msg = f"⚔️ Dᴀɴᴏ: {final_hit}"

        if num_attacks > 1:
            log_messages.append(f"➡️ Gᴏʟᴘᴇ {i + 1}: {hit_msg}")
        else:
            log_messages.append(hit_msg)

    return {
        "total_damage": total_damage,
        "log_messages": log_messages,
        "num_hits": int(num_attacks),
        "attacker_mp_left": attacker_mp_left # <--- DEVOLVE A MANA RESTANTE!
    }
