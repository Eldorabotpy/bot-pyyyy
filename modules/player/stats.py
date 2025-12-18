# modules/player/stats.py 
# (VERSÃO FINAL: Mapeamento completo baseado em attributes.py)

from __future__ import annotations
import logging
from typing import Dict, Optional, Tuple, Any, List
from modules.game_data.skills import SKILL_DATA
# REMOVIDO IMPORT GLOBAL DE PLAYER_MANAGER PARA EVITAR CICLO
from modules import game_data, clan_manager
from modules.game_data.class_evolution import get_evolution_options, get_class_ancestry

try:
    from modules.combat.durability import is_item_broken
except ImportError:
    def is_item_broken(x): return False

logger = logging.getLogger(__name__)

# ========================================
# CONSTANTES DE PROGRESSÃO DE CLASSE
# ========================================
MAGIC_CLASSES = {
    "mago", "arquimago", "feiticeiro", "bruxo", "necromante", 
    "curandeiro", "sacerdote", "clerigo", "druida", "xama",
    "bardo", "mistico", "elementalista"
}

AGILITY_CLASSES = {
    "cacador", "arqueiro", "patrulheiro", 
    "assassino", "ninja", "ladino", 
    "monge"
}

CLASS_PROGRESSIONS = {
    "guerreiro": { "BASE": {"max_hp": 52, "attack": 5, "defense": 4, "initiative": 4, "luck": 3}, "PER_LVL": {"max_hp": 8, "attack": 1, "defense": 2, "initiative": 0, "luck": 0}, "FREE_POINTS_PER_LVL": 1, "mana_stat": "luck" },
    "berserker": { "BASE": {"max_hp": 55, "attack": 6, "defense": 3, "initiative": 5, "luck": 3}, "PER_LVL": {"max_hp": 9, "attack": 2, "defense": 0, "initiative": 1, "luck": 0}, "FREE_POINTS_PER_LVL": 1, "mana_stat": "luck" },
    "cacador": { "BASE": {"max_hp": 48, "attack": 6, "defense": 3, "initiative": 6, "luck": 4}, "PER_LVL": {"max_hp": 6, "attack": 2, "defense": 0, "initiative": 2, "luck": 1}, "FREE_POINTS_PER_LVL": 1, "mana_stat": "initiative" },
    "monge": { "BASE": {"max_hp": 50, "attack": 5, "defense": 4, "initiative": 6, "luck": 3}, "PER_LVL": {"max_hp": 7, "attack": 1, "defense": 2, "initiative": 2, "luck": 0}, "FREE_POINTS_PER_LVL": 1, "mana_stat": "initiative" },
    "mago": { "BASE": {"max_hp": 45, "attack": 7, "defense": 2, "initiative": 5, "luck": 4}, "PER_LVL": {"max_hp": 5, "attack": 3, "defense": 0, "initiative": 1, "luck": 1}, "FREE_POINTS_PER_LVL": 1, "mana_stat": "magic_attack" },
    "bardo": { "BASE": {"max_hp": 47, "attack": 5, "defense": 3, "initiative": 5, "luck": 6}, "PER_LVL": {"max_hp": 6, "attack": 1, "defense": 1, "initiative": 1, "luck": 2}, "FREE_POINTS_PER_LVL": 1, "mana_stat": "luck" },
    "assassino": { "BASE": {"max_hp": 47, "attack": 6, "defense": 2, "initiative": 7, "luck": 5}, "PER_LVL": {"max_hp": 5, "attack": 2, "defense": 0, "initiative": 3, "luck": 1}, "FREE_POINTS_PER_LVL": 1, "mana_stat": "initiative" },
    "samurai": { "BASE": {"max_hp": 50, "attack": 6, "defense": 4, "initiative": 5, "luck": 4}, "PER_LVL": {"max_hp": 7, "attack": 2, "defense": 1, "initiative": 1, "luck": 0}, "FREE_POINTS_PER_LVL": 1, "mana_stat": "defense" },
    "curandeiro": { "BASE": {"max_hp": 48, "attack": 5, "defense": 4, "initiative": 5, "luck": 5}, "PER_LVL": {"max_hp": 6, "attack": 1, "defense": 2, "initiative": 1, "luck": 1}, "FREE_POINTS_PER_LVL": 1, "mana_stat": "luck" },
    "_default": { "BASE": {"max_hp": 50, "attack": 5, "defense": 3, "initiative": 5, "luck": 5}, "PER_LVL": {"max_hp": 7, "attack": 1, "defense": 1, "initiative": 1, "luck": 0}, "FREE_POINTS_PER_LVL": 1, "mana_stat": "luck" },
}

