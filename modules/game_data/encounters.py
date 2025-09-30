# modules/game_data/encounters.py

import math
import random
from typing import Dict, Any
from .regions import get_region_profile
from . import monsters_data  # supondo que seus monstros-base fiquem aqui
from modules import player_manager

def _clamp(v, lo, hi):
    return max(lo, min(hi, v))

def pick_monster_for_region(region_id: str) -> dict:
    """
    Escolhe um monstro de uma pool da região.
    Você pode manter uma lista por região em monsters_data, ou filtrar por tags.
    """
    pool = monsters_data.REGION_POOLS.get(region_id) or monsters_data.REGION_POOLS.get("default", [])
    return dict(random.choice(pool)) if pool else dict(random.choice(monsters_data.DEFAULT_POOL))

def scale_monster_for_region(monster: dict, region_id: str, player_data: dict) -> dict:
    """
    Aplica multiplicadores de dificuldade da região e um scaling leve por tier vs. nível do jogador.
    Retorna um novo dicionário 'combat_details' pronto para usar.
    """
    region = get_region_profile(region_id)
    # base do monstro
    base_hp   = int(monster.get("hp", 10))
    base_atk  = int(monster.get("attack", 3))
    base_def  = int(monster.get("defense", 1))
    base_ini  = int(monster.get("initiative", 5))
    base_luck = int(monster.get("luck", 5))
    base_xp   = int(monster.get("xp_reward", 5))
    base_gold = int(monster.get("gold_drop", 3))

    # escala por dificuldade da região
    hp   = int(math.ceil(base_hp   * float(region.get("hp", 1.0))))
    atk  = int(math.ceil(base_atk  * float(region.get("attack", 1.0))))
    dfn  = int(math.ceil(base_def  * float(region.get("defense", 1.0))))
    ini  = int(math.ceil(base_ini  * float(region.get("initiative", 1.0))))
    lck  = int(math.ceil(base_luck * float(region.get("luck", 1.0))))

    xp   = int(math.ceil(base_xp   * float(region.get("xp", 1.0))))
    gold = int(math.ceil(base_gold * float(region.get("gold", 1.0))))

    # scaling por tier vs. nível do jogador (deixa a região mínima desafiadora pra high level e não trivially easy)
    plevel = int(player_data.get("level", 1))
    min_lv, max_lv = region.get("_range", (1, 999))
    tier = int(region.get("_tier", 1))

    # fator de pressão de nível: abaixo do piso da região, +dano do mob; acima do teto, -dano do mob, mas nunca trivial
    if plevel < min_lv:
        gap = min_lv - plevel
        # até +20% de atk/def a cada 5 níveis de gap (cap 60%)
        factor = 1.0 + _clamp(0.20 * (gap / 5.0), 0.0, 0.60)
        atk = int(math.ceil(atk * factor))
        dfn = int(math.ceil(dfn * (1.0 + 0.12 * (gap / 5.0))))   # defesa cresce um pouco menos
        hp  = int(math.ceil(hp  * (1.0 + 0.18 * (gap / 5.0))))
    elif plevel > max_lv:
        gap = plevel - max_lv
        # reduz levemente mas com piso pra não ficar ridículo
        atk = int(max(1, math.floor(atk * (1.0 - _clamp(0.15 * (gap / 5.0), 0.0, 0.45)))))
        dfn = int(max(0, math.floor(dfn * (1.0 - _clamp(0.10 * (gap / 5.0), 0.0, 0.35)))))
        # HP cai menos que o dano (pra lutas não virarem 1-hit)
        hp  = int(max(1, math.floor(hp * (1.0 - _clamp(0.08 * (gap / 5.0), 0.0, 0.25)))))

    # leve ajuste por tier (cada tier acima de 1 empurra ~6–10%)
    if tier > 1:
        tpush = 1.0 + 0.08 * (tier - 1)
        hp  = int(math.ceil(hp  * tpush))
        atk = int(math.ceil(atk * tpush))
        dfn = int(math.ceil(dfn * (1.0 + 0.05 * (tier - 1))))

    # viés na fuga por região
    flee_bias = float(region.get("flee_bias", 0.0))  # +/- 0.05 etc.

    # loot table pode ser herdada do monstro e ajustada pela região (drop multiplier)
    drop_mult = float(region.get("drop", 1.0))
    loot = []
    for it in monster.get("loot_table", []):
        dc = float(it.get("drop_chance", 0))
        loot.append({
            **it,
            "drop_chance": dc * drop_mult
        })

    # monta combat_details nos campos que seu handler já usa
    return {
        "monster_name": monster.get("name", "Inimigo"),
        "monster_hp": hp,
        "monster_attack": atk,
        "monster_defense": dfn,
        "monster_initiative": ini,
        "monster_luck": lck,
        "monster_xp_reward": xp,
        "monster_gold_drop": gold,
        "loot_table": loot,
        "flee_bias": flee_bias,
        "region_id": region_id,
        "region_difficulty": region.get("_difficulty"),
        "region_display": region.get("_display"),
        "battle_log": [],
    }
