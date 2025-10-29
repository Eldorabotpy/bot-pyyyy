# modules/player/stats.py (VERSÃO FINAL COMPLETA)

from __future__ import annotations
from typing import Dict, Optional, Tuple

from modules import game_data, clan_manager
from modules.game_data.class_evolution import get_evolution_options

# ========================================
# CONSTANTES DE PROGRESSÃO DE CLASSE
# ========================================

CLASS_PROGRESSIONS = {
    "guerreiro": { "BASE": {"max_hp": 52, "attack": 5, "defense": 4, "initiative": 4, "luck": 3}, "PER_LVL": {"max_hp": 8, "attack": 1, "defense": 2, "initiative": 0, "luck": 0}, "FREE_POINTS_PER_LVL": 1, "mana_stat": "luck" },
    "berserker": { "BASE": {"max_hp": 55, "attack": 6, "defense": 3, "initiative": 5, "luck": 3}, "PER_LVL": {"max_hp": 9, "attack": 2, "defense": 0, "initiative": 1, "luck": 0}, "FREE_POINTS_PER_LVL": 1, "mana_stat": "luck" },
    "cacador": { "BASE": {"max_hp": 48, "attack": 6, "defense": 3, "initiative": 6, "luck": 4}, "PER_LVL": {"max_hp": 6, "attack": 2, "defense": 0, "initiative": 2, "luck": 1}, "FREE_POINTS_PER_LVL": 1, "mana_stat": "initiative" },
    "monge": { "BASE": {"max_hp": 50, "attack": 5, "defense": 4, "initiative": 6, "luck": 3}, "PER_LVL": {"max_hp": 7, "attack": 1, "defense": 2, "initiative": 2, "luck": 0}, "FREE_POINTS_PER_LVL": 1, "mana_stat": "initiative" },
    "mago": { "BASE": {"max_hp": 45, "attack": 7, "defense": 2, "initiative": 5, "luck": 4}, "PER_LVL": {"max_hp": 5, "attack": 3, "defense": 0, "initiative": 1, "luck": 1}, "FREE_POINTS_PER_LVL": 1, "mana_stat": "attack" },
    "bardo": { "BASE": {"max_hp": 47, "attack": 5, "defense": 3, "initiative": 5, "luck": 6}, "PER_LVL": {"max_hp": 6, "attack": 1, "defense": 1, "initiative": 1, "luck": 2}, "FREE_POINTS_PER_LVL": 1, "mana_stat": "luck" },
    "assassino": { "BASE": {"max_hp": 47, "attack": 6, "defense": 2, "initiative": 7, "luck": 5}, "PER_LVL": {"max_hp": 5, "attack": 2, "defense": 0, "initiative": 3, "luck": 1}, "FREE_POINTS_PER_LVL": 1, "mana_stat": "initiative" },
    "samurai": { "BASE": {"max_hp": 50, "attack": 6, "defense": 4, "initiative": 5, "luck": 4}, "PER_LVL": {"max_hp": 7, "attack": 2, "defense": 1, "initiative": 1, "luck": 0}, "FREE_POINTS_PER_LVL": 1, "mana_stat": "defense" },
    "_default": { "BASE": {"max_hp": 50, "attack": 5, "defense": 3, "initiative": 5, "luck": 5}, "PER_LVL": {"max_hp": 7, "attack": 1, "defense": 1, "initiative": 1, "luck": 0}, "FREE_POINTS_PER_LVL": 1, "mana_stat": "luck" },
}