CLASS_POINT_GAINS = {
    "guerreiro": {"max_hp": 4, "defense": 2}, 
    "berserker": {"max_hp": 3, "attack": 2},  
    "cacador":   {"attack": 2, "initiative": 2}, 
    "monge":     {"defense": 2, "initiative": 2}, 
    "mago":      {"max_hp": 2, "attack": 2, "luck": 2}, 
    "bardo":     {"max_hp": 3, "luck": 2}, 
    "assassino": {"attack": 2, "initiative": 2, "luck": 2}, 
    "samurai":   {"attack": 2, "defense": 2},
    "curandeiro":{"max_hp": 4, "defense": 2}, 
    "_default":  {"max_hp": 3, "attack": 1, "defense": 1, "initiative": 1, "luck": 1},
}

_BASELINE_KEYS = ("max_hp", "attack", "defense", "initiative", "luck")

def _ival(x: Any, default: int = 0) -> int:
    try: return int(round(float(x)))
    except: return int(default) if default else 0

def _get_class_key_normalized(pdata: dict) -> Optional[str]:
    current_class = pdata.get("class_key") or pdata.get("class") or pdata.get("classe")
    if not current_class: return "_default"
    try:
        ancestry = get_class_ancestry(current_class)
        if ancestry: return ancestry[-1]
    except: pass
    if current_class.lower() in CLASS_PROGRESSIONS: return current_class.lower()
    return "_default"

def _apply_passive_skill_bonuses(pdata: dict, total_stats: dict):
    player_skills_dict = pdata.get("skills", {})
    if not isinstance(player_skills_dict, dict): return
    for skill_id, skill_info in player_skills_dict.items():
        if not isinstance(skill_info, dict): continue 
        skill_data = SKILL_DATA.get(skill_id)
        if not skill_data or skill_data.get("type") != "passive": continue 
        rarity = skill_info.get("rarity", "comum")
        rarity_effects_data = skill_data.get("rarity_effects", {}).get(rarity)
        if not rarity_effects_data: continue
        effects = rarity_effects_data.get("effects", {})
        if not effects: continue

        stat_bonuses = effects.get("stat_add_mult", {})
        if stat_bonuses:
            for stat, multiplier in stat_bonuses.items():
                if stat in total_stats:
                    bonus_valor = total_stats[stat] * float(multiplier)
                    total_stats[stat] += int(bonus_valor)
                elif stat == "max_mp": 
                    total_stats["max_mana"] = total_stats.get("max_mana", 50) + int(total_stats.get("max_mana", 50) * float(multiplier))
                elif stat == "magic_attack": 
                    if "magic_attack" not in total_stats: total_stats["magic_attack"] = total_stats.get("attack", 0)
                    total_stats["magic_attack"] += int(total_stats.get("magic_attack", 0) * float(multiplier))
                else:
                    total_stats[stat] = total_stats.get(stat, 0.0) + float(multiplier) 

        res_bonuses = effects.get("resistance_mult", {})
        if res_bonuses:
            if "resistance" not in total_stats: total_stats["resistance"] = {}
            for res_type, value in res_bonuses.items():
                total_stats["resistance"][res_type] = total_stats["resistance"].get(res_type, 0.0) + float(value)
        
        if effects.get("crit_immune", False): total_stats["crit_immune"] = True 

        scaling = effects.get("stat_scaling")
        if scaling:
            try:
                source_stat_val = total_stats.get(scaling["source_stat"], 0)
                target_stat = scaling["target_stat"]
                ratio = float(scaling["ratio"])
                bonus = source_stat_val * ratio
                if target_stat in total_stats: total_stats[target_stat] += int(bonus)
                else: total_stats[target_stat] = total_stats.get(target_stat, 0.0) + bonus
            except: pass

