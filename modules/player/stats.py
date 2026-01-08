# modules/player/stats.py
# (VERSÃO DEFINITIVA: Balanceamento Ativo + Correção de Mago)

from __future__ import annotations
import logging
from typing import Dict, Optional, Tuple, Any, List, Union

# --- IMPORTS ---
from modules.game_data.skills import SKILL_DATA
from modules.game_data.classes import CLASSES_DATA, get_stat_modifiers
from modules import game_data, clan_manager
from modules.game_data.class_evolution import get_evolution_options, get_class_ancestry

# Tenta importar o módulo de balanceamento
try:
    from modules import balance
except ImportError:
    balance = None  # Fallback se o arquivo não existir

try:
    from modules.combat.durability import is_item_broken
except ImportError:
    def is_item_broken(x): return False

logger = logging.getLogger(__name__)

# ========================================
# 1. CONSTANTES E LISTAS DE CLASSES
# ========================================

MAGIC_CLASSES = {
    "mago", "arquimago", "feiticeiro", "bruxo", "necromante", 
    "curandeiro", "sacerdote", "clerigo", "druida", "xama",
    "bardo", "mistico", "elementalista", "hierofante", "oraculo_celestial"
}

AGILITY_CLASSES = {
    "cacador", "arqueiro", "patrulheiro", "franco_atirador",
    "assassino", "ninja", "ladino", "ladrao", "ladrao_de_sombras", "ceifador",
    "monge", "samurai", "ronin", "kenshi", "mestre_das_laminas"
}

# TABELA DE PROGRESSÃO (STATUS BASE)
CLASS_PROGRESSIONS = {
    "guerreiro":   { "BASE": {"max_hp": 60, "attack": 6, "defense": 5, "initiative": 4, "luck": 3}, "PER_LVL": {"max_hp": 8, "attack": 2, "defense": 2, "initiative": 0, "luck": 0}, "mana_stat": "luck" },
    "berserker":   { "BASE": {"max_hp": 65, "attack": 8, "defense": 3, "initiative": 5, "luck": 3}, "PER_LVL": {"max_hp": 9, "attack": 3, "defense": 0, "initiative": 1, "luck": 0}, "mana_stat": "luck" },
    "cacador":     { "BASE": {"max_hp": 50, "attack": 7, "defense": 3, "initiative": 7, "luck": 4}, "PER_LVL": {"max_hp": 6, "attack": 2, "defense": 1, "initiative": 2, "luck": 1}, "mana_stat": "initiative" },
    "monge":       { "BASE": {"max_hp": 55, "attack": 6, "defense": 4, "initiative": 6, "luck": 3}, "PER_LVL": {"max_hp": 7, "attack": 2, "defense": 2, "initiative": 2, "luck": 0}, "mana_stat": "initiative" },
    "mago":        { "BASE": {"max_hp": 45, "attack": 8, "defense": 2, "initiative": 5, "luck": 4}, "PER_LVL": {"max_hp": 5, "attack": 4, "defense": 0, "initiative": 1, "luck": 1}, "mana_stat": "magic_attack" },
    "bardo":       { "BASE": {"max_hp": 48, "attack": 5, "defense": 3, "initiative": 5, "luck": 7}, "PER_LVL": {"max_hp": 6, "attack": 1, "defense": 1, "initiative": 1, "luck": 3}, "mana_stat": "luck" },
    "assassino":   { "BASE": {"max_hp": 48, "attack": 8, "defense": 2, "initiative": 8, "luck": 5}, "PER_LVL": {"max_hp": 5, "attack": 3, "defense": 0, "initiative": 3, "luck": 1}, "mana_stat": "initiative" },
    "samurai":     { "BASE": {"max_hp": 55, "attack": 7, "defense": 4, "initiative": 6, "luck": 4}, "PER_LVL": {"max_hp": 7, "attack": 3, "defense": 1, "initiative": 2, "luck": 0}, "mana_stat": "defense" },
    "curandeiro":  { "BASE": {"max_hp": 50, "attack": 4, "defense": 4, "initiative": 5, "luck": 5}, "PER_LVL": {"max_hp": 6, "attack": 1, "defense": 2, "initiative": 1, "luck": 2}, "mana_stat": "luck" },
    
    "_default":    { "BASE": {"max_hp": 50, "attack": 5, "defense": 3, "initiative": 5, "luck": 5}, "PER_LVL": {"max_hp": 7, "attack": 1, "defense": 1, "initiative": 1, "luck": 1}, "mana_stat": "luck" },
}

