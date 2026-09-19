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
    
    # 👇 1. CRIE A LISTA DE LOGS AQUI NO TOPO! 👇
    log_messages: list[str] = []

    # --- 1. PREPARAÇÃO (CANÔNICO) ---
    canon = None
    canon_effects: dict = {}
    attacker_mp_left = attacker_current_mp
    
    # NOVAS VARIÁVEIS PARA O FRONTEND
    anim_effect_to_frontend = ""
    skill_type_to_frontend = "active"

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
        
        # 👇 1. A NOVA TRAVA: VERIFICA O COOLDOWN ANTES DE GASTAR MANA 👇
        from modules.cooldowns import verificar_cooldown
        pode_usar, msg_erro = verificar_cooldown(attacker_pdata, skill_id)
        if not pode_usar:
            return {
                "total_damage": 0,
                "log_messages": [f"⚠️ {msg_erro}"], # Retorna: "⏳ Aguarde X turno(s)!"
                "num_hits": 0,
                "attacker_mp_left": attacker_current_mp, # Devolve a mana intacta
                "anim_effect": "",
                "tipo_skill": ""
            }

        # ======= LÓGICA DE CONSUMO DE MANA =======
        # 🛠️ CORREÇÃO: Usa a função que abre a gaveta de raridade para achar a mana!
        merged_skill = _get_player_skill_data_by_rarity(attacker_pdata, skill_id) or SKILL_DATA.get(skill_id, {})
        
        mana_cost = int(merged_skill.get("mana_cost", merged_skill.get("mp_cost", 0)))
        
        # 👇 CAPTURA O EFEITO VISUAL PARA MANDAR PRO JS
        anim_effect_to_frontend = merged_skill.get("anim_effect", "")
        skill_type_to_frontend = merged_skill.get("type", "active")
        
        if attacker_mp_left < mana_cost:
            # Caso não tenha mana suficiente, o feitiço falha
            return {
                "total_damage": 0,
                "log_messages": [f"⚠️ 𝗠𝗮𝗻𝗮 𝗶𝗻𝘀𝘂𝗳𝗶𝗰𝗶𝗲𝗻𝘁𝗲! Precisa de {mana_cost} MP. O feitiço falhou!"],
                "num_hits": 0,
                "attacker_mp_left": attacker_mp_left,
                "anim_effect": "",
                "tipo_skill": ""
            }
        
        # Desconta a mana usada da conta do jogador
        attacker_mp_left -= mana_cost
        
        # 👇 NOVO: Adiciona o nome da Magia ao log para o Frontend renderizar
        skill_name = merged_skill.get("name", "Habilidade Secreta")
        # log_messages.append(f"✨ Cᴏɴᴊᴜʀᴏᴜ {skill_name}!")

        # 👇 CHAMA A FUNÇÃO DE COOLDOWN PARA COMEÇAR A CONTAGEM (NOVA LINHA!)
        from modules.cooldowns import aplicar_cooldown
        attacker_pdata = aplicar_cooldown(attacker_pdata, skill_id, rarity)
        # =========================================
        
    attacker_stats_modified = attacker_stats.copy()
    target_stats_modified = target_stats.copy()

    # --- 2. DURABILIDADE ---
    is_weapon_broken, _, (w_cur, w_max) = durability.is_weapon_broken(attacker_pdata)
    if is_weapon_broken:
        log_messages.append("⚠️ Sᴜᴀ ᴀʀᴍᴀ ᴇsᴛᴀ́ QUEBRADA!")

    # --- 3. MULTI-HIT / MULTIPLICADORES / PENETRAÇÃO (CANÔNICO -> BRIDGE) ---
    damage_def = (canon_effects.get("damage") or {}) if canon_effects else {}
    multi_def = (canon_effects.get("multi_hit") or {}) if canon_effects else {}
    exec_def = (canon_effects.get("execute") or {}) if canon_effects else {}

    # 👇 A CORREÇÃO DE OURO: Lê as propriedades diretas do seu banco de dados
    raw_effects = {}
    
    num_attacks = 1 # 👈 NOVO: O PADRÃO SEMPRE É 1 ATAQUE!

    if not skill_id:
        # log_messages.append("🗡️ Aᴛᴀᴄᴏᴜ ᴄᴏᴍ ᴀ ᴀʀᴍᴀ!") 
        # O log do ataque base fica aqui, mas a variável num_attacks já foi declarada lá em cima
        pass
    if multi_def:
        mh_min = int(multi_def.get("min", 1) or 1)
        mh_max = int(multi_def.get("max", mh_min) or mh_min)
        if mh_min > mh_max:
            mh_min, mh_max = mh_max, mh_min
        num_attacks = random.randint(max(1, mh_min), max(1, mh_max))

    # Multiplicador de dano: Usa o Canon se existir, ou pega direto do seu JSON
    if multi_def:
        dmg_mult = float(multi_def.get("per_hit_mult", 1.0) or 1.0)
    elif damage_def and "mult" in damage_def:
        dmg_mult = float(damage_def.get("mult", 1.0) or 1.0)
    elif "damage_multiplier" in raw_effects:
        dmg_mult = float(raw_effects.get("damage_multiplier", 1.0))
    else:
        dmg_mult = 1.0

    # Penetração (armadura/defesa física)
    defense_pen = float(damage_def.get("armor_pen", 0.0) or 0.0) if damage_def else 0.0
    bonus_crit = float(damage_def.get("bonus_crit", 0.0) or 0.0) if damage_def else 0.0

    # --- 4. ATAQUE BÁSICO / DUPLO ---
    if not skill_id:
        num_attacks = 1
        ini = attacker_stats_modified.get("initiative", 0)
        chance = min(50.0, max(0.0, (ini * 0.25) + attacker_stats_modified.get("double_attack_chance_flat", 0)))
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
    
    # Overrides de passivas
    po = passive_overrides or {}
    d_add = float(po.get("damage_mult_add", 0.0) or 0.0)
    if d_add:
        roll_opts["damage_multiplier"] = float(roll_opts.get("damage_multiplier", 1.0)) * (1.0 + d_add)

    c_add = float(po.get("bonus_crit_chance_add", 0.0) or 0.0)
    if c_add:
        roll_opts["bonus_crit_chance"] = float(roll_opts.get("bonus_crit_chance", 0.0)) + c_add

    if bool(po.get("cannot_be_dodged", False)):
        roll_opts["cannot_be_dodged"] = True

    if bonus_crit > 0:
        roll_opts["bonus_crit_chance"] = float(roll_opts.get("bonus_crit_chance", 0.0)) + float(bonus_crit)
    
    if damage_def and bool(damage_def.get("cannot_dodge", False)):
        roll_opts["cannot_be_dodged"] = True

    # 👇 A CORREÇÃO MÁGICA: Garante que o jogo sabe que a magia usa Inteligência e não Força!
    if (damage_def and damage_def.get("type") == "magic") or (raw_effects.get("damage_type") == "magic"):
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
    hits = []

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

        hits.append({"damage": final_hit, "critical": is_crit, "hit_number": i + 1, "log_index": len(log_messages) - 1})

    return {
        "hits": hits,
        "total_damage": total_damage,
        "log_messages": log_messages,
        "num_hits": int(num_attacks),
        "attacker_mp_left": attacker_mp_left, # <--- DEVOLVE A MANA RESTANTE!
        # 👇 MANDA AS INFORMAÇÕES VISUAIS PARA O LOG
        "anim_effect": anim_effect_to_frontend, 
        "tipo_skill": skill_type_to_frontend
    }