def _apply_party_aura_bonuses(ally_data: dict, target_stats: dict):
    ally_skills_dict = ally_data.get("skills", {})
    if not isinstance(ally_skills_dict, dict): return
    for skill_id, skill_info in ally_skills_dict.items():
        if not isinstance(skill_info, dict): continue
        skill_data = SKILL_DATA.get(skill_id)
        if not skill_data or skill_data.get("type") != "passive": continue
        rarity = skill_info.get("rarity", "comum")
        rarity_effects_data = skill_data.get("rarity_effects", {}).get(rarity)
        if not rarity_effects_data: continue
        effects = rarity_effects_data.get("effects", {})
        aura_bonuses = effects.get("party_aura", {})
        if not aura_bonuses: continue 
        stat_bonuses = aura_bonuses.get("stat_add_mult", {})
        if stat_bonuses:
            for stat, multiplier in stat_bonuses.items():
                if stat in target_stats:
                    bonus_valor = target_stats[stat] * float(multiplier)
                    target_stats[stat] += int(bonus_valor)
                else:
                    target_stats[stat] = target_stats.get(stat, 0.0) + float(multiplier)
        if aura_bonuses.get("cannot_be_dodged", False): target_stats["cannot_be_dodged"] = True
        if "hp_regen_percent" in aura_bonuses:
             target_stats["hp_regen_percent"] = target_stats.get("hp_regen_percent", 0.0) + float(aura_bonuses["hp_regen_percent"])
        if "mp_regen_percent" in aura_bonuses:
             target_stats["mp_regen_percent"] = target_stats.get("mp_regen_percent", 0.0) + float(aura_bonuses["mp_regen_percent"])

def _calculate_mana(pdata: dict, total_stats: dict, ckey_fallback: str | None):
    ckey = _get_class_key_normalized(pdata) or ckey_fallback
    class_prog = CLASS_PROGRESSIONS.get(ckey) or CLASS_PROGRESSIONS["_default"]
    mana_attribute_name = class_prog.get("mana_stat", "luck")
    mana_attribute_value = total_stats.get(mana_attribute_name, 0)
    mana_base = 10
    mana_por_ponto = 5
    total_stats['max_mana'] = mana_base + (mana_attribute_value * mana_por_ponto)

# ========================================
# --- FUNÇÃO MESTRA DE STATS (ATUALIZADA) ---
# ========================================

