# modules/balance.py
from __future__ import annotations
from typing import Dict, Tuple

# ---- Regras base de status ----
# REGRA OFICIAL DA TELA DE ATRIBUTOS:
# - Cada clique no botão + gasta exatamente 1 ponto livre.
# - Cada clique adiciona exatamente +1 investimento visível no atributo.
# - Sem custo progressivo, sem ganho fracionado e sem hardcap silencioso.
#
# Motivo: a tela só possui Ataque, Defesa, Agilidade e Sorte.
# A regra antiga tinha custo 2/3, ganho fracionado e hardcap; isso podia consumir
# vários pontos sem o número subir na tela, principalmente em Sorte/Agilidade.
STAT_RULES: Dict[str, dict] = {
    "hp":         {"per_point": 1.0, "softcap": 999999, "dr_factor": 1.0, "hardcap": 999999},
    "attack":     {"per_point": 1.0, "softcap": 999999, "dr_factor": 1.0, "hardcap": 999999},
    "defense":    {"per_point": 1.0, "softcap": 999999, "dr_factor": 1.0, "hardcap": 999999},
    "initiative": {"per_point": 1.0, "softcap": 999999, "dr_factor": 1.0, "hardcap": 999999},
    "luck":       {"per_point": 1.0, "softcap": 999999, "dr_factor": 1.0, "hardcap": 999999},
}

# Mantido por compatibilidade com outras partes do código, mas o custo real agora é sempre 1.
COST_STEPS: Tuple[Tuple[int, int], ...] = (
    (999999, 1),
)

# Afinidade continua existindo apenas para exibição futura, não para custo/ganho de ponto.
COST_MIN, COST_MAX = 1.0, 1.0
EFFECT_MIN, EFFECT_MAX = 1.0, 1.0
DISPLAY_MIN, DISPLAY_MAX = 0.90, 1.10

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
    Custo oficial da UI de atributos: sempre 1 ponto livre por clique.
    """
    return 1

def effect_from_points(stat: str, points_in_stat: int, class_key: str) -> float:
    """
    Efeito oficial da UI de atributos: 1 investimento = +1 atributo.
    Retorna o valor acumulado inteiro para impedir gasto sem aumento visual.
    """
    try:
        return max(0, int(points_in_stat or 0))
    except Exception:
        return 0

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