CLASS_POINT_GAINS = {
    "guerreiro": {"max_hp": 4, "attack": 1, "defense": 2, "initiative": 1, "luck": 1},
    "berserker": {"max_hp": 3, "attack": 2, "defense": 1, "initiative": 1, "luck": 1},
    "cacador":   {"max_hp": 3, "attack": 2, "defense": 1, "initiative": 2, "luck": 1},
    "monge":     {"max_hp": 3, "attack": 1, "defense": 2, "initiative": 2, "luck": 1},
    "mago":      {"max_hp": 2, "attack": 3, "defense": 1, "initiative": 1, "luck": 2},
    "bardo":     {"max_hp": 3, "attack": 1, "defense": 1, "initiative": 1, "luck": 2},
    "assassino": {"max_hp": 2, "attack": 2, "defense": 1, "initiative": 3, "luck": 2},
    "samurai":   {"max_hp": 3, "attack": 2, "defense": 2, "initiative": 1, "luck": 1},
    "_default":  {"max_hp": 3, "attack": 1, "defense": 1, "initiative": 1, "luck": 1},
}

_BASELINE_KEYS = ("max_hp", "attack", "defense", "initiative", "luck")

def _ival(x, default=0):
    try: return int(x)
    except Exception: return int(default)

def _get_class_key_normalized(pdata: dict) -> Optional[str]:
    ck = pdata.get("class_key") or pdata.get("class") or pdata.get("classe") or pdata.get("class_type")
    if isinstance(ck, str) and ck.strip():
        return ck.strip().lower()
    return None

async def get_player_total_stats(player_data: dict) -> dict:

    # 1. Calcula os stats base (de classe + nível) - SEMPRE NECESSÁRIO
    lvl = _ival(player_data.get("level"), 1)
    ckey = _get_class_key_normalized(player_data)
    class_baseline = _compute_class_baseline_for_level(ckey, lvl)
    total = {}
    for k in _BASELINE_KEYS:
        total[k] = _ival(class_baseline.get(k))
    for k in _BASELINE_KEYS:
        current_val_in_data = _ival(player_data.get(k)) # Valor no topo do save
        baseline_val = _ival(class_baseline.get(k)) # Valor base já em 'total'

        # Calcula quanto foi investido manualmente (pontos de atributo)
        invested_delta = max(0, current_val_in_data - baseline_val)

        if invested_delta > 0:
             # Adiciona apenas a diferença, pois a base já está lá
             # Precisamos saber quanto cada ponto investido dá (do CLASS_POINT_GAINS)
             gains = _get_point_gains_for_class(ckey)
             gain_per_point = max(1, _ival(gains.get(k)))

             if current_val_in_data > baseline_val:
                  total[k] = current_val_in_data # Usa o valor do save se for maior que a base pura

    inventory = player_data.get('inventory', {}) or {}
    equipped = player_data.get('equipment', {}) or {}

    for slot, unique_id in (equipped.items() if isinstance(equipped, dict) else []):
        if not unique_id: continue
        inst = inventory.get(unique_id)
        if not isinstance(inst, dict): continue
        ench = inst.get('enchantments', {}) or {}
        for stat_key, data in ench.items():
            val = _ival((data or {}).get('value'))
            if stat_key == 'dmg': total['attack'] = total.get('attack', 0) + val # Usa .get() para segurança
            elif stat_key == 'hp': total['max_hp'] = total.get('max_hp', 0) + val
            elif stat_key in ('defense', 'initiative', 'luck') and stat_key in total: total[stat_key] += val

    # 5. Adiciona Buffs de Clã
    clan_id = player_data.get("clan_id")
    if clan_id:
        clan_buffs = clan_manager.get_clan_buffs(clan_id)
        if "all_stats_percent" in clan_buffs:
            percent_bonus = 1 + (clan_buffs["all_stats_percent"] / 100.0)
            total['max_hp'] = int(total.get('max_hp', 0) * percent_bonus)
            total['attack'] = int(total.get('attack', 0) * percent_bonus)
            total['defense'] = int(total.get('defense', 0) * percent_bonus)
        if "flat_hp_bonus" in clan_buffs:
            total['max_hp'] = total.get('max_hp', 0) + clan_buffs["flat_hp_bonus"]

    # 6. Calcula Mana
    class_key = _get_class_key_normalized(player_data) 
    class_prog = CLASS_PROGRESSIONS.get(class_key) or CLASS_PROGRESSIONS["_default"]
    mana_attribute_name = class_prog.get("mana_stat", "luck") 
    # Usa .get() aqui também para segurança
    mana_attribute_value = total.get(mana_attribute_name, 0)
    mana_base = 10
    mana_por_ponto = 5
    total['max_mana'] = mana_base + (mana_attribute_value * mana_por_ponto)        

    # Garante que nenhum stat principal é None ou negativo antes de retornar
    for k in _BASELINE_KEYS:
        total[k] = max(0, _ival(total.get(k))) # Converte None para 0 e garante não-negativo

    return total

