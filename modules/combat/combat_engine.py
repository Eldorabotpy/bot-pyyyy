# modules/combat/combat_engine.py
import random
import logging
from typing import Any

# Importa os seus módulos de dados e regras
from modules.game_data.skills import SKILL_DATA
from modules.combat import criticals

logger = logging.getLogger(__name__)

def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default

def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default

async def processar_acao_combate(
    attacker_stats: dict,
    target_stats: dict,
    skill_id: str | None,
    attacker_current_hp: int = 9999,  # HP atual para skills (como low_hp_dmg_boost)
) -> dict:
    """
    Cérebro do combate: recebe stats e skill_id e retorna:
    {
      "total_damage": int,
      "log_messages": list[str],
      "num_hits": int,
      "hits": list[int]  # opcional, dano por golpe
    }

    Defensive — não lança exceções inesperadas; em caso de erro retorna um resultado com total_damage=0.
    """
    try:
        skill_info = SKILL_DATA.get(skill_id) if skill_id else None
        skill_effects = skill_info.get("effects", {}) if skill_info else {}

        # Cópias defensivas (não alteramos os dicts originais)
        attacker_stats_modified = dict(attacker_stats or {})
        target_stats_modified = dict(target_stats or {})

        log_messages = []

        # --- Normalize inputs ---
        # Garantir campos numéricos básicos
        attacker_stats_modified['initiative'] = _to_int(attacker_stats_modified.get('initiative', 0), 0)
        attacker_stats_modified['luck'] = _to_int(attacker_stats_modified.get('luck', 0), 0)
        attacker_stats_modified['max_hp'] = _to_int(attacker_stats_modified.get('max_hp', 1), 1)

        target_stats_modified['defense'] = _to_int(target_stats_modified.get('defense', 0), 0)

        # --- Efeitos provenientes da skill ---
        # multi_hit: quantos ataques a skill dá (se skill_id fornecido)
        num_attacks = _to_int(skill_effects.get("multi_hit", 0))
        defense_penetration = _to_float(skill_effects.get("defense_penetration", 0.0))
        bonus_crit_chance = _to_float(skill_effects.get("bonus_crit_chance", 0.0))

        # Determinação do número de ataques
        if skill_id:
            # skill define multi_hit (1 por padrão)
            num_attacks = max(1, _to_int(skill_effects.get("multi_hit", 1)))
        else:
            # ataque básico: chance de double attack via iniciativa
            initiative = _to_int(attacker_stats_modified.get('initiative', 0))
            double_attack_chance = (initiative * 0.25) / 100.0
            double_attack_chance = min(max(double_attack_chance, 0.0), 0.50)
            num_attacks = 2 if random.random() < double_attack_chance else 1
            if num_attacks == 2:
                log_messages.append("⚡ 𝐀𝐓𝐀Q𝐔𝐄 𝐃𝐔𝐏𝐋𝐎!")

        # Aplicar defesa penetrada (defense_penetration é fração entre 0.0 e 1.0)
        defense_penetration = max(min(defense_penetration, 1.0), 0.0)
        if defense_penetration > 0:
            original_def = _to_int(target_stats_modified.get('defense', 0))
            new_def = int(original_def * (1.0 - defense_penetration))
            new_def = max(new_def, 0)
            target_stats_modified['defense'] = new_def
            log_messages.append(f"💨 Você ignora {defense_penetration*100:.0f}% da defesa!")

        # Aplicar bônus temporário de critical (representamos como aumento de 'luck')
        # Nota: multiplicador 140 é heurístico — documentado aqui para revisão futura.
        if bonus_crit_chance > 0:
            added_luck = int(bonus_crit_chance * 140)
            attacker_stats_modified['luck'] = _to_int(attacker_stats_modified.get('luck', 0)) + added_luck
            log_messages.append("🎯 Mirando um ponto vital...")

        # Lógica para 'low_hp_dmg_boost' (ex.: fúria)
        skill_effects_to_use = dict(skill_effects)
        if "low_hp_dmg_boost" in skill_effects:
            attacker_max_hp = _to_int(attacker_stats_modified.get('max_hp', 1), 1)
            if attacker_max_hp <= 0:
                attacker_max_hp = 1
            player_hp_percent = float(attacker_current_hp) / float(attacker_max_hp)
            if player_hp_percent < 0.3:
                current_mult = _to_float(skill_effects_to_use.get("damage_multiplier", 1.0), 1.0)
                boost = _to_float(skill_effects.get("low_hp_dmg_boost", 0.0), 0.0)
                skill_effects_to_use["damage_multiplier"] = current_mult * (1.0 + boost)
                log_messages.append("🩸 Fúria Selvagem!")

        # --- Loop de ataques / cálculo de dano ---
        total_damage = 0
        hits = []

        for i in range(max(1, _to_int(num_attacks, 1))):
            # Aqui assumimos que criticals.roll_damage retorna (damage, is_crit, is_mega)
            player_damage_raw, is_crit, is_mega = criticals.roll_damage(
                attacker_stats_modified,
                target_stats_modified,
                skill_effects_to_use
            )

            # Force int and minimum 1 damage (evita 0 damage que pode travar lógicas que esperam progresso)
            player_damage = max(1, _to_int(player_damage_raw, 1))
            hits.append(player_damage)
            total_damage += player_damage

            if num_attacks > 1:
                log_messages.append(f"➡️ Golpe {i+1} causa {player_damage} de dano.")
            else:
                log_messages.append(f"➡️ Você causa {player_damage} de dano.")

            if is_mega:
                log_messages.append("💥💥 𝐌𝐄𝐆𝐀 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎!")
            elif is_crit:
                log_messages.append("💥 𝐃𝐀𝐍𝐎 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎!")

        # Resultado padronizado
        return {
            "total_damage": int(total_damage),
            "log_messages": log_messages,
            "num_hits": int(len(hits)),
            "hits": hits
        }

    except Exception as e:
        logger.exception(f"[processar_acao_combate] erro inesperado: {e}")
        # Retorna estrutura defensiva — nenhum dano aplicado
        return {
            "total_damage": 0,
            "log_messages": [f"Erro interno no cálculo de dano: {str(e)}"],
            "num_hits": 0,
            "hits": []
        }
