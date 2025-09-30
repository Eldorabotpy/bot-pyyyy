# modules/balance.py
from __future__ import annotations
from typing import Dict, Tuple

# ---- Regras base de status ----
# Observações:
# - HP agora rende +3 por ponto (antes era 12).
# - Softcap = ponto a partir do qual entra DR (diminuição de retorno).
# - dr_factor = multiplicador aplicado aos pontos ACIMA do softcap.
# - hardcap = limite superior em "pontos efetivos" (antes de multiplicar por per_point).
STAT_RULES: Dict[str, dict] = {
    "hp":         {"per_point": 3.0,  "softcap": 50, "dr_factor": 0.6, "hardcap": 120},
    "attack":     {"per_point": 1.8,  "softcap": 40, "dr_factor": 0.7, "hardcap": 100},
    "defense":    {"per_point": 1.6,  "softcap": 40, "dr_factor": 0.7, "hardcap": 100},
    "initiative": {"per_point": 0.8,  "softcap": 35, "dr_factor": 0.7, "hardcap": 90},
    "luck":       {"per_point": 0.5,  "softcap": 30, "dr_factor": 0.6, "hardcap": 80},
}

# Custo por ponto no MESMO status (degraus por total já investido naquele status)
COST_STEPS: Tuple[Tuple[int, int], ...] = (
    (25, 1),   # 0..24 -> próximo ponto custa 1
    (50, 2),   # 25..49 -> custa 2
    (9999, 3)  # 50+ -> custa 3
)

# Mapeamento dos pesos (afinidade de classe) para custo/efeito/exibição
# p_norm = (peso - min) / (max - min)  => 0..1
COST_MIN, COST_MAX = 0.8, 1.2           # favorecido => mais barato
EFFECT_MIN, EFFECT_MAX = 0.90, 1.10     # favorecido => rende ~+10%
DISPLAY_MIN, DISPLAY_MAX = 0.90, 1.10   # apenas visual

def _get_class_weights(class_key: str) -> Dict[str, float]:
    """
    Lê 'stat_modifiers' do modules.game_data.classes (CLASSES_DATA[class_key]['stat_modifiers'])
    como PESOS de afinidade. Se não achar, usa 1.0 para todos.
    """
    try:
        from modules.game_data import classes as classes_mod  # CLASSES_DATA
        raw = getattr(classes_mod, "CLASSES_DATA", {}).get(class_key, {})
        weights = dict(raw.get("stat_modifiers", {}))
        for s in STAT_RULES.keys():
            weights.setdefault(s, 1.0)
        return weights
    except Exception:
        return {s: 1.0 for s in STAT_RULES.keys()}

def _normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """
    Normaliza cada peso para 0..1 por classe (min→0, max→1).
    Se não houver variação, tudo vira 0.5 (neutro).
    """
    vals = list(weights.values())
    w_min, w_max = min(vals), max(vals)
    if w_max <= w_min:
        return {k: 0.5 for k in weights.keys()}
    return {k: (v - w_min) / (w_max - w_min) for k, v in weights.items()}

def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def class_affinity_factors(class_key: str, stat: str) -> Tuple[float, float, float]:
    """
    Retorna (cost_mult, effect_mult, display_mult) para UMA classe/UM stat.

    IMPORTANTE: Afinidades NÃO afetam HP (nem custo, nem efeito).
    Para 'hp', devolvemos (1.0, 1.0, 1.0).
    """
    if stat == "hp":
        return (1.0, 1.0, 1.0)

    weights = _get_class_weights(class_key)
    norm = _normalize_weights(weights)
    p = float(norm.get(stat, 0.5))

    cost_mult = _lerp(COST_MAX, COST_MIN, p)         # p=1 -> 0.8 | p=0 -> 1.2
    effect_mult = _lerp(EFFECT_MIN, EFFECT_MAX, p)   # p=1 -> 1.10 | p=0 -> 0.90
    display_mult = _lerp(DISPLAY_MIN, DISPLAY_MAX, p)
    return (cost_mult, effect_mult, display_mult)

def point_cost_for(stat: str, already_invested_in_stat: int, class_key: str) -> int:
    """
    Custo do PRÓXIMO ponto nesse stat: degrau base + afinidade da classe (exceto HP).
    """
    base_cost = 1
    for limit, cost in COST_STEPS:
        if already_invested_in_stat < limit:
            base_cost = cost
            break

    cost_mult, _, _ = class_affinity_factors(class_key, stat)
    final_cost = max(1, int(round(base_cost * cost_mult)))
    return final_cost

def effect_from_points(stat: str, points_in_stat: int, class_key: str) -> float:
    """
    Efeito BRUTO acumulado dos pontos para um stat:
      - aplica softcap/DR
      - aplica afinidade (exceto em HP)
      - clamp em hardcap (em “pontos efetivos” × per_point)
    """
    rules = STAT_RULES[stat]
    per = float(rules["per_point"])
    sc = int(rules["softcap"])
    dr = float(rules["dr_factor"])
    cap = int(rules["hardcap"])

    under = min(points_in_stat, sc)
    over  = max(0, points_in_stat - sc)

    total = under * per + over * per * dr

    # Afinidade só para ATK/DEF/INI/SRT (hp fica neutro)
    _, effect_mult, _ = class_affinity_factors(class_key, stat)
    total *= effect_mult

    # Hardcap em pontos efetivos
    max_total = cap * per
    return min(total, max_total)

# ----- Utilitário para UI (opcional) -----
def ui_display_modifiers(class_key: str) -> Dict[str, float]:
    """
    Multiplicadores apenas para EXIBIÇÃO (0.90..1.10),
    derivados dos PESOS — para o menu de detalhes da classe.
    HP fica 1.0 (sem afinidade visual).
    """
    mods = {}
    for stat in STAT_RULES.keys():
        if stat == "hp":
            mods[stat] = 1.0
        else:
            _, _, disp = class_affinity_factors(class_key, stat)
            mods[stat] = round(disp, 2)
    return mods