async def get_player_total_stats(player_data: dict, ally_user_ids: List[int] = None) -> dict:
    from modules import player_manager
    from modules.player.premium import PremiumManager 

    lvl = _ival(player_data.get("level"), 1)
    ckey = _get_class_key_normalized(player_data)
    real_class_key = (player_data.get("class_key") or player_data.get("class") or "").lower()

    # 1. Base Stats
    class_baseline = _compute_class_baseline_for_level(ckey, lvl)
    total: Dict[str, Any] = {} 
    for k in _BASELINE_KEYS:
        total[k] = _ival(player_data.get(k, class_baseline.get(k)), class_baseline.get(k, 0))
    total['magic_attack'] = 0

    # 2. Equipamentos (Enchantments)
    inventory = player_data.get('inventory', {}) or {}
    equipped = player_data.get('equipment', {}) or {}
    
    if isinstance(equipped, dict):
        for slot, unique_id in equipped.items():
            if not unique_id: continue
            inst = inventory.get(unique_id)
            if not isinstance(inst, dict): continue
            if is_item_broken(inst): continue 
            ench = inst.get('enchantments', {}) or {}
            
            for stat_key, data in ench.items():
                val = _ival((data or {}).get('value', 0), 0)
                k = stat_key.lower().strip()
                
                # --- CORREÇÃO: MAPEAMENTO COMPLETO (Baseado em attributes.py) ---
                
                # HP / VIDA
                if k in ("hp", "vida", "health", "max_hp", "vitalidade", "vit"): 
                    stat_key = "max_hp"
                
                # DEFESA
                elif k in ("defesa", "defense", "def", "resistencia", "resistance", "res", "armadura", "armor"): 
                    stat_key = "defense"
                
                # INICIATIVA / AGILIDADE
                elif k in ("iniciativa", "initiative", "ini", "agilidade", "agility", "agi", "velocidade", "speed", "spd", "run"): 
                    stat_key = "initiative"
                
                # SORTE
                elif k in ("sorte", "luck", "lucky", "luk"): 
                    stat_key = "luck"

                # ATTACK (Físico/Geral)
                # Inclui: Força (Guerreiro), Fúria (Berserker), Precisão (Caçador), Letalidade (Assassino), Foco (Monge), Bushido (Samurai)
                elif k in ("ataque", "attack", "atk", "dmg", "damage", "fisico", "dano_fisico", 
                           "forca", "strength", "str", 
                           "furia", "fury", 
                           "precisao", "precision", 
                           "letalidade", "lethality", "morte", "death", "execucao", "fatalidade", "perfuracao", 
                           "foco", "focus", 
                           "bushido"): 
                    stat_key = "attack"
                
                # MAGIC ATTACK
                # Inclui: Inteligência (Mago), Carisma (Bardo)
                elif k in ("inteligencia", "intelligence", "int", "magia", "magic", "poder_magico", "dano_magico", "magic_attack", "matk", 
                           "carisma", "charisma"): 
                    stat_key = "magic_attack"
                    
                # CRIT (Se houver separado)
                elif k in ("crit", "critico", "mira"): 
                    stat_key = "crit_chance_flat"

                # --- SOMA NO TOTAL ---
                if stat_key == 'max_hp': 
                    total['max_hp'] = total.get('max_hp', 0) + val
                elif stat_key == 'magic_attack': 
                    total['magic_attack'] = total.get('magic_attack', 0) + val
                elif stat_key in ('attack', 'defense', 'initiative', 'luck'): 
                    total[stat_key] = total.get(stat_key, 0) + val
                else:
                    if stat_key not in _BASELINE_KEYS: 
                        total[stat_key] = total.get(stat_key, 0) + val

    # 3. Clã Buffs
    clan_id = player_data.get("clan_id")
    if clan_id:
        try:
            clan_buffs = clan_manager.get_clan_buffs(clan_id) or {}
            if "all_stats_percent" in clan_buffs:
                percent_bonus = 1 + (float(clan_buffs.get("all_stats_percent", 0)) / 100.0)
                for st in ['max_hp', 'attack', 'defense']:
                     total[st] = int(total.get(st, 0) * percent_bonus)

            if "flat_hp_bonus" in clan_buffs:
                total['max_hp'] = total.get('max_hp', 0) + int(clan_buffs.get("flat_hp_bonus", 0))
        except: pass

    # 4. Premium
    try:
        premium = PremiumManager(player_data)
        if premium.is_premium():
            vip_percent = float(premium.get_perk_value("all_stats_percent", 0))
            if vip_percent > 0:
                mult_vip = 1 + (vip_percent / 100.0)
                stats_affected = ['max_hp', 'attack', 'defense', 'initiative', 'luck', 'magic_attack']
                for st in stats_affected:
                    current_val = total.get(st, 0)
                    total[st] = int(current_val * mult_vip)
            
            vip_luck = int(premium.get_perk_value("bonus_luck", 0))
            if vip_luck > 0:
                total['luck'] = total.get('luck', 0) + vip_luck

    except Exception as e:
        logger.error(f"Erro ao calcular stats Premium: {e}")

    # 5. Passivas e Auras
    try:
        _apply_passive_skill_bonuses(player_data, total)
        if ally_user_ids:
            for ally_id in ally_user_ids:
                if ally_id == player_data.get("user_id"): continue
                ally_data = await player_manager.get_player_data(ally_id)
                if ally_data: _apply_party_aura_bonuses(ally_data, total)
    except: pass

    # 6. Runas
    try:
        rune_bonuses = player_manager.get_rune_bonuses(player_data)
        for stat, value in rune_bonuses.items():
            if stat == "magic_attack": 
                total["magic_attack"] = total.get("magic_attack", 0) + int(value)
            elif stat in total:
                total[stat] += value
            else:
                total[stat] = total.get(stat, 0) + value
    except Exception as e:
        logger.error(f"Erro ao calcular bônus de runas: {e}")

    # 7. Unificação de Dano (Mágico vs Físico)
    base_attack = total.get('attack', 0)
    magic_bonus = total.get('magic_attack', 0)
    is_magic = real_class_key in MAGIC_CLASSES
    if not is_magic:
        ancestry = get_class_ancestry(real_class_key)
        if any(c in MAGIC_CLASSES for c in ancestry): is_magic = True
    if is_magic:
        total['attack'] = base_attack + magic_bonus
        total['magic_attack'] = total['attack']

    is_agility = real_class_key in AGILITY_CLASSES
    if not is_agility:
         ancestry = get_class_ancestry(real_class_key)
         if any(c in AGILITY_CLASSES for c in ancestry): is_agility = True
    if is_agility:
        ini_bonus = int(total.get('initiative', 0) * 0.25)
        total['attack'] += ini_bonus

    # 8. MANA CALCULATION
    _calculate_mana(player_data, total, ckey_fallback=ckey)

    # 9. Sanitização
    for k in _BASELINE_KEYS:
        total[k] = max(0, _ival(total.get(k), 0))
    total['max_mana'] = max(0, _ival(total.get('max_mana', 10)))
    
    return total