# Usado apenas para referência visual no menu (se balance.py estiver ativo, o ganho real varia)
CLASS_POINT_GAINS = {
    "_default":  {"max_hp": 3, "attack": 1, "defense": 1, "initiative": 1, "luck": 1},
    "guerreiro": {"max_hp": 4, "defense": 2}, 
    "berserker": {"max_hp": 3, "attack": 2},  
    "cacador":   {"attack": 2, "initiative": 2}, 
    "monge":     {"defense": 2, "initiative": 2}, 
    "mago":      {"max_hp": 2, "attack": 2, "luck": 2}, 
    "bardo":     {"max_hp": 3, "luck": 2}, 
    "assassino": {"attack": 2, "initiative": 2, "luck": 2}, 
    "samurai":   {"attack": 2, "defense": 2},
    "curandeiro":{"max_hp": 4, "defense": 2}, 
}

PROFILE_KEYS = ("max_hp", "attack", "defense", "initiative", "luck", "magic_attack")
_BASELINE_KEYS = ("max_hp", "attack", "defense", "initiative", "luck")

# ========================================
# 2. HELPER FUNCTIONS
# ========================================

def _ival(x: Any, default: int = 0) -> int:
    try: return int(round(float(x)))
    except: return int(default) if default else 0

def _get_class_key_normalized(pdata: dict) -> str:
    raw_class = pdata.get("class_key") or pdata.get("class") or pdata.get("classe")
    if not raw_class: return "_default"
    
    norm = str(raw_class).strip().lower().replace("_", " ") 
    raw_clean = str(raw_class).strip().lower()
    
    if raw_clean in CLASS_PROGRESSIONS: return raw_clean
    if norm in CLASS_PROGRESSIONS: return norm

    aliases = {
        "ladrao de sombras": "assassino", "ninja": "assassino",
        "cavaleiro": "guerreiro", "templario": "guerreiro",
        "barbaro": "berserker", "selvagem": "berserker",
        "patrulheiro": "cacador", "franco atirador": "cacador",
        "arquimago": "mago", "feiticeiro": "mago",
        "clerigo": "curandeiro", "sacerdote": "curandeiro",
        "ronin": "samurai", "kenshi": "samurai",
        "menestrel": "bardo", "trovador": "bardo"
    }
    if norm in aliases: return aliases[norm]

    try:
        ancestry = get_class_ancestry(raw_clean)
        for ancestor in ancestry:
            if ancestor.lower() in CLASS_PROGRESSIONS:
                return ancestor.lower()
    except Exception:
        pass
    
    return "_default"

def _map_stat_name(raw_key: str) -> str | None:
    if not raw_key: return None
    k = str(raw_key).lower().strip().replace("_", "").replace(" ", "")
    if k in ("ataque", "attack", "atk", "str", "forca", "strength", "dano", "fisico", "furia", "bushido", "foco", "precisao", "letalidade", "physatk"): return "attack"
    if k in ("inteligencia", "int", "matk", "magia", "magic", "magicattack", "fe", "faith", "carisma", "charisma", "arcano"): return "magic_attack"
    if k in ("defesa", "defense", "def", "armadura", "armor", "resistencia", "res", "vitality"): return "defense"
    if k in ("hp", "vida", "health", "maxhp", "vitalidade", "vit", "hpmax", "points_hp"): return "max_hp"
    if k in ("iniciativa", "initiative", "agi", "agilidade", "velocidade", "speed", "dex", "destreza"): return "initiative"
    if k in ("sorte", "luck", "luk", "critico", "crt", "chance"): return "luck"
    return None

# ========================================
# 3. CÁLCULO TOTAL DE STATUS (CORE ENGINE)
# ========================================

