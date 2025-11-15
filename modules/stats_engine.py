# modules/stats_engine.py
from __future__ import annotations
from typing import Dict, Tuple
from modules.game_data.classes import get_stat_modifiers
# =========================
# Pontos por atributo (fixo)
# =========================
# hp => +3 por ponto
# attack/defense/initiative/luck => +1 por ponto
PER_POINT: Dict[str, int] = {
    "hp": 3,
    "attack": 1,
    "defense": 1,
    "initiative": 1,
    "luck": 1,
}

def _i(x) -> int:
    try:
        return int(round(float(x)))
    except Exception:
        return 0

# =========================
# Distribuição por pontos investidos
# (sem modificadores de classe aqui; os multiplicadores de classe
#  costumam ser aplicados em outro estágio do pipeline de stats)
# =========================
def compute_final_stats(class_key: str, invested: Dict[str, int] | None) -> Dict[str, int]:
    """
    Retorna APENAS o bloco 'base por pontos' (para UI e composições),
    já aplicando os ganhos fixos E OS MODIFICADORES DE CLASSE.
    """
    inv = invested or {}
    
    # --- LINHAS ADICIONADAS ---
    # Pega os modificadores da classe (ex: {'hp': 3.0, 'attack': 1.4, ...})
    modifiers = get_stat_modifiers(class_key)
    mod_hp  = modifiers.get("hp", 1.0)
    mod_atk = modifiers.get("attack", 1.0)
    mod_def = modifiers.get("defense", 1.0)
    mod_ini = modifiers.get("initiative", 1.0)
    mod_luk = modifiers.get("luck", 1.0)
    # --------------------------

    pts_hp  = _i(inv.get("hp", 0))
    pts_atk = _i(inv.get("attack", 0))
    pts_def = _i(inv.get("defense", 0))
    pts_ini = _i(inv.get("initiative", 0))
    pts_luk = _i(inv.get("luck", 0))

    # --- BLOCO DE RETORNO ALTERADO ---
    # Agora a fórmula é: (Pontos * ValorPorPonto) * ModificadorDaClasse
    return {
        "hp":         _i((pts_hp  * PER_POINT["hp"])       * mod_hp),
        "attack":     _i((pts_atk * PER_POINT["attack"])   * mod_atk),
        "defense":    _i((pts_def * PER_POINT["defense"])  * mod_def),
        "initiative": _i((pts_ini * PER_POINT["initiative"]) * mod_ini),
        "luck":       _i((pts_luk * PER_POINT["luck"])     * mod_luk),
    }

# =========================
# Dano por raridade (usado pela forja)
# =========================
# Multiplicadores por raridade. Ajuste à vontade para calibrar progressão.
_RARITY_DMG_MULT: Dict[str, float] = {
    "comum":    1.00,
    "bom":      1.10,
    "raro":     1.25,
    "epico":    1.45,
    "lendario": 1.70,
}

def _apply_rarity_multiplier_to_range(base_min: int, base_max: int, rarity: str) -> Tuple[int, int]:
    k = str(rarity or "comum").lower()
    mult = float(_RARITY_DMG_MULT.get(k, 1.0))
    # arredonda pra inteiro e garante pelo menos 1
    out_min = max(1, int(round(base_min * mult)))
    out_max = max(out_min, int(round(base_max * mult)))
    return out_min, out_max

def calc_damage_range_for_class(base_min: int, base_max: int, rarity: str) -> Tuple[int, int]:
    """
    Aplica um multiplicador de raridade sobre (base_min, base_max) e retorna (min, max) inteiros.
    OBS: O *tipo* do dano e o *atributo* que escala (for/int/agi/sab) são definidos
         em modules.game_data.classes.get_primary_damage_profile(...) e usados pela forja.
    """
    try:
        bmin = int(base_min)
        bmax = int(base_max)
    except Exception:
        # fallback seguro
        bmin, bmax = 1, max(1, int(base_max) if isinstance(base_max, (int, float, str)) else 1)

    if bmin <= 0 and bmax <= 0:
        bmin, bmax = 1, 1
    if bmax < bmin:
        bmax = bmin

    return _apply_rarity_multiplier_to_range(bmin, bmax, rarity)