async def get_player_dodge_chance(player_data: dict, ally_user_ids: List[int] = None) -> float:
    total_stats = await get_player_total_stats(player_data, ally_user_ids)
    initiative = total_stats.get('initiative', 0)
    dodge_chance = (initiative * 0.4) / 100.0
    dodge_chance += total_stats.get('dodge_chance_flat', 0)
    if total_stats.get("cannot_be_dodged", False): return 0.0 
    return min(dodge_chance, 0.75) 

async def get_player_double_attack_chance(player_data: dict, ally_user_ids: List[int] = None) -> float:
    total_stats = await get_player_total_stats(player_data, ally_user_ids)
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
    levels_gained, points_gained = 0, 0
    current_xp = int(player_data.get('xp', 0))
    ckey = _get_class_key_normalized(player_data)

    while True:
        current_level = int(player_data.get('level', 1))
        xp_needed = int(game_data.get_xp_for_next_combat_level(current_level))
        if xp_needed <= 0 or current_xp < xp_needed: break
        current_xp -= xp_needed

        old_baseline = _compute_class_baseline_for_level(ckey, current_level)
        new_baseline = _compute_class_baseline_for_level(ckey, current_level + 1)

        for k in _BASELINE_KEYS:
            stat_increase = new_baseline.get(k, 0) - old_baseline.get(k, 0)
            if stat_increase > 0:
                current_val = int(player_data.get(k, old_baseline.get(k, 0)))
                player_data[k] = current_val + stat_increase
                if k == "max_hp":
                    current_hp = int(player_data.get("current_hp", current_val))
                    player_data["current_hp"] = current_hp + stat_increase

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
    return (lvl >= 5) and (not already_has_class) and (not already_offered)

async def mark_class_choice_offered(user_id: int):
    from .core import get_player_data, save_player_data
    pdata = await get_player_data(user_id)
    if not pdata: return
    pdata["class_choice_offered"] = True
    await save_player_data(user_id, pdata)

def _get_point_gains_for_class(ckey: Optional[str]) -> dict:
    norm_key = (ckey or "").lower()
    gains = CLASS_POINT_GAINS.get(norm_key)
    if gains is None:
        try:
            ancestry = get_class_ancestry(norm_key)
            if ancestry:
                base_class = ancestry[-1]
                gains = CLASS_POINT_GAINS.get(base_class.lower())
        except: pass
    if gains is None: gains = CLASS_POINT_GAINS.get(norm_key, CLASS_POINT_GAINS["_default"])
    full: Dict[str, int] = {}
    for k in _BASELINE_KEYS:
        full[k] = max(1, _ival(gains.get(k), CLASS_POINT_GAINS["_default"].get(k, 1)))
    return full