async def get_player_dodge_chance(player_data: dict) -> float:
    total_stats = await get_player_total_stats(player_data)
    initiative = total_stats.get('initiative', 0)
    dodge_chance = (initiative * 0.4) / 100.0
    return min(dodge_chance, 0.75)

async def get_player_double_attack_chance(player_data: dict) -> float:
    total_stats = await get_player_total_stats(player_data)
    initiative = total_stats.get('initiative', 0)
    double_attack_chance = (initiative * 0.25) / 100.0
    return min(double_attack_chance, 0.50)

def allowed_points_for_level(pdata: dict) -> int:
    lvl = _ival(pdata.get("level"), 1)
    ckey = _get_class_key_normalized(pdata)
    prog = CLASS_PROGRESSIONS.get(ckey or "") or CLASS_PROGRESSIONS["_default"]
    per_lvl = _ival(prog.get("FREE_POINTS_PER_LVL"), 0)
    return per_lvl * max(0, lvl - 1)

def check_and_apply_level_up(player_data: dict) -> tuple[int, int, str]:
    """Opção A: XP Excedente (Carry-over)"""
    levels_gained, points_gained = 0, 0
    current_xp = int(player_data.get('xp', 0))

    while True:
        current_level = int(player_data.get('level', 1))
        xp_needed = int(game_data.get_xp_for_next_combat_level(current_level))
        
        if xp_needed <= 0 or current_xp < xp_needed:
            break
        
        current_xp -= xp_needed
        
        old_allowed = allowed_points_for_level(player_data)
        player_data['level'] = current_level + 1
        new_allowed = allowed_points_for_level(player_data)
        
        delta_points = max(0, new_allowed - old_allowed)
        
        levels_gained += 1
        points_gained += delta_points

    if levels_gained > 0:
        player_data['xp'] = current_xp
        
        allowed = allowed_points_for_level(player_data)
        spent = compute_spent_status_points(player_data)
        player_data['stat_points'] = max(0, allowed - spent)

    level_up_message = ""
    if levels_gained > 0:
        nivel_txt = "nível" if levels_gained == 1 else "níveis"
        ponto_txt = "ponto" if points_gained == 1 else "pontos"
        level_up_message = (
            f"\n\n✨ <b>Parabéns!</b> Você subiu {levels_gained} {nivel_txt} "
            f"(agora Nv. {player_data['level']}) e ganhou {points_gained} {ponto_txt} de atributo."
        )
        
    return levels_gained, points_gained, level_up_message

def needs_class_choice(player_data: dict) -> bool:
    lvl = _ival(player_data.get("level"), 1)
    already_has_class = bool(player_data.get("class"))
    already_offered = bool(player_data.get("class_choice_offered"))
    return (lvl >= 10) and (not already_has_class) and (not already_offered)

async def mark_class_choice_offered(user_id: int):
    from .core import get_player_data, save_player_data
    pdata = await get_player_data(user_id)
    if not pdata: return
    pdata["class_choice_offered"] = True
    await save_player_data(user_id, pdata)
    
def _get_point_gains_for_class(ckey: Optional[str]) -> dict:
    gains = CLASS_POINT_GAINS.get((ckey or "").lower()) or CLASS_POINT_GAINS["_default"]
    full = {}
    for k in _BASELINE_KEYS:
        full[k] = max(1, _ival(gains.get(k), CLASS_POINT_GAINS["_default"][k]))
    return full