async def get_player_total_stats(player_data: dict, ally_user_ids: list = None) -> dict:
    from modules import player_manager
    from modules.player.premium import PremiumManager 

    lvl = _ival(player_data.get("level"), 1)
    # ckey: Classe Base (usada para Stats Base de Progressão)
    ckey = _get_class_key_normalized(player_data)
    # real_class_key: Classe Real/Evoluída (usada para Balanceamento e Modificadores)
    real_class_key = (player_data.get("class_key") or player_data.get("class") or "").lower()
    
    # ----------------------------------------------------
    # PASSO 1: BASE DA CLASSE (FIXO DA TABELA)
    # ----------------------------------------------------
    class_baseline = _compute_class_baseline_for_level(ckey, lvl)
    total: Dict[str, Any] = {} 
    
    for k in _BASELINE_KEYS:
        total[k] = class_baseline.get(k, 0)
    total['magic_attack'] = class_baseline.get('magic_attack', 0)

    # ----------------------------------------------------
    # PASSO 2: ESCALONAMENTO DE EVOLUÇÃO (BASE)
    # Aplica multiplicadores de classe na BASE para refletir a evolução (ex: Guerreiro -> Templário)
    # ----------------------------------------------------
    if real_class_key and real_class_key != ckey and real_class_key != "_default":
        current_mods = get_stat_modifiers(real_class_key)
        base_mods = get_stat_modifiers(ckey)
        
        if current_mods and base_mods:
            for stat_k in list(total.keys()):
                mod_k = "hp" if stat_k == "max_hp" else stat_k
                if stat_k == "magic_attack": mod_k = "inteligencia"

                mod_curr = float(current_mods.get(mod_k, 1.0))
                # Fallback Mago: Se não tiver inteligencia, usa attack
                if stat_k == "magic_attack" and mod_curr == 1.0:
                    mod_curr = float(current_mods.get("attack", 1.0))

                mod_base = float(base_mods.get(mod_k, 1.0))
                if stat_k == "magic_attack" and mod_base == 1.0:
                    mod_base = float(base_mods.get("attack", 1.0))

                if mod_base > 0:
                    ratio = mod_curr / mod_base
                    total[stat_k] = int(total[stat_k] * ratio)

    # ----------------------------------------------------
    # PASSO 3: PONTOS INVESTIDOS (COM BALANCE.PY)
    # ----------------------------------------------------
    invested_clicks = player_data.get("invested", {})
    if not isinstance(invested_clicks, dict): invested_clicks = {}

    if balance:
        # Modo Avançado: Usa Softcaps, DR e Afinidade
        for k, clicks in invested_clicks.items():
            n_clicks = _ival(clicks, 0)
            if n_clicks <= 0: continue

            # Mapeia chaves do stats.py para o balance.py (max_hp -> hp)
            target_key = _map_stat_name(k) or k
            balance_key = "hp" if target_key == "max_hp" else target_key
            
            # Se for magic_attack, calculamos usando a curva de attack 
            # (assumindo que Mago tem afinidade alta em Attack no classes.py para compensar)
            if target_key == "magic_attack": balance_key = "attack"

            # Se a chave não existir no balance (ex: desconhecida), ignora ou trata linear
            if balance_key not in balance.STAT_RULES:
                # Fallback Linear
                gains = _get_point_gains_for_class(ckey)
                gain_per_click = gains.get(target_key, 1)
                if target_key not in total: total[target_key] = 0
                total[target_key] += (n_clicks * gain_per_click)
            else:
                # Cálculo da Curva (Balance)
                added_val = balance.effect_from_points(balance_key, n_clicks, real_class_key)
                
                if target_key not in total: total[target_key] = 0
                total[target_key] += int(added_val)

    else:
        # Modo Legado: Linear (se balance.py não existir)
        gains = _get_point_gains_for_class(ckey)
        for k, clicks in invested_clicks.items():
            target_key = _map_stat_name(k) or k
            if target_key == "magic_attack":
                gain = gains.get("magic_attack", gains.get("attack", 1))
                total["magic_attack"] += (_ival(clicks, 0) * gain)
            elif target_key in total or target_key in _BASELINE_KEYS:
                if target_key not in total: total[target_key] = 0
                gain_per_click = gains.get(target_key, 1)
                total[target_key] += (_ival(clicks, 0) * gain_per_click)

    # ----------------------------------------------------
    # PASSO 4: EQUIPAMENTOS
    # ----------------------------------------------------
    inventory = player_data.get('inventory', {}) or {}
    equipped = player_data.get('equipment', {}) or {}
    
    if isinstance(equipped, dict):
        for slot, unique_id in equipped.items():
            if not unique_id: continue
            inst = inventory.get(unique_id)
            if not isinstance(inst, dict) or is_item_broken(inst): continue 
            
            def add_item_stat(r_stat, r_val):
                v = _ival(r_val, 0)
                if v <= 0: return
                s_key = _map_stat_name(r_stat)
                if s_key:
                    if s_key not in total: total[s_key] = 0
                    total[s_key] += v
                elif s_key == "magic_attack" or r_stat in ("inteligencia", "magic"):
                    total["magic_attack"] += v

            base_stats = inst.get('stats') or inst.get('attributes') or {}
            for k, v in base_stats.items(): add_item_stat(k, v)

            ench = inst.get('enchantments', {}) or {}
            for k, data in ench.items(): add_item_stat(k, (data or {}).get('value', 0))

    # ----------------------------------------------------
    # PASSO 5: BÔNUS EXTERNOS (CLÃ, PREMIUM, BUFFS)
    # ----------------------------------------------------
    clan_id = player_data.get("clan_id")
    if clan_id:
        try:
            clan_buffs = clan_manager.get_clan_buffs(clan_id) or {}
            if "all_stats_percent" in clan_buffs:
                percent_bonus = 1 + (float(clan_buffs.get("all_stats_percent", 0)) / 100.0)
                for st in ['max_hp', 'attack', 'defense', 'magic_attack']: 
                     if st in total: total[st] = int(total.get(st, 0) * percent_bonus)
            if "flat_hp_bonus" in clan_buffs:
                total['max_hp'] += int(clan_buffs.get("flat_hp_bonus", 0))
        except: pass

    try:
        premium = PremiumManager(player_data)
        if premium.is_premium():
            vip_percent = float(premium.get_perk_value("all_stats_percent", 0))
            if vip_percent > 0:
                mult_vip = 1 + (vip_percent / 100.0)
                for st in ['max_hp', 'attack', 'defense', 'initiative', 'luck', 'magic_attack']:
                    if st in total: total[st] = int(total.get(st, 0) * mult_vip)
            vip_luck = int(premium.get_perk_value("bonus_luck", 0))
            if vip_luck > 0: total['luck'] += vip_luck
    except: pass

    try:
        _apply_passive_skill_bonuses(player_data, total)
        if ally_user_ids:
            my_id_str = str(player_data.get("user_id") or player_data.get("_id") or "")
            for ally_id in ally_user_ids:
                if str(ally_id) == my_id_str: continue
                ally_data = await player_manager.get_player_data(ally_id)
                if ally_data: _apply_party_aura_bonuses(ally_data, total)
        
        rune_bonuses = player_manager.get_rune_bonuses(player_data)
        for stat, value in rune_bonuses.items():
            k_rune = _map_stat_name(stat) or stat
            if k_rune in total: total[k_rune] += int(value)
            elif k_rune == "magic_attack": total["magic_attack"] += int(value)
    except: pass

    # ----------------------------------------------------
    # PASSO 6: CORREÇÕES ESPECÍFICAS DE CLASSE (Mago/Ladino)
    # ----------------------------------------------------
    
    # Verifica se é classe mágica
    is_magic = False
    if real_class_key in MAGIC_CLASSES: is_magic = True
    else:
        try:
            ancestry = get_class_ancestry(real_class_key)
            if any(c in MAGIC_CLASSES for c in ancestry): is_magic = True
        except: pass

    # === CORREÇÃO: MAGO CONVERTE ATAQUE EM MAGIA ===
    if is_magic:
        raw_attack = total.get("attack", 0)
        # Se magic_attack for menor que attack (ou zero), herda o valor
        if total.get("magic_attack", 0) < raw_attack:
             total["magic_attack"] = raw_attack
        
        # Opcional: Se quiser que Mago tenha ataque físico fraco, descomente:
        # total["attack"] = int(total["attack"] * 0.3) 

    # Bônus de Agilidade para classes de Destreza
    is_agility = False
    if real_class_key in AGILITY_CLASSES: is_agility = True
    else:
        try:
            ancestry = get_class_ancestry(real_class_key)
            if any(c in AGILITY_CLASSES for c in ancestry): is_agility = True
        except: pass

    if is_agility:
        ini_bonus = int(total.get('initiative', 0) * 0.15)
        total['attack'] += ini_bonus
    
    # Recalcula Mana com base no novo total (magic_attack agora estará preenchido)
    _calculate_mana(player_data, total, ckey_fallback=ckey)
    
    # Sanitização final
    for k in total:
        if k != "resistance": 
             total[k] = max(0, _ival(total.get(k), 0))
    
    total['max_hp'] = max(1, total.get('max_hp', 1))
    total['max_mana'] = max(10, total.get('max_mana', 10))
    
    return total