def compute_spent_status_points(pdata: dict) -> int:
    lvl = _ival(pdata.get("level"), 1)
    ckey = _get_class_key_normalized(pdata)
    class_baseline = _compute_class_baseline_for_level(ckey, lvl)
    gains = _get_point_gains_for_class(ckey)
    spent = 0
    for k in _BASELINE_KEYS:
        current_stat_value = _ival(pdata.get(k), class_baseline.get(k))
        baseline_stat_value = _ival(class_baseline.get(k))
        delta = current_stat_value - baseline_stat_value
        if delta <= 0: continue 
        gain_per_point = max(1, int(gains.get(k, 1)))
        points_for_this_stat = (delta + gain_per_point - 1) // gain_per_point
        spent += points_for_this_stat
    return spent

async def reset_stats_and_refund_points(pdata: dict) -> int:
    _ensure_base_stats_block_inplace(pdata)
    lvl = _ival(pdata.get("level"), 1)
    ckey = _get_class_key_normalized(pdata)
    class_baseline = _compute_class_baseline_for_level(ckey, lvl)
    spent_before = compute_spent_status_points(pdata)
    for k in _BASELINE_KEYS:
        pdata[k] = _ival(class_baseline.get(k))
    pdata["stat_points"] = allowed_points_for_level(pdata) 
    if isinstance(pdata.get("invested"), dict): pdata["invested"] = {k: 0 for k in _BASELINE_KEYS}
    try:
        totals = await get_player_total_stats(pdata)
        max_hp = _ival(totals.get("max_hp"), pdata.get("max_hp"))
        pdata["current_hp"] = max(1, max_hp)
    except: pass
    return spent_before

async def _sync_all_stats_inplace(pdata: dict) -> bool:
    mig = _migrate_point_pool_to_stat_points_inplace(pdata)
    base_changed = _ensure_base_stats_block_inplace(pdata)
    cls_sync = await _apply_class_progression_sync_inplace(pdata)
    synced = _sync_stat_points_to_level_cap_inplace(pdata)
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
        base = {
            "max_hp":     max(1, _ival(pdata.get("max_hp"), defaults["max_hp"]) - _ival(inv.get("hp"))),
            "attack":     max(0, _ival(pdata.get("attack"), defaults["attack"]) - _ival(inv.get("attack"))),
            "defense":    max(0, _ival(pdata.get("defense"), defaults["defense"]) - _ival(inv.get("defense"))),
            "initiative": max(0, _ival(pdata.get("initiative"), defaults["initiative"]) - _ival(inv.get("initiative"))),
            "luck":       max(0, _ival(pdata.get("luck"), defaults["luck"]) - _ival(inv.get("luck"))),
        }
        pdata["base_stats"] = base
        changed = True
    if not isinstance(pdata.get("base_stats"), dict):
        pdata["base_stats"] = dict(defaults); changed = True
    else:
        b = pdata["base_stats"]
        out = {k: _ival(b.get(k), defaults[k]) for k in _BASELINE_KEYS}
        if out != b: pdata["base_stats"] = out; changed = True
    return changed

def _compute_class_baseline_for_level(class_key: Optional[str], level: int) -> dict:
    lvl = max(1, int(level or 1))
    prog = CLASS_PROGRESSIONS.get((class_key or "").lower()) or CLASS_PROGRESSIONS["_default"]
    base = dict(prog["BASE"])
    per = dict(prog["PER_LVL"])
    if lvl <= 1: return base
    levels_up = lvl - 1
    out: Dict[str, int] = {}
    for k in _BASELINE_KEYS:
        out[k] = _ival(base.get(k)) + _ival(per.get(k)) * levels_up
    return out

