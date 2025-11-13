# modules/combat/criticals.py (VERSÃO MELHORADA)
import random
import math
import logging
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)

def _clamp(v: float, lo: float, hi: float) -> float:
    """Garante que um valor permaneça dentro de um intervalo mínimo e máximo."""
    try:
        fv = float(v)
    except Exception:
        fv = lo
    return max(lo, min(hi, fv))

def _diminishing_crit_chance_from_luck(luck: int) -> float:
    """Calcula a chance de crítico com base na sorte, com retornos decrescentes.
    Retorna um valor em percentual (0.0 - 100.0).
    """
    l = max(0, int(luck))
    # Fórmula: 1 - 0.99^LUCK -> valor entre 0 e ~1; multiplicamos por 100.
    return 100.0 * (1.0 - (0.99 ** l))

def get_crit_params(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gera parâmetros de crítico com base nos stats da entidade.
    Saída:
    {
      "chance": float,       # % chance de crítico
      "mega_chance": float,  # % chance de tornar crítico em mega
      "mult": float,         # multiplicador para crítico normal
      "mega_mult": float,    # multiplicador para mega crítico
      "min_damage": int
    }
    """
    luck = int(stats.get("luck", 5))

    # Detecta se é monstro (heurística: chaves específicas)
    is_monster = ('monster_luck' in stats) or ('monster_name' in stats)

    # Teto de chance base: monstros têm teto menor
    chance_cap = 30.0 if is_monster else 40.0

    chance = _diminishing_crit_chance_from_luck(luck)
    chance = _clamp(chance, 0.0, chance_cap)

    # Multiplicadores de dano
    mult = 1.5 if is_monster else 1.6
    mega_mult = 1.75 if is_monster else 2.0

    # Mega chance: limitado ao intervalo [0, 100], com teto seguro
    mega_chance = _clamp(min(25.0, (luck / 2.0)), 0.0, 100.0)

    return {
        "chance": chance,
        "mega_chance": mega_chance,
        "mult": float(mult),
        "mega_mult": float(mega_mult),
        "min_damage": 1,
    }

def roll_damage(attacker_stats: Dict[str, Any], target_stats: Dict[str, Any], options: Dict[str, Any] = None) -> Tuple[int, bool, bool]:
    """
    Calcula o dano esperado de um ataque.
    Retorna (final_damage:int, is_crit:bool, is_mega:bool)

    Options suportadas:
      - damage_multiplier: float (multiplica attack base)
      - damage_type: "magic" ou outro (magic ignora defesa)
      - bonus_crit_chance: float (em pontos percentuais, adicionado à chance calculada)
    """
    if options is None:
        options = {}

    try:
        raw_attack = int(attacker_stats.get('attack', 0))
    except Exception:
        raw_attack = 0

    try:
        target_defense = int(target_stats.get('defense', 0))
    except Exception:
        target_defense = 0

    params = get_crit_params(attacker_stats)

    # Permite que options adicionem chance de crítico sem alterar stats
    base_chance = float(params.get("chance", 0.0))
    bonus_crit = float(options.get("bonus_crit_chance", 0.0))
    chance = _clamp(base_chance + bonus_crit, 0.0, 100.0)

    mega_chance = _clamp(float(params.get("mega_chance", 0.0)), 0.0, 100.0)

    skill_mult = float(options.get("damage_multiplier", 1.0))
    damage_type = options.get("damage_type", None)

    # Rola crítico
    r = random.random() * 100.0
    is_crit = (r <= chance)
    is_mega = False

    crit_mult = 1.0
    if is_crit:
        # decide se é mega
        if random.random() * 100.0 <= mega_chance:
            crit_mult = float(params.get("mega_mult", 2.0))
            is_mega = True
        else:
            crit_mult = float(params.get("mult", 1.6))

    # Cálculo base do ataque com multiplicadores
    attack_with_skill = float(raw_attack) * skill_mult
    boosted_attack = math.ceil(attack_with_skill * crit_mult)

    # Aplica defesa (a menos que seja dano mágico)
    if str(damage_type).lower() == "magic":
        final_damage = max(int(params.get("min_damage", 1)), int(boosted_attack))
    else:
        # defesa não pode ser negativa (protege)
        target_defense = max(0, int(target_defense))
        final_damage = max(int(params.get("min_damage", 1)), int(boosted_attack) - target_defense)

    # Garantir que final_damage é inteiro não-negativo
    final_damage = max(0, int(final_damage))

    # Debug log opcional
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "roll_damage: atk=%s def=%s skill_mult=%s crit=%s mega=%s crit_mult=%s boosted=%s final=%s (chance=%s bonus_crit=%s)",
            raw_attack, target_defense, skill_mult, is_crit, is_mega, crit_mult, boosted_attack, final_damage, chance, bonus_crit
        )

    return final_damage, bool(is_crit), bool(is_mega)