async def get_player_dodge_chance(player_data: dict, ally_user_ids: list = None) -> float:
    total_stats = await get_player_total_stats(player_data, ally_user_ids)
    initiative = total_stats.get('initiative', 0)
    dodge_chance = (initiative * 0.4) / 100.0
    dodge_chance += total_stats.get('dodge_chance_flat', 0)
    if total_stats.get("cannot_be_dodged", False): return 0.0 
    return min(dodge_chance, 0.75)

async def get_player_double_attack_chance(player_data: dict, ally_user_ids: list = None) -> float:
    total_stats = await get_player_total_stats(player_data, ally_user_ids)
    initiative = total_stats.get('initiative', 0)
    double_attack_chance = (initiative * 0.25) / 100.0
    return min(double_attack_chance, 0.50)

# ========================================
# 4. FUNÇÕES DE SUPORTE
# ========================================

def _calculate_mana(pdata: dict, total_stats: dict, ckey_fallback: str | None):
    ckey = _get_class_key_normalized(pdata) or ckey_fallback
    prog = CLASS_PROGRESSIONS.get(ckey) or CLASS_PROGRESSIONS["_default"]
    mana_stat = prog.get("mana_stat", "luck")
    
    # Se for magic_attack, agora o sistema encontrará o valor correto
    if mana_stat == "magic_attack":
        mana_val = total_stats.get("magic_attack", 0)
        multiplier = 3
    else:
        mana_val = total_stats.get(mana_stat, 0)
        multiplier = 5
        
    total_stats['max_mana'] = 20 + (mana_val * multiplier)