def _current_invested_delta_over_baseline(pdata: dict, baseline: dict) -> dict:
    delta: Dict[str, int] = {}
    for k in _BASELINE_KEYS:
        cur = _ival(pdata.get(k), baseline.get(k))
        base = _ival(baseline.get(k))
        delta[k] = max(0, cur - base)
    return delta

async def _apply_class_progression_sync_inplace(pdata: dict) -> bool:
    changed = False
    lvl = _ival(pdata.get("level"), 1)
    ckey = _get_class_key_normalized(pdata)
    class_baseline = _compute_class_baseline_for_level(ckey, lvl)
    current_base_stats = pdata.get("base_stats") or {}
    if any(_ival(current_base_stats.get(k)) != _ival(class_baseline.get(k)) for k in _BASELINE_KEYS):
        pdata["base_stats"] = {k: _ival(class_baseline.get(k)) for k in _BASELINE_KEYS}
        changed = True
    try:
        totals = await get_player_total_stats(pdata, None)
        max_hp = _ival(totals.get("max_hp"), pdata.get("max_hp"))
        cur_hp = _ival(pdata.get("current_hp"), max_hp)
        new_hp = min(max_hp, max(1, cur_hp))
        if new_hp != cur_hp: pdata["current_hp"] = new_hp; changed = True
        max_mp = _ival(totals.get("max_mana"), 10)
        cur_mp = _ival(pdata.get("current_mp"), max_mp)
        new_mp = min(max_mp, max(0, cur_mp))
        if new_mp != cur_mp or "current_mp" not in pdata: pdata["current_mp"] = new_mp; changed = True
    except: pass
    return changed

def _sync_stat_points_to_level_cap_inplace(pdata: dict) -> bool:
    allowed = allowed_points_for_level(pdata)
    spent = compute_spent_status_points(pdata)
    desired = max(0, allowed - spent)
    cur = max(0, _ival(pdata.get("stat_points"), 0))
    if cur != desired: pdata["stat_points"] = desired; return True
    return False

def has_completed_dungeon(player_data: dict, dungeon_id: str, difficulty: str) -> bool:
    completions = player_data.get("dungeon_completions", {})
    return difficulty in completions.get(dungeon_id, [])

def can_see_evolution_menu(player_data: dict) -> bool:
    current_class = player_data.get("class")
    if not current_class: return False
    player_level = player_data.get("level", 1)
    all_options = get_evolution_options(current_class, player_level, show_locked=True)
    return bool(all_options)

def mark_dungeon_as_completed(player_data: dict, dungeon_id: str, difficulty: str):
    if "dungeon_completions" not in player_data: player_data["dungeon_completions"] = {}
    if dungeon_id not in player_data["dungeon_completions"]: player_data["dungeon_completions"][dungeon_id] = []
    if difficulty not in player_data["dungeon_completions"][dungeon_id]: player_data["dungeon_completions"][dungeon_id].append(difficulty)

async def apply_class_change_and_recalculate(player_data: dict, new_class_key: str):
    lvl = _ival(player_data.get("level"), 1)
    old_ckey = _get_class_key_normalized(player_data)
    old_baseline = _compute_class_baseline_for_level(old_ckey, lvl)
    invested_diffs = {}
    for k in _BASELINE_KEYS:
        current_val = _ival(player_data.get(k, old_baseline.get(k)))
        base_val = _ival(old_baseline.get(k))
        invested_diffs[k] = max(0, current_val - base_val)
    player_data["class"] = new_class_key
    player_data["class_key"] = new_class_key
    if "class_tag" in player_data: del player_data["class_tag"]
    new_ckey = _get_class_key_normalized(player_data)
    new_baseline = _compute_class_baseline_for_level(new_ckey, lvl)
    for k in _BASELINE_KEYS:
        new_base = _ival(new_baseline.get(k))
        saved_investment = invested_diffs.get(k, 0)
        player_data[k] = new_base + saved_investment
    totals = await get_player_total_stats(player_data)
    player_data["current_hp"] = _ival(totals.get("max_hp"))
    player_data["current_mp"] = _ival(totals.get("max_mana"))
    player_data["class_choice_offered"] = True
    return player_data