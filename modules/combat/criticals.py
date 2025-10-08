# modules/combat/criticals.py
import random
import math

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def _diminishing_crit_chance_from_luck(luck: int) -> float:
    l = max(0, int(luck))
    return 100.0 * (1.0 - (0.99 ** l))

def get_crit_params_for_player(player_data: dict, total_stats: dict) -> dict:
    luck = int(total_stats.get("luck", 5))
    chance = _clamp(_diminishing_crit_chance_from_luck(luck), 1.0, 40.0)
    # ... (adicione aqui a lógica de bônus por classe, se houver)
    return {
        "chance": chance,
        "mega_chance": min(25.0, luck / 2.0),
        "mult": 1.6,
        "mega_mult": 2.0,
        "min_damage": 1,
    }

def get_crit_params_for_monster(details: dict) -> dict:
    luck = int(details.get("monster_luck", details.get("luck", 5)))
    chance = _clamp(_diminishing_crit_chance_from_luck(luck), 1.0, 30.0)
    return {
        "chance": chance,
        "mega_chance": min(15.0, luck / 3.0),
        "mult": 1.5,
        "mega_mult": 1.75,
        "min_damage": 1,
    }

def roll_damage(raw_attack: int, target_defense: int, params: dict) -> tuple[int, bool, bool]:
    r = random.random() * 100.0
    is_crit = (r <= float(params.get("chance", 0.0)))
    mult, mega = 1.0, False
    if is_crit:
        if random.random() * 100.0 <= float(params.get("mega_chance", 0.0)):
            mult, mega = float(params.get("mega_mult", 2.0)), True
        else:
            mult = float(params.get("mult", 1.6))

    boosted = math.ceil(float(raw_attack) * mult)
    dmg = max(int(params.get("min_damage", 1)), boosted - int(target_defense))
    return dmg, is_crit, mega