def allowed_points_for_level(pdata: dict) -> int:
    lvl = _ival(pdata.get("level"), 1)
    return max(0, lvl - 1)

async def reset_stats_and_refund_points(pdata: dict) -> int:
    lvl = _ival(pdata.get("level"), 1)
    ckey = _get_class_key_normalized(pdata)
    
    class_baseline = _compute_class_baseline_for_level(ckey, lvl)
    
    for k in _BASELINE_KEYS:
        pdata[k] = class_baseline.get(k, 0)
    pdata["base_stats"] = class_baseline.copy()

    should_have_points = allowed_points_for_level(pdata)
    pdata["stat_points"] = should_have_points
    pdata["invested"] = {}
    
    pdata["current_hp"] = max(1, pdata.get("max_hp", 100))
    pdata["current_mp"] = max(10, pdata.get("max_mana", 10))

    return should_have_points

def _compute_class_baseline_for_level(class_key: str, level: int) -> dict:
    lvl = max(1, int(level or 1))
    ckey = (class_key or "").lower()
    
    prog = CLASS_PROGRESSIONS.get(ckey)
    if not prog:
        try:
            ancestry = get_class_ancestry(ckey) 
            if ancestry:
                for ancestor in reversed(ancestry):
                    if ancestor.lower() in CLASS_PROGRESSIONS:
                        prog = CLASS_PROGRESSIONS[ancestor.lower()]
                        break
        except: pass
        
    if not prog: prog = CLASS_PROGRESSIONS["_default"]
    
    base = dict(prog["BASE"])
    per = dict(prog["PER_LVL"])
    
    levels_up = lvl - 1
    out: Dict[str, int] = {}
    for k in _BASELINE_KEYS:
        out[k] = _ival(base.get(k)) + (_ival(per.get(k)) * levels_up)
    return out

# ... [MANTENHA AS DEMAIS FUNÇÕES AUXILIARES EXISTENTES NO ARQUIVO:
# check_and_apply_level_up, needs_class_choice, _get_point_gains_for_class, etc.]
# Elas não precisam de alteração para o balanceamento funcionar.

def check_and_apply_level_up(player_data: dict) -> tuple[int, int, str]:
    levels_gained, points_gained = 0, 0
    current_xp = int(player_data.get('xp', 0))
    ckey = _get_class_key_normalized(player_data)

    while True:
        current_level = int(player_data.get('level', 1))
        xp_needed = int(game_data.get_xp_for_next_combat_level(current_level))
        if xp_needed <= 0 or current_xp < xp_needed: break
        
        current_xp -= xp_needed
        # Baseline update apenas para HP
        old_baseline = _compute_class_baseline_for_level(ckey, current_level)
        new_baseline = _compute_class_baseline_for_level(ckey, current_level + 1)
        hp_increase = max(0, new_baseline.get("max_hp", 0) - old_baseline.get("max_hp", 0))

        player_data['level'] = current_level + 1
        player_data["current_hp"] = int(player_data.get("current_hp", 1) + hp_increase)
        
        levels_gained += 1
        points_gained += 1 

    if levels_gained > 0:
        player_data['xp'] = current_xp
        current_balance = int(player_data.get('stat_points', 0))
        player_data['stat_points'] = current_balance + points_gained

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