def compute_spent_status_points(pdata: dict) -> int:
    """Calcula quantos pontos de atributo o jogador já gastou manualmente."""
    lvl = _ival(pdata.get("level"), 1)
    ckey = _get_class_key_normalized(pdata)
    
    class_baseline = _compute_class_baseline_for_level(ckey, lvl)
    gains = _get_point_gains_for_class(ckey)
    spent = 0
    
    for k in _BASELINE_KEYS:
        current_stat_value = _ival(pdata.get(k), class_baseline.get(k))
        baseline_stat_value = _ival(class_baseline.get(k))
        
        delta = current_stat_value - baseline_stat_value
        
        if delta <= 0:
            continue
            
        gain_per_point = max(1, int(gains.get(k, 1)))
        
        points_for_this_stat = (delta + gain_per_point - 1) // gain_per_point
        spent += points_for_this_stat
            
    return spent

async def reset_stats_and_refund_points(pdata: dict) -> int:
    _ensure_base_stats_block_inplace(pdata)
    base = pdata["base_stats"]
    spent_before = compute_spent_status_points(pdata)
    for k in _BASELINE_KEYS:
        pdata[k] = _ival(base.get(k))
    pdata["stat_points"] = allowed_points_for_level(pdata)
    if isinstance(pdata.get("invested"), dict):
        pdata["invested"] = {k: 0 for k in _BASELINE_KEYS}
    try:
        totals = await get_player_total_stats(pdata)
        max_hp = _ival(totals.get("max_hp"), pdata.get("max_hp"))
        pdata["current_hp"] = max(1, min(_ival(pdata.get("current_hp"), max_hp), max_hp))
    except Exception: pass
    return spent_before

# <<< CORREÇÃO 12: Adiciona async def >>>
async def _sync_all_stats_inplace(pdata: dict) -> bool:
    """Função mestra que executa todas as sincronizações de stats."""
    mig = _migrate_point_pool_to_stat_points_inplace(pdata) # Síncrono
    base_changed = _ensure_base_stats_block_inplace(pdata) # Síncrono
    cls_sync = await _apply_class_progression_sync_inplace(pdata) 
    
    synced = _sync_stat_points_to_level_cap_inplace(pdata) # Síncrono
    return any([mig, base_changed, cls_sync, synced])

def _migrate_point_pool_to_stat_points_inplace(pdata: dict) -> bool:
    if "point_pool" in pdata:
        add = _ival(pdata.pop("point_pool", 0), 0)
        cur = _ival(pdata.get("stat_points"), 0)
        pdata["stat_points"] = max(0, cur + max(0, add))
        return True
    return False

def _get_default_baseline_from_new_player() -> dict:
    return {"max_hp": 50, "attack": 5, "defense": 3, "initiative": 5, "luck": 5}

def _ensure_base_stats_block_inplace(pdata: dict) -> bool:
    changed = False
    base = pdata.get("base_stats")
    defaults = _get_default_baseline_from_new_player()

    if base is None and isinstance(pdata.get("invested"), dict):
        inv = pdata.get("invested") or {}
        hp_inv   = _ival(inv.get("hp"))
        atk_inv  = _ival(inv.get("attack"))
        def_inv  = _ival(inv.get("defense"))
        ini_inv  = _ival(inv.get("initiative"))
        luck_inv = _ival(inv.get("luck"))
        base = {
            "max_hp":     max(1, _ival(pdata.get("max_hp"), defaults["max_hp"]) - hp_inv),
            "attack":     max(0, _ival(pdata.get("attack"), defaults["attack"]) - atk_inv),
            "defense":    max(0, _ival(pdata.get("defense"), defaults["defense"]) - def_inv),
            "initiative": max(0, _ival(pdata.get("initiative"), defaults["initiative"]) - ini_inv),
            "luck":       max(0, _ival(pdata.get("luck"), defaults["luck"]) - luck_inv),
        }
        pdata["base_stats"] = base
        changed = True

    if not isinstance(pdata.get("base_stats"), dict):
        pdata["base_stats"] = dict(defaults)
        changed = True
    else:
        b = pdata["base_stats"]
        out = {}
        for k in _BASELINE_KEYS:
            out[k] = _ival(b.get(k), defaults[k])
        if out != b:
            pdata["base_stats"] = out
            changed = True
    return changed

def _compute_class_baseline_for_level(class_key: Optional[str], level: int) -> dict:
    lvl = max(1, int(level or 1))
    prog = CLASS_PROGRESSIONS.get((class_key or "").lower()) or CLASS_PROGRESSIONS["_default"]

    base = dict(prog["BASE"])
    per  = dict(prog["PER_LVL"])
    if lvl <= 1:
        return base

    levels_up = lvl - 1
    out = {}
    for k in _BASELINE_KEYS:
        out[k] = _ival(base.get(k)) + _ival(per.get(k)) * levels_up
    return out

def _current_invested_delta_over_baseline(pdata: dict, baseline: dict) -> dict:
    delta = {}
    base_stats = pdata.get("base_stats", {})
    
    for k in _BASELINE_KEYS:
        cur = _ival(base_stats.get(k), baseline.get(k))
        base = _ival(baseline.get(k))
        d = cur - base
        delta[k] = max(0, d)
    return delta

# <<< CORREÇÃO 14: Adiciona async def >>>
async def _apply_class_progression_sync_inplace(pdata: dict) -> bool:
    """VERSÃO CORRIGIDA: Não sobrescreve os stats principais."""
    changed = False
    lvl = _ival(pdata.get("level"), 1)
    ckey = _get_class_key_normalized(pdata)
    class_baseline = _compute_class_baseline_for_level(ckey, lvl) # Síncrono

    current_base_stats = pdata.get("base_stats") or {}
    if any(_ival(current_base_stats.get(k)) != _ival(class_baseline.get(k)) for k in _BASELINE_KEYS):
        pdata["base_stats"] = {k: _ival(class_baseline.get(k)) for k in _BASELINE_KEYS}
        changed = True

    try:
        # <<< CORREÇÃO 15: Adiciona await >>>
        totals = await get_player_total_stats(pdata) # Chama função async
        max_hp = _ival(totals.get("max_hp"), pdata.get("max_hp"))
        cur_hp = _ival(pdata.get("current_hp"), max_hp)
        new_hp = min(max_hp, max(1, cur_hp))
        if new_hp != cur_hp:
            pdata["current_hp"] = new_hp
            changed = True
    except Exception:
        pass

    return changed

def _sync_stat_points_to_level_cap_inplace(pdata: dict) -> bool:
    allowed = allowed_points_for_level(pdata)
    spent = compute_spent_status_points(pdata)
    desired = max(0, allowed - spent)
    cur = max(0, _ival(pdata.get("stat_points"), 0))
    if cur != desired:
        pdata["stat_points"] = desired
        return True
    return False

def has_completed_dungeon(player_data: dict, dungeon_id: str, difficulty: str) -> bool:
    completions = player_data.get("dungeon_completions", {})
    return difficulty in completions.get(dungeon_id, [])

def can_see_evolution_menu(player_data: dict) -> bool:
    current_class = player_data.get("class")
    if not current_class:
        return False

    player_level = player_data.get("level", 1)
    all_options = get_evolution_options(current_class, player_level, show_locked=True)

    if not all_options:
        return False

    for option in all_options:
        if player_level >= option.get("min_level", 999):
            return True
    return False

def mark_dungeon_as_completed(player_data: dict, dungeon_id: str, difficulty: str):
    if "dungeon_completions" not in player_data:
        player_data["dungeon_completions"] = {}
    
    if dungeon_id not in player_data["dungeon_completions"]:
        player_data["dungeon_completions"][dungeon_id] = []
        
    if difficulty not in player_data["dungeon_completions"][dungeon_id]:
        player_data["dungeon_completions"][dungeon_id].append(difficulty)