async def mark_class_choice_offered(user_id: Union[str, int]):
    from .core import get_player_data, save_player_data
    uid = str(user_id) if isinstance(user_id, int) else user_id
    pdata = await get_player_data(uid)
    if not pdata: return
    pdata["class_choice_offered"] = True
    await save_player_data(uid, pdata)

def _get_point_gains_for_class(ckey: str) -> dict:
    norm_key = (ckey or "").lower()
    gains = CLASS_POINT_GAINS.get(norm_key)
    if gains is None and norm_key != "_default":
        try:
            ancestry = get_class_ancestry(norm_key)
            if ancestry:
                base_class = ancestry[-1]
                gains = CLASS_POINT_GAINS.get(base_class.lower())
        except: pass
    if gains is None: gains = CLASS_POINT_GAINS["_default"]
    return gains

def compute_spent_status_points(pdata: dict) -> int:
    inv = pdata.get("invested")
    if isinstance(inv, dict):
        return sum(int(v) for v in inv.values())
    return 0

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
    player_data["class"] = new_class_key
    player_data["class_key"] = new_class_key
    if "class_tag" in player_data: del player_data["class_tag"]
    await reset_stats_and_refund_points(player_data)
    player_data["class_choice_offered"] = True
    return player_data

def add_xp(player_data: dict, amount: int):
    if not player_data: return
    current_xp = player_data.get("xp", 0)
    try:
        amount = int(amount)
        current_xp = int(current_xp)
    except: amount = 0
    player_data["xp"] = current_xp + amount

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
                target = _map_stat_name(stat) or stat
                if target in total_stats:
                    bonus_valor = total_stats[target] * float(multiplier)
                    total_stats[target] += int(bonus_valor)
                elif target == "magic_attack": 
                    if "magic_attack" not in total_stats: total_stats["magic_attack"] = total_stats.get("attack", 0)
                    total_stats["magic_attack"] += int(total_stats.get("magic_attack", 0) * float(multiplier))

        res_bonuses = effects.get("resistance_mult", {})
        if res_bonuses:
            if "resistance" not in total_stats: total_stats["resistance"] = {}
            for res_type, value in res_bonuses.items():
                total_stats["resistance"][res_type] = total_stats["resistance"].get(res_type, 0.0) + float(value)
        if effects.get("crit_immune", False): total_stats["crit_immune"] = True 

        scaling = effects.get("stat_scaling")
        if scaling:
            try:
                src = _map_stat_name(scaling["source_stat"]) or scaling["source_stat"]
                tgt = _map_stat_name(scaling["target_stat"]) or scaling["target_stat"]
                val = total_stats.get(src, 0)
                bonus = val * float(scaling["ratio"])
                if tgt in total_stats: total_stats[tgt] += int(bonus)
                else: total_stats[tgt] = total_stats.get(tgt, 0.0) + bonus
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
                target = _map_stat_name(stat) or stat
                if target in target_stats:
                    bonus_valor = target_stats[target] * float(multiplier)
                    target_stats[target] += int(bonus_valor)
                else:
                    target_stats[target] = target_stats.get(target, 0.0) + float(multiplier)
        if aura_bonuses.get("cannot_be_dodged", False): target_stats["cannot_be_dodged"] = True
        if "hp_regen_percent" in aura_bonuses:
             target_stats["hp_regen_percent"] = target_stats.get("hp_regen_percent", 0.0) + float(aura_bonuses["hp_regen_percent"])
        if "mp_regen_percent" in aura_bonuses:
             target_stats["mp_regen_percent"] = target_stats.get("mp_regen_percent", 0.0) + float(aura_bonuses["mp_regen_percent"])

async def _sync_all_stats_inplace(pdata: dict) -> bool: return False
def _migrate_point_pool_to_stat_points_inplace(pdata: dict) -> bool: return False
def _get_default_baseline_from_new_player() -> dict: return {"max_hp": 50, "attack": 5, "defense": 3, "initiative": 5, "luck": 5}
def _ensure_base_stats_block_inplace(pdata: dict) -> bool: return False
def _current_invested_delta_over_baseline(pdata: dict, baseline: dict) -> dict: return {}
async def _apply_class_progression_sync_inplace(pdata: dict) -> bool: return False
def _sync_stat_points_to_level_cap_inplace(pdata: dict) -> bool: